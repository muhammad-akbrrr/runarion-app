import { useState, useEffect, useRef, useCallback } from 'react';
import { router } from '@inertiajs/react';
import { Project, ProjectChapter } from '@/types';
import { useUnifiedSave } from './useUnifiedSave';
import { useStreamingLLM } from './useStreamingLLM';
import { useOptimizedVersionControl } from './useOptimizedVersionControl';
import Echo from '@/echo';

interface UseProjectEditorProps {
    workspaceId: string;
    projectId: string;
    project: Project;
    initialChapters: ProjectChapter[];
}

/**
 * Calculate plain text length from markdown string
 * This matches what textContent returns from DOM elements
 */
function getPlainTextLength(markdown: string): number {
    if (!markdown) return 0;
    // Remove markdown formatting to get plain text length
    // This matches what textContent returns from DOM
    let plainText = markdown
        .replace(/\*\*([^*]+)\*\*/g, '$1')      // **bold** - remove first
        .replace(/\*([^*]+)\*/g, '$1')         // *italic* - after bold is removed
        .replace(/`([^`]+)`/g, '$1')           // `code`
        .replace(/#{1,6}\s+/g, '')             // headings (# Header)
        .replace(/^\s*[-*+]\s+/gm, '')         // unordered list markers
        .replace(/^\s*\d+\.\s+/gm, '')         // ordered list markers
        .replace(/^>\s+/gm, '')                // blockquote markers
        .replace(/~~([^~]+)~~/g, '$1');        // ~~strikethrough~~
    
    return plainText.length;
}

/**
 * Get plain text from markdown (for segment calculations)
 */
function getPlainText(markdown: string): string {
    if (!markdown) return '';
    return markdown
        .replace(/\*\*([^*]+)\*\*/g, '$1')
        .replace(/\*([^*]+)\*/g, '$1')
        .replace(/`([^`]+)`/g, '$1')
        .replace(/#{1,6}\s+/g, '')
        .replace(/^\s*[-*+]\s+/gm, '')
        .replace(/^\s*\d+\.\s+/gm, '')
        .replace(/^>\s+/gm, '')
        .replace(/~~([^~]+)~~/g, '$1');
}

/**
 * Adjust AI ranges when user inserts or deletes text
 * This handles the "edit in between AI text" use case
 */
function adjustAiRanges(ranges: number[][], changePos: number, changeDelta: number): number[][] {
    const newRanges: number[][] = [];
    
    for (const [start, end] of ranges) {
        // Case 1: Edit is AFTER this range - no change needed
        if (changePos >= end) {
            newRanges.push([start, end]);
            continue;
        }
        
        // Case 2: Edit is BEFORE this range - shift entire range
        if (changePos <= start) {
            const newStart = start + changeDelta;
            const newEnd = end + changeDelta;
            if (newStart >= 0 && newEnd > newStart) {
                newRanges.push([newStart, newEnd]);
            }
            continue;
        }
        
        // Case 3: Edit is INSIDE this range
        if (changeDelta > 0) {
            // INSERTION: Split the range into two, leaving a gap for user text
            // Example: Range [100, 200], insert 5 chars at position 150
            // Result: [100, 150] (AI) ... gap of 5 (User) ... [155, 205] (AI)
            newRanges.push([start, changePos]); 
            newRanges.push([changePos + changeDelta, end + changeDelta]);
        } else {
            // DELETION: Shrink the range
            const newEnd = end + changeDelta;
            if (newEnd > start) {
                newRanges.push([start, newEnd]);
            }
        }
    }
    
    // Filter out invalid ranges (where start >= end)
    return newRanges.filter(([s, e]) => s < e);
}

export function useProjectEditor({
    workspaceId,
    projectId,
    project,
    initialChapters,
}: UseProjectEditorProps) {
    // Core state
    const [isGenerating, setIsGenerating] = useState(false);
    const [content, setContent] = useState("");
    const [settings, setSettings] = useState(project.settings || {});
    const [localChapters, setLocalChapters] = useState<ProjectChapter[]>(initialChapters);
    const [selectedChapter, setSelectedChapter] = useState<ProjectChapter | null>(null);
    const [preservedChapterOrder, setPreservedChapterOrder] = useState<number | null>(null);
    
    // Refs for tracking state
    const isInitialized = useRef(false);
    const originalContent = useRef<string>('');
    const originalSettings = useRef<any>({});
    
    // Track the last chapter order to detect actual chapter switches vs content updates
    const lastChapterOrderRef = useRef<number | null>(null);
    
    // Base content for streaming (user text before generation starts)
    const [baseContent, setBaseContent] = useState<string>('');
    const baseContentRef = useRef<string>('');
    
    // AI RANGES COLOR CODING: Track [start, end] positions of AI-generated text
    // Everything defaults to BLUE (user text)
    // Only text inside an aiRange is GRAY (AI text)
    // When user types inside AI text, the range splits, creating a blue gap
    const [aiRanges, setAiRanges] = useState<number[][]>([]);
    
    // Track previous plain text for diff detection
    const prevPlainTextRef = useRef<string>('');
    
    // Track where generation started (to calculate AI range end)
    const generationStartPos = useRef<number>(0);
    
    // Flag to skip diff detection immediately after generation
    const justCompletedGeneration = useRef<boolean>(false);
    
    // Color coding toggle (default: enabled)
    const [isColorCoded, setIsColorCoded] = useState<boolean>(true);
    
    // Refs to access current values inside callbacks (avoid stale closure)
    const selectedChapterRef = useRef<ProjectChapter | null>(null);
    const saveContentRef = useRef<((order: number, content: string | null, trigger: string, aiRanges?: number[][]) => Promise<any>) | null>(null);

    // Unified save hook
    const {
        saveContent,
        saveSettings,
        debouncedSaveContent,
        debouncedSaveSettings,
        forceSave,
        cancelPendingSaves,
    } = useUnifiedSave({
        workspaceId,
        projectId,
        onContentSaved: (updatedChapters) => {
            console.log('Content saved, updating local chapters');
            setLocalChapters(updatedChapters);
            
            // Update selected chapter with latest content
            if (selectedChapter) {
                const updatedSelectedChapter = updatedChapters.find(ch => ch.order === selectedChapter.order);
                if (updatedSelectedChapter) {
                    setSelectedChapter(updatedSelectedChapter);
                    originalContent.current = updatedSelectedChapter.content || '';
                }
            }
        },
        onSettingsSaved: () => {
            console.log('Settings saved successfully');
            originalSettings.current = { ...settings };
        },
        onSaveError: (error) => {
            console.error('Save error:', error);
        },
    });

    // Keep refs updated for use inside callbacks
    selectedChapterRef.current = selectedChapter;
    saveContentRef.current = saveContent;

    // Streaming LLM hook
    const {
        isStreaming,
        streamingText,
        error: streamError,
        isRegenerating,
        cancelStream,
    } = useStreamingLLM({
        workspaceId,
        projectId,
        chapterOrder: selectedChapter?.order ?? 0,
        onStreamComplete: (generatedText) => {
            console.log('🎯 Stream completed', {
                isRegenerating,
                generatedTextLength: generatedText.length,
                generationStartPos: generationStartPos.current,
                baseContentRefLength: baseContentRef.current?.length || 0,
                baseContentPreview: baseContentRef.current?.substring(0, 50) || '(empty)'
            });
            setIsGenerating(false);
            
            // CRITICAL: Use baseContentRef which was frozen BEFORE generation started
            const userText = baseContentRef.current || '';
            let separator = '';
            
            if (userText && !userText.endsWith('\n') && !userText.endsWith(' ') && 
                !generatedText.startsWith('\n') && !generatedText.startsWith(' ')) {
                separator = ' ';
            }
            
            const finalContent = userText + separator + generatedText;
            
            console.log('🎯 Final content composed:', {
                userTextLength: userText.length,
                separatorLength: separator.length,
                generatedTextLength: generatedText.length,
                finalContentLength: finalContent.length
            });
            
            // Calculate the AI text range
            // Start = where user text ended (in plain text chars)
            // End = start + length of generated text (in plain text chars)
            const aiStart = generationStartPos.current;
            const generatedPlainText = getPlainText(generatedText);
            const separatorLength = separator.length;
            const aiEnd = aiStart + separatorLength + generatedPlainText.length;
            
            console.log('🎨 Calculating AI range:', { aiStart, aiEnd, generatedPlainTextLength: generatedPlainText.length });
            
            // Add this AI range to our tracking and save immediately
            // NOTE: We compute the new ranges synchronously to use in the save
            const newRange: [number, number] = aiEnd > aiStart ? [aiStart, aiEnd] : [0, 0];
            let updatedRanges: number[][] = [];
            
            if (aiEnd > aiStart) {
                // Use a ref to capture the computed ranges for the save
                setAiRanges((prev: number[][]) => {
                    updatedRanges = [...prev, newRange];
                    console.log('🎨 setAiRanges called:', { prev, newRange, updated: updatedRanges });
                    
                    // Trigger save INSIDE the setState callback where we have the correct ranges
                    // Use refs to avoid stale closure issues
                    const currentChapter = selectedChapterRef.current;
                    const currentSaveContent = saveContentRef.current;
                    if (currentChapter && currentSaveContent) {
                        console.log('🎨 Saving content with aiRanges after generation:', { 
                            order: currentChapter.order, 
                            aiRangesCount: updatedRanges.length,
                            updatedRanges
                        });
                        currentSaveContent(currentChapter.order, finalContent, 'llm_generation', updatedRanges);
                    } else {
                        console.log('🎨 Cannot save - missing refs:', { hasChapter: !!currentChapter, hasSave: !!currentSaveContent });
                    }
                    
                    return updatedRanges;
                });
            } else {
                console.log('🎨 Skipping AI range - aiEnd <= aiStart');
            }
            
            // CRITICAL: Set flag to skip diff detection for the next content update
            justCompletedGeneration.current = true;
            
            // Update content state
            setContent(finalContent);
            originalContent.current = finalContent;
            
            // Update prevPlainTextRef so diff detection works correctly
            prevPlainTextRef.current = getPlainText(finalContent);
        },
        onStreamError: (error) => {
            console.error('Stream error:', error);
            setIsGenerating(false);
            
            // Show error alert
            alert(error);
            
            // On error during regeneration, restore the original chapter content
            if (isRegenerating && selectedChapter) {
                setContent(selectedChapter.content || '');
                originalContent.current = selectedChapter.content || '';
            }
        },
    });

    // Version control hook
    const versionControl = useOptimizedVersionControl({
        workspaceId,
        projectId,
        chapterOrder: selectedChapter?.order ?? 0,
        initialNavigationInfo: selectedChapter?.navigation_info,
        onContentUpdate: (newContent) => {
            setContent(newContent);
            originalContent.current = newContent;
        },
        isGenerating: isGenerating || isStreaming,
    });

    // Update local chapters when prop changes
    useEffect(() => {
        setLocalChapters(initialChapters);
        
        // Restore preserved chapter after generation
        if (preservedChapterOrder !== null) {
            const chapterToRestore = initialChapters.find(ch => ch.order === preservedChapterOrder);
            if (chapterToRestore) {
                console.log("Restoring chapter after generation:", chapterToRestore.chapter_name);
                setSelectedChapter(chapterToRestore);
                setPreservedChapterOrder(null);
                return;
            }
        }
        
        // Update or reset selected chapter based on whether it still exists
        if (selectedChapter) {
            const updatedChapter = initialChapters.find(ch => ch.order === selectedChapter.order);
            if (updatedChapter) {
                // Chapter still exists - update if content changed
                if (updatedChapter.content !== selectedChapter.content) {
                    console.log('Chapter content updated from server');
                    setSelectedChapter(updatedChapter);
                }
            } else {
                // Chapter was deleted - reset to first available chapter or null
                console.log('Selected chapter was deleted, selecting first available chapter');
                
                // Clear the lastChapterOrderRef so the chapter switch useEffect treats this as a new switch
                lastChapterOrderRef.current = null;
                
                if (initialChapters.length > 0) {
                    const newChapter = initialChapters[0];
                    console.log('Switching to chapter:', newChapter.chapter_name, 'with content length:', newChapter.content?.length || 0);
                    
                    // Clear localStorage of deleted chapter reference
                    const storageKey = `lastChapter_${projectId}`;
                    localStorage.setItem(storageKey, newChapter.order.toString());
                    
                    // Set the new chapter - the useEffect watching selectedChapter will load content
                    setSelectedChapter(newChapter);
                } else {
                    setSelectedChapter(null);
                    // Only clear content if there are no chapters at all
                    setContent("");
                    originalContent.current = "";
                    setAiRanges([]);
                }
            }
        }
    }, [initialChapters, preservedChapterOrder, projectId]);

    // Initialize content when chapter changes
    useEffect(() => {
        if (selectedChapter) {
            const chapterContent = selectedChapter.content || "";
            const isChapterSwitch = lastChapterOrderRef.current !== selectedChapter.order;
            
            console.log('Chapter useEffect triggered:', {
                chapterName: selectedChapter.chapter_name,
                isChapterSwitch,
                justCompletedGeneration: justCompletedGeneration.current,
                lastOrder: lastChapterOrderRef.current,
                currentOrder: selectedChapter.order
            });
            
            // Update the last chapter order
            lastChapterOrderRef.current = selectedChapter.order;
            
            // If generation just completed, DON'T reset anything
            // The server pushed an update with the new content, but we already have it
            if (justCompletedGeneration.current) {
                console.log('Skipping chapter init - generation just completed, preserving aiRanges');
                // Keep the flag set for a bit longer to handle multiple updates
                setTimeout(() => {
                    justCompletedGeneration.current = false;
                }, 1000);
                return;
            }
            
            // Only reset everything on actual chapter switch
            if (isChapterSwitch) {
                console.log('Initializing content for chapter:', selectedChapter.chapter_name);
                setContent(chapterContent);
                originalContent.current = chapterContent;
                
                // Reset baseContent when switching chapters
                setBaseContent("");
                
                // Load AI ranges from chapter data (persisted to server)
                // If no ai_ranges saved, start fresh with empty array
                const savedAiRanges = (selectedChapter as any).ai_ranges || [];
                console.log('🎨 Loading ai_ranges from chapter:', savedAiRanges);
                setAiRanges(savedAiRanges);
                prevPlainTextRef.current = getPlainText(chapterContent);
                
                // Save last viewed chapter to localStorage
                const storageKey = `lastChapter_${projectId}`;
                localStorage.setItem(storageKey, selectedChapter.order.toString());
                
                // Initialize version control if needed
                if (!selectedChapter.navigation_info) {
                    initializeChapterHistory(selectedChapter.order, chapterContent);
                }
            } else {
                // Same chapter, content updated from server - don't reset aiRanges
                console.log('Content updated from server for same chapter, preserving aiRanges');
            }
        } else {
            setContent("");
            originalContent.current = "";
            setBaseContent("");
            setAiRanges([]);
            prevPlainTextRef.current = '';
            lastChapterOrderRef.current = null;
        }
    }, [selectedChapter?.order, selectedChapter?.content, projectId]);

    // Initialize settings - only on mount or when project.settings changes from server
    useEffect(() => {
        const initialSettings = project.settings || {};
        
        // Only update if settings have actually changed from server
        // This prevents resetting user changes during chapter switches
        const settingsChanged = JSON.stringify(initialSettings) !== JSON.stringify(originalSettings.current);
        
        if (settingsChanged || !isInitialized.current) {
            console.log('Initializing settings from project:', { settingsChanged, isInitialized: isInitialized.current });
            setSettings(initialSettings);
            originalSettings.current = initialSettings;
        }
        
        // Mark as initialized
        if (!isInitialized.current) {
            const timer = setTimeout(() => {
                isInitialized.current = true;
                console.log("Project editor initialized");
            }, 100);

            return () => clearTimeout(timer);
        }
    }, [project.settings]);

    // Auto-save settings when they change
    useEffect(() => {
        if (!isInitialized.current || isGenerating || isStreaming) {
            console.log('Skipping settings auto-save:', { 
                isInitialized: isInitialized.current, 
                isGenerating, 
                isStreaming 
            });
            return;
        }

        const settingsChanged = JSON.stringify(settings) !== JSON.stringify(originalSettings.current);
        
        if (settingsChanged) {
            console.log('Settings changed, auto-saving with 2s debounce', {
                changedKeys: Object.keys(settings).filter(key => 
                    JSON.stringify(settings[key]) !== JSON.stringify(originalSettings.current[key])
                )
            });
            // Use 2 second debounce for settings to batch rapid changes
            debouncedSaveSettings(settings, 2000);
        }
    }, [settings, debouncedSaveSettings, isGenerating, isStreaming]);

    // Handle streaming text updates - removed duplicate logic
    // The StreamingPlugin will handle the visual streaming updates
    // We only need to track the streaming state here
    useEffect(() => {
        if (isStreaming && streamingText) {
            console.log('Streaming in progress:', {
                baseContentLength: originalContent.current.length,
                streamingTextLength: streamingText.length,
                isRegenerating,
            });
        }
    }, [isStreaming, streamingText, isRegenerating]);

    // Auto-select chapter (restore last viewed or default to first)
    useEffect(() => {
        if (localChapters.length > 0 && !selectedChapter && preservedChapterOrder === null) {
            // Try to restore last viewed chapter from localStorage
            const storageKey = `lastChapter_${projectId}`;
            const lastChapterOrder = localStorage.getItem(storageKey);
            
            let chapterToSelect = localChapters[0];
            
            if (lastChapterOrder !== null) {
                const lastChapter = localChapters.find(ch => ch.order === parseInt(lastChapterOrder));
                if (lastChapter) {
                    chapterToSelect = lastChapter;
                    console.log("Restored last viewed chapter:", lastChapter.chapter_name);
                } else {
                    console.log("Last viewed chapter not found, using first chapter");
                }
            } else {
                console.log("No last viewed chapter, using first chapter");
            }
            
            setSelectedChapter(chapterToSelect);
        }
    }, [localChapters, selectedChapter, preservedChapterOrder, projectId]);

    // Listen for content updates from operations
    useEffect(() => {
        const channelName = `project.${workspaceId}.${projectId}`;
        let channel: any = null;

        try {
            channel = Echo.channel(channelName);
            
            channel.listen('.project.content.updated', (data: any) => {
                console.log('Project content updated via websocket:', data);
                
                // Security: Only process events for current workspace/project
                if (data.workspace_id !== workspaceId || data.project_id !== projectId) {
                    return;
                }
                
                // Only handle updates for the current chapter
                if (selectedChapter && data.chapter_order === selectedChapter.order) {
                    
                    // Handle different types of updates
                    if (['undo_step', 'redo_step', 'version_switch'].includes(data.trigger)) {
                        // Full content replacement for navigation operations
                        console.log('Updating content from navigation operation:', data.content);
                        setContent(data.content || '');
                        originalContent.current = data.content || '';
                        
                        // Refresh the page data to get updated navigation info
                        router.reload({ only: ['chapters'] });
                    } else if (data.trigger === 'regenerate_switch_to_parent') {
                        // Switch to parent content during regeneration
                        console.log('Switching to parent content for regeneration:', data.content);
                        setContent(data.content || '');
                        originalContent.current = data.content || '';
                    } else if (['llm_generation', 'llm_regeneration'].includes(data.trigger)) {
                        // Generation completed - refresh navigation info
                        console.log('Generation completed, refreshing navigation info');
                        setTimeout(() => {
                            router.reload({ only: ['chapters'] });
                        }, 100);
                    }
                }
            });
            
        } catch (error) {
            console.error('Error setting up content update listener:', error);
        }

        return () => {
            if (channel) {
                try {
                    channel.stopListening('.project.content.updated');
                    Echo.leave(channelName);
                } catch (error) {
                    console.error('Error cleaning up content update listener:', error);
                }
            }
        };
    }, [workspaceId, projectId, selectedChapter?.order]);

    // Chapter management functions
    const handleChapterSelect = useCallback((chapterOrder: number) => {
        if (isGenerating || isStreaming) {
            console.log("Cannot switch chapters during generation");
            return;
        }

        const chapter = localChapters.find(c => c.order === chapterOrder);
        if (chapter) {
            // Save current content before switching if changed
            const contentChanged = selectedChapter && content !== originalContent.current;
            const settingsChanged = JSON.stringify(settings) !== JSON.stringify(originalSettings.current);
            
            if (contentChanged || settingsChanged) {
                console.log('Saving before chapter switch', { contentChanged, settingsChanged });
                
                const saveData: any = {};
                
                if (contentChanged) {
                    saveData.content = {
                        order: selectedChapter.order,
                        content: content ?? '', // Treat null as empty string
                        trigger: 'manual'
                    };
                }
                
                if (settingsChanged) {
                    saveData.settings = settings;
                }
                
                forceSave(saveData);
            }
            
            setSelectedChapter(chapter);
            console.log("Chapter switched to:", chapter.chapter_name);
        }
    }, [localChapters, isGenerating, isStreaming, selectedChapter, content, settings, forceSave]);

    const handleAddChapter = useCallback((chapterName: string) => {
        if (isGenerating || isStreaming) {
            return Promise.reject(new Error("Cannot add chapters during generation"));
        }

        return new Promise<void>((resolve, reject) => {
            // Save current content and settings before adding chapter
            const contentChanged = selectedChapter && content !== originalContent.current;
            const settingsChanged = JSON.stringify(settings) !== JSON.stringify(originalSettings.current);
            
            if (contentChanged || settingsChanged) {
                console.log('Saving before adding chapter', { contentChanged, settingsChanged });
                
                const saveData: any = {};
                
                if (contentChanged) {
                    saveData.content = {
                        order: selectedChapter.order,
                        content: content ?? '', // Treat null as empty string
                        trigger: 'manual'
                    };
                }
                
                if (settingsChanged) {
                    saveData.settings = settings;
                }
                
                forceSave(saveData);
            }
            
            router.post(
                route("editor.project.chapter", {
                    workspace_id: workspaceId,
                    project_id: projectId,
                }),
                { chapter_name: chapterName },
                {
                    preserveState: true,
                    preserveScroll: true,
                    onSuccess: (page) => {
                        const updatedChapters = page.props.chapters as ProjectChapter[];
                        if (updatedChapters && updatedChapters.length > 0) {
                            setLocalChapters(updatedChapters);
                            setSelectedChapter(updatedChapters[updatedChapters.length - 1]);
                        }
                        resolve();
                    },
                    onError: (errors) => {
                        console.error("Failed to add chapter:", errors);
                        reject(errors);
                    },
                }
            );
        });
    }, [workspaceId, projectId, isGenerating, isStreaming, selectedChapter, content, settings, forceSave]);

    // Settings management
    const handleSettingChange = useCallback((key: string, value: any) => {
        setSettings(prev => ({
            ...prev,
            [key]: value
        }));
    }, []);

    // Initialize generation history for a chapter
    const initializeChapterHistory = useCallback(async (chapterOrder: number, content: string) => {
        try {
            console.log('Initializing chapter history:', { chapterOrder, contentLength: content.length });
            const response = await new Promise<any>((resolve, reject) => {
                router.post(
                    route("editor.project.initialize-history", {
                        workspace_id: workspaceId,
                        project_id: projectId,
                    }),
                    {
                        order: chapterOrder,
                        content: content,
                    },
                    {
                        preserveState: true,
                        preserveScroll: true,
                        onSuccess: (page) => {
                            console.log('Chapter history initialized successfully');
                            resolve(page);
                        },
                        onError: (errors) => {
                            console.error('Failed to initialize chapter history:', errors);
                            reject(errors);
                        },
                    }
                );
            });
        } catch (error) {
            console.error('Error initializing chapter history:', error);
        }
    }, [workspaceId, projectId]);

    // Text generation
    const handleGenerateText = useCallback((currentEditorContent?: string) => {
        if (!selectedChapter || isGenerating || isStreaming) {
            return;
        }

        setPreservedChapterOrder(selectedChapter.order);

        // Use current editor content if provided, otherwise fall back to state
        // This ensures we capture what the user actually sees, not stale state
        const currentContent = currentEditorContent ?? content ?? '';
        
        // Save current content and settings before generation
        const contentChanged = currentContent !== originalContent.current;
        const settingsChanged = JSON.stringify(settings) !== JSON.stringify(originalSettings.current);
        
        if (contentChanged || settingsChanged) {
            console.log('Saving before generation', { contentChanged, settingsChanged });
            
            const saveData: any = {};
            
            if (contentChanged) {
                saveData.content = {
                    order: selectedChapter.order,
                    content: currentContent,
                    trigger: 'manual'
                };
            }
            
            if (settingsChanged) {
                saveData.settings = settings;
            }
            
            forceSave(saveData);
        }
        
        // CRITICAL: Update originalContent to current content before generation
        originalContent.current = currentContent;
        
        // CRITICAL: Freeze baseContent BEFORE generation starts
        // baseContent = the user's text that was in the editor before AI generates
        setBaseContent(currentContent);
        baseContentRef.current = currentContent;
        
        // CRITICAL: Record where AI text will start (for aiRanges tracking)
        // This is the plain text length of current content
        const plainTextLength = getPlainText(currentContent).length;
        generationStartPos.current = plainTextLength;
        
        console.log('🎯 handleGenerateText - frozen state:', {
            baseContentRefLength: baseContentRef.current.length,
            baseContentPreview: baseContentRef.current.substring(0, 50),
            generationStartPos: generationStartPos.current,
            plainTextLength
        });
        prevPlainTextRef.current = getPlainText(currentContent);
        
        console.log('🎨 Generation starting at position:', plainTextLength);
        
        console.log('🎨 Generation will start at position:', plainTextLength);
        
        setContent(currentContent);

        console.log("Starting text generation with content:", {
            contentLength: currentContent.length,
            aiStartPosition: plainTextLength,
            contentPreview: currentContent.substring(0, 50) + '...'
        });
        
        // NOW trigger generation - baseContent is already set
        setIsGenerating(true);

        const generationSettings = {
            prompt: currentContent || "",
            order: selectedChapter.order,
            settings: {
                currentPreset: settings.currentPreset || "story-telling",
                authorProfile: settings.authorProfile || '',  // FIX: Was missing - needed for style DNA
                aiModel: settings.aiModel || 'gemini-2.0-flash',
                memory: settings.memory || '',
                storyGenre: settings.storyGenre || '',
                storyTone: settings.storyTone || '',
                storyPov: settings.storyPov || '',
                temperature: settings.temperature || 1.0,
                repetitionPenalty: settings.repetitionPenalty || 0.0,
                outputLength: settings.outputLength || 300,
                minOutputToken: settings.minOutputToken || 50,
                topP: settings.topP || 0.85,
                tailFree: settings.tailFree || 0.85,
                topA: settings.topA || 0.85,
                topK: settings.topK || 0.85,
                phraseBias: settings.phraseBias || [],
                bannedPhrases: settings.bannedPhrases || [],
                stopSequences: settings.stopSequences || [],
            }
        };

        router.post(
            route("editor.project.generate", {
                workspace_id: workspaceId,
                project_id: projectId,
            }),
            generationSettings,
            {
                preserveState: true,
                preserveScroll: true,
                onSuccess: () => {
                    console.log("Text generation request sent successfully");
                },
                onError: (errors) => {
                    console.error("Failed to start text generation:", errors);
                    setIsGenerating(false);
                    setPreservedChapterOrder(null);
                    
                    // Handle Inertia errors
                    if (errors.generation) {
                        alert(errors.generation);
                    } else {
                        alert('Failed to start generation. Please try again.');
                    }
                },
            }
        );
    }, [workspaceId, projectId, selectedChapter, content, isGenerating, isStreaming, settings, forceSave, setContent]);

    // Text regeneration
    const handleRegenerateText = useCallback((currentEditorContent?: string) => {
        if (!selectedChapter || isGenerating || isStreaming || !versionControl.canRegenerate) {
            return;
        }

        setPreservedChapterOrder(selectedChapter.order);
        setIsGenerating(true);

        // Use current editor content if provided, otherwise use state
        const currentContent = currentEditorContent ?? content ?? '';
        
        // Update baseContent to current content (which will be cleared during regeneration)
        originalContent.current = currentContent;
        setBaseContent(currentContent);
        setContent(currentContent);

        console.log("Starting text regeneration with content:", {
            contentLength: currentContent.length,
            contentPreview: currentContent.substring(0, 50) + '...'
        });

        const regenerationSettings = {
            order: selectedChapter.order,
            settings: {
                currentPreset: settings.currentPreset || "creative-writing",
                aiModel: settings.aiModel || 'gemini-2.0-flash',
                memory: settings.memory || '',
                storyGenre: settings.storyGenre || '',
                storyTone: settings.storyTone || '',
                storyPov: settings.storyPov || '',
                temperature: settings.temperature || 1.0,
                repetitionPenalty: settings.repetitionPenalty || 0.0,
                outputLength: settings.outputLength || 300,
                minOutputToken: settings.minOutputToken || 50,
                topP: settings.topP || 0.85,
                tailFree: settings.tailFree || 0.85,
                topA: settings.topA || 0.85,
                topK: settings.topK || 0.85,
                phraseBias: settings.phraseBias || [],
                bannedPhrases: settings.bannedPhrases || [],
                stopSequences: settings.stopSequences || [],
            }
        };

        router.post(
            route("editor.project.regenerate", {
                workspace_id: workspaceId,
                project_id: projectId,
            }),
            regenerationSettings,
            {
                preserveState: true,
                preserveScroll: true,
                onSuccess: () => {
                    console.log("Text regeneration request sent successfully");
                },
                onError: (errors) => {
                    console.error("Failed to start text regeneration:", errors);
                    setIsGenerating(false);
                    setPreservedChapterOrder(null);
                    
                    if (errors.generation) {
                        alert(errors.generation);
                    } else {
                        alert('Failed to start regeneration. Please try again.');
                    }
                },
            }
        );
    }, [workspaceId, projectId, selectedChapter, isGenerating, isStreaming, settings, versionControl.canRegenerate]);

    const handleCancelGeneration = useCallback(() => {
        if (isStreaming) {
            cancelStream();
        }
        setIsGenerating(false);
        setPreservedChapterOrder(null);
        
        // If we were regenerating, restore the original chapter content
        if (isRegenerating && selectedChapter) {
            console.log('Restoring content after regeneration cancellation');
            setContent(selectedChapter.content || '');
            originalContent.current = selectedChapter.content || '';
        }
        
        console.log("Text generation cancelled");
    }, [isStreaming, isRegenerating, selectedChapter, cancelStream]);

    // Smart save function that only saves if content actually changed
    const smartSave = useCallback((order: number, content: string | null, trigger: string) => {
        const normalizedContent = content ?? ''; // Treat null as empty string
        const normalizedOriginal = originalContent.current ?? ''; // Treat null as empty string
        
        if (selectedChapter && normalizedContent !== normalizedOriginal) {
            console.log('Content changed, saving:', { 
                originalLength: normalizedOriginal.length, 
                currentLength: normalizedContent.length,
                trigger,
                aiRangesCount: aiRanges.length
            });
            
            // Update the original content reference immediately to prevent duplicate saves
            originalContent.current = normalizedContent;
            
            if (trigger === 'auto') {
                // Pass aiRanges to persist them to the server
                debouncedSaveContent(order, normalizedContent, trigger, 1000, aiRanges);
            } else {
                saveContent(order, normalizedContent, trigger, aiRanges);
            }
        } else {
            console.log('No content change detected, skipping save');
        }
    }, [selectedChapter, saveContent, debouncedSaveContent, aiRanges]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            cancelPendingSaves();
        };
    }, [cancelPendingSaves]);

    // Sync baseContent ref with state
    useEffect(() => {
        baseContentRef.current = baseContent;
    }, [baseContent]);

    // Track user edits and adjust AI ranges accordingly
    // This enables "writing in between" AI text - the ranges split to accommodate user text
    useEffect(() => {
        // Don't track changes during AI generation/streaming
        if (isStreaming || isGenerating) return;
        if (content === undefined || content === null) return;
        
        // Skip if generation just completed - the AI ranges are already set correctly
        if (justCompletedGeneration.current) {
            console.log('🔍 Skipping diff detection - generation just completed');
            justCompletedGeneration.current = false;
            return;
        }
        
        const currentPlainText = getPlainText(content);
        const prevPlainText = prevPlainTextRef.current;
        
        // Only process if content actually changed AND there's a real diff
        if (currentPlainText !== prevPlainText) {
            const diff = currentPlainText.length - prevPlainText.length;
            
            // Skip if no actual length change (just formatting)
            if (diff === 0) {
                prevPlainTextRef.current = currentPlainText;
                return;
            }
            
            // Find where the change happened (first index that differs)
            let changePos = 0;
            const len = Math.min(prevPlainText.length, currentPlainText.length);
            while (changePos < len && prevPlainText[changePos] === currentPlainText[changePos]) {
                changePos++;
            }
            
            console.log('🔍 User edit detected:', { changePos, diff, prevLength: prevPlainText.length, currentLength: currentPlainText.length });
            
            // Adjust AI ranges based on the edit
            setAiRanges(prev => {
                const adjusted = adjustAiRanges(prev, changePos, diff);
                console.log('🔍 Adjusted AI ranges:', { before: prev, after: adjusted });
                return adjusted;
            });
            
            // Update ref for next comparison
            prevPlainTextRef.current = currentPlainText;
        }
    }, [content, isStreaming, isGenerating]);

    return {
        // State
        isSaving: false, // Always false since saves are async
        isGenerating: isGenerating || isStreaming,
        content,
        setContent,
        settings,
        localChapters,
        selectedChapter,
        
        // Streaming state
        isStreaming,
        streamingText,
        streamError,
        isRegenerating,
        baseContent, // User text before generation (for StreamingPlugin)
        aiRanges, // Array of [start, end] positions for AI text (for color coding)
        isColorCoded, // Color coding toggle state
        setIsColorCoded, // Toggle color coding
        
        // Version control state
        versionControl,
        
        // Computed values
        selectedChapterOrder: selectedChapter?.order ?? 0,
        
        // Actions
        handleChapterSelect,
        handleAddChapter,
        handleSettingChange,
        handleGenerateText,
        handleRegenerateText,
        handleCancelGeneration,
        
        // Save functions
        saveContent: (order: number, content: string | null, trigger: string) => saveContent(order, content ?? '', trigger, aiRanges),
        smartSave,
    };
}

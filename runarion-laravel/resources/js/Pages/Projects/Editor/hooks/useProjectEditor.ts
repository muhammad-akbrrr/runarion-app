import { useState, useEffect, useRef, useCallback } from 'react';
import { router } from '@inertiajs/react';
import { Project, ProjectChapter } from '@/types/project';
import { THINKING_MODELS } from '@/types/project';
import { useUnifiedSave } from './useUnifiedSave';
import { useStreamingLLM } from './useStreamingLLM';
import { useOptimizedVersionControl } from './useOptimizedVersionControl';
import { migrateAiRangesToMetadata, needsMigration } from '../utils/migrateAiRanges';
import Echo from '@/echo';

interface UseProjectEditorProps {
    workspaceId: string;
    projectId: string;
    project: Project;
    initialChapters: ProjectChapter[];
    editorRef?: React.MutableRefObject<any>;
}

/**
 * Check if content is valid Lexical JSON format
 */
function isLexicalJSON(content: string): boolean {
    if (!content?.trim().startsWith('{')) return false;
    try {
        const parsed = JSON.parse(content);
        return parsed.root?.type === 'root';
    } catch {
        return false;
    }
}

/**
 * Extract plain text from a Lexical JSON node recursively
 */
function extractTextFromLexicalNode(node: any): string {
    if (!node) return '';

    // Text node - return its text content
    if (node.type === 'text') {
        return node.text || '';
    }

    // For paragraph nodes, add newline after (except for the last one)
    if (node.type === 'paragraph' && node.children) {
        const text = node.children.map((child: any) => extractTextFromLexicalNode(child)).join('');
        return text;
    }

    // For root and other container nodes, process children
    if (node.children && Array.isArray(node.children)) {
        return node.children.map((child: any, index: number) => {
            const text = extractTextFromLexicalNode(child);
            // Add newline between paragraphs
            if (child.type === 'paragraph' && index < node.children.length - 1) {
                return text + '\n\n';
            }
            return text;
        }).join('');
    }

    return '';
}

/**
 * Extract plain text from Lexical JSON
 */
function getPlainTextFromJSON(jsonContent: string): string {
    try {
        const parsed = JSON.parse(jsonContent);
        return extractTextFromLexicalNode(parsed.root);
    } catch {
        return '';
    }
}

/**
 * Calculate plain text length from content (Lexical JSON or plain text)
 * This matches what textContent returns from DOM elements
 */
function getPlainTextLength(content: string): number {
    if (!content) return 0;
    return getPlainText(content).length;
}

/**
 * Get plain text from content (handles both Lexical JSON and plain text)
 */
function getPlainText(content: string): string {
    if (!content) return '';

    // Check if it's Lexical JSON
    if (isLexicalJSON(content)) {
        return getPlainTextFromJSON(content);
    }

    // Otherwise treat as plain text (or legacy markdown)
    return content
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
 * Build generation settings object with consistent defaults
 * This ensures generate and regenerate use the EXACT SAME settings
 */
function buildGenerationSettings(settings: any) {
    const aiModel = settings.aiModel || 'gemini-2.0-flash';
    const isThinkingModel = THINKING_MODELS.includes(aiModel);

    return {
        currentPreset: settings.currentPreset || "story-telling",
        authorProfile: settings.authorProfile || '',
        aiModel: aiModel,
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
        // Only include thinkingBudget for thinking models
        ...(isThinkingModel && {
            thinkingBudget: settings.thinkingBudget || 4096,
        }),
    };
}

export function useProjectEditor({
    workspaceId,
    projectId,
    project,
    initialChapters,
    editorRef,
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
    
    // Color coding toggle (default: enabled)
    // Color coding now uses OriginTextNode metadata instead of position-based aiRanges
    const [isColorCoded, setIsColorCoded] = useState<boolean>(true);
    
    // Refs to access current values inside callbacks (avoid stale closure)
    const selectedChapterRef = useRef<ProjectChapter | null>(null);

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
            console.log('Stream completed', {
                isRegenerating,
                generatedTextLength: generatedText.length,
                baseContentRefLength: baseContentRef.current?.length || 0,
                baseContentPreview: baseContentRef.current?.substring(0, 50) || '(empty)'
            });
            setIsGenerating(false);

            // CRITICAL: Use baseContentRef which was frozen BEFORE generation started
            // baseContent might be Lexical JSON, so extract plain text for composition
            const baseContentRaw = baseContentRef.current || '';
            const userPlainText = getPlainText(baseContentRaw);

            // Calculate separator based on plain text
            let separator = '';
            if (userPlainText && !userPlainText.endsWith('\n') && !userPlainText.endsWith(' ') &&
                !generatedText.startsWith('\n') && !generatedText.startsWith(' ')) {
                separator = ' ';
            }

            // Compose final content as plain text (will be converted to JSON by OnChangePlugin)
            const finalContent = userPlainText + separator + generatedText;

            console.log('Final content composed:', {
                userPlainTextLength: userPlainText.length,
                separatorLength: separator.length,
                generatedTextLength: generatedText.length,
                finalContentLength: finalContent.length
            });

            // Save content after generation
            // Origin metadata (user vs ai) is now embedded in OriginTextNode in Lexical JSON
            const currentChapter = selectedChapterRef.current;
            if (currentChapter) {
                saveContent(currentChapter.order, finalContent, 'llm_generation');
            }

            // Update content state (plain text - will be converted to JSON by ContentUpdatePlugin → OnChangePlugin)
            setContent(finalContent);
            originalContent.current = finalContent;

            // Cache the newly generated version for instant switching
            // Note: Navigation info will be updated via websocket, cache with current info
            if (currentChapter?.navigation_info) {
                // Cache with incremented version index (new generation = new version)
                const newVersionIndex = currentChapter.navigation_info.currentVersionIndex + 1;
                versionControl.cacheVersion(newVersionIndex, finalContent);
            }
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
        currentNodeId: selectedChapter?.navigation_info?.currentNodeId, // Pass currentNodeId for cache context
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
                // Check if navigation_info changed (compare JSON to handle object equality)
                const navigationChanged = JSON.stringify(updatedChapter.navigation_info) !==
                                          JSON.stringify(selectedChapter.navigation_info);

                // Chapter still exists - update if content, name, or navigation_info changed
                if (updatedChapter.content !== selectedChapter.content ||
                    updatedChapter.chapter_name !== selectedChapter.chapter_name ||
                    navigationChanged) {
                    console.log('Chapter updated from server:', {
                        contentChanged: updatedChapter.content !== selectedChapter.content,
                        nameChanged: updatedChapter.chapter_name !== selectedChapter.chapter_name,
                        navigationChanged
                    });
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
                lastOrder: lastChapterOrderRef.current,
                currentOrder: selectedChapter.order
            });

            // Update the last chapter order
            lastChapterOrderRef.current = selectedChapter.order;

            // Only reset everything on actual chapter switch
            if (isChapterSwitch) {
                console.log('Initializing content for chapter:', selectedChapter.chapter_name);
                setContent(chapterContent);
                originalContent.current = chapterContent;

                // Cache current version for instant switching
                if (selectedChapter.navigation_info) {
                    versionControl.cacheVersion(
                        selectedChapter.navigation_info.currentVersionIndex,
                        chapterContent,
                        selectedChapter.navigation_info
                    );
                }

                // Reset baseContent when switching chapters
                setBaseContent("");

                // Migrate legacy aiRanges if present (one-time migration to OriginTextNode)
                if (needsMigration(selectedChapter.ai_ranges) && editorRef?.current) {
                    console.log('Migrating legacy aiRanges to OriginTextNode metadata');
                    // Small delay to ensure editor is fully loaded with content
                    setTimeout(() => {
                        if (editorRef?.current) {
                            migrateAiRangesToMetadata(editorRef.current, selectedChapter.ai_ranges!);
                        }
                    }, 100);
                }

                // Save last viewed chapter to localStorage
                const storageKey = `lastChapter_${projectId}`;
                localStorage.setItem(storageKey, selectedChapter.order.toString());

                // Initialize version control if needed
                if (!selectedChapter.navigation_info) {
                    initializeChapterHistory(selectedChapter.order, chapterContent);
                }
            } else {
                // Same chapter, content updated from server
                console.log('Content updated from server for same chapter');
            }
        } else {
            setContent("");
            originalContent.current = "";
            setBaseContent("");
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
            const changedKeys = Object.keys(settings).filter(key => 
                    JSON.stringify(settings[key]) !== JSON.stringify(originalSettings.current[key])
            );
            
            console.log('Settings changed, auto-saving', {
                changedKeys,
                aiModel: settings.aiModel,
            });
            
            // If aiModel changed, save immediately (no debounce) to ensure it's persisted
            if (changedKeys.includes('aiModel')) {
                console.log('AI Model changed, saving immediately:', settings.aiModel);
                saveSettings(settings).catch(console.error);
            } else {
                // Use 1 second debounce for other settings to batch rapid changes
                debouncedSaveSettings(settings, 1000);
            }
        }
    }, [settings, debouncedSaveSettings, saveSettings, isGenerating, isStreaming]);

    // Save settings immediately when component unmounts (e.g., switching tabs)
    useEffect(() => {
        return () => {
            // On unmount, save settings immediately if there are pending changes
            if (isInitialized.current) {
                const settingsChanged = JSON.stringify(settings) !== JSON.stringify(originalSettings.current);
                if (settingsChanged) {
                    console.log('Component unmounting, force-saving settings immediately');
                    // Force immediate save on unmount (bypass debounce)
                    saveSettings(settings).catch(console.error);
                }
            }
        };
    }, [settings, saveSettings]);

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

                        // Cache the received version for instant switching
                        if (data.version_index !== undefined) {
                            versionControl.cacheVersion(
                                data.version_index,
                                data.content || '',
                                data.navigation_info
                            );
                        }

                        // Refresh the page data to get updated navigation info
                        router.reload({ only: ['chapters'] });
                    } else if (data.trigger === 'regenerate_switch_to_parent') {
                        // Switch to parent content during regeneration
                        const parentContent = data.content || '';

                        // Update content state
                        setContent(parentContent);
                        originalContent.current = parentContent;

                        // CRITICAL: Update base content for StreamingPlugin
                        // This ensures the streaming plugin composes: PARENT + NEW_AI_TEXT
                        setBaseContent(parentContent);
                        baseContentRef.current = parentContent;

                        console.log('Switched to parent content for regeneration:', {
                            parentContentLength: parentContent.length
                        });
                    } else if (['llm_generation', 'llm_regeneration'].includes(data.trigger)) {
                        // Generation completed - refresh navigation info
                        console.log('Generation completed, refreshing navigation info');
                        setTimeout(() => {
                            router.reload({ only: ['chapters'] });
                        }, 100);
                    }
                }
            });

            // Listen for operation state changes to update navigation info directly
            // This provides a direct path for navigation updates without relying on router.reload
            channel.listen('.operation.state.changed', (data: any) => {
                console.log('Operation state changed via websocket:', data);

                // Only process unlocked state with navigation info for current chapter
                if (data.locked === false &&
                    data.navigationInfo &&
                    selectedChapter &&
                    data.chapter_order === selectedChapter.order) {

                    console.log('Updating navigation info directly from websocket:', data.navigationInfo);

                    // Update selectedChapter with new navigation_info directly
                    setSelectedChapter(prev => prev ? {
                        ...prev,
                        navigation_info: data.navigationInfo
                    } : null);
                }
            });

        } catch (error) {
            console.error('Error setting up content update listener:', error);
        }

        return () => {
            if (channel) {
                try {
                    channel.stopListening('.project.content.updated');
                    channel.stopListening('.operation.state.changed');
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

        console.log('handleGenerateText - frozen state:', {
            baseContentRefLength: baseContentRef.current.length,
            baseContentPreview: baseContentRef.current.substring(0, 50)
        });

        setContent(currentContent);

        console.log("Starting text generation with content:", {
            contentLength: currentContent.length,
            contentPreview: currentContent.substring(0, 50) + '...'
        });
        
        // NOW trigger generation - baseContent is already set
        setIsGenerating(true);

        const generationSettings = {
            prompt: currentContent || "",
            order: selectedChapter.order,
            chapter_name: selectedChapter.chapter_name || 'Untitled',
            settings: buildGenerationSettings(settings),
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
            chapter_name: selectedChapter.chapter_name || 'Untitled',
            settings: buildGenerationSettings(settings),
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
                trigger
            });

            // Update the original content reference immediately to prevent duplicate saves
            originalContent.current = normalizedContent;

            if (trigger === 'auto') {
                debouncedSaveContent(order, normalizedContent, trigger, 1000);
            } else {
                saveContent(order, normalizedContent, trigger);
            }
        } else {
            console.log('No content change detected, skipping save');
        }
    }, [selectedChapter, saveContent, debouncedSaveContent]);

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
        // Color coding now uses OriginTextNode metadata instead of aiRanges
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
        saveContent: (order: number, content: string | null, trigger: string) => saveContent(order, content ?? '', trigger),
        smartSave,
    };
}

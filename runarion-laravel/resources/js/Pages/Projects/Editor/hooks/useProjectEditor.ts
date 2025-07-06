import { useState, useEffect, useRef, useCallback } from 'react';
import { router } from '@inertiajs/react';
import { Project, ProjectChapter } from '@/types';
import { useEventDrivenSave } from './useEventDrivenSave';
import { useStreamingLLM } from './useStreamingLLM';

interface UseProjectEditorProps {
    workspaceId: string;
    projectId: string;
    project: Project;
    initialChapters: ProjectChapter[];
}

export function useProjectEditor({
    workspaceId,
    projectId,
    project,
    initialChapters,
}: UseProjectEditorProps) {
    // Core state
    const [isSaving, setIsSaving] = useState(false);
    const [isGenerating, setIsGenerating] = useState(false);
    const [content, setContent] = useState("");
    const [settings, setSettings] = useState(project.settings || {});
    const [localChapters, setLocalChapters] = useState<ProjectChapter[]>(initialChapters);
    const [selectedChapter, setSelectedChapter] = useState<ProjectChapter | null>(null);
    const [preservedChapterOrder, setPreservedChapterOrder] = useState<number | null>(null);
    
    const isInitialized = useRef(false);
    const lastSavedContent = useRef<string>('');
    const lastSavedSettings = useRef<any>({});
    const saveTimeout = useRef<NodeJS.Timeout | null>(null);
    const originalChapterContent = useRef<string>(''); // Track content at chapter load

    // Event-driven save hook
    const { saveContent, saveSettings, forceSave } = useEventDrivenSave({
        workspaceId,
        projectId,
        onContentSaved: (updatedChapters) => {
            setLocalChapters(updatedChapters);
            
            // Update selected chapter with latest content
            if (selectedChapter) {
                const updatedSelectedChapter = updatedChapters.find(ch => ch.order === selectedChapter.order);
                if (updatedSelectedChapter) {
                    setSelectedChapter(updatedSelectedChapter);
                }
            }
        },
        onSettingsSaved: () => {
            // Settings saved callback if needed
        },
        onSaveStart: () => setIsSaving(true),
        onSaveEnd: () => setIsSaving(false),
    });

    // Streaming LLM hook
    const {
        isStreaming,
        streamingText,
        error: streamError,
        cancelStream,
    } = useStreamingLLM({
        workspaceId,
        projectId,
        chapterOrder: selectedChapter?.order ?? 0,
        onStreamComplete: (fullText) => {
            console.log('Stream completed, updating content');
            setIsGenerating(false);
            
            // The content will be updated via the ProjectContentUpdated event
            // which is broadcasted from the StreamLLMJob
        },
        onStreamError: (error) => {
            console.error('Stream error:', error);
            setIsGenerating(false);
        },
    });

    // Update local chapters when prop changes, but preserve selected chapter
    useEffect(() => {
        setLocalChapters(initialChapters);
        
        // If we have a preserved chapter order (from generation), restore it
        if (preservedChapterOrder !== null) {
            const chapterToRestore = initialChapters.find(ch => ch.order === preservedChapterOrder);
            if (chapterToRestore) {
                setSelectedChapter(chapterToRestore);
                setPreservedChapterOrder(null);
                console.log("Restored chapter after generation:", chapterToRestore.chapter_name);
                return;
            }
        }
        
        // Update selectedChapter if it exists in the new chapters
        if (selectedChapter) {
            const updatedChapter = initialChapters.find(ch => ch.order === selectedChapter.order);
            if (updatedChapter) {
                setSelectedChapter(updatedChapter);
            }
        }
    }, [initialChapters, preservedChapterOrder, selectedChapter]);

    // Initialize component
    useEffect(() => {
        if (selectedChapter) {
            const chapterContent = selectedChapter.content || "";
            setContent(chapterContent);
            lastSavedContent.current = chapterContent;
            originalChapterContent.current = chapterContent; // Store original content
        } else {
            setContent("");
            lastSavedContent.current = "";
            originalChapterContent.current = "";
        }
        
        // Initialize settings
        const initialSettings = project.settings || {};
        setSettings(initialSettings);
        lastSavedSettings.current = initialSettings;
        
        // Mark as initialized after a brief delay
        const timer = setTimeout(() => {
            isInitialized.current = true;
            console.log("Project editor initialized");
        }, 500);

        return () => clearTimeout(timer);
    }, [selectedChapter, project.settings]);

    // Settings auto-save effect (keep only settings auto-save, content save moved to Main.tsx)
    useEffect(() => {
        if (!isInitialized.current || isGenerating || isStreaming) {
            return;
        }

        // Clear existing timeout
        if (saveTimeout.current) {
            clearTimeout(saveTimeout.current);
        }

        // Check if settings changed (removed content auto-save to prevent conflicts)
        const settingsChanged = JSON.stringify(settings) !== JSON.stringify(lastSavedSettings.current);

        if (!settingsChanged) {
            return;
        }

        // Set debounced save for settings only
        saveTimeout.current = setTimeout(() => {
            if (settingsChanged) {
                console.log('Auto-saving settings changes');
                saveSettings(settings);
                lastSavedSettings.current = { ...settings };
            }
        }, 1000); // 1 second debounce

        return () => {
            if (saveTimeout.current) {
                clearTimeout(saveTimeout.current);
            }
        };
    }, [settings, saveSettings, isGenerating, isStreaming]); // Removed content and selectedChapter dependencies

    // Update content when streaming
    useEffect(() => {
        if (isStreaming && streamingText) {
            // Show streaming text in real-time without saving
            const baseContent = lastSavedContent.current;
            const separator = baseContent && !baseContent.endsWith(' ') && !streamingText.startsWith(' ') ? ' ' : '';
            setContent(baseContent + separator + streamingText);
        }
    }, [isStreaming, streamingText]);

    // Ensure first chapter is selected by default
    useEffect(() => {
        if (localChapters.length > 0 && !selectedChapter && preservedChapterOrder === null) {
            setSelectedChapter(localChapters[0]);
            console.log("Auto-selected first chapter:", localChapters[0].chapter_name);
        }
    }, [localChapters, selectedChapter, preservedChapterOrder]);

    // Chapter management functions
    const handleChapterSelect = useCallback((chapterOrder: number) => {
        if (isGenerating || isStreaming) {
            console.log("Cannot switch chapters during text generation or streaming");
            return;
        }

        const chapter = localChapters.find(c => c.order === chapterOrder);
        if (chapter) {
            // Force save current content before switching
            if (selectedChapter && content !== lastSavedContent.current) {
                forceSave(selectedChapter.order, content, 'manual');
            }
            
            setSelectedChapter(chapter);
            console.log("Chapter switched to:", chapter.chapter_name);
        }
    }, [localChapters, isGenerating, isStreaming, selectedChapter, content, forceSave]);

    const handleAddChapter = useCallback((chapterName: string) => {
        if (isGenerating || isStreaming) {
            console.log("Cannot add chapters during text generation or streaming");
            return Promise.reject(new Error("Cannot add chapters during text generation or streaming"));
        }

        return new Promise<void>((resolve, reject) => {
            // Force save current content before adding chapter
            if (selectedChapter && content !== lastSavedContent.current) {
                forceSave(selectedChapter.order, content, 'manual');
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
    }, [workspaceId, projectId, isGenerating, isStreaming, selectedChapter, content, forceSave]);

    // Settings management
    const handleSettingChange = useCallback((key: string, value: any) => {
        setSettings(prev => ({
            ...prev,
            [key]: value
        }));
    }, []);

    // Text generation function
    const handleGenerateText = useCallback(() => {
        if (!selectedChapter || isGenerating || isStreaming) {
            return;
        }

        // Preserve the current chapter order before generation
        setPreservedChapterOrder(selectedChapter.order);
        setIsGenerating(true);

        // Force save current content before generation
        if (content !== lastSavedContent.current) {
            forceSave(selectedChapter.order, content, 'manual');
        }

        console.log("Starting text generation - preserving chapter:", selectedChapter.chapter_name);

        // Extract relevant settings for the generation request
        const generationSettings = {
            prompt: content || "<please start writing here>",
            order: selectedChapter.order,
            settings: {
                // Model settings
                aiModel: settings.aiModel || 'gpt-4o-mini',
                
                // Story settings
                storyGenre: settings.storyGenre || '',
                storyTone: settings.storyTone || '',
                storyPov: settings.storyPov || '',
                
                // Generation parameters
                temperature: settings.temperature || 1.0,
                repetitionPenalty: settings.repetitionPenalty || 0.0,
                outputLength: settings.outputLength || 300,
                minOutputToken: settings.minOutputToken || 50,
                topP: settings.topP || 0.85,
                tailFree: settings.tailFree || 0.85,
                topA: settings.topA || 0.85,
                topK: settings.topK || 0.85,
                
                // Advanced settings
                phraseBias: settings.phraseBias || [],
                bannedPhrases: settings.bannedPhrases || [],
                stopSequences: settings.stopSequences || [],
            }
        };

        console.log("Sending streaming text generation request");

        router.post(
            route("editor.project.generate", {
                workspace_id: workspaceId,
                project_id: projectId,
            }),
            generationSettings,
            {
                preserveState: true,
                preserveScroll: true,
                onSuccess: (response) => {
                    console.log("Text generation request sent successfully");
                    // The streaming will be handled by the useStreamingLLM hook
                },
                onError: (errors) => {
                    console.error("Failed to start text generation:", errors);
                    setIsGenerating(false);
                    setPreservedChapterOrder(null);
                },
            }
        );
    }, [workspaceId, projectId, selectedChapter, content, isGenerating, isStreaming, settings, forceSave]);

    const handleCancelGeneration = useCallback(() => {
        if (isStreaming) {
            cancelStream();
        }
        setIsGenerating(false);
        setPreservedChapterOrder(null);
        console.log("Text generation cancelled");
    }, [isStreaming, cancelStream]);

    return {
        // State
        isSaving,
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
        
        // Computed values
        selectedChapterOrder: selectedChapter?.order ?? 0,
        
        // Actions
        handleChapterSelect,
        handleAddChapter,
        handleSettingChange,
        handleGenerateText,
        handleCancelGeneration,
        
        // Save functions
        saveContent: (order: number, content: string, trigger: string) => saveContent(order, content, trigger),
        smartSave: (order: number, content: string, trigger: string) => {
            // Normalize both contents to plain text for comparison
            const normalizeContent = (htmlContent: string) => {
                if (!htmlContent) return '';
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = htmlContent;
                return (tempDiv.textContent || tempDiv.innerText || '').trim();
            };

            const currentPlainText = normalizeContent(content);
            const originalPlainText = normalizeContent(originalChapterContent.current);

            // Only save if the plain text content has actually changed
            if (selectedChapter && currentPlainText !== originalPlainText) {
                console.log('Content changed, saving:', { 
                    originalText: originalPlainText?.substring(0, 50) + '...', 
                    currentText: currentPlainText?.substring(0, 50) + '...',
                    originalHTML: originalChapterContent.current?.substring(0, 100),
                    currentHTML: content?.substring(0, 100)
                });
                saveContent(order, content, trigger);
                // Update original content after successful save to prevent duplicate saves
                originalChapterContent.current = content;
            } else {
                console.log('No content change detected, skipping save:', {
                    originalText: originalPlainText,
                    currentText: currentPlainText
                });
            }
        },
    };
}

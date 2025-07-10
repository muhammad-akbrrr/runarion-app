import { useState, useEffect, useRef, useCallback } from 'react';
import { router } from '@inertiajs/react';
import { Project, ProjectChapter } from '@/types';
import { useUnifiedSave } from './useUnifiedSave';
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
        onStreamComplete: (updatedContent) => {
            console.log('Stream completed');
            setIsGenerating(false);
        },
        onStreamError: (error) => {
            console.error('Stream error:', error);
            setIsGenerating(false);
        },
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
        
        // Update selected chapter if it exists in new chapters
        if (selectedChapter) {
            const updatedChapter = initialChapters.find(ch => ch.order === selectedChapter.order);
            if (updatedChapter && updatedChapter.content !== selectedChapter.content) {
                console.log('Chapter content updated from server');
                setSelectedChapter(updatedChapter);
            }
        }
    }, [initialChapters, preservedChapterOrder]);

    // Initialize content when chapter changes
    useEffect(() => {
        if (selectedChapter) {
            const chapterContent = selectedChapter.content || "";
            console.log('Initializing content for chapter:', selectedChapter.chapter_name);
            setContent(chapterContent);
            originalContent.current = chapterContent;
        } else {
            setContent("");
            originalContent.current = "";
        }
    }, [selectedChapter?.order, selectedChapter?.content]);

    // Initialize settings
    useEffect(() => {
        const initialSettings = project.settings || {};
        setSettings(initialSettings);
        originalSettings.current = initialSettings;
        
        // Mark as initialized
        const timer = setTimeout(() => {
            isInitialized.current = true;
            console.log("Project editor initialized");
        }, 100);

        return () => clearTimeout(timer);
    }, [project.settings]);

    // Auto-save settings when they change
    useEffect(() => {
        if (!isInitialized.current || isGenerating || isStreaming) {
            return;
        }

        const settingsChanged = JSON.stringify(settings) !== JSON.stringify(originalSettings.current);
        
        if (settingsChanged) {
            console.log('Settings changed, auto-saving');
            debouncedSaveSettings(settings, 1000);
        }
    }, [settings, debouncedSaveSettings, isGenerating, isStreaming]);

    // Handle streaming text updates
    useEffect(() => {
        if (isStreaming && streamingText) {
            const baseContent = originalContent.current;
            let separator = '';
            
            if (baseContent && !baseContent.endsWith('\n') && !baseContent.endsWith(' ') && 
                !streamingText.startsWith('\n') && !streamingText.startsWith(' ')) {
                separator = ' ';
            }
            
            setContent(baseContent + separator + streamingText);
        }
    }, [isStreaming, streamingText]);

    // Auto-select first chapter
    useEffect(() => {
        if (localChapters.length > 0 && !selectedChapter && preservedChapterOrder === null) {
            setSelectedChapter(localChapters[0]);
            console.log("Auto-selected first chapter:", localChapters[0].chapter_name);
        }
    }, [localChapters, selectedChapter, preservedChapterOrder]);

    // Chapter management functions
    const handleChapterSelect = useCallback((chapterOrder: number) => {
        if (isGenerating || isStreaming) {
            console.log("Cannot switch chapters during generation");
            return;
        }

        const chapter = localChapters.find(c => c.order === chapterOrder);
        if (chapter) {
            // Save current content before switching if changed
            if (selectedChapter && content !== originalContent.current) {
                console.log('Saving content before chapter switch');
                forceSave({
                    content: {
                        order: selectedChapter.order,
                        content: content ?? '', // Treat null as empty string
                        trigger: 'manual'
                    }
                });
            }
            
            setSelectedChapter(chapter);
            console.log("Chapter switched to:", chapter.chapter_name);
        }
    }, [localChapters, isGenerating, isStreaming, selectedChapter, content, forceSave]);

    const handleAddChapter = useCallback((chapterName: string) => {
        if (isGenerating || isStreaming) {
            return Promise.reject(new Error("Cannot add chapters during generation"));
        }

        return new Promise<void>((resolve, reject) => {
            // Save current content before adding chapter
            if (selectedChapter && content !== originalContent.current) {
                forceSave({
                    content: {
                        order: selectedChapter.order,
                        content: content ?? '', // Treat null as empty string
                        trigger: 'manual'
                    }
                });
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

    // Text generation
    const handleGenerateText = useCallback(() => {
        if (!selectedChapter || isGenerating || isStreaming) {
            return;
        }

        setPreservedChapterOrder(selectedChapter.order);
        setIsGenerating(true);

        // Save current content before generation
        if (content !== originalContent.current) {
            forceSave({
                content: {
                    order: selectedChapter.order,
                    content: content ?? '', // Treat null as empty string
                    trigger: 'manual'
                }
            });
        }

        console.log("Starting text generation");

        const generationSettings = {
            prompt: content || "",
            order: selectedChapter.order,
            settings: {
                currentPreset: settings.currentPreset || "creative-writing",
                aiModel: settings.aiModel || 'gpt-4o-mini',
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
            
            if (trigger === 'auto') {
                debouncedSaveContent(order, normalizedContent, trigger);
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
        
        // Computed values
        selectedChapterOrder: selectedChapter?.order ?? 0,
        
        // Actions
        handleChapterSelect,
        handleAddChapter,
        handleSettingChange,
        handleGenerateText,
        handleCancelGeneration,
        
        // Save functions
        saveContent: (order: number, content: string | null, trigger: string) => saveContent(order, content ?? '', trigger),
        smartSave,
    };
}

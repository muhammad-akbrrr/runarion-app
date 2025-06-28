import { useState, useEffect, useRef, useCallback } from 'react';
import { router } from '@inertiajs/react';
import { Project, ProjectChapter } from '@/types';
import { useAutoSave } from './useAutoSave';

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

    // Auto-save hook
    const { debouncedSave, cancelSave, forceSave, initializeLastSavedContent } = useAutoSave({
        workspaceId,
        projectId,
        isInitialized: isInitialized.current,
        isGenerating,
        onContentSaved: (updatedChapters) => {
            setLocalChapters(updatedChapters);
            
            // Update selected chapter with latest content, preserving the current selection
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

    // Update local chapters when prop changes, but preserve selected chapter
    useEffect(() => {
        setLocalChapters(initialChapters);
        
        // If we have a preserved chapter order (from generation), restore it
        if (preservedChapterOrder !== null) {
            const chapterToRestore = initialChapters.find(ch => ch.order === preservedChapterOrder);
            if (chapterToRestore) {
                setSelectedChapter(chapterToRestore);
                setPreservedChapterOrder(null); // Clear the preserved order
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
            // Initialize the autosave with current content to prevent unnecessary saves
            initializeLastSavedContent(chapterContent);
        } else {
            setContent("");
        }
        
        // Initialize settings
        const initialSettings = project.settings || {};
        setSettings(initialSettings);
        
        // Mark as initialized after a brief delay to prevent race conditions
        const timer = setTimeout(() => {
            isInitialized.current = true;
            console.log("Project editor initialized");
        }, 500); // Increased delay to ensure proper initialization

        return () => clearTimeout(timer);
    }, [selectedChapter, project.settings, initializeLastSavedContent]);

    // Auto-save effect - only trigger when not generating
    useEffect(() => {
        if (!isInitialized.current || isGenerating) {
            return;
        }

        const saveData: any = {};
        
        // Add content data if we have a selected chapter
        if (selectedChapter) {
            saveData.content = {
                order: selectedChapter.order,
                content: content,
            };
        }
        
        // Add settings data
        saveData.settings = settings;

        debouncedSave(saveData);

        return () => cancelSave();
    }, [content, settings, selectedChapter, debouncedSave, cancelSave, isGenerating]);

    // Ensure first chapter is selected by default only if no chapter is selected and no preserved order
    useEffect(() => {
        if (localChapters.length > 0 && !selectedChapter && preservedChapterOrder === null) {
            setSelectedChapter(localChapters[0]);
            console.log("Auto-selected first chapter:", localChapters[0].chapter_name);
        }
    }, [localChapters, selectedChapter, preservedChapterOrder]);

    // Chapter management functions
    const handleChapterSelect = useCallback((chapterOrder: number) => {
        // Prevent chapter switching during generation
        if (isGenerating) {
            console.log("Cannot switch chapters during text generation");
            return;
        }

        const chapter = localChapters.find(c => c.order === chapterOrder);
        if (chapter) {
            // Cancel any pending autosave before switching
            cancelSave();
            setSelectedChapter(chapter);
            console.log("Chapter switched to:", chapter.chapter_name);
        }
    }, [localChapters, isGenerating, cancelSave]);

    const handleAddChapter = useCallback((chapterName: string) => {
        // Prevent adding chapters during generation
        if (isGenerating) {
            console.log("Cannot add chapters during text generation");
            return Promise.reject(new Error("Cannot add chapters during text generation"));
        }

        return new Promise<void>((resolve, reject) => {
            // Cancel any pending autosave before adding chapter
            cancelSave();
            
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
    }, [workspaceId, projectId, isGenerating, cancelSave]);

    // Settings management
    const handleSettingChange = useCallback((key: string, value: any) => {
        setSettings(prev => ({
            ...prev,
            [key]: value
        }));
    }, []);

    // Text generation function
    const handleGenerateText = useCallback(() => {
        if (!selectedChapter || isGenerating) {
            return;
        }

        // Preserve the current chapter order before generation
        setPreservedChapterOrder(selectedChapter.order);
        
        // Cancel any pending autosave before generation
        cancelSave();
        console.log("Starting text generation - autosave cancelled, preserving chapter:", selectedChapter.chapter_name);

        setIsGenerating(true);

        router.post(
            route("editor.project.generate", {
                workspace_id: workspaceId,
                project_id: projectId,
            }),
            {
                prompt: content || "Continue the story",
                order: selectedChapter.order,
            },
            {
                preserveState: false,
                preserveScroll: true,
                onSuccess: (page) => {
                    // The controller redirects back to the editor with updated content
                    const updatedChapters = page.props.chapters as ProjectChapter[];
                    if (updatedChapters) {
                        setLocalChapters(updatedChapters);
                        // Don't set selected chapter here - let the useEffect handle restoration
                        console.log("Text generation completed successfully, chapters updated");
                    }
                },
                onError: (errors) => {
                    console.error("Failed to generate text:", errors);
                    // Clear preserved order on error
                    setPreservedChapterOrder(null);
                },
                onFinish: () => {
                    setIsGenerating(false);
                    console.log("Text generation finished - autosave will resume");
                },
            }
        );
    }, [workspaceId, projectId, selectedChapter, content, isGenerating, cancelSave]);

    return {
        // State
        isSaving,
        isGenerating,
        content,
        setContent,
        settings,
        localChapters,
        selectedChapter,
        
        // Computed values
        selectedChapterOrder: selectedChapter?.order ?? 0,
        
        // Actions
        handleChapterSelect,
        handleAddChapter,
        handleSettingChange,
        handleGenerateText,
    };
}

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
    const [content, setContent] = useState("");
    const [settings, setSettings] = useState(project.settings || {});
    const [localChapters, setLocalChapters] = useState<ProjectChapter[]>(initialChapters);
    const [selectedChapter, setSelectedChapter] = useState<ProjectChapter | null>(
        initialChapters.length > 0 ? initialChapters[0] : null
    );
    
    const isInitialized = useRef(false);

    // Auto-save hook
    const { debouncedSave, cancelSave } = useAutoSave({
        workspaceId,
        projectId,
        isInitialized: isInitialized.current,
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

    // Update local chapters when prop changes
    useEffect(() => {
        setLocalChapters(initialChapters);
        
        // Update selectedChapter if it exists in the new chapters
        if (selectedChapter) {
            const updatedChapter = initialChapters.find(ch => ch.order === selectedChapter.order);
            if (updatedChapter) {
                setSelectedChapter(updatedChapter);
            }
        }
    }, [initialChapters]);

    // Initialize component
    useEffect(() => {
        if (selectedChapter) {
            setContent(selectedChapter.content || "");
        } else {
            setContent("");
        }
        
        // Initialize settings
        const initialSettings = project.settings || {};
        setSettings(initialSettings);
        
        // Mark as initialized after a brief delay
        const timer = setTimeout(() => {
            isInitialized.current = true;
            console.log("Project editor initialized");
        }, 100);

        return () => clearTimeout(timer);
    }, [selectedChapter, project.settings]);

    // Auto-save effect
    useEffect(() => {
        if (!isInitialized.current) {
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
    }, [content, settings, selectedChapter, debouncedSave, cancelSave]);

    // Ensure first chapter is selected by default
    useEffect(() => {
        if (localChapters.length > 0 && !selectedChapter) {
            setSelectedChapter(localChapters[0]);
        }
    }, [localChapters, selectedChapter]);

    // Chapter management functions
    const handleChapterSelect = useCallback((chapterOrder: number) => {
        const chapter = localChapters.find(c => c.order === chapterOrder);
        if (chapter) {
            setSelectedChapter(chapter);
        }
    }, [localChapters]);

    const handleAddChapter = useCallback((chapterName: string) => {
        return new Promise<void>((resolve, reject) => {
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
    }, [workspaceId, projectId]);

    // Settings management
    const handleSettingChange = useCallback((key: string, value: any) => {
        setSettings(prev => ({
            ...prev,
            [key]: value
        }));
    }, []);

    return {
        // State
        isSaving,
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
    };
}

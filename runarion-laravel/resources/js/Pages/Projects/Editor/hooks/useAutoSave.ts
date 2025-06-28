import { useRef, useCallback } from 'react';
import { router } from '@inertiajs/react';
import { ProjectChapter } from '@/types';

interface UseAutoSaveProps {
    workspaceId: string;
    projectId: string;
    isInitialized: boolean;
    onContentSaved?: (chapters: ProjectChapter[]) => void;
    onSettingsSaved?: () => void;
    onSaveStart?: () => void;
    onSaveEnd?: () => void;
}

interface SaveData {
    content?: {
        order: number;
        content: string;
    };
    settings?: any;
}

export function useAutoSave({
    workspaceId,
    projectId,
    isInitialized,
    onContentSaved,
    onSettingsSaved,
    onSaveStart,
    onSaveEnd,
}: UseAutoSaveProps) {
    const saveTimeout = useRef<NodeJS.Timeout | null>(null);
    const lastSavedContent = useRef<string>("");
    const lastSavedSettings = useRef<any>({});

    const saveData = useCallback(async (data: SaveData) => {
        if (!isInitialized) {
            console.log("Skipping save: not initialized yet");
            return;
        }

        const { content: contentData, settings } = data;
        
        // Allow empty content - compare with null/undefined check instead of truthy check
        const contentChanged = contentData !== undefined && contentData.content !== lastSavedContent.current;
        const settingsChanged = settings && JSON.stringify(settings) !== JSON.stringify(lastSavedSettings.current);

        if (!contentChanged && !settingsChanged) {
            console.log("No changes to save");
            return;
        }

        console.log("Starting save", { 
            contentChanged, 
            settingsChanged, 
            contentLength: contentData?.content?.length || 0 
        });
        onSaveStart?.();

        const savePromises = [];

        // Save content if changed (including empty content)
        if (contentChanged && contentData !== undefined) {
            console.log("Saving content changes", { 
                isEmpty: contentData.content === "", 
                length: contentData.content.length 
            });
            
            const contentPromise = new Promise((resolve, reject) => {
                router.patch(
                    route("editor.project.updateData", {
                        workspace_id: workspaceId,
                        project_id: projectId,
                    }),
                    {
                        order: contentData.order,
                        content: contentData.content, // Allow empty string
                    },
                    {
                        preserveState: true,
                        preserveScroll: true,
                        onSuccess: (page) => {
                            lastSavedContent.current = contentData.content;
                            console.log("Content saved successfully", { 
                                isEmpty: contentData.content === "",
                                length: contentData.content.length 
                            });
                            
                            const updatedChapters = page.props.chapters as ProjectChapter[];
                            if (updatedChapters) {
                                onContentSaved?.(updatedChapters);
                            }
                            
                            resolve(true);
                        },
                        onError: (errors) => {
                            console.error("Failed to save content:", errors);
                            reject(errors);
                        },
                    }
                );
            });
            savePromises.push(contentPromise);
        }

        // Save settings if changed
        if (settingsChanged && settings) {
            console.log("Saving settings changes");
            const settingsPromise = new Promise((resolve, reject) => {
                router.patch(
                    route("editor.project.updateSettings", {
                        workspace_id: workspaceId,
                        project_id: projectId,
                    }),
                    settings,
                    {
                        preserveState: true,
                        preserveScroll: true,
                        onSuccess: () => {
                            lastSavedSettings.current = { ...settings };
                            console.log("Settings saved successfully");
                            onSettingsSaved?.();
                            resolve(true);
                        },
                        onError: (errors) => {
                            console.error("Failed to save settings:", errors);
                            reject(errors);
                        },
                    }
                );
            });
            savePromises.push(settingsPromise);
        }

        // Handle all save operations
        if (savePromises.length > 0) {
            try {
                const results = await Promise.allSettled(savePromises);
                const failures = results.filter(result => result.status === 'rejected');
                
                if (failures.length > 0) {
                    console.error("Some saves failed:", failures);
                } else {
                    console.log("All saves completed successfully");
                }
            } catch (error) {
                console.error("Save operation failed:", error);
            } finally {
                onSaveEnd?.();
            }
        } else {
            onSaveEnd?.();
        }
    }, [workspaceId, projectId, isInitialized, onContentSaved, onSettingsSaved, onSaveStart, onSaveEnd]);

    const debouncedSave = useCallback((data: SaveData, delay: number = 1000) => {
        // Clear existing timeout
        if (saveTimeout.current) {
            clearTimeout(saveTimeout.current);
        }

        // Set new timeout
        saveTimeout.current = setTimeout(() => {
            saveData(data);
        }, delay);
    }, [saveData]);

    const cancelSave = useCallback(() => {
        if (saveTimeout.current) {
            clearTimeout(saveTimeout.current);
            saveTimeout.current = null;
        }
    }, []);

    return {
        saveData,
        debouncedSave,
        cancelSave,
        lastSavedContent: lastSavedContent.current,
        lastSavedSettings: lastSavedSettings.current,
    };
}

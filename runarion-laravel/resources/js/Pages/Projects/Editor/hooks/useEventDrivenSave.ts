import { useRef, useCallback } from 'react';
import { router } from '@inertiajs/react';
import { ProjectChapter } from '@/types';

interface UseEventDrivenSaveProps {
    workspaceId: string;
    projectId: string;
    onContentSaved?: (chapters: ProjectChapter[]) => void;
    onSettingsSaved?: () => void;
    onSaveStart?: () => void;
    onSaveEnd?: () => void;
}

interface SaveData {
    content?: {
        order: number;
        content: string;
        trigger?: string;
    };
    settings?: any;
}

export function useEventDrivenSave({
    workspaceId,
    projectId,
    onContentSaved,
    onSettingsSaved,
    onSaveStart,
    onSaveEnd,
}: UseEventDrivenSaveProps) {
    const isSaving = useRef<boolean>(false);
    const saveQueue = useRef<SaveData[]>([]);
    const isProcessingQueue = useRef<boolean>(false);

    const processQueue = useCallback(async () => {
        if (isProcessingQueue.current || saveQueue.current.length === 0) {
            return;
        }

        isProcessingQueue.current = true;
        onSaveStart?.();

        try {
            while (saveQueue.current.length > 0) {
                const saveData = saveQueue.current.shift();
                if (!saveData) continue;

                const { content: contentData, settings } = saveData;
                const savePromises = [];

                // Save content if provided
                if (contentData) {
                    console.log('Saving content changes', {
                        order: contentData.order,
                        length: contentData.content.length,
                        trigger: contentData.trigger || 'manual',
                    });

                    const contentPromise = new Promise((resolve, reject) => {
                        router.patch(
                            route("editor.project.updateData", {
                                workspace_id: workspaceId,
                                project_id: projectId,
                            }),
                            {
                                order: contentData.order,
                                content: contentData.content,
                                trigger: contentData.trigger || 'manual',
                            },
                            {
                                preserveState: true,
                                preserveScroll: true,
                                onSuccess: (page) => {
                                    console.log('Content saved successfully');
                                    const updatedChapters = page.props.chapters as ProjectChapter[];
                                    if (updatedChapters) {
                                        onContentSaved?.(updatedChapters);
                                    }
                                    resolve(true);
                                },
                                onError: (errors) => {
                                    console.error('Failed to save content:', errors);
                                    reject(errors);
                                },
                            }
                        );
                    });
                    savePromises.push(contentPromise);
                }

                // Save settings if provided
                if (settings) {
                    console.log('Saving settings changes');
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
                                    console.log('Settings saved successfully');
                                    onSettingsSaved?.();
                                    resolve(true);
                                },
                                onError: (errors) => {
                                    console.error('Failed to save settings:', errors);
                                    reject(errors);
                                },
                            }
                        );
                    });
                    savePromises.push(settingsPromise);
                }

                // Wait for all saves to complete
                if (savePromises.length > 0) {
                    try {
                        const results = await Promise.allSettled(savePromises);
                        const failures = results.filter(result => result.status === 'rejected');
                        
                        if (failures.length > 0) {
                            console.error('Some saves failed:', failures);
                        }
                    } catch (error) {
                        console.error('Save operation failed:', error);
                    }
                }
            }
        } finally {
            isProcessingQueue.current = false;
            onSaveEnd?.();
        }
    }, [workspaceId, projectId, onContentSaved, onSettingsSaved, onSaveStart, onSaveEnd]);

    const queueSave = useCallback((data: SaveData) => {
        // Add to queue
        saveQueue.current.push(data);
        
        // Process queue
        processQueue();
    }, [processQueue]);

    const immediateSave = useCallback(async (data: SaveData) => {
        // Clear queue and save immediately
        saveQueue.current = [];
        saveQueue.current.push(data);
        await processQueue();
    }, [processQueue]);

    const saveContent = useCallback((order: number, content: string, trigger: string = 'manual') => {
        queueSave({
            content: {
                order,
                content,
                trigger,
            },
        });
    }, [queueSave]);

    const saveSettings = useCallback((settings: any) => {
        queueSave({
            settings,
        });
    }, [queueSave]);

    const saveBoth = useCallback((order: number, content: string, settings: any, trigger: string = 'manual') => {
        queueSave({
            content: {
                order,
                content,
                trigger,
            },
            settings,
        });
    }, [queueSave]);

    const forceSave = useCallback(async (order: number, content: string, trigger: string = 'manual') => {
        await immediateSave({
            content: {
                order,
                content,
                trigger,
            },
        });
    }, [immediateSave]);

    return {
        saveContent,
        saveSettings,
        saveBoth,
        forceSave,
        isSaving: isProcessingQueue.current,
        queueLength: saveQueue.current.length,
    };
}

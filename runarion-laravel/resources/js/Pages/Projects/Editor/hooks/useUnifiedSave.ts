import { useRef, useCallback, useEffect } from 'react';
import { router } from '@inertiajs/react';
import { ProjectChapter } from '@/types';

interface SaveOperation {
    id: string;
    timestamp: number;
    data: {
        content?: {
            order: number;
            content: string | null;
            trigger?: string;
        };
        settings?: any;
    };
    resolve: (result: any) => void;
    reject: (error: any) => void;
}

interface UseUnifiedSaveProps {
    workspaceId: string;
    projectId: string;
    onContentSaved?: (chapters: ProjectChapter[]) => void;
    onSettingsSaved?: () => void;
    onSaveError?: (error: any) => void;
}

export function useUnifiedSave({
    workspaceId,
    projectId,
    onContentSaved,
    onSettingsSaved,
    onSaveError,
}: UseUnifiedSaveProps) {
    const saveQueue = useRef<SaveOperation[]>([]);
    const isProcessing = useRef<boolean>(false);
    const debounceTimeout = useRef<NodeJS.Timeout | null>(null);
    const lastSaveData = useRef<{
        content?: { order: number; content: string };
        settings?: any;
    }>({});

    // Generate unique operation ID
    const generateOperationId = useCallback(() => {
        return `save_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }, []);

    // Process the save queue
    const processQueue = useCallback(async () => {
        if (isProcessing.current || saveQueue.current.length === 0) {
            return;
        }

        isProcessing.current = true;

        try {
            // Get the most recent operation for each type (content/settings)
            const operations = saveQueue.current;
            saveQueue.current = [];

            // Consolidate operations - take the latest content and settings
            let latestContent: SaveOperation['data']['content'] | undefined;
            let latestSettings: SaveOperation['data']['settings'] | undefined;
            const allResolvers: Array<{ resolve: Function; reject: Function }> = [];

            operations.forEach(op => {
                allResolvers.push({ resolve: op.resolve, reject: op.reject });
                
                if (op.data.content) {
                    latestContent = op.data.content;
                }
                if (op.data.settings) {
                    latestSettings = op.data.settings;
                }
            });

            // Skip if no actual changes
            const contentChanged = latestContent && (
                !lastSaveData.current.content ||
                lastSaveData.current.content.order !== latestContent.order ||
                (lastSaveData.current.content.content ?? '') !== (latestContent.content ?? '') // Compare with null handling
            );

            const settingsChanged = latestSettings && (
                JSON.stringify(lastSaveData.current.settings) !== JSON.stringify(latestSettings)
            );

            if (!contentChanged && !settingsChanged) {
                console.log('No changes detected, skipping save');
                allResolvers.forEach(({ resolve }) => resolve({ skipped: true }));
                return;
            }

            console.log('Processing unified save:', {
                contentChanged: !!contentChanged,
                settingsChanged: !!settingsChanged,
                operationCount: operations.length
            });

            // Prepare unified save data
            const saveData: any = {};
            
            if (latestContent) {
                saveData.content = {
                    order: latestContent.order,
                    content: latestContent.content ?? '',
                    trigger: latestContent.trigger || 'manual'
                };
            }

            if (latestSettings) {
                saveData.settings = latestSettings;
            }

            // Make unified save request
            const savePromise = new Promise((resolve, reject) => {
                console.log('Saving payload:', saveData);
                router.patch(
                    route("editor.project.updateUnified", {
                        workspace_id: workspaceId,
                        project_id: projectId,
                    }),
                    saveData,
                    {
                        preserveState: true,
                        preserveScroll: true,
                        onSuccess: (page) => {
                            console.log('Unified save successful');
                            
                            // Update last saved data
                            if (latestContent) {
                                lastSaveData.current.content = {
                                    order: latestContent.order,
                                    content: latestContent.content ?? ''
                                };
                            }
                            if (latestSettings) {
                                lastSaveData.current.settings = { ...latestSettings };
                            }

                            // Call callbacks
                            if (latestContent && onContentSaved) {
                                const updatedChapters = page.props.chapters as ProjectChapter[];
                                if (updatedChapters) {
                                    onContentSaved(updatedChapters);
                                }
                            }
                            
                            if (latestSettings && onSettingsSaved) {
                                onSettingsSaved();
                            }

                            resolve(page);
                        },
                        onError: (errors) => {
                            console.error('Unified save failed:', errors);
                            onSaveError?.(errors);
                            reject(errors);
                        },
                    }
                );
            });

            // Wait for save to complete and resolve all operations
            try {
                const result = await savePromise;
                allResolvers.forEach(({ resolve }) => resolve(result));
            } catch (error) {
                allResolvers.forEach(({ reject }) => reject(error));
            }

        } catch (error) {
            console.error('Error processing save queue:', error);
            // Reject any remaining operations
            saveQueue.current.forEach(op => op.reject(error));
            saveQueue.current = [];
        } finally {
            isProcessing.current = false;
            
            // Process any new operations that were added during processing
            if (saveQueue.current.length > 0) {
                setTimeout(processQueue, 0);
            }
        }
    }, [workspaceId, projectId, onContentSaved, onSettingsSaved, onSaveError]);

    // Add operation to queue
    const queueSave = useCallback((data: SaveOperation['data']): Promise<any> => {
        return new Promise((resolve, reject) => {
            const operation: SaveOperation = {
                id: generateOperationId(),
                timestamp: Date.now(),
                data,
                resolve,
                reject,
            };

            saveQueue.current.push(operation);
            
            // Process queue immediately for immediate saves
            setTimeout(processQueue, 0);
        });
    }, [generateOperationId, processQueue]);

    // Debounced save for auto-save scenarios
    const debouncedSave = useCallback((data: SaveOperation['data'], delay: number = 1000): Promise<any> => {
        return new Promise((resolve, reject) => {
            // Clear existing timeout
            if (debounceTimeout.current) {
                clearTimeout(debounceTimeout.current);
            }

            // Set new timeout
            debounceTimeout.current = setTimeout(async () => {
                try {
                    const result = await queueSave(data);
                    resolve(result);
                } catch (error) {
                    reject(error);
                }
            }, delay);
        });
    }, [queueSave]);

    // Save content only
    const saveContent = useCallback(async (order: number, content: string | null, trigger: string = 'manual'): Promise<any> => {
        return queueSave({
            content: { order, content: content ?? '', trigger }
        });
    }, [queueSave]);

    // Save settings only
    const saveSettings = useCallback(async (settings: any): Promise<any> => {
        return queueSave({
            settings
        });
    }, [queueSave]);

    // Save both content and settings
    const saveBoth = useCallback(async (order: number, content: string | null, settings: any, trigger: string = 'manual'): Promise<any> => {
        return queueSave({
            content: { order, content: content ?? '', trigger },
            settings
        });
    }, [queueSave]);

    // Debounced content save
    const debouncedSaveContent = useCallback(async (order: number, content: string | null, trigger: string = 'auto', delay: number = 1000): Promise<any> => {
        return debouncedSave({
            content: { order, content: content ?? '', trigger }
        }, delay);
    }, [debouncedSave]);

    // Debounced settings save
    const debouncedSaveSettings = useCallback(async (settings: any, delay: number = 1000): Promise<any> => {
        return debouncedSave({
            settings
        }, delay);
    }, [debouncedSave]);

    // Force immediate save (cancels any pending debounced saves)
    const forceSave = useCallback(async (data: SaveOperation['data']): Promise<any> => {
        // Cancel any pending debounced saves
        if (debounceTimeout.current) {
            clearTimeout(debounceTimeout.current);
            debounceTimeout.current = null;
        }
        
        return queueSave(data);
    }, [queueSave]);

    // Cancel all pending saves
    const cancelPendingSaves = useCallback(() => {
        if (debounceTimeout.current) {
            clearTimeout(debounceTimeout.current);
            debounceTimeout.current = null;
        }
        
        // Reject all queued operations
        const operations = saveQueue.current;
        saveQueue.current = [];
        operations.forEach(op => op.reject(new Error('Save cancelled')));
        
        console.log('All pending saves cancelled');
    }, []);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            cancelPendingSaves();
        };
    }, [cancelPendingSaves]);

    return {
        // Basic save operations
        saveContent,
        saveSettings,
        saveBoth,
        
        // Debounced save operations
        debouncedSaveContent,
        debouncedSaveSettings,
        
        // Advanced operations
        forceSave,
        cancelPendingSaves,
        
        // State
        isProcessing: isProcessing.current,
        queueLength: saveQueue.current.length,
    };
}

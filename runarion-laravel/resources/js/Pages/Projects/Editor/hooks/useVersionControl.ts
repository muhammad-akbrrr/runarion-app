import { useState, useEffect, useCallback, useRef } from 'react';
import { router } from '@inertiajs/react';

interface GenerationStep {
    id: string;
    parentId: string | null;
    parentVersionIndex?: number | null;
    content: string;
    timestamp: number;
    settings: any;
    isUserGenerated: boolean;
    versions: Array<{
        index: number;
        content: string;
        timestamp: number;
    }>;
}

interface GenerationHistory {
    steps: GenerationStep[];
    currentStepId: string | null;
    lastSelectedVersions: Record<string, number>;
}

interface VersionControlState {
    currentStep: GenerationStep | null;
    availableVersions: Array<{
        index: number;
        content: string;
        timestamp: number;
    }>;
    currentVersionIndex: number;
    canUndo: boolean;
    canRedo: boolean;
    totalVersions: number;
}

interface UseVersionControlProps {
    workspaceId: string;
    projectId: string;
    chapterOrder: number;
    generationHistory: GenerationHistory | null;
    onHistoryUpdate?: (history: GenerationHistory) => void;
    onContentUpdate?: (content: string) => void;
}

export function useVersionControl({
    workspaceId,
    projectId,
    chapterOrder,
    generationHistory,
    onHistoryUpdate,
    onContentUpdate,
}: UseVersionControlProps) {
    const [state, setState] = useState<VersionControlState>({
        currentStep: null,
        availableVersions: [],
        currentVersionIndex: 0,
        canUndo: false,
        canRedo: false,
        totalVersions: 0,
    });

    const [isLoading, setIsLoading] = useState(false);
    const lastHistoryRef = useRef<GenerationHistory | null>(null);

    // Helper function to check if step has child steps
    const hasChildSteps = useCallback((steps: GenerationStep[], stepId: string): boolean => {
        return steps.some(step => step.parentId === stepId);
    }, []);

    // Helper function to check if step has valid child steps for current version
    const hasValidChildStepsForCurrentVersion = useCallback((steps: GenerationStep[], stepId: string, currentVersionIndex: number): boolean => {
        const childSteps = steps.filter(step => step.parentId === stepId);
        
        const validChildSteps = childSteps.filter(step => {
            const childParentVersionIndex = step.parentVersionIndex;
            const isValid = childParentVersionIndex === null || childParentVersionIndex === undefined || childParentVersionIndex === currentVersionIndex;
            
            console.log('Child step validation:', {
                stepId: step.id,
                parentId: step.parentId,
                childParentVersionIndex,
                currentVersionIndex,
                isValid
            });
            
            return isValid;
        });
        
        console.log('Valid child steps check:', {
            parentStepId: stepId,
            currentVersionIndex,
            totalChildSteps: childSteps.length,
            validChildSteps: validChildSteps.length,
            hasValidChildren: validChildSteps.length > 0
        });
        
        return validChildSteps.length > 0;
    }, []);

    // Update state when generation history changes
    useEffect(() => {
        if (!generationHistory) {
            setState({
                currentStep: null,
                availableVersions: [],
                currentVersionIndex: 0,
                canUndo: false,
                canRedo: false,
                totalVersions: 0,
            });
            return;
        }

        // Only update if history actually changed
        if (JSON.stringify(generationHistory) === JSON.stringify(lastHistoryRef.current)) {
            return;
        }

        lastHistoryRef.current = generationHistory;

        const { currentStepId, steps, lastSelectedVersions } = generationHistory;
        
        if (!currentStepId) {
            setState(prev => ({
                ...prev,
                currentStep: null,
                availableVersions: [],
                currentVersionIndex: 0,
                canUndo: false,
                canRedo: false,
                totalVersions: 0,
            }));
            return;
        }

        const currentStep = steps.find(step => step.id === currentStepId);
        if (!currentStep) {
            return;
        }

        const currentVersionIndex = lastSelectedVersions[currentStepId] ?? 0;
        const availableVersions = currentStep.versions || [];
        const canUndo = currentStep.parentId !== null;
        
        const canRedo = hasValidChildStepsForCurrentVersion(steps, currentStepId, currentVersionIndex);

        setState({
            currentStep,
            availableVersions,
            currentVersionIndex,
            canUndo,
            canRedo,
            totalVersions: availableVersions.length,
        });

        console.log('Version control state updated:', {
            currentStepId,
            currentVersionIndex,
            totalVersions: availableVersions.length,
            canUndo,
            canRedo,
            currentStepParentId: currentStep?.parentId,
            currentStepParentVersionIndex: currentStep?.parentVersionIndex,
            hasValidChildSteps: hasValidChildStepsForCurrentVersion(steps, currentStepId, currentVersionIndex),
        });
    }, [generationHistory, hasValidChildStepsForCurrentVersion]);

    // Switch to a different version within current step
    const switchVersion = useCallback(async (versionIndex: number) => {
        if (!state.currentStep || isLoading) {
            return;
        }

        if (versionIndex < 0 || versionIndex >= state.availableVersions.length) {
            console.warn('Invalid version index:', versionIndex);
            return;
        }

        if (versionIndex === state.currentVersionIndex) {
            console.log('Already on version', versionIndex);
            return;
        }

        setIsLoading(true);

        try {
            console.log('Switching to version:', versionIndex);

            const response = await new Promise<any>((resolve, reject) => {
                router.post(
                    route("editor.project.switch-version", {
                        workspace_id: workspaceId,
                        project_id: projectId,
                    }),
                    {
                        order: chapterOrder,
                        version_index: versionIndex,
                    },
                    {
                        preserveState: true,
                        preserveScroll: true,
                        onSuccess: (page) => {
                            console.log('Version switched successfully - redo capability may have changed');
                            resolve(page);
                        },
                        onError: (errors) => {
                            console.error('Failed to switch version:', errors);
                            reject(errors);
                        },
                    }
                );
            });

            // Update content if callback provided
            if (onContentUpdate && state.availableVersions[versionIndex]) {
                onContentUpdate(state.availableVersions[versionIndex].content);
            }

        } catch (error) {
            console.error('Error switching version:', error);
        } finally {
            setIsLoading(false);
        }
    }, [workspaceId, projectId, chapterOrder, state.currentStep, state.currentVersionIndex, state.availableVersions, isLoading, onContentUpdate]);

    // Undo to parent step
    const undo = useCallback(async () => {
        if (!state.canUndo || isLoading) {
            return;
        }

        setIsLoading(true);

        try {
            console.log('Undoing to parent step');

            await new Promise<void>((resolve, reject) => {
                router.post(
                    route("editor.project.undo-step", {
                        workspace_id: workspaceId,
                        project_id: projectId,
                    }),
                    {
                        order: chapterOrder,
                    },
                    {
                        preserveState: true,
                        preserveScroll: true,
                        onSuccess: () => {
                            console.log('Undo successful');
                            resolve();
                        },
                        onError: (errors) => {
                            console.error('Failed to undo:', errors);
                            reject(errors);
                        },
                    }
                );
            });

        } catch (error) {
            console.error('Error undoing step:', error);
        } finally {
            setIsLoading(false);
        }
    }, [workspaceId, projectId, chapterOrder, state.canUndo, isLoading]);

    // Redo to last selected child step
    const redo = useCallback(async () => {
        if (!state.canRedo || isLoading) {
            console.log('Redo blocked:', { canRedo: state.canRedo, isLoading });
            return;
        }

        if (generationHistory && state.currentStep) {
            const hasValidChildren = hasValidChildStepsForCurrentVersion(
                generationHistory.steps, 
                state.currentStep.id, 
                state.currentVersionIndex
            );
            
            if (!hasValidChildren) {
                console.log('Redo blocked: No valid child steps for current version');
                return;
            }
        }

        setIsLoading(true);

        try {
            console.log('Redoing to child step');

            await new Promise<void>((resolve, reject) => {
                router.post(
                    route("editor.project.redo-step", {
                        workspace_id: workspaceId,
                        project_id: projectId,
                    }),
                    {
                        order: chapterOrder,
                    },
                    {
                        preserveState: true,
                        preserveScroll: true,
                        onSuccess: () => {
                            console.log('Redo successful');
                            resolve();
                        },
                        onError: (errors) => {
                            console.error('Failed to redo:', errors);
                            reject(errors);
                        },
                    }
                );
            });

        } catch (error) {
            console.error('Error redoing step:', error);
        } finally {
            setIsLoading(false);
        }
    }, [workspaceId, projectId, chapterOrder, state.canRedo, state.currentStep, state.currentVersionIndex, isLoading, generationHistory, hasValidChildStepsForCurrentVersion]);

    // Regenerate current step (create new version)
    const regenerate = useCallback(async (settings: any) => {
        if (!state.currentStep || isLoading) {
            return;
        }

        setIsLoading(true);

        try {
            console.log('Regenerating current step');

            await new Promise<void>((resolve, reject) => {
                router.post(
                    route("editor.project.regenerate", {
                        workspace_id: workspaceId,
                        project_id: projectId,
                    }),
                    {
                        order: chapterOrder,
                        settings,
                    },
                    {
                        preserveState: true,
                        preserveScroll: true,
                        onSuccess: () => {
                            console.log('Regeneration started');
                            resolve();
                        },
                        onError: (errors) => {
                            console.error('Failed to start regeneration:', errors);
                            reject(errors);
                        },
                    }
                );
            });

        } catch (error) {
            console.error('Error starting regeneration:', error);
        } finally {
            setIsLoading(false);
        }
    }, [workspaceId, projectId, chapterOrder, state.currentStep, isLoading]);

    // Check if we can regenerate (has generation history)
    const canRegenerate = useCallback(() => {
        return state.currentStep !== null && !isLoading;
    }, [state.currentStep, isLoading]);

    // Get display text for version button
    const getVersionDisplayText = useCallback(() => {
        if (state.totalVersions <= 1) {
            return "0";
        }
        return state.currentVersionIndex.toString();
    }, [state.currentVersionIndex, state.totalVersions]);

    // Check if this is the latest generation
    const isLatestGeneration = useCallback(() => {
        if (!generationHistory || !state.currentStep) {
            return true;
        }

        return !hasValidChildStepsForCurrentVersion(
            generationHistory.steps, 
            state.currentStep.id, 
            state.currentVersionIndex
        );
    }, [generationHistory, state.currentStep, state.currentVersionIndex, hasValidChildStepsForCurrentVersion]);

    return {
        // State
        currentStep: state.currentStep,
        availableVersions: state.availableVersions,
        currentVersionIndex: state.currentVersionIndex,
        totalVersions: state.totalVersions,
        canUndo: state.canUndo,
        canRedo: state.canRedo,
        isLoading,

        // Actions
        switchVersion,
        undo,
        redo,
        regenerate,

        // Computed values
        canRegenerate: canRegenerate(),
        versionDisplayText: getVersionDisplayText(),
        isLatestGeneration: isLatestGeneration(),

        // Helper functions
        hasGenerationHistory: () => state.currentStep !== null,
    };
}
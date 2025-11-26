import { useState, useEffect, useCallback } from 'react';
import { router } from '@inertiajs/react';

interface NavigationInfo {
    canUndo: boolean;
    canRedo: boolean;
    canRegenerate: boolean;
    currentVersionIndex: number;
    totalVersions: number;
    versionDisplayText: string;
}

interface UseOptimizedVersionControlProps {
    workspaceId: string;
    projectId: string;
    chapterOrder: number;
    initialNavigationInfo?: NavigationInfo;
    onContentUpdate?: (content: string) => void;
    isGenerating?: boolean;
}

export function useOptimizedVersionControl({
    workspaceId,
    projectId,
    chapterOrder,
    initialNavigationInfo,
    onContentUpdate,
    isGenerating = false,
}: UseOptimizedVersionControlProps) {
    const [navigationInfo, setNavigationInfo] = useState<NavigationInfo>(
        initialNavigationInfo || {
            canUndo: false,
            canRedo: false,
            canRegenerate: false,
            currentVersionIndex: 0,
            totalVersions: 0,
            versionDisplayText: '0',
        }
    );

    const [isLoading, setIsLoading] = useState(false);

    // Update navigation info when props change
    useEffect(() => {
        if (initialNavigationInfo) {
            setNavigationInfo(initialNavigationInfo);
        }
    }, [initialNavigationInfo]);

    // Only disable during actual loading operations, not generation
    const canPerformOperation = !isLoading;

    // Undo operation
    const undo = useCallback(() => {
        if (!navigationInfo.canUndo || !canPerformOperation) return;

        setIsLoading(true);
        router.post(
            route('editor.project.undo-step', {
                workspace_id: workspaceId,
                project_id: projectId,
            }),
            { order: chapterOrder },
            {
                preserveState: true,
                preserveScroll: true,
                onSuccess: () => {
                    console.log('Undo operation completed');
                },
                onError: (errors) => {
                    console.error('Undo operation failed:', errors);
                },
                onFinish: () => {
                    setIsLoading(false);
                },
            }
        );
    }, [workspaceId, projectId, chapterOrder, navigationInfo.canUndo, canPerformOperation]);

    // Redo operation
    const redo = useCallback(() => {
        if (!navigationInfo.canRedo || !canPerformOperation) return;

        setIsLoading(true);
        router.post(
            route('editor.project.redo-step', {
                workspace_id: workspaceId,
                project_id: projectId,
            }),
            { order: chapterOrder },
            {
                preserveState: true,
                preserveScroll: true,
                onSuccess: () => {
                    console.log('Redo operation completed');
                },
                onError: (errors) => {
                    console.error('Redo operation failed:', errors);
                },
                onFinish: () => {
                    setIsLoading(false);
                },
            }
        );
    }, [workspaceId, projectId, chapterOrder, navigationInfo.canRedo, canPerformOperation]);

    // Switch version operation
    const switchVersion = useCallback((versionIndex: number) => {
        if (!canPerformOperation || versionIndex === navigationInfo.currentVersionIndex) return;

        setIsLoading(true);
        router.post(
            route('editor.project.switch-version', {
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
                onSuccess: () => {
                    console.log('Version switch completed');
                },
                onError: (errors) => {
                    console.error('Version switch failed:', errors);
                },
                onFinish: () => {
                    setIsLoading(false);
                },
            }
        );
    }, [workspaceId, projectId, chapterOrder, navigationInfo.currentVersionIndex, canPerformOperation]);

    return {
        // State
        currentVersionIndex: navigationInfo.currentVersionIndex,
        totalVersions: navigationInfo.totalVersions,
        canUndo: navigationInfo.canUndo && canPerformOperation,
        canRedo: navigationInfo.canRedo && canPerformOperation,
        canRegenerate: navigationInfo.canRegenerate && canPerformOperation,
        isLoading: isLoading,
        versionDisplayText: navigationInfo.versionDisplayText,

        // Actions
        undo,
        redo,
        switchVersion,
    };
}

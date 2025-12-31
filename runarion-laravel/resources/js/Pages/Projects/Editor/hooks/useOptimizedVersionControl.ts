import { useState, useEffect, useCallback } from 'react';
import { router } from '@inertiajs/react';
import { useVersionCache } from './useVersionCache';

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
    currentNodeId?: string;
    initialNavigationInfo?: NavigationInfo;
    onContentUpdate?: (content: string) => void;
    isGenerating?: boolean;
}

export function useOptimizedVersionControl({
    workspaceId,
    projectId,
    chapterOrder,
    currentNodeId,
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

    // Version cache for instant switching
    const versionCache = useVersionCache();

    // Update cache context when node or chapter changes
    useEffect(() => {
        versionCache.setContext(currentNodeId || '', chapterOrder);
    }, [currentNodeId, chapterOrder, versionCache]);

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

    // Switch version operation - with cache support for instant switching
    const switchVersion = useCallback((versionIndex: number) => {
        if (!canPerformOperation || versionIndex === navigationInfo.currentVersionIndex) return;

        // Check cache first for instant switching
        const cached = versionCache.get(versionIndex);

        if (cached) {
            console.log(`Version cache HIT: v${versionIndex}`);

            // INSTANT: Update UI immediately from cache
            if (onContentUpdate && cached.content) {
                onContentUpdate(cached.content);
            }

            // Optimistically update navigation info
            if (cached.navigationInfo) {
                setNavigationInfo(cached.navigationInfo);
            } else {
                setNavigationInfo(prev => ({
                    ...prev,
                    currentVersionIndex: versionIndex,
                    versionDisplayText: String(versionIndex),
                }));
            }

            // Background sync with server for consistency
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
                    only: [], // Don't update any props - we already have the content
                }
            );
            return;
        }

        // FALLBACK: Fetch from server
        console.log(`Version cache MISS: v${versionIndex}, fetching from server`);
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
    }, [workspaceId, projectId, chapterOrder, navigationInfo.currentVersionIndex, canPerformOperation, versionCache, onContentUpdate]);

    // Cache a version (called by useProjectEditor after loading/generating)
    const cacheVersion = useCallback((
        versionIndex: number,
        content: string,
        navInfo?: NavigationInfo
    ) => {
        // Validate content before caching to prevent storing invalid data
        if (!content) {
            console.warn('Version cache: Attempted to cache empty content, skipping');
            return;
        }

        // Ensure versionIndex is valid
        if (versionIndex < 0 || !Number.isInteger(versionIndex)) {
            console.warn('Version cache: Invalid version index, skipping:', versionIndex);
            return;
        }

        versionCache.set(versionIndex, content, navInfo || navigationInfo);
    }, [versionCache, navigationInfo]);

    // Invalidate cache (called when node changes via undo/redo)
    const invalidateCache = useCallback((reason: 'node_change' | 'chapter_change' | 'generation') => {
        versionCache.invalidate(reason);
    }, [versionCache]);

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

        // Cache control
        cacheVersion,
        invalidateCache,
        hasVersionCached: versionCache.has,
    };
}

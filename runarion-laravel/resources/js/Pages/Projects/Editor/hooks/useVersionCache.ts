import { useRef, useCallback } from 'react';

interface NavigationInfo {
    canUndo: boolean;
    canRedo: boolean;
    canRegenerate: boolean;
    currentVersionIndex: number;
    totalVersions: number;
    versionDisplayText: string;
}

interface VersionCacheEntry {
    content: string;           // Lexical JSON content
    timestamp: number;         // When cached
    navigationInfo?: NavigationInfo;
}

interface VersionCacheState {
    nodeId: string;            // Current node ID
    chapterOrder: number;
    versions: Map<number, VersionCacheEntry>;
}

const MAX_CACHE_SIZE = 10;

/**
 * Hook for caching version content client-side to enable instant version switching.
 *
 * Features:
 * - Caches up to 10 versions using LRU eviction
 * - Invalidates on node/chapter changes
 * - Enables instant switching for cached versions
 */
export function useVersionCache() {
    const cacheRef = useRef<VersionCacheState>({
        nodeId: '',
        chapterOrder: -1,
        versions: new Map(),
    });

    /**
     * Get cached version content by version index
     */
    const get = useCallback((versionIndex: number): VersionCacheEntry | null => {
        return cacheRef.current.versions.get(versionIndex) || null;
    }, []);

    /**
     * Cache a version's content
     */
    const set = useCallback((
        versionIndex: number,
        content: string,
        navigationInfo?: NavigationInfo
    ) => {
        const cache = cacheRef.current;

        // Evict oldest if at capacity and this is a new entry
        if (cache.versions.size >= MAX_CACHE_SIZE && !cache.versions.has(versionIndex)) {
            let oldestKey = -1;
            let oldestTime = Infinity;

            cache.versions.forEach((entry, key) => {
                if (entry.timestamp < oldestTime) {
                    oldestTime = entry.timestamp;
                    oldestKey = key;
                }
            });

            if (oldestKey >= 0) {
                cache.versions.delete(oldestKey);
            }
        }

        cache.versions.set(versionIndex, {
            content,
            timestamp: Date.now(),
            navigationInfo,
        });

        console.log(`Version cache: stored v${versionIndex}, cache size: ${cache.versions.size}`);
    }, []);

    /**
     * Check if a version is cached
     */
    const has = useCallback((versionIndex: number): boolean => {
        return cacheRef.current.versions.has(versionIndex);
    }, []);

    /**
     * Invalidate the cache
     */
    const invalidate = useCallback((reason: 'node_change' | 'chapter_change' | 'generation') => {
        const size = cacheRef.current.versions.size;
        cacheRef.current.versions.clear();
        console.log(`Version cache invalidated: ${reason}, cleared ${size} entries`);
    }, []);

    /**
     * Update cache context (invalidates if context changed)
     */
    const setContext = useCallback((nodeId: string, chapterOrder: number) => {
        const cache = cacheRef.current;

        if (cache.nodeId !== nodeId || cache.chapterOrder !== chapterOrder) {
            cache.versions.clear();
            cache.nodeId = nodeId;
            cache.chapterOrder = chapterOrder;
            console.log(`Version cache: context updated (node: ${nodeId}, chapter: ${chapterOrder})`);
        }
    }, []);

    /**
     * Get cache size for debugging
     */
    const getSize = useCallback((): number => {
        return cacheRef.current.versions.size;
    }, []);

    /**
     * Get all cached version indices for debugging
     */
    const getCachedVersions = useCallback((): number[] => {
        return Array.from(cacheRef.current.versions.keys());
    }, []);

    return {
        get,
        set,
        has,
        invalidate,
        setContext,
        getSize,
        getCachedVersions,
    };
}

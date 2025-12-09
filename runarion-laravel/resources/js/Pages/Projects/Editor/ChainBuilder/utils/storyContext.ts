// Story context utilities for combining chapters

import { ProjectChapter } from '../types';

/**
 * Get full story context from all chapters
 */
export const getFullStoryContext = (chapters: ProjectChapter[]): string => {
    if (!chapters || chapters.length === 0) return '';
    
    return chapters
        .sort((a, b) => a.order - b.order)
        .map(ch => `=== ${ch.chapter_name} ===\n${ch.content || ''}`)
        .join('\n\n');
};

/**
 * Get recent story context (last N chapters) for continuation
 */
export const getRecentStoryContext = (
    chapters: ProjectChapter[],
    limit: number = 5
): string => {
    if (!chapters || chapters.length === 0) return '';
    
    const recent = chapters
        .sort((a, b) => b.order - a.order)
        .slice(0, limit)
        .reverse();
    
    return getFullStoryContext(recent);
};

/**
 * Get story context up to a specific chapter
 */
export const getStoryContextUpTo = (
    chapters: ProjectChapter[],
    maxOrder: number
): string => {
    if (!chapters || chapters.length === 0) return '';
    
    const upToChapters = chapters
        .filter(ch => ch.order <= maxOrder)
        .sort((a, b) => a.order - b.order);
    
    return getFullStoryContext(upToChapters);
};


// Story context utilities for combining chapters

import { ProjectChapter } from '../types';
import { extractTextFromLexical } from '../../utils/lexicalTextExtract';

/**
 * Get full story context from all chapters
 * Handles both plain text and Lexical JSON content formats
 */
export const getFullStoryContext = (chapters: ProjectChapter[]): string => {
    if (!chapters || chapters.length === 0) return '';

    return chapters
        .sort((a, b) => a.order - b.order)
        .map(ch => {
            // Convert Lexical JSON to plain text if needed
            const plainContent = extractTextFromLexical(ch.content);
            return `=== ${ch.chapter_name} ===\n${plainContent || ''}`;
        })
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


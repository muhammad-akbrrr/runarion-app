/**
 * Fuzzy Text Matching Utilities
 * Used to find text in the editor even when there are minor differences
 * (whitespace, quotes, special characters, etc.)
 */

interface MatchResult {
    found: boolean;
    start: number;
    end: number;
    confidence: number;
    matchedText: string;
}

/**
 * Normalize text for comparison by:
 * - Converting smart quotes to straight quotes
 * - Normalizing dashes
 * - Normalizing ellipsis
 * - Normalizing whitespace
 */
export function normalizeText(text: string): string {
    return text
        // Smart single quotes to straight
        .replace(/[\u2018\u2019\u201A\u201B\u2032\u2035]/g, "'")
        // Smart double quotes to straight
        .replace(/[\u201C\u201D\u201E\u201F\u2033\u2036]/g, '"')
        // Em dash and en dash variations
        .replace(/[\u2014\u2015\u2012\u2013]/g, '-')
        // Ellipsis
        .replace(/\u2026/g, '...')
        // Non-breaking space
        .replace(/\u00A0/g, ' ')
        // Multiple spaces to single
        .replace(/\s+/g, ' ')
        .trim();
}

/**
 * Create a simplified version for looser matching
 * Removes all punctuation and converts to lowercase
 */
export function simplifyText(text: string): string {
    return normalizeText(text)
        .toLowerCase()
        .replace(/[^\w\s]/g, '')
        .replace(/\s+/g, ' ')
        .trim();
}

/**
 * Calculate similarity between two strings using Levenshtein distance
 * Returns a value between 0 and 1 (1 = identical)
 */
export function calculateSimilarity(str1: string, str2: string): number {
    const len1 = str1.length;
    const len2 = str2.length;
    
    if (len1 === 0 && len2 === 0) return 1;
    if (len1 === 0 || len2 === 0) return 0;
    
    // For very long strings, use a faster approximation
    if (len1 > 1000 || len2 > 1000) {
        return approximateSimilarity(str1, str2);
    }
    
    const matrix: number[][] = [];
    
    for (let i = 0; i <= len1; i++) {
        matrix[i] = [i];
    }
    for (let j = 0; j <= len2; j++) {
        matrix[0][j] = j;
    }
    
    for (let i = 1; i <= len1; i++) {
        for (let j = 1; j <= len2; j++) {
            const cost = str1[i - 1] === str2[j - 1] ? 0 : 1;
            matrix[i][j] = Math.min(
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j - 1] + cost
            );
        }
    }
    
    const distance = matrix[len1][len2];
    const maxLen = Math.max(len1, len2);
    return 1 - distance / maxLen;
}

/**
 * Fast approximation of string similarity using word overlap
 */
function approximateSimilarity(str1: string, str2: string): number {
    const words1 = new Set(str1.toLowerCase().split(/\s+/));
    const words2 = new Set(str2.toLowerCase().split(/\s+/));
    
    let intersection = 0;
    for (const word of words1) {
        if (words2.has(word)) {
            intersection++;
        }
    }
    
    const union = words1.size + words2.size - intersection;
    return union === 0 ? 0 : intersection / union;
}

/**
 * Find best match for searchText in content
 * Uses multiple strategies with increasing fuziness
 */
export function findBestMatch(content: string, searchText: string): MatchResult {
    // Strategy 1: Exact match
    let index = content.indexOf(searchText);
    if (index !== -1) {
        return {
            found: true,
            start: index,
            end: index + searchText.length,
            confidence: 1.0,
            matchedText: searchText,
        };
    }
    
    // Strategy 2: Normalized match
    const normalizedContent = normalizeText(content);
    const normalizedSearch = normalizeText(searchText);
    
    index = normalizedContent.indexOf(normalizedSearch);
    if (index !== -1) {
        // Find the actual position in original content
        const result = findOriginalPosition(content, normalizedContent, index, normalizedSearch.length);
        return {
            found: true,
            ...result,
            confidence: 0.95,
        };
    }
    
    // Strategy 3: Sliding window with similarity threshold
    const windowResult = slidingWindowMatch(content, searchText, 0.85);
    if (windowResult.found) {
        return windowResult;
    }
    
    // Strategy 4: Word-based matching (for longer text)
    if (searchText.length > 50) {
        const wordResult = wordBasedMatch(content, searchText, 0.75);
        if (wordResult.found) {
            return wordResult;
        }
    }
    
    // No match found
    return {
        found: false,
        start: -1,
        end: -1,
        confidence: 0,
        matchedText: '',
    };
}

/**
 * Find original position in content from normalized position
 */
function findOriginalPosition(
    original: string,
    normalized: string,
    normalizedStart: number,
    normalizedLength: number
): { start: number; end: number; matchedText: string } {
    // Map normalized positions back to original
    let originalPos = 0;
    let normalizedPos = 0;
    let start = 0;
    let end = 0;
    
    // Find start position
    while (normalizedPos < normalizedStart && originalPos < original.length) {
        const origChar = original[originalPos];
        const normChar = normalizeText(origChar);
        
        if (normChar.length > 0) {
            normalizedPos += normChar.length;
        }
        originalPos++;
    }
    start = originalPos;
    
    // Find end position
    let matchLength = 0;
    while (matchLength < normalizedLength && originalPos < original.length) {
        const origChar = original[originalPos];
        const normChar = normalizeText(origChar);
        
        if (normChar.length > 0) {
            matchLength += normChar.length;
        }
        originalPos++;
    }
    end = originalPos;
    
    return {
        start,
        end,
        matchedText: original.substring(start, end),
    };
}

/**
 * Sliding window match with similarity threshold
 */
function slidingWindowMatch(
    content: string,
    searchText: string,
    threshold: number
): MatchResult {
    const searchLen = searchText.length;
    const normalizedSearch = normalizeText(searchText);
    const simplifiedSearch = simplifyText(searchText);
    
    let bestMatch: MatchResult = {
        found: false,
        start: -1,
        end: -1,
        confidence: 0,
        matchedText: '',
    };
    
    // Use a window slightly larger than search text to account for differences
    const windowSize = Math.ceil(searchLen * 1.2);
    const step = Math.max(1, Math.floor(searchLen / 10));
    
    for (let i = 0; i <= content.length - searchLen; i += step) {
        const window = content.substring(i, i + windowSize);
        const normalizedWindow = normalizeText(window);
        
        // Quick check using simplified comparison
        const simplifiedWindow = simplifyText(window);
        const quickSimilarity = calculateSimilarity(
            simplifiedWindow.substring(0, Math.min(50, simplifiedSearch.length)),
            simplifiedSearch.substring(0, 50)
        );
        
        // Skip if first 50 chars are too different
        if (quickSimilarity < 0.5) continue;
        
        // Full similarity check
        const similarity = calculateSimilarity(normalizedWindow, normalizedSearch);
        
        if (similarity > bestMatch.confidence && similarity >= threshold) {
            // Refine the exact boundaries
            const refinedEnd = Math.min(i + windowSize, content.length);
            let actualEnd = refinedEnd;
            
            // Try to find better end boundary
            for (let e = refinedEnd; e >= i + searchLen * 0.8; e--) {
                const testWindow = content.substring(i, e);
                const testSimilarity = calculateSimilarity(normalizeText(testWindow), normalizedSearch);
                if (testSimilarity > similarity) {
                    actualEnd = e;
                    break;
                }
            }
            
            bestMatch = {
                found: true,
                start: i,
                end: actualEnd,
                confidence: similarity,
                matchedText: content.substring(i, actualEnd),
            };
        }
    }
    
    return bestMatch;
}

/**
 * Word-based matching for longer text
 */
function wordBasedMatch(
    content: string,
    searchText: string,
    threshold: number
): MatchResult {
    const searchWords = searchText.split(/\s+/);
    if (searchWords.length < 3) {
        return { found: false, start: -1, end: -1, confidence: 0, matchedText: '' };
    }
    
    // Find first few words as anchor
    const anchorWords = searchWords.slice(0, Math.min(5, searchWords.length));
    const anchorPattern = anchorWords.map(w => 
        w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    ).join('\\s+');
    
    const anchorRegex = new RegExp(anchorPattern, 'i');
    const anchorMatch = anchorRegex.exec(content);
    
    if (!anchorMatch) {
        return { found: false, start: -1, end: -1, confidence: 0, matchedText: '' };
    }
    
    // Found anchor, now expand to find full match
    const anchorStart = anchorMatch.index;
    const estimatedEnd = Math.min(anchorStart + searchText.length * 1.3, content.length);
    
    // Binary search for best end position
    let bestEnd = estimatedEnd;
    let bestConfidence = 0;
    
    for (let end = anchorStart + searchText.length * 0.8; end <= estimatedEnd; end += 10) {
        const candidate = content.substring(anchorStart, end);
        const similarity = calculateSimilarity(normalizeText(candidate), normalizeText(searchText));
        
        if (similarity > bestConfidence) {
            bestConfidence = similarity;
            bestEnd = end;
        }
    }
    
    if (bestConfidence >= threshold) {
        return {
            found: true,
            start: anchorStart,
            end: bestEnd,
            confidence: bestConfidence,
            matchedText: content.substring(anchorStart, bestEnd),
        };
    }
    
    return { found: false, start: -1, end: -1, confidence: 0, matchedText: '' };
}

/**
 * Apply an edit to content using fuzzy matching
 */
export function applyFuzzyEdit(
    content: string,
    oldText: string,
    newText: string
): { success: boolean; newContent: string; matchResult: MatchResult } {
    const matchResult = findBestMatch(content, oldText);
    
    if (!matchResult.found) {
        return {
            success: false,
            newContent: content,
            matchResult,
        };
    }
    
    const newContent = 
        content.substring(0, matchResult.start) +
        newText +
        content.substring(matchResult.end);
    
    return {
        success: true,
        newContent,
        matchResult,
    };
}


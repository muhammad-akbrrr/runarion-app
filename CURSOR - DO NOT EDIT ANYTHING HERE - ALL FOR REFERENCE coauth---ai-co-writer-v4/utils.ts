
/**
 * Finds the best matching substring in a large text for a given snippet.
 * Handles whitespace discrepancies and minor punctuation differences.
 */
export const findBestMatch = (fullText: string, snippet: string): { start: number; end: number; match: string } | null => {
    if (!fullText || !snippet) return null;

    // 1. Try Exact Match
    const exactIdx = fullText.indexOf(snippet);
    if (exactIdx !== -1) {
        return { start: exactIdx, end: exactIdx + snippet.length, match: snippet };
    }

    // 2. Normalized Whitespace Match
    // Collapses all newlines/tabs/spaces into single spaces for comparison
    const normalize = (s: string) => s.replace(/\s+/g, ' ').trim();
    const cleanSnippet = normalize(snippet);
    const cleanFull = normalize(fullText);
    
    // We need to map the "clean" index back to the "dirty" index. 
    // This is complex, so we use a simpler approach: Token matching.

    // 3. Token Sequence Matcher (Robust)
    // Split snippet into words. Find that sequence of words in the full text.
    const tokens = snippet.split(/\s+/).filter(t => t.length > 0);
    if (tokens.length === 0) return null;

    // Create a regex pattern that allows flexible whitespace between words
    // Escape special regex chars in tokens
    const escapeRegExp = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const patternStr = tokens.map(escapeRegExp).join('[\\s\\W]+'); // Allow whitespace or non-word chars between words
    
    try {
        const regex = new RegExp(patternStr, 'gm'); // multiline search
        const match = regex.exec(fullText);
        
        if (match) {
            return {
                start: match.index,
                end: match.index + match[0].length,
                match: match[0]
            };
        }
    } catch (e) {
        console.warn("Regex match failed", e);
    }

    // 4. Soft Fallback: First 20 chars + Last 20 chars match
    // If the middle is messed up, check if the start and end align
    if (snippet.length > 50) {
        const startFrag = snippet.substring(0, 20);
        const endFrag = snippet.substring(snippet.length - 20);
        
        const startIdx = fullText.indexOf(startFrag);
        if (startIdx !== -1) {
            // Search for end frag AFTER start frag
            const endIdx = fullText.indexOf(endFrag, startIdx + 20);
            if (endIdx !== -1) {
                const candidate = fullText.substring(startIdx, endIdx + endFrag.length);
                // Sanity check: length shouldn't be wildly different
                if (Math.abs(candidate.length - snippet.length) < snippet.length * 0.5) {
                    return {
                        start: startIdx,
                        end: endIdx + endFrag.length,
                        match: candidate
                    };
                }
            }
        }
    }

    return null;
};

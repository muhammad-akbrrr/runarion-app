import { useEffect, useRef, useCallback } from 'react';
import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import { 
    $getRoot, 
    $isTextNode, 
    TextNode,
    $getNodeByKey,
    LexicalNode,
    $isParagraphNode,
    ElementNode
} from 'lexical';
import { $convertToMarkdownString, TRANSFORMERS } from '@lexical/markdown';

interface ColorCodingPluginProps {
    /** Array of [start, end] positions for AI-generated text */
    aiRanges?: number[][];
    isColorCoded: boolean;
}

const USER_COLOR = '#1e40af'; // Blue-800
const AI_COLOR = '#6b7280';   // Gray-500

/**
 * Get plain text from markdown (must match useProjectEditor.ts exactly!)
 */
function getPlainText(markdown: string): string {
    if (!markdown) return '';
    return markdown
        .replace(/\*\*([^*]+)\*\*/g, '$1')
        .replace(/\*([^*]+)\*/g, '$1')
        .replace(/`([^`]+)`/g, '$1')
        .replace(/#{1,6}\s+/g, '')
        .replace(/^\s*[-*+]\s+/gm, '')
        .replace(/^\s*\d+\.\s+/gm, '')
        .replace(/^>\s+/gm, '')
        .replace(/~~([^~]+)~~/g, '$1');
}

/**
 * Determines if a character position is within any AI range
 */
function isPositionInAiRange(position: number, ranges: number[][]): boolean {
    for (const [start, end] of ranges) {
        if (position >= start && position < end) {
            return true;
        }
    }
    return false;
}

/**
 * Find the split points within a text node where color should change
 * Returns array of positions (relative to node start) where splits should occur
 */
function findSplitPoints(nodeStart: number, nodeEnd: number, aiRanges: number[][]): number[] {
    const splits: Set<number> = new Set();
    
    for (const [aiStart, aiEnd] of aiRanges) {
        // If AI range starts inside this node
        if (aiStart > nodeStart && aiStart < nodeEnd) {
            splits.add(aiStart - nodeStart);
        }
        // If AI range ends inside this node
        if (aiEnd > nodeStart && aiEnd < nodeEnd) {
            splits.add(aiEnd - nodeStart);
        }
    }
    
    return Array.from(splits).sort((a, b) => a - b);
}

/**
 * Color coding plugin that splits text nodes at AI boundaries
 * to achieve character-level color differentiation.
 * 
 * This plugin works by:
 * 1. Converting Lexical content to markdown to get accurate positions
 * 2. Finding text nodes that span both user and AI content
 * 3. Splitting them at the boundary using Lexical's splitText()
 * 4. Applying different colors to each segment
 */
export function ColorCodingPlugin({ 
    aiRanges = [], 
    isColorCoded 
}: ColorCodingPluginProps) {
    const [editor] = useLexicalComposerContext();
    
    // Use ref to access latest ranges inside the closure
    const aiRangesRef = useRef<number[][]>(aiRanges || []);
    aiRangesRef.current = aiRanges || [];
    
    // Track if we're currently processing to prevent infinite loops
    const isProcessingRef = useRef(false);

    const applyColorsViaLexical = useCallback(() => {
        if (isProcessingRef.current) return;
        
        const ranges = aiRangesRef.current || [];
        
        editor.update(() => {
            isProcessingRef.current = true;
            
            try {
                const root = $getRoot();
                
                // Convert current Lexical content to markdown to get accurate plain text
                // This ensures we use the SAME position counting as useProjectEditor
                const markdown = $convertToMarkdownString(TRANSFORMERS);
                const plainText = getPlainText(markdown);
                
                // Build a mapping from plain text position to Lexical text nodes
                // by walking through both simultaneously
                const textNodesInfo: { node: TextNode; start: number; end: number }[] = [];
                
                let plainTextIndex = 0;
                
                const collectTextNodes = (node: LexicalNode) => {
                    if ($isTextNode(node)) {
                        const nodeText = node.getTextContent();
                        const nodeLength = nodeText.length;
                        
                        // Find where this node's text appears in the plain text
                        // Starting from our current position
                        const foundIndex = plainText.indexOf(nodeText, plainTextIndex);
                        
                        if (foundIndex !== -1 && foundIndex < plainTextIndex + nodeLength + 10) {
                            // Found a reasonable match
                            textNodesInfo.push({
                                node,
                                start: foundIndex,
                                end: foundIndex + nodeLength
                            });
                            plainTextIndex = foundIndex + nodeLength;
                        } else {
                            // Fallback: use sequential positioning
                            textNodesInfo.push({
                                node,
                                start: plainTextIndex,
                                end: plainTextIndex + nodeLength
                            });
                            plainTextIndex += nodeLength;
                        }
                    } else if ('getChildren' in node) {
                        const children = (node as ElementNode).getChildren();
                        for (const c of children) {
                            collectTextNodes(c);
                        }
                    }
                };
                
                // Process all children
                for (const child of root.getChildren()) {
                    collectTextNodes(child);
                }
                
                // Debug: log positions when there are AI ranges
                if (ranges.length > 0 && textNodesInfo.length > 0) {
                    console.log('🎨 ColorCodingPlugin positions:', {
                        plainTextLength: plainText.length,
                        nodes: textNodesInfo.slice(0, 3).map(t => ({
                            text: `"${t.node.getTextContent().substring(0, 15)}..."`,
                            start: t.start,
                            end: t.end
                        })),
                        aiRanges: ranges.map((r: number[]) => `[${r[0]}-${r[1]}]`).join(', ')
                    });
                }
                
                // Now process each text node - split if needed and apply colors
                for (const { node, start, end } of textNodesInfo) {
                    // Check if node still exists (might have been modified)
                    const currentNode = $getNodeByKey(node.getKey());
                    if (!currentNode || !$isTextNode(currentNode)) continue;
                    
                    const text = currentNode.getTextContent();
                    if (text.length === 0) continue;
                    
                    // Find split points within this node
                    const splitPoints = findSplitPoints(start, end, ranges);
                    
                    // Filter out invalid split points (0 or >= text length)
                    const validSplitPoints = splitPoints.filter(p => p > 0 && p < text.length);
                    
                    if (validSplitPoints.length > 0 && isColorCoded) {
                        // Need to split this node
                        try {
                            const newNodes = currentNode.splitText(...validSplitPoints);
                            
                            // Apply colors to each resulting node
                            let currentOffset = start;
                            for (const newNode of newNodes) {
                                const nodeText = newNode.getTextContent();
                                const nodeStart = currentOffset;
                                
                                // Check if this segment is AI text (check the first char of segment)
                                const isAi = isPositionInAiRange(nodeStart, ranges);
                                
                                // Apply style
                                newNode.setStyle(isAi ? `color: ${AI_COLOR}` : `color: ${USER_COLOR}`);
                                
                                currentOffset += nodeText.length;
                            }
                        } catch (e) {
                            // splitText might fail if positions are invalid
                            // Fall back to coloring the whole node
                            const isAi = isPositionInAiRange(start, ranges);
                            currentNode.setStyle(isAi ? `color: ${AI_COLOR}` : `color: ${USER_COLOR}`);
                        }
                    } else {
                        // No split needed - color the whole node
                        if (isColorCoded) {
                            const isAi = ranges.length > 0 && isPositionInAiRange(start, ranges);
                            currentNode.setStyle(isAi ? `color: ${AI_COLOR}` : `color: ${USER_COLOR}`);
                        } else {
                            // Remove color styling
                            currentNode.setStyle('');
                        }
                    }
                }
            } finally {
                isProcessingRef.current = false;
            }
        }, { tag: 'color-coding', discrete: true });
    }, [editor, isColorCoded]);

    // Apply colors when aiRanges change
    useEffect(() => {
        // Small delay to let other updates settle
        const timeoutId = setTimeout(() => {
            applyColorsViaLexical();
        }, 50);
        
        return () => clearTimeout(timeoutId);
    }, [aiRanges, isColorCoded, applyColorsViaLexical]);

    // Also apply on editor updates, but debounced
    useEffect(() => {
        let timeoutId: ReturnType<typeof setTimeout> | null = null;
        
        const unsubscribe = editor.registerUpdateListener(({ tags }: { tags: Set<string> }) => {
            // Skip if this update was from our own color coding
            if (tags.has('color-coding')) return;
            
            // Debounce to avoid too many updates
            if (timeoutId) clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                applyColorsViaLexical();
            }, 100);
        });

        return () => {
            unsubscribe();
            if (timeoutId) clearTimeout(timeoutId);
        };
    }, [editor, applyColorsViaLexical]);

    return null;
}

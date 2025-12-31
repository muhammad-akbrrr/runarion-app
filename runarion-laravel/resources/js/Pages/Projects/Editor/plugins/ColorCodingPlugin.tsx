import { useEffect, useCallback, useRef } from 'react';
import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import { $getRoot, LexicalNode, ElementNode } from 'lexical';
import { $isOriginTextNode } from '../nodes/OriginTextNode';

interface ColorCodingPluginProps {
    isColorCoded: boolean;
    // aiRanges prop removed - now uses OriginTextNode metadata
}

const USER_COLOR = '#1e40af'; // Blue-800
const AI_COLOR = '#6b7280';   // Gray-500

/**
 * Color coding plugin that applies colors based on OriginTextNode metadata.
 *
 * This plugin reads the origin ('user' or 'ai') from each text node and applies
 * appropriate styling. This is much simpler and more reliable than the previous
 * position-based approach since the metadata survives all editor operations.
 */
export function ColorCodingPlugin({ isColorCoded }: ColorCodingPluginProps) {
    const [editor] = useLexicalComposerContext();

    // Track if we're currently processing to prevent infinite loops
    const isProcessingRef = useRef(false);

    const applyColors = useCallback(() => {
        if (isProcessingRef.current) return;

        editor.update(() => {
            isProcessingRef.current = true;

            try {
                const root = $getRoot();

                // Recursively process all nodes
                const processNode = (node: LexicalNode) => {
                    if ($isOriginTextNode(node)) {
                        if (isColorCoded) {
                            const color = node.getOrigin() === 'ai' ? AI_COLOR : USER_COLOR;
                            node.setStyle(`color: ${color}`);
                        } else {
                            // Remove color styling when color coding is disabled
                            node.setStyle('');
                        }
                    }

                    // Process children for element nodes
                    if ('getChildren' in node) {
                        const children = (node as ElementNode).getChildren();
                        children.forEach(processNode);
                    }
                };

                root.getChildren().forEach(processNode);
            } finally {
                isProcessingRef.current = false;
            }
        }, { tag: 'color-coding', discrete: true });
    }, [editor, isColorCoded]);

    // Apply colors when isColorCoded changes
    useEffect(() => {
        // Small delay to let other updates settle
        const timeoutId = setTimeout(() => {
            applyColors();
        }, 50);

        return () => clearTimeout(timeoutId);
    }, [isColorCoded, applyColors]);

    // Apply colors on editor updates (debounced)
    useEffect(() => {
        let timeoutId: ReturnType<typeof setTimeout> | null = null;

        const unsubscribe = editor.registerUpdateListener(({ tags }) => {
            // Skip if this update was from our own color coding
            if (tags.has('color-coding')) return;

            // Debounce to avoid too many updates
            if (timeoutId) clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                applyColors();
            }, 100);
        });

        return () => {
            unsubscribe();
            if (timeoutId) clearTimeout(timeoutId);
        };
    }, [editor, applyColors]);

    return null;
}

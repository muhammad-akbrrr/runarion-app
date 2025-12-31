import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import { useEffect, useRef } from 'react';
import { TextNode, $getRoot, LexicalNode, ElementNode } from 'lexical';
import { $createOriginTextNode, OriginTextNode } from '../nodes/OriginTextNode';

/**
 * Plugin that automatically converts plain TextNodes to OriginTextNodes with 'user' origin.
 * This ensures all user-typed content is properly tagged, while AI-generated content
 * (created via StreamingPlugin) uses 'ai' origin.
 *
 * Also runs an initial pass on mount to convert any existing TextNodes that may have been
 * deserialized before the transform was registered.
 */
export function OriginTrackingPlugin(): null {
    const [editor] = useLexicalComposerContext();
    const hasRunInitialPassRef = useRef(false);

    useEffect(() => {
        // Register a node transform that converts TextNodes to OriginTextNodes
        // This runs whenever a new TextNode is created in the editor
        const unregisterTransform = editor.registerNodeTransform(TextNode, (node) => {
            // Skip if already an OriginTextNode (prevents infinite loop)
            if (node instanceof OriginTextNode) {
                return;
            }

            // Convert plain TextNode to OriginTextNode with 'user' origin
            const originNode = $createOriginTextNode(node.getTextContent(), 'user');

            // Preserve all formatting properties
            originNode.setFormat(node.getFormat());
            originNode.setDetail(node.getDetail());
            originNode.setMode(node.getMode());
            originNode.setStyle(node.getStyle());

            // Replace the TextNode with the OriginTextNode
            node.replace(originNode);
        });

        // ALSO: Run initial pass to convert any existing TextNodes
        // This catches nodes that were deserialized before the transform was registered
        // Use queueMicrotask to ensure this runs after initial content load
        if (!hasRunInitialPassRef.current) {
            hasRunInitialPassRef.current = true;

            queueMicrotask(() => {
                editor.update(() => {
                    const root = $getRoot();
                    let convertedCount = 0;

                    const convertTextNodes = (node: LexicalNode) => {
                        // Check if this is a plain TextNode (not OriginTextNode)
                        if (node instanceof TextNode && !(node instanceof OriginTextNode)) {
                            const originNode = $createOriginTextNode(node.getTextContent(), 'user');
                            originNode.setFormat(node.getFormat());
                            originNode.setDetail(node.getDetail());
                            originNode.setMode(node.getMode());
                            originNode.setStyle(node.getStyle());
                            node.replace(originNode);
                            convertedCount++;
                        }
                        // Recursively process children of element nodes
                        if ('getChildren' in node && typeof (node as ElementNode).getChildren === 'function') {
                            (node as ElementNode).getChildren().forEach(convertTextNodes);
                        }
                    };

                    root.getChildren().forEach(convertTextNodes);

                    if (convertedCount > 0) {
                        console.log(`OriginTrackingPlugin: Converted ${convertedCount} existing TextNodes to OriginTextNodes`);
                    }
                }, { discrete: true, tag: 'origin-tracking-init' });
            });
        }

        return unregisterTransform;
    }, [editor]);

    return null;
}

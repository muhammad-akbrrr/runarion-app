import { LexicalEditor, $getRoot, TextNode } from 'lexical';
import { $isOriginTextNode, $createOriginTextNode, OriginTextNode } from '../nodes/OriginTextNode';

interface ReplaceResult {
    success: boolean;
    error?: string;
}

/**
 * Get plain text content from Lexical editor
 */
export function getPlainTextFromEditor(editor: LexicalEditor): string {
    let text = '';
    editor.getEditorState().read(() => {
        text = $getRoot().getTextContent();
    });
    return text;
}

/**
 * Replace text in Lexical editor using the editor API
 * Preserves JSON structure and node types
 */
export function replaceTextInLexicalEditor(
    editor: LexicalEditor,
    oldText: string,
    newText: string
): Promise<ReplaceResult> {
    return new Promise((resolve) => {
        editor.update(() => {
            try {
                const root = $getRoot();
                const textContent = root.getTextContent();

                const startIndex = textContent.indexOf(oldText);
                if (startIndex === -1) {
                    resolve({ success: false, error: 'Text not found in editor' });
                    return;
                }

                // Walk through all text nodes
                let currentPos = 0;
                type NodeInfo = { node: TextNode | OriginTextNode; startOffset: number; endOffset: number };
                const nodesToProcess: NodeInfo[] = [];

                const processNode = (node: any) => {
                    if (node.__type === 'text' || node.__type === 'origin-text') {
                        const nodeText = node.getTextContent();
                        const nodeStart = currentPos;
                        const nodeEnd = currentPos + nodeText.length;
                        const targetEnd = startIndex + oldText.length;

                        if (nodeEnd > startIndex && nodeStart < targetEnd) {
                            nodesToProcess.push({
                                node,
                                startOffset: Math.max(0, startIndex - nodeStart),
                                endOffset: Math.min(nodeText.length, targetEnd - nodeStart)
                            });
                        }
                        currentPos = nodeEnd;
                    }

                    if (typeof node.getChildren === 'function') {
                        for (const child of node.getChildren()) {
                            processNode(child);
                        }
                    }
                };

                processNode(root);

                if (nodesToProcess.length === 0) {
                    resolve({ success: false, error: 'Could not locate text nodes' });
                    return;
                }

                // Single node case (most common)
                if (nodesToProcess.length === 1) {
                    const { node, startOffset, endOffset } = nodesToProcess[0];
                    const nodeText = node.getTextContent();
                    const newNodeText = nodeText.slice(0, startOffset) + newText + nodeText.slice(endOffset);

                    if ($isOriginTextNode(node)) {
                        const newNode = $createOriginTextNode(newNodeText, 'user');
                        newNode.setFormat(node.getFormat());
                        newNode.setStyle(node.getStyle());
                        node.replace(newNode);
                    } else {
                        node.setTextContent(newNodeText);
                    }
                } else {
                    // Multi-node case: update first, remove middle, trim last
                    const first = nodesToProcess[0];
                    const firstText = first.node.getTextContent();
                    const newFirstText = firstText.slice(0, first.startOffset) + newText;

                    if ($isOriginTextNode(first.node)) {
                        const newNode = $createOriginTextNode(newFirstText, 'user');
                        newNode.setFormat(first.node.getFormat());
                        first.node.replace(newNode);
                    } else {
                        first.node.setTextContent(newFirstText);
                    }

                    for (let i = 1; i < nodesToProcess.length; i++) {
                        const { node, endOffset } = nodesToProcess[i];
                        if (i === nodesToProcess.length - 1) {
                            const lastText = node.getTextContent();
                            const remainingText = lastText.slice(endOffset);
                            if (remainingText) {
                                node.setTextContent(remainingText);
                            } else {
                                node.remove();
                            }
                        } else {
                            node.remove();
                        }
                    }
                }

                resolve({ success: true });
            } catch (error) {
                console.error('[LexicalReplace] Error:', error);
                resolve({ success: false, error: String(error) });
            }
        });
    });
}

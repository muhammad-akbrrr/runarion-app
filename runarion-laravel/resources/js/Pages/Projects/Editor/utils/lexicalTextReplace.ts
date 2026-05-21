import {
    LexicalEditor,
    $getRoot,
    $createRangeSelection,
    $setSelection,
    TextNode,
    $isElementNode,
    $createParagraphNode,
    $createLineBreakNode,
} from 'lexical';
import { $createOriginTextNode, OriginType } from '../nodes/OriginTextNode';

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
 * Replace text in Lexical editor using Selection API
 * Uses $createRangeSelection + setTextNodeRange + insertText pattern
 * This is the proper Lexical way to programmatically replace text
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

                // Find the position of oldText
                const startIndex = textContent.indexOf(oldText);
                if (startIndex === -1) {
                    resolve({ success: false, error: 'Text not found in editor' });
                    return;
                }
                const endIndex = startIndex + oldText.length;

                // Walk through nodes using paragraph-aware position tracking
                // This matches how getTextContent() counts characters (including \n paragraph separators)
                let charPos = 0;
                let startNode: TextNode | null = null;
                let startOffset = 0;
                let endNode: TextNode | null = null;
                let endOffset = 0;

                const allParagraphs = root.getChildren();

                for (let pIdx = 0; pIdx < allParagraphs.length; pIdx++) {
                    // Early exit if both nodes found
                    if (startNode && endNode) break;

                    const para = allParagraphs[pIdx];

                    // Skip non-element nodes (safety check)
                    if (!$isElementNode(para)) continue;

                    const children = para.getChildren();

                    for (const child of children) {
                        // Early exit if both nodes found
                        if (startNode && endNode) break;

                        // Process both TextNode and OriginTextNode (which extends TextNode)
                        if (child instanceof TextNode) {
                            const nodeText = child.getTextContent();
                            const nodeStart = charPos;
                            const nodeEnd = charPos + nodeText.length;

                            // Check if this node contains the start position
                            // Condition: startIndex is within [nodeStart, nodeEnd)
                            if (!startNode && startIndex >= nodeStart && startIndex < nodeEnd) {
                                startNode = child;
                                startOffset = startIndex - nodeStart;
                            }

                            // Check if this node contains the end position
                            // Condition: endIndex is within (nodeStart, nodeEnd]
                            if (!endNode && endIndex > nodeStart && endIndex <= nodeEnd) {
                                endNode = child;
                                endOffset = endIndex - nodeStart;
                            }

                            charPos += nodeText.length;
                        }
                    }

                    // CRITICAL FIX: Account for paragraph separator character (\n)
                    // getTextContent() includes \n between paragraphs
                    if (pIdx < allParagraphs.length - 1) {
                        charPos += 1;
                    }
                }

                // Validate we found both nodes
                if (!startNode || !endNode) {
                    console.error('[LexicalReplace] Could not locate text nodes', {
                        textContentPreview: textContent.substring(0, 200),
                        searchText: oldText.substring(0, 100),
                        startIndex,
                        endIndex,
                        charPosReached: charPos,
                        paragraphCount: allParagraphs.length,
                    });
                    resolve({ success: false, error: 'Could not locate text nodes' });
                    return;
                }

                // Validate offsets are within bounds
                const startNodeLength = startNode.getTextContent().length;
                const endNodeLength = endNode.getTextContent().length;

                startOffset = Math.max(0, Math.min(startOffset, startNodeLength));
                endOffset = Math.max(0, Math.min(endOffset, endNodeLength));

                // Create a range selection spanning the old text
                const rangeSelection = $createRangeSelection();

                // Set the selection range using setTextNodeRange
                // This sets both anchor and focus to span the old text
                rangeSelection.setTextNodeRange(
                    startNode as TextNode,
                    startOffset,
                    endNode as TextNode,
                    endOffset
                );

                // Apply the selection to the editor
                $setSelection(rangeSelection);

                // Replace the selected text
                // insertText() automatically DELETES the selection first, then inserts
                rangeSelection.insertText(newText);

                resolve({ success: true });
            } catch (error) {
                console.error('[LexicalReplace] Error:', error);
                resolve({ success: false, error: String(error) });
            }
        });
    });
}

/**
 * Append text to the end of the editor with a specific origin
 * Used for ChainBuilder output insertion to properly mark content as AI-generated
 */
export function appendTextWithOrigin(
    editor: LexicalEditor,
    text: string,
    origin: OriginType,
    separator: string = '\n\n'
): Promise<ReplaceResult> {
    return new Promise((resolve) => {
        editor.update(() => {
            try {
                const root = $getRoot();
                const currentContent = root.getTextContent();

                // Add separator if there's existing content
                const needsSeparator = currentContent.trim().length > 0;

                // Split the new text by double newlines to create paragraphs
                const paragraphs = text.split(/\n\n+/);

                paragraphs.forEach((para, index) => {
                    if (!para.trim() && index !== paragraphs.length - 1) return;

                    // Add separator paragraph before first new paragraph if needed
                    if (needsSeparator && index === 0) {
                        // Get last paragraph and append separator + content
                        const lastChild = root.getLastChild();
                        if (lastChild && $isElementNode(lastChild)) {
                            // Add a blank line by creating a new paragraph
                            if (separator === '\n\n') {
                                const blankPara = $createParagraphNode();
                                root.append(blankPara);
                            }
                        }
                    }

                    const p = $createParagraphNode();
                    // Handle single newlines within paragraph
                    const lines = para.split('\n');
                    lines.forEach((line, lineIndex) => {
                        if (lineIndex > 0) {
                            p.append($createOriginTextNode('\n', origin));
                        }
                        if (line) {
                            p.append($createOriginTextNode(line, origin));
                        }
                    });
                    root.append(p);
                });

                // Move cursor to end
                const lastPara = root.getLastChild();
                if (lastPara) {
                    lastPara.selectEnd();
                }

                resolve({ success: true });
            } catch (error) {
                console.error('[LexicalAppend] Error:', error);
                resolve({ success: false, error: String(error) });
            }
        });
    });
}

/**
 * Inserts chain builder result as AI-originated content at the end of the document
 * Ignores any markdown formatting in the text and treats everything as plain text
 *
 * @param editor - Lexical editor instance
 * @param text - Plain text result from chain builder
 * @returns Promise that resolves when insertion is complete
 */
export function insertChainBuilderResult(
    editor: LexicalEditor,
    text: string
): Promise<void> {
    return new Promise((resolve) => {
        editor.update(() => {
            const root = $getRoot();

            // Split by double newlines for paragraphs
            const paragraphs = text.split(/\n\n+/);

            paragraphs.forEach((para) => {
                const p = $createParagraphNode();
                const lines = para.split('\n');

                lines.forEach((line, idx) => {
                    // Add line break for lines after the first
                    if (idx > 0) {
                        p.append($createLineBreakNode());
                    }
                    // Only add text if line is not empty
                    if (line.trim()) {
                        // Create OriginTextNode with 'ai' origin for color coding
                        p.append($createOriginTextNode(line, 'ai'));
                    }
                });

                // Append paragraph to end of document
                root.append(p);
            });

            // Move cursor to end
            root.selectEnd();

            resolve();
        }, { discrete: true });
    });
}

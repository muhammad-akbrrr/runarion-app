import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import { useEffect, useRef } from 'react';
import {
    TextNode,
    $getRoot,
    $getSelection,
    $isRangeSelection,
    LexicalNode,
    ElementNode,
    KEY_BACKSPACE_COMMAND,
    KEY_DELETE_COMMAND,
    INSERT_PARAGRAPH_COMMAND,
    $createParagraphNode,
    COMMAND_PRIORITY_HIGH,
    LexicalEditor,
    $getNodeByKey,
} from 'lexical';
import { $createOriginTextNode, OriginTextNode, $isOriginTextNode } from '../nodes/OriginTextNode';

// =================================================================
// TYPE DEFINITIONS
// =================================================================
interface InsertionInfo {
    offset: number;
    insertedText: string;
    textBefore: string;
    textAfter: string;
}

// =================================================================
// HELPER FUNCTIONS
// =================================================================

/**
 * Detect what text was inserted into a string by comparing before/after.
 * Uses longest common prefix/suffix to find the inserted portion.
 */
function detectInsertion(prevText: string, currentText: string): InsertionInfo | null {
    // Find the common prefix (text before insertion)
    let prefixEnd = 0;
    while (
        prefixEnd < prevText.length &&
        prefixEnd < currentText.length &&
        prevText[prefixEnd] === currentText[prefixEnd]
    ) {
        prefixEnd++;
    }

    // Find the common suffix (text after insertion)
    let suffixStart = prevText.length;
    let currentSuffixStart = currentText.length;
    while (
        suffixStart > prefixEnd &&
        currentSuffixStart > prefixEnd &&
        prevText[suffixStart - 1] === currentText[currentSuffixStart - 1]
    ) {
        suffixStart--;
        currentSuffixStart--;
    }

    // Calculate inserted text
    const insertedText = currentText.slice(prefixEnd, currentSuffixStart);

    if (insertedText.length === 0) return null;

    return {
        offset: prefixEnd,
        insertedText,
        textBefore: prevText.slice(0, prefixEnd),
        textAfter: prevText.slice(suffixStart),
    };
}

/**
 * Split an AI node into [ai-before, user-text, ai-after] nodes.
 * Uses queueMicrotask to avoid nested update issues.
 */
function queueNodeSplit(editor: LexicalEditor, nodeKey: string, info: InsertionInfo): void {
    queueMicrotask(() => {
        editor.update(
            () => {
                const node = $getNodeByKey(nodeKey);
                if (!$isOriginTextNode(node) || node.getOrigin() !== 'ai') return;

                const format = node.getFormat();
                const detail = node.getDetail();
                const style = node.getStyle();

                // Build replacement nodes
                const nodesToInsert: OriginTextNode[] = [];

                // Text before insertion keeps 'ai' origin
                if (info.textBefore) {
                    const beforeNode = $createOriginTextNode(info.textBefore, 'ai');
                    beforeNode.setFormat(format);
                    beforeNode.setDetail(detail);
                    beforeNode.setStyle(style);
                    nodesToInsert.push(beforeNode);
                }

                // Inserted text gets 'user' origin
                const userNode = $createOriginTextNode(info.insertedText, 'user');
                userNode.setFormat(format);
                userNode.setDetail(detail);
                userNode.setStyle(style);
                nodesToInsert.push(userNode);

                // Text after insertion keeps 'ai' origin
                if (info.textAfter) {
                    const afterNode = $createOriginTextNode(info.textAfter, 'ai');
                    afterNode.setFormat(format);
                    afterNode.setDetail(detail);
                    afterNode.setStyle(style);
                    nodesToInsert.push(afterNode);
                }

                // Replace original node with the new nodes
                const first = nodesToInsert[0];
                node.replace(first);
                let current = first;
                for (let i = 1; i < nodesToInsert.length; i++) {
                    current.insertAfter(nodesToInsert[i]);
                    current = nodesToInsert[i];
                }

                // Position cursor at end of user text
                userNode.selectEnd();
            },
            { tag: 'origin-tracking-split' }
        );
    });
}

/**
 * Plugin that handles origin tracking for text in the editor.
 *
 * 1. Converts plain TextNodes to OriginTextNodes with 'user' origin
 * 2. Intercepts text insertion into AI nodes and properly splits them
 * 3. Handles backspace/delete at origin boundaries
 * 4. Merges adjacent nodes with same origin to prevent fragmentation
 */
export function OriginTrackingPlugin(): null {
    const [editor] = useLexicalComposerContext();
    const hasRunInitialPassRef = useRef(false);

    useEffect(() => {
        // =================================================================
        // TRANSFORM 1: Convert plain TextNodes to OriginTextNodes
        // This handles pasted content, programmatic insertions, etc.
        // =================================================================
        const unregisterTextNodeTransform = editor.registerNodeTransform(TextNode, (node) => {
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

        // =================================================================
        // TRANSFORM 2: Merge adjacent OriginTextNodes with same origin
        // Prevents excessive node fragmentation over time
        // =================================================================
        const unregisterMergeTransform = editor.registerNodeTransform(OriginTextNode, (node) => {
            const prevSibling = node.getPreviousSibling();

            // Merge with previous sibling if same origin and format
            if (
                $isOriginTextNode(prevSibling) &&
                prevSibling.getOrigin() === node.getOrigin() &&
                prevSibling.getFormat() === node.getFormat() &&
                prevSibling.getStyle() === node.getStyle()
            ) {
                const mergedText = prevSibling.getTextContent() + node.getTextContent();
                prevSibling.setTextContent(mergedText);
                node.remove();
            }
        });

        // =================================================================
        // UPDATE LISTENER: Detect text insertion into AI nodes
        // This runs AFTER every editor update, comparing previous/current state
        // =================================================================
        const unregisterUpdateListener = editor.registerUpdateListener(
            ({ editorState, prevEditorState, tags }) => {
                // Skip if this update was from our own origin tracking split
                if (tags.has('origin-tracking-split')) return;

                // Read the current editor state
                editorState.read(() => {
                    // Get current selection
                    const selection = $getSelection();
                    if (!$isRangeSelection(selection) || !selection.isCollapsed()) return;

                    const anchorNode = selection.anchor.getNode();

                    // Only process if cursor is in an AI-origin node
                    if (!$isOriginTextNode(anchorNode) || anchorNode.getOrigin() !== 'ai') return;

                    const currentText = anchorNode.getTextContent();
                    const nodeKey = anchorNode.getKey();

                    // Get the same node from previous state to compare text
                    const prevNodeMap = prevEditorState._nodeMap;
                    const prevNode = prevNodeMap.get(nodeKey);

                    // Skip if node didn't exist before (new node) or isn't an OriginTextNode
                    if (!prevNode || !(prevNode instanceof OriginTextNode)) return;

                    const prevText = prevNode.__text;

                    // Detect if text was inserted (length increased)
                    if (currentText.length > prevText.length) {
                        const insertionInfo = detectInsertion(prevText, currentText);
                        if (insertionInfo) {
                            // Queue the split operation asynchronously to avoid nested updates
                            queueNodeSplit(editor, nodeKey, insertionInfo);
                        }
                    }
                });
            }
        );

        // =================================================================
        // COMMAND: Handle backspace at origin boundaries
        // Prevents merging of different-origin nodes during deletion
        // =================================================================
        const unregisterBackspaceCommand = editor.registerCommand(
            KEY_BACKSPACE_COMMAND,
            (event) => {
                const selection = $getSelection();
                if (!$isRangeSelection(selection) || !selection.isCollapsed()) {
                    return false; // Let default handling proceed for range selections
                }

                const anchor = selection.anchor;
                const anchorNode = anchor.getNode();

                // If at the start of a node, check the previous sibling
                if (anchor.offset === 0 && $isOriginTextNode(anchorNode)) {
                    const prevSibling = anchorNode.getPreviousSibling();

                    // If previous sibling is an AI node and current is user (or vice versa)
                    if ($isOriginTextNode(prevSibling) && prevSibling.getOrigin() !== anchorNode.getOrigin()) {
                        const prevText = prevSibling.getTextContent();

                        if (prevText.length > 1) {
                            // Delete last character of previous node
                            prevSibling.setTextContent(prevText.slice(0, -1));
                        } else {
                            // Remove the entire previous node if only one character
                            prevSibling.remove();
                        }

                        event?.preventDefault();
                        return true;
                    }
                }

                return false;
            },
            COMMAND_PRIORITY_HIGH
        );

        // =================================================================
        // COMMAND: Handle delete at origin boundaries
        // Prevents merging of different-origin nodes during forward deletion
        // =================================================================
        const unregisterDeleteCommand = editor.registerCommand(
            KEY_DELETE_COMMAND,
            (event) => {
                const selection = $getSelection();
                if (!$isRangeSelection(selection) || !selection.isCollapsed()) {
                    return false;
                }

                const anchor = selection.anchor;
                const anchorNode = anchor.getNode();

                // If at the end of a node, check the next sibling
                if ($isOriginTextNode(anchorNode)) {
                    const nodeText = anchorNode.getTextContent();

                    if (anchor.offset === nodeText.length) {
                        const nextSibling = anchorNode.getNextSibling();

                        // If next sibling has different origin
                        if ($isOriginTextNode(nextSibling) && nextSibling.getOrigin() !== anchorNode.getOrigin()) {
                            const nextText = nextSibling.getTextContent();

                            if (nextText.length > 1) {
                                // Delete first character of next node
                                nextSibling.setTextContent(nextText.slice(1));
                            } else {
                                // Remove the entire next node if only one character
                                nextSibling.remove();
                            }

                            event?.preventDefault();
                            return true;
                        }
                    }
                }

                return false;
            },
            COMMAND_PRIORITY_HIGH
        );

        // =================================================================
        // COMMAND: Handle Enter key to preserve origin when splitting paragraphs
        // Prevents AI-origin text from becoming user-origin after paragraph split
        // =================================================================
        const unregisterParagraphCommand = editor.registerCommand(
            INSERT_PARAGRAPH_COMMAND,
            () => {
                const selection = $getSelection();
                if (!$isRangeSelection(selection) || !selection.isCollapsed()) {
                    return false; // Let default handler proceed for range selections
                }

                const anchorNode = selection.anchor.getNode();

                // Only intercept if we're in an AI-origin node
                if (!$isOriginTextNode(anchorNode) || anchorNode.getOrigin() !== 'ai') {
                    return false; // Let default handler proceed for user text
                }

                const anchorOffset = selection.anchor.offset;
                const textContent = anchorNode.getTextContent();

                // Get formatting to preserve
                const format = anchorNode.getFormat();
                const detail = anchorNode.getDetail();
                const style = anchorNode.getStyle();

                // Text before cursor stays in current paragraph
                const textBefore = textContent.slice(0, anchorOffset);
                // Text after cursor goes to new paragraph
                const textAfter = textContent.slice(anchorOffset);

                // Update current node with text before cursor
                if (textBefore) {
                    anchorNode.setTextContent(textBefore);
                } else {
                    // If cursor at start, remove empty node
                    anchorNode.remove();
                }

                // Create new paragraph with text after cursor (preserving AI origin)
                const newParagraph = $createParagraphNode();
                if (textAfter) {
                    const newTextNode = $createOriginTextNode(textAfter, 'ai'); // Preserve origin!
                    newTextNode.setFormat(format);
                    newTextNode.setDetail(detail);
                    newTextNode.setStyle(style);
                    newParagraph.append(newTextNode);
                }

                // Insert new paragraph after current one
                const parentParagraph = anchorNode.getParent();
                if (parentParagraph) {
                    parentParagraph.insertAfter(newParagraph);
                }

                // Move cursor to start of new paragraph
                newParagraph.selectStart();

                return true; // We handled it
            },
            COMMAND_PRIORITY_HIGH
        );

        // =================================================================
        // INITIAL PASS: Convert any existing TextNodes on load
        // This catches nodes that were deserialized before transforms registered
        // =================================================================
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

        return () => {
            unregisterTextNodeTransform();
            unregisterMergeTransform();
            unregisterUpdateListener();
            unregisterBackspaceCommand();
            unregisterDeleteCommand();
            unregisterParagraphCommand();
        };
    }, [editor]);

    return null;
}

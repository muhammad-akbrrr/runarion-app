import { useEffect, useRef } from "react";
import { useLexicalComposerContext } from "@lexical/react/LexicalComposerContext";
import { $getRoot, $createParagraphNode } from "lexical";
import {
    HEADING,
    UNORDERED_LIST,
    ORDERED_LIST,
    QUOTE,
    BOLD_STAR,
    BOLD_UNDERSCORE,
    ITALIC_STAR,
    ITALIC_UNDERSCORE,
    STRIKETHROUGH,
    INLINE_CODE,
} from "@lexical/markdown";
import { $createOriginTextNode } from "../Nodes/OriginTextNode";

// Define supported transformers - exported for use by other plugins (e.g., InlineDiffPlugin)
export const SUPPORTED_TRANSFORMERS = [
    HEADING,
    UNORDERED_LIST,
    ORDERED_LIST,
    QUOTE,
    BOLD_STAR,
    BOLD_UNDERSCORE,
    ITALIC_STAR,
    ITALIC_UNDERSCORE,
    STRIKETHROUGH,
    INLINE_CODE,
];

interface ContentUpdatePluginProps {
    content: string;
    isStreaming: boolean;
}

/**
 * Check if content is valid Lexical JSON format
 * Lexical JSON has a root object with type === 'root'
 */
function isLexicalJSON(content: string): boolean {
    if (!content?.trim().startsWith("{")) return false;
    try {
        const parsed = JSON.parse(content);
        return parsed.root?.type === "root";
    } catch {
        return false;
    }
}

/**
 * Custom plugin to update editor content when chapter changes
 * Handles Lexical JSON (primary) and markdown (legacy) conversion
 */
export function ContentUpdatePlugin({
    content,
    isStreaming,
}: ContentUpdatePluginProps) {
    const [editor] = useLexicalComposerContext();
    const wasStreamingRef = useRef(false);
    const skipNextUpdateRef = useRef(false);
    const lastContentLengthRef = useRef(0);

    useEffect(() => {
        // Track when streaming ends - skip the next update to prevent flicker
        if (wasStreamingRef.current && !isStreaming) {
            console.log(
                "ContentUpdatePlugin: Streaming just ended, will skip next update",
            );
            skipNextUpdateRef.current = true;
        }
        wasStreamingRef.current = isStreaming;

        // Don't update content during streaming to avoid conflicts
        if (isStreaming) {
            console.log(
                "ContentUpdatePlugin: Skipping update during streaming",
            );
            return;
        }

        // Skip the update right after streaming ends (StreamingPlugin already rendered the content)
        if (skipNextUpdateRef.current) {
            console.log(
                "ContentUpdatePlugin: Skipping post-streaming update to prevent flicker",
            );
            skipNextUpdateRef.current = false;
            return;
        }

        console.log("ContentUpdatePlugin: Checking if content update needed", {
            contentLength: content?.length || 0,
            contentPreview: content?.substring(0, 50) + "...",
        });

        // Check if content is Lexical JSON (proper structure check)
        const isJSON = isLexicalJSON(content);

        // Get current content for comparison
        const currentContent = JSON.stringify(editor.getEditorState().toJSON());

        // For JSON content, compare directly to avoid unnecessary updates
        if (isJSON && currentContent === content) {
            console.log(
                "ContentUpdatePlugin: Content unchanged, skipping update",
            );
            return;
        }

        // Determine if this is a major change (chapter switch) or minor edit
        const previousLength = lastContentLengthRef.current;
        const newLength = content?.length || 0;
        const lengthDiff = Math.abs(newLength - previousLength);
        const isMajorChange =
            previousLength === 0 || lengthDiff > previousLength * 0.5;

        console.log("ContentUpdatePlugin: Updating editor content", {
            currentLength: currentContent.length,
            newLength: newLength,
            isMajorChange,
            format: isJSON ? "lexical-json" : "markdown/plaintext",
        });

        lastContentLengthRef.current = newLength;

        // Save scroll position before update
        const editorElement = editor.getRootElement();
        const scrollContainer =
            editorElement?.closest(".overflow-y-auto") ||
            editorElement?.parentElement;
        const savedScrollTop = scrollContainer?.scrollTop || 0;

        if (content && content.trim()) {
            if (isJSON) {
                // CRITICAL: Load from Lexical JSON OUTSIDE of editor.update()
                // This allows node transforms (TextNode → OriginTextNode) to run properly
                try {
                    const editorState = editor.parseEditorState(content);
                    editor.setEditorState(editorState);
                    console.log(
                        "ContentUpdatePlugin: Successfully loaded from Lexical JSON",
                    );

                    // Set cursor position after state is set
                    if (isMajorChange) {
                        setTimeout(() => {
                            editor.update(() => {
                                const root = $getRoot();
                                if (root.getChildrenSize() > 0) {
                                    const lastChild = root.getLastChild();
                                    if (lastChild) {
                                        lastChild.selectEnd();
                                    }
                                }
                            });
                        }, 10);
                    }
                } catch (error) {
                    console.error(
                        "ContentUpdatePlugin: Error parsing Lexical JSON, falling back to plain text:",
                        error,
                    );
                    // Fall through to plain text handling
                    loadAsPlainText(
                        editor,
                        content,
                        isMajorChange,
                    );
                }
            } else {
                // Plain text handling inside editor.update()
                loadAsPlainText(
                    editor,
                    content,
                    isMajorChange,
                );
            }
        } else {
            // Empty content - add empty paragraph inside editor.update()
            editor.update(() => {
                const root = $getRoot();
                root.clear();
                const paragraph = $createParagraphNode();
                root.append(paragraph);
            });
        }

        // Restore scroll position for minor edits
        if (!isMajorChange && scrollContainer) {
            setTimeout(() => {
                scrollContainer.scrollTop = savedScrollTop;
            }, 20);
        }
    }, [content, editor, isStreaming]);

    return null;
}

/**
 * Helper function to load plain text content into the editor
 * Uses OriginTextNode with 'user' origin for proper color coding support
 */
function loadAsPlainText(
    editor: any,
    content: string,
    isMajorChange: boolean,
) {
    editor.update(() => {
        const root = $getRoot();
        root.clear();

        // Split by double newlines for paragraphs
        const paragraphs = content.split(/\n\n+/);
        paragraphs.forEach((para, index) => {
            if (para.trim() || index === paragraphs.length - 1) {
                const p = $createParagraphNode();
                // Handle single newlines within paragraph
                const lines = para.split("\n");
                lines.forEach((line, lineIndex) => {
                    if (lineIndex > 0) {
                        // Use OriginTextNode for proper origin tracking
                        p.append($createOriginTextNode("\n", "user"));
                    }
                    if (line) {
                        p.append($createOriginTextNode(line, "user"));
                    }
                });
                root.append(p);
            }
        });

        console.log(
            "ContentUpdatePlugin: Loaded content as plain text with OriginTextNode",
        );

        // Set cursor to end on major changes
        if (isMajorChange) {
            setTimeout(() => {
                editor.update(() => {
                    const root = $getRoot();
                    if (root.getChildrenSize() > 0) {
                        const lastChild = root.getLastChild();
                        if (lastChild) {
                            lastChild.selectEnd();
                        }
                    }
                });
            }, 10);
        }
    });
}

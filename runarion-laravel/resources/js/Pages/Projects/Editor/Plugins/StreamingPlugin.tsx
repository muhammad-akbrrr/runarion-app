import { useEffect, useRef } from "react";
import { useLexicalComposerContext } from "@lexical/react/LexicalComposerContext";
import {
    $getRoot,
    $createParagraphNode,
    $isParagraphNode,
    ParagraphNode,
} from "lexical";
import { $createOriginTextNode } from "../Nodes/OriginTextNode";

interface StreamingPluginProps {
    isStreaming: boolean;
    streamingText: string;
    baseContent: string;
    isRegenerating?: boolean;
    onStreamingUpdate?: (fullContent: string) => void;
}

/**
 * Check if content is valid Lexical JSON format
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
 * Extract plain text from Lexical JSON for separator calculation
 */
function getPlainTextFromJSON(jsonContent: string): string {
    try {
        const parsed = JSON.parse(jsonContent);
        return extractTextFromNode(parsed.root);
    } catch {
        return jsonContent;
    }
}

function extractTextFromNode(node: any): string {
    if (!node) return "";
    if (node.type === "text") return node.text || "";
    if (node.children && Array.isArray(node.children)) {
        return node.children
            .map((child: any, index: number) => {
                const text = extractTextFromNode(child);
                if (
                    child.type === "paragraph" &&
                    index < node.children.length - 1
                ) {
                    return text + "\n\n";
                }
                return text;
            })
            .join("");
    }
    return "";
}

/**
 * Plugin to handle real-time streaming text updates from LLM
 * Combines base content with streaming text and renders in real-time
 * Properly handles paragraph breaks (newlines) for whitespace preservation
 */
export function StreamingPlugin({
    isStreaming,
    streamingText,
    baseContent,
    isRegenerating = false,
    onStreamingUpdate,
}: StreamingPluginProps) {
    const [editor] = useLexicalComposerContext();
    const lastStreamingTextRef = useRef<string>("");
    const isStreamingRef = useRef<boolean>(false);
    const baseContentAtStartRef = useRef<string>("");
    const baseContentRenderedRef = useRef<boolean>(false);
    // Track the current paragraph node we're appending to
    const currentParagraphRef = useRef<ParagraphNode | null>(null);
    // Track how much of the streaming text we've already rendered
    const renderedStreamingLengthRef = useRef<number>(0);

    useEffect(() => {
        // Track streaming state changes
        if (isStreaming !== isStreamingRef.current) {
            isStreamingRef.current = isStreaming;
            if (!isStreaming) {
                // Streaming ended, reset refs
                lastStreamingTextRef.current = "";
                baseContentAtStartRef.current = "";
                baseContentRenderedRef.current = false;
                currentParagraphRef.current = null;
                renderedStreamingLengthRef.current = 0;
                console.log("StreamingPlugin: Streaming ended");
            } else {
                // Streaming started - capture baseContent at this moment
                baseContentAtStartRef.current = baseContent || "";
                baseContentRenderedRef.current = false;
                currentParagraphRef.current = null;
                renderedStreamingLengthRef.current = 0;
                console.log(
                    "StreamingPlugin: Streaming started with baseContent:",
                    {
                        baseContentLength: baseContent?.length || 0,
                        baseContentPreview: baseContent?.substring(0, 50) || "",
                    },
                );
            }
        }

        if (
            isStreaming &&
            streamingText &&
            streamingText !== lastStreamingTextRef.current
        ) {
            lastStreamingTextRef.current = streamingText;

            // Use the baseContent captured at stream start to avoid race conditions
            const effectiveBaseContent =
                baseContentAtStartRef.current || baseContent || "";

            // Get plain text version for separator calculation
            const baseContentPlainText = isLexicalJSON(effectiveBaseContent)
                ? getPlainTextFromJSON(effectiveBaseContent)
                : effectiveBaseContent;

            // Calculate separator for full content notification
            let separator = "";
            if (baseContentPlainText) {
                if (
                    !baseContentPlainText.endsWith("\n") &&
                    !baseContentPlainText.endsWith(" ") &&
                    !streamingText.startsWith("\n") &&
                    !streamingText.startsWith(" ")
                ) {
                    separator = " ";
                }
            }

            const fullContent =
                baseContentPlainText + separator + streamingText;

            // Notify parent component of the streaming update
            if (onStreamingUpdate) {
                onStreamingUpdate(fullContent);
            }

            // FIRST TIME: Initialize editor with base content
            // Handle Lexical JSON OUTSIDE of editor.update() to avoid frozen node map error
            if (!baseContentRenderedRef.current) {
                if (
                    effectiveBaseContent &&
                    isLexicalJSON(effectiveBaseContent)
                ) {
                    // Load from Lexical JSON using setEditorState (outside update block)
                    try {
                        const editorState =
                            editor.parseEditorState(effectiveBaseContent);
                        editor.setEditorState(editorState);
                        console.log(
                            "StreamingPlugin: Loaded base content from Lexical JSON",
                        );

                        // Wait for node transforms to complete before reading state
                        // This ensures TextNode → OriginTextNode transforms have executed
                        queueMicrotask(() => {
                            editor.getEditorState().read(() => {
                                const root = $getRoot();
                                const lastChild = root.getLastChild();
                                if (lastChild && $isParagraphNode(lastChild)) {
                                    currentParagraphRef.current = lastChild;
                                }
                            });
                        });

                        baseContentRenderedRef.current = true;
                    } catch (error) {
                        console.error(
                            "StreamingPlugin: Error loading Lexical JSON:",
                            error,
                        );
                        // Fall through to plain text handling
                    }
                }

                // If not JSON or JSON failed, handle as plain text
                if (!baseContentRenderedRef.current) {
                    editor.update(
                        () => {
                            const root = $getRoot();
                            root.clear();

                            if (effectiveBaseContent) {
                                // Treat as plain text, split by paragraphs
                                const paragraphs =
                                    effectiveBaseContent.split(/\n\n+/);
                                paragraphs.forEach((para, index) => {
                                    if (
                                        para.trim() ||
                                        index === paragraphs.length - 1
                                    ) {
                                        const p = $createParagraphNode();
                                        // Handle single newlines within paragraph as line breaks
                                        const lines = para.split("\n");
                                        lines.forEach((line, lineIndex) => {
                                            if (lineIndex > 0) {
                                                p.append(
                                                    $createOriginTextNode(
                                                        "\n",
                                                        "user",
                                                    ),
                                                );
                                            }
                                            if (line) {
                                                p.append(
                                                    $createOriginTextNode(
                                                        line,
                                                        "user",
                                                    ),
                                                );
                                            }
                                        });
                                        root.append(p);
                                    }
                                });
                                console.log(
                                    "StreamingPlugin: Loaded base content as plain text with paragraph detection",
                                );
                            }

                            // Get the last paragraph to continue appending
                            const lastChild = root.getLastChild();
                            if (lastChild && $isParagraphNode(lastChild)) {
                                currentParagraphRef.current = lastChild;
                            }
                        },
                        { discrete: true },
                    );

                    baseContentRenderedRef.current = true;
                }
            }

            // INCREMENTAL: Only process new text since last update
            const newText = streamingText.slice(
                renderedStreamingLengthRef.current,
            );

            if (newText) {
                editor.update(
                    () => {
                        const root = $getRoot();

                        // Re-acquire reference to last paragraph (may have changed after setEditorState)
                        if (!currentParagraphRef.current) {
                            const lastChild = root.getLastChild();
                            if (lastChild && $isParagraphNode(lastChild)) {
                                currentParagraphRef.current = lastChild;
                            }
                        }

                        // Add separator if this is the first streaming text
                        const textToProcess =
                            renderedStreamingLengthRef.current === 0
                                ? separator + newText
                                : newText;

                        // Process text character by character to handle newlines properly
                        let currentText = "";

                        for (let i = 0; i < textToProcess.length; i++) {
                            const char = textToProcess[i];

                            if (char === "\n") {
                                // Flush current text to current paragraph
                                if (currentText) {
                                    if (!currentParagraphRef.current) {
                                        currentParagraphRef.current =
                                            $createParagraphNode();
                                        root.append(
                                            currentParagraphRef.current,
                                        );
                                    }
                                    currentParagraphRef.current.append(
                                        $createOriginTextNode(
                                            currentText,
                                            "ai",
                                        ),
                                    );
                                    currentText = "";
                                }

                                // ANY newline = new paragraph (simplified behavior)
                                currentParagraphRef.current =
                                    $createParagraphNode();
                                root.append(currentParagraphRef.current);
                            } else {
                                currentText += char;
                            }
                        }

                        // Flush remaining text
                        if (currentText) {
                            if (!currentParagraphRef.current) {
                                currentParagraphRef.current =
                                    $createParagraphNode();
                                root.append(currentParagraphRef.current);
                            }
                            currentParagraphRef.current.append(
                                $createOriginTextNode(currentText, "ai"),
                            );
                        }

                        renderedStreamingLengthRef.current =
                            streamingText.length;
                    },
                    { discrete: true },
                ); // Use discrete update to batch changes
            }
        }
    }, [
        isStreaming,
        streamingText,
        baseContent,
        isRegenerating,
        editor,
        onStreamingUpdate,
    ]);

    return null;
}

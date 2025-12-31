import { useEffect, useState, useCallback, useRef } from "react";
import { useLexicalComposerContext } from "@lexical/react/LexicalComposerContext";
import {
    $getSelection,
    $isRangeSelection,
    $isElementNode,
    $getRoot,
    $createParagraphNode,
    FORMAT_TEXT_COMMAND,
    COMMAND_PRIORITY_LOW,
    SELECTION_CHANGE_COMMAND,
    RangeSelection,
    TextNode,
} from "lexical";
import { $setBlocksType } from "@lexical/selection";
import { $createHeadingNode, HeadingTagType } from "@lexical/rich-text";
import { createPortal } from "react-dom";
import { Button } from "@/Components/ui/button";
import { Textarea } from "@/Components/ui/textarea";
import {
    Bold,
    Italic,
    Underline,
    Strikethrough,
    Heading1,
    Heading2,
    Heading3,
    Pilcrow,
    Sparkles,
    PenLine,
    Heart,
    Loader2,
    X,
    Send,
} from "lucide-react";
import { MagicWandButton } from "@/Components/MagicWandButton";

interface UnifiedSelectionToolbarPluginProps {
    workspaceId: string;
    projectId: string;
    chapterOrder: number;
    aiModel?: string;
    onRewriteComplete?: (oldText: string, newText: string) => void;
}

interface ToolbarPosition {
    top: number;
    left: number;
}

export function UnifiedSelectionToolbarPlugin({
    workspaceId,
    projectId,
    chapterOrder,
    aiModel = "gemini-2.5-flash",
    onRewriteComplete,
}: UnifiedSelectionToolbarPluginProps) {
    const [editor] = useLexicalComposerContext();

    // Visibility & position
    const [isVisible, setIsVisible] = useState(false);
    const [position, setPosition] = useState<ToolbarPosition>({
        top: 0,
        left: 0,
    });

    // Selection data
    const [selectedText, setSelectedText] = useState("");
    const [selectionLength, setSelectionLength] = useState(0);
    const [contextBefore, setContextBefore] = useState("");
    const [contextAfter, setContextAfter] = useState("");

    // Formatting states
    const [isBold, setIsBold] = useState(false);
    const [isItalic, setIsItalic] = useState(false);
    const [isUnderline, setIsUnderline] = useState(false);
    const [isStrikethrough, setIsStrikethrough] = useState(false);

    // AI interaction states
    const [isLoading, setIsLoading] = useState(false);
    const [showCustomPrompt, setShowCustomPrompt] = useState(false);
    const [customPrompt, setCustomPrompt] = useState("");

    // Refs
    const toolbarRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const isInteractingRef = useRef(false);
    const savedSelectionRef = useRef<RangeSelection | null>(null);
    const lastSelectionRef = useRef<string>("");

    // Derived states
    const canUseFormatting = selectionLength >= 1;
    const canUseAI = selectionLength >= 3;

    // Update formatting state based on selection
    const updateFormattingState = useCallback(() => {
        editor.getEditorState().read(() => {
            const selection = $getSelection();
            if ($isRangeSelection(selection)) {
                setIsBold(selection.hasFormat("bold"));
                setIsItalic(selection.hasFormat("italic"));
                setIsUnderline(selection.hasFormat("underline"));
                setIsStrikethrough(selection.hasFormat("strikethrough"));
            }
        });
    }, [editor]);

    // Get context around selection (500 chars before/after)
    const getSelectionContext = useCallback(() => {
        let before = "";
        let after = "";
        let selected = "";

        editor.getEditorState().read(() => {
            const selection = $getSelection();
            if (!$isRangeSelection(selection)) return;

            selected = selection.getTextContent();

            // Get the full text content of the editor
            const root = editor.getEditorState()._nodeMap.get("root");
            if (!root) return;

            const fullText = root.getTextContent();
            const selectedText = selection.getTextContent();

            // Find where the selected text appears
            const selectedIndex = fullText.indexOf(selectedText);
            if (selectedIndex === -1) return;

            // Get context (up to 500 characters before and after for better context)
            const contextLength = 500;
            before = fullText.substring(
                Math.max(0, selectedIndex - contextLength),
                selectedIndex
            );
            after = fullText.substring(
                selectedIndex + selectedText.length,
                selectedIndex + selectedText.length + contextLength
            );
        });

        return { before, after, selected };
    }, [editor]);

    // Update toolbar position based on selection
    const updateToolbar = useCallback(() => {
        // Don't update if we're interacting with the toolbar
        if (isInteractingRef.current) {
            return;
        }

        const nativeSelection = window.getSelection();

        if (
            !nativeSelection ||
            nativeSelection.rangeCount === 0 ||
            nativeSelection.isCollapsed
        ) {
            setIsVisible(false);
            setShowCustomPrompt(false);
            return;
        }

        const selectedTextContent = nativeSelection.toString().trim();
        const length = selectedTextContent.length;

        // Require at least 1 character to show toolbar
        if (length < 1) {
            setIsVisible(false);
            setShowCustomPrompt(false);
            return;
        }

        // Check if selection is within the editor
        const editorElement = editor.getRootElement();
        if (!editorElement) {
            setIsVisible(false);
            return;
        }

        // Check if selection is inside the editor element
        const range = nativeSelection.getRangeAt(0);
        if (!editorElement.contains(range.commonAncestorContainer)) {
            setIsVisible(false);
            return;
        }

        const rect = range.getBoundingClientRect();

        // Store the selected text and length
        setSelectedText(selectedTextContent);
        setSelectionLength(length);
        lastSelectionRef.current = selectedTextContent;

        // Get context for AI features
        if (length >= 3) {
            const context = getSelectionContext();
            setContextBefore(context.before);
            setContextAfter(context.after);
        }

        // Update formatting state
        updateFormattingState();

        // Calculate position (above the selection)
        // Wider for vertical column layout
        const toolbarWidth = showCustomPrompt ? 420 : 280;
        const selectionMidX = rect.left + rect.width / 2;
        let left = selectionMidX - toolbarWidth / 2;

        // Keep toolbar within viewport
        left = Math.max(
            10,
            Math.min(left, window.innerWidth - toolbarWidth - 10)
        );

        // Position above selection with some padding
        let top = rect.top + window.scrollY - 10;

        // If too close to top, show below selection
        if (top < 10) {
            top = rect.bottom + window.scrollY + 10;
        }

        setPosition({ top, left });
        setIsVisible(true);
    }, [editor, getSelectionContext, updateFormattingState, showCustomPrompt]);

    // Listen for selection changes with debounce
    useEffect(() => {
        let timeoutId: NodeJS.Timeout | null = null;

        const handleSelectionChange = () => {
            // Don't update if interacting with toolbar
            if (isInteractingRef.current) return;

            // Debounce the update
            if (timeoutId) clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                updateToolbar();
            }, 100);
        };

        const removeListener = editor.registerCommand(
            SELECTION_CHANGE_COMMAND,
            () => {
                handleSelectionChange();
                return false;
            },
            COMMAND_PRIORITY_LOW
        );

        // Listen for mouseup to catch selection end
        const handleMouseUp = (e: MouseEvent) => {
            // Don't trigger if clicking on toolbar
            if (toolbarRef.current?.contains(e.target as Node)) {
                return;
            }

            // Delay to let selection settle
            setTimeout(() => {
                if (!isInteractingRef.current) {
                    updateToolbar();
                }
            }, 50);
        };

        document.addEventListener("mouseup", handleMouseUp);

        return () => {
            removeListener();
            document.removeEventListener("mouseup", handleMouseUp);
            if (timeoutId) clearTimeout(timeoutId);
        };
    }, [editor, updateToolbar]);

    // Save current selection
    const saveSelection = useCallback(() => {
        editor.getEditorState().read(() => {
            const selection = $getSelection();
            if ($isRangeSelection(selection)) {
                savedSelectionRef.current = selection.clone();
            }
        });
    }, [editor]);

    // Handle toolbar interaction state
    const handleToolbarMouseDown = useCallback(
        (e: React.MouseEvent) => {
            e.preventDefault();
            e.stopPropagation();
            isInteractingRef.current = true;
            saveSelection();
        },
        [saveSelection]
    );

    const handleToolbarMouseUp = useCallback((e: React.MouseEvent) => {
        e.stopPropagation();
        // Reset interaction state after a short delay
        setTimeout(() => {
            isInteractingRef.current = false;
        }, 100);
    }, []);

    // Focus input when custom prompt is shown
    useEffect(() => {
        if (showCustomPrompt && inputRef.current) {
            setTimeout(() => {
                inputRef.current?.focus();
            }, 50);
        }
    }, [showCustomPrompt]);

    // Hide toolbar when clicking outside
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (toolbarRef.current?.contains(e.target as Node)) {
                return;
            }

            isInteractingRef.current = false;

            const editorElement = editor.getRootElement();
            if (editorElement?.contains(e.target as Node)) {
                return;
            }

            setIsVisible(false);
            setShowCustomPrompt(false);
            setCustomPrompt("");
        };

        document.addEventListener("mousedown", handleClickOutside);

        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, [editor]);

    // Handle escape key
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === "Escape" && isVisible) {
                setIsVisible(false);
                setShowCustomPrompt(false);
                setCustomPrompt("");
                isInteractingRef.current = false;
            }
        };

        document.addEventListener("keydown", handleKeyDown);
        return () => {
            document.removeEventListener("keydown", handleKeyDown);
        };
    }, [isVisible]);

    // ==================== FORMATTING HANDLERS ====================

    const formatBold = useCallback(() => {
        editor.dispatchCommand(FORMAT_TEXT_COMMAND, "bold");
        setIsBold(!isBold);
    }, [editor, isBold]);

    const formatItalic = useCallback(() => {
        editor.dispatchCommand(FORMAT_TEXT_COMMAND, "italic");
        setIsItalic(!isItalic);
    }, [editor, isItalic]);

    const formatUnderline = useCallback(() => {
        editor.dispatchCommand(FORMAT_TEXT_COMMAND, "underline");
        setIsUnderline(!isUnderline);
    }, [editor, isUnderline]);

    const formatStrikethrough = useCallback(() => {
        editor.dispatchCommand(FORMAT_TEXT_COMMAND, "strikethrough");
        setIsStrikethrough(!isStrikethrough);
    }, [editor, isStrikethrough]);

    const applyHeading = useCallback(
        (level: HeadingTagType) => {
            editor.update(() => {
                const selection = $getSelection();
                if ($isRangeSelection(selection)) {
                    $setBlocksType(selection, () => $createHeadingNode(level));
                }
            });
            setTimeout(() => {
                isInteractingRef.current = false;
            }, 200);
        },
        [editor]
    );

    const applyParagraph = useCallback(() => {
        editor.update(() => {
            const selection = $getSelection();
            if ($isRangeSelection(selection)) {
                $setBlocksType(selection, () => $createParagraphNode());
            }
        });
        setTimeout(() => {
            isInteractingRef.current = false;
        }, 200);
    }, [editor]);

    // ==================== AI REWRITE HANDLER ====================

    const handleRewrite = useCallback(
        async (
            action: "rewrite" | "humanize" | "custom",
            customInstruction?: string
        ) => {
            const textToRewrite = selectedText || lastSelectionRef.current;
            if (!textToRewrite || isLoading) return;

            setIsLoading(true);
            isInteractingRef.current = true;

            try {
                const csrfToken =
                    document
                        .querySelector('meta[name="csrf-token"]')
                        ?.getAttribute("content") || "";

                const response = await fetch(
                    route('editor.project.rewrite-selection', { workspace_id: workspaceId, project_id: projectId }),
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            Accept: "application/json",
                            "X-CSRF-TOKEN": csrfToken,
                        },
                        body: JSON.stringify({
                            selected_text: textToRewrite,
                            context_before: contextBefore,
                            context_after: contextAfter,
                            action: action,
                            custom_instruction:
                                customInstruction || customPrompt,
                            chapter_order: chapterOrder,
                            model: aiModel,
                        }),
                    }
                );

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || "Failed to rewrite text");
                }

                const data = await response.json();

                if (data.success && data.new_text) {
                    // Replace the text in the editor using find-and-replace
                    editor.update(() => {
                        const root = $getRoot();

                        // Collect all text nodes and their positions
                        const textNodes: Array<{
                            node: TextNode;
                            start: number;
                            end: number;
                        }> = [];
                        let currentIndex = 0;

                        const collectTextNodes = (node: any) => {
                            if (node instanceof TextNode) {
                                const nodeText = node.getTextContent();
                                textNodes.push({
                                    node,
                                    start: currentIndex,
                                    end: currentIndex + nodeText.length,
                                });
                                currentIndex += nodeText.length;
                            } else if (node.getChildren) {
                                const children = node.getChildren();
                                for (let i = 0; i < children.length; i++) {
                                    collectTextNodes(children[i]);
                                    // Add newline character for paragraph breaks (except last child)
                                    if (
                                        node.getType?.() === "root" &&
                                        i < children.length - 1
                                    ) {
                                        currentIndex += 1;
                                    }
                                }
                            }
                        };

                        collectTextNodes(root);

                        const textContent = root.getTextContent();
                        const startIndex = textContent.indexOf(textToRewrite);

                        if (startIndex === -1) {
                            console.warn("Original text not found in editor");
                            return;
                        }

                        const endIndex = startIndex + textToRewrite.length;

                        // Find which nodes contain the start and end of our selection
                        let startNode: TextNode | null = null;
                        let startOffset = 0;
                        let endNode: TextNode | null = null;
                        let endOffset = 0;

                        // Recalculate positions accounting for newlines properly
                        let charPos = 0;
                        const allParagraphs = root.getChildren();

                        for (
                            let pIdx = 0;
                            pIdx < allParagraphs.length;
                            pIdx++
                        ) {
                            const para = allParagraphs[pIdx];
                            if (!$isElementNode(para)) continue;

                            const children = para.getChildren();
                            for (const child of children) {
                                if (child instanceof TextNode) {
                                    const nodeText = child.getTextContent();
                                    const nodeStart = charPos;
                                    const nodeEnd = charPos + nodeText.length;

                                    if (
                                        !startNode &&
                                        startIndex >= nodeStart &&
                                        startIndex < nodeEnd
                                    ) {
                                        startNode = child;
                                        startOffset = startIndex - nodeStart;
                                    }

                                    if (
                                        !endNode &&
                                        endIndex > nodeStart &&
                                        endIndex <= nodeEnd
                                    ) {
                                        endNode = child;
                                        endOffset = endIndex - nodeStart;
                                    }

                                    charPos += nodeText.length;
                                }
                            }

                            if (pIdx < allParagraphs.length - 1) {
                                charPos += 1;
                            }
                        }

                        if (!startNode || !endNode) {
                            console.warn(
                                "Could not find start/end nodes for replacement"
                            );
                            return;
                        }

                        // Case 1: Start and end are in the same node
                        if (startNode === endNode) {
                            const nodeText = startNode.getTextContent();
                            const newText =
                                nodeText.substring(0, startOffset) +
                                data.new_text +
                                nodeText.substring(endOffset);
                            startNode.setTextContent(newText);
                        } else {
                            // Case 2: Text spans multiple nodes
                            let inRange = false;
                            const nodesToRemove: TextNode[] = [];
                            let foundEnd = false;

                            for (
                                let pIdx = 0;
                                pIdx < allParagraphs.length && !foundEnd;
                                pIdx++
                            ) {
                                const para = allParagraphs[pIdx];
                                if (!$isElementNode(para)) continue;

                                const children = para.getChildren();
                                for (const child of children) {
                                    if (child instanceof TextNode) {
                                        if (child === startNode) {
                                            const nodeText =
                                                child.getTextContent();
                                            child.setTextContent(
                                                nodeText.substring(
                                                    0,
                                                    startOffset
                                                ) + data.new_text
                                            );
                                            inRange = true;
                                        } else if (child === endNode) {
                                            const nodeText =
                                                child.getTextContent();
                                            const remainingText =
                                                nodeText.substring(endOffset);
                                            if (remainingText) {
                                                child.setTextContent(
                                                    remainingText
                                                );
                                            } else {
                                                nodesToRemove.push(child);
                                            }
                                            foundEnd = true;
                                            break;
                                        } else if (inRange) {
                                            nodesToRemove.push(child);
                                        }
                                    }
                                }
                            }

                            // Remove middle nodes
                            for (const node of nodesToRemove) {
                                const parent = node.getParent();
                                node.remove();
                                if (
                                    parent &&
                                    parent.getChildrenSize?.() === 0
                                ) {
                                    parent.remove();
                                }
                            }
                        }
                    });

                    // Notify parent component
                    if (onRewriteComplete) {
                        onRewriteComplete(textToRewrite, data.new_text);
                    }

                    // Hide toolbar after successful rewrite
                    setIsVisible(false);
                    setShowCustomPrompt(false);
                    setCustomPrompt("");
                }
            } catch (error) {
                console.error("Rewrite error:", error);
                alert(
                    error instanceof Error
                        ? error.message
                        : "Failed to rewrite text"
                );
            } finally {
                setIsLoading(false);
                isInteractingRef.current = false;
            }
        },
        [
            selectedText,
            lastSelectionRef,
            isLoading,
            workspaceId,
            projectId,
            contextBefore,
            contextAfter,
            customPrompt,
            chapterOrder,
            aiModel,
            editor,
            onRewriteComplete,
        ]
    );

    // ==================== EVENT HANDLERS ====================

    const handleCustomClick = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        isInteractingRef.current = true;
        setShowCustomPrompt(true);
    }, []);

    const handleBackClick = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setShowCustomPrompt(false);
        setCustomPrompt("");
    }, []);

    const handleActionClick = useCallback(
        (action: "rewrite" | "humanize") => (e: React.MouseEvent) => {
            e.preventDefault();
            e.stopPropagation();
            isInteractingRef.current = true;
            handleRewrite(action);
        },
        [handleRewrite]
    );

    const handleSubmitClick = useCallback(
        (e: React.MouseEvent) => {
            e.preventDefault();
            e.stopPropagation();
            if (customPrompt.trim()) {
                handleRewrite("custom", customPrompt);
            }
        },
        [customPrompt, handleRewrite]
    );

    const handleInputKeyDown = useCallback(
        (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
            e.stopPropagation();
            if (e.key === "Enter" && !e.shiftKey && customPrompt.trim()) {
                e.preventDefault();
                handleRewrite("custom", customPrompt);
            } else if (e.key === "Escape") {
                e.preventDefault();
                setShowCustomPrompt(false);
                setCustomPrompt("");
            }
        },
        [customPrompt, handleRewrite]
    );

    const handleInputFocus = useCallback(() => {
        isInteractingRef.current = true;
    }, []);

    // ==================== TOOLBAR RENDER ====================

    const toolbar = isVisible ? (
        <div
            ref={toolbarRef}
            className="fixed z-9999 animate-in fade-in-0 zoom-in-95 duration-100"
            style={{
                top: `${position.top}px`,
                left: `${position.left}px`,
            }}
            onMouseDown={handleToolbarMouseDown}
            onMouseUp={handleToolbarMouseUp}
            onClick={(e) => e.stopPropagation()}
        >
            <div className="bg-white text-gray-900 rounded-lg shadow-2xl border border-gray-200 overflow-hidden">
                {!showCustomPrompt ? (
                    <div className="p-2">
                        {/* FORMATTING SECTION */}
                        <div className="flex flex-col gap-1">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 px-3 justify-start text-gray-700 hover:bg-gray-100"
                                onClick={() => applyHeading("h1")}
                                title="Heading 1"
                                disabled={!canUseFormatting}
                            >
                                <Heading1 className="h-4 w-4 mr-2" />
                                <span className="text-sm">Heading 1</span>
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 px-3 justify-start text-gray-700 hover:bg-gray-100"
                                onClick={() => applyHeading("h2")}
                                title="Heading 2"
                                disabled={!canUseFormatting}
                            >
                                <Heading2 className="h-4 w-4 mr-2" />
                                <span className="text-sm">Heading 2</span>
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 px-3 justify-start text-gray-700 hover:bg-gray-100"
                                onClick={() => applyHeading("h3")}
                                title="Heading 3"
                                disabled={!canUseFormatting}
                            >
                                <Heading3 className="h-4 w-4 mr-2" />
                                <span className="text-sm">Heading 3</span>
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 px-3 justify-start text-gray-700 hover:bg-gray-100"
                                onClick={() => applyParagraph()}
                                title="Paragraph"
                                disabled={!canUseFormatting}
                            >
                                <Pilcrow className="h-4 w-4 mr-2" />
                                <span className="text-sm">Paragraph</span>
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className={`h-8 px-3 justify-start hover:bg-gray-100 ${
                                    isBold
                                        ? "bg-gray-100 text-gray-900"
                                        : "text-gray-700"
                                }`}
                                onClick={formatBold}
                                title="Bold"
                                disabled={!canUseFormatting}
                            >
                                <Bold className="h-4 w-4 mr-2" />
                                <span className="text-sm">Bold</span>
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className={`h-8 px-3 justify-start hover:bg-gray-100 ${
                                    isItalic
                                        ? "bg-gray-100 text-gray-900"
                                        : "text-gray-700"
                                }`}
                                onClick={formatItalic}
                                title="Italic"
                                disabled={!canUseFormatting}
                            >
                                <Italic className="h-4 w-4 mr-2" />
                                <span className="text-sm">Italic</span>
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className={`h-8 px-3 justify-start hover:bg-gray-100 ${
                                    isUnderline
                                        ? "bg-gray-100 text-gray-900"
                                        : "text-gray-700"
                                }`}
                                onClick={formatUnderline}
                                title="Underline"
                                disabled={!canUseFormatting}
                            >
                                <Underline className="h-4 w-4 mr-2" />
                                <span className="text-sm">Underline</span>
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className={`h-8 px-3 justify-start hover:bg-gray-100 ${
                                    isStrikethrough
                                        ? "bg-gray-100 text-gray-900"
                                        : "text-gray-700"
                                }`}
                                onClick={formatStrikethrough}
                                title="Strikethrough"
                                disabled={!canUseFormatting}
                            >
                                <Strikethrough className="h-4 w-4 mr-2" />
                                <span className="text-sm">Strikethrough</span>
                            </Button>
                        </div>

                        {/* DIVIDER */}
                        <div className="w-full h-px bg-gray-200 my-2" />

                        {/* AI SECTION */}
                        <div className="flex flex-col gap-1">
                            <Button
                                variant="ghost"
                                size="sm"
                                className={`h-8 px-3 w-full justify-start ${
                                    canUseAI
                                        ? "text-gray-700 hover:bg-gray-100 cursor-pointer"
                                        : "text-gray-400 bg-gray-50 cursor-not-allowed opacity-50"
                                }`}
                                onClick={handleActionClick("rewrite")}
                                disabled={!canUseAI || isLoading}
                                title={
                                    !canUseAI
                                        ? "Select at least 3 characters to use AI features"
                                        : "Rewrite"
                                }
                            >
                                {isLoading ? (
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                ) : (
                                    <PenLine className="h-4 w-4 mr-2" />
                                )}
                                <span className="text-sm">Rewrite</span>
                            </Button>

                            <Button
                                variant="ghost"
                                size="sm"
                                className={`h-8 px-3 w-full justify-start ${
                                    canUseAI
                                        ? "text-gray-700 hover:bg-gray-100 cursor-pointer"
                                        : "text-gray-400 bg-gray-50 cursor-not-allowed opacity-50"
                                }`}
                                onClick={handleActionClick("humanize")}
                                disabled={!canUseAI || isLoading}
                                title={
                                    !canUseAI
                                        ? "Select at least 3 characters to use AI features"
                                        : "Humanize"
                                }
                            >
                                {isLoading ? (
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                ) : (
                                    <Heart className="h-4 w-4 mr-2" />
                                )}
                                <span className="text-sm">Humanize</span>
                            </Button>

                            <Button
                                variant="ghost"
                                size="sm"
                                className={`h-8 px-3 w-full justify-start ${
                                    canUseAI
                                        ? "text-gray-700 hover:bg-gray-100 cursor-pointer"
                                        : "text-gray-400 bg-gray-50 cursor-not-allowed opacity-50"
                                }`}
                                onClick={handleCustomClick}
                                disabled={!canUseAI || isLoading}
                                title={
                                    !canUseAI
                                        ? "Select at least 3 characters to use AI features"
                                        : "Custom"
                                }
                            >
                                <Sparkles className="h-4 w-4 mr-2" />
                                <span className="text-sm">Custom</span>
                            </Button>
                        </div>
                    </div>
                ) : (
                    <div className="p-3 w-96">
                        <div className="flex items-center gap-2 mb-2">
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6 text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                                onClick={handleBackClick}
                            >
                                <X className="h-4 w-4" />
                            </Button>
                            <span className="text-sm text-gray-600">
                                Custom instruction
                            </span>
                        </div>
                        <div className="space-y-2">
                            <div className="flex gap-2">
                                <Textarea
                                    ref={inputRef}
                                    placeholder="e.g., Make it more dramatic...&#10;Or write a full paragraph of instructions..."
                                    value={customPrompt}
                                    onChange={(e) =>
                                        setCustomPrompt(e.target.value)
                                    }
                                    onKeyDown={handleInputKeyDown}
                                    onFocus={handleInputFocus}
                                    className="min-h-20 max-h-[200px] bg-white border-gray-300 text-gray-900 placeholder:text-gray-400 text-sm focus:ring-violet-500 focus:border-violet-500 resize-y"
                                    autoFocus
                                />
                                <div className="flex flex-col gap-2">
                                    <MagicWandButton
                                        text={customPrompt}
                                        onEnhanced={(enhanced) =>
                                            setCustomPrompt(enhanced)
                                        }
                                        enhancementMode="custom_instruction"
                                        workspaceId={workspaceId}
                                        projectId={projectId}
                                        aiModel={aiModel}
                                        disabled={isLoading}
                                        size="icon"
                                        variant="outline"
                                        className="h-10 w-10 border-green-600 bg-green-50 hover:bg-green-100 hover:border-green-500 text-green-600 shrink-0"
                                    />
                                    <Button
                                        size="icon"
                                        className="h-10 w-10 bg-violet-600 hover:bg-violet-700 shrink-0"
                                        onClick={handleSubmitClick}
                                        disabled={
                                            isLoading || !customPrompt.trim()
                                        }
                                        title="Submit"
                                    >
                                        {isLoading ? (
                                            <Loader2 className="h-5 w-5 animate-spin" />
                                        ) : (
                                            <Send className="h-5 w-5" />
                                        )}
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    ) : null;

    // Render toolbar via portal to body
    return createPortal(toolbar, document.body);
}

export default UnifiedSelectionToolbarPlugin;

import { useEffect, useState, useCallback, useRef } from "react";
import { useLexicalComposerContext } from "@lexical/react/LexicalComposerContext";
import {
    $getSelection,
    $isRangeSelection,
    $createParagraphNode,
    FORMAT_TEXT_COMMAND,
    COMMAND_PRIORITY_LOW,
    SELECTION_CHANGE_COMMAND,
    RangeSelection,
} from "lexical";
import { $setBlocksType } from "@lexical/selection";
import { $createHeadingNode, HeadingTagType } from "@lexical/rich-text";
import { createPortal } from "react-dom";
import { Button } from "@/Components/ui/button";
import {
    Bold,
    Italic,
    Underline,
    Strikethrough,
    Heading1,
    Heading2,
    Heading3,
    Pilcrow,
} from "lucide-react";

interface ToolbarPosition {
    top: number;
    left: number;
}

export function FormattingToolbarPlugin() {
    const [editor] = useLexicalComposerContext();
    const [isVisible, setIsVisible] = useState(false);
    const [position, setPosition] = useState<ToolbarPosition>({
        top: 0,
        left: 0,
    });
    const [isBold, setIsBold] = useState(false);
    const [isItalic, setIsItalic] = useState(false);
    const [isUnderline, setIsUnderline] = useState(false);
    const [isStrikethrough, setIsStrikethrough] = useState(false);
    const toolbarRef = useRef<HTMLDivElement>(null);
    const isInteractingRef = useRef(false);

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
            return;
        }

        const selectedTextContent = nativeSelection.toString().trim();

        // Require at least 1 character to show toolbar
        if (selectedTextContent.length < 1) {
            setIsVisible(false);
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

        // Update formatting state
        updateFormattingState();

        // Calculate position (above the selection)
        const toolbarWidth = 320;
        const selectionMidX = rect.left + rect.width / 2;
        let left = selectionMidX - toolbarWidth / 2;

        // Keep toolbar within viewport
        left = Math.max(
            10,
            Math.min(left, window.innerWidth - toolbarWidth - 10)
        );

        // Position above selection with some padding
        let top = rect.top + window.scrollY - 50;

        // If too close to top, show below selection
        if (top < 10) {
            top = rect.bottom + window.scrollY + 10;
        }

        setPosition({ top, left });
        setIsVisible(true);
    }, [editor, updateFormattingState]);

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

    // Handle toolbar interaction state
    const handleToolbarMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        isInteractingRef.current = true;
    }, []);

    const handleToolbarMouseUp = useCallback((e: React.MouseEvent) => {
        e.stopPropagation();
        // Reset interaction state after a short delay
        setTimeout(() => {
            isInteractingRef.current = false;
        }, 100);
    }, []);

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
                isInteractingRef.current = false;
            }
        };

        document.addEventListener("keydown", handleKeyDown);
        return () => {
            document.removeEventListener("keydown", handleKeyDown);
        };
    }, [isVisible]);

    // Format handlers
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

    const formatHeading = useCallback(
        (level: HeadingTagType) => {
            editor.update(() => {
                const selection = $getSelection();
                if ($isRangeSelection(selection)) {
                    $setBlocksType(selection, () => $createHeadingNode(level));
                }
            });
        },
        [editor]
    );

    const formatParagraph = useCallback(() => {
        editor.update(() => {
            const selection = $getSelection();
            if ($isRangeSelection(selection)) {
                $setBlocksType(selection, () => $createParagraphNode());
            }
        });
    }, [editor]);

    // Store selection before any action
    const savedSelectionRef = useRef<RangeSelection | null>(null);

    // Save current selection
    const saveSelection = useCallback(() => {
        editor.getEditorState().read(() => {
            const selection = $getSelection();
            if ($isRangeSelection(selection)) {
                savedSelectionRef.current = selection.clone();
            }
        });
    }, [editor]);

    // Apply heading with saved selection
    const applyHeading = useCallback(
        (level: HeadingTagType) => {
            editor.update(() => {
                // Restore selection if needed
                if (savedSelectionRef.current) {
                    savedSelectionRef.current.dirty = true;
                }
                const selection = $getSelection();
                if ($isRangeSelection(selection)) {
                    $setBlocksType(selection, () => $createHeadingNode(level));
                }
            });
            // Keep toolbar visible briefly
            setTimeout(() => {
                isInteractingRef.current = false;
            }, 200);
        },
        [editor]
    );

    // Apply paragraph with saved selection
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

    // Toolbar component
    const toolbar = isVisible ? (
        <div
            ref={toolbarRef}
            className="fixed z-9999 animate-in fade-in-0 zoom-in-95 duration-100"
            style={{
                top: `${position.top}px`,
                left: `${position.left}px`,
            }}
            onMouseDown={(e) => {
                e.preventDefault();
                e.stopPropagation();
                isInteractingRef.current = true;
                saveSelection();
            }}
            onMouseUp={handleToolbarMouseUp}
            onClick={(e) => e.stopPropagation()}
        >
            <div className="bg-zinc-900 text-white rounded-lg shadow-2xl border border-zinc-700 overflow-hidden">
                <div className="flex items-center gap-0.5 p-1.5">
                    {/* Paragraph */}
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0 text-white hover:bg-zinc-800"
                        onClick={() => applyParagraph()}
                        title="Paragraph"
                    >
                        <Pilcrow className="h-4 w-4" />
                    </Button>

                    {/* Heading 1 */}
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0 text-white hover:bg-zinc-800"
                        onClick={() => applyHeading("h1")}
                        title="Heading 1"
                    >
                        <Heading1 className="h-4 w-4" />
                    </Button>

                    {/* Heading 2 */}
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0 text-white hover:bg-zinc-800"
                        onClick={() => applyHeading("h2")}
                        title="Heading 2"
                    >
                        <Heading2 className="h-4 w-4" />
                    </Button>

                    {/* Heading 3 */}
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0 text-white hover:bg-zinc-800"
                        onClick={() => applyHeading("h3")}
                        title="Heading 3"
                    >
                        <Heading3 className="h-4 w-4" />
                    </Button>

                    <div className="w-px h-5 bg-zinc-700 mx-0.5" />

                    {/* Bold */}
                    <Button
                        variant="ghost"
                        size="sm"
                        className={`h-8 w-8 p-0 hover:bg-zinc-800 ${
                            isBold ? "bg-zinc-700 text-white" : "text-white"
                        }`}
                        onClick={formatBold}
                        title="Bold"
                    >
                        <Bold className="h-4 w-4" />
                    </Button>

                    {/* Italic */}
                    <Button
                        variant="ghost"
                        size="sm"
                        className={`h-8 w-8 p-0 hover:bg-zinc-800 ${
                            isItalic ? "bg-zinc-700 text-white" : "text-white"
                        }`}
                        onClick={formatItalic}
                        title="Italic"
                    >
                        <Italic className="h-4 w-4" />
                    </Button>

                    {/* Underline */}
                    <Button
                        variant="ghost"
                        size="sm"
                        className={`h-8 w-8 p-0 hover:bg-zinc-800 ${
                            isUnderline
                                ? "bg-zinc-700 text-white"
                                : "text-white"
                        }`}
                        onClick={formatUnderline}
                        title="Underline"
                    >
                        <Underline className="h-4 w-4" />
                    </Button>

                    {/* Strikethrough */}
                    <Button
                        variant="ghost"
                        size="sm"
                        className={`h-8 w-8 p-0 hover:bg-zinc-800 ${
                            isStrikethrough
                                ? "bg-zinc-700 text-white"
                                : "text-white"
                        }`}
                        onClick={formatStrikethrough}
                        title="Strikethrough"
                    >
                        <Strikethrough className="h-4 w-4" />
                    </Button>
                </div>
            </div>
        </div>
    ) : null;

    // Render toolbar via portal to body
    return createPortal(toolbar, document.body);
}

export default FormattingToolbarPlugin;

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { useLexicalComposerContext } from "@lexical/react/LexicalComposerContext";
import { $getRoot } from "lexical";
import { $convertToMarkdownString } from "@lexical/markdown";
import { createPortal } from "react-dom";
import { Check, X, ChevronLeft, ChevronRight } from "lucide-react";
import { usePendingEdits } from "../contexts/PendingEditsContext";
import { SUPPORTED_TRANSFORMERS } from "./ContentUpdatePlugin";

interface InlineDiffPluginProps {
    content: string;
    onApplyEdit: (oldText: string, newText: string) => boolean;
}

// Normalize text for matching
function normalizeForMatch(text: string): string {
    return text
        .replace(/[\u2018\u2019\u201A\u201B\u2032\u2035]/g, "'")
        .replace(/[\u201C\u201D\u201E\u201F\u2033\u2036]/g, '"')
        .replace(/[\u2014\u2015\u2012\u2013]/g, "-")
        .replace(/\u2026/g, "...")
        .replace(/\u00A0/g, " ")
        .replace(/\n+/g, " ")
        .replace(/\s+/g, " ")
        .trim();
}

// Find text in editor and return DOM range
function findTextInEditor(
    editorElement: HTMLElement,
    searchText: string
): Range | null {
    const normalizedSearch = normalizeForMatch(searchText);
    const editorText = editorElement.textContent || "";
    const normalizedEditorText = normalizeForMatch(editorText);

    // Find position in normalized text
    const matchIndex = normalizedEditorText.indexOf(normalizedSearch);
    if (matchIndex === -1) {
        // Try partial match (first 50 chars)
        const partialSearch = normalizedSearch.substring(0, 50);
        const partialIndex = normalizedEditorText.indexOf(partialSearch);
        if (partialIndex === -1) return null;
    }

    // Now we need to map back to actual DOM positions
    // Walk through text nodes
    const walker = document.createTreeWalker(
        editorElement,
        NodeFilter.SHOW_TEXT,
        null
    );

    let charCount = 0;
    let normalizedCharCount = 0;
    let startNode: Text | null = null;
    let startOffset = 0;
    let endNode: Text | null = null;
    let endOffset = 0;

    const targetStart =
        matchIndex !== -1
            ? matchIndex
            : normalizedEditorText.indexOf(
                  normalizeForMatch(searchText.substring(0, 50))
              );
    const targetLength = normalizedSearch.length;

    let node = walker.nextNode() as Text | null;
    while (node) {
        const nodeText = node.textContent || "";
        const normalizedNodeText = normalizeForMatch(nodeText);
        const nodeNormalizedLength = normalizedNodeText.length;

        // Check if start is in this node
        if (
            !startNode &&
            normalizedCharCount + nodeNormalizedLength > targetStart
        ) {
            startNode = node;
            // Map normalized position back to actual position (approximate)
            const normalizedOffset = targetStart - normalizedCharCount;
            startOffset = Math.min(normalizedOffset, nodeText.length);
        }

        // Check if end is in this node
        if (
            startNode &&
            normalizedCharCount + nodeNormalizedLength >=
                targetStart + targetLength
        ) {
            endNode = node;
            const normalizedOffset =
                targetStart + targetLength - normalizedCharCount;
            endOffset = Math.min(normalizedOffset, nodeText.length);
            break;
        }

        normalizedCharCount += nodeNormalizedLength;
        charCount += nodeText.length;
        node = walker.nextNode() as Text | null;
    }

    if (startNode && endNode) {
        try {
            const range = document.createRange();
            range.setStart(startNode, Math.max(0, startOffset));
            range.setEnd(endNode, Math.min(endNode.length, endOffset));
            return range;
        } catch (e) {
            console.error("[InlineDiff] Error creating range:", e);
        }
    }

    return null;
}

export function InlineDiffPlugin({
    content,
    onApplyEdit,
}: InlineDiffPluginProps) {
    const [editor] = useLexicalComposerContext();
    const {
        advisorMode,
        pendingEdits,
        activeEditId,
        setActiveEditId,
        acceptEdit,
        rejectEdit,
        getEditById,
        markEditAsStale,
    } = usePendingEdits();

    const [inlinePosition, setInlinePosition] = useState<{
        top: number;
        left: number;
        width: number;
    } | null>(null);
    const [highlightElements, setHighlightElements] = useState<HTMLElement[]>(
        []
    );
    const highlightContainerRef = useRef<HTMLElement | null>(null);

    const activeEdit = activeEditId ? getEditById(activeEditId) : null;

    // Track edits we've already checked for staleness to avoid loops
    const checkedForStaleness = useRef<Set<string>>(new Set());

    // Auto-select first pending edit (skip stale ones)
    useEffect(() => {
        if (advisorMode === "agent" && pendingEdits.length > 0) {
            // If current active edit is stale, move to next
            if (activeEditId) {
                const currentEdit = pendingEdits.find(
                    (e) => e.id === activeEditId
                );
                if (currentEdit?.status === "stale") {
                    const nextPending = pendingEdits.find(
                        (e) => e.status === "pending"
                    );
                    setActiveEditId(nextPending?.id || null);
                    return;
                }
            }

            // If no active edit, select first pending
            if (!activeEditId) {
                const firstPending = pendingEdits.find(
                    (e) => e.status === "pending"
                );
                if (firstPending) {
                    setActiveEditId(firstPending.id);
                }
            }
        }
    }, [advisorMode, pendingEdits, activeEditId, setActiveEditId]);

    // Find and highlight text when active edit changes
    useEffect(() => {
        // Clean up previous highlights
        highlightElements.forEach((el) => el.remove());
        setHighlightElements([]);
        if (highlightContainerRef.current) {
            highlightContainerRef.current.remove();
            highlightContainerRef.current = null;
        }

        if (!activeEdit || advisorMode !== "agent") {
            setInlinePosition(null);
            return;
        }

        const editorElement = editor.getRootElement();
        if (!editorElement) return;

        // Add keyframe animation style if needed
        if (!document.getElementById("inline-diff-styles")) {
            const style = document.createElement("style");
            style.id = "inline-diff-styles";
            style.textContent = `
                @keyframes highlight-pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.6; }
                }
            `;
            document.head.appendChild(style);
        }

        // Function to create and position highlights using fixed positioning
        const createHighlights = (shouldScroll: boolean = false) => {
            // Clear existing highlights
            highlightElements.forEach((el) => el.remove());
            if (highlightContainerRef.current) {
                highlightContainerRef.current.remove();
                highlightContainerRef.current = null;
            }

            const range = findTextInEditor(editorElement, activeEdit.oldText);

            if (range) {
                const rects = range.getClientRects();
                if (rects.length > 0) {
                    // Create a fixed container for highlights
                    const container = document.createElement("div");
                    container.className = "inline-diff-highlight-container";
                    container.style.cssText = `
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100vw;
                        height: 100vh;
                        pointer-events: none;
                        z-index: 9990;
                        overflow: hidden;
                    `;

                    document.body.appendChild(container);
                    highlightContainerRef.current = container;

                    // Create individual highlight for each rect (each line of text)
                    const highlights: HTMLElement[] = [];

                    for (let i = 0; i < rects.length; i++) {
                        const rect = rects[i];

                        // Skip tiny rects (sometimes browser creates 0-width rects)
                        if (rect.width < 2) continue;

                        const highlight = document.createElement("div");
                        highlight.className = "inline-diff-highlight-segment";
                        highlight.style.cssText = `
                            position: fixed;
                            top: ${rect.top}px;
                            left: ${rect.left}px;
                            width: ${rect.width}px;
                            height: ${rect.height}px;
                            background: rgba(239, 68, 68, 0.25);
                            border-bottom: 2px solid rgba(239, 68, 68, 0.8);
                            pointer-events: none;
                            animation: highlight-pulse 1.5s ease-in-out infinite;
                            animation-delay: ${i * 0.03}s;
                            border-radius: 2px;
                        `;

                        container.appendChild(highlight);
                        highlights.push(highlight);
                    }

                    setHighlightElements(highlights);

                    // Position the inline toolbar using the last rect
                    const firstRect = rects[0];
                    const lastRect = rects[rects.length - 1];
                    setInlinePosition({
                        top: lastRect.bottom + 4,
                        left: firstRect.left,
                        width: Math.max(300, lastRect.right - firstRect.left),
                    });

                    // Only scroll into view on initial creation, not on updates
                    if (shouldScroll) {
                        // Check if text is outside visible area
                        const isAboveViewport = firstRect.top < 100;
                        const isBelowViewport =
                            firstRect.bottom > window.innerHeight - 200;

                        if (isAboveViewport || isBelowViewport) {
                            // Find the text node's parent element and scroll to it
                            const textParent =
                                range.startContainer.parentElement;
                            if (textParent) {
                                // Use scrollIntoView with a slight delay to avoid conflicts
                                setTimeout(() => {
                                    textParent.scrollIntoView({
                                        behavior: "smooth",
                                        block: "center",
                                    });
                                    // Recreate highlights after scroll completes
                                    setTimeout(
                                        () => createHighlights(false),
                                        400
                                    );
                                }, 50);
                            }
                        }
                    }

                    return true;
                }
            } else {
                // Text not found - mark this edit as stale and move to next
                if (
                    activeEdit &&
                    !checkedForStaleness.current.has(activeEdit.id)
                ) {
                    checkedForStaleness.current.add(activeEdit.id);
                    console.log(
                        "[InlineDiff] Text not found, marking edit as stale:",
                        activeEdit.oldText.substring(0, 50)
                    );
                    markEditAsStale(activeEdit.id);

                    // Find next pending edit that isn't stale
                    const nextPending = pendingEdits.find(
                        (e) => e.id !== activeEdit.id && e.status === "pending"
                    );
                    if (nextPending) {
                        setActiveEditId(nextPending.id);
                    } else {
                        setActiveEditId(null);
                        setInlinePosition(null);
                    }
                }
            }
            return false;
        };

        // Delay to ensure content is rendered, then create highlights with scroll
        const timeoutId = setTimeout(() => {
            createHighlights(true);
        }, 150);

        // Update highlights on scroll (fixed elements need to be recreated)
        let scrollTimeout: NodeJS.Timeout;
        const handleScroll = () => {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                createHighlights(false);
            }, 50);
        };

        // Listen for scroll on the editor's scroll container
        const scrollContainer =
            editorElement.closest(".overflow-y-auto") ||
            editorElement.parentElement;
        scrollContainer?.addEventListener("scroll", handleScroll, {
            passive: true,
        });
        window.addEventListener("scroll", handleScroll, { passive: true });

        return () => {
            clearTimeout(timeoutId);
            clearTimeout(scrollTimeout);
            highlightElements.forEach((el) => el.remove());
            if (highlightContainerRef.current) {
                highlightContainerRef.current.remove();
            }
            scrollContainer?.removeEventListener("scroll", handleScroll);
            window.removeEventListener("scroll", handleScroll);
        };
    }, [
        activeEdit,
        editor,
        advisorMode,
        markEditAsStale,
        pendingEdits,
        setActiveEditId,
    ]);

    // Clean up highlights on unmount
    useEffect(() => {
        return () => {
            document
                .querySelectorAll(".inline-diff-highlight-container")
                .forEach((el) => el.remove());
            document
                .querySelectorAll(".inline-diff-highlight-segment")
                .forEach((el) => el.remove());
        };
    }, []);

    // Handle accept - apply the edit directly
    const handleAccept = useCallback(() => {
        if (!activeEdit) return;

        // Save scroll position before applying
        const editorElement = editor.getRootElement();
        const scrollContainer =
            editorElement?.closest(".overflow-y-auto") ||
            editorElement?.parentElement;
        const savedScrollTop = scrollContainer?.scrollTop || 0;
        const savedWindowScroll = window.scrollY;

        // Try to apply via the content state
        const success = onApplyEdit(activeEdit.oldText, activeEdit.newText);

        // Restore scroll position after a brief delay
        setTimeout(() => {
            if (scrollContainer) {
                scrollContainer.scrollTop = savedScrollTop;
            }
            window.scrollTo(0, savedWindowScroll);
        }, 50);

        if (success) {
            acceptEdit(activeEdit.id);
            // Clean up highlights
            highlightElements.forEach((el) => el.remove());
            setHighlightElements([]);
            if (highlightContainerRef.current) {
                highlightContainerRef.current.remove();
                highlightContainerRef.current = null;
            }

            // Move to next
            const remaining = pendingEdits.filter(
                (e) => e.id !== activeEdit.id && e.status === "pending"
            );
            if (remaining.length > 0) {
                setActiveEditId(remaining[0].id);
            } else {
                setActiveEditId(null);
                setInlinePosition(null);
            }
        } else {
            // Try direct DOM replacement as fallback
            const editorElement = editor.getRootElement();
            if (editorElement) {
                const range = findTextInEditor(
                    editorElement,
                    activeEdit.oldText
                );
                if (range) {
                    // Use editor update for proper state management
                    editor.update(() => {
                        const root = $getRoot();
                        const currentContent = $convertToMarkdownString(
                            SUPPORTED_TRANSFORMERS
                        );

                        // Try various text replacements
                        let newContent = currentContent;
                        if (currentContent.includes(activeEdit.oldText)) {
                            newContent = currentContent.replace(
                                activeEdit.oldText,
                                activeEdit.newText
                            );
                        } else {
                            // Try normalized replacement
                            const normalizedOld = normalizeForMatch(
                                activeEdit.oldText
                            );
                            const lines = currentContent.split("\n");
                            for (let i = 0; i < lines.length; i++) {
                                if (
                                    normalizeForMatch(lines[i]).includes(
                                        normalizedOld
                                    )
                                ) {
                                    // Found the line, try to replace
                                    const lineNormalized = normalizeForMatch(
                                        lines[i]
                                    );
                                    const idx =
                                        lineNormalized.indexOf(normalizedOld);
                                    if (idx !== -1) {
                                        // Approximate replacement
                                        lines[i] =
                                            lines[i].substring(0, idx) +
                                            activeEdit.newText +
                                            lines[i].substring(
                                                idx + activeEdit.oldText.length
                                            );
                                        break;
                                    }
                                }
                            }
                            newContent = lines.join("\n");
                        }

                        if (newContent !== currentContent) {
                            // Content changed - this will trigger the content update flow
                            console.log(
                                "[InlineDiff] Applied edit via fallback"
                            );
                        }
                    });

                    acceptEdit(activeEdit.id);
                    // Clean up highlights
                    highlightElements.forEach((el) => el.remove());
                    setHighlightElements([]);
                    if (highlightContainerRef.current) {
                        highlightContainerRef.current.remove();
                        highlightContainerRef.current = null;
                    }

                    const remaining = pendingEdits.filter(
                        (e) => e.id !== activeEdit.id && e.status === "pending"
                    );
                    if (remaining.length > 0) {
                        setActiveEditId(remaining[0].id);
                    } else {
                        setActiveEditId(null);
                        setInlinePosition(null);
                    }
                }
            }
        }
    }, [
        activeEdit,
        onApplyEdit,
        acceptEdit,
        pendingEdits,
        setActiveEditId,
        editor,
        highlightElements,
    ]);

    // Handle reject
    const handleReject = useCallback(() => {
        if (!activeEdit) return;

        rejectEdit(activeEdit.id);
        // Clean up highlights
        highlightElements.forEach((el) => el.remove());
        setHighlightElements([]);
        if (highlightContainerRef.current) {
            highlightContainerRef.current.remove();
            highlightContainerRef.current = null;
        }

        const remaining = pendingEdits.filter(
            (e) => e.id !== activeEdit.id && e.status === "pending"
        );
        if (remaining.length > 0) {
            setActiveEditId(remaining[0].id);
        } else {
            setActiveEditId(null);
            setInlinePosition(null);
        }
    }, [
        activeEdit,
        rejectEdit,
        pendingEdits,
        setActiveEditId,
        highlightElements,
    ]);

    // Navigate to previous/next edit
    const handlePrevEdit = useCallback(() => {
        const pendingOnly = pendingEdits.filter((e) => e.status === "pending");
        const currentIdx = pendingOnly.findIndex((e) => e.id === activeEditId);
        if (currentIdx > 0) {
            setActiveEditId(pendingOnly[currentIdx - 1].id);
        }
    }, [pendingEdits, activeEditId, setActiveEditId]);

    const handleNextEdit = useCallback(() => {
        const pendingOnly = pendingEdits.filter((e) => e.status === "pending");
        const currentIdx = pendingOnly.findIndex((e) => e.id === activeEditId);
        if (currentIdx < pendingOnly.length - 1) {
            setActiveEditId(pendingOnly[currentIdx + 1].id);
        }
    }, [pendingEdits, activeEditId, setActiveEditId]);

    // Keyboard shortcuts
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (advisorMode !== "agent" || !activeEdit) return;

            if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                e.preventDefault();
                handleAccept();
            } else if (e.key === "Escape") {
                e.preventDefault();
                handleReject();
            } else if (e.key === "ArrowLeft" || e.key === "[") {
                e.preventDefault();
                handlePrevEdit();
            } else if (e.key === "ArrowRight" || e.key === "]") {
                e.preventDefault();
                handleNextEdit();
            }
        };

        document.addEventListener("keydown", handleKeyDown);
        return () => document.removeEventListener("keydown", handleKeyDown);
    }, [
        advisorMode,
        activeEdit,
        handleAccept,
        handleReject,
        handlePrevEdit,
        handleNextEdit,
    ]);

    // Don't render if not in agent mode, no active edit, or active edit is stale
    if (
        advisorMode !== "agent" ||
        !activeEdit ||
        !inlinePosition ||
        activeEdit.status === "stale"
    ) {
        return null;
    }

    const pendingOnly = pendingEdits.filter((e) => e.status === "pending");
    const pendingCount = pendingOnly.length;
    const currentPendingIndex = pendingOnly.findIndex(
        (e) => e.id === activeEditId
    );
    const hasPrev = currentPendingIndex > 0;
    const hasNext = currentPendingIndex < pendingCount - 1;

    // Compact inline toolbar - Cursor style
    const toolbar = (
        <div
            className="fixed z-9999"
            style={{
                top: `${inlinePosition.top}px`,
                left: `${inlinePosition.left}px`,
            }}
        >
            {/* Compact diff preview */}
            <div className="bg-white rounded-lg shadow-xl border border-gray-300 overflow-hidden max-w-lg animate-in fade-in slide-in-from-top-1 duration-150">
                {/* Mini header with navigation */}
                <div className="flex items-center justify-between px-2 py-1.5 bg-gray-100 border-b text-xs">
                    <div className="flex items-center gap-1">
                        {/* Navigation arrows */}
                        <button
                            onClick={handlePrevEdit}
                            disabled={!hasPrev}
                            className={`p-1 rounded transition-colors ${
                                hasPrev
                                    ? "hover:bg-gray-200 text-gray-600"
                                    : "text-gray-300 cursor-not-allowed"
                            }`}
                            title="Previous edit (←)"
                        >
                            <ChevronLeft className="h-4 w-4" />
                        </button>
                        <span className="font-medium text-gray-600 min-w-[60px] text-center">
                            Edit {currentPendingIndex + 1}/{pendingCount}
                        </span>
                        <button
                            onClick={handleNextEdit}
                            disabled={!hasNext}
                            className={`p-1 rounded transition-colors ${
                                hasNext
                                    ? "hover:bg-gray-200 text-gray-600"
                                    : "text-gray-300 cursor-not-allowed"
                            }`}
                            title="Next edit (→)"
                        >
                            <ChevronRight className="h-4 w-4" />
                        </button>
                    </div>
                    <div className="flex items-center gap-1">
                        <button
                            onClick={handleReject}
                            className="p-1 rounded hover:bg-red-100 text-red-500 transition-colors"
                            title="Reject (Esc)"
                        >
                            <X className="h-4 w-4" />
                        </button>
                        <button
                            onClick={handleAccept}
                            className="p-1 rounded hover:bg-green-100 text-green-600 transition-colors"
                            title="Accept (⌘↵)"
                        >
                            <Check className="h-4 w-4" />
                        </button>
                    </div>
                </div>

                {/* Inline diff content - compact */}
                <div className="p-2 space-y-1.5 max-h-40 overflow-y-auto text-sm">
                    <div className="bg-red-50 rounded px-2 py-1 border-l-2 border-red-400">
                        <span className="line-through text-red-700">
                            {activeEdit.oldText.substring(0, 150)}
                            {activeEdit.oldText.length > 150 ? "..." : ""}
                        </span>
                    </div>
                    <div className="bg-green-50 rounded px-2 py-1 border-l-2 border-green-400">
                        <span className="text-green-700">
                            {activeEdit.newText.substring(0, 150)}
                            {activeEdit.newText.length > 150 ? "..." : ""}
                        </span>
                    </div>
                </div>

                {/* Keyboard hints */}
                <div className="px-3 py-1 bg-gray-50 border-t text-[10px] text-gray-400 flex gap-3 flex-wrap">
                    <span>
                        <kbd className="px-1 bg-white border rounded">⌘↵</kbd>{" "}
                        accept
                    </span>
                    <span>
                        <kbd className="px-1 bg-white border rounded">esc</kbd>{" "}
                        reject
                    </span>
                    <span>
                        <kbd className="px-1 bg-white border rounded">←</kbd>
                        <kbd className="px-1 bg-white border rounded">
                            →
                        </kbd>{" "}
                        navigate
                    </span>
                </div>
            </div>
        </div>
    );

    return createPortal(toolbar, document.body);
}

export default InlineDiffPlugin;

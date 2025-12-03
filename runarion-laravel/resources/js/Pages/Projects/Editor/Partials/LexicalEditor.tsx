import { useRef, useCallback, useState, useEffect } from "react";
import {
    LexicalComposer,
    type InitialConfigType,
} from "@lexical/react/LexicalComposer";
import { RichTextPlugin } from "@lexical/react/LexicalRichTextPlugin";
import { ContentEditable } from "@lexical/react/LexicalContentEditable";
import { HistoryPlugin } from "@lexical/react/LexicalHistoryPlugin";
import { OnChangePlugin } from "@lexical/react/LexicalOnChangePlugin";
import { LexicalErrorBoundary } from "@lexical/react/LexicalErrorBoundary";
import { ListPlugin } from "@lexical/react/LexicalListPlugin";
import { MarkdownShortcutPlugin } from "@lexical/react/LexicalMarkdownShortcutPlugin";
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
    $convertToMarkdownString 
} from "@lexical/markdown";
import {
    $getSelection,
    $isRangeSelection,
    FORMAT_TEXT_COMMAND,
    TextNode,
    $createParagraphNode,
} from "lexical";
import {
    HeadingNode,
    $createHeadingNode,
    QuoteNode,
} from "@lexical/rich-text";
import { ListNode, ListItemNode } from "@lexical/list";
import { $setBlocksType } from "@lexical/selection";
import { ContentUpdatePlugin, EditorRefPlugin, StreamingPlugin, ColorCodingPlugin } from "../plugins";
import {
    ContextMenu,
    ContextMenuContent,
    ContextMenuItem,
    ContextMenuTrigger,
    ContextMenuSeparator,
} from "@/Components/ui/context-menu";

// Define supported transformers using the correct exports
const SUPPORTED_TRANSFORMERS = [
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

// Debug: Log supported transformers
console.log('Supported transformers:', SUPPORTED_TRANSFORMERS.map(t => ({
    type: t.type,
    tag: (t as any).tag ?? undefined
})));

const editorConfig: InitialConfigType = {
    namespace: "MyEditor",
    nodes: [
        HeadingNode,
        ListNode,
        ListItemNode,
        QuoteNode,
        TextNode,
    ],
    theme: {
        paragraph: "text-base leading-relaxed text-gray-900",
        heading: {
            h1: "text-4xl font-bold mb-4 text-gray-900",
            h2: "text-3xl font-bold mb-3 text-gray-800",
            h3: "text-2xl font-semibold mb-3 text-gray-800",
            h4: "text-xl font-semibold mb-2 text-gray-700",
            h5: "text-lg font-medium mb-2 text-gray-700",
            h6: "text-base font-medium mb-2 text-gray-600",
        },
        text: {
            bold: "font-bold",
            italic: "italic",
            underline: "underline",
            strikethrough: "line-through",
            code: "bg-gray-100 px-1 py-0.5 rounded text-sm font-mono",
        },
        textAlignLeft: "text-left",
        textAlignCenter: "text-center",
        textAlignRight: "text-right",
        textAlignJustify: "text-justify",
        list: {
            nested: {
                listitem: "list-none",
            },
            ol: "list-decimal ml-6 my-2",
            ul: "list-disc ml-6 my-2",
            listitem: "mb-1",
        },
        quote: "border-l-4 border-gray-300 pl-4 italic text-gray-700 my-4",
    },
    onError(error) {
        throw error;
    },
};

const Placeholder = () => (
    <div className="absolute pointer-events-none text-gray-400">
        Start typing here...
    </div>
);

interface LexicalEditorProps {
    content: string;
    setContent: (content: string) => void;
    isStreaming: boolean;
    streamingText: string;
    baseContent: string;
    aiRanges: number[][]; // Array of [start, end] positions for AI text
    isColorCoded: boolean;
    selectedChapter: any;
    isInteracting: boolean;
    setIsInteracting: (interacting: boolean) => void;
    isRegenerating?: boolean;
    onBlur: () => void;
    onGetCurrentContent?: (callback: () => string) => void;
}

export function LexicalEditor({
    content,
    setContent,
    isStreaming,
    streamingText,
    baseContent,
    aiRanges,
    isColorCoded,
    selectedChapter,
    isInteracting,
    setIsInteracting,
    isRegenerating = false,
    onBlur,
    onGetCurrentContent,
}: LexicalEditorProps) {
    // Store editor instance for context menu
    const editorRef = useRef<any>(null);
    
    // Debug: Log aiRanges when they change
    useEffect(() => {
        console.log('🎨 LexicalEditor received aiRanges:', aiRanges);
    }, [aiRanges]);
    
    // Expose function to get current editor content
    useEffect(() => {
        if (onGetCurrentContent) {
            onGetCurrentContent(() => {
                if (!editorRef.current) return '';
                
                let currentContent = '';
                editorRef.current.getEditorState().read(() => {
                    currentContent = $convertToMarkdownString(SUPPORTED_TRANSFORMERS);
                });
                return currentContent;
            });
        }
    }, [onGetCurrentContent]);

    // Handle streaming updates from the plugin
    const handleStreamingUpdate = useCallback((fullContent: string) => {
        // Update the content state to match what's being displayed
        // This keeps the state in sync with the visual content during streaming
        console.log('LexicalEditor: Received streaming update', {
            fullContentLength: fullContent.length,
            isStreaming,
            isRegenerating
        });
        // Don't update content state during streaming to avoid conflicts
        // The final content will be set when streaming completes
    }, [isStreaming, isRegenerating]);

    // Format functions for context menu
    const formatHeading = (level: 1 | 2 | 3 | 4 | 5 | 6) => {
        if (editorRef.current) {
            editorRef.current.update(() => {
                const selection = $getSelection();
                if ($isRangeSelection(selection)) {
                    $setBlocksType(selection, () =>
                        $createHeadingNode(`h${level}`)
                    );
                }
            });
        }
    };

    const formatParagraph = () => {
        if (editorRef.current) {
            editorRef.current.update(() => {
                const selection = $getSelection();
                if ($isRangeSelection(selection)) {
                    $setBlocksType(selection, () => $createParagraphNode());
                }
            });
        }
    };

    const formatBold = () => {
        if (editorRef.current) {
            editorRef.current.dispatchCommand(FORMAT_TEXT_COMMAND, "bold");
        }
    };

    const formatItalic = () => {
        if (editorRef.current) {
            editorRef.current.dispatchCommand(FORMAT_TEXT_COMMAND, "italic");
        }
    };

    const formatUnderline = () => {
        if (editorRef.current) {
            editorRef.current.dispatchCommand(FORMAT_TEXT_COMMAND, "underline");
        }
    };

    return (
        <div
            className="
                flex-1 overflow-y-auto
                rounded-md border shadow-sm
                absolute top-0 left-0 w-full h-full
            "
        >
            <ContextMenu>
                <ContextMenuTrigger asChild>
                    <div 
                        className={`bg-white rounded-lg min-h-full h-auto p-6 !pb-18 flex items-start justify-start editor-content ${
                            isColorCoded ? 'color-coded' : ''
                        }`}
                        data-user-content-length={baseContent?.length || 0}
                        onContextMenu={() => setIsInteracting(true)}
                    >
                        <LexicalComposer initialConfig={editorConfig}>
                            <RichTextPlugin
                                contentEditable={
                                    <ContentEditable
                                        className={`outline-none w-full min-h-full ${
                                            isStreaming ? "opacity-90" : ""
                                        }`}
                                        onBlur={onBlur}
                                    />
                                }
                                placeholder={<Placeholder />}
                                ErrorBoundary={LexicalErrorBoundary}
                            />
                            <HistoryPlugin />
                            <ListPlugin />
                            <MarkdownShortcutPlugin transformers={SUPPORTED_TRANSFORMERS} />
                            <OnChangePlugin
                                onChange={(editorState, editor) => {
                                    // Only update content state when not streaming and not interacting
                                    // Don't update during regeneration to prevent conflicts
                                    if (!isStreaming && !isInteracting && !isRegenerating) {
                                        editorState.read(() => {
                                            const newContent = $convertToMarkdownString(SUPPORTED_TRANSFORMERS);
                                            console.log('OnChangePlugin: Content changed', {
                                                newContentLength: newContent.length,
                                                isStreaming,
                                                isInteracting,
                                                isRegenerating
                                            });
                                            setContent(newContent);
                                        });
                                    } else {
                                        console.log('OnChangePlugin: Skipping content update', {
                                            isStreaming,
                                            isInteracting,
                                            isRegenerating
                                        });
                                    }
                                }}
                            />
                            <ContentUpdatePlugin content={content} isStreaming={isStreaming} />
                            <StreamingPlugin 
                                isStreaming={isStreaming}
                                streamingText={streamingText}
                                baseContent={baseContent} // User text before generation (preserved)
                                isRegenerating={isRegenerating}
                                onStreamingUpdate={handleStreamingUpdate}
                            />
                            <ColorCodingPlugin 
                                aiRanges={aiRanges || []}
                                isColorCoded={isColorCoded}
                            />
                            <EditorRefPlugin editorRef={editorRef} />
                        </LexicalComposer>
                    </div>
                </ContextMenuTrigger>
                <ContextMenuContent 
                    onCloseAutoFocus={() => setIsInteracting(false)}
                    onEscapeKeyDown={() => setIsInteracting(false)}
                    onPointerDownOutside={() => setIsInteracting(false)}
                >
                    <ContextMenuItem onClick={() => { formatHeading(1); setIsInteracting(false); }}>
                        Heading 1
                    </ContextMenuItem>
                    <ContextMenuItem onClick={() => { formatHeading(2); setIsInteracting(false); }}>
                        Heading 2
                    </ContextMenuItem>
                    <ContextMenuItem onClick={() => { formatHeading(3); setIsInteracting(false); }}>
                        Heading 3
                    </ContextMenuItem>
                    <ContextMenuItem onClick={() => { formatParagraph(); setIsInteracting(false); }}>
                        Paragraph
                    </ContextMenuItem>
                    <ContextMenuSeparator />
                    <ContextMenuItem onClick={() => { formatBold(); setIsInteracting(false); }}>
                        Bold
                    </ContextMenuItem>
                    <ContextMenuItem onClick={() => { formatItalic(); setIsInteracting(false); }}>
                        Italic
                    </ContextMenuItem>
                    <ContextMenuItem onClick={() => { formatUnderline(); setIsInteracting(false); }}>
                        Underline
                    </ContextMenuItem>
                </ContextMenuContent>
            </ContextMenu>
        </div>
    );
}

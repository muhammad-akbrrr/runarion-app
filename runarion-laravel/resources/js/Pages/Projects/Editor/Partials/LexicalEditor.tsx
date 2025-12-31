import { useRef, useCallback, useEffect } from "react";
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
} from "@lexical/markdown";
import { HeadingNode, QuoteNode } from "@lexical/rich-text";
import { ListNode, ListItemNode } from "@lexical/list";
import { TextNode } from "lexical";
import { OriginTextNode } from "../nodes/OriginTextNode";
import {
    ContentUpdatePlugin,
    EditorRefPlugin,
    StreamingPlugin,
    ColorCodingPlugin,
    InlineDiffPlugin,
    OriginTrackingPlugin,
} from "../plugins";
import { UnifiedSelectionToolbarPlugin } from "../plugins/UnifiedSelectionToolbarPlugin";

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
console.log(
    "Supported transformers:",
    SUPPORTED_TRANSFORMERS.map((t) => ({
        type: t.type,
        tag: (t as any).tag ?? undefined,
    }))
);

const editorConfig: InitialConfigType = {
    namespace: "MyEditor",
    nodes: [
        HeadingNode,
        ListNode,
        ListItemNode,
        QuoteNode,
        OriginTextNode,
        // CRITICAL: Include TextNode to allow deserialization of legacy "type": "text" nodes
        // The OriginTrackingPlugin will automatically convert these to OriginTextNode with 'user' origin
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
    isColorCoded: boolean;
    selectedChapter: any;
    isInteracting: boolean;
    setIsInteracting: (interacting: boolean) => void;
    isRegenerating?: boolean;
    onBlur: () => void;
    onGetCurrentContent?: (callback: () => string) => void;
    // Props for selection toolbar
    workspaceId?: string;
    projectId?: string;
    aiModel?: string;
    selectionToolbarMode?: string;
    // Props for inline diff (Agent mode)
    onApplyEdit?: (oldText: string, newText: string) => boolean;
    // External ref for migration support
    editorRef?: React.MutableRefObject<any>;
}

export function LexicalEditor({
    content,
    setContent,
    isStreaming,
    streamingText,
    baseContent,
    isColorCoded,
    selectedChapter,
    isInteracting,
    setIsInteracting,
    isRegenerating = false,
    onBlur,
    onGetCurrentContent,
    workspaceId,
    projectId,
    aiModel,
    onApplyEdit,
    editorRef,
}: LexicalEditorProps) {
    // Internal editor ref (used when external ref not provided)
    const internalEditorRef = useRef<any>(null);

    // Use external ref if provided, otherwise use internal
    const effectiveEditorRef = editorRef || internalEditorRef;

    // Expose function to get current editor content as Lexical JSON
    useEffect(() => {
        if (onGetCurrentContent) {
            onGetCurrentContent(() => {
                if (!effectiveEditorRef.current) return "";

                // Serialize as Lexical JSON for proper whitespace preservation
                const editorState = effectiveEditorRef.current.getEditorState();
                return JSON.stringify(editorState.toJSON());
            });
        }
    }, [onGetCurrentContent]);

    // Handle streaming updates from the plugin
    const handleStreamingUpdate = useCallback(
        (fullContent: string) => {
            // Update the content state to match what's being displayed
            // This keeps the state in sync with the visual content during streaming
            console.log("LexicalEditor: Received streaming update", {
                fullContentLength: fullContent.length,
                isStreaming,
                isRegenerating,
            });
            // Don't update content state during streaming to avoid conflicts
            // The final content will be set when streaming completes
        },
        [isStreaming, isRegenerating]
    );

    return (
        <div
            className="
                flex-1 overflow-y-auto
                rounded-md border shadow-sm
                absolute top-0 left-0 w-full h-full
            "
        >
            <div
                className={`bg-white rounded-lg min-h-full h-auto p-6 pb-18! flex items-start justify-start editor-content ${
                    isColorCoded ? "color-coded" : ""
                }`}
                data-user-content-length={baseContent?.length || 0}
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
                    <MarkdownShortcutPlugin
                        transformers={SUPPORTED_TRANSFORMERS}
                    />
                    <OnChangePlugin
                        onChange={(editorState, editor) => {
                            // Only update content state when not streaming and not interacting
                            // Don't update during regeneration to prevent conflicts
                            if (
                                !isStreaming &&
                                !isInteracting &&
                                !isRegenerating
                            ) {
                                // Serialize as Lexical JSON for proper whitespace preservation
                                const json = JSON.stringify(editorState.toJSON());
                                console.log(
                                    "OnChangePlugin: Content changed",
                                    {
                                        newContentLength: json.length,
                                        isStreaming,
                                        isInteracting,
                                        isRegenerating,
                                    }
                                );
                                setContent(json);
                            } else {
                                console.log(
                                    "OnChangePlugin: Skipping content update",
                                    {
                                        isStreaming,
                                        isInteracting,
                                        isRegenerating,
                                    }
                                );
                            }
                        }}
                    />
                    <ContentUpdatePlugin
                        content={content}
                        isStreaming={isStreaming}
                    />
                    <StreamingPlugin
                        isStreaming={isStreaming}
                        streamingText={streamingText}
                        baseContent={baseContent} // User text before generation (preserved)
                        isRegenerating={isRegenerating}
                        onStreamingUpdate={handleStreamingUpdate}
                    />
                    <OriginTrackingPlugin />
                    <ColorCodingPlugin
                        isColorCoded={isColorCoded}
                    />
                    <EditorRefPlugin editorRef={effectiveEditorRef} />

                    {/* Unified Selection Toolbar - combines formatting + AI features */}
                    {workspaceId && projectId && selectedChapter && (
                        <UnifiedSelectionToolbarPlugin
                            workspaceId={workspaceId}
                            projectId={projectId}
                            chapterOrder={selectedChapter.order}
                            aiModel={aiModel}
                            onRewriteComplete={(oldText, newText) => {
                                console.log("Selection rewritten:", {
                                    oldText: oldText.substring(0, 50),
                                    newText: newText.substring(0, 50),
                                });
                            }}
                        />
                    )}

                    {/* Inline Diff Plugin - for Agent mode edits */}
                    {onApplyEdit && (
                        <InlineDiffPlugin
                            content={content}
                            onApplyEdit={onApplyEdit}
                        />
                    )}
                </LexicalComposer>
            </div>
        </div>
    );
}

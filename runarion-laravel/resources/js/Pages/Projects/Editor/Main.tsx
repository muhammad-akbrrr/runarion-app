import { useState, useRef, useEffect, useCallback } from "react";
import { Head, usePage } from "@inertiajs/react";
import { ChevronDown, Square } from "lucide-react";
import ProjectEditorLayout from "@/Layouts/ProjectEditorLayout";
import { EditorSidebar } from "./Partials/Sidebar/EditorSidebar";
import { EditorToolbar } from "./Partials/MainEditorToolbar";
import { Button } from "@/Components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
    DropdownMenuRadioGroup,
    DropdownMenuRadioItem,
} from "@/Components/ui/dropdown-menu";
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
import { HEADING, UNORDERED_LIST, ORDERED_LIST } from "@lexical/markdown";
import {
    $getRoot,
    $createParagraphNode,
    $createTextNode,
    $getSelection,
    $isRangeSelection,
    FORMAT_TEXT_COMMAND,
} from "lexical";
import {
    HeadingNode,
    $createHeadingNode,
    $createQuoteNode,
} from "@lexical/rich-text";
import { ListNode, ListItemNode, $createListItemNode } from "@lexical/list";
import { $setBlocksType } from "@lexical/selection";
import { useLexicalComposerContext } from "@lexical/react/LexicalComposerContext";
import { $generateHtmlFromNodes, $generateNodesFromDOM } from "@lexical/html";
import { PageProps, Project, ProjectChapter } from "@/types";
import AddChapterDialog from "./Partials/AddChapterDialog";
import { useProjectEditor } from "./hooks";
import {
    ContextMenu,
    ContextMenuContent,
    ContextMenuItem,
    ContextMenuTrigger,
    ContextMenuSeparator,
} from "@/Components/ui/context-menu";

// Import Echo for WebSocket connection
import "@/echo";

// Custom plugin to update editor content when chapter changes
function ContentUpdatePlugin({ content }: { content: string }) {
    const [editor] = useLexicalComposerContext();

    useEffect(() => {
        editor.getEditorState().read(() => {
            const root = $getRoot();
            // Compare HTML content instead of plain text
            const currentContent = $generateHtmlFromNodes(editor, null);
            if (currentContent === content) {
                return; // No need to update
            }
            editor.update(() => {
                const root = $getRoot();
                root.clear();

                if (content && content.trim()) {
                    // If content is HTML, parse it properly using Lexical's HTML import
                    if (content.startsWith('<') && content.includes('>')) {
                        try {
                            const parser = new DOMParser();
                            const doc = parser.parseFromString(content, 'text/html');
                            const nodes = $generateNodesFromDOM(editor, doc);
                            root.append(...nodes);
                        } catch (error) {
                            console.error('Error parsing HTML content:', error);
                            // Fallback to plain text
                            const paragraph = $createParagraphNode();
                            const textNode = $createTextNode(content);
                            paragraph.append(textNode);
                            root.append(paragraph);
                        }
                    } else {
                        // Handle plain text content as before
                        const lines = content.split("\n");
                        lines.forEach((line, index) => {
                            if (line.trim() || index === 0) {
                                const paragraph = $createParagraphNode();
                                const textNode = $createTextNode(line);
                                paragraph.append(textNode);
                                root.append(paragraph);
                            }
                        });
                    }
                } else {
                    // Add empty paragraph if no content
                    const paragraph = $createParagraphNode();
                    root.append(paragraph);
                }

                // Set cursor to end after content is loaded
                if (root.getChildrenSize() > 0) {
                    const lastChild = root.getLastChild();
                    if (lastChild) {
                        lastChild.selectEnd();
                    }
                } else {
                    // If no content, select the root
                    root.selectEnd();
                }
            });
        });
    }, [content, editor]);

    return null;
}

// Plugin to store editor reference
function EditorRefPlugin({ editorRef }: { editorRef: React.MutableRefObject<any> }) {
    const [editor] = useLexicalComposerContext();
    
    useEffect(() => {
        editorRef.current = editor;
    }, [editor, editorRef]);
    
    return null;
}



const editorConfig: InitialConfigType = {
    namespace: "MyEditor",
    nodes: [HeadingNode, ListNode, ListItemNode],
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

export default function ProjectEditorPage({
    workspaceId,
    projectId,
    project,
    chapters = [],
}: PageProps<{
    workspaceId: string;
    projectId: string;
    project: Project;
    chapters?: ProjectChapter[];
}>) {
    const { errors } = usePage().props;

    // Use custom hook for all editor logic
    const {
        isSaving,
        isGenerating,
        content,
        setContent,
        settings,
        localChapters,
        selectedChapter,
        selectedChapterOrder,
        isStreaming,
        streamingText,
        streamError,
        handleChapterSelect,
        handleAddChapter,
        handleSettingChange,
        handleGenerateText,
        handleCancelGeneration,
        saveContent,
        smartSave,
    } = useProjectEditor({
        workspaceId,
        projectId,
        project,
        initialChapters: chapters,
    });

    // Store editor instance for context menu
    const editorRef = useRef<any>(null);
    
    // State to prevent saves during UI interactions
    const [isInteracting, setIsInteracting] = useState(false);

    // Handle focus out save - only save if content has changed
    const handleEditorBlur = useCallback(() => {
        if (selectedChapter && !isInteracting && !isStreaming) {
            smartSave(selectedChapter.order, content, 'manual');
        }
    }, [selectedChapter, content, smartSave, isInteracting, isStreaming]);

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

    // Add Chapter Dialog state
    const [addChapterDialogOpen, setAddChapterDialogOpen] = useState(false);
    const [newChapterName, setNewChapterName] = useState("");
    const [addChapterLoading, setAddChapterLoading] = useState(false);

    // Handler for adding a new chapter
    const handleAddChapterClick = async () => {
        if (!newChapterName.trim()) return;

        setAddChapterLoading(true);
        try {
            await handleAddChapter(newChapterName);
            setAddChapterDialogOpen(false);
            setNewChapterName("");
        } catch (error) {
            console.error("Failed to add chapter:", error);
        } finally {
            setAddChapterLoading(false);
        }
    };

    return (
        <ProjectEditorLayout
            project={project}
            projectId={projectId}
            workspaceId={workspaceId}
            isSaving={isSaving}
            setIsSaving={() => {}} // Managed by hook now
        >
            <Head title="Project Editor" />

            <EditorSidebar
                settings={settings}
                onSettingChange={handleSettingChange}
                workspaceId={workspaceId}
                projectId={projectId}
            >
                <div className="flex items-center justify-between">
                    {/* Left side - Menu items */}
                    <div
                        className="
                            flex items-center space-x-1
                            p-0.5
                            bg-white
                            rounded-lg border
                        "
                    >
                        <Button variant="ghost" size="sm">
                            File
                        </Button>
                        <Button variant="ghost" size="sm">
                            Edit
                        </Button>
                        <Button variant="ghost" size="sm">
                            View
                        </Button>
                        <Button variant="ghost" size="sm">
                            Profile
                        </Button>
                    </div>

                    {/* Right side - Chapter management */}
                    <div className="flex items-center space-x-3">
                        <DropdownMenu>
                            <DropdownMenuTrigger>
                                <Button
                                    variant="outline"
                                    className="flex flex-row justify-between items-center w-50 overflow-hidden"
                                    disabled={isGenerating}
                                >
                                    <p className="truncate">
                                        {selectedChapter
                                            ? selectedChapter.chapter_name
                                            : "Select Chapter"}
                                    </p>
                                    <ChevronDown className="h-4 w-4" />
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="start" className="w-50">
                                <DropdownMenuRadioGroup
                                    value={selectedChapterOrder.toString()}
                                    onValueChange={(value) =>
                                        handleChapterSelect(parseInt(value))
                                    }
                                >
                                    {localChapters.length > 0 ? (
                                        localChapters.map((chapter, index) => (
                                            <DropdownMenuRadioItem
                                                key={index}
                                                value={chapter.order.toString()}
                                                disabled={isGenerating}
                                            >
                                                {chapter.chapter_name}
                                            </DropdownMenuRadioItem>
                                        ))
                                    ) : (
                                        <DropdownMenuItem disabled>
                                            No chapters available
                                        </DropdownMenuItem>
                                    )}
                                </DropdownMenuRadioGroup>
                            </DropdownMenuContent>
                        </DropdownMenu>

                        <Button
                            onClick={() => setAddChapterDialogOpen(true)}
                            disabled={isGenerating}
                        >
                            New Chapter
                        </Button>
                        <AddChapterDialog
                            open={addChapterDialogOpen}
                            setOpen={setAddChapterDialogOpen}
                            chapterName={newChapterName}
                            setChapterName={setNewChapterName}
                            loading={addChapterLoading}
                            handleAddChapter={handleAddChapterClick}
                        />
                    </div>
                </div>

                <div className="flex-1 relative overflow-hidden">
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
                                    className="bg-white rounded-lg min-h-full h-auto p-6 !pb-18 flex items-start justify-start"
                                    onContextMenu={() => setIsInteracting(true)}
                                >
                                    <LexicalComposer initialConfig={editorConfig}>
                                <RichTextPlugin
                                    contentEditable={
                                        <ContentEditable
                                            className={`outline-none w-full min-h-full ${
                                                isStreaming ? "opacity-90" : ""
                                            }`}
                                            onBlur={handleEditorBlur}
                                        />
                                    }
                                    placeholder={<Placeholder />}
                                    ErrorBoundary={LexicalErrorBoundary}
                                />
                                <HistoryPlugin />
                                <ListPlugin />
                                <MarkdownShortcutPlugin
                                    transformers={[
                                        HEADING,
                                        UNORDERED_LIST,
                                        ORDERED_LIST,
                                    ]}
                                />
                                <OnChangePlugin
                                    onChange={(editorState, editor) => {
                                        // Only update content state, let the hook handle saving
                                        if (!isStreaming && !isInteracting) {
                                            editorState.read(() => {
                                                const root = $getRoot();
                                                const newContent = $generateHtmlFromNodes(editor, null);
                                                setContent(newContent);
                                            });
                                        }
                                    }}
                                />
                                        <ContentUpdatePlugin content={content} />
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

                    <div className="absolute left-0 bottom-0 w-full p-4">
                        <EditorToolbar
                            onSend={handleGenerateText}
                            isGenerating={isGenerating}
                            wordCount={
                                content
                                    ? (() => {
                                        // Strip HTML tags for accurate word count
                                        const tempDiv = document.createElement('div');
                                        tempDiv.innerHTML = content;
                                        const plainText = tempDiv.textContent || tempDiv.innerText || '';
                                        return plainText.split(/\s+/).filter(Boolean).length;
                                    })()
                                    : 0
                            }
                        />
                    </div>
                </div>
            </EditorSidebar>
        </ProjectEditorLayout>
    );
}

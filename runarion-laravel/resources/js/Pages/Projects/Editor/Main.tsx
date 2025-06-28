import { useState } from "react";
import { Head, usePage } from "@inertiajs/react";
import { ChevronDown } from "lucide-react";
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
import { $getRoot, $createParagraphNode, $createTextNode } from "lexical";
import { useLexicalComposerContext } from "@lexical/react/LexicalComposerContext";
import { PageProps, Project, ProjectChapter } from "@/types";
import AddChapterDialog from "./Partials/AddChapterDialog";
import { useProjectEditor } from "./hooks";
import { useEffect } from "react";

// Custom plugin to update editor content when chapter changes
function ContentUpdatePlugin({ content }: { content: string }) {
    const [editor] = useLexicalComposerContext();

    useEffect(() => {
        editor.getEditorState().read(() => {
            const root = $getRoot();
            const currentContent = root.getTextContent();
            if (currentContent === content) {
                return; // No need to update
            }
            editor.update(() => {
                const root = $getRoot();
                root.clear();

                if (content && content.trim()) {
                    // Split content by lines to create multiple paragraphs if needed
                    const lines = content.split("\n");
                    lines.forEach((line, index) => {
                        if (line.trim() || index === 0) {
                            // Always add first line, even if empty
                            const paragraph = $createParagraphNode();
                            const textNode = $createTextNode(line);
                            paragraph.append(textNode);
                            root.append(paragraph);
                        }
                    });
                } else {
                    // Add empty paragraph if no content
                    const paragraph = $createParagraphNode();
                    root.append(paragraph);
                }
            });
        });
    }, [content, editor]);

    return null;
}

const editorConfig: InitialConfigType = {
    namespace: "MyEditor",
    theme: {
        paragraph: "text-base leading-relaxed text-gray-900",
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
        handleChapterSelect,
        handleAddChapter,
        handleSettingChange,
        handleGenerateText,
    } = useProjectEditor({
        workspaceId,
        projectId,
        project,
        initialChapters: chapters,
    });

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
                                    onValueChange={(value) => handleChapterSelect(parseInt(value))}
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
                        <div className="bg-white rounded-lg min-h-full h-auto p-6 flex items-start justify-start">
                            <LexicalComposer initialConfig={editorConfig}>
                                <RichTextPlugin
                                    contentEditable={
                                        <ContentEditable className="outline-none w-full min-h-full" />
                                    }
                                    placeholder={<Placeholder />}
                                    ErrorBoundary={LexicalErrorBoundary}
                                />
                                <HistoryPlugin />
                                <OnChangePlugin
                                    onChange={(editorState) => {
                                        editorState.read(() => {
                                            const root = $getRoot();
                                            const newContent = root.getTextContent();
                                            // Only update if content actually changed to avoid loops
                                            if (newContent !== content) {
                                                setContent(newContent);
                                            }
                                        });
                                    }}
                                />
                                <ContentUpdatePlugin content={content} />
                            </LexicalComposer>
                        </div>
                    </div>

                    <div className="absolute left-0 bottom-0 w-full p-4">
                        <EditorToolbar 
                            onSend={handleGenerateText}
                            isGenerating={isGenerating}
                            wordCount={content ? content.split(/\s+/).filter(Boolean).length : 0}
                        />
                    </div>
                </div>
            </EditorSidebar>
        </ProjectEditorLayout>
    );
}

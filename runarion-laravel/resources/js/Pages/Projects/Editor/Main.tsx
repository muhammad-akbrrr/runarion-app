import { useState, useEffect, useRef } from "react";
import { Head, router } from "@inertiajs/react";
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
    const [isSaving, setIsSaving] = useState(false);
    const [content, setContent] = useState("");
    const [selectedChapter, setSelectedChapter] =
        useState<ProjectChapter | null>(
            chapters.length > 0 ? chapters[0] : null
        );
    const saveTimeout = useRef<NodeJS.Timeout | null>(null);
    const lastSavedContent = useRef<string>("");

    // Add Chapter Dialog state
    const [addChapterDialogOpen, setAddChapterDialogOpen] = useState(false);
    const [newChapterName, setNewChapterName] = useState("");
    const [addChapterLoading, setAddChapterLoading] = useState(false);

    // Update content when selected chapter changes
    useEffect(() => {
        if (selectedChapter) {
            setContent(selectedChapter.content || "");
            lastSavedContent.current = selectedChapter.content || "";
        } else {
            setContent("");
            lastSavedContent.current = "";
        }
    }, [selectedChapter]);

    // Debounced auto-save handler for content changes
    useEffect(() => {
        if (!selectedChapter) return;
        if (content === lastSavedContent.current) return;
        if (saveTimeout.current) clearTimeout(saveTimeout.current);

        saveTimeout.current = setTimeout(() => {
            console.log("Starting save, setting isSaving to true");
            setIsSaving(true);
            router.patch(
                route("editor.project.updateData", {
                    workspace_id: workspaceId,
                    project_id: projectId,
                }),
                {
                    order: selectedChapter.order,
                    content: content,
                },
                {
                    preserveState: true,
                    preserveScroll: true,
                    onSuccess: (page) => {
                        console.log(
                            "Save successful, setting isSaving to false"
                        );
                        setIsSaving(false);
                        lastSavedContent.current = content;
                        // Optionally update chapters/selectedChapter from response
                    },
                    onError: () => {
                        console.log("Save failed, setting isSaving to false");
                        setIsSaving(false);
                    },
                }
            );
        }, 1000);

        return () => {
            if (saveTimeout.current) clearTimeout(saveTimeout.current);
        };
    }, [content, selectedChapter, workspaceId, projectId]);

    // Ensure first chapter is selected by default when chapters are loaded
    useEffect(() => {
        if (chapters.length > 0 && !selectedChapter) {
            setSelectedChapter(chapters[0]);
        }
    }, [chapters, selectedChapter]);

    // Get the selected chapter order for the radio group
    const selectedChapterOrder = selectedChapter?.order ?? 0;

    // Handler for adding a new chapter
    const handleAddChapter = async () => {
        setAddChapterLoading(true);
        router.post(
            route("editor.project.chapter", {
                workspace_id: workspaceId,
                project_id: projectId,
            }),
            { chapter_name: newChapterName },
            {
                preserveState: true,
                preserveScroll: true,
                onSuccess: (page) => {
                    const chapters = page.props.chapters as ProjectChapter[];
                    if (chapters && chapters.length > 0) {
                        setSelectedChapter(chapters[chapters.length - 1]);
                    }
                    setAddChapterDialogOpen(false);
                    setNewChapterName("");
                },
                onFinish: () => setAddChapterLoading(false),
            }
        );
    };

    return (
        <ProjectEditorLayout
            project={project}
            projectId={projectId}
            workspaceId={workspaceId}
            isSaving={isSaving}
            setIsSaving={setIsSaving}
        >
            <Head title="Project Editor" />

            <EditorSidebar 
                projectSettings={project.settings || {}}
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
                                    onValueChange={(value) => {
                                        const chapter = chapters.find(
                                            (c) => c.order.toString() === value
                                        );
                                        if (chapter) {
                                            setSelectedChapter(chapter);
                                        }
                                    }}
                                >
                                    {chapters.length > 0 ? (
                                        chapters.map((chapter, index) => (
                                            <DropdownMenuRadioItem
                                                key={index}
                                                value={chapter.order.toString()}
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

                        <Button onClick={() => setAddChapterDialogOpen(true)}>
                            New Chapter
                        </Button>
                        <AddChapterDialog
                            open={addChapterDialogOpen}
                            setOpen={setAddChapterDialogOpen}
                            chapterName={newChapterName}
                            setChapterName={setNewChapterName}
                            loading={addChapterLoading}
                            handleAddChapter={handleAddChapter}
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
                                            const newContent =
                                                root.getTextContent();
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
                        <EditorToolbar />
                    </div>
                </div>
            </EditorSidebar>
        </ProjectEditorLayout>
    );
}

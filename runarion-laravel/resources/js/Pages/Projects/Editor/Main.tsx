import { useState, useEffect } from "react";
import { Head } from "@inertiajs/react";
import { ChevronDown, Check } from "lucide-react";
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
import {
    $getRoot,
    $createParagraphNode,
    $createTextNode,
    $getSelection,
    $isRangeSelection,
} from "lexical";
import { useLexicalComposerContext } from "@lexical/react/LexicalComposerContext";
import { PageProps, Project, ProjectChapter } from "@/types";

// Custom plugin to update editor content when chapter changes
function ContentUpdatePlugin({ content }: { content: string }) {
    const [editor] = useLexicalComposerContext();

    useEffect(() => {
        console.log(
            "ContentUpdatePlugin: Updating editor with content:",
            content
        );
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
    chapters,
}: PageProps<{
    workspaceId: string;
    projectId: string;
    project: Project;
    chapters: ProjectChapter[];
}>) {
    const [content, setContent] = useState("");
    const [selectedChapter, setSelectedChapter] =
        useState<ProjectChapter | null>(
            chapters.length > 0 ? chapters[0] : null
        );

    // Update content when selected chapter changes
    useEffect(() => {
        if (selectedChapter) {
            console.log(
                "Selected chapter:",
                selectedChapter.chapter_name,
                "Content:",
                selectedChapter.content
            );
            setContent(selectedChapter.content || "");
        } else {
            setContent("");
        }
    }, [selectedChapter]);

    // Ensure first chapter is selected by default when chapters are loaded
    useEffect(() => {
        if (chapters.length > 0 && !selectedChapter) {
            setSelectedChapter(chapters[0]);
        }
    }, [chapters, selectedChapter]);

    // Get the selected chapter order for the radio group
    const selectedChapterOrder = selectedChapter?.order ?? 0;

    return (
        <ProjectEditorLayout
            project={project}
            projectId={projectId}
            workspaceId={workspaceId}
        >
            <Head title="Project Editor" />

            <EditorSidebar>
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
                                    className="flex flex-row justify-between items-center w-54"
                                >
                                    {selectedChapter
                                        ? selectedChapter.chapter_name
                                        : "Select Chapter"}
                                    <ChevronDown className="h-4 w-4" />
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="start">
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

                        <Button>New Chapter</Button>
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
                                        <ContentEditable className="outline-none w-full min-h-[500px]" />
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

import { useState } from "react";
import { Head } from "@inertiajs/react";
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
import { $getRoot } from "lexical";
import { PageProps, Project } from "@/types";

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
}: PageProps<{
    workspaceId: string;
    projectId: string;
    project: Project;
}>) {
    const [content, setContent] = useState("");

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
                                <Button variant="outline">
                                    Select Chapter
                                    <ChevronDown className="h-4 w-4" />
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="start">
                                <DropdownMenuItem>Chapter 1</DropdownMenuItem>
                                <DropdownMenuItem>Chapter 2</DropdownMenuItem>
                                <DropdownMenuItem>Chapter 3</DropdownMenuItem>
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
                                            setContent(root.getTextContent());
                                        });
                                    }}
                                />
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

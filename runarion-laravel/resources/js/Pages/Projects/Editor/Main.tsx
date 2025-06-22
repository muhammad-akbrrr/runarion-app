import { useState, useEffect } from "react";
import { Head, usePage, router } from "@inertiajs/react";
import { ChevronDown, Save } from "lucide-react";
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
import { PageProps, Project } from "@/types";
import { EditorProvider } from "./EditorContext";

interface FlashData {
    data?: {
        success: boolean;
        text?: string;
        error_message?: string;
    };
    success?: boolean;
    message?: string;
    projectContent?: ProjectContent;
}

interface ProjectContent {
    id: number;
    project_id: string;
    content: string | null;
    editor_state: any | null;
    word_count: number;
    character_count: number;
    version: number;
    last_edited_at: string;
    created_at: string;
    updated_at: string;
}

export default function ProjectEditorPage({
    workspaceId,
    projectId,
    project,
    projectContent,
}: PageProps<{
    workspaceId: string;
    projectId: string;
    project: Project;
    projectContent?: ProjectContent;
}>) {
    const page = usePage();
    const { auth } = page.props;
    const userId = auth.user.id;
    const [content, setContent] = useState(projectContent?.content || "");
    const [isSaving, setIsSaving] = useState(false);
    const [lastSaved, setLastSaved] = useState<Date | null>(null);

    const flash = page.props.flash as FlashData;

    useEffect(() => {
        if (projectContent?.content) {
            const editorContent = document.getElementById("editor-content");
            if (editorContent) {
                editorContent.innerHTML = projectContent.content;
                setContent(editorContent.innerText || "");
            }
        }
    }, [projectContent]);

    useEffect(() => {
        console.log("Flash data:", flash);

        if (flash && flash.data) {
            const data = flash.data;

            if (data.success) {
                const generatedText = data.text;

                if (generatedText) {
                    const editorContent = document.getElementById("editor-content");

                    if (editorContent) {
                        const formattedText = generatedText.replace(/\n/g, "<br />");

                        if (
                            editorContent.innerText.trim() === "Start typing here..." ||
                            editorContent.innerText.trim() === ""
                        ) {
                            editorContent.innerHTML = formattedText;
                        } else {
                            editorContent.innerHTML += formattedText;
                        }

                        setContent(editorContent.innerText || "");
                    }
                }
            }
        }

        if (flash && flash.success && flash.message === "Content saved successfully") {
            const editorContent = document.getElementById("editor-content");

            if (
                editorContent &&
                flash.projectContent?.content &&
                editorContent.innerHTML !== flash.projectContent.content
            ) {
                editorContent.innerHTML = flash.projectContent.content;
                setContent(editorContent.innerText || "");
            }

            setIsSaving(false);
            setLastSaved(new Date());
        }
    }, [flash]);

    const handleContentChange = (e: React.FormEvent<HTMLDivElement>) => {
        const newContent = e.currentTarget.textContent || "";
        setContent(newContent);
    };

    const handleSave = () => {
        const editorContent = document.getElementById("editor-content");
        if (!editorContent) return;

        setIsSaving(true);

        const editorContext = document.querySelector('[data-editor-context]');
        const editorState = editorContext ? JSON.parse(editorContext.getAttribute('data-editor-state') || '{}') : {};

        router.post(
            route('workspace.projects.editor.save', {
                workspace_id: workspaceId,
                project_id: projectId
            }),
            {
                content: editorContent.innerHTML,
                editor_state: editorState
            },
            {
                preserveScroll: true,
                onSuccess: () => {
                    setIsSaving(false);
                    setLastSaved(new Date());
                },
                onError: () => {
                    setIsSaving(false);
                    console.error("Failed to save content.");
                }
            }
        );
    };

    return (
        <ProjectEditorLayout
            project={project}
            projectId={projectId}
            workspaceId={workspaceId}
        >
            <Head title="Project Editor" />

            <EditorProvider
                workspaceId={workspaceId}
                projectId={projectId}
                userId={userId}
                initialEditorState={projectContent?.editor_state}
            >
                <EditorSidebar>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-1 p-0.5 bg-white rounded-lg border">
                            <Button variant="ghost" size="sm" onClick={handleSave} disabled={isSaving}>
                                {isSaving ? "Saving..." : "File"}
                            </Button>
                            <Button variant="ghost" size="sm">Edit</Button>
                            <Button variant="ghost" size="sm">View</Button>
                            <Button variant="ghost" size="sm">Profile</Button>
                        </div>

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
                        <div className="flex-1 overflow-y-auto rounded-md border shadow-sm absolute top-0 left-0 w-full h-full">
                            <div className="bg-white rounded-lg h-[200vh] p-6">
                                <div className="relative">
                                    <div
                                        id="editor-content"
                                        className="relative w-full h-full outline-none resize-none text-gray-900 placeholder-gray-400"
                                        contentEditable
                                        suppressContentEditableWarning={true}
                                        onInput={handleContentChange}
                                        style={{
                                            lineHeight: "1.6",
                                            fontSize: "16px",
                                        }}
                                    />

                                    {content.trim() === "" && (
                                        <span className="absolute text-gray-400 pointer-events-none">
                                            Start typing here...
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="absolute left-0 bottom-0 w-full p-4">
                            <EditorToolbar lastSaved={lastSaved} />
                        </div>
                    </div>
                </EditorSidebar>
            </EditorProvider>
        </ProjectEditorLayout>
    );
}

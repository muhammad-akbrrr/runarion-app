import { useState, useEffect, useRef } from "react";
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
import { EditorProvider, useEditor } from "./EditorContext";
import { toast } from "sonner";

interface FlashData {
    data?: {
        success: boolean;
        text?: string;
        error_message?: string;
    };
    success?: boolean;
    message?: string;
    projectContent?: ProjectContent;
    last_autosaved_at?: string;
}

interface ProjectContent {
    id: number;
    project_id: string;
    chapter_id: string;
    content: string | null;
    editor_state: any | null;
    word_count: number;
    character_count: number;
    version: number;
    last_edited_at: string;
    last_autosaved_at: string | null;
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
    const [currentChapter, setCurrentChapter] = useState("chapter_1");
    const [isSaving, setIsSaving] = useState(false);
    const [isAutoSaving, setIsAutoSaving] = useState(false);
    const [lastSaved, setLastSaved] = useState<Date | null>(null);
    const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);
    
    // Get the flash data from the page props
    const flash = page.props.flash as FlashData;

    // Initialize editor with saved content if available
    useEffect(() => {
        if (projectContent?.content) {
            const editorContent = document.getElementById("editor-content");
            if (editorContent) {
                editorContent.innerHTML = projectContent.content;
                setContent(editorContent.innerText || "");
            }
        }
        
        // Set up auto-save timer
        autoSaveTimerRef.current = setInterval(() => {
            handleAutoSave();
        }, 30000); // Auto-save every 30 seconds
        
        // Clean up timer on unmount
        return () => {
            if (autoSaveTimerRef.current) {
                clearInterval(autoSaveTimerRef.current);
            }
        };
    }, []);

    // Handle flash messages for story generation and other operations
    useEffect(() => {
        console.log("Flash data:", flash);
        
        // Handle generation response
        if (flash && flash.data) {
            const data = flash.data;
            
            if (data.success) {
                // Get the generated text
                const generatedText = data.text;
                
                if (generatedText) {
                    // Get the editor content element
                    const editorContent = document.getElementById("editor-content");
                    
                    // Append the generated text to the existing content
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
                    
                    // Show success toast
                    toast.success("Story generated successfully!");
                }
            } else if (data.error_message) {
                // Show error toast
                toast.error(data.error_message || "Failed to generate story");
            }
        }
        
        // Handle save/autosave response
        if (flash && flash.success) {
            setLastSaved(new Date());
            
            if (flash.message === "Content saved successfully") {
                toast.success(flash.message);
                setIsSaving(false);
            } else if (flash.message === "Content auto-saved successfully") {
                console.log("Content auto-saved successfully");
                setIsAutoSaving(false);
            }
            
            // Update content if provided in flash
            if (flash.projectContent && flash.projectContent.content) {
                const editorContent = document.getElementById("editor-content");
                if (editorContent && editorContent.innerHTML !== flash.projectContent.content) {
                    editorContent.innerHTML = flash.projectContent.content;
                    setContent(editorContent.innerText || "");
                }
            }
        }
    }, [flash]);

    // Handle content change
    const handleContentChange = (e: React.FormEvent<HTMLDivElement>) => {
        const newContent = e.currentTarget.textContent || "";
        setContent(newContent);
    };

    // Handle manual save
    const handleSave = () => {
        const editorContent = document.getElementById("editor-content");
        if (!editorContent) return;
        
        setIsSaving(true);
        
        // Get the editor state from context
        const editorContext = document.querySelector('[data-editor-context]');
        const editorState = editorContext ? JSON.parse(editorContext.getAttribute('data-editor-state') || '{}') : {};
        
        // Use Inertia for all requests
        router.post(
            route('workspace.projects.editor.save', {
                workspace_id: workspaceId,
                project_id: projectId
            }),
            {
                content: editorContent.innerHTML,
                chapter_id: currentChapter,
                editor_state: editorState
            },
            {
                preserveScroll: true,
                onError: (errors) => {
                    setIsSaving(false);
                    console.error("Save errors:", errors);
                    toast.error("Failed to save content. Please try again.");
                }
            }
        );
    };

    // Handle auto-save
    const handleAutoSave = () => {
        const editorContent = document.getElementById("editor-content");
        if (!editorContent || editorContent.innerHTML.trim() === "" || isAutoSaving) return;
        
        // Don't auto-save if content hasn't changed
        if (projectContent?.content === editorContent.innerHTML) return;
        
        setIsAutoSaving(true);
        
        // Get the editor state from context
        const editorContext = document.querySelector('[data-editor-context]');
        const editorState = editorContext ? JSON.parse(editorContext.getAttribute('data-editor-state') || '{}') : {};
        
        // Use Inertia for all requests
        router.post(
            route('workspace.projects.editor.autosave', {
                workspace_id: workspaceId,
                project_id: projectId
            }),
            {
                content: editorContent.innerHTML,
                chapter_id: currentChapter,
                editor_state: editorState
            },
            {
                preserveScroll: true,
                onError: (errors) => {
                    setIsAutoSaving(false);
                    console.error("Auto-save errors:", errors);
                }
            }
        );
    };

    // Load content for a specific chapter
    const loadChapterContent = (chapterId: string) => {
        router.visit(
            route('workspace.projects.editor.content', {
                workspace_id: workspaceId,
                project_id: projectId
            }),
            {
                data: { chapter_id: chapterId },
                preserveState: true,
                onSuccess: () => {
                    setCurrentChapter(chapterId);
                },
                onError: (errors) => {
                    console.error("Load chapter errors:", errors);
                    toast.error("Failed to load chapter content. Please try again.");
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
                        {/* Left side - Menu items */}
                        <div
                            className="
                                flex items-center space-x-1
                                p-0.5
                                bg-white
                                rounded-lg border
                            "
                        >
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button variant="ghost" size="sm">
                                        File
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="start">
                                    <DropdownMenuItem onClick={handleSave}>
                                        <Save className="h-4 w-4 mr-2" />
                                        Save
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
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
                                    <DropdownMenuItem onClick={() => loadChapterContent("chapter_1")}>
                                        Chapter 1
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => loadChapterContent("chapter_2")}>
                                        Chapter 2
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => loadChapterContent("chapter_3")}>
                                        Chapter 3
                                    </DropdownMenuItem>
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
                            <div
                                className="
                                    bg-white rounded-lg
                                    h-[200vh] p-6
                                "
                            >
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
                            <EditorToolbar 
                                currentChapter={currentChapter}
                                onSave={handleSave}
                                isSaving={isSaving}
                                lastSaved={lastSaved}
                            />
                        </div>
                    </div>
                </EditorSidebar>
            </EditorProvider>
        </ProjectEditorLayout>
    );
}

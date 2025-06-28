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
    const [settings, setSettings] = useState(project.settings || {});
    const [localChapters, setLocalChapters] = useState<ProjectChapter[]>(chapters);
    const [selectedChapter, setSelectedChapter] =
        useState<ProjectChapter | null>(
            chapters.length > 0 ? chapters[0] : null
        );
    
    // Unified save timeout for both content and settings
    const saveTimeout = useRef<NodeJS.Timeout | null>(null);
    const lastSavedContent = useRef<string>("");
    const lastSavedSettings = useRef<any>({});
    const isInitialized = useRef(false);

    // Add Chapter Dialog state
    const [addChapterDialogOpen, setAddChapterDialogOpen] = useState(false);
    const [newChapterName, setNewChapterName] = useState("");
    const [addChapterLoading, setAddChapterLoading] = useState(false);

    // Update local chapters when chapters prop changes
    useEffect(() => {
        setLocalChapters(chapters);
        
        // Update selectedChapter if it exists in the new chapters
        if (selectedChapter) {
            const updatedChapter = chapters.find(ch => ch.order === selectedChapter.order);
            if (updatedChapter) {
                setSelectedChapter(updatedChapter);
            }
        }
    }, [chapters]);

    // Initialize component
    useEffect(() => {
        if (selectedChapter) {
            setContent(selectedChapter.content || "");
            lastSavedContent.current = selectedChapter.content || "";
        } else {
            setContent("");
            lastSavedContent.current = "";
        }
        
        // Initialize settings
        const initialSettings = project.settings || {};
        setSettings(initialSettings);
        lastSavedSettings.current = initialSettings;
        
        // Mark as initialized after a brief delay to ensure all components are mounted
        setTimeout(() => {
            isInitialized.current = true;
            console.log("Project editor initialized");
        }, 100);
    }, [selectedChapter, project.settings]);

    // Unified save function for both content and settings
    const saveProjectData = () => {
        if (!isInitialized.current) {
            console.log("Skipping save: not initialized yet");
            return;
        }

        const contentChanged = content !== lastSavedContent.current;
        const settingsChanged = JSON.stringify(settings) !== JSON.stringify(lastSavedSettings.current);

        if (!contentChanged && !settingsChanged) {
            console.log("No changes to save");
            return;
        }

        console.log("Starting unified save", { contentChanged, settingsChanged });
        setIsSaving(true);

        // Prepare save promises
        const savePromises = [];

        // Save content if changed and we have a selected chapter
        if (contentChanged && selectedChapter) {
            console.log("Saving content changes");
            const contentPromise = new Promise((resolve, reject) => {
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
                            lastSavedContent.current = content;
                            console.log("Content saved successfully");
                            
                            // Update local chapters with server response
                            const updatedChapters = page.props.chapters as ProjectChapter[];
                            if (updatedChapters) {
                                setLocalChapters(updatedChapters);
                                
                                // Update selected chapter with latest content
                                const updatedSelectedChapter = updatedChapters.find(ch => ch.order === selectedChapter.order);
                                if (updatedSelectedChapter) {
                                    setSelectedChapter(updatedSelectedChapter);
                                }
                            }
                            
                            resolve(true);
                        },
                        onError: (errors) => {
                            console.error("Failed to save content:", errors);
                            reject(errors);
                        },
                    }
                );
            });
            savePromises.push(contentPromise);
        }

        // Save settings if changed
        if (settingsChanged) {
            console.log("Saving settings changes");
            const settingsPromise = new Promise((resolve, reject) => {
                router.patch(
                    route("editor.project.updateSettings", {
                        workspace_id: workspaceId,
                        project_id: projectId,
                    }),
                    settings,
                    {
                        preserveState: true,
                        preserveScroll: true,
                        onSuccess: () => {
                            lastSavedSettings.current = { ...settings };
                            console.log("Settings saved successfully");
                            resolve(true);
                        },
                        onError: (errors) => {
                            console.error("Failed to save settings:", errors);
                            reject(errors);
                        },
                    }
                );
            });
            savePromises.push(settingsPromise);
        }

        // Handle all save operations
        if (savePromises.length > 0) {
            Promise.allSettled(savePromises)
                .then((results) => {
                    const failures = results.filter(result => result.status === 'rejected');
                    if (failures.length > 0) {
                        console.error("Some saves failed:", failures);
                    } else {
                        console.log("All saves completed successfully");
                    }
                })
                .finally(() => {
                    setIsSaving(false);
                });
        } else {
            setIsSaving(false);
        }
    };

    // Unified debounced auto-save effect
    useEffect(() => {
        if (!isInitialized.current) {
            return;
        }

        // Clear existing timeout
        if (saveTimeout.current) {
            clearTimeout(saveTimeout.current);
        }

        // Set new timeout
        saveTimeout.current = setTimeout(() => {
            saveProjectData();
        }, 1000);

        return () => {
            if (saveTimeout.current) {
                clearTimeout(saveTimeout.current);
            }
        };
    }, [content, settings, selectedChapter, workspaceId, projectId]);

    // Ensure first chapter is selected by default when chapters are loaded
    useEffect(() => {
        if (localChapters.length > 0 && !selectedChapter) {
            setSelectedChapter(localChapters[0]);
        }
    }, [localChapters, selectedChapter]);

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
                    const updatedChapters = page.props.chapters as ProjectChapter[];
                    if (updatedChapters && updatedChapters.length > 0) {
                        setLocalChapters(updatedChapters);
                        setSelectedChapter(updatedChapters[updatedChapters.length - 1]);
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
                currentPreset={settings.currentPreset || "story-telling"}
                authorProfile={settings.authorProfile || "tolkien"}
                aiModel={settings.aiModel || "chatgpt-4o"}
                memory={settings.memory || ""}
                storyGenre={settings.storyGenre || ""}
                storyTone={settings.storyTone || ""}
                storyPov={settings.storyPov || ""}
                temperature={settings.temperature || 1}
                repetitionPenalty={settings.repetitionPenalty || 0}
                outputLength={settings.outputLength || 300}
                minOutputToken={settings.minOutputToken || 50}
                topP={settings.topP || 0.85}
                tailFree={settings.tailFree || 0.85}
                topA={settings.topA || 0.85}
                topK={settings.topK || 0.85}
                phraseBias={settings.phraseBias || []}
                bannedPhrases={settings.bannedPhrases || []}
                stopSequences={settings.stopSequences || []}
                onSettingChange={(key: string, value: any) => {
                    setSettings(prev => ({
                        ...prev,
                        [key]: value
                    }));
                }}
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
                                        const chapter = localChapters.find(
                                            (c) => c.order.toString() === value
                                        );
                                        if (chapter) {
                                            setSelectedChapter(chapter);
                                        }
                                    }}
                                >
                                    {localChapters.length > 0 ? (
                                        localChapters.map((chapter, index) => (
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

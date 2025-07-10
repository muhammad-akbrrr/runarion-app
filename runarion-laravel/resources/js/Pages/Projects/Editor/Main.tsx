import { useState, useCallback } from "react";
import { Head, usePage } from "@inertiajs/react";
import { ChevronDown } from "lucide-react";
import ProjectEditorLayout from "@/Layouts/ProjectEditorLayout";
import { EditorSidebar } from "./Partials/Sidebar/EditorSidebar";
import { EditorToolbar } from "./Partials/MainEditorToolbar";
import { LexicalEditor } from "./Partials/LexicalEditor";
import { Button } from "@/Components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
    DropdownMenuRadioGroup,
    DropdownMenuRadioItem,
} from "@/Components/ui/dropdown-menu";
import { PageProps, Project, ProjectChapter } from "@/types";
import AddChapterDialog from "./Partials/AddChapterDialog";
import { useProjectEditor } from "./Hooks";

// Import Echo for WebSocket connection
import "@/echo";

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

    // State to prevent saves during UI interactions
    const [isInteracting, setIsInteracting] = useState(false);

    // Handle focus out save - only save if content has changed
    const handleEditorBlur = useCallback(() => {
        console.log('Editor blur event', {
            hasSelectedChapter: !!selectedChapter,
            isInteracting,
            isStreaming,
            contentLength: (content ?? '').length // Handle null content
        });
        if (selectedChapter && !isInteracting && !isStreaming) {
            smartSave(selectedChapter.order, content, 'manual');
        }
    }, [selectedChapter, content, smartSave, isInteracting, isStreaming]);

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
            setIsSaving={() => {}} // No longer needed since saves are async
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
                    <LexicalEditor
                        content={content}
                        setContent={setContent}
                        isStreaming={isStreaming}
                        streamingText={streamingText}
                        selectedChapter={selectedChapter}
                        isInteracting={isInteracting}
                        setIsInteracting={setIsInteracting}
                        onBlur={handleEditorBlur}
                    />

                    <div className="absolute left-0 bottom-0 w-full p-4">
                        <EditorToolbar
                            onSend={handleGenerateText}
                            isGenerating={isGenerating}
                            wordCount={
                                content
                                    ? (() => {
                                        // Count words from markdown content directly
                                        const plainText = (content ?? '') // Handle null content
                                            .replace(/[#*_`~\[\]()]/g, '') // Remove markdown syntax
                                            .replace(/\n+/g, ' ') // Replace newlines with spaces
                                            .trim();
                                        const wordCount = plainText.split(/\s+/).filter(Boolean).length;
                                        return wordCount;
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

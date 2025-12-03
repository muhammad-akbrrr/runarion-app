import { useState, useCallback, useRef, useEffect } from "react";
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
import { useProjectEditor } from "./hooks";

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
    const { errors, authorStyles: rawAuthorStyles } = usePage().props;
    
    // Get author styles from page props (provided by controller)
    // Controller sends: { id, name, status, avatar, color }
    const authorStyles = (rawAuthorStyles as Array<{ id: string; name: string; status?: string }> | undefined)?.map(style => ({
        id: style.id,
        name: style.name,
        status: style.status,
    })) ?? [];

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
        isRegenerating,
        baseContent,
        aiRanges,
        isColorCoded,
        setIsColorCoded,
        versionControl,
        handleChapterSelect,
        handleAddChapter,
        handleSettingChange,
        handleGenerateText,
        handleRegenerateText,
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
    
    // Ref to get current editor content
    const getCurrentEditorContentRef = useRef<(() => string) | null>(null);
    
    // Debug: Log when aiRanges changes
    useEffect(() => {
        console.log('🎨 Main.tsx aiRanges updated:', aiRanges);
    }, [aiRanges]);

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
    const [addChapterError, setAddChapterError] = useState<string>("");

    // Handler for adding a new chapter
    const handleAddChapterClick = async () => {
        if (!newChapterName.trim()) return;

        // Clear previous errors
        setAddChapterError("");
        setAddChapterLoading(true);
        
        try {
            await handleAddChapter(newChapterName);
            setAddChapterDialogOpen(false);
            setNewChapterName("");
            setAddChapterError("");
        } catch (error: any) {
            console.error("Failed to add chapter:", error);
            // Extract error message from Inertia error object
            if (error?.chapter_name) {
                setAddChapterError(error.chapter_name);
            } else if (typeof error === 'string') {
                setAddChapterError(error);
            } else {
                setAddChapterError("Failed to add chapter. Please try again.");
            }
        } finally {
            setAddChapterLoading(false);
        }
    };

    // Get existing chapter names for validation
    const existingChapterNames = localChapters.map(ch => ch.chapter_name);

    // Handle dialog open/close to reset state
    const handleDialogOpenChange = (open: boolean) => {
        setAddChapterDialogOpen(open);
        if (!open) {
            // Reset state when closing
            setNewChapterName("");
            setAddChapterError("");
        }
    };

    // Handle chapter name change to clear errors
    const handleChapterNameChange = (name: string) => {
        setNewChapterName(name);
        // Clear backend error when user starts typing
        if (addChapterError) {
            setAddChapterError("");
        }
    };

    // Prepare version control state for toolbar
    const versionControlState = {
        currentVersionIndex: versionControl.currentVersionIndex,
        totalVersions: versionControl.totalVersions,
        canUndo: versionControl.canUndo,
        canRedo: versionControl.canRedo,
        canRegenerate: versionControl.canRegenerate,
        isLoading: versionControl.isLoading,
        versionDisplayText: versionControl.versionDisplayText,
        onUndo: versionControl.undo,
        onRedo: versionControl.redo,
        onSwitchVersion: versionControl.switchVersion,
        onRegenerate: () => {
            // Pass current settings to regenerate function
            const currentSettings = {
                currentPreset: settings.currentPreset || "creative-writing",
                aiModel: settings.aiModel || 'gemini-2.0-flash',
                memory: settings.memory || '',
                storyGenre: settings.storyGenre || '',
                storyTone: settings.storyTone || '',
                storyPov: settings.storyPov || '',
                temperature: settings.temperature || 1.0,
                repetitionPenalty: settings.repetitionPenalty || 0.0,
                outputLength: settings.outputLength || 300,
                minOutputToken: settings.minOutputToken || 50,
                topP: settings.topP || 0.85,
                tailFree: settings.tailFree || 0.85,
                topA: settings.topA || 0.85,
                topK: settings.topK || 0.85,
                phraseBias: settings.phraseBias || [],
                bannedPhrases: settings.bannedPhrases || [],
                stopSequences: settings.stopSequences || [],
            };
            handleRegenerateText();
        },
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
                authorStyles={authorStyles}
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
                            setOpen={handleDialogOpenChange}
                            chapterName={newChapterName}
                            setChapterName={handleChapterNameChange}
                            loading={addChapterLoading}
                            handleAddChapter={handleAddChapterClick}
                            existingChapterNames={existingChapterNames}
                            error={addChapterError}
                        />
                    </div>
                </div>

                <div className="flex-1 relative overflow-hidden">
                    <LexicalEditor
                        content={content}
                        setContent={setContent}
                        isStreaming={isStreaming}
                        streamingText={streamingText}
                        baseContent={baseContent}
                        aiRanges={aiRanges}
                        isColorCoded={isColorCoded}
                        selectedChapter={selectedChapter}
                        isInteracting={isInteracting}
                        setIsInteracting={setIsInteracting}
                        isRegenerating={isRegenerating}
                        onBlur={handleEditorBlur}
                        onGetCurrentContent={(getter) => {
                            getCurrentEditorContentRef.current = getter;
                        }}
                    />

                    <div className="absolute left-0 bottom-0 w-full p-4">
                        <EditorToolbar
                            onSend={() => {
                                // Get current editor content directly before generating
                                const currentEditorContent = getCurrentEditorContentRef.current?.() ?? content ?? '';
                                handleGenerateText(currentEditorContent);
                            }}
                            isGenerating={isGenerating}
                            versionControl={versionControlState}
                            isColorCoded={isColorCoded}
                            onToggleColorCoding={() => {
                                if (typeof setIsColorCoded === 'function') {
                                    setIsColorCoded(!isColorCoded);
                                }
                            }}
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

import { useState, useCallback, useRef, useEffect } from "react";
import { Head, usePage, router } from "@inertiajs/react";
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
import { Input } from "@/Components/ui/input";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";
import { Edit, Trash2 } from "lucide-react";
import { PageProps, Project, ProjectChapter } from "@/types";
import type { AuthorStyle } from "@/types/files";
import type { PipelineLock } from "@/types/project";
import AddChapterDialog from "./Partials/AddChapterDialog";
import { useProjectEditor } from "./Hooks";
import { PendingEditsProvider } from "./Contexts/PendingEditsContext";
import { MagicWandButton } from "@/Components/MagicWandButton";
import { findBestMatch } from "./Utils/fuzzyTextMatch";
import {
    getPlainTextFromEditor,
    replaceTextInLexicalEditor,
    insertChainBuilderResult,
} from "./Utils/lexicalTextReplace";
import { isLexicalJSON, extractTextFromNode } from "./Utils/lexicalTextExtract";
import { toast } from "sonner";
import { useWorkspacePipelineEvents } from "@/Hooks/useWorkspacePipelineEvents";
import { http } from "@/Lib/http";

/**
 * Calculate word count from content (handles both Lexical JSON and plain text)
 */
function getWordCount(content: string | null | undefined): number {
    if (!content) return 0;

    let plainText: string;

    if (isLexicalJSON(content)) {
        try {
            const parsed = JSON.parse(content);
            plainText = extractTextFromNode(parsed.root);
        } catch {
            return 0;
        }
    } else {
        // Plain text - just use as-is (with markdown cleanup)
        plainText = content
            .replace(/[#*_`~\[\]()]/g, "") // Remove markdown syntax
            .replace(/\n+/g, " ");
    }

    const cleaned = plainText.replace(/\n+/g, " ").trim();
    if (!cleaned) return 0;

    return cleaned.split(/\s+/).filter(Boolean).length;
}

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
    const {
        authorStyles: rawAuthorStyles,
        projectPipelineLock: rawProjectPipelineLock,
        flash,
    } = usePage().props;
    const projectPipelineLock =
        (rawProjectPipelineLock as PipelineLock | null | undefined) ?? null;
    const isPipelineLocked = Boolean(projectPipelineLock?.isLocked);
    const lockMessage =
        projectPipelineLock?.message ||
        (projectPipelineLock?.operationType === "snapshot_restore"
            ? "A snapshot restore is in progress for this project."
            : "This project is locked by an active operation.");

    // Get author styles from page props (provided by controller)
    const authorStyles =
        (rawAuthorStyles as AuthorStyle[] | undefined)?.map((style) => ({
            id: style.id,
            name: style.name,
            status: style.status,
            schemaVersion: style.schemaVersion,
        })) ?? [];

    // Ref to store Lexical editor instance for migration (must be declared before useProjectEditor)
    const editorRef = useRef<any>(null);

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
        isRegenerating,
        baseContent,
        isColorCoded,
        setIsColorCoded,
        versionControl,
        handleChapterSelect,
        handleAddChapter,
        handleSettingChange,
        handleGenerateText,
        handleRegenerateText,
        smartSave,
        flushSettingsBeforeNavigation,
    } = useProjectEditor({
        workspaceId,
        projectId,
        project,
        initialChapters: chapters,
        editorRef,
    });

    // State to prevent saves during UI interactions
    const [isInteracting, setIsInteracting] = useState(false);

    // State to track external saving operations (e.g., advisor chat operations)
    // Uses debounced indicator like useUnifiedSave to prevent flashing
    const [isExternalSavingRaw, setIsExternalSavingRaw] = useState(false);
    const [isExternalSavingIndicator, setIsExternalSavingIndicator] =
        useState(false);
    const externalSavingDebounceRef = useRef<NodeJS.Timeout | null>(null);

    // Debounce the external saving indicator (stays visible 1.5s after save completes)
    useEffect(() => {
        if (isExternalSavingRaw) {
            // Show indicator immediately when saving starts
            setIsExternalSavingIndicator(true);
            // Clear any pending "done" timer
            if (externalSavingDebounceRef.current) {
                clearTimeout(externalSavingDebounceRef.current);
                externalSavingDebounceRef.current = null;
            }
        } else {
            // Debounce hiding the indicator - wait 1.5s after saving ends
            externalSavingDebounceRef.current = setTimeout(() => {
                setIsExternalSavingIndicator(false);
            }, 1500);
        }

        return () => {
            if (externalSavingDebounceRef.current) {
                clearTimeout(externalSavingDebounceRef.current);
            }
        };
    }, [isExternalSavingRaw]);

    useEffect(() => {
        if (flash?.success) toast.success(flash.success);
        if (flash?.error) toast.error(flash.error);
        if (flash?.info) toast.info(flash.info);
        if (flash?.warning) toast.warning(flash.warning);
    }, [flash?.success, flash?.error, flash?.info, flash?.warning]);

    useWorkspacePipelineEvents({
        workspaceId,
        projectId,
        reloadOnly: [
            "chapters",
            "projectPipelineLock",
            "project_completed_onboarding",
            "authorStyles",
            "project",
        ],
    });

    // Callback for external saving changes (passed to AdvisorTab)
    const handleExternalSavingChange = useCallback((saving: boolean) => {
        setIsExternalSavingRaw(saving);
    }, []);

    // Combined saving state for the indicator
    const isCombinedSaving = isSaving || isExternalSavingIndicator;

    // Ref to get current editor content
    const getCurrentEditorContentRef = useRef<(() => string) | null>(null);

    // Handle chain builder results from URL params (legacy/backward compatibility)
    // NOTE: New flow saves content server-side before redirect, so this won't trigger.
    // Kept for backward compatibility with any bookmarked URLs or edge cases.
    useEffect(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const chainResult = urlParams.get("chainBuilderResult");
        const chainTimestamp = urlParams.get("chainBuilderTimestamp");

        if (chainResult && chainTimestamp && editorRef.current) {
            // Process only once per timestamp
            const processedKey = `chainbuilder_processed_${projectId}_${chainTimestamp}`;
            if (sessionStorage.getItem(processedKey)) {
                return;
            }

            // Insert result using utility
            insertChainBuilderResult(editorRef.current, chainResult)
                .then(() => {
                    // Mark as processed
                    sessionStorage.setItem(processedKey, "true");

                    // Clean up URL params
                    const newUrl = window.location.pathname;
                    window.history.replaceState({}, "", newUrl);

                    // Show success toast
                    toast.success("Chain builder result appended to story");

                    // Save the updated content
                    if (selectedChapter && editorRef.current) {
                        const updatedJson = JSON.stringify(
                            editorRef.current.getEditorState().toJSON(),
                        );
                        smartSave(selectedChapter.order, updatedJson, "manual");
                    }
                })
                .catch((error) => {
                    console.error(
                        "Failed to insert chain builder result:",
                        error,
                    );
                    toast.error("Failed to append chain builder result");
                });
        }
    }, [projectId, selectedChapter, smartSave]);

    // Handle focus out save - only save if content has changed
    const handleEditorBlur = useCallback(() => {
        console.log("Editor blur event", {
            hasSelectedChapter: !!selectedChapter,
            isInteracting,
            isStreaming,
            isPipelineLocked,
            contentLength: (content ?? "").length, // Handle null content
        });
        if (
            selectedChapter &&
            !isInteracting &&
            !isStreaming &&
            !isPipelineLocked
        ) {
            smartSave(selectedChapter.order, content, "manual");
        }
    }, [
        selectedChapter,
        content,
        smartSave,
        isInteracting,
        isStreaming,
        isPipelineLocked,
    ]);

    // Add Chapter Dialog state
    const [addChapterDialogOpen, setAddChapterDialogOpen] = useState(false);
    const [newChapterName, setNewChapterName] = useState("");
    const [addChapterLoading, setAddChapterLoading] = useState(false);
    const [addChapterError, setAddChapterError] = useState<string>("");

    // Handler for adding a new chapter
    const handleAddChapterClick = async () => {
        if (isPipelineLocked) {
            toast.error(
                lockMessage,
            );
            return;
        }
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
            } else if (typeof error === "string") {
                setAddChapterError(error);
            } else {
                setAddChapterError("Failed to add chapter. Please try again.");
            }
        } finally {
            setAddChapterLoading(false);
        }
    };

    // Get existing chapter names for validation
    const existingChapterNames = localChapters.map((ch) => ch.chapter_name);

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

    // Chapter edit/delete state
    const [editChapterDialogOpen, setEditChapterDialogOpen] = useState(false);
    const [editingChapter, setEditingChapter] = useState<ProjectChapter | null>(
        null,
    );
    const [editingChapterName, setEditingChapterName] = useState("");
    const [editChapterLoading, setEditChapterLoading] = useState(false);
    const [editChapterError, setEditChapterError] = useState<string>("");

    // Handle edit chapter
    const handleEditChapter = (chapter: ProjectChapter) => {
        setEditingChapter(chapter);
        setEditingChapterName(chapter.chapter_name);
        setEditChapterError("");
        setEditChapterDialogOpen(true);
    };

    const handleSaveChapterEdit = async () => {
        if (isPipelineLocked) {
            toast.error(
                lockMessage,
            );
            return;
        }
        if (!editingChapter || !editingChapterName.trim()) return;

        setEditChapterError("");
        setEditChapterLoading(true);

        try {
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/chapter/${editingChapter.order}`,
                {
                    method: "PATCH",
                    data: {
                        chapter_name: editingChapterName.trim(),
                    },
                },
            );

            if (response.status >= 200 && response.status < 300) {
                // Reload the page to get updated chapters
                router.reload();
                setEditChapterDialogOpen(false);
                setEditingChapter(null);
                setEditingChapterName("");
            } else {
                const error = response.data;
                setEditChapterError(error.error || "Failed to update chapter");
            }
        } catch (error: any) {
            console.error("Failed to update chapter:", error);
            setEditChapterError("Failed to update chapter. Please try again.");
        } finally {
            setEditChapterLoading(false);
        }
    };

    // Handle delete chapter
    const handleDeleteChapter = async (chapter: ProjectChapter) => {
        if (isPipelineLocked) {
            toast.error(
                lockMessage,
            );
            return;
        }
        if (
            !confirm(
                `Are you sure you want to delete "${chapter.chapter_name}"? This cannot be undone.`,
            )
        ) {
            return;
        }

        try {
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/chapter/${chapter.order}`,
                {
                    method: "DELETE",
                    headers: {
                        Accept: "application/json",
                    },
                },
            );

            if (response.status >= 200 && response.status < 300) {
                // Reload the page to get updated chapters
                router.reload();
            } else {
                const error = response.data;
                alert(error.error || "Failed to delete chapter");
            }
        } catch (error: any) {
            console.error("Failed to delete chapter:", error);
            alert("Failed to delete chapter. Please try again.");
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
            if (isPipelineLocked) {
                toast.error(
                    lockMessage,
                );
                return;
            }
            handleRegenerateText();
        },
    };

    // Callback for applying story fixes from the auditor
    // Auto-applies the fix and returns success/failure (no confirmation dialog needed)
    // NOTE: This is async to ensure sequential application of batch fixes
    const handleApplyStoryFix = useCallback(
        async (oldText: string, newText: string): Promise<boolean> => {
            console.log("[StoryFix] handleApplyStoryFix called");
            console.log("[StoryFix] oldText:", oldText?.substring(0, 100));

            const editor = editorRef.current;
            if (!editor) {
                console.warn("[StoryFix] No editor reference");
                return false;
            }

            // Get PLAIN TEXT from editor (not Lexical JSON)
            const plainContent = getPlainTextFromEditor(editor);
            if (!plainContent) {
                console.warn("[StoryFix] No content in editor");
                return false;
            }

            console.log("[StoryFix] Content length:", plainContent.length);

            // Helper function to apply the replacement - now properly async
            const applyReplacement = async (
                textToReplace: string,
            ): Promise<boolean> => {
                const result = await replaceTextInLexicalEditor(
                    editor,
                    textToReplace,
                    newText,
                );
                if (result.success && selectedChapter) {
                    console.log("[StoryFix] Replacement successful, saving...");
                    // Small delay for Lexical to process the update
                    await new Promise((resolve) => setTimeout(resolve, 100));
                    const updatedJson = JSON.stringify(
                        editor.getEditorState().toJSON(),
                    );
                    smartSave(selectedChapter.order, updatedJson, "manual");
                    return true;
                } else if (!result.success) {
                    console.error(
                        "[StoryFix] Replacement failed:",
                        result.error,
                    );
                }
                return false;
            };

            // Strategy 1: Exact match - auto-apply
            if (plainContent.includes(oldText)) {
                console.log("[StoryFix] Found exact match! Auto-applying...");
                return await applyReplacement(oldText);
            }

            // Strategy 2: Fuzzy match - auto-apply
            console.log("[StoryFix] Trying fuzzy match...");
            const match = findBestMatch(plainContent, oldText);

            if (match.found && match.confidence >= 0.5) {
                console.log(
                    `[StoryFix] Found match with ${(match.confidence * 100).toFixed(0)}% confidence. Auto-applying...`,
                );
                return await applyReplacement(match.matchedText);
            }

            // Low confidence (<50%) or not found - return false
            console.warn(
                "[StoryFix] Could not find text - match confidence too low or not found",
            );
            console.log(
                "[StoryFix] Best match confidence:",
                match.found
                    ? `${(match.confidence * 100).toFixed(0)}%`
                    : "No match",
            );
            console.log(
                "[StoryFix] Old text preview:",
                oldText.substring(0, 200),
            );
            return false;
        },
        [selectedChapter, smartSave],
    );

    // Wrapper for LexicalEditor's inline diff - now just forwards to handleApplyStoryFix
    // For inline editing, auto-apply matches (user can undo via Lexical history)
    const handleInlineApplyEdit = useCallback(
        async (oldText: string, newText: string): Promise<boolean> => {
            return await handleApplyStoryFix(oldText, newText);
        },
        [handleApplyStoryFix],
    );

    return (
        <PendingEditsProvider>
            <ProjectEditorLayout
                project={project}
                projectId={projectId}
                workspaceId={workspaceId}
                isSaving={isCombinedSaving}
                setIsSaving={() => {}} // No longer needed since saves are async
            >
                <Head title="Project Editor" />

                <EditorSidebar
                    settings={settings}
                    onSettingChange={handleSettingChange}
                    workspaceId={workspaceId}
                    projectId={projectId}
                    authorStyles={authorStyles}
                    projectPipelineLock={projectPipelineLock}
                    onApplyStoryFix={handleApplyStoryFix}
                    onSavingChange={handleExternalSavingChange}
                >
                    {projectPipelineLock?.isLocked && (
                        <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                            {lockMessage} Phase:{" "}
                            {projectPipelineLock.phase.replaceAll("_", " ")}.
                        </div>
                    )}
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
                                        disabled={
                                            isGenerating || isPipelineLocked
                                        }
                                    >
                                        <p className="truncate">
                                            {selectedChapter
                                                ? selectedChapter.chapter_name
                                                : "Select Chapter"}
                                        </p>
                                        <ChevronDown className="h-4 w-4" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent
                                    align="start"
                                    className="w-64"
                                >
                                    <DropdownMenuRadioGroup
                                        value={selectedChapterOrder.toString()}
                                        onValueChange={(value) =>
                                            handleChapterSelect(parseInt(value))
                                        }
                                    >
                                        {localChapters.length > 0 ? (
                                            localChapters.map(
                                                (chapter, index) => (
                                                    <div
                                                        key={index}
                                                        className="group"
                                                    >
                                                        <DropdownMenuRadioItem
                                                            value={chapter.order.toString()}
                                                            disabled={
                                                                isGenerating ||
                                                                isPipelineLocked
                                                            }
                                                            className="flex items-center justify-between"
                                                        >
                                                            <span className="flex-1">
                                                                {
                                                                    chapter.chapter_name
                                                                }
                                                            </span>
                                                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                                <Button
                                                                    variant="ghost"
                                                                    size="icon"
                                                                    className="h-6 w-6"
                                                                    onPointerDown={(
                                                                        e,
                                                                    ) =>
                                                                        e.stopPropagation()
                                                                    }
                                                                    onClick={(
                                                                        e,
                                                                    ) => {
                                                                        e.preventDefault();
                                                                        e.stopPropagation();
                                                                        handleEditChapter(
                                                                            chapter,
                                                                        );
                                                                    }}
                                                                    disabled={
                                                                        isGenerating ||
                                                                        isPipelineLocked
                                                                    }
                                                                >
                                                                    <Edit className="h-3 w-3" />
                                                                </Button>
                                                                <Button
                                                                    variant="ghost"
                                                                    size="icon"
                                                                    className="h-6 w-6 text-red-500 hover:text-red-700"
                                                                    onPointerDown={(
                                                                        e,
                                                                    ) =>
                                                                        e.stopPropagation()
                                                                    }
                                                                    onClick={(
                                                                        e,
                                                                    ) => {
                                                                        e.preventDefault();
                                                                        e.stopPropagation();
                                                                        handleDeleteChapter(
                                                                            chapter,
                                                                        );
                                                                    }}
                                                                    disabled={
                                                                        isGenerating ||
                                                                        isPipelineLocked
                                                                    }
                                                                >
                                                                    <Trash2 className="h-3 w-3" />
                                                                </Button>
                                                            </div>
                                                        </DropdownMenuRadioItem>
                                                    </div>
                                                ),
                                            )
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
                                disabled={isGenerating || isPipelineLocked}
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
                                workspaceId={workspaceId}
                                projectId={projectId}
                            />
                        </div>
                    </div>

                    {/* Edit Chapter Dialog */}
                    <Dialog
                        open={editChapterDialogOpen}
                        onOpenChange={setEditChapterDialogOpen}
                    >
                        <DialogContent>
                            <DialogHeader>
                                <DialogTitle>Edit Chapter</DialogTitle>
                                <DialogDescription>
                                    Update the chapter name. This will not
                                    affect the chapter content.
                                </DialogDescription>
                            </DialogHeader>
                            <div className="space-y-4 py-4">
                                <div>
                                    <label className="text-sm font-medium">
                                        Chapter Name
                                    </label>
                                    <div className="flex gap-2 mt-1">
                                        <Input
                                            value={editingChapterName}
                                            onChange={(e) => {
                                                setEditingChapterName(
                                                    e.target.value,
                                                );
                                                setEditChapterError("");
                                            }}
                                            placeholder="Enter chapter name"
                                            className="flex-1"
                                            disabled={editChapterLoading}
                                        />
                                        <MagicWandButton
                                            text={editingChapterName}
                                            onEnhanced={(enhanced) => {
                                                setEditingChapterName(enhanced);
                                                setEditChapterError("");
                                            }}
                                            enhancementMode="chapter_name"
                                            workspaceId={workspaceId}
                                            projectId={projectId}
                                            disabled={editChapterLoading}
                                            size="icon"
                                            variant="outline"
                                            chapterContent={
                                                editingChapter?.content || ""
                                            }
                                        />
                                    </div>
                                    {editChapterError && (
                                        <p className="text-sm text-red-500 mt-1">
                                            {editChapterError}
                                        </p>
                                    )}
                                </div>
                            </div>
                            <DialogFooter>
                                <Button
                                    variant="outline"
                                    onClick={() => {
                                        setEditChapterDialogOpen(false);
                                        setEditingChapter(null);
                                        setEditingChapterName("");
                                        setEditChapterError("");
                                    }}
                                    disabled={editChapterLoading}
                                >
                                    Cancel
                                </Button>
                                <Button
                                    onClick={handleSaveChapterEdit}
                                    disabled={
                                        editChapterLoading ||
                                        !editingChapterName.trim()
                                    }
                                >
                                    {editChapterLoading ? "Saving..." : "Save"}
                                </Button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>

                    <div className="flex-1 relative overflow-hidden">
                        <LexicalEditor
                            content={content}
                            setContent={setContent}
                            isStreaming={isStreaming}
                            streamingText={streamingText}
                            baseContent={baseContent}
                            isColorCoded={isColorCoded}
                            selectedChapter={selectedChapter}
                            isInteracting={isInteracting}
                            setIsInteracting={setIsInteracting}
                            isRegenerating={isRegenerating}
                            onBlur={handleEditorBlur}
                            onGetCurrentContent={(getter) => {
                                getCurrentEditorContentRef.current = getter;
                            }}
                            workspaceId={workspaceId}
                            projectId={projectId}
                            aiModel={settings.aiModel}
                            selectionToolbarMode={settings.selectionToolbarMode}
                            onApplyEdit={handleInlineApplyEdit}
                            editorRef={editorRef}
                        />
                        {projectPipelineLock?.isLocked && (
                            <div className="absolute inset-0 z-20 cursor-not-allowed bg-white/35" />
                        )}

                        <div className="absolute left-0 bottom-0 w-full p-4">
                            <EditorToolbar
                                onSend={() => {
                                    if (isPipelineLocked) {
                                        toast.error(
                                            lockMessage,
                                        );
                                        return;
                                    }
                                    // Get current editor content directly before generating
                                    const currentEditorContent =
                                        getCurrentEditorContentRef.current?.() ??
                                        content ??
                                        "";
                                    handleGenerateText(currentEditorContent);
                                }}
                                isGenerating={isGenerating}
                                versionControl={versionControlState}
                                isColorCoded={isColorCoded}
                                onToggleColorCoding={() => {
                                    if (typeof setIsColorCoded === "function") {
                                        setIsColorCoded(!isColorCoded);
                                    }
                                }}
                                workspaceId={workspaceId}
                                projectId={projectId}
                                wordCount={getWordCount(content)}
                                onBeforeNavigate={flushSettingsBeforeNavigation}
                                isLocked={isPipelineLocked}
                            />
                        </div>
                    </div>
                </EditorSidebar>
            </ProjectEditorLayout>
        </PendingEditsProvider>
    );
}

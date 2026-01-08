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
    DropdownMenuSeparator,
    DropdownMenuSub,
    DropdownMenuSubContent,
    DropdownMenuSubTrigger,
} from "@/Components/ui/dropdown-menu";
import { Input } from "@/Components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/Components/ui/dialog";
import { Edit, Trash2 } from "lucide-react";
import { PageProps, Project, ProjectChapter } from "@/types";
import AddChapterDialog from "./Partials/AddChapterDialog";
import { useProjectEditor } from "./hooks";
import { PendingEditsProvider } from "./contexts/PendingEditsContext";
import { MagicWandButton } from "@/Components/MagicWandButton";
import { findBestMatch } from "./utils/fuzzyTextMatch";
import { getPlainTextFromEditor, replaceTextInLexicalEditor } from "./utils/lexicalTextReplace";

// Import Echo for WebSocket connection
import "@/echo";

/**
 * Check if content is valid Lexical JSON format
 */
function isLexicalJSON(content: string): boolean {
    if (!content?.trim().startsWith('{')) return false;
    try {
        const parsed = JSON.parse(content);
        return parsed.root?.type === 'root';
    } catch {
        return false;
    }
}

/**
 * Extract plain text from Lexical JSON node recursively
 */
function extractTextFromNode(node: any): string {
    if (!node) return '';

    // Text node - return its text content
    if (node.type === 'text' || node.type === 'origin-text') {
        return node.text || '';
    }

    // For container nodes, process children
    if (node.children && Array.isArray(node.children)) {
        return node.children.map((child: any, index: number) => {
            const text = extractTextFromNode(child);
            // Add paragraph breaks between paragraphs
            if (child.type === 'paragraph' && index < node.children.length - 1) {
                return text + '\n\n';
            }
            return text;
        }).join('');
    }

    return '';
}

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
            .replace(/[#*_`~\[\]()]/g, '') // Remove markdown syntax
            .replace(/\n+/g, ' ');
    }

    const cleaned = plainText.replace(/\n+/g, ' ').trim();
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
    const { errors, authorStyles: rawAuthorStyles } = usePage().props;
    
    // Get author styles from page props (provided by controller)
    // Controller sends: { id, name, status, avatar, color }
    const authorStyles = (rawAuthorStyles as Array<{ id: string; name: string; status?: string }> | undefined)?.map(style => ({
        id: style.id,
        name: style.name,
        status: style.status,
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
        streamError,
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
        handleCancelGeneration,
        saveContent,
        smartSave,
    } = useProjectEditor({
        workspaceId,
        projectId,
        project,
        initialChapters: chapters,
        editorRef,
    });

    // State to prevent saves during UI interactions
    const [isInteracting, setIsInteracting] = useState(false);
    
    // Ref to get current editor content
    const getCurrentEditorContentRef = useRef<(() => string) | null>(null);

    // Check for pending chainbuilder result
    useEffect(() => {
        const resultKey = `chainbuilder_result_${projectId}`;
        const timestampKey = `chainbuilder_result_timestamp_${projectId}`;
        
        const result = localStorage.getItem(resultKey);
        const timestamp = localStorage.getItem(timestampKey);
        
        // Only apply if result is recent (within last 5 minutes)
        if (result && timestamp && selectedChapter) {
            const resultAge = Date.now() - parseInt(timestamp);
            if (resultAge < 5 * 60 * 1000) { // 5 minutes
                // Get current content - try ref first, then fallback to state
                // Use a small delay to ensure ref is set
                setTimeout(() => {
                const currentContent = getCurrentEditorContentRef.current?.() ?? content ?? '';
                    
                    // FIX: Remove any overlap between current content and result
                    // The result might already include some of the current content if it was in story context
                    let cleanResult = result.trim();
                    
                    // Only append if we have current content (don't replace empty chapter)
                    if (currentContent.trim()) {
                        // Check if result starts with current content (duplication)
                        const currentTrimmed = currentContent.trim();
                        if (cleanResult.startsWith(currentTrimmed)) {
                            // Result already includes current content, strip it
                            cleanResult = cleanResult.slice(currentTrimmed.length).trimStart();
                        } else {
                            // Check for partial overlap at the end of current content
                            // Look for the last few words/sentences of current content in the result
                            const currentWords = currentTrimmed.split(/\s+/).filter(Boolean);
                            const resultWords = cleanResult.split(/\s+/).filter(Boolean);
                            
                            // Check if result starts with tail of current content (overlap)
                            if (currentWords.length > 0 && resultWords.length > 0) {
                                // Check last 10 words of current content
                                const tailWords = currentWords.slice(-10).join(' ');
                                if (tailWords && cleanResult.startsWith(tailWords)) {
                                    cleanResult = cleanResult.slice(tailWords.length).trimStart();
                                }
                            }
                        }
                        
                        // Only append if we have new content to add
                        if (cleanResult) {
                            const separator = currentContent && !currentContent.endsWith('\n') && !currentContent.endsWith(' ')
                                ? '\n\n'
                                : '';
                            const appendedText = separator + cleanResult;
                            const newContent = currentContent + appendedText;

                            // Update content - AI origin is now tracked via OriginTextNode metadata
                            setContent(newContent);

                            if (selectedChapter) {
                                smartSave(selectedChapter.order, newContent, 'manual');
                            }
                        }
                        // If cleanResult is empty after deduplication, don't append anything
                    } else {
                        // If chapter is empty, just set the content (no append needed)
                        setContent(cleanResult);

                        if (selectedChapter) {
                            smartSave(selectedChapter.order, cleanResult, 'manual');
                        }
                    }

                // Clear the stored result
                localStorage.removeItem(resultKey);
                localStorage.removeItem(timestampKey);
                }, 100); // Small delay to ensure ref is set
            } else {
                // Clear old result
                localStorage.removeItem(resultKey);
                localStorage.removeItem(timestampKey);
            }
        }
    }, [projectId, content, setContent, selectedChapter, smartSave]);

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

    // Chapter edit/delete state
    const [editChapterDialogOpen, setEditChapterDialogOpen] = useState(false);
    const [editingChapter, setEditingChapter] = useState<ProjectChapter | null>(null);
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
        if (!editingChapter || !editingChapterName.trim()) return;

        setEditChapterError("");
        setEditChapterLoading(true);

        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/chapter/${editingChapter.order}`,
                {
                    method: "PATCH",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                    body: JSON.stringify({
                        chapter_name: editingChapterName.trim(),
                    }),
                }
            );

            if (response.ok) {
                const data = await response.json();
                // Reload the page to get updated chapters
                router.reload();
                setEditChapterDialogOpen(false);
                setEditingChapter(null);
                setEditingChapterName("");
            } else {
                const error = await response.json();
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
        if (!confirm(`Are you sure you want to delete "${chapter.chapter_name}"? This cannot be undone.`)) {
            return;
        }

        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/chapter/${chapter.order}`,
                {
                    method: "DELETE",
                    headers: {
                        "Accept": "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                }
            );

            if (response.ok) {
                // Reload the page to get updated chapters
                router.reload();
            } else {
                const error = await response.json();
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

    // Callback for applying story fixes from the auditor
    // Auto-applies the fix and returns success/failure (no confirmation dialog needed)
    const handleApplyStoryFix = useCallback((oldText: string, newText: string): boolean => {
        console.log('[StoryFix] handleApplyStoryFix called');
        console.log('[StoryFix] oldText:', oldText?.substring(0, 100));

        const editor = editorRef.current;
        if (!editor) {
            console.warn('[StoryFix] No editor reference');
            return false;
        }

        // Get PLAIN TEXT from editor (not Lexical JSON)
        const plainContent = getPlainTextFromEditor(editor);
        if (!plainContent) {
            console.warn('[StoryFix] No content in editor');
            return false;
        }

        console.log('[StoryFix] Content length:', plainContent.length);

        // Helper function to apply the replacement
        const applyReplacement = (textToReplace: string) => {
            replaceTextInLexicalEditor(editor, textToReplace, newText).then(result => {
                if (result.success && selectedChapter) {
                    console.log('[StoryFix] Replacement successful, saving...');
                    setTimeout(() => {
                        const updatedJson = JSON.stringify(editor.getEditorState().toJSON());
                        smartSave(selectedChapter.order, updatedJson, 'manual');
                    }, 100);
                } else if (!result.success) {
                    console.error('[StoryFix] Replacement failed:', result.error);
                }
            });
        };

        // Strategy 1: Exact match - auto-apply
        if (plainContent.includes(oldText)) {
            console.log('[StoryFix] Found exact match! Auto-applying...');
            applyReplacement(oldText);
            return true;
        }

        // Strategy 2: Fuzzy match - auto-apply
        console.log('[StoryFix] Trying fuzzy match...');
        const match = findBestMatch(plainContent, oldText);

        if (match.found && match.confidence >= 0.50) {
            console.log(`[StoryFix] Found match with ${(match.confidence * 100).toFixed(0)}% confidence. Auto-applying...`);
            applyReplacement(match.matchedText);
            return true;
        }

        // Low confidence (<50%) or not found - return false
        console.warn('[StoryFix] Could not find text - match confidence too low or not found');
        console.log('[StoryFix] Best match confidence:', match.found ? `${(match.confidence * 100).toFixed(0)}%` : 'No match');
        console.log('[StoryFix] Old text preview:', oldText.substring(0, 200));
        return false;
    }, [selectedChapter, smartSave]);

    // Wrapper for LexicalEditor's inline diff - now just forwards to handleApplyStoryFix
    // For inline editing, auto-apply matches (user can undo via Lexical history)
    const handleInlineApplyEdit = useCallback((oldText: string, newText: string): boolean => {
        return handleApplyStoryFix(oldText, newText);
    }, [handleApplyStoryFix]);

    return (
        <PendingEditsProvider>
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
                onApplyStoryFix={handleApplyStoryFix}
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
                            <DropdownMenuContent align="start" className="w-64">
                                <DropdownMenuRadioGroup
                                    value={selectedChapterOrder.toString()}
                                    onValueChange={(value) =>
                                        handleChapterSelect(parseInt(value))
                                    }
                                >
                                    {localChapters.length > 0 ? (
                                        localChapters.map((chapter, index) => (
                                            <div key={index} className="group">
                                                <DropdownMenuRadioItem
                                                    value={chapter.order.toString()}
                                                    disabled={isGenerating}
                                                    className="flex items-center justify-between"
                                                >
                                                    <span className="flex-1">{chapter.chapter_name}</span>
                                                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            className="h-6 w-6"
                                                            onPointerDown={(e) => e.stopPropagation()}
                                                            onClick={(e) => {
                                                                e.preventDefault();
                                                                e.stopPropagation();
                                                                handleEditChapter(chapter);
                                                            }}
                                                            disabled={isGenerating}
                                                        >
                                                            <Edit className="h-3 w-3" />
                                                        </Button>
                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            className="h-6 w-6 text-red-500 hover:text-red-700"
                                                            onPointerDown={(e) => e.stopPropagation()}
                                                            onClick={(e) => {
                                                                e.preventDefault();
                                                                e.stopPropagation();
                                                                handleDeleteChapter(chapter);
                                                            }}
                                                            disabled={isGenerating}
                                                        >
                                                            <Trash2 className="h-3 w-3" />
                                                        </Button>
                                                    </div>
                                                </DropdownMenuRadioItem>
                                            </div>
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
                            workspaceId={workspaceId}
                            projectId={projectId}
                        />
                    </div>
                </div>

                {/* Edit Chapter Dialog */}
                <Dialog open={editChapterDialogOpen} onOpenChange={setEditChapterDialogOpen}>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Edit Chapter</DialogTitle>
                            <DialogDescription>
                                Update the chapter name. This will not affect the chapter content.
                            </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                            <div>
                                <label className="text-sm font-medium">Chapter Name</label>
                                <div className="flex gap-2 mt-1">
                                    <Input
                                        value={editingChapterName}
                                        onChange={(e) => {
                                            setEditingChapterName(e.target.value);
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
                                        chapterContent={editingChapter?.content || ''}
                                    />
                                </div>
                                {editChapterError && (
                                    <p className="text-sm text-red-500 mt-1">{editChapterError}</p>
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
                                disabled={editChapterLoading || !editingChapterName.trim()}
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
                            workspaceId={workspaceId}
                            projectId={projectId}
                            wordCount={getWordCount(content)}
                        />
                    </div>
                </div>
            </EditorSidebar>
        </ProjectEditorLayout>
        </PendingEditsProvider>
    );
}

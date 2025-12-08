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
    // Returns true if the fix was successfully applied to the editor
    const handleApplyStoryFix = useCallback((oldText: string, newText: string): boolean => {
        console.log('[StoryFix] handleApplyStoryFix called');
        console.log('[StoryFix] oldText:', oldText?.substring(0, 100));
        
        if (!content) {
            console.warn('[StoryFix] No content available in editor');
            return false;
        }
        
        // Normalize text for comparison - aggressive normalization
        const normalizeText = (text: string): string => {
            return text
                .replace(/[\u2018\u2019\u201A\u201B\u2032\u2035']/g, "'")
                .replace(/[\u201C\u201D\u201E\u201F\u2033\u2036"]/g, '"')
                .replace(/[\u2014\u2015\u2012\u2013—–-]/g, '-')
                .replace(/\u2026/g, '...')
                .replace(/\u00A0/g, ' ')
                .replace(/\r\n/g, '\n')
                .replace(/\r/g, '\n');
        };
        
        // Even more aggressive - collapse whitespace
        const superNormalize = (text: string): string => {
            return normalizeText(text)
                .replace(/\n+/g, ' ')
                .replace(/\s+/g, ' ')
                .trim()
                .toLowerCase();
        };
        
        const normalizedContent = normalizeText(content);
        const normalizedOldText = normalizeText(oldText);
        
        // Strategy 1: Exact match
        if (content.includes(oldText)) {
            console.log('[StoryFix] Found exact match!');
            const newContent = content.replace(oldText, newText);
            setContent(newContent);
            if (selectedChapter) {
                smartSave(selectedChapter.order, newContent, 'manual');
            }
            return true;
        }
        
        // Strategy 2: Normalized match (preserves newlines)
        if (normalizedContent.includes(normalizedOldText)) {
            console.log('[StoryFix] Found normalized match!');
            const idx = normalizedContent.indexOf(normalizedOldText);
            const newContent = normalizedContent.substring(0, idx) + newText + normalizedContent.substring(idx + normalizedOldText.length);
            setContent(newContent);
            if (selectedChapter) {
                smartSave(selectedChapter.order, newContent, 'manual');
            }
            return true;
        }
        
        // Strategy 3: Line-by-line search with fuzzy matching
        console.log('[StoryFix] Trying line-by-line search...');
        const contentLines = content.split('\n');
        const oldTextSuper = superNormalize(oldText);
        
        // Find lines that might contain our text
        for (let i = 0; i < contentLines.length; i++) {
            const lineSuper = superNormalize(contentLines[i]);
            
            // Check if the first part of oldText appears in this line
            const oldTextFirstWords = oldTextSuper.split(' ').slice(0, 5).join(' ');
            if (lineSuper.includes(oldTextFirstWords)) {
                console.log('[StoryFix] Found potential match at line', i);
                
                // Try to match from this line onwards
                let combinedLines = '';
                let endLineIdx = i;
                
                for (let j = i; j < Math.min(i + 10, contentLines.length); j++) {
                    combinedLines += (j > i ? '\n' : '') + contentLines[j];
                    const combinedSuper = superNormalize(combinedLines);
                    
                    if (combinedSuper.includes(oldTextSuper) || oldTextSuper.includes(combinedSuper.substring(0, oldTextSuper.length))) {
                        endLineIdx = j;
                        
                        // Found a match - replace these lines
                        const newContentLines = [
                            ...contentLines.slice(0, i),
                            newText,
                            ...contentLines.slice(endLineIdx + 1)
                        ];
                        const newContent = newContentLines.join('\n');
                        console.log('[StoryFix] Applied via line replacement');
                        setContent(newContent);
                        if (selectedChapter) {
                            smartSave(selectedChapter.order, newContent, 'manual');
                        }
                        return true;
                    }
                }
            }
        }
        
        // Strategy 4: Substring match (if oldText is long, try first 100 chars)
        if (oldText.length > 100) {
            const partialOld = superNormalize(oldText.substring(0, 100));
            const contentSuper = superNormalize(content);
            
            if (contentSuper.includes(partialOld)) {
                console.log('[StoryFix] Found partial match, doing aggressive replace');
                // Find the approximate position
                const idx = contentSuper.indexOf(partialOld);
                const ratio = content.length / contentSuper.length;
                const approxStart = Math.max(0, Math.floor(idx * ratio) - 20);
                
                // Find the end by looking for newlines or sentence endings
                let approxEnd = Math.min(content.length, approxStart + oldText.length + 100);
                
                // Try to find a clean break point
                const afterText = content.substring(approxStart + oldText.length - 50, approxEnd + 100);
                const periodIdx = afterText.indexOf('. ');
                const newlineIdx = afterText.indexOf('\n');
                
                if (periodIdx > 0 && periodIdx < 150) {
                    approxEnd = approxStart + oldText.length - 50 + periodIdx + 2;
                } else if (newlineIdx > 0 && newlineIdx < 150) {
                    approxEnd = approxStart + oldText.length - 50 + newlineIdx;
                }
                
                const newContent = content.substring(0, approxStart) + newText + content.substring(approxEnd);
                setContent(newContent);
                if (selectedChapter) {
                    smartSave(selectedChapter.order, newContent, 'manual');
                }
                return true;
            }
        }
        
        console.warn('[StoryFix] Could not find old text - all strategies failed');
        console.log('[StoryFix] Old text preview:', oldText.substring(0, 200));
        return false;
    }, [content, setContent, selectedChapter, smartSave]);

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
                        workspaceId={workspaceId}
                        projectId={projectId}
                        aiModel={settings.aiModel}
                        selectionToolbarMode={settings.selectionToolbarMode}
                        onApplyEdit={handleApplyStoryFix}
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
        </PendingEditsProvider>
    );
}

import { useState } from "react";
import { Button } from "@/Components/ui/button";
import { Badge } from "@/Components/ui/badge";
import { Checkbox } from "@/Components/ui/checkbox";
import { Label } from "@/Components/ui/label";
import {
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/Components/ui/accordion";
import {
    BookOpen,
    Loader2,
    Wand2,
    CheckSquare,
    ChevronDown,
    ChevronRight,
} from "lucide-react";
import type {
    ConsistencyIssue,
    ScanStatus,
    StoryTextPreviewData,
    BatchFixItem,
} from "./types";
import { getSeverityColor, getIssueTypeColor, postJson } from "./utils";
import { http } from "@/Lib/http";
import StoryFixPreviewDialog from "./Shared/StoryFixPreviewDialog";
import BatchStoryFixPreviewDialog from "./Shared/BatchStoryFixPreviewDialog";

interface StoryConsistencySectionProps {
    workspaceId: string;
    projectId: string;
    selectedModel: string;
    scanStatus: ScanStatus | null;
    // Persisted state from parent
    storyIssues: ConsistencyIssue[];
    onStoryIssuesChange: (issues: ConsistencyIssue[]) => void;
    // External callback for applying fixes to the editor (auto-applies, returns success/failure)
    onApplyStoryFix?: (oldText: string, newText: string) => Promise<boolean>;
}

export default function StoryConsistencySection({
    workspaceId,
    projectId,
    selectedModel,
    scanStatus,
    storyIssues,
    onStoryIssuesChange,
    onApplyStoryFix,
}: StoryConsistencySectionProps) {
    const [loadingStoryCheck, setLoadingStoryCheck] = useState(false);
    const [selectedStoryIssues, setSelectedStoryIssues] = useState<Set<number>>(
        new Set(),
    );
    const [applyingStoryFix, setApplyingStoryFix] = useState<number | null>(
        null,
    );
    const [applyingAllStory, setApplyingAllStory] = useState(false);
    const [expandedStoryIssues, setExpandedStoryIssues] = useState<Set<number>>(
        new Set(),
    );
    const [previewMode, setPreviewMode] = useState(true);

    // Chapter selection
    const [storyCheckMode, setStoryCheckMode] = useState<"all" | "selected">(
        "all",
    );
    const [selectedChapters, setSelectedChapters] = useState<Set<number>>(
        new Set(),
    );

    // Story text preview (single fix)
    const [storyTextPreview, setStoryTextPreview] =
        useState<StoryTextPreviewData | null>(null);
    const [editedStoryText, setEditedStoryText] = useState("");

    // Batch fix state
    const [batchFixes, setBatchFixes] = useState<BatchFixItem[]>([]);
    const [batchDialogOpen, setBatchDialogOpen] = useState(false);
    const [applyingBatch, setApplyingBatch] = useState(false);

    const handleStoryConsistencyCheck = async () => {
        setLoadingStoryCheck(true);
        onStoryIssuesChange([]);

        // Build request payload - only include chapter_orders when specific chapters are selected
        const payload: Record<string, any> = {
            model: selectedModel,
            provider: "gemini",
        };

        if (storyCheckMode === "selected" && selectedChapters.size > 0) {
            payload.chapter_orders = Array.from(selectedChapters);
        }

        try {
            const response = await postJson(
                `/${workspaceId}/projects/${projectId}/editor/auditor/check-consistency/story`,
                payload,
            );
            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                onStoryIssuesChange(data.results?.issues || []);
            }
        } catch (error) {
            console.error("Error checking story consistency:", error);
        } finally {
            setLoadingStoryCheck(false);
        }
    };

    const handleApplyStoryTextFix = async (
        issue: ConsistencyIssue,
        index: number,
    ) => {
        setApplyingStoryFix(index);
        try {
            const response = await postJson(
                `/${workspaceId}/projects/${projectId}/editor/auditor/fix-story-text`,
                {
                    issue_type: issue.issue_type,
                    title: issue.title,
                    description: issue.description,
                    evidence: issue.evidence,
                    location: issue.location,
                    suggestion: issue.suggestion,
                    model: selectedModel,
                    provider: "gemini",
                },
            );
            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                if (data.success) {
                    const results = data.results;
                    setStoryTextPreview({
                        issue,
                        index,
                        oldText: results.old_text || "",
                        newText: results.new_text || "",
                        explanation: results.explanation || "",
                        chapterName:
                            results.chapter_name ||
                            issue.location ||
                            "Unknown Chapter",
                        chapterOrder: results.chapter_order ?? 0,
                        contentHash: results.content_hash || undefined, // Store hash for change detection
                    });
                    setEditedStoryText(results.new_text || "");
                } else {
                    alert(
                        `Failed to generate fix: ${data.error || "Unknown error"}`,
                    );
                }
            } else {
                const error = response.data;
                alert(
                    `Failed to generate fix: ${error.error || "Unknown error"}`,
                );
            }
        } catch (error) {
            console.error("Error generating story fix:", error);
            alert("Failed to generate fix");
        } finally {
            setApplyingStoryFix(null);
        }
    };

    const confirmStoryTextFix = async () => {
        if (!storyTextPreview) return;

        try {
            if (onApplyStoryFix) {
                // Auto-apply the fix (returns success/failure)
                const success = await onApplyStoryFix(
                    storyTextPreview.oldText,
                    editedStoryText,
                );

                if (success) {
                    alert(
                        `Fix applied to ${storyTextPreview.chapterName}! The editor has been updated.`,
                    );
                    // Remove from list
                    onStoryIssuesChange(
                        storyIssues.filter(
                            (_, i) => i !== storyTextPreview.index,
                        ),
                    );
                    setSelectedStoryIssues((prev) => {
                        const next = new Set(prev);
                        next.delete(storyTextPreview.index);
                        return next;
                    });
                } else {
                    alert(
                        `Could not find a match for the text. The chapter may have been edited since the fix was generated.`,
                    );
                }

                setStoryTextPreview(null);
                setEditedStoryText("");
                return;
            }

            // Fallback to direct API save (when onApplyStoryFix is not provided)
            const chapterOrder = storyTextPreview.chapterOrder;

            const chaptersResponse = await http(
                `/${workspaceId}/projects/${projectId}/editor/chapters`,
                { headers: { Accept: "application/json" } },
            );

            if (
                chaptersResponse.status >= 200 &&
                chaptersResponse.status < 300
            ) {
                const chaptersData = chaptersResponse.data;
                const chapters = chaptersData.chapters || [];
                const chapter =
                    chapters.find((c: any) => c.order === chapterOrder) ||
                    chapters[0];

                if (chapter && chapter.content) {
                    const normalizeText = (text: string): string => {
                        return text
                            .replace(/[\u2018\u2019\u201A\u201B]/g, "'")
                            .replace(/[\u201C\u201D\u201E\u201F]/g, '"')
                            .replace(/[\u2014\u2015]/g, "--")
                            .replace(/[\u2013]/g, "-")
                            .replace(/\u2026/g, "...")
                            .replace(/\u00A0/g, " ")
                            .replace(/\s+/g, " ")
                            .trim();
                    };

                    let newContent: string | null = null;
                    if (chapter.content.includes(storyTextPreview.oldText)) {
                        newContent = chapter.content.replace(
                            storyTextPreview.oldText,
                            editedStoryText,
                        );
                    } else {
                        const normalizedContent = normalizeText(
                            chapter.content,
                        );
                        const normalizedOldText = normalizeText(
                            storyTextPreview.oldText,
                        );

                        if (normalizedContent.includes(normalizedOldText)) {
                            const idx =
                                normalizedContent.indexOf(normalizedOldText);
                            const ratio =
                                chapter.content.length /
                                normalizedContent.length;
                            const start = Math.floor(idx * ratio);
                            const end = Math.ceil(
                                (idx + normalizedOldText.length) * ratio,
                            );
                            newContent =
                                chapter.content.substring(0, start) +
                                editedStoryText +
                                chapter.content.substring(end);
                        }
                    }

                    if (newContent && newContent !== chapter.content) {
                        const updateResponse = await http(
                            `/${workspaceId}/projects/${projectId}/editor/unified`,
                            {
                                method: "PATCH",
                                headers: {
                                    "Content-Type": "application/json",
                                    Accept: "application/json",
                                },
                                data: {
                                    content: {
                                        order: chapterOrder,
                                        content: newContent,
                                        trigger: "manual",
                                    },
                                },
                            },
                        );

                        if (
                            !(
                                updateResponse.status >= 200 &&
                                updateResponse.status < 300
                            )
                        ) {
                            throw new Error("Failed to save chapter");
                        }

                        alert(
                            `Fix applied to ${storyTextPreview.chapterName}! Please refresh to see changes.`,
                        );
                    } else {
                        alert(
                            "Text not found in chapter. The fix may have already been applied or the text has changed.",
                        );
                    }
                }
            }

            // Remove from list
            onStoryIssuesChange(
                storyIssues.filter((_, i) => i !== storyTextPreview.index),
            );
            setSelectedStoryIssues((prev) => {
                const next = new Set(prev);
                next.delete(storyTextPreview.index);
                return next;
            });

            setStoryTextPreview(null);
            setEditedStoryText("");
        } catch (error) {
            console.error("Error applying story fix:", error);
            alert(
                "Failed to apply fix: " +
                    (error instanceof Error ? error.message : "Unknown error"),
            );
        }
    };

    const handleApplyAllStorySelected = async () => {
        if (selectedStoryIssues.size === 0) {
            alert("Please select at least one issue to fix");
            return;
        }

        setApplyingAllStory(true);

        try {
            // Collect all selected issues
            const selectedIndices = Array.from(selectedStoryIssues);
            const issuesToFix = selectedIndices.map((idx) => ({
                ...storyIssues[idx],
                original_index: idx,
            }));

            // Call batch API
            const response = await postJson(
                `/${workspaceId}/projects/${projectId}/editor/auditor/batch-fix-story-text`,
                {
                    issues: issuesToFix,
                    model: selectedModel,
                    provider: "gemini",
                },
            );

            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                if (data.success && data.results?.fixes) {
                    // Transform to BatchFixItem array
                    const fixItems: BatchFixItem[] = data.results.fixes.map(
                        (fix: any) => ({
                            issueIndex: selectedIndices[fix.issue_index],
                            issue: storyIssues[
                                selectedIndices[fix.issue_index]
                            ],
                            oldText: fix.old_text,
                            newText: fix.new_text,
                            editedText: fix.new_text,
                            explanation: fix.explanation,
                            chapterOrder: fix.chapter_order,
                            chapterName: fix.chapter_name,
                            position: fix.position,
                            enabled: true,
                        }),
                    );

                    setBatchFixes(fixItems);
                    setBatchDialogOpen(true);
                } else if (data.results?.errors?.length > 0) {
                    alert(
                        `Some fixes could not be generated:\n${data.results.errors.join("\n")}`,
                    );
                }
            } else {
                const error = response.data;
                alert(
                    `Failed to generate fixes: ${error.error || "Unknown error"}`,
                );
            }
        } catch (error) {
            console.error("Error generating batch fixes:", error);
            alert("Failed to generate fixes");
        } finally {
            setApplyingAllStory(false);
        }
    };

    // Batch fix handlers
    const handleBatchFixEdit = (index: number, newText: string) => {
        setBatchFixes((prev) =>
            prev.map((fix, i) =>
                i === index ? { ...fix, editedText: newText } : fix,
            ),
        );
    };

    const handleBatchFixToggle = (index: number, enabled: boolean) => {
        setBatchFixes((prev) =>
            prev.map((fix, i) => (i === index ? { ...fix, enabled } : fix)),
        );
    };

    const handleBatchApply = async () => {
        setApplyingBatch(true);

        // Get enabled fixes, sorted by position DESC (apply bottom-to-top)
        // This ensures earlier fixes don't shift positions of later fixes
        const enabledFixes = batchFixes
            .filter((fix) => fix.enabled)
            .sort((a, b) => b.position - a.position);

        let successCount = 0;
        const failedFixes: string[] = [];
        const appliedIndices: number[] = [];

        // Apply fixes sequentially - each must complete before the next
        // This ensures the editor state is updated between fixes
        for (const fix of enabledFixes) {
            if (onApplyStoryFix) {
                const success = await onApplyStoryFix(
                    fix.oldText,
                    fix.editedText,
                );
                if (success) {
                    successCount++;
                    appliedIndices.push(fix.issueIndex);
                } else {
                    failedFixes.push(
                        fix.issue?.title || `Fix ${fix.issueIndex + 1}`,
                    );
                }
            }
        }

        // Remove successfully applied issues from list
        if (successCount > 0) {
            const appliedSet = new Set(appliedIndices);
            onStoryIssuesChange(
                storyIssues.filter((_, i) => !appliedSet.has(i)),
            );
            setSelectedStoryIssues(new Set());
        }

        setBatchDialogOpen(false);
        setBatchFixes([]);
        setApplyingBatch(false);

        // Show result
        if (failedFixes.length === 0) {
            alert(`Successfully applied ${successCount} fixes!`);
        } else {
            alert(
                `Applied ${successCount} fixes. Failed: ${failedFixes.join(", ")}`,
            );
        }
    };

    const toggleStoryIssueExpanded = (idx: number) => {
        setExpandedStoryIssues((prev) => {
            const next = new Set(prev);
            if (next.has(idx)) next.delete(idx);
            else next.add(idx);
            return next;
        });
    };

    const toggleStoryIssueSelected = (idx: number) => {
        setSelectedStoryIssues((prev) => {
            const next = new Set(prev);
            if (next.has(idx)) next.delete(idx);
            else next.add(idx);
            return next;
        });
    };

    const toggleSelectAllStoryIssues = () => {
        if (selectedStoryIssues.size === storyIssues.length) {
            setSelectedStoryIssues(new Set());
        } else {
            setSelectedStoryIssues(new Set(storyIssues.map((_, i) => i)));
        }
    };

    const isDisabled =
        loadingStoryCheck ||
        (storyCheckMode === "selected" && selectedChapters.size === 0);

    return (
        <>
            <AccordionItem value="story-consistency">
                <AccordionTrigger className="hover:no-underline">
                    <div className="flex items-center gap-2">
                        <BookOpen className="h-4 w-4 text-purple-600" />
                        <span className="font-medium">Story Consistency</span>
                        {storyIssues.length > 0 && (
                            <Badge variant="destructive" className="ml-2">
                                {storyIssues.length} issues
                            </Badge>
                        )}
                    </div>
                </AccordionTrigger>
                <AccordionContent>
                    <div className="space-y-3 pt-2">
                        <p className="text-xs text-gray-500">
                            Analyzes your story for plot holes, timeline issues,
                            character inconsistencies, and continuity errors.
                        </p>

                        {/* Chapter Selection */}
                        <div className="p-2 border rounded space-y-2">
                            <div className="flex items-center justify-between">
                                <Label className="text-xs font-medium">
                                    Select Chapters:
                                </Label>
                                <div className="flex gap-1">
                                    <Button
                                        variant={
                                            storyCheckMode === "all"
                                                ? "default"
                                                : "outline"
                                        }
                                        size="sm"
                                        className="h-6 text-xs px-2"
                                        onClick={() => setStoryCheckMode("all")}
                                    >
                                        All
                                    </Button>
                                    <Button
                                        variant={
                                            storyCheckMode === "selected"
                                                ? "default"
                                                : "outline"
                                        }
                                        size="sm"
                                        className="h-6 text-xs px-2"
                                        onClick={() =>
                                            setStoryCheckMode("selected")
                                        }
                                    >
                                        Select
                                    </Button>
                                </div>
                            </div>

                            {storyCheckMode === "selected" && scanStatus && (
                                <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
                                    {Object.values(scanStatus.chapters).map(
                                        (ch) => (
                                            <label
                                                key={ch.chapter_order}
                                                className={`flex items-center gap-1 px-2 py-1 rounded text-xs cursor-pointer transition-colors ${
                                                    selectedChapters.has(
                                                        ch.chapter_order,
                                                    )
                                                        ? "bg-purple-100 text-purple-800 border border-purple-300"
                                                        : "bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200"
                                                }`}
                                            >
                                                <Checkbox
                                                    checked={selectedChapters.has(
                                                        ch.chapter_order,
                                                    )}
                                                    onCheckedChange={(
                                                        checked,
                                                    ) => {
                                                        const next = new Set(
                                                            selectedChapters,
                                                        );
                                                        if (checked)
                                                            next.add(
                                                                ch.chapter_order,
                                                            );
                                                        else
                                                            next.delete(
                                                                ch.chapter_order,
                                                            );
                                                        setSelectedChapters(
                                                            next,
                                                        );
                                                    }}
                                                    className="h-3 w-3"
                                                />
                                                {ch.chapter_name ||
                                                    `Ch ${ch.chapter_order + 1}`}
                                            </label>
                                        ),
                                    )}
                                </div>
                            )}

                            {storyCheckMode === "selected" &&
                                selectedChapters.size > 0 && (
                                    <div className="text-xs text-purple-600">
                                        {selectedChapters.size} chapter
                                        {selectedChapters.size === 1
                                            ? ""
                                            : "s"}{" "}
                                        selected
                                    </div>
                                )}
                        </div>

                        <Button
                            size="sm"
                            onClick={handleStoryConsistencyCheck}
                            disabled={isDisabled}
                            className="w-full"
                        >
                            {loadingStoryCheck ? (
                                <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Analyzing...
                                </>
                            ) : (
                                <>
                                    <BookOpen className="h-4 w-4 mr-2" />
                                    {storyCheckMode === "all"
                                        ? "Check Story Consistency"
                                        : `Check ${selectedChapters.size} Chapter${
                                              selectedChapters.size === 1
                                                  ? ""
                                                  : "s"
                                          }`}
                                </>
                            )}
                        </Button>

                        {storyIssues.length > 0 && (
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs font-medium text-purple-700">
                                        {storyIssues.length} issue
                                        {storyIssues.length !== 1
                                            ? "s"
                                            : ""}{" "}
                                        found
                                    </span>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-6 text-xs text-gray-400 hover:text-red-500"
                                        onClick={() => {
                                            onStoryIssuesChange([]);
                                            setSelectedStoryIssues(new Set());
                                        }}
                                    >
                                        Clear All
                                    </Button>
                                </div>

                                <div className="flex items-center justify-between p-2 bg-purple-50 rounded">
                                    <div className="flex items-center gap-2">
                                        <Checkbox
                                            checked={previewMode}
                                            onCheckedChange={(checked) =>
                                                setPreviewMode(!!checked)
                                            }
                                        />
                                        <span className="text-xs text-purple-700">
                                            Show details after applying fix
                                        </span>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between gap-2 p-2 bg-gray-50 rounded">
                                    <div className="flex items-center gap-2">
                                        <Checkbox
                                            checked={
                                                selectedStoryIssues.size ===
                                                    storyIssues.length &&
                                                storyIssues.length > 0
                                            }
                                            onCheckedChange={
                                                toggleSelectAllStoryIssues
                                            }
                                        />
                                        <span className="text-xs text-gray-600">
                                            {selectedStoryIssues.size > 0
                                                ? `${selectedStoryIssues.size} selected`
                                                : "Select all"}
                                        </span>
                                    </div>
                                    {selectedStoryIssues.size > 0 && (
                                        <Button
                                            size="sm"
                                            variant="default"
                                            onClick={
                                                handleApplyAllStorySelected
                                            }
                                            disabled={applyingAllStory}
                                            className="h-7 text-xs bg-purple-600 hover:bg-purple-700"
                                        >
                                            {applyingAllStory ? (
                                                <>
                                                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                                    Applying...
                                                </>
                                            ) : (
                                                <>
                                                    <CheckSquare className="h-3 w-3 mr-1" />
                                                    Fix Selected (
                                                    {selectedStoryIssues.size})
                                                </>
                                            )}
                                        </Button>
                                    )}
                                </div>

                                <div className="space-y-2 max-h-64 overflow-y-auto">
                                    {storyIssues.map((issue, idx) => (
                                        <div
                                            key={idx}
                                            className={`p-2 rounded border ${getSeverityColor(
                                                issue.severity,
                                            )}`}
                                        >
                                            <div className="flex items-start gap-2">
                                                <Checkbox
                                                    checked={selectedStoryIssues.has(
                                                        idx,
                                                    )}
                                                    onCheckedChange={() =>
                                                        toggleStoryIssueSelected(
                                                            idx,
                                                        )
                                                    }
                                                    className="mt-0.5"
                                                />

                                                <div
                                                    className="flex-1 min-w-0 cursor-pointer"
                                                    onClick={() =>
                                                        toggleStoryIssueExpanded(
                                                            idx,
                                                        )
                                                    }
                                                >
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <Badge
                                                            className={`${getIssueTypeColor(
                                                                issue.issue_type,
                                                            )} text-white text-xs`}
                                                        >
                                                            {issue.issue_type?.replace(
                                                                "_",
                                                                " ",
                                                            )}
                                                        </Badge>
                                                        {issue.location && (
                                                            <span className="text-xs text-gray-500">
                                                                {issue.location}
                                                            </span>
                                                        )}
                                                        <span className="text-gray-400 ml-auto">
                                                            {expandedStoryIssues.has(
                                                                idx,
                                                            ) ? (
                                                                <ChevronDown className="w-4! h-4!" />
                                                            ) : (
                                                                <ChevronRight className="w-4! h-4!" />
                                                            )}
                                                        </span>
                                                    </div>
                                                    <p className="font-medium text-sm">
                                                        {issue.title ||
                                                            issue.entity_name}
                                                    </p>
                                                    {issue.description && (
                                                        <p
                                                            className={`text-xs mt-1 ${
                                                                expandedStoryIssues.has(
                                                                    idx,
                                                                )
                                                                    ? ""
                                                                    : "line-clamp-2"
                                                            }`}
                                                        >
                                                            {issue.description}
                                                        </p>
                                                    )}
                                                    {issue.evidence && (
                                                        <p
                                                            className={`text-xs mt-1 italic text-gray-600 ${
                                                                expandedStoryIssues.has(
                                                                    idx,
                                                                )
                                                                    ? ""
                                                                    : "line-clamp-2"
                                                            }`}
                                                        >
                                                            "{issue.evidence}"
                                                        </p>
                                                    )}
                                                    {issue.suggestion && (
                                                        <p
                                                            className={`text-xs mt-1 text-gray-600 ${
                                                                expandedStoryIssues.has(
                                                                    idx,
                                                                )
                                                                    ? ""
                                                                    : "line-clamp-2"
                                                            }`}
                                                        >
                                                            {issue.suggestion}
                                                        </p>
                                                    )}
                                                </div>

                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    onClick={() =>
                                                        handleApplyStoryTextFix(
                                                            issue,
                                                            idx,
                                                        )
                                                    }
                                                    disabled={
                                                        applyingStoryFix ===
                                                            idx ||
                                                        applyingAllStory
                                                    }
                                                    className="h-7 text-xs shrink-0"
                                                >
                                                    {applyingStoryFix ===
                                                    idx ? (
                                                        <Loader2 className="h-3 w-3 animate-spin" />
                                                    ) : (
                                                        <>
                                                            <Wand2 className="h-3 w-3 mr-1" />
                                                            Fix
                                                        </>
                                                    )}
                                                </Button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {storyIssues.length === 0 && !loadingStoryCheck && (
                            <p className="text-xs text-gray-500 italic text-center">
                                No issues found (or check hasn't been run yet)
                            </p>
                        )}
                    </div>
                </AccordionContent>
            </AccordionItem>

            <StoryFixPreviewDialog
                previewData={storyTextPreview}
                editedText={editedStoryText}
                onEditedTextChange={setEditedStoryText}
                onConfirm={confirmStoryTextFix}
                onClose={() => setStoryTextPreview(null)}
            />

            <BatchStoryFixPreviewDialog
                open={batchDialogOpen}
                fixes={batchFixes}
                onFixEdit={handleBatchFixEdit}
                onFixToggle={handleBatchFixToggle}
                onConfirm={handleBatchApply}
                onClose={() => {
                    setBatchDialogOpen(false);
                    setBatchFixes([]);
                }}
                isApplying={applyingBatch}
            />
        </>
    );
}

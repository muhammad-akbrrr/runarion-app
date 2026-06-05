import { useState } from "react";
import { Button } from "@/Components/ui/button";
import { Badge } from "@/Components/ui/badge";
import { Checkbox } from "@/Components/ui/checkbox";
import {
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/Components/ui/accordion";
import {
    AlertTriangle,
    Loader2,
    Wand2,
    CheckSquare,
    ChevronDown,
    ChevronRight,
} from "lucide-react";
import type {
    ConsistencyIssue,
    SharedSectionProps,
    RecordFixPreviewData,
} from "./types";
import { getSeverityColor, getIssueTypeColor, postJson } from "./utils";
import CategoryEntityPicker, {
    type PickerMode,
} from "./Shared/CategoryEntityPicker";
import RecordFixPreviewDialog from "./Shared/RecordFixPreviewDialog";

interface RecordConsistencySectionProps extends SharedSectionProps {
    // Persisted state from parent
    recordIssues: ConsistencyIssue[];
    onRecordIssuesChange: (issues: ConsistencyIssue[]) => void;
}

export default function RecordConsistencySection({
    workspaceId,
    projectId,
    selectedModel,
    availableCategories,
    availableEntities,
    loadingCategories,
    loadingEntities,
    loadEntitiesForCategory,
    recordIssues,
    onRecordIssuesChange,
}: RecordConsistencySectionProps) {
    const [loadingRecordCheck, setLoadingRecordCheck] = useState(false);
    const [selectedIssues, setSelectedIssues] = useState<Set<number>>(
        new Set(),
    );
    const [applyingFix, setApplyingFix] = useState<number | null>(null);
    const [applyingAll, setApplyingAll] = useState(false);
    const [expandedIssues, setExpandedIssues] = useState<Set<number>>(
        new Set(),
    );
    const [previewMode, setPreviewMode] = useState(true);
    const [previewData, setPreviewData] = useState<RecordFixPreviewData | null>(
        null,
    );

    // Selection state
    const [recordCheckMode, setRecordCheckMode] = useState<PickerMode>("all");
    const [selectedCategories, setSelectedCategories] = useState<Set<string>>(
        new Set(),
    );
    const [selectedEntities, setSelectedEntities] = useState<Set<string>>(
        new Set(),
    );
    const [expandedCategory, setExpandedCategory] = useState<string | null>(
        null,
    );

    const handleRecordConsistencyCheck = async () => {
        setLoadingRecordCheck(true);
        onRecordIssuesChange([]);

        const targetCategories =
            recordCheckMode === "category"
                ? Array.from(selectedCategories)
                : null;
        const targetEntities =
            recordCheckMode === "entity" ? Array.from(selectedEntities) : null;

        try {
            const response = await postJson(
                `/${workspaceId}/projects/${projectId}/editor/auditor/check-consistency/records`,
                {
                    model: selectedModel,
                    provider: "gemini",
                    categories: targetCategories,
                    entity_ids: targetEntities,
                },
            );
            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                onRecordIssuesChange(data.results?.issues || []);
            }
        } catch (error) {
            console.error("Error checking record consistency:", error);
        } finally {
            setLoadingRecordCheck(false);
        }
    };

    const handleApplyFix = async (
        issue: ConsistencyIssue,
        index: number,
        skipPreview = false,
    ) => {
        setApplyingFix(index);
        try {
            const response = await postJson(
                `/${workspaceId}/projects/${projectId}/editor/auditor/apply-fix`,
                {
                    entity_name: issue.entity_name,
                    entity_type: issue.entity_type,
                    field: issue.field,
                    issue_type: issue.issue_type,
                    suggestion: issue.suggestion,
                    story_evidence: issue.story_evidence,
                    model: selectedModel,
                    provider: "gemini",
                },
            );

            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                const results = data.results || data;
                if (data.success && results) {
                    if (previewMode && !skipPreview) {
                        setPreviewData({
                            issue,
                            index,
                            field: results.field || issue.field || "unknown",
                            oldValue:
                                typeof results.old_value === "object"
                                    ? JSON.stringify(results.old_value, null, 2)
                                    : String(results.old_value ?? ""),
                            newValue:
                                typeof results.new_value === "object"
                                    ? JSON.stringify(results.new_value, null, 2)
                                    : String(results.new_value ?? ""),
                            explanation:
                                results.explanation || results.message || "",
                        });
                    }

                    // Remove from list since it was applied
                    onRecordIssuesChange(
                        recordIssues.filter((_, i) => i !== index),
                    );
                    setSelectedIssues((prev) => {
                        const next = new Set(prev);
                        next.delete(index);
                        return next;
                    });
                } else {
                    alert(
                        `Failed to apply fix: ${
                            data.error || results?.error || "Unknown error"
                        }`,
                    );
                }
            } else {
                const error = response.data;
                alert(`Failed to apply fix: ${error.error || "Unknown error"}`);
            }
        } catch (error) {
            console.error("Error applying fix:", error);
            alert("Failed to apply fix");
        } finally {
            setApplyingFix(null);
        }
    };

    const handleApplyAllSelected = async () => {
        if (selectedIssues.size === 0) {
            alert("Please select at least one issue to fix");
            return;
        }

        if (
            !confirm(`Apply fixes for ${selectedIssues.size} selected issues?`)
        ) {
            return;
        }

        setApplyingAll(true);
        let successCount = 0;
        let failCount = 0;

        const sortedIndices = Array.from(selectedIssues).sort((a, b) => b - a);

        for (const idx of sortedIndices) {
            const issue = recordIssues[idx];
            if (!issue) continue;

            try {
                const response = await postJson(
                    `/${workspaceId}/projects/${projectId}/editor/auditor/apply-fix`,
                    {
                        entity_name: issue.entity_name,
                        entity_type: issue.entity_type,
                        field: issue.field,
                        issue_type: issue.issue_type,
                        suggestion: issue.suggestion,
                        story_evidence: issue.story_evidence,
                        model: selectedModel,
                        provider: "gemini",
                    },
                );
                if (response.status >= 200 && response.status < 300) {
                    const data = response.data;
                    const results = data.results || data;
                    if (data.success || results.success) {
                        successCount++;
                    } else {
                        failCount++;
                    }
                } else {
                    failCount++;
                }
            } catch {
                failCount++;
            }
        }

        if (successCount > 0) {
            alert(
                `Applied ${successCount} fix(es) successfully${
                    failCount > 0 ? `, ${failCount} failed` : ""
                }`,
            );
            handleRecordConsistencyCheck();
        } else {
            alert(`Failed to apply any fixes. ${failCount} error(s) occurred.`);
        }

        setSelectedIssues(new Set());
        setApplyingAll(false);
    };

    const toggleIssueSelection = (idx: number) => {
        setSelectedIssues((prev) => {
            const next = new Set(prev);
            if (next.has(idx)) next.delete(idx);
            else next.add(idx);
            return next;
        });
    };

    const selectAllIssues = () => {
        if (selectedIssues.size === recordIssues.length) {
            setSelectedIssues(new Set());
        } else {
            setSelectedIssues(new Set(recordIssues.map((_, i) => i)));
        }
    };

    const toggleIssueExpanded = (idx: number) => {
        setExpandedIssues((prev) => {
            const next = new Set(prev);
            if (next.has(idx)) next.delete(idx);
            else next.add(idx);
            return next;
        });
    };

    const isDisabled =
        loadingRecordCheck ||
        (recordCheckMode === "category" && selectedCategories.size === 0) ||
        (recordCheckMode === "entity" && selectedEntities.size === 0);

    return (
        <>
            <AccordionItem value="record-consistency">
                <AccordionTrigger className="hover:no-underline">
                    <div className="flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-orange-600" />
                        <span className="font-medium">Record Consistency</span>
                        {recordIssues.length > 0 && (
                            <Badge variant="destructive" className="ml-2">
                                {recordIssues.length} issues
                            </Badge>
                        )}
                    </div>
                </AccordionTrigger>
                <AccordionContent>
                    <div className="space-y-3 pt-2">
                        <p className="text-xs text-gray-500">
                            Compares your database records against story content
                            to find contradictions, outdated info, or missing
                            updates.
                        </p>

                        <CategoryEntityPicker
                            mode={recordCheckMode}
                            onModeChange={setRecordCheckMode}
                            availableCategories={availableCategories}
                            availableEntities={availableEntities}
                            selectedCategories={selectedCategories}
                            selectedEntities={selectedEntities}
                            onCategoriesChange={setSelectedCategories}
                            onEntitiesChange={setSelectedEntities}
                            loadingCategories={loadingCategories}
                            loadingEntities={loadingEntities}
                            expandedCategory={expandedCategory}
                            onExpandCategory={setExpandedCategory}
                            loadEntitiesForCategory={loadEntitiesForCategory}
                            accentColor="orange"
                        />

                        <Button
                            size="sm"
                            onClick={handleRecordConsistencyCheck}
                            disabled={isDisabled}
                            className="w-full"
                        >
                            {loadingRecordCheck ? (
                                <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Checking...
                                </>
                            ) : (
                                <>
                                    <AlertTriangle className="h-4 w-4 mr-2" />
                                    {recordCheckMode === "all" &&
                                        "Check All Records"}
                                    {recordCheckMode === "category" &&
                                        `Check ${selectedCategories.size} Categor${
                                            selectedCategories.size === 1
                                                ? "y"
                                                : "ies"
                                        }`}
                                    {recordCheckMode === "entity" &&
                                        `Check ${selectedEntities.size} Entit${
                                            selectedEntities.size === 1
                                                ? "y"
                                                : "ies"
                                        }`}
                                </>
                            )}
                        </Button>

                        {recordIssues.length > 0 && (
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs font-medium text-orange-700">
                                        {recordIssues.length} issue
                                        {recordIssues.length !== 1
                                            ? "s"
                                            : ""}{" "}
                                        found
                                    </span>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-6 text-xs text-gray-400 hover:text-red-500"
                                        onClick={() => {
                                            onRecordIssuesChange([]);
                                            setSelectedIssues(new Set());
                                        }}
                                    >
                                        Clear All
                                    </Button>
                                </div>

                                <div className="flex items-center justify-between p-2 bg-blue-50 rounded">
                                    <div className="flex items-center gap-2">
                                        <Checkbox
                                            checked={previewMode}
                                            onCheckedChange={(checked) =>
                                                setPreviewMode(!!checked)
                                            }
                                        />
                                        <span className="text-xs text-blue-700">
                                            Show details after applying fix
                                        </span>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between gap-2 p-2 bg-gray-50 rounded">
                                    <div className="flex items-center gap-2">
                                        <Checkbox
                                            checked={
                                                selectedIssues.size ===
                                                    recordIssues.length &&
                                                recordIssues.length > 0
                                            }
                                            onCheckedChange={selectAllIssues}
                                        />
                                        <span className="text-xs text-gray-600">
                                            {selectedIssues.size > 0
                                                ? `${selectedIssues.size} selected`
                                                : "Select all"}
                                        </span>
                                    </div>
                                    {selectedIssues.size > 0 && (
                                        <Button
                                            size="sm"
                                            variant="default"
                                            onClick={handleApplyAllSelected}
                                            disabled={applyingAll}
                                            className="h-7 text-xs"
                                        >
                                            {applyingAll ? (
                                                <>
                                                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                                    Applying...
                                                </>
                                            ) : (
                                                <>
                                                    <CheckSquare className="h-3 w-3 mr-1" />
                                                    Fix Selected (
                                                    {selectedIssues.size})
                                                </>
                                            )}
                                        </Button>
                                    )}
                                </div>

                                <div className="space-y-2 max-h-64 overflow-y-auto">
                                    {recordIssues.map((issue, idx) => (
                                        <div
                                            key={idx}
                                            className={`p-2 rounded border ${getSeverityColor(
                                                issue.severity,
                                            )}`}
                                        >
                                            <div className="flex items-start gap-2">
                                                <Checkbox
                                                    checked={selectedIssues.has(
                                                        idx,
                                                    )}
                                                    onCheckedChange={() =>
                                                        toggleIssueSelection(
                                                            idx,
                                                        )
                                                    }
                                                    className="mt-0.5"
                                                />

                                                <div
                                                    className="flex-1 min-w-0 cursor-pointer"
                                                    onClick={() =>
                                                        toggleIssueExpanded(idx)
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
                                                        <span className="font-medium text-sm truncate">
                                                            {issue.entity_name}
                                                        </span>
                                                        <span className="text-gray-400 ml-auto">
                                                            {expandedIssues.has(
                                                                idx,
                                                            ) ? (
                                                                <ChevronDown className="w-4! h-4!" />
                                                            ) : (
                                                                <ChevronRight className="w-4! h-4!" />
                                                            )}
                                                        </span>
                                                    </div>
                                                    {issue.field && (
                                                        <p className="text-xs">
                                                            <strong>
                                                                Field:
                                                            </strong>{" "}
                                                            {issue.field}
                                                        </p>
                                                    )}
                                                    {issue.story_evidence && (
                                                        <p
                                                            className={`text-xs mt-1 italic text-orange-700 ${
                                                                expandedIssues.has(
                                                                    idx,
                                                                )
                                                                    ? ""
                                                                    : "line-clamp-2"
                                                            }`}
                                                        >
                                                            "
                                                            {
                                                                issue.story_evidence
                                                            }
                                                            "
                                                        </p>
                                                    )}
                                                    {issue.suggestion && (
                                                        <p
                                                            className={`text-xs mt-1 text-gray-600 ${
                                                                expandedIssues.has(
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
                                                        handleApplyFix(
                                                            issue,
                                                            idx,
                                                        )
                                                    }
                                                    disabled={
                                                        applyingFix === idx ||
                                                        applyingAll
                                                    }
                                                    className="h-7 text-xs shrink-0"
                                                >
                                                    {applyingFix === idx ? (
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

                        {recordIssues.length === 0 && !loadingRecordCheck && (
                            <p className="text-xs text-gray-500 italic text-center">
                                No issues found (or check hasn't been run yet)
                            </p>
                        )}
                    </div>
                </AccordionContent>
            </AccordionItem>

            <RecordFixPreviewDialog
                previewData={previewData}
                onClose={() => setPreviewData(null)}
            />
        </>
    );
}

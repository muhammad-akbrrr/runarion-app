import { useState, useEffect } from "react";
import { Button } from "@/Components/ui/button";
import { Label } from "@/Components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/Components/ui/select";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/Components/ui/tooltip";
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/Components/ui/accordion";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";
import { Textarea } from "@/Components/ui/textarea";
import { Badge } from "@/Components/ui/badge";
import { Checkbox } from "@/Components/ui/checkbox";
import {
    HelpCircle,
    RefreshCw,
    AlertTriangle,
    BookOpen,
    GitMerge,
    CheckCircle,
    Clock,
    FileText,
    Loader2,
    Sparkles,
    TrendingUp,
    Wand2,
    CheckSquare,
    Eye,
} from "lucide-react";

interface AuditorToolsTabProps {
    workspaceId: string;
    projectId: string;
    selectedModel: string;
    onApplyStoryFix?: (oldText: string, newText: string) => boolean;
}

interface ChapterScanInfo {
    chapter_order: number;
    chapter_name: string;
    current_content_hash: string;
    stored_content_hash: string;
    has_changes: boolean;
    content_length: number;

    // Detailed extraction status
    extraction: {
        done: boolean;
        last_at: string | null;
        categories_extracted: string[];
        entity_count: number;
        warning: string | null; // Warning if entities were deleted
    };

    // Record keeper summarization status
    record_keeper: {
        done: boolean;
        last_at: string | null;
        warning: string | null; // Warning if record keeper entry deleted
    };

    // Data integrity warning
    has_warning: boolean;

    // Category-specific summarization status
    category_summaries: {
        done: boolean;
        last_at: string | null;
        categories_summarized: string[];
    };

    // What needs to be done
    needs_extraction: boolean;
    needs_summarization: boolean;

    // Legacy fields
    last_extraction_at: string | null;
    last_summarization_at: string | null;
    entities_extracted: string[];
    not_scanned: boolean;
}

interface ScanStatus {
    chapters: Record<number, ChapterScanInfo>;
    total_chapters: number;
    extraction_pending: number;
    summarization_pending: number;
    data_warnings: number; // Count of chapters with deleted/modified data
    // Legacy
    chapters_with_changes: number;
    chapters_not_scanned: number;
}

interface ConsistencyIssue {
    entity_name?: string;
    entity_type?: string;
    issue_type: string;
    title?: string;
    field?: string;
    current_db_value?: string;
    story_evidence?: string;
    description?: string;
    location?: string;
    evidence?: string;
    severity: string;
    suggestion: string;
}

interface DuplicateGroup {
    entities: Array<{ vertex_id: string; name: string }>;
    entity_type: string;
    confidence: number;
    reason: string;
    suggested_canonical: string;
}

interface PropertyChange {
    field: string;
    old_value: any;
    new_value: any;
    reason: string;
    chapter_reference?: number;
}

interface RefreshResults {
    entities_processed: number;
    entities_updated: number;
    entities_unchanged: number;
    changes_by_entity: Record<string, PropertyChange[]>;
    errors: string[];
}

export default function AuditorToolsTab({
    workspaceId,
    projectId,
    selectedModel,
    onApplyStoryFix,
}: AuditorToolsTabProps) {
    const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);
    const [loadingScanStatus, setLoadingScanStatus] = useState(false);

    const [recordIssues, setRecordIssues] = useState<ConsistencyIssue[]>([]);
    const [loadingRecordCheck, setLoadingRecordCheck] = useState(false);

    const [storyIssues, setStoryIssues] = useState<ConsistencyIssue[]>([]);
    const [loadingStoryCheck, setLoadingStoryCheck] = useState(false);

    const [duplicates, setDuplicates] = useState<DuplicateGroup[]>([]);
    const [duplicateErrors, setDuplicateErrors] = useState<string[]>([]);
    const [loadingDuplicates, setLoadingDuplicates] = useState(false);

    const [merging, setMerging] = useState<string | null>(null);

    const [refreshResults, setRefreshResults] = useState<RefreshResults | null>(
        null
    );
    const [loadingRefresh, setLoadingRefresh] = useState(false);

    // Record issue fixing state
    const [selectedIssues, setSelectedIssues] = useState<Set<number>>(
        new Set()
    );
    const [applyingFix, setApplyingFix] = useState<number | null>(null);
    const [applyingAll, setApplyingAll] = useState(false);
    const [expandedIssues, setExpandedIssues] = useState<Set<number>>(
        new Set()
    );

    // Story issue fixing state
    const [selectedStoryIssues, setSelectedStoryIssues] = useState<Set<number>>(
        new Set()
    );
    const [applyingStoryFix, setApplyingStoryFix] = useState<number | null>(
        null
    );
    const [applyingAllStory, setApplyingAllStory] = useState(false);
    const [expandedStoryIssues, setExpandedStoryIssues] = useState<Set<number>>(
        new Set()
    );

    // Preview mode (shared between record and story)
    const [previewMode, setPreviewMode] = useState(true); // Default to preview mode
    const [previewData, setPreviewData] = useState<{
        issue: ConsistencyIssue;
        index: number;
        field: string;
        oldValue: string;
        newValue: string;
        explanation: string;
    } | null>(null);
    const [editedNewValue, setEditedNewValue] = useState("");

    // Story text fix preview
    const [storyTextPreview, setStoryTextPreview] = useState<{
        issue: ConsistencyIssue;
        index: number;
        oldText: string;
        newText: string;
        explanation: string;
        chapterName: string;
        chapterOrder: number;
    } | null>(null);
    const [editedStoryText, setEditedStoryText] = useState("");

    // Selection states for filtering operations
    const [availableCategories, setAvailableCategories] = useState<string[]>(
        []
    );
    const [availableEntities, setAvailableEntities] = useState<
        Record<string, Array<{ vertex_id: string; name: string }>>
    >({});
    const [selectedCategories, setSelectedCategories] = useState<Set<string>>(
        new Set()
    );
    const [selectedEntities, setSelectedEntities] = useState<Set<string>>(
        new Set()
    ); // vertex_ids
    const [selectedChapters, setSelectedChapters] = useState<Set<number>>(
        new Set()
    );
    const [refreshMode, setRefreshMode] = useState<
        "all" | "category" | "entity"
    >("all");
    const [storyCheckMode, setStoryCheckMode] = useState<"all" | "selected">(
        "all"
    );
    const [recordCheckMode, setRecordCheckMode] = useState<
        "all" | "category" | "entity"
    >("all");
    const [duplicateCheckMode, setDuplicateCheckMode] = useState<
        "all" | "category" | "entity"
    >("all");
    const [loadingCategories, setLoadingCategories] = useState(false);
    const [loadingEntities, setLoadingEntities] = useState(false);
    const [expandedCategory, setExpandedCategory] = useState<string | null>(
        null
    );

    // Persistence key for localStorage
    const STORAGE_KEY = `auditor_state_${projectId}`;

    // Load persisted state on mount
    useEffect(() => {
        loadScanStatus();
        loadAvailableCategories();
        loadPersistedState();
    }, []);

    // Save state when results change
    useEffect(() => {
        savePersistedState();
    }, [recordIssues, storyIssues, refreshResults, duplicates]);

    const loadPersistedState = () => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                const parsed = JSON.parse(saved);
                if (parsed.recordIssues) setRecordIssues(parsed.recordIssues);
                if (parsed.storyIssues) setStoryIssues(parsed.storyIssues);
                if (parsed.refreshResults)
                    setRefreshResults(parsed.refreshResults);
                if (parsed.duplicates) setDuplicates(parsed.duplicates);
            }
        } catch (error) {
            console.error("Error loading persisted state:", error);
        }
    };

    const savePersistedState = () => {
        try {
            const state = {
                recordIssues,
                storyIssues,
                refreshResults,
                duplicates,
                savedAt: new Date().toISOString(),
            };
            localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
        } catch (error) {
            console.error("Error saving persisted state:", error);
        }
    };

    const clearAllPersistedState = () => {
        localStorage.removeItem(STORAGE_KEY);
        setRecordIssues([]);
        setStoryIssues([]);
        setRefreshResults(null);
        setDuplicates([]);
    };

    const loadAvailableCategories = async () => {
        setLoadingCategories(true);
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/records/categories`,
                { headers: { Accept: "application/json" } }
            );
            if (response.ok) {
                const data = await response.json();
                const cats = data.categories || [];
                setAvailableCategories(cats);
            }
        } catch (error) {
            console.error("Error loading categories:", error);
        } finally {
            setLoadingCategories(false);
        }
    };

    const loadEntitiesForCategory = async (category: string) => {
        if (availableEntities[category]) return; // Already loaded

        console.log(`[Auditor] Loading entities for category: ${category}`);
        setLoadingEntities(true);
        try {
            const url = `/${workspaceId}/projects/${projectId}/editor/records/entities?category=${encodeURIComponent(
                category
            )}`;
            console.log(`[Auditor] Fetching: ${url}`);

            const response = await fetch(url, {
                headers: { Accept: "application/json" },
            });
            console.log(`[Auditor] Response status: ${response.status}`);

            if (response.ok) {
                const data = await response.json();
                console.log(
                    `[Auditor] Got ${
                        data.entities?.length || 0
                    } entities for ${category}`
                );
                setAvailableEntities((prev) => ({
                    ...prev,
                    [category]: (data.entities || []).map((e: any) => ({
                        vertex_id: String(e.vertex_id),
                        name: e.name,
                    })),
                }));
            } else {
                console.error(
                    `[Auditor] Failed to load entities: ${response.status}`
                );
            }
        } catch (error) {
            console.error("[Auditor] Error loading entities:", error);
        } finally {
            setLoadingEntities(false);
        }
    };

    const toggleCategoryExpand = (category: string) => {
        if (expandedCategory === category) {
            setExpandedCategory(null);
        } else {
            setExpandedCategory(category);
            loadEntitiesForCategory(category);
        }
    };

    const selectAllEntitiesInCategory = (category: string) => {
        const entities = availableEntities[category] || [];
        const newSelected = new Set(selectedEntities);
        entities.forEach((e) => newSelected.add(e.vertex_id));
        setSelectedEntities(newSelected);
    };

    const deselectAllEntitiesInCategory = (category: string) => {
        const entities = availableEntities[category] || [];
        const entityIds = new Set(entities.map((e) => e.vertex_id));
        const newSelected = new Set(selectedEntities);
        entityIds.forEach((id) => newSelected.delete(id));
        setSelectedEntities(newSelected);
    };

    const loadScanStatus = async () => {
        setLoadingScanStatus(true);
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/scan-status`,
                { headers: { Accept: "application/json" } }
            );
            if (response.ok) {
                const data = await response.json();
                setScanStatus(data.scan_status || null);
            }
        } catch (error) {
            console.error("Error loading scan status:", error);
        } finally {
            setLoadingScanStatus(false);
        }
    };

    const handleRecordConsistencyCheck = async () => {
        setLoadingRecordCheck(true);
        setRecordIssues([]);

        const targetCategories =
            recordCheckMode === "category"
                ? Array.from(selectedCategories)
                : null;
        const targetEntities =
            recordCheckMode === "entity" ? Array.from(selectedEntities) : null;

        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/check-consistency/records`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                    body: JSON.stringify({
                        model: selectedModel,
                        provider: "gemini",
                        categories: targetCategories,
                        entity_ids: targetEntities,
                    }),
                }
            );
            if (response.ok) {
                const data = await response.json();
                setRecordIssues(data.results?.issues || []);
            }
        } catch (error) {
            console.error("Error checking record consistency:", error);
        } finally {
            setLoadingRecordCheck(false);
        }
    };

    const handleStoryConsistencyCheck = async () => {
        setLoadingStoryCheck(true);
        setStoryIssues([]);

        const targetChapters =
            storyCheckMode === "selected" ? Array.from(selectedChapters) : null;

        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/check-consistency/story`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                    body: JSON.stringify({
                        model: selectedModel,
                        provider: "gemini",
                        chapter_orders: targetChapters,
                    }),
                }
            );
            if (response.ok) {
                const data = await response.json();
                setStoryIssues(data.results?.issues || []);
            }
        } catch (error) {
            console.error("Error checking story consistency:", error);
        } finally {
            setLoadingStoryCheck(false);
        }
    };

    const handleFindDuplicates = async () => {
        setLoadingDuplicates(true);
        setDuplicates([]);
        setDuplicateErrors([]);

        // Determine scope based on mode
        const targetCategories =
            duplicateCheckMode === "category"
                ? Array.from(selectedCategories)
                : null;
        const targetEntities =
            duplicateCheckMode === "entity"
                ? Array.from(selectedEntities)
                : null;

        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/find-duplicates`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                    body: JSON.stringify({
                        model: selectedModel,
                        provider: "gemini",
                        scope: duplicateCheckMode,
                        categories: targetCategories,
                        entity_ids: targetEntities,
                    }),
                }
            );
            if (response.ok) {
                const data = await response.json();
                setDuplicates(data.results?.potential_duplicates || []);
                // Check for errors (API failures during scan)
                const errors = data.results?.errors || [];
                setDuplicateErrors(errors);

                // If there are errors, show a user-friendly message
                if (
                    errors.length > 0 &&
                    (data.results?.potential_duplicates || []).length === 0
                ) {
                    // Check if it's rate limit error
                    const hasRateLimit = errors.some(
                        (e: string) =>
                            e.includes("429") ||
                            e.includes("quota") ||
                            e.includes("RESOURCE_EXHAUSTED")
                    );
                    if (hasRateLimit) {
                        alert(
                            "API rate limit exceeded. Please wait and try again, or use a paid API key."
                        );
                    }
                }
            } else {
                const errorData = await response.json();
                const errorMsg =
                    errorData.details?.error ||
                    errorData.error ||
                    "Unknown error";
                if (errorMsg.includes("429") || errorMsg.includes("quota")) {
                    alert(
                        "API rate limit exceeded. Please wait and try again, or use a paid API key."
                    );
                } else {
                    alert(`Failed to find duplicates: ${errorMsg}`);
                }
            }
        } catch (error) {
            console.error("Error finding duplicates:", error);
            alert(`Failed to find duplicates: ${error}`);
        } finally {
            setLoadingDuplicates(false);
        }
    };

    const handleMergeEntities = async (group: DuplicateGroup) => {
        if (group.entities.length < 2) return;

        const source = group.entities.find(
            (e) => e.name !== group.suggested_canonical
        );
        const target =
            group.entities.find((e) => e.name === group.suggested_canonical) ||
            group.entities[0];

        if (!source || !target) return;

        if (
            !confirm(
                `Merge "${source.name}" into "${target.name}"?\n\nThis will:\n- Combine properties from both entities\n- Delete "${source.name}"\n- Keep "${target.name}" as the canonical entity`
            )
        ) {
            return;
        }

        setMerging(source.vertex_id);
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/merge-entities`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                    body: JSON.stringify({
                        source_vertex_id: source.vertex_id,
                        target_vertex_id: target.vertex_id,
                        merge_strategy: "combine",
                    }),
                }
            );
            if (response.ok) {
                // Remove the merged group from local state instead of rescanning
                setDuplicates((prev) =>
                    prev.filter(
                        (g) =>
                            g.entities[0]?.vertex_id !==
                            group.entities[0]?.vertex_id
                    )
                );
                // Show brief success message (no blocking alert)
                console.log("Entities merged successfully!");
            } else {
                const error = await response.json();
                alert(`Failed to merge: ${error.error || "Unknown error"}`);
            }
        } catch (error) {
            console.error("Error merging entities:", error);
            alert("Failed to merge entities");
        } finally {
            setMerging(null);
        }
    };

    // Apply a single fix (with optional preview)
    const handleApplyFix = async (
        issue: ConsistencyIssue,
        index: number,
        skipPreview = false
    ) => {
        // If preview mode is on and not skipping, get preview first
        if (previewMode && !skipPreview) {
            setApplyingFix(index);
            try {
                const response = await fetch(
                    `/${workspaceId}/projects/${projectId}/editor/auditor/apply-fix`,
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            Accept: "application/json",
                            "X-CSRF-TOKEN":
                                document
                                    .querySelector('meta[name="csrf-token"]')
                                    ?.getAttribute("content") || "",
                        },
                        body: JSON.stringify({
                            entity_name: issue.entity_name,
                            entity_type: issue.entity_type,
                            field: issue.field,
                            issue_type: issue.issue_type,
                            suggestion: issue.suggestion,
                            story_evidence: issue.story_evidence,
                            model: selectedModel,
                            provider: "gemini",
                        }),
                    }
                );
                if (response.ok) {
                    const data = await response.json();
                    // Results are wrapped in a results object
                    const results = data.results || data;
                    if (data.success && results) {
                        // Show preview dialog
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
                        setEditedNewValue(
                            typeof results.new_value === "object"
                                ? JSON.stringify(results.new_value, null, 2)
                                : String(results.new_value ?? "")
                        );

                        // If no change was made, inform user
                        if (results.action === "no_change") {
                            // Still show preview but mark as no change needed
                        }

                        // Remove from list since it was already applied
                        setRecordIssues((prev) =>
                            prev.filter((_, i) => i !== index)
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
                            }`
                        );
                    }
                } else {
                    const error = await response.json();
                    alert(
                        `Failed to apply fix: ${error.error || "Unknown error"}`
                    );
                }
            } catch (error) {
                console.error("Error getting preview:", error);
                alert("Failed to get preview");
            } finally {
                setApplyingFix(null);
            }
            return;
        }

        // Direct apply (no preview)
        setApplyingFix(index);
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/apply-fix`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                    body: JSON.stringify({
                        entity_name: issue.entity_name,
                        entity_type: issue.entity_type,
                        field: issue.field,
                        issue_type: issue.issue_type,
                        suggestion: issue.suggestion,
                        story_evidence: issue.story_evidence,
                        model: selectedModel,
                        provider: "gemini",
                    }),
                }
            );
            if (response.ok) {
                const data = await response.json();
                const results = data.results || data;
                if (data.success || results.success) {
                    // Remove the fixed issue from the list
                    setRecordIssues((prev) =>
                        prev.filter((_, i) => i !== index)
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
                        }`
                    );
                }
            } else {
                const error = await response.json();
                alert(`Failed to apply fix: ${error.error || "Unknown error"}`);
            }
        } catch (error) {
            console.error("Error applying fix:", error);
            alert("Failed to apply fix");
        } finally {
            setApplyingFix(null);
        }
    };

    // Apply all selected fixes
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

        // Get sorted indices (highest first) to avoid index shifting during removal
        const sortedIndices = Array.from(selectedIssues).sort((a, b) => b - a);

        for (const idx of sortedIndices) {
            const issue = recordIssues[idx];
            if (!issue) continue;

            try {
                const response = await fetch(
                    `/${workspaceId}/projects/${projectId}/editor/auditor/apply-fix`,
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            Accept: "application/json",
                            "X-CSRF-TOKEN":
                                document
                                    .querySelector('meta[name="csrf-token"]')
                                    ?.getAttribute("content") || "",
                        },
                        body: JSON.stringify({
                            entity_name: issue.entity_name,
                            entity_type: issue.entity_type,
                            field: issue.field,
                            issue_type: issue.issue_type,
                            suggestion: issue.suggestion,
                            story_evidence: issue.story_evidence,
                            model: selectedModel,
                            provider: "gemini",
                        }),
                    }
                );
                if (response.ok) {
                    const data = await response.json();
                    const results = data.results || data;
                    if (data.success || results.success) {
                        successCount++;
                    } else {
                        failCount++;
                    }
                } else {
                    failCount++;
                }
            } catch (error) {
                failCount++;
            }
        }

        // Refresh the issues after applying fixes
        if (successCount > 0) {
            alert(
                `Applied ${successCount} fix(es) successfully${
                    failCount > 0 ? `, ${failCount} failed` : ""
                }`
            );
            // Re-run consistency check to get updated list
            handleRecordConsistencyCheck();
        } else {
            alert(`Failed to apply any fixes. ${failCount} error(s) occurred.`);
        }

        setSelectedIssues(new Set());
        setApplyingAll(false);
    };

    // Toggle issue selection
    const toggleIssueSelection = (idx: number) => {
        setSelectedIssues((prev) => {
            const next = new Set(prev);
            if (next.has(idx)) {
                next.delete(idx);
            } else {
                next.add(idx);
            }
            return next;
        });
    };

    // Select all issues
    const selectAllIssues = () => {
        if (selectedIssues.size === recordIssues.length) {
            setSelectedIssues(new Set());
        } else {
            setSelectedIssues(new Set(recordIssues.map((_, i) => i)));
        }
    };

    // Apply a single story text fix (edits the chapter content, not entity properties)
    const handleApplyStoryTextFix = async (
        issue: ConsistencyIssue,
        index: number
    ) => {
        setApplyingStoryFix(index);
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/fix-story-text`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                    body: JSON.stringify({
                        issue_type: issue.issue_type,
                        title: issue.title,
                        description: issue.description,
                        evidence: issue.evidence,
                        location: issue.location,
                        suggestion: issue.suggestion,
                        model: selectedModel,
                        provider: "gemini",
                    }),
                }
            );
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    const results = data.results;
                    // Always show preview for story text fixes
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
                    });
                    setEditedStoryText(results.new_text || "");
                } else {
                    alert(
                        `Failed to generate fix: ${
                            data.error || "Unknown error"
                        }`
                    );
                }
            } else {
                const error = await response.json();
                alert(
                    `Failed to generate fix: ${error.error || "Unknown error"}`
                );
            }
        } catch (error) {
            console.error("Error generating story fix:", error);
            alert("Failed to generate fix");
        } finally {
            setApplyingStoryFix(null);
        }
    };

    // Confirm and apply the story text fix
    const confirmStoryTextFix = async () => {
        if (!storyTextPreview) return;

        try {
            console.log("[AuditorFix] Starting fix application...");
            console.log(
                "[AuditorFix] Old text length:",
                storyTextPreview.oldText?.length
            );
            console.log(
                "[AuditorFix] New text length:",
                editedStoryText?.length
            );

            // If callback is provided, use it (for live editor updates)
            // The callback will update the editor state AND trigger auto-save
            if (onApplyStoryFix) {
                console.log("[AuditorFix] Calling onApplyStoryFix callback...");
                const success = onApplyStoryFix(
                    storyTextPreview.oldText,
                    editedStoryText
                );

                if (success) {
                    console.log(
                        "[AuditorFix] Callback succeeded - editor updated!"
                    );
                    // Show success message
                    alert(
                        `✅ Fix applied to ${storyTextPreview.chapterName}! The editor has been updated.`
                    );
                } else {
                    console.warn(
                        "[AuditorFix] Callback failed - text not found in editor"
                    );
                    // Show warning but don't fail - might be a sync issue
                    alert(
                        `⚠️ Could not find text in the current editor. The text may have changed. Please try refreshing and applying again.`
                    );
                }
            } else {
                // No callback - fall back to direct API save
                console.log(
                    "[AuditorFix] No callback, using direct API save..."
                );
                const chapterOrder = storyTextPreview.chapterOrder;

                // Fetch current chapter
                const chaptersResponse = await fetch(
                    `/${workspaceId}/projects/${projectId}/editor/chapters`,
                    { headers: { Accept: "application/json" } }
                );

                if (chaptersResponse.ok) {
                    const chaptersData = await chaptersResponse.json();
                    const chapters = chaptersData.chapters || [];
                    const chapter =
                        chapters.find((c: any) => c.order === chapterOrder) ||
                        chapters[0];

                    if (chapter && chapter.content) {
                        // Normalize text for comparison
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

                        // Try exact match first, then normalized
                        let newContent: string | null = null;
                        if (
                            chapter.content.includes(storyTextPreview.oldText)
                        ) {
                            newContent = chapter.content.replace(
                                storyTextPreview.oldText,
                                editedStoryText
                            );
                        } else {
                            const normalizedContent = normalizeText(
                                chapter.content
                            );
                            const normalizedOldText = normalizeText(
                                storyTextPreview.oldText
                            );

                            if (normalizedContent.includes(normalizedOldText)) {
                                // Use approximate replacement based on position
                                const idx =
                                    normalizedContent.indexOf(
                                        normalizedOldText
                                    );
                                const ratio =
                                    chapter.content.length /
                                    normalizedContent.length;
                                const start = Math.floor(idx * ratio);
                                const end = Math.ceil(
                                    (idx + normalizedOldText.length) * ratio
                                );
                                newContent =
                                    chapter.content.substring(0, start) +
                                    editedStoryText +
                                    chapter.content.substring(end);
                            }
                        }

                        if (newContent && newContent !== chapter.content) {
                            const updateResponse = await fetch(
                                `/${workspaceId}/projects/${projectId}/editor/unified`,
                                {
                                    method: "PATCH",
                                    headers: {
                                        "Content-Type": "application/json",
                                        Accept: "application/json",
                                        "X-CSRF-TOKEN":
                                            document
                                                .querySelector(
                                                    'meta[name="csrf-token"]'
                                                )
                                                ?.getAttribute("content") || "",
                                    },
                                    body: JSON.stringify({
                                        content: {
                                            order: chapterOrder,
                                            content: newContent,
                                            trigger: "manual",
                                        },
                                    }),
                                }
                            );

                            if (!updateResponse.ok) {
                                throw new Error("Failed to save chapter");
                            }

                            alert(
                                `✅ Fix applied to ${storyTextPreview.chapterName}! Please refresh to see changes.`
                            );
                        } else {
                            alert(
                                "⚠️ Text not found in chapter. The fix may have already been applied or the text has changed."
                            );
                        }
                    }
                }
            }

            // Remove from list
            setStoryIssues((prev) =>
                prev.filter((_, i) => i !== storyTextPreview.index)
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
                    (error instanceof Error ? error.message : "Unknown error")
            );
        }
    };

    // Apply all selected story fixes
    const handleApplyAllStorySelected = async () => {
        if (selectedStoryIssues.size === 0) {
            alert("Please select at least one issue to fix");
            return;
        }

        const fixableCount = selectedStoryIssues.size;

        if (
            !confirm(
                `Generate fixes for ${fixableCount} selected issues?\n\nNote: Each fix will be shown for review before applying.`
            )
        ) {
            return;
        }

        // For story fixes, we process one at a time with preview
        const indices = Array.from(selectedStoryIssues);
        if (indices.length > 0) {
            const firstIdx = indices[0];
            const issue = storyIssues[firstIdx];
            if (issue) {
                await handleApplyStoryTextFix(issue, firstIdx);
            }
        }
    };

    const handleRefreshAllProperties = async () => {
        const targetCategories =
            refreshMode === "category" ? Array.from(selectedCategories) : null;
        const targetEntities =
            refreshMode === "entity" ? Array.from(selectedEntities) : null;

        let message =
            "This will update ALL entity properties to reflect their current state in the story.\n\nCharacters who have changed (e.g., brave → cowardly) will have their properties updated.\n\nPrevious values will be backed up.\n\nContinue?";

        if (refreshMode === "category") {
            message = `This will update entity properties for categories: ${targetCategories?.join(
                ", "
            )}\n\nPrevious values will be backed up.\n\nContinue?`;
        } else if (refreshMode === "entity") {
            message = `This will update ${
                targetEntities?.length
            } selected entit${
                targetEntities?.length === 1 ? "y" : "ies"
            }.\n\nPrevious values will be backed up.\n\nContinue?`;
        }

        if (!confirm(message)) {
            return;
        }

        setLoadingRefresh(true);
        setRefreshResults(null);
        try {
            // Use bulk endpoint for ALL modes (entity, category, all)
            // The backend handles filtering by entity_ids or categories
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/refresh-all-properties`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                    body: JSON.stringify({
                        model: selectedModel,
                        provider: "gemini",
                        categories: targetCategories,
                        entity_ids: targetEntities,
                    }),
                }
            );

            if (response.ok) {
                const data = await response.json();
                setRefreshResults(data.results || null);
            } else {
                // Extract detailed error message from response
                try {
                    const errorData = await response.json();
                    const errorMsg =
                        errorData.details?.error ||
                        errorData.error ||
                        "Unknown error";

                    // Check for common errors and provide helpful messages
                    if (
                        errorMsg.includes("429") ||
                        errorMsg.includes("quota") ||
                        errorMsg.includes("RESOURCE_EXHAUSTED")
                    ) {
                        alert(
                            "API rate limit exceeded. Please wait a minute and try again, or use a paid API key."
                        );
                    } else {
                        alert(`Failed to refresh: ${errorMsg}`);
                    }
                } catch {
                    alert(`Failed to refresh: HTTP ${response.status}`);
                }
            }
        } catch (error) {
            console.error("Error refreshing properties:", error);
            alert(`Failed to refresh: ${error}`);
        } finally {
            setLoadingRefresh(false);
        }
    };

    const getSeverityColor = (severity: string) => {
        switch (severity?.toLowerCase()) {
            case "critical":
            case "high":
                return "bg-red-100 text-red-800 border-red-200";
            case "major":
            case "medium":
                return "bg-yellow-100 text-yellow-800 border-yellow-200";
            default:
                return "bg-blue-100 text-blue-800 border-blue-200";
        }
    };

    const getIssueTypeColor = (type: string) => {
        switch (type?.toLowerCase()) {
            case "contradiction":
                return "bg-red-500";
            case "outdated":
                return "bg-orange-500";
            case "missing_update":
                return "bg-blue-500";
            case "plot_holes":
                return "bg-purple-500";
            case "timeline":
                return "bg-yellow-500";
            case "character":
                return "bg-green-500";
            case "continuity":
                return "bg-pink-500";
            default:
                return "bg-gray-500";
        }
    };

    return (
        <div className="space-y-4">
            <Accordion
                type="multiple"
                defaultValue={["scan-status"]}
                className="w-full"
            >
                {/* Scan Status Section */}
                <AccordionItem value="scan-status">
                    <AccordionTrigger className="hover:no-underline">
                        <div className="flex items-center gap-2">
                            <Clock className="h-4 w-4 text-blue-600" />
                            <span className="font-medium">Scan Status</span>
                            {scanStatus && (
                                <Badge variant="outline" className="ml-2">
                                    {scanStatus.chapters_with_changes +
                                        scanStatus.chapters_not_scanned}{" "}
                                    pending
                                </Badge>
                            )}
                        </div>
                    </AccordionTrigger>
                    <AccordionContent>
                        <div className="space-y-3 pt-2">
                            <div className="flex items-center justify-between">
                                <p className="text-xs text-gray-500">
                                    Shows which chapters have been scanned and
                                    which have changes.
                                </p>
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={loadScanStatus}
                                    disabled={loadingScanStatus}
                                >
                                    {loadingScanStatus ? (
                                        <Loader2 className="h-3 w-3 animate-spin" />
                                    ) : (
                                        <RefreshCw className="h-3 w-3" />
                                    )}
                                </Button>
                            </div>

                            {scanStatus && (
                                <>
                                    {/* Summary Stats */}
                                    <div className="grid grid-cols-4 gap-2 text-center">
                                        <div className="p-2 bg-gray-50 rounded">
                                            <div className="text-lg font-bold">
                                                {scanStatus.total_chapters}
                                            </div>
                                            <div className="text-xs text-gray-500">
                                                Chapters
                                            </div>
                                        </div>
                                        <div className="p-2 bg-blue-50 rounded">
                                            <div className="text-lg font-bold text-blue-700">
                                                {scanStatus.extraction_pending ||
                                                    scanStatus.chapters_not_scanned ||
                                                    0}
                                            </div>
                                            <div className="text-xs text-blue-600">
                                                Extract
                                            </div>
                                        </div>
                                        <div className="p-2 bg-orange-50 rounded">
                                            <div className="text-lg font-bold text-orange-700">
                                                {scanStatus.summarization_pending ||
                                                    0}
                                            </div>
                                            <div className="text-xs text-orange-600">
                                                Summary
                                            </div>
                                        </div>
                                        {(scanStatus.data_warnings || 0) >
                                            0 && (
                                            <div className="p-2 bg-red-50 rounded">
                                                <div className="text-lg font-bold text-red-700">
                                                    {scanStatus.data_warnings}
                                                </div>
                                                <div className="text-xs text-red-600">
                                                    ⚠️ Warnings
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    {/* Chapter Details */}
                                    <div className="max-h-64 overflow-y-auto space-y-2">
                                        {Object.values(scanStatus.chapters)
                                            .sort(
                                                (a, b) =>
                                                    a.chapter_order -
                                                    b.chapter_order
                                            )
                                            .map((ch) => (
                                                <div
                                                    key={ch.chapter_order}
                                                    className={`p-2 rounded border text-xs ${
                                                        ch.has_changes
                                                            ? "border-yellow-300 bg-yellow-50"
                                                            : "border-green-300 bg-green-50"
                                                    }`}
                                                >
                                                    <div className="flex items-center justify-between mb-1">
                                                        <span className="font-medium">
                                                            Ch.{" "}
                                                            {ch.chapter_order +
                                                                1}
                                                            : {ch.chapter_name}
                                                        </span>
                                                        {ch.has_changes && (
                                                            <Badge
                                                                variant="outline"
                                                                className="text-[10px] bg-yellow-100 text-yellow-700"
                                                            >
                                                                Changed
                                                            </Badge>
                                                        )}
                                                    </div>

                                                    {/* Status indicators */}
                                                    <div className="grid grid-cols-2 gap-1 mt-1">
                                                        {/* Extraction Status */}
                                                        <div
                                                            className={`flex items-center gap-1 px-1.5 py-0.5 rounded ${
                                                                ch.extraction
                                                                    ?.warning
                                                                    ? "bg-red-100 text-red-700"
                                                                    : ch
                                                                          .extraction
                                                                          ?.done
                                                                    ? "bg-green-100 text-green-700"
                                                                    : "bg-gray-100 text-gray-500"
                                                            }`}
                                                        >
                                                            {ch.extraction
                                                                ?.warning ? (
                                                                <AlertTriangle className="h-3 w-3" />
                                                            ) : ch.extraction
                                                                  ?.done ? (
                                                                <CheckCircle className="h-3 w-3" />
                                                            ) : (
                                                                <Clock className="h-3 w-3" />
                                                            )}
                                                            <span>Extract</span>
                                                            {ch.extraction
                                                                ?.categories_extracted
                                                                ?.length >
                                                                0 && (
                                                                <span className="text-[10px]">
                                                                    (
                                                                    {
                                                                        ch
                                                                            .extraction
                                                                            .categories_extracted
                                                                            .length
                                                                    }
                                                                    )
                                                                </span>
                                                            )}
                                                        </div>

                                                        {/* Record Keeper Status */}
                                                        <div
                                                            className={`flex items-center gap-1 px-1.5 py-0.5 rounded ${
                                                                ch.record_keeper
                                                                    ?.warning
                                                                    ? "bg-red-100 text-red-700"
                                                                    : ch
                                                                          .record_keeper
                                                                          ?.done
                                                                    ? "bg-green-100 text-green-700"
                                                                    : "bg-gray-100 text-gray-500"
                                                            }`}
                                                        >
                                                            {ch.record_keeper
                                                                ?.warning ? (
                                                                <AlertTriangle className="h-3 w-3" />
                                                            ) : ch.record_keeper
                                                                  ?.done ? (
                                                                <CheckCircle className="h-3 w-3" />
                                                            ) : (
                                                                <Clock className="h-3 w-3" />
                                                            )}
                                                            <span>Summary</span>
                                                        </div>
                                                    </div>

                                                    {/* Warning messages */}
                                                    {(ch.extraction?.warning ||
                                                        ch.record_keeper
                                                            ?.warning) && (
                                                        <div className="mt-1 text-[10px] text-red-600 bg-red-50 p-1 rounded">
                                                            {ch.extraction
                                                                ?.warning && (
                                                                <div>
                                                                    ⚠️{" "}
                                                                    {
                                                                        ch
                                                                            .extraction
                                                                            .warning
                                                                    }
                                                                </div>
                                                            )}
                                                            {ch.record_keeper
                                                                ?.warning && (
                                                                <div>
                                                                    ⚠️{" "}
                                                                    {
                                                                        ch
                                                                            .record_keeper
                                                                            .warning
                                                                    }
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}

                                                    {/* Categories extracted */}
                                                    {ch.extraction
                                                        ?.categories_extracted
                                                        ?.length > 0 && (
                                                        <div className="mt-1 text-[10px] text-gray-500">
                                                            Categories:{" "}
                                                            {ch.extraction.categories_extracted.join(
                                                                ", "
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                    </div>

                                    <p className="text-xs text-gray-500 italic">
                                        💡 Use Extractor for entities,
                                        Summarizer for Record Keeper entries.
                                    </p>
                                </>
                            )}
                        </div>
                    </AccordionContent>
                </AccordionItem>

                {/* Record Consistency Checker */}
                <AccordionItem value="record-consistency">
                    <AccordionTrigger className="hover:no-underline">
                        <div className="flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4 text-orange-600" />
                            <span className="font-medium">
                                Record Consistency
                            </span>
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
                                Compares your database records against story
                                content to find contradictions, outdated info,
                                or missing updates.
                            </p>

                            {/* Category/Entity Selection */}
                            <div className="p-2 border rounded space-y-2">
                                <div className="flex items-center justify-between">
                                    <Label className="text-xs font-medium">
                                        Scope:
                                    </Label>
                                    <div className="flex gap-1">
                                        <Button
                                            variant={
                                                recordCheckMode === "all"
                                                    ? "default"
                                                    : "outline"
                                            }
                                            size="sm"
                                            className="h-6 text-xs px-2"
                                            onClick={() =>
                                                setRecordCheckMode("all")
                                            }
                                        >
                                            All
                                        </Button>
                                        <Button
                                            variant={
                                                recordCheckMode === "category"
                                                    ? "default"
                                                    : "outline"
                                            }
                                            size="sm"
                                            className="h-6 text-xs px-2"
                                            onClick={() =>
                                                setRecordCheckMode("category")
                                            }
                                        >
                                            Category
                                        </Button>
                                        <Button
                                            variant={
                                                recordCheckMode === "entity"
                                                    ? "default"
                                                    : "outline"
                                            }
                                            size="sm"
                                            className="h-6 text-xs px-2"
                                            onClick={() =>
                                                setRecordCheckMode("entity")
                                            }
                                        >
                                            Entity
                                        </Button>
                                    </div>
                                </div>

                                {recordCheckMode === "category" && (
                                    <div className="flex flex-wrap gap-1 max-h-32 overflow-y-auto">
                                        {loadingCategories ? (
                                            <span className="text-xs text-gray-400">
                                                Loading categories...
                                            </span>
                                        ) : availableCategories.length === 0 ? (
                                            <span className="text-xs text-gray-400">
                                                No categories found
                                            </span>
                                        ) : (
                                            availableCategories.map((cat) => (
                                                <label
                                                    key={cat}
                                                    className={`flex items-center gap-1 px-2 py-1 rounded text-xs cursor-pointer transition-colors ${
                                                        selectedCategories.has(
                                                            cat
                                                        )
                                                            ? "bg-orange-100 text-orange-800 border border-orange-300"
                                                            : "bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200"
                                                    }`}
                                                >
                                                    <Checkbox
                                                        checked={selectedCategories.has(
                                                            cat
                                                        )}
                                                        onCheckedChange={(
                                                            checked
                                                        ) => {
                                                            const next =
                                                                new Set(
                                                                    selectedCategories
                                                                );
                                                            if (checked)
                                                                next.add(cat);
                                                            else
                                                                next.delete(
                                                                    cat
                                                                );
                                                            setSelectedCategories(
                                                                next
                                                            );
                                                        }}
                                                        className="h-3 w-3"
                                                    />
                                                    {cat}
                                                </label>
                                            ))
                                        )}
                                    </div>
                                )}

                                {recordCheckMode === "entity" && (
                                    <div className="space-y-1 max-h-40 overflow-y-auto">
                                        {loadingCategories ? (
                                            <span className="text-xs text-gray-400">
                                                Loading categories...
                                            </span>
                                        ) : availableCategories.length === 0 ? (
                                            <span className="text-xs text-gray-400">
                                                No categories found
                                            </span>
                                        ) : (
                                            availableCategories.map((cat) => (
                                                <div
                                                    key={cat}
                                                    className="border rounded"
                                                >
                                                    <div
                                                        className={`flex items-center justify-between p-1.5 cursor-pointer hover:bg-gray-50`}
                                                        onClick={() =>
                                                            toggleCategoryExpand(
                                                                cat
                                                            )
                                                        }
                                                    >
                                                        <span className="text-xs font-medium">
                                                            {cat}
                                                        </span>
                                                        <span className="text-xs text-gray-400">
                                                            {expandedCategory ===
                                                            cat
                                                                ? "▼"
                                                                : "▶"}
                                                        </span>
                                                    </div>

                                                    {expandedCategory ===
                                                        cat && (
                                                        <div className="border-t p-1.5 bg-gray-50 space-y-1">
                                                            {loadingEntities ? (
                                                                <span className="text-xs text-gray-400">
                                                                    Loading...
                                                                </span>
                                                            ) : (
                                                                  availableEntities[
                                                                      cat
                                                                  ] || []
                                                              ).length === 0 ? (
                                                                <span className="text-xs text-gray-400">
                                                                    No entities
                                                                </span>
                                                            ) : (
                                                                <>
                                                                    <div className="flex gap-2 mb-1">
                                                                        <Button
                                                                            variant="ghost"
                                                                            size="sm"
                                                                            className="h-5 text-xs px-1"
                                                                            onClick={() =>
                                                                                selectAllEntitiesInCategory(
                                                                                    cat
                                                                                )
                                                                            }
                                                                        >
                                                                            Select
                                                                            All
                                                                        </Button>
                                                                        <Button
                                                                            variant="ghost"
                                                                            size="sm"
                                                                            className="h-5 text-xs px-1"
                                                                            onClick={() =>
                                                                                deselectAllEntitiesInCategory(
                                                                                    cat
                                                                                )
                                                                            }
                                                                        >
                                                                            Deselect
                                                                            All
                                                                        </Button>
                                                                    </div>
                                                                    {(
                                                                        availableEntities[
                                                                            cat
                                                                        ] || []
                                                                    ).map(
                                                                        (
                                                                            entity
                                                                        ) => (
                                                                            <label
                                                                                key={
                                                                                    entity.vertex_id
                                                                                }
                                                                                className={`flex items-center gap-1.5 text-xs cursor-pointer p-1 rounded ${
                                                                                    selectedEntities.has(
                                                                                        entity.vertex_id
                                                                                    )
                                                                                        ? "bg-orange-100 text-orange-800"
                                                                                        : "hover:bg-gray-100"
                                                                                }`}
                                                                            >
                                                                                <Checkbox
                                                                                    checked={selectedEntities.has(
                                                                                        entity.vertex_id
                                                                                    )}
                                                                                    onCheckedChange={(
                                                                                        checked
                                                                                    ) => {
                                                                                        const next =
                                                                                            new Set(
                                                                                                selectedEntities
                                                                                            );
                                                                                        if (
                                                                                            checked
                                                                                        )
                                                                                            next.add(
                                                                                                entity.vertex_id
                                                                                            );
                                                                                        else
                                                                                            next.delete(
                                                                                                entity.vertex_id
                                                                                            );
                                                                                        setSelectedEntities(
                                                                                            next
                                                                                        );
                                                                                    }}
                                                                                    className="h-3 w-3"
                                                                                />
                                                                                {
                                                                                    entity.name
                                                                                }
                                                                            </label>
                                                                        )
                                                                    )}
                                                                </>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            ))
                                        )}
                                    </div>
                                )}

                                {recordCheckMode === "category" &&
                                    selectedCategories.size > 0 && (
                                        <div className="text-xs text-orange-600">
                                            {selectedCategories.size} categor
                                            {selectedCategories.size === 1
                                                ? "y"
                                                : "ies"}{" "}
                                            selected
                                        </div>
                                    )}

                                {recordCheckMode === "entity" &&
                                    selectedEntities.size > 0 && (
                                        <div className="text-xs text-orange-600">
                                            {selectedEntities.size} entit
                                            {selectedEntities.size === 1
                                                ? "y"
                                                : "ies"}{" "}
                                            selected
                                        </div>
                                    )}
                            </div>

                            <Button
                                size="sm"
                                onClick={handleRecordConsistencyCheck}
                                disabled={
                                    loadingRecordCheck ||
                                    (recordCheckMode === "category" &&
                                        selectedCategories.size === 0) ||
                                    (recordCheckMode === "entity" &&
                                        selectedEntities.size === 0)
                                }
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
                                            `Check ${
                                                selectedCategories.size
                                            } Categor${
                                                selectedCategories.size === 1
                                                    ? "y"
                                                    : "ies"
                                            }`}
                                        {recordCheckMode === "entity" &&
                                            `Check ${
                                                selectedEntities.size
                                            } Entit${
                                                selectedEntities.size === 1
                                                    ? "y"
                                                    : "ies"
                                            }`}
                                    </>
                                )}
                            </Button>

                            {recordIssues.length > 0 && (
                                <div className="space-y-2">
                                    {/* Header with clear button */}
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
                                                setRecordIssues([]);
                                                setSelectedIssues(new Set());
                                            }}
                                        >
                                            Clear All
                                        </Button>
                                    </div>

                                    {/* Show results toggle */}
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

                                    {/* Batch actions */}
                                    <div className="flex items-center justify-between gap-2 p-2 bg-gray-50 rounded">
                                        <div className="flex items-center gap-2">
                                            <Checkbox
                                                checked={
                                                    selectedIssues.size ===
                                                        recordIssues.length &&
                                                    recordIssues.length > 0
                                                }
                                                onCheckedChange={
                                                    selectAllIssues
                                                }
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

                                    {/* Issues list */}
                                    <div className="space-y-2 max-h-64 overflow-y-auto">
                                        {recordIssues.map((issue, idx) => (
                                            <div
                                                key={idx}
                                                className={`p-2 rounded border ${getSeverityColor(
                                                    issue.severity
                                                )}`}
                                            >
                                                <div className="flex items-start gap-2">
                                                    {/* Checkbox */}
                                                    <Checkbox
                                                        checked={selectedIssues.has(
                                                            idx
                                                        )}
                                                        onCheckedChange={() =>
                                                            toggleIssueSelection(
                                                                idx
                                                            )
                                                        }
                                                        className="mt-0.5"
                                                    />

                                                    <div
                                                        className="flex-1 min-w-0 cursor-pointer"
                                                        onClick={() =>
                                                            setExpandedIssues(
                                                                (prev) => {
                                                                    const next =
                                                                        new Set(
                                                                            prev
                                                                        );
                                                                    if (
                                                                        next.has(
                                                                            idx
                                                                        )
                                                                    ) {
                                                                        next.delete(
                                                                            idx
                                                                        );
                                                                    } else {
                                                                        next.add(
                                                                            idx
                                                                        );
                                                                    }
                                                                    return next;
                                                                }
                                                            )
                                                        }
                                                    >
                                                        <div className="flex items-center gap-2 mb-1">
                                                            <Badge
                                                                className={`${getIssueTypeColor(
                                                                    issue.issue_type
                                                                )} text-white text-xs`}
                                                            >
                                                                {issue.issue_type?.replace(
                                                                    "_",
                                                                    " "
                                                                )}
                                                            </Badge>
                                                            <span className="font-medium text-sm truncate">
                                                                {
                                                                    issue.entity_name
                                                                }
                                                            </span>
                                                            <span className="text-[10px] text-gray-400 ml-auto">
                                                                {expandedIssues.has(
                                                                    idx
                                                                )
                                                                    ? "▼"
                                                                    : "▶"}
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
                                                                        idx
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
                                                                        idx
                                                                    )
                                                                        ? ""
                                                                        : "line-clamp-2"
                                                                }`}
                                                            >
                                                                💡{" "}
                                                                {
                                                                    issue.suggestion
                                                                }
                                                            </p>
                                                        )}
                                                    </div>

                                                    {/* Apply button */}
                                                    <Button
                                                        size="sm"
                                                        variant="outline"
                                                        onClick={() =>
                                                            handleApplyFix(
                                                                issue,
                                                                idx
                                                            )
                                                        }
                                                        disabled={
                                                            applyingFix ===
                                                                idx ||
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

                            {recordIssues.length === 0 &&
                                !loadingRecordCheck && (
                                    <p className="text-xs text-gray-500 italic text-center">
                                        No issues found (or check hasn't been
                                        run yet)
                                    </p>
                                )}
                        </div>
                    </AccordionContent>
                </AccordionItem>

                {/* Story Consistency Checker */}
                <AccordionItem value="story-consistency">
                    <AccordionTrigger className="hover:no-underline">
                        <div className="flex items-center gap-2">
                            <BookOpen className="h-4 w-4 text-purple-600" />
                            <span className="font-medium">
                                Story Consistency
                            </span>
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
                                Analyzes your story for plot holes, timeline
                                issues, character inconsistencies, and
                                continuity errors.
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
                                            onClick={() =>
                                                setStoryCheckMode("all")
                                            }
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

                                {storyCheckMode === "selected" &&
                                    scanStatus && (
                                        <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
                                            {Object.values(
                                                scanStatus.chapters
                                            ).map((ch) => (
                                                <label
                                                    key={ch.chapter_order}
                                                    className={`flex items-center gap-1 px-2 py-1 rounded text-xs cursor-pointer transition-colors ${
                                                        selectedChapters.has(
                                                            ch.chapter_order
                                                        )
                                                            ? "bg-purple-100 text-purple-800 border border-purple-300"
                                                            : "bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200"
                                                    }`}
                                                >
                                                    <Checkbox
                                                        checked={selectedChapters.has(
                                                            ch.chapter_order
                                                        )}
                                                        onCheckedChange={(
                                                            checked
                                                        ) => {
                                                            const next =
                                                                new Set(
                                                                    selectedChapters
                                                                );
                                                            if (checked)
                                                                next.add(
                                                                    ch.chapter_order
                                                                );
                                                            else
                                                                next.delete(
                                                                    ch.chapter_order
                                                                );
                                                            setSelectedChapters(
                                                                next
                                                            );
                                                        }}
                                                        className="h-3 w-3"
                                                    />
                                                    {ch.chapter_name ||
                                                        `Ch ${
                                                            ch.chapter_order + 1
                                                        }`}
                                                </label>
                                            ))}
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
                                disabled={
                                    loadingStoryCheck ||
                                    (storyCheckMode === "selected" &&
                                        selectedChapters.size === 0)
                                }
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
                                            : `Check ${
                                                  selectedChapters.size
                                              } Chapter${
                                                  selectedChapters.size === 1
                                                      ? ""
                                                      : "s"
                                              }`}
                                    </>
                                )}
                            </Button>

                            {storyIssues.length > 0 && (
                                <div className="space-y-2">
                                    {/* Header with clear button */}
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
                                                setStoryIssues([]);
                                                setSelectedStoryIssues(
                                                    new Set()
                                                );
                                            }}
                                        >
                                            Clear All
                                        </Button>
                                    </div>

                                    {/* Show details toggle */}
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

                                    {/* Batch actions */}
                                    <div className="flex items-center justify-between gap-2 p-2 bg-gray-50 rounded">
                                        <div className="flex items-center gap-2">
                                            <Checkbox
                                                checked={
                                                    selectedStoryIssues.size ===
                                                        storyIssues.length &&
                                                    storyIssues.length > 0
                                                }
                                                onCheckedChange={() => {
                                                    if (
                                                        selectedStoryIssues.size ===
                                                        storyIssues.length
                                                    ) {
                                                        setSelectedStoryIssues(
                                                            new Set()
                                                        );
                                                    } else {
                                                        setSelectedStoryIssues(
                                                            new Set(
                                                                storyIssues.map(
                                                                    (_, i) => i
                                                                )
                                                            )
                                                        );
                                                    }
                                                }}
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
                                                        {
                                                            selectedStoryIssues.size
                                                        }
                                                        )
                                                    </>
                                                )}
                                            </Button>
                                        )}
                                    </div>

                                    {/* Issues list */}
                                    <div className="space-y-2 max-h-64 overflow-y-auto">
                                        {storyIssues.map((issue, idx) => (
                                            <div
                                                key={idx}
                                                className={`p-2 rounded border ${getSeverityColor(
                                                    issue.severity
                                                )}`}
                                            >
                                                <div className="flex items-start gap-2">
                                                    {/* Checkbox */}
                                                    <Checkbox
                                                        checked={selectedStoryIssues.has(
                                                            idx
                                                        )}
                                                        onCheckedChange={() => {
                                                            setSelectedStoryIssues(
                                                                (prev) => {
                                                                    const next =
                                                                        new Set(
                                                                            prev
                                                                        );
                                                                    if (
                                                                        next.has(
                                                                            idx
                                                                        )
                                                                    ) {
                                                                        next.delete(
                                                                            idx
                                                                        );
                                                                    } else {
                                                                        next.add(
                                                                            idx
                                                                        );
                                                                    }
                                                                    return next;
                                                                }
                                                            );
                                                        }}
                                                        className="mt-0.5"
                                                    />

                                                    <div
                                                        className="flex-1 min-w-0 cursor-pointer"
                                                        onClick={() =>
                                                            setExpandedStoryIssues(
                                                                (prev) => {
                                                                    const next =
                                                                        new Set(
                                                                            prev
                                                                        );
                                                                    if (
                                                                        next.has(
                                                                            idx
                                                                        )
                                                                    ) {
                                                                        next.delete(
                                                                            idx
                                                                        );
                                                                    } else {
                                                                        next.add(
                                                                            idx
                                                                        );
                                                                    }
                                                                    return next;
                                                                }
                                                            )
                                                        }
                                                    >
                                                        <div className="flex items-center gap-2 mb-1">
                                                            <Badge
                                                                className={`${getIssueTypeColor(
                                                                    issue.issue_type
                                                                )} text-white text-xs`}
                                                            >
                                                                {issue.issue_type?.replace(
                                                                    "_",
                                                                    " "
                                                                )}
                                                            </Badge>
                                                            {issue.location && (
                                                                <span className="text-xs text-gray-500">
                                                                    {
                                                                        issue.location
                                                                    }
                                                                </span>
                                                            )}
                                                            <span className="text-[10px] text-gray-400 ml-auto">
                                                                {expandedStoryIssues.has(
                                                                    idx
                                                                )
                                                                    ? "▼"
                                                                    : "▶"}
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
                                                                        idx
                                                                    )
                                                                        ? ""
                                                                        : "line-clamp-2"
                                                                }`}
                                                            >
                                                                {
                                                                    issue.description
                                                                }
                                                            </p>
                                                        )}
                                                        {issue.evidence && (
                                                            <p
                                                                className={`text-xs mt-1 italic text-gray-600 ${
                                                                    expandedStoryIssues.has(
                                                                        idx
                                                                    )
                                                                        ? ""
                                                                        : "line-clamp-2"
                                                                }`}
                                                            >
                                                                "
                                                                {issue.evidence}
                                                                "
                                                            </p>
                                                        )}
                                                        {issue.suggestion && (
                                                            <p
                                                                className={`text-xs mt-1 text-gray-600 ${
                                                                    expandedStoryIssues.has(
                                                                        idx
                                                                    )
                                                                        ? ""
                                                                        : "line-clamp-2"
                                                                }`}
                                                            >
                                                                💡{" "}
                                                                {
                                                                    issue.suggestion
                                                                }
                                                            </p>
                                                        )}
                                                    </div>

                                                    {/* Fix button - always show for story issues */}
                                                    <Button
                                                        size="sm"
                                                        variant="outline"
                                                        onClick={() =>
                                                            handleApplyStoryTextFix(
                                                                issue,
                                                                idx
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
                                    No issues found (or check hasn't been run
                                    yet)
                                </p>
                            )}
                        </div>
                    </AccordionContent>
                </AccordionItem>

                {/* Property Refresh (Arc-Aware) */}
                <AccordionItem value="property-refresh">
                    <AccordionTrigger className="hover:no-underline">
                        <div className="flex items-center gap-2">
                            <Sparkles className="h-4 w-4 text-indigo-600" />
                            <span className="font-medium">
                                Property Refresh
                            </span>
                            {refreshResults &&
                                refreshResults.entities_updated > 0 && (
                                    <Badge
                                        variant="outline"
                                        className="ml-2 bg-indigo-50 text-indigo-700"
                                    >
                                        {refreshResults.entities_updated}{" "}
                                        updated
                                    </Badge>
                                )}
                        </div>
                    </AccordionTrigger>
                    <AccordionContent>
                        <div className="space-y-3 pt-2">
                            <p className="text-xs text-gray-500">
                                <strong>Arc-Aware Updates:</strong> Updates
                                entity properties to reflect their
                                <em> current state</em> in the story. Characters
                                who have changed (brave → cowardly, determined →
                                broken) will be updated. Previous values are
                                backed up.
                            </p>

                            <div className="p-2 bg-indigo-50 rounded text-xs space-y-1">
                                <div className="flex items-center gap-1">
                                    <span className="font-medium text-indigo-800">
                                        How it works:
                                    </span>
                                </div>
                                <ul className="list-disc list-inside text-indigo-700 space-y-0.5 ml-1">
                                    <li>
                                        Reads all chapters to understand story
                                        progression
                                    </li>
                                    <li>
                                        Determines each entity's{" "}
                                        <em>current</em> state
                                    </li>
                                    <li>
                                        Updates properties to match where story
                                        is NOW
                                    </li>
                                    <li>
                                        Logs changes with chapter references &
                                        reasons
                                    </li>
                                </ul>
                            </div>

                            {/* Category/Entity Selection */}
                            <div className="p-2 border rounded space-y-2">
                                <div className="flex items-center justify-between">
                                    <Label className="text-xs font-medium">
                                        Scope:
                                    </Label>
                                    <div className="flex gap-1">
                                        <Button
                                            variant={
                                                refreshMode === "all"
                                                    ? "default"
                                                    : "outline"
                                            }
                                            size="sm"
                                            className="h-6 text-xs px-2"
                                            onClick={() =>
                                                setRefreshMode("all")
                                            }
                                        >
                                            All
                                        </Button>
                                        <Button
                                            variant={
                                                refreshMode === "category"
                                                    ? "default"
                                                    : "outline"
                                            }
                                            size="sm"
                                            className="h-6 text-xs px-2"
                                            onClick={() =>
                                                setRefreshMode("category")
                                            }
                                        >
                                            Category
                                        </Button>
                                        <Button
                                            variant={
                                                refreshMode === "entity"
                                                    ? "default"
                                                    : "outline"
                                            }
                                            size="sm"
                                            className="h-6 text-xs px-2"
                                            onClick={() =>
                                                setRefreshMode("entity")
                                            }
                                        >
                                            Entity
                                        </Button>
                                    </div>
                                </div>

                                {(refreshMode === "category" ||
                                    refreshMode === "entity") && (
                                    <div className="space-y-1 max-h-40 overflow-y-auto">
                                        {loadingCategories ? (
                                            <span className="text-xs text-gray-400">
                                                Loading categories...
                                            </span>
                                        ) : availableCategories.length === 0 ? (
                                            <span className="text-xs text-gray-400">
                                                No categories found
                                            </span>
                                        ) : (
                                            availableCategories.map((cat) => (
                                                <div
                                                    key={cat}
                                                    className="border rounded"
                                                >
                                                    <div
                                                        className={`flex items-center justify-between p-1.5 cursor-pointer hover:bg-gray-50 ${
                                                            selectedCategories.has(
                                                                cat
                                                            )
                                                                ? "bg-indigo-50"
                                                                : ""
                                                        }`}
                                                        onClick={() => {
                                                            if (
                                                                refreshMode ===
                                                                "entity"
                                                            ) {
                                                                toggleCategoryExpand(
                                                                    cat
                                                                );
                                                            }
                                                        }}
                                                    >
                                                        <label className="flex items-center gap-1.5 text-xs cursor-pointer">
                                                            <Checkbox
                                                                checked={selectedCategories.has(
                                                                    cat
                                                                )}
                                                                onCheckedChange={(
                                                                    checked
                                                                ) => {
                                                                    const next =
                                                                        new Set(
                                                                            selectedCategories
                                                                        );
                                                                    if (checked)
                                                                        next.add(
                                                                            cat
                                                                        );
                                                                    else
                                                                        next.delete(
                                                                            cat
                                                                        );
                                                                    setSelectedCategories(
                                                                        next
                                                                    );
                                                                }}
                                                                className="h-3 w-3"
                                                                onClick={(e) =>
                                                                    e.stopPropagation()
                                                                }
                                                            />
                                                            <span
                                                                className={
                                                                    selectedCategories.has(
                                                                        cat
                                                                    )
                                                                        ? "text-indigo-700 font-medium"
                                                                        : ""
                                                                }
                                                            >
                                                                {cat}
                                                            </span>
                                                        </label>
                                                        {refreshMode ===
                                                            "entity" && (
                                                            <span className="text-xs text-gray-400">
                                                                {expandedCategory ===
                                                                cat
                                                                    ? "▼"
                                                                    : "▶"}
                                                            </span>
                                                        )}
                                                    </div>

                                                    {refreshMode === "entity" &&
                                                        expandedCategory ===
                                                            cat && (
                                                            <div className="border-t p-1.5 bg-gray-50 space-y-1">
                                                                {loadingEntities ? (
                                                                    <span className="text-xs text-gray-400">
                                                                        Loading...
                                                                    </span>
                                                                ) : (
                                                                      availableEntities[
                                                                          cat
                                                                      ] || []
                                                                  ).length ===
                                                                  0 ? (
                                                                    <span className="text-xs text-gray-400">
                                                                        No
                                                                        entities
                                                                    </span>
                                                                ) : (
                                                                    <>
                                                                        <div className="flex gap-2 mb-1">
                                                                            <Button
                                                                                variant="ghost"
                                                                                size="sm"
                                                                                className="h-5 text-xs px-1"
                                                                                onClick={() =>
                                                                                    selectAllEntitiesInCategory(
                                                                                        cat
                                                                                    )
                                                                                }
                                                                            >
                                                                                Select
                                                                                All
                                                                            </Button>
                                                                            <Button
                                                                                variant="ghost"
                                                                                size="sm"
                                                                                className="h-5 text-xs px-1"
                                                                                onClick={() =>
                                                                                    deselectAllEntitiesInCategory(
                                                                                        cat
                                                                                    )
                                                                                }
                                                                            >
                                                                                Deselect
                                                                                All
                                                                            </Button>
                                                                        </div>
                                                                        {(
                                                                            availableEntities[
                                                                                cat
                                                                            ] ||
                                                                            []
                                                                        ).map(
                                                                            (
                                                                                entity
                                                                            ) => (
                                                                                <label
                                                                                    key={
                                                                                        entity.vertex_id
                                                                                    }
                                                                                    className={`flex items-center gap-1.5 text-xs cursor-pointer p-1 rounded ${
                                                                                        selectedEntities.has(
                                                                                            entity.vertex_id
                                                                                        )
                                                                                            ? "bg-indigo-100 text-indigo-800"
                                                                                            : "hover:bg-gray-100"
                                                                                    }`}
                                                                                >
                                                                                    <Checkbox
                                                                                        checked={selectedEntities.has(
                                                                                            entity.vertex_id
                                                                                        )}
                                                                                        onCheckedChange={(
                                                                                            checked
                                                                                        ) => {
                                                                                            const next =
                                                                                                new Set(
                                                                                                    selectedEntities
                                                                                                );
                                                                                            if (
                                                                                                checked
                                                                                            )
                                                                                                next.add(
                                                                                                    entity.vertex_id
                                                                                                );
                                                                                            else
                                                                                                next.delete(
                                                                                                    entity.vertex_id
                                                                                                );
                                                                                            setSelectedEntities(
                                                                                                next
                                                                                            );
                                                                                        }}
                                                                                        className="h-3 w-3"
                                                                                    />
                                                                                    {
                                                                                        entity.name
                                                                                    }
                                                                                </label>
                                                                            )
                                                                        )}
                                                                    </>
                                                                )}
                                                            </div>
                                                        )}
                                                </div>
                                            ))
                                        )}
                                    </div>
                                )}

                                {refreshMode === "category" &&
                                    selectedCategories.size > 0 && (
                                        <div className="text-xs text-indigo-600">
                                            {selectedCategories.size} categor
                                            {selectedCategories.size === 1
                                                ? "y"
                                                : "ies"}{" "}
                                            selected
                                        </div>
                                    )}

                                {refreshMode === "entity" &&
                                    selectedEntities.size > 0 && (
                                        <div className="text-xs text-indigo-600">
                                            {selectedEntities.size} entit
                                            {selectedEntities.size === 1
                                                ? "y"
                                                : "ies"}{" "}
                                            selected
                                        </div>
                                    )}
                            </div>

                            <Button
                                size="sm"
                                onClick={handleRefreshAllProperties}
                                disabled={
                                    loadingRefresh ||
                                    (refreshMode === "category" &&
                                        selectedCategories.size === 0) ||
                                    (refreshMode === "entity" &&
                                        selectedEntities.size === 0)
                                }
                                className="w-full"
                            >
                                {loadingRefresh ? (
                                    <>
                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                        Processing entities...
                                    </>
                                ) : (
                                    <>
                                        <Sparkles className="h-4 w-4 mr-2" />
                                        {refreshMode === "all" &&
                                            "Refresh All Entities"}
                                        {refreshMode === "category" &&
                                            `Refresh ${
                                                selectedCategories.size
                                            } Categor${
                                                selectedCategories.size === 1
                                                    ? "y"
                                                    : "ies"
                                            }`}
                                        {refreshMode === "entity" &&
                                            `Refresh ${
                                                selectedEntities.size
                                            } Entit${
                                                selectedEntities.size === 1
                                                    ? "y"
                                                    : "ies"
                                            }`}
                                    </>
                                )}
                            </Button>

                            {loadingRefresh && (
                                <div className="p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-700">
                                    <strong>Processing in batches...</strong>{" "}
                                    Each entity is analyzed against your story.
                                    For large databases, this can take 2-5
                                    minutes. Please don't close this tab.
                                </div>
                            )}

                            {refreshResults && (
                                <div className="space-y-2">
                                    {/* Header with clear button */}
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-medium text-indigo-700">
                                            Refresh complete
                                        </span>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="h-6 text-xs text-gray-400 hover:text-red-500"
                                            onClick={() =>
                                                setRefreshResults(null)
                                            }
                                        >
                                            Clear
                                        </Button>
                                    </div>

                                    <div className="grid grid-cols-3 gap-2 text-center">
                                        <div className="p-2 bg-gray-50 rounded">
                                            <div className="text-lg font-bold">
                                                {
                                                    refreshResults.entities_processed
                                                }
                                            </div>
                                            <div className="text-xs text-gray-500">
                                                Processed
                                            </div>
                                        </div>
                                        <div className="p-2 bg-indigo-50 rounded">
                                            <div className="text-lg font-bold text-indigo-700">
                                                {
                                                    refreshResults.entities_updated
                                                }
                                            </div>
                                            <div className="text-xs text-indigo-600">
                                                Updated
                                            </div>
                                        </div>
                                        <div className="p-2 bg-green-50 rounded">
                                            <div className="text-lg font-bold text-green-700">
                                                {
                                                    refreshResults.entities_unchanged
                                                }
                                            </div>
                                            <div className="text-xs text-green-600">
                                                Current
                                            </div>
                                        </div>
                                    </div>

                                    {Object.keys(
                                        refreshResults.changes_by_entity
                                    ).length > 0 && (
                                        <div className="max-h-48 overflow-y-auto space-y-2">
                                            {Object.entries(
                                                refreshResults.changes_by_entity
                                            ).map(([entityName, changes]) => (
                                                <div
                                                    key={entityName}
                                                    className="p-2 rounded border bg-white"
                                                >
                                                    <div className="font-medium text-sm mb-1">
                                                        {entityName}
                                                    </div>
                                                    {changes.map(
                                                        (change, idx) => (
                                                            <div
                                                                key={idx}
                                                                className="text-xs bg-gray-50 p-1.5 rounded mt-1"
                                                            >
                                                                <div className="flex items-center gap-1">
                                                                    <span className="font-medium">
                                                                        {
                                                                            change.field
                                                                        }
                                                                        :
                                                                    </span>
                                                                    <span className="text-red-600 line-through">
                                                                        {String(
                                                                            change.old_value
                                                                        ).slice(
                                                                            0,
                                                                            30
                                                                        )}
                                                                    </span>
                                                                    <span className="text-gray-400">
                                                                        →
                                                                    </span>
                                                                    <span className="text-green-600">
                                                                        {String(
                                                                            change.new_value
                                                                        ).slice(
                                                                            0,
                                                                            30
                                                                        )}
                                                                    </span>
                                                                </div>
                                                                {change.reason && (
                                                                    <div className="text-gray-500 mt-0.5 italic">
                                                                        {change.chapter_reference &&
                                                                            `Ch. ${change.chapter_reference}: `}
                                                                        {
                                                                            change.reason
                                                                        }
                                                                    </div>
                                                                )}
                                                            </div>
                                                        )
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    {refreshResults.errors.length > 0 && (
                                        <div className="text-xs text-red-600 bg-red-50 p-2 rounded">
                                            <strong>Errors:</strong>
                                            <ul className="list-disc list-inside">
                                                {refreshResults.errors.map(
                                                    (err, idx) => (
                                                        <li key={idx}>{err}</li>
                                                    )
                                                )}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            )}

                            {!refreshResults && !loadingRefresh && (
                                <p className="text-xs text-gray-500 italic text-center">
                                    Run refresh to update entity properties to
                                    current story state
                                </p>
                            )}
                        </div>
                    </AccordionContent>
                </AccordionItem>

                {/* Duplicate Finder */}
                <AccordionItem value="duplicates">
                    <AccordionTrigger className="hover:no-underline">
                        <div className="flex items-center gap-2">
                            <GitMerge className="h-4 w-4 text-green-600" />
                            <span className="font-medium">
                                Record Optimizer
                            </span>
                            {duplicates.length > 0 && (
                                <Badge variant="outline" className="ml-2">
                                    {duplicates.length} duplicates
                                </Badge>
                            )}
                        </div>
                    </AccordionTrigger>
                    <AccordionContent>
                        <div className="space-y-3 pt-2">
                            <p className="text-xs text-gray-500">
                                Find potential duplicate entities (same entity
                                with different names) and merge them to clean up
                                your database.
                            </p>

                            {/* Scope Selection for Duplicate Finder */}
                            <div className="p-2 border rounded space-y-2">
                                <div className="flex items-center justify-between">
                                    <Label className="text-xs font-medium">
                                        Scope:
                                    </Label>
                                    <div className="flex gap-1">
                                        <Button
                                            variant={
                                                duplicateCheckMode === "all"
                                                    ? "default"
                                                    : "outline"
                                            }
                                            size="sm"
                                            className="h-6 text-xs px-2"
                                            onClick={() =>
                                                setDuplicateCheckMode("all")
                                            }
                                        >
                                            All
                                        </Button>
                                        <Button
                                            variant={
                                                duplicateCheckMode ===
                                                "category"
                                                    ? "default"
                                                    : "outline"
                                            }
                                            size="sm"
                                            className="h-6 text-xs px-2"
                                            onClick={() =>
                                                setDuplicateCheckMode(
                                                    "category"
                                                )
                                            }
                                        >
                                            Category
                                        </Button>
                                        <Button
                                            variant={
                                                duplicateCheckMode === "entity"
                                                    ? "default"
                                                    : "outline"
                                            }
                                            size="sm"
                                            className="h-6 text-xs px-2"
                                            onClick={() =>
                                                setDuplicateCheckMode("entity")
                                            }
                                        >
                                            Entity
                                        </Button>
                                    </div>
                                </div>

                                {duplicateCheckMode === "category" && (
                                    <div className="flex flex-wrap gap-1 max-h-32 overflow-y-auto">
                                        {loadingCategories ? (
                                            <span className="text-xs text-gray-400">
                                                Loading categories...
                                            </span>
                                        ) : availableCategories.length === 0 ? (
                                            <span className="text-xs text-gray-400">
                                                No categories found
                                            </span>
                                        ) : (
                                            availableCategories.map((cat) => (
                                                <label
                                                    key={cat}
                                                    className={`flex items-center gap-1 px-2 py-1 rounded text-xs cursor-pointer transition-colors ${
                                                        selectedCategories.has(
                                                            cat
                                                        )
                                                            ? "bg-green-100 text-green-800 border border-green-300"
                                                            : "bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200"
                                                    }`}
                                                >
                                                    <Checkbox
                                                        checked={selectedCategories.has(
                                                            cat
                                                        )}
                                                        onCheckedChange={(
                                                            checked
                                                        ) => {
                                                            const next =
                                                                new Set(
                                                                    selectedCategories
                                                                );
                                                            if (checked)
                                                                next.add(cat);
                                                            else
                                                                next.delete(
                                                                    cat
                                                                );
                                                            setSelectedCategories(
                                                                next
                                                            );
                                                        }}
                                                        className="h-3 w-3"
                                                    />
                                                    {cat}
                                                </label>
                                            ))
                                        )}
                                    </div>
                                )}

                                {duplicateCheckMode === "entity" && (
                                    <div className="space-y-1 max-h-40 overflow-y-auto">
                                        {loadingCategories ? (
                                            <span className="text-xs text-gray-400">
                                                Loading categories...
                                            </span>
                                        ) : availableCategories.length === 0 ? (
                                            <span className="text-xs text-gray-400">
                                                No categories found
                                            </span>
                                        ) : (
                                            availableCategories.map((cat) => (
                                                <div
                                                    key={cat}
                                                    className="border rounded"
                                                >
                                                    <div
                                                        className={`flex items-center justify-between p-1.5 cursor-pointer hover:bg-gray-50`}
                                                        onClick={() =>
                                                            toggleCategoryExpand(
                                                                cat
                                                            )
                                                        }
                                                    >
                                                        <span className="text-xs font-medium">
                                                            {cat}
                                                        </span>
                                                        <span className="text-xs text-gray-400">
                                                            {expandedCategory ===
                                                            cat
                                                                ? "▼"
                                                                : "▶"}
                                                        </span>
                                                    </div>

                                                    {expandedCategory ===
                                                        cat && (
                                                        <div className="border-t p-1.5 bg-gray-50 space-y-1">
                                                            {loadingEntities ? (
                                                                <span className="text-xs text-gray-400">
                                                                    Loading...
                                                                </span>
                                                            ) : (
                                                                  availableEntities[
                                                                      cat
                                                                  ] || []
                                                              ).length === 0 ? (
                                                                <span className="text-xs text-gray-400">
                                                                    No entities
                                                                </span>
                                                            ) : (
                                                                <>
                                                                    <div className="flex gap-2 mb-1">
                                                                        <Button
                                                                            variant="ghost"
                                                                            size="sm"
                                                                            className="h-5 text-xs px-1"
                                                                            onClick={() =>
                                                                                selectAllEntitiesInCategory(
                                                                                    cat
                                                                                )
                                                                            }
                                                                        >
                                                                            Select
                                                                            All
                                                                        </Button>
                                                                        <Button
                                                                            variant="ghost"
                                                                            size="sm"
                                                                            className="h-5 text-xs px-1"
                                                                            onClick={() =>
                                                                                deselectAllEntitiesInCategory(
                                                                                    cat
                                                                                )
                                                                            }
                                                                        >
                                                                            Deselect
                                                                            All
                                                                        </Button>
                                                                    </div>
                                                                    {(
                                                                        availableEntities[
                                                                            cat
                                                                        ] || []
                                                                    ).map(
                                                                        (
                                                                            entity
                                                                        ) => (
                                                                            <label
                                                                                key={
                                                                                    entity.vertex_id
                                                                                }
                                                                                className={`flex items-center gap-1.5 text-xs cursor-pointer p-1 rounded ${
                                                                                    selectedEntities.has(
                                                                                        entity.vertex_id
                                                                                    )
                                                                                        ? "bg-green-100 text-green-800"
                                                                                        : "hover:bg-gray-100"
                                                                                }`}
                                                                            >
                                                                                <Checkbox
                                                                                    checked={selectedEntities.has(
                                                                                        entity.vertex_id
                                                                                    )}
                                                                                    onCheckedChange={(
                                                                                        checked
                                                                                    ) => {
                                                                                        const next =
                                                                                            new Set(
                                                                                                selectedEntities
                                                                                            );
                                                                                        if (
                                                                                            checked
                                                                                        )
                                                                                            next.add(
                                                                                                entity.vertex_id
                                                                                            );
                                                                                        else
                                                                                            next.delete(
                                                                                                entity.vertex_id
                                                                                            );
                                                                                        setSelectedEntities(
                                                                                            next
                                                                                        );
                                                                                    }}
                                                                                    className="h-3 w-3"
                                                                                />
                                                                                {
                                                                                    entity.name
                                                                                }
                                                                            </label>
                                                                        )
                                                                    )}
                                                                </>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            ))
                                        )}
                                    </div>
                                )}

                                {duplicateCheckMode === "category" &&
                                    selectedCategories.size > 0 && (
                                        <div className="text-xs text-green-600">
                                            {selectedCategories.size} categor
                                            {selectedCategories.size === 1
                                                ? "y"
                                                : "ies"}{" "}
                                            selected
                                        </div>
                                    )}

                                {duplicateCheckMode === "entity" &&
                                    selectedEntities.size > 0 && (
                                        <div className="text-xs text-green-600">
                                            {selectedEntities.size} entit
                                            {selectedEntities.size === 1
                                                ? "y"
                                                : "ies"}{" "}
                                            selected
                                        </div>
                                    )}
                            </div>

                            <Button
                                size="sm"
                                onClick={handleFindDuplicates}
                                disabled={
                                    loadingDuplicates ||
                                    (duplicateCheckMode === "category" &&
                                        selectedCategories.size === 0) ||
                                    (duplicateCheckMode === "entity" &&
                                        selectedEntities.size === 0)
                                }
                                className="w-full"
                            >
                                {loadingDuplicates ? (
                                    <>
                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                        Scanning...
                                    </>
                                ) : (
                                    <>
                                        <GitMerge className="h-4 w-4 mr-2" />
                                        {duplicateCheckMode === "all" &&
                                            "Find All Duplicates"}
                                        {duplicateCheckMode === "category" &&
                                            `Find in ${
                                                selectedCategories.size
                                            } Categor${
                                                selectedCategories.size === 1
                                                    ? "y"
                                                    : "ies"
                                            }`}
                                        {duplicateCheckMode === "entity" &&
                                            `Check ${
                                                selectedEntities.size
                                            } Entit${
                                                selectedEntities.size === 1
                                                    ? "y"
                                                    : "ies"
                                            }`}
                                    </>
                                )}
                            </Button>

                            {duplicates.length > 0 && (
                                <div className="space-y-2 max-h-64 overflow-y-auto">
                                    {duplicates.map((group, idx) => (
                                        <div
                                            key={idx}
                                            className="p-2 rounded border bg-gray-50"
                                        >
                                            <div className="flex items-center gap-2 mb-1">
                                                <Badge
                                                    variant="outline"
                                                    className="text-xs"
                                                >
                                                    {group.entity_type}
                                                </Badge>
                                                <span className="text-xs text-gray-500">
                                                    {Math.round(
                                                        group.confidence * 100
                                                    )}
                                                    % confidence
                                                </span>
                                            </div>
                                            <div className="flex items-center gap-1 mb-1">
                                                {group.entities.map((e, i) => (
                                                    <span key={e.vertex_id}>
                                                        <span
                                                            className={`text-sm ${
                                                                e.name ===
                                                                group.suggested_canonical
                                                                    ? "font-bold"
                                                                    : ""
                                                            }`}
                                                        >
                                                            {e.name}
                                                        </span>
                                                        {i <
                                                            group.entities
                                                                .length -
                                                                1 && (
                                                            <span className="text-gray-400 mx-1">
                                                                ≈
                                                            </span>
                                                        )}
                                                    </span>
                                                ))}
                                            </div>
                                            <p className="text-xs text-gray-600 mb-2">
                                                {group.reason}
                                            </p>
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={() =>
                                                    handleMergeEntities(group)
                                                }
                                                disabled={merging !== null}
                                                className="w-full"
                                            >
                                                {merging ===
                                                group.entities[0]?.vertex_id ? (
                                                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                                ) : (
                                                    <GitMerge className="h-3 w-3 mr-1" />
                                                )}
                                                Merge into "
                                                {group.suggested_canonical}"
                                            </Button>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {duplicateErrors.length > 0 && (
                                <div className="p-2 rounded border border-red-200 bg-red-50 text-xs">
                                    <p className="font-medium text-red-700 mb-1">
                                        Errors during scan:
                                    </p>
                                    <ul className="list-disc list-inside text-red-600 space-y-0.5">
                                        {duplicateErrors.map((err, i) => (
                                            <li
                                                key={i}
                                                className="truncate"
                                                title={err}
                                            >
                                                {err.includes("429") ||
                                                err.includes(
                                                    "RESOURCE_EXHAUSTED"
                                                )
                                                    ? "API rate limit exceeded - try again later"
                                                    : err.length > 60
                                                    ? err.substring(0, 60) +
                                                      "..."
                                                    : err}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {duplicates.length === 0 &&
                                duplicateErrors.length === 0 &&
                                !loadingDuplicates && (
                                    <p className="text-xs text-gray-500 italic text-center">
                                        No duplicates found (or scan hasn't been
                                        run yet)
                                    </p>
                                )}
                        </div>
                    </AccordionContent>
                </AccordionItem>
            </Accordion>

            {/* Fix Review Dialog */}
            <Dialog
                open={previewData !== null}
                onOpenChange={(open) => !open && setPreviewData(null)}
            >
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <CheckCircle className="h-4 w-4 text-green-600" />
                            Fix Applied Successfully
                        </DialogTitle>
                        <DialogDescription>
                            The following change was made to{" "}
                            <strong>{previewData?.issue.entity_name}</strong>
                        </DialogDescription>
                    </DialogHeader>

                    {previewData && (
                        <div className="space-y-4">
                            <div>
                                <Label className="text-xs text-gray-500">
                                    Field Updated
                                </Label>
                                <p className="font-medium text-blue-700">
                                    {previewData.field}
                                </p>
                            </div>

                            <div>
                                <Label className="text-xs text-gray-500">
                                    Previous Value
                                </Label>
                                <div className="p-2 bg-red-50 rounded text-sm font-mono border border-red-200 max-h-24 overflow-y-auto">
                                    {previewData.oldValue || (
                                        <span className="text-gray-400 italic">
                                            (no value)
                                        </span>
                                    )}
                                </div>
                            </div>

                            <div>
                                <Label className="text-xs text-gray-500">
                                    New Value
                                </Label>
                                <div className="p-2 bg-green-50 rounded text-sm font-mono border border-green-200 max-h-24 overflow-y-auto">
                                    {previewData.newValue || (
                                        <span className="text-gray-400 italic">
                                            (no value)
                                        </span>
                                    )}
                                </div>
                            </div>

                            {previewData.explanation && (
                                <div>
                                    <Label className="text-xs text-gray-500">
                                        Explanation
                                    </Label>
                                    <p className="text-sm text-gray-600 italic bg-blue-50 p-2 rounded">
                                        {previewData.explanation}
                                    </p>
                                </div>
                            )}

                            {previewData.oldValue === previewData.newValue && (
                                <div className="p-2 bg-yellow-50 rounded border border-yellow-200 text-sm text-yellow-700">
                                    ⚠️ No change was needed - the value was
                                    already correct.
                                </div>
                            )}
                        </div>
                    )}

                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setPreviewData(null)}
                        >
                            Close
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Story Text Fix Preview Dialog */}
            <Dialog
                open={storyTextPreview !== null}
                onOpenChange={(open) => !open && setStoryTextPreview(null)}
            >
                <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Wand2 className="h-4 w-4 text-purple-600" />
                            Review Story Fix
                        </DialogTitle>
                        <DialogDescription>
                            Review the suggested text change for{" "}
                            <strong>{storyTextPreview?.chapterName}</strong>
                        </DialogDescription>
                    </DialogHeader>

                    {storyTextPreview && (
                        <div className="space-y-4 flex-1 overflow-y-auto">
                            <div className="p-2 bg-purple-50 rounded border border-purple-200">
                                <Label className="text-xs text-purple-700 font-medium">
                                    Issue: {storyTextPreview.issue.title}
                                </Label>
                                {storyTextPreview.issue.description && (
                                    <p className="text-xs text-purple-600 mt-1">
                                        {storyTextPreview.issue.description}
                                    </p>
                                )}
                            </div>

                            <div>
                                <Label className="text-xs text-gray-500 flex items-center gap-1">
                                    <span className="text-red-500">●</span>{" "}
                                    Original Text (will be replaced)
                                </Label>
                                <div className="p-3 bg-red-50 rounded text-sm font-mono border border-red-200 max-h-32 overflow-y-auto whitespace-pre-wrap">
                                    {storyTextPreview.oldText || (
                                        <span className="text-gray-400 italic">
                                            (text not found)
                                        </span>
                                    )}
                                </div>
                            </div>

                            <div>
                                <Label className="text-xs text-gray-500 flex items-center gap-1">
                                    <span className="text-green-500">●</span>{" "}
                                    Revised Text (editable)
                                </Label>
                                <Textarea
                                    value={editedStoryText}
                                    onChange={(e) =>
                                        setEditedStoryText(e.target.value)
                                    }
                                    className="min-h-[120px] font-mono text-sm bg-green-50 border-green-200"
                                    placeholder="Enter the revised text..."
                                />
                            </div>

                            {storyTextPreview.explanation && (
                                <div>
                                    <Label className="text-xs text-gray-500">
                                        AI Explanation
                                    </Label>
                                    <p className="text-sm text-gray-600 italic bg-blue-50 p-2 rounded">
                                        {storyTextPreview.explanation}
                                    </p>
                                </div>
                            )}

                            <div className="p-2 bg-yellow-50 rounded border border-yellow-200 text-xs text-yellow-700">
                                <strong>💡 Tip:</strong> The revised text will
                                replace the original text in your chapter. You
                                can edit it before applying.
                            </div>
                        </div>
                    )}

                    <DialogFooter className="gap-2">
                        <Button
                            variant="outline"
                            onClick={() => setStoryTextPreview(null)}
                        >
                            Cancel
                        </Button>
                        <Button
                            onClick={confirmStoryTextFix}
                            disabled={!editedStoryText.trim()}
                            className="bg-purple-600 hover:bg-purple-700"
                        >
                            <CheckCircle className="h-4 w-4 mr-2" />
                            Apply Fix to Chapter
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

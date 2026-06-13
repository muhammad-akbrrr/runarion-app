import { useState } from "react";
import { Button } from "@/Components/ui/button";
import { Badge } from "@/Components/ui/badge";
import {
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/Components/ui/accordion";
import { GitMerge, Loader2 } from "lucide-react";
import type { DuplicateGroup, SharedSectionProps } from "./types";
import { postJson } from "./utils";
import CategoryEntityPicker, {
    type PickerMode,
} from "./Shared/CategoryEntityPicker";
import { toast } from "sonner";
import { useConfirm } from "@/Components/ConfirmDialogProvider";

interface DuplicateFinderSectionProps extends SharedSectionProps {
    // Persisted state from parent
    duplicates: DuplicateGroup[];
    onDuplicatesChange: (duplicates: DuplicateGroup[]) => void;
}

export default function DuplicateFinderSection({
    workspaceId,
    projectId,
    selectedModel,
    availableCategories,
    availableEntities,
    loadingCategories,
    loadingEntities,
    loadEntitiesForCategory,
    duplicates,
    onDuplicatesChange,
}: DuplicateFinderSectionProps) {
    const confirm = useConfirm();
    const [loadingDuplicates, setLoadingDuplicates] = useState(false);
    const [duplicateErrors, setDuplicateErrors] = useState<string[]>([]);
    const [merging, setMerging] = useState<string | null>(null);

    // Selection state
    const [duplicateCheckMode, setDuplicateCheckMode] =
        useState<PickerMode>("all");
    const [selectedCategories, setSelectedCategories] = useState<Set<string>>(
        new Set(),
    );
    const [selectedEntities, setSelectedEntities] = useState<Set<string>>(
        new Set(),
    );
    const [expandedCategory, setExpandedCategory] = useState<string | null>(
        null,
    );

    const handleFindDuplicates = async () => {
        setLoadingDuplicates(true);
        onDuplicatesChange([]);
        setDuplicateErrors([]);

        const targetCategories =
            duplicateCheckMode === "category"
                ? Array.from(selectedCategories)
                : null;
        const targetEntities =
            duplicateCheckMode === "entity"
                ? Array.from(selectedEntities)
                : null;

        try {
            const response = await postJson(
                `/${workspaceId}/projects/${projectId}/editor/auditor/find-duplicates`,
                {
                    model: selectedModel,
                    provider: "gemini",
                    scope: duplicateCheckMode,
                    categories: targetCategories,
                    entity_ids: targetEntities,
                },
            );

            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                onDuplicatesChange(data.results?.potential_duplicates || []);
                const errors = data.results?.errors || [];
                setDuplicateErrors(errors);

                if (
                    errors.length > 0 &&
                    (data.results?.potential_duplicates || []).length === 0
                ) {
                    const hasRateLimit = errors.some(
                        (e: string) =>
                            e.includes("429") ||
                            e.includes("quota") ||
                            e.includes("RESOURCE_EXHAUSTED"),
                    );
                    if (hasRateLimit) {
                        toast.error(
                            "API rate limit exceeded. Please wait and try again, or use a paid API key.",
                        );
                    }
                }
            } else {
                const errorData = response.data;
                const errorMsg =
                    errorData.details?.error ||
                    errorData.error ||
                    "Unknown error";
                if (errorMsg.includes("429") || errorMsg.includes("quota")) {
                    toast.error(
                        "API rate limit exceeded. Please wait and try again, or use a paid API key.",
                    );
                } else {
                    toast.error(`Failed to find duplicates: ${errorMsg}`);
                }
            }
        } catch (error) {
            console.error("Error finding duplicates:", error);
            toast.error(`Failed to find duplicates: ${error}`);
        } finally {
            setLoadingDuplicates(false);
        }
    };

    const handleMergeEntities = async (group: DuplicateGroup) => {
        if (group.entities.length < 2) return;

        // Find target first (the canonical entity to keep)
        // Use case-insensitive comparison and trim whitespace
        const canonicalLower = group.suggested_canonical.toLowerCase().trim();
        const target =
            group.entities.find(
                (e) => e.name.toLowerCase().trim() === canonicalLower,
            ) || group.entities[0];

        // Source is any entity that's NOT the target
        const source = group.entities.find(
            (e) => e.vertex_id !== target.vertex_id,
        );

        if (!source || !target) return;

        if (
            !(await confirm({
                title: "Merge duplicate entities?",
                description: `Merge "${source.name}" into "${target.name}"?\n\nThis will:\n- Combine properties from both entities\n- Delete "${source.name}"\n- Keep "${target.name}" as the canonical entity`,
                actionLabel: "Merge entities",
            }))
        ) {
            return;
        }

        setMerging(source.vertex_id);
        try {
            const response = await postJson(
                `/${workspaceId}/projects/${projectId}/editor/auditor/merge-entities`,
                {
                    source_vertex_id: source.vertex_id,
                    target_vertex_id: target.vertex_id,
                    merge_strategy: "combine",
                },
            );

            if (response.status >= 200 && response.status < 300) {
                // Remove the merged group from local state
                onDuplicatesChange(
                    duplicates.filter(
                        (g) =>
                            g.entities[0]?.vertex_id !==
                            group.entities[0]?.vertex_id,
                    ),
                );
                console.log("Entities merged successfully!");
            } else {
                const error = response.data;
                const errorMsg =
                    error.details?.error || error.error || "Unknown error";
                toast.error(`Failed to merge: ${errorMsg}`);
            }
        } catch (error) {
            console.error("Error merging entities:", error);
            toast.error("Failed to merge entities");
        } finally {
            setMerging(null);
        }
    };

    const isDisabled =
        loadingDuplicates ||
        (duplicateCheckMode === "category" && selectedCategories.size === 0) ||
        (duplicateCheckMode === "entity" && selectedEntities.size === 0);

    return (
        <AccordionItem value="duplicates">
            <AccordionTrigger className="hover:no-underline">
                <div className="flex items-center gap-2">
                    <GitMerge className="h-4 w-4 text-green-600" />
                    <span className="font-medium">Record Optimizer</span>
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
                        Find potential duplicate entities (same entity with
                        different names) and merge them to clean up your
                        database.
                    </p>

                    <CategoryEntityPicker
                        mode={duplicateCheckMode}
                        onModeChange={setDuplicateCheckMode}
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
                        accentColor="green"
                    />

                    <Button
                        size="sm"
                        onClick={handleFindDuplicates}
                        disabled={isDisabled}
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
                                    `Find in ${selectedCategories.size} Categor${
                                        selectedCategories.size === 1
                                            ? "y"
                                            : "ies"
                                    }`}
                                {duplicateCheckMode === "entity" &&
                                    `Check ${selectedEntities.size} Entit${
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
                                            {Math.round(group.confidence * 100)}
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
                                                    group.entities.length -
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
                                        className="w-full truncate overflow-hidden max-w-full whitespace-normal! min-h-8! h-auto!"
                                    >
                                        {merging ===
                                        group.entities[0]?.vertex_id ? (
                                            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                        ) : (
                                            <GitMerge className="h-3 w-3 mr-1" />
                                        )}
                                        Merge into "{group.suggested_canonical}"
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
                                        err.includes("RESOURCE_EXHAUSTED")
                                            ? "API rate limit exceeded - try again later"
                                            : err.length > 60
                                              ? err.substring(0, 60) + "..."
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
                                No duplicates found (or scan hasn't been run
                                yet)
                            </p>
                        )}
                </div>
            </AccordionContent>
        </AccordionItem>
    );
}

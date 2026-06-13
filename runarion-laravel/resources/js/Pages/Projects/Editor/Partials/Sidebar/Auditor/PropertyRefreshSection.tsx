import { useState } from "react";
import { Button } from "@/Components/ui/button";
import { Badge } from "@/Components/ui/badge";
import {
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/Components/ui/accordion";
import { Sparkles, Loader2, ArrowRightIcon } from "lucide-react";
import type { RefreshResults, SharedSectionProps } from "./types";
import { postJson } from "./utils";
import CategoryEntityPicker, {
    type PickerMode,
} from "./Shared/CategoryEntityPicker";
import { toast } from "sonner";
import { useConfirm } from "@/Components/ConfirmDialogProvider";

interface PropertyRefreshSectionProps extends SharedSectionProps {
    // Persisted state from parent
    refreshResults: RefreshResults | null;
    onRefreshResultsChange: (results: RefreshResults | null) => void;
}

export default function PropertyRefreshSection({
    workspaceId,
    projectId,
    selectedModel,
    availableCategories,
    availableEntities,
    loadingCategories,
    loadingEntities,
    loadEntitiesForCategory,
    refreshResults,
    onRefreshResultsChange,
}: PropertyRefreshSectionProps) {
    const confirm = useConfirm();
    const [loadingRefresh, setLoadingRefresh] = useState(false);

    // Selection state
    const [refreshMode, setRefreshMode] = useState<PickerMode>("all");
    const [selectedCategories, setSelectedCategories] = useState<Set<string>>(
        new Set(),
    );
    const [selectedEntities, setSelectedEntities] = useState<Set<string>>(
        new Set(),
    );
    const [expandedCategory, setExpandedCategory] = useState<string | null>(
        null,
    );

    const handleRefreshAllProperties = async () => {
        const targetCategories =
            refreshMode === "category" ? Array.from(selectedCategories) : null;
        const targetEntities =
            refreshMode === "entity" ? Array.from(selectedEntities) : null;

        let message =
            "This will update ALL entity properties to reflect their current state in the story.\n\nCharacters who have changed (e.g., brave → cowardly) will have their properties updated.\n\nPrevious values will be backed up.\n\nContinue?";

        if (refreshMode === "category") {
            message = `This will update entity properties for categories: ${targetCategories?.join(
                ", ",
            )}\n\nPrevious values will be backed up.\n\nContinue?`;
        } else if (refreshMode === "entity") {
            message = `This will update ${
                targetEntities?.length
            } selected entit${
                targetEntities?.length === 1 ? "y" : "ies"
            }.\n\nPrevious values will be backed up.\n\nContinue?`;
        }

        if (
            !(await confirm({
                title: "Refresh entity properties?",
                description: message,
                actionLabel: "Refresh properties",
            }))
        ) {
            return;
        }

        setLoadingRefresh(true);
        onRefreshResultsChange(null);

        try {
            const response = await postJson(
                `/${workspaceId}/projects/${projectId}/editor/auditor/refresh-all-properties`,
                {
                    model: selectedModel,
                    provider: "gemini",
                    categories: targetCategories,
                    entity_ids: targetEntities,
                },
            );

            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                onRefreshResultsChange(data.results || null);
            } else {
                try {
                    const errorData = response.data;
                    const errorMsg =
                        errorData.details?.error ||
                        errorData.error ||
                        "Unknown error";

                    if (
                        errorMsg.includes("429") ||
                        errorMsg.includes("quota") ||
                        errorMsg.includes("RESOURCE_EXHAUSTED")
                    ) {
                        toast.error(
                            "API rate limit exceeded. Please wait a minute and try again, or use a paid API key.",
                        );
                    } else {
                        toast.error(`Failed to refresh: ${errorMsg}`);
                    }
                } catch {
                    toast.error(`Failed to refresh: HTTP ${response.status}`);
                }
            }
        } catch (error) {
            console.error("Error refreshing properties:", error);
            toast.error(`Failed to refresh: ${error}`);
        } finally {
            setLoadingRefresh(false);
        }
    };

    const isDisabled =
        loadingRefresh ||
        (refreshMode === "category" && selectedCategories.size === 0) ||
        (refreshMode === "entity" && selectedEntities.size === 0);

    return (
        <AccordionItem value="property-refresh">
            <AccordionTrigger className="hover:no-underline">
                <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-indigo-600" />
                    <span className="font-medium">Property Refresh</span>
                    {refreshResults && refreshResults.entities_updated > 0 && (
                        <Badge
                            variant="outline"
                            className="ml-2 bg-indigo-50 text-indigo-700"
                        >
                            {refreshResults.entities_updated} updated
                        </Badge>
                    )}
                </div>
            </AccordionTrigger>
            <AccordionContent>
                <div className="space-y-3 pt-2">
                    <p className="text-xs text-gray-500">
                        <strong>Arc-Aware Updates:</strong> Updates entity
                        properties to reflect their <em>current state</em> in
                        the story. Characters who have changed (brave →
                        cowardly, determined → broken) will be updated. Previous
                        values are backed up.
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
                                Determines each entity's <em>current</em> state
                            </li>
                            <li>
                                Updates properties to match where story is NOW
                            </li>
                            <li>
                                Logs changes with chapter references & reasons
                            </li>
                        </ul>
                    </div>

                    <CategoryEntityPicker
                        mode={refreshMode}
                        onModeChange={setRefreshMode}
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
                        accentColor="indigo"
                        showCategoryCheckbox={true}
                    />

                    <Button
                        size="sm"
                        onClick={handleRefreshAllProperties}
                        disabled={isDisabled}
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
                                    `Refresh ${selectedEntities.size} Entit${
                                        selectedEntities.size === 1
                                            ? "y"
                                            : "ies"
                                    }`}
                            </>
                        )}
                    </Button>

                    {loadingRefresh && (
                        <div className="p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-700">
                            <strong>Processing in batches...</strong> Each
                            entity is analyzed against your story. For large
                            databases, this can take 2-5 minutes. Please don't
                            close this tab.
                        </div>
                    )}

                    {refreshResults && (
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-xs font-medium text-indigo-700">
                                    Refresh complete
                                </span>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-6 text-xs text-gray-400 hover:text-red-500"
                                    onClick={() => onRefreshResultsChange(null)}
                                >
                                    Clear
                                </Button>
                            </div>

                            <div className="grid grid-cols-3 gap-2 text-center">
                                <div className="p-2 bg-gray-50 rounded">
                                    <div className="text-lg font-bold">
                                        {refreshResults.entities_processed}
                                    </div>
                                    <div className="text-xs text-gray-500">
                                        Processed
                                    </div>
                                </div>
                                <div className="p-2 bg-indigo-50 rounded">
                                    <div className="text-lg font-bold text-indigo-700">
                                        {refreshResults.entities_updated}
                                    </div>
                                    <div className="text-xs text-indigo-600">
                                        Updated
                                    </div>
                                </div>
                                <div className="p-2 bg-green-50 rounded">
                                    <div className="text-lg font-bold text-green-700">
                                        {refreshResults.entities_unchanged}
                                    </div>
                                    <div className="text-xs text-green-600">
                                        Current
                                    </div>
                                </div>
                            </div>

                            {Object.keys(refreshResults.changes_by_entity)
                                .length > 0 && (
                                <div className="max-h-64 overflow-y-auto space-y-2">
                                    {Object.entries(
                                        refreshResults.changes_by_entity,
                                    ).map(([entityName, changes]) => (
                                        <div
                                            key={entityName}
                                            className="p-2 flex flex-col gap-1.5 rounded border bg-white"
                                        >
                                            <div className="font-medium text-sm">
                                                {entityName}
                                            </div>
                                            {changes.map((change, idx) => (
                                                <div
                                                    key={idx}
                                                    className="flex flex-col gap-2 text-xs bg-gray-50 p-1.5 rounded mt-1"
                                                >
                                                    <div className="flex items-center gap-x-2 gap-y-1 flex-wrap">
                                                        <span className="font-medium">
                                                            {change.field}:
                                                        </span>
                                                        <span className="text-red-600 line-through">
                                                            {String(
                                                                change.old_value,
                                                            ).slice(0, 30)}
                                                        </span>
                                                        <ArrowRightIcon className="h-3 w-3 text-gray-400" />
                                                        <span className="text-green-600">
                                                            {String(
                                                                change.new_value,
                                                            ).slice(0, 30)}
                                                        </span>
                                                    </div>
                                                    {change.reason && (
                                                        <div className="text-gray-500 italic">
                                                            {change.chapter_reference &&
                                                                `Ch. ${change.chapter_reference}: `}
                                                            {change.reason}
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
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
                                            ),
                                        )}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}

                    {!refreshResults && !loadingRefresh && (
                        <p className="text-xs text-gray-500 italic text-center">
                            Run refresh to update entity properties to current
                            story state
                        </p>
                    )}
                </div>
            </AccordionContent>
        </AccordionItem>
    );
}

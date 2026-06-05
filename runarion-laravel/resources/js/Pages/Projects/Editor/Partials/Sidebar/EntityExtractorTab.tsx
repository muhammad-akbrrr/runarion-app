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
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/Components/ui/tooltip";
import { Checkbox } from "@/Components/ui/checkbox";
import { HelpCircle, Play } from "lucide-react";
import { http } from "@/Lib/http";

interface EntityExtractorTabProps {
    workspaceId: string;
    projectId: string;
    selectedModel: string;
}

interface Chapter {
    order: number;
    chapter_name: string;
    content: string;
}

interface CollectionType {
    id: string;
    name: string;
    value: string;
    is_system?: boolean;
}

export default function EntityExtractorTab({
    workspaceId,
    projectId,
    selectedModel,
}: EntityExtractorTabProps) {
    const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
    const [useAllCategories, setUseAllCategories] = useState<boolean>(true);
    const [selectedChapters, setSelectedChapters] = useState<number[]>([]);
    const [useAllChapters, setUseAllChapters] = useState<boolean>(true);
    const [scanMode, setScanMode] = useState<
        "incremental" | "full" | "new_only"
    >("incremental");
    const [chapters, setChapters] = useState<Chapter[]>([]);
    const [collectionTypes, setCollectionTypes] = useState<CollectionType[]>(
        []
    );
    const [loading, setLoading] = useState(false);
    const [showConfirmDialog, setShowConfirmDialog] = useState(false);
    const [estimatedTime, setEstimatedTime] = useState<string>("");

    // Load chapters and collection types on mount
    useEffect(() => {
        loadChapters();
        loadCollectionTypes();
    }, []);

    // Calculate estimated time when settings change
    useEffect(() => {
        calculateEstimatedTime();
    }, [
        selectedCategories,
        useAllCategories,
        selectedChapters,
        useAllChapters,
        chapters.length,
        collectionTypes.length,
    ]);

    const loadChapters = async () => {
        try {
            const response = await http(
                route("editor.project.chapters", {
                    workspace_id: workspaceId,
                    project_id: projectId,
                }),
                {
                    headers: {
                        Accept: "application/json",
                        "X-Requested-With": "XMLHttpRequest",
                    },
                }
            );
            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                if (data.chapters) {
                    setChapters(data.chapters);
                }
            }
        } catch (error) {
            console.error("Error loading chapters:", error);
        }
    };

    const loadCollectionTypes = async () => {
        try {
            const response = await http(
                route("records.collection-types.list", {
                    workspace_id: workspaceId,
                    project_id: projectId,
                }),
                { headers: { Accept: "application/json" } }
            );
            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                const systemTypes = [
                    {
                        id: "character",
                        name: "Character",
                        value: "character",
                        is_system: true,
                    },
                    {
                        id: "location",
                        name: "Location",
                        value: "location",
                        is_system: true,
                    },
                    {
                        id: "item",
                        name: "Item",
                        value: "item",
                        is_system: true,
                    },
                    {
                        id: "theme",
                        name: "Theme",
                        value: "theme",
                        is_system: true,
                    },
                    {
                        id: "plot_point",
                        name: "Plot Point",
                        value: "plot_point",
                        is_system: true,
                    },
                ];
                const customTypes = (data.collection_types?.custom || []).map(
                    (type: any) => ({
                        id: type.id,
                        name: type.name,
                        value: type.name.toLowerCase().replace(/\s+/g, "_"),
                        is_system: false,
                    })
                );
                // Exclude Record Keeper (not a category for extraction)
                setCollectionTypes([...systemTypes, ...customTypes]);
            }
        } catch (error) {
            console.error("Error loading collection types:", error);
        }
    };

    const calculateEstimatedTime = () => {
        const categoriesToProcess = useAllCategories
            ? collectionTypes.length
            : selectedCategories.length;

        // Estimate: 60 seconds per category (processes all chapters at once)
        const baseTime = categoriesToProcess * 60;

        const minutes = Math.ceil(baseTime / 60);
        if (minutes < 1) {
            setEstimatedTime("Less than 1 minute");
        } else if (minutes === 1) {
            setEstimatedTime("~1 minute");
        } else {
            setEstimatedTime(`~${minutes} minutes`);
        }
    };

    const handleStart = () => {
        if (useAllCategories && collectionTypes.length === 0) {
            alert(
                "No categories available. Please create some collection types first."
            );
            return;
        }
        if (!useAllCategories && selectedCategories.length === 0) {
            alert("Please select at least one category");
            return;
        }
        setShowConfirmDialog(true);
    };

    const handleConfirm = async () => {
        setShowConfirmDialog(false);
        setLoading(true);

        try {
            const categories = useAllCategories
                ? ["all_categories"]
                : selectedCategories;

            const response = await http(
                route("auditor.extract", {
                    workspace_id: workspaceId,
                    project_id: projectId,
                }),
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                    },
                    data: {
                        categories: categories,
                        chapter_orders: useAllChapters
                            ? null
                            : selectedChapters,
                        scan_mode: useAllChapters ? scanMode : "full", // If specific chapters selected, always use full
                        model: selectedModel,
                        provider: "gemini",
                    },
                }
            );

            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                const created = data.results?.entities_created || 0;
                const updated = data.results?.entities_updated || 0;
                const categoriesProcessed =
                    data.results?.categories_processed || {};
                const errors = data.results?.errors || [];

                let message = `Entity extraction complete!\n\nCreated: ${created} entities\nUpdated: ${updated} entities\n\n`;

                // Add per-category breakdown
                const categoryNames = Object.keys(categoriesProcessed);
                if (categoryNames.length > 0) {
                    message += "By Category:\n";
                    categoryNames.forEach((cat) => {
                        const stats = categoriesProcessed[cat];
                        message += `  ${cat}: ${stats.created} created, ${stats.updated} updated\n`;
                    });
                }

                if (errors.length > 0) {
                    message += `\n\nErrors (${errors.length}):\n${errors
                        .slice(0, 5)
                        .join("\n")}`;
                    if (errors.length > 5) {
                        message += `\n... and ${errors.length - 5} more errors`;
                    }
                }

                if (created === 0 && updated === 0) {
                    message += `\n\n⚠️ No entities were extracted. This might mean:\n- No entities of selected categories found in manuscript\n- Chapter content is too short\n- Check Python logs for details`;
                }

                alert(message);

                // Reload entities to show new ones
                if (created > 0 || updated > 0) {
                    // Dispatch custom event to trigger entity refresh in RecordsPanel
                    window.dispatchEvent(
                        new CustomEvent("entities-extracted", {
                            detail: { created, updated },
                        })
                    );
                }
            } else {
                const error = response.data;
                let errorMessage = `Failed to extract entities: ${
                    error.error || "Unknown error"
                }`;
                if (error.details) {
                    errorMessage += `\n\nDetails: ${JSON.stringify(
                        error.details,
                        null,
                        2
                    )}`;
                }
                alert(errorMessage);
            }
        } catch (error: any) {
            console.error("Error extracting entities:", error);
            alert(
                `Failed to extract entities: ${error?.message || String(error)}`
            );
        } finally {
            setLoading(false);
        }
    };

    const toggleCategory = (categoryValue: string) => {
        if (selectedCategories.includes(categoryValue)) {
            setSelectedCategories(
                selectedCategories.filter((c) => c !== categoryValue)
            );
        } else {
            setSelectedCategories([...selectedCategories, categoryValue]);
        }
    };

    return (
        <div className="space-y-6">
            {/* Description */}
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-center gap-2 mb-2">
                    <h3 className="text-sm font-semibold text-blue-900">
                        Entity Extractor
                    </h3>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <HelpCircle className="h-4 w-4 text-blue-600 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs">
                            <p>
                                Automatically extracts entities from your
                                manuscript content. Works with both system
                                categories (Character, Location, etc.) and
                                custom categories you create. Entities are
                                created/updated in the Records System with
                                properties extracted from the text.
                            </p>
                        </TooltipContent>
                    </Tooltip>
                </div>
                <p className="text-xs text-blue-700">
                    Scans your entire manuscript and extracts entities based on
                    selected categories. Custom categories use their field
                    schemas to extract relevant information dynamically.
                </p>
            </div>

            {/* Category Selection */}
            <div>
                <div className="flex items-center gap-2 mb-2">
                    <Label className="text-sm font-medium">Categories:</Label>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs">
                            <p>
                                Select which entity categories to extract. "All
                                Categories" processes all system and custom
                                categories sequentially. Custom categories will
                                extract fields based on their field schemas.
                            </p>
                        </TooltipContent>
                    </Tooltip>
                </div>
                <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                        <Checkbox
                            id="all-categories"
                            checked={useAllCategories}
                            onCheckedChange={(checked) => {
                                setUseAllCategories(checked as boolean);
                                if (checked) {
                                    setSelectedCategories([]);
                                }
                            }}
                        />
                        <Label
                            htmlFor="all-categories"
                            className="text-sm cursor-pointer"
                        >
                            All Categories ({collectionTypes.length} categories)
                        </Label>
                    </div>
                    {!useAllCategories && (
                        <div className="max-h-60 overflow-y-auto border rounded p-2 space-y-2">
                            {collectionTypes.length === 0 ? (
                                <p className="text-sm text-gray-500 italic">
                                    No categories found.
                                </p>
                            ) : (
                                collectionTypes.map((type) => (
                                    <div
                                        key={type.id}
                                        className="flex items-center space-x-2"
                                    >
                                        <Checkbox
                                            id={`category-${type.id}`}
                                            checked={selectedCategories.includes(
                                                type.value
                                            )}
                                            onCheckedChange={() =>
                                                toggleCategory(type.value)
                                            }
                                        />
                                        <Label
                                            htmlFor={`category-${type.id}`}
                                            className="text-sm cursor-pointer"
                                        >
                                            {type.name}
                                        </Label>
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Chapter Selection */}
            <div>
                <div className="flex items-center gap-2 mb-2">
                    <Label className="text-sm font-medium">Chapters:</Label>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs">
                            <p>
                                Select which chapters to extract entities from.
                                Usually you want all chapters to get a complete
                                picture of all entities in your story.
                            </p>
                        </TooltipContent>
                    </Tooltip>
                </div>
                <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                        <Checkbox
                            id="all-chapters-extract"
                            checked={useAllChapters}
                            onCheckedChange={(checked) => {
                                setUseAllChapters(checked as boolean);
                                if (checked) {
                                    setSelectedChapters([]);
                                }
                            }}
                        />
                        <Label
                            htmlFor="all-chapters-extract"
                            className="text-sm cursor-pointer"
                        >
                            All Chapters ({chapters.length} chapters)
                        </Label>
                    </div>
                    {!useAllChapters && (
                        <div className="max-h-40 overflow-y-auto border rounded p-2 space-y-2">
                            {chapters.length === 0 ? (
                                <p className="text-sm text-gray-500 italic">
                                    No chapters found.
                                </p>
                            ) : (
                                chapters.map((chapter) => (
                                    <div
                                        key={chapter.order}
                                        className="flex items-center space-x-2"
                                    >
                                        <Checkbox
                                            id={`chapter-extract-${chapter.order}`}
                                            checked={selectedChapters.includes(
                                                chapter.order
                                            )}
                                            onCheckedChange={(checked) => {
                                                if (checked) {
                                                    setSelectedChapters([
                                                        ...selectedChapters,
                                                        chapter.order,
                                                    ]);
                                                } else {
                                                    setSelectedChapters(
                                                        selectedChapters.filter(
                                                            (o) =>
                                                                o !==
                                                                chapter.order
                                                        )
                                                    );
                                                }
                                            }}
                                        />
                                        <Label
                                            htmlFor={`chapter-extract-${chapter.order}`}
                                            className="text-sm cursor-pointer"
                                        >
                                            Chapter {chapter.order + 1}:{" "}
                                            {chapter.chapter_name}
                                        </Label>
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Scan Mode Selection (only when using all chapters) */}
            {useAllChapters && (
                <div>
                    <div className="flex items-center gap-2 mb-2">
                        <Label className="text-sm font-medium">
                            Scan Mode:
                        </Label>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs">
                                <p>
                                    <strong>Incremental:</strong> Only process
                                    chapters that have changed or never been
                                    scanned. Saves time and API costs.
                                    <br />
                                    <br />
                                    <strong>Full Rescan:</strong> Process all
                                    chapters regardless of previous scans. Use
                                    when you want fresh extraction.
                                    <br />
                                    <br />
                                    <strong>New Only:</strong> Only process
                                    chapters that have never been scanned
                                    before.
                                </p>
                            </TooltipContent>
                        </Tooltip>
                    </div>
                    <Select
                        value={scanMode}
                        onValueChange={(
                            value: "incremental" | "full" | "new_only"
                        ) => setScanMode(value)}
                    >
                        <SelectTrigger className="w-full">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="incremental">
                                Incremental (only changed/new)
                            </SelectItem>
                            <SelectItem value="full">
                                Full Rescan (all chapters)
                            </SelectItem>
                            <SelectItem value="new_only">
                                New Only (unscanned chapters)
                            </SelectItem>
                        </SelectContent>
                    </Select>
                    <p className="text-xs text-gray-500 mt-1">
                        {scanMode === "incremental" &&
                            "Processes only chapters with changes since last scan."}
                        {scanMode === "full" &&
                            "Rescans all chapters - useful if you want fresh extraction."}
                        {scanMode === "new_only" &&
                            "Only processes chapters that have never been scanned."}
                    </p>
                </div>
            )}

            {/* Estimated Time */}
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-center gap-2">
                    <p className="text-sm text-blue-800">
                        <strong>Estimated Time:</strong>{" "}
                        {estimatedTime || "Calculating..."}
                    </p>
                </div>
                <p className="text-xs text-blue-600 mt-1">
                    {scanMode === "incremental"
                        ? "Incremental mode will skip chapters that haven't changed since last scan."
                        : "Extraction processes all selected chapters at once for each category."}{" "}
                    Entities are created or updated in the Records System. You
                    can navigate away and will be notified when complete.
                </p>
            </div>

            {/* Start Button */}
            <Button
                onClick={handleStart}
                disabled={
                    loading ||
                    (!useAllCategories && selectedCategories.length === 0)
                }
                className="w-full"
            >
                <Play className="h-4 w-4 mr-2" />
                {loading ? "Extracting..." : "Start Extraction"}
            </Button>
            <p className="text-xs text-gray-500 text-center">
                This will extract entities from your manuscript and
                create/update them in the Records System based on selected
                categories.
            </p>

            {/* Confirmation Dialog */}
            <Dialog
                open={showConfirmDialog}
                onOpenChange={setShowConfirmDialog}
            >
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Confirm Entity Extraction</DialogTitle>
                        <DialogDescription>
                            This will extract entities from your manuscript and
                            create/update them in the Records System. You can
                            navigate away and will be notified when complete.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-2 py-4">
                        <div className="text-sm">
                            <strong>Categories:</strong>{" "}
                            {useAllCategories
                                ? `All (${collectionTypes.length})`
                                : `${selectedCategories.length} selected`}
                        </div>
                        <div className="text-sm">
                            <strong>Chapters:</strong>{" "}
                            {useAllChapters
                                ? `All (${chapters.length})`
                                : `${selectedChapters.length} selected`}
                        </div>
                        <div className="text-sm">
                            <strong>Model:</strong> {selectedModel}
                        </div>
                        <div className="text-sm">
                            <strong>Estimated Time:</strong>{" "}
                            {estimatedTime || "Calculating..."}
                        </div>
                    </div>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setShowConfirmDialog(false)}
                        >
                            Cancel
                        </Button>
                        <Button onClick={handleConfirm}>Confirm & Start</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

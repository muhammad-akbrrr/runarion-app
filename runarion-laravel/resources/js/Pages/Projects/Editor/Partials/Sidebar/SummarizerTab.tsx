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
import { RadioGroup, RadioGroupItem } from "@/Components/ui/radio-group";
import { HelpCircle, Play, AlertCircle } from "lucide-react";

interface SummarizerTabProps {
    workspaceId: string;
    projectId: string;
    selectedModel: string;
}

interface Entity {
    vertex_id: string;  // String to avoid JS precision loss with large Apache AGE IDs
    name: string;
    type: string;
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

export default function SummarizerTab({ 
    workspaceId, 
    projectId, 
    selectedModel 
}: SummarizerTabProps) {
    const [enableRecordKeeper, setEnableRecordKeeper] = useState<boolean>(true);
    const [selectedCategory, setSelectedCategory] = useState<string>("none");
    const [analysisMode, setAnalysisMode] = useState<"all" | "focused">("all");
    const [selectedEntities, setSelectedEntities] = useState<number[]>([]);
    const [selectedChapters, setSelectedChapters] = useState<number[]>([]);
    const [useAllChapters, setUseAllChapters] = useState<boolean>(true);
    const [entities, setEntities] = useState<Entity[]>([]);
    const [chapters, setChapters] = useState<Chapter[]>([]);
    const [collectionTypes, setCollectionTypes] = useState<CollectionType[]>([]);
    const [loading, setLoading] = useState(false);
    const [showConfirmDialog, setShowConfirmDialog] = useState(false);
    const [estimatedTime, setEstimatedTime] = useState<string>("");

    // Load entities, chapters, and collection types on mount
    useEffect(() => {
        loadEntities();
        loadChapters();
        loadCollectionTypes();
    }, []);

    // Reset selected entities when category or mode changes
    useEffect(() => {
        setSelectedEntities([]);
    }, [selectedCategory, analysisMode]);

    // Calculate estimated time when settings change
    useEffect(() => {
        calculateEstimatedTime();
    }, [selectedCategory, analysisMode, selectedEntities, selectedChapters, useAllChapters, chapters.length, entities.length]);

    const loadEntities = async () => {
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/records/entities`,
                { headers: { "Accept": "application/json" } }
            );
            if (response.ok) {
                const data = await response.json();
                setEntities(data.entities || []);
            }
        } catch (error) {
            console.error("Error loading entities:", error);
        }
    };

    const loadChapters = async () => {
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/chapters`,
                { 
                    headers: { 
                        "Accept": "application/json",
                        "X-Requested-With": "XMLHttpRequest"
                    } 
                }
            );
            if (response.ok) {
                const data = await response.json();
                if (data.chapters) {
                    setChapters(data.chapters);
                }
            } else {
                console.error("Failed to load chapters:", response.status);
            }
        } catch (error) {
            console.error("Error loading chapters:", error);
        }
    };

    const loadCollectionTypes = async () => {
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/records/collection-types`,
                { headers: { "Accept": "application/json" } }
            );
            if (response.ok) {
                const data = await response.json();
                const systemTypes = [
                    { id: "character", name: "Character", value: "character", is_system: true },
                    { id: "location", name: "Location", value: "location", is_system: true },
                    { id: "item", name: "Item", value: "item", is_system: true },
                    { id: "theme", name: "Theme", value: "theme", is_system: true },
                    { id: "plot_point", name: "Plot Point", value: "plot_point", is_system: true },
                ];
                const customTypes = (data.collection_types?.custom || []).map((type: any) => ({
                    id: type.id,
                    name: type.name,
                    value: type.name.toLowerCase().replace(/\s+/g, '_'),
                    is_system: false,
                }));
                setCollectionTypes([...systemTypes, ...customTypes]);
            }
        } catch (error) {
            console.error("Error loading collection types:", error);
        }
    };

    const calculateEstimatedTime = () => {
        const chaptersToProcess = useAllChapters ? chapters.length : selectedChapters.length;
        
        let baseTime = 0;
        
        // Record Keeper time (if enabled)
        if (enableRecordKeeper) {
            baseTime += chaptersToProcess * 45; // 45 seconds per chapter for Record Keeper
        }
        
        // Add time for entity summaries if category is selected
        if (selectedCategory && selectedCategory !== "none" && selectedCategory !== "all_categories") {
            if (analysisMode === "all") {
                const entityCount = entities.filter(e => {
                    const entityType = e.type?.toLowerCase() || "";
                    return entityType === selectedCategory.toLowerCase();
                }).length;
                baseTime += entityCount * chaptersToProcess * 30; // 30 seconds per entity per chapter
            } else {
                // Focused mode
                baseTime += selectedEntities.length * chaptersToProcess * 30;
            }
        } else if (selectedCategory === "all_categories") {
            // All categories mode - process all categories sequentially
            const categories = collectionTypes.filter(ct => ct.value !== "record_keeper");
            let totalEntityTime = 0;
            categories.forEach(category => {
                const entityCount = entities.filter(e => {
                    const entityType = e.type?.toLowerCase() || "";
                    return entityType === category.value.toLowerCase();
                }).length;
                totalEntityTime += entityCount * chaptersToProcess * 30;
            });
            baseTime += totalEntityTime;
        }

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
        // Must have at least Record Keeper or a category selected
        if (!enableRecordKeeper && (selectedCategory === "none" || !selectedCategory)) {
            alert("Please enable Record Keeper or select a category");
            return;
        }
        if (selectedCategory && selectedCategory !== "none" && selectedCategory !== "all_categories" && analysisMode === "focused" && selectedEntities.length === 0) {
            alert("Please select at least one entity for focused mode");
            return;
        }
        setShowConfirmDialog(true);
    };

    const handleConfirm = async () => {
        setShowConfirmDialog(false);
        setLoading(true);
        
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/summarize`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                    body: JSON.stringify({
                        enable_record_keeper: enableRecordKeeper,
                        category: selectedCategory && selectedCategory !== "none" ? selectedCategory : null,
                        mode: selectedCategory && selectedCategory !== "none" && selectedCategory !== "all_categories" ? analysisMode : "all",
                        entity_ids: selectedCategory && selectedCategory !== "none" && selectedCategory !== "all_categories" && analysisMode === "focused" ? selectedEntities : null,
                        chapter_orders: useAllChapters ? null : selectedChapters,
                        model: selectedModel,
                        provider: "gemini",
                    }),
                }
            );

            if (response.ok) {
                const data = await response.json();
                const rkCreated = data.results?.record_keeper_entries_created || 0;
                const rkUpdated = data.results?.record_keeper_entries_updated || 0;
                const entitiesProcessed = data.results?.entities_processed || 0;
                const entitiesUpdated = data.results?.entities_updated || 0;
                const errors = data.results?.errors || [];
                
                // Build appropriate message based on what was done
                let message = "Summarization complete!\n\n";
                
                // Show Record Keeper results if record keeper was enabled
                if (enableRecordKeeper && (rkCreated > 0 || rkUpdated > 0 || !selectedCategory || selectedCategory === "none")) {
                    message += `📋 Record Keeper:\nCreated: ${rkCreated} entries | Updated: ${rkUpdated} entries\n\n`;
                }
                
                // Show entity summary results if a category was selected
                if (selectedCategory && selectedCategory !== "none") {
                    message += `🔍 Entity Summaries:\nProcessed: ${entitiesProcessed} entities | Updated: ${entitiesUpdated} entities`;
                }
                
                if (errors.length > 0) {
                    message += `\n\n❌ Errors (${errors.length}):\n${errors.slice(0, 5).join('\n')}`;
                    if (errors.length > 5) {
                        message += `\n... and ${errors.length - 5} more errors`;
                    }
                }
                
                const totalWork = rkCreated + rkUpdated + entitiesUpdated;
                if (totalWork === 0) {
                    message += `\n\n⚠️ No entries were created. This might mean:\n- Chapters don't have content yet\n- Chapter content is too short (< 100 characters)\n- Check Python logs for details`;
                }
                
                alert(message);
                
                // Reload entities to show updated summaries
                if (totalWork > 0) {
                    // TODO: Trigger entity reload in parent component
                }
            } else {
                const error = await response.json();
                let errorMessage = `Failed to start summarization: ${error.error || "Unknown error"}`;
                if (error.details) {
                    errorMessage += `\n\nDetails: ${JSON.stringify(error.details, null, 2)}`;
                }
                alert(errorMessage);
            }
        } catch (error: any) {
            console.error("Error starting summarization:", error);
            alert(`Failed to start summarization: ${error?.message || String(error)}`);
        } finally {
            setLoading(false);
        }
    };

    const getFilteredEntities = () => {
        if (!selectedCategory || selectedCategory === "none") return [];
        
        return entities.filter(e => {
            const entityType = e.type?.toLowerCase() || "";
            return entityType === selectedCategory.toLowerCase();
        });
    };

    const getCategoryLabel = () => {
        if (!selectedCategory || selectedCategory === "none") return "";
        const category = collectionTypes.find(ct => ct.value === selectedCategory);
        return category ? category.name : selectedCategory.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    };

    return (
        <div className="space-y-6">
            {/* Record Keeper Toggle */}
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-blue-900">Record Keeper Summary</h3>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <HelpCircle className="h-4 w-4 text-blue-600 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs">
                            <p>
                                    <strong>Record Keeper:</strong> Analyzes your manuscript and creates 
                                Record Keeper entries for each chapter. Each entry includes a comprehensive 
                                summary, character activity, key events, themes, and locations mentioned. 
                            </p>
                        </TooltipContent>
                    </Tooltip>
                    </div>
                    <div className="flex items-center space-x-2">
                        <Checkbox
                            id="enable-record-keeper"
                            checked={enableRecordKeeper}
                            onCheckedChange={(checked) => setEnableRecordKeeper(checked as boolean)}
                        />
                        <Label htmlFor="enable-record-keeper" className="text-sm cursor-pointer">
                            Enable
                        </Label>
                    </div>
                </div>
                <p className="text-xs text-blue-700">
                    Creates chapter-by-chapter summaries stored as Record Keeper entities. 
                    You can enable/disable this independently of category summaries.
                </p>
            </div>

            {/* Category Selection */}
            <div>
                <div className="flex items-center gap-2 mb-2">
                    <Label htmlFor="category-select" className="text-sm font-medium">
                        Category Summaries:
                    </Label>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs">
                            <p>
                                Generate chapter-by-chapter activity summaries for entities. 
                                This creates/updates entity properties with <code>_summaries</code> array 
                                that appears in the Summary tab when you open an entity. Works with 
                                both system categories (Character, Location, etc.) and custom categories 
                                (like Faction) you create.
                            </p>
                        </TooltipContent>
                    </Tooltip>
                </div>
                <Select value={selectedCategory || "none"} onValueChange={(value) => {
                    setSelectedCategory(value === "none" ? "" : value);
                    if (value === "all_categories") {
                        setAnalysisMode("all"); // All categories mode uses "all" mode
                    }
                }}>
                    <SelectTrigger id="category-select">
                        <SelectValue placeholder="Select a category (optional)" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="none">None (Record Keeper only)</SelectItem>
                        <SelectItem value="all_categories">All Categories</SelectItem>
                        {collectionTypes.map((type) => (
                            <SelectItem key={type.id} value={type.value}>
                                {type.name}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                <p className="text-xs text-gray-500 mt-1">
                    Select a category to generate entity summaries, or "All Categories" to process 
                    all categories sequentially. Leave as "None" to only run Record Keeper (if enabled).
                </p>
            </div>

            {/* Analysis Mode Selection (only show if single category is selected, not "all_categories") */}
            {selectedCategory && selectedCategory !== "none" && selectedCategory !== "all_categories" && (
                <div>
                    <div className="flex items-center gap-2 mb-2">
                        <Label className="text-sm font-medium">
                            Analysis Mode:
                        </Label>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs">
                                <p>
                                    <strong>All:</strong> Process all {getCategoryLabel().toLowerCase()} entities across selected chapters.
                                    <br /><br />
                                    <strong>Focused:</strong> Select specific {getCategoryLabel().toLowerCase()} entities to analyze in detail.
                                </p>
                            </TooltipContent>
                        </Tooltip>
                    </div>
                    <RadioGroup value={analysisMode} onValueChange={(value) => setAnalysisMode(value as "all" | "focused")}>
                        <div className="flex items-center space-x-2">
                            <RadioGroupItem value="all" id="mode-all" />
                            <Label htmlFor="mode-all" className="cursor-pointer">
                                All {getCategoryLabel()}s
                            </Label>
                        </div>
                        <div className="flex items-center space-x-2">
                            <RadioGroupItem value="focused" id="mode-focused" />
                            <Label htmlFor="mode-focused" className="cursor-pointer">
                                Focused (Select Specific)
                            </Label>
                        </div>
                    </RadioGroup>
                </div>
            )}

            {/* Entity Selection (for focused mode) */}
            {selectedCategory && analysisMode === "focused" && (
                <div>
                    <div className="flex items-center gap-2 mb-2">
                        <Label className="text-sm font-medium">
                            Select {getCategoryLabel()}s:
                        </Label>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs">
                                <p>
                                    Choose which {getCategoryLabel().toLowerCase()} entities to analyze. 
                                    Only entities of the selected category are shown.
                                </p>
                            </TooltipContent>
                        </Tooltip>
                    </div>
                    <div className="max-h-40 overflow-y-auto border rounded p-2 space-y-2">
                        {getFilteredEntities().length === 0 ? (
                            <p className="text-sm text-gray-500 italic">
                                No {getCategoryLabel().toLowerCase()} entities found.
                            </p>
                        ) : (
                            getFilteredEntities().map((entity) => (
                                <div key={entity.vertex_id} className="flex items-center space-x-2">
                                    <Checkbox
                                        id={`entity-${entity.vertex_id}`}
                                        checked={selectedEntities.includes(entity.vertex_id)}
                                        onCheckedChange={(checked) => {
                                            if (checked) {
                                                setSelectedEntities([...selectedEntities, entity.vertex_id]);
                                            } else {
                                                setSelectedEntities(selectedEntities.filter(id => id !== entity.vertex_id));
                                            }
                                        }}
                                    />
                                    <Label 
                                        htmlFor={`entity-${entity.vertex_id}`}
                                        className="text-sm cursor-pointer"
                                    >
                                        {entity.name}
                                    </Label>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}

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
                                Select which chapters to analyze. Processing happens sequentially, 
                                one chapter at a time, to handle large manuscripts efficiently.
                            </p>
                        </TooltipContent>
                    </Tooltip>
                </div>
                <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                        <Checkbox
                            id="all-chapters"
                            checked={useAllChapters}
                            onCheckedChange={(checked) => {
                                setUseAllChapters(checked as boolean);
                                if (checked) {
                                    setSelectedChapters([]);
                                }
                            }}
                        />
                        <Label htmlFor="all-chapters" className="text-sm cursor-pointer">
                            All Chapters ({chapters.length} chapters)
                        </Label>
                    </div>
                    {!useAllChapters && (
                        <div className="max-h-40 overflow-y-auto border rounded p-2 space-y-2">
                            {chapters.length === 0 ? (
                                <p className="text-sm text-gray-500 italic">No chapters found.</p>
                            ) : (
                                chapters.map((chapter) => (
                                    <div key={chapter.order} className="flex items-center space-x-2">
                                        <Checkbox
                                            id={`chapter-${chapter.order}`}
                                            checked={selectedChapters.includes(chapter.order)}
                                            onCheckedChange={(checked) => {
                                                if (checked) {
                                                    setSelectedChapters([...selectedChapters, chapter.order]);
                                                } else {
                                                    setSelectedChapters(selectedChapters.filter(o => o !== chapter.order));
                                                }
                                            }}
                                        />
                                        <Label 
                                            htmlFor={`chapter-${chapter.order}`}
                                            className="text-sm cursor-pointer"
                                        >
                                            Chapter {chapter.order + 1}: {chapter.chapter_name}
                                        </Label>
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Estimated Time */}
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-blue-600" />
                    <p className="text-sm text-blue-800">
                        <strong>Estimated Time:</strong> {estimatedTime || "Calculating..."}
                    </p>
                </div>
                <p className="text-xs text-blue-600 mt-1">
                    Processing happens sequentially to ensure accuracy. 
                    {enableRecordKeeper && " Record Keeper entries will be created for all selected chapters. "}
                    {selectedCategory && selectedCategory !== "none" && selectedCategory !== "all_categories" && `Entity summaries will be generated for ${getCategoryLabel()}. `}
                    {selectedCategory === "all_categories" && "All categories will be processed sequentially. "}
                    You can navigate away and will be notified when complete.
                </p>
            </div>

            {/* Start Button */}
            <Button 
                onClick={handleStart} 
                disabled={loading || (!enableRecordKeeper && (selectedCategory === "none" || !selectedCategory)) || (selectedCategory && selectedCategory !== "none" && selectedCategory !== "all_categories" && analysisMode === "focused" && selectedEntities.length === 0)}
                className="w-full"
            >
                <Play className="h-4 w-4 mr-2" />
                {loading ? "Starting..." : "Start Summarization"}
            </Button>
            <p className="text-xs text-gray-500 text-center">
                {enableRecordKeeper && "Will create Record Keeper entries for all selected chapters. "}
                {selectedCategory && selectedCategory !== "none" && selectedCategory !== "all_categories" && `Will generate summaries for ${getCategoryLabel()}. `}
                {selectedCategory === "all_categories" && "Will process all categories sequentially. "}
                {!enableRecordKeeper && !selectedCategory && "Please enable at least one option."}
            </p>

            {/* Confirmation Dialog */}
            <Dialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Confirm Summarization</DialogTitle>
                        <DialogDescription>
                            A terminal window will appear showing progress. You can navigate away 
                            and will be notified when the analysis is complete.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-2 py-4">
                        {enableRecordKeeper && (
                        <div className="text-sm">
                            <strong>Record Keeper:</strong> Will create entries for all selected chapters
                        </div>
                        )}
                        {selectedCategory && selectedCategory !== "none" && (
                            <>
                                <div className="text-sm">
                                    <strong>Category:</strong> {selectedCategory === "all_categories" ? "All Categories" : getCategoryLabel()}
                                </div>
                                {selectedCategory !== "all_categories" && (
                                <div className="text-sm">
                                    <strong>Mode:</strong> {analysisMode === "all" ? `All ${getCategoryLabel()}s` : `Focused (${selectedEntities.length} selected)`}
                                </div>
                                )}
                            </>
                        )}
                        <div className="text-sm">
                            <strong>Chapters:</strong> {useAllChapters ? `All (${chapters.length})` : `${selectedChapters.length} selected`}
                        </div>
                        <div className="text-sm">
                            <strong>Model:</strong> {selectedModel}
                        </div>
                        <div className="text-sm">
                            <strong>Estimated Time:</strong> {estimatedTime || "Calculating..."}
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowConfirmDialog(false)}>
                            Cancel
                        </Button>
                        <Button onClick={handleConfirm}>
                            Confirm & Start
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

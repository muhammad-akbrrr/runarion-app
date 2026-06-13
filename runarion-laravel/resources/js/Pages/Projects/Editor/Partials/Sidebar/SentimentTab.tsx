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
import {
    Collapsible,
    CollapsibleContent,
    CollapsibleTrigger,
} from "@/Components/ui/collapsible";
import { Checkbox } from "@/Components/ui/checkbox";
import { Badge } from "@/Components/ui/badge";
import { ScrollArea } from "@/Components/ui/scroll-area";
import { http } from "@/Lib/http";
import { toast } from "sonner";
import { useConfirm } from "@/Components/ConfirmDialogProvider";
import {
    HelpCircle,
    Play,
    Heart,
    ChevronDown,
    ChevronRight,
    RefreshCw,
    AlertTriangle,
    ArrowRight,
    Quote,
    Loader2,
    Trash2,
} from "lucide-react";

interface SentimentTabProps {
    workspaceId: string;
    projectId: string;
    selectedModel: string;
}

interface Chapter {
    order: number;
    chapter_name: string;
    content: string;
}

interface Character {
    vertex_id: string;
    name: string;
    type: string;
    properties: Record<string, any>;
}

// New: Individual interaction record
interface Interaction {
    vertex_id?: string | null;
    source_character: string;
    target_character: string;
    chapter_number: number;
    chapter_name: string;
    interaction_type: string;
    emotional_tone: string;
    sentiment_modifier: number;
    sentiment_reasons: string[];
    context: string;
    text_evidence: string;
}

// New: Chapter processing result
interface ChapterResult {
    chapter: string;
    chapter_number: number;
    status: "success" | "error" | "skipped";
    interactions_found?: number;
    interactions_stored?: number;
    error?: string;
    reason?: string;
}

// Text evidence for aggregated relationships
interface TextEvidence {
    quote: string;
    chapter?: string;
    chapter_number?: number;
    location?: string;
    interaction_type?: string;
    sentiment_modifier?: number;
}

// Aggregated relationship (built from interactions)
interface AggregatedRelationship {
    source: string;
    target: string;
    relationship_type: string;
    emotional_tone: string;
    sentiment_score: number;
    interaction_count: number;
    context: string;
    text_evidence: TextEvidence[];
    tone_breakdown?: Record<string, number>;
    type_breakdown?: Record<string, number>;
    chapter_range?: {
        first: number;
        last: number;
    };
    chapter_analyses?: Array<{
        chapter_number: number;
        chapter_name?: string;
        sentiment_score?: number;
        emotional_tone?: string;
        context?: string;
    }>;
}

interface RelationshipChange {
    source: string;
    target: string;
    relationship_type: string;
    old_emotional_tone?: string;
    new_emotional_tone?: string;
    old_sentiment_score?: number;
    new_sentiment_score?: number;
    new_context?: string;
    edge_id?: string;
    note?: string;
}

export default function SentimentTab({
    workspaceId,
    projectId,
    selectedModel,
}: SentimentTabProps) {
    const confirm = useConfirm();
    const [selectedCharacters, setSelectedCharacters] = useState<string[]>([]);
    const [, setUseAllCharacters] = useState<boolean>(true);
    const [focusMode, setFocusMode] = useState<"all" | "selected" | "1-to-1">(
        "all"
    );
    const [selectedChapters, setSelectedChapters] = useState<number[]>([]);
    const [useAllChapters, setUseAllChapters] = useState<boolean>(true);
    const [chapters, setChapters] = useState<Chapter[]>([]);
    const [characters, setCharacters] = useState<Character[]>([]);
    const [loadingCharacters, setLoadingCharacters] = useState(false);
    const [loading, setLoading] = useState(false);
    const [scanningChanges] = useState(false);
    const [deletingInteractions, setDeletingInteractions] = useState(false);
    const [showConfirmDialog, setShowConfirmDialog] = useState(false);
    const [characterSearch, setCharacterSearch] = useState("");

    // Results state - NEW: separate interactions and relationships
    const [interactions, setInteractions] = useState<Interaction[]>([]);
    const [, setChapterResults] = useState<ChapterResult[]>([]);
    const [aggregatedRelationships, setAggregatedRelationships] = useState<
        AggregatedRelationship[]
    >([]);
    const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
    const [isV2Results, setIsV2Results] = useState(false); // Track if current results are V2 (chapter-based)

    // Change scanner state
    const [changes] = useState<{
        new_relationships: AggregatedRelationship[];
        modified_relationships: RelationshipChange[];
        potentially_removed: RelationshipChange[];
        unchanged: {
            source: string;
            target: string;
            relationship_type: string;
        }[];
    } | null>(null);
    const [changeSummary] = useState<{
        new_count: number;
        modified_count: number;
        removed_count: number;
        unchanged_count: number;
    } | null>(null);

    // Load chapters and characters on mount
    useEffect(() => {
        console.log("[SentimentTab] Component mounted, loading data...", {
            workspaceId,
            projectId,
        });
        loadChapters();
        loadCharacters();
    }, [workspaceId, projectId]);

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

    const loadCharacters = async () => {
        setLoadingCharacters(true);
        try {
            const url =
                route("records.entities", {
                    workspace_id: workspaceId,
                    project_id: projectId,
                }) + "?category=character";
            console.log("[SentimentTab] Loading characters from:", url);

            const response = await http(url, {
                headers: {
                    Accept: "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            console.log("[SentimentTab] Response status:", response.status);

            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                console.log("[SentimentTab] Loaded characters:", data);
                setCharacters(data.entities || []);
            } else {
                console.error(
                    "[SentimentTab] Failed to load characters:",
                    response.status,
                    (typeof response.data === "string" ? response.data : JSON.stringify(response.data ?? ""))
                );
            }
        } catch (error) {
            console.error("[SentimentTab] Error loading characters:", error);
        } finally {
            setLoadingCharacters(false);
        }
    };

    const handleStart = () => {
        if (chapters.length === 0) {
            toast.warning("No chapters found. Please write some content first.");
            return;
        }
        setShowConfirmDialog(true);
    };

    const handleConfirm = async () => {
        setShowConfirmDialog(false);
        setLoading(true);
        setInteractions([]);
        setChapterResults([]);
        setAggregatedRelationships([]);

        try {
            const response = await http(
                route("auditor.extract-relationships", {
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
                        character_ids:
                            focusMode === "all" ? null : selectedCharacters,
                        chapter_orders: useAllChapters
                            ? null
                            : selectedChapters,
                        model: selectedModel,
                        provider: "gemini",
                        focus_mode: focusMode, // Send focus mode to backend
                    },
                }
            );

            if (response.status >= 200 && response.status < 300) {
                const data = response.data;

                // Check if this is V2 response (chapter-based analysis)
                const isV2 =
                    data.relationships?.[0]?.chapter_analyses !== undefined ||
                    data.relationships?.[0]?.overall !== undefined;

                if (isV2) {
                    // V2: Chapter-based analysis - relationships contain chapter_analyses
                    // Transform V2 data for compatibility with existing state
                    const v2Relationships = data.relationships || [];

                    // Build aggregated relationships from V2 format
                    const aggregated = v2Relationships.map((rel: any) => ({
                        source: rel.source,
                        target: rel.target,
                        relationship_type:
                            rel.overall?.relationship_type || "UNKNOWN",
                        emotional_tone:
                            rel.overall?.emotional_tone || "neutral",
                        sentiment_score: rel.overall?.overall_sentiment || 0,
                        interaction_count: rel.chapter_analyses?.length || 0,
                        context: rel.overall?.summary || "",
                        text_evidence:
                            rel.chapter_analyses?.map((ch: any) => ({
                                quote: ch.key_moment || ch.summary,
                                chapter: ch.chapter_name,
                                chapter_number: ch.chapter_number,
                                sentiment_modifier: ch.sentiment_score,
                            })) || [],
                        chapter_analyses: rel.chapter_analyses, // Keep V2 data
                    }));

                    setAggregatedRelationships(aggregated);
                    setInteractions([]); // V2 doesn't use individual interactions
                    setChapterResults([]); // V2 doesn't use chapter_results
                    setIsV2Results(true); // Mark as V2 results

                    // Dispatch event to refresh relationships in Records Panel
                    if (v2Relationships.length > 0) {
                        window.dispatchEvent(
                            new CustomEvent("relationships-extracted", {
                                detail: { count: v2Relationships.length },
                            })
                        );
                    }

                    // V2 success check
                    if (v2Relationships.length === 0) {
                        toast.info(
                            "No relationships could be analyzed. Make sure your characters appear together in the selected chapters."
                        );
                    }
                } else {
                    // V1: Interaction-based (legacy)
                    setInteractions(data.interactions || []);
                    setChapterResults(data.chapter_results || []);
                    setAggregatedRelationships(data.relationships || []);
                    setIsV2Results(false); // Mark as V1 results

                    // Dispatch event to refresh relationships in Records Panel
                    const totalStored =
                        data.chapter_results?.reduce(
                            (sum: number, ch: ChapterResult) =>
                                sum + (ch.interactions_stored || 0),
                            0
                        ) || 0;

                    if (totalStored > 0) {
                        window.dispatchEvent(
                            new CustomEvent("relationships-extracted", {
                                detail: { count: totalStored },
                            })
                        );
                    }

                    if ((data.interactions?.length || 0) === 0) {
                        toast.info(
                            "No interactions were detected in the selected chapters. Try selecting more chapters or check if your manuscript contains character interactions."
                        );
                    }
                }
            } else {
                const error = response.data;
                toast.error(
                    `Failed to extract relationships: ${
                        error.error || "Unknown error"
                    }`
                );
            }
        } catch (error: any) {
            console.error("Error extracting relationships:", error);
            toast.error(
                `Failed to extract relationships: ${
                    error?.message || String(error)
                }`
            );
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteAllInteractions = async () => {
        if (
            !(await confirm({
                title: "Delete all interactions?",
                description:
                    "Are you sure you want to delete ALL interactions? This cannot be undone.",
                actionLabel: "Delete interactions",
            }))
        ) {
            return;
        }

        setDeletingInteractions(true);

        try {
            const response = await http(
                route("auditor.delete-all-interactions", {
                    workspace_id: workspaceId,
                    project_id: projectId,
                }),
                {
                    method: "DELETE",
                    headers: {
                        Accept: "application/json",
                    },
                }
            );

            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                if (data.deleted_count === 0) {
                    toast.info(
                        "No interactions to delete. The database is already clean!"
                    );
                } else {
                    toast.success(
                        `Deleted ${data.deleted_count} interactions successfully!`
                    );
                }
                setInteractions([]);
                setAggregatedRelationships([]);
                setChapterResults([]);
            } else {
                const error = response.data;
                toast.error(
                    `Failed to delete interactions: ${
                        error.error || "Unknown error"
                    }`
                );
            }
        } catch (error: any) {
            console.error("Error deleting interactions:", error);
            toast.error(
                `Failed to delete interactions: ${
                    error?.message || String(error)
                }`
            );
        } finally {
            setDeletingInteractions(false);
        }
    };

    // Filter characters for search in 1-to-1 mode
    const filteredCharacters = characters.filter((char) =>
        char.name.toLowerCase().includes(characterSearch.toLowerCase())
    );

    const toggleExpanded = (key: string) => {
        const newExpanded = new Set(expandedItems);
        if (newExpanded.has(key)) {
            newExpanded.delete(key);
        } else {
            newExpanded.add(key);
        }
        setExpandedItems(newExpanded);
    };

    const getSentimentColor = (score: number): string => {
        if (score < -50) return "text-red-600 bg-red-50";
        if (score < -20) return "text-orange-600 bg-orange-50";
        if (score < 20) return "text-gray-600 bg-gray-50";
        if (score < 50) return "text-blue-600 bg-blue-50";
        return "text-green-600 bg-green-50";
    };

    const getRelationshipKey = (rel: AggregatedRelationship): string => {
        return `${rel.source}|${rel.target}|${rel.relationship_type}`;
    };

    return (
        <div className="space-y-4">
            {/* Description */}
            <div className="p-3 bg-rose-50 rounded-lg border border-rose-200">
                <div className="flex items-center gap-2 mb-2">
                    <h3 className="text-sm font-semibold text-rose-900">
                        Sentiment Analyzer
                    </h3>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <HelpCircle className="h-4 w-4 text-rose-600 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs">
                            <p>
                                Analyzes character relationships
                                chapter-by-chapter, creating individual
                                interaction records that build up into
                                aggregated relationship scores with full
                                evidence trails.
                            </p>
                        </TooltipContent>
                    </Tooltip>
                </div>
                <p className="text-xs text-rose-700">
                    Extract interaction records per chapter → Build
                    relationships from evidence. Track how relationships evolve
                    over time.
                </p>
            </div>

            {/* Character Selection with Focus Mode */}
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
                                <strong>All:</strong> Extract all character
                                relationships.
                                <br />
                                <strong>Selected:</strong> Focus on specific
                                characters.
                                <br />
                                <strong>1-to-1:</strong> Deep-dive into one
                                specific relationship between two characters.
                            </p>
                        </TooltipContent>
                    </Tooltip>
                </div>

                {/* Mode Selection */}
                <div className="flex gap-1 mb-2">
                    <Button
                        variant={focusMode === "all" ? "default" : "outline"}
                        size="sm"
                        className="flex-1 text-xs h-8"
                        onClick={() => {
                            setFocusMode("all");
                            setUseAllCharacters(true);
                            setSelectedCharacters([]);
                        }}
                    >
                        All
                    </Button>
                    <Button
                        variant={
                            focusMode === "selected" ? "default" : "outline"
                        }
                        size="sm"
                        className="flex-1 text-xs h-8"
                        onClick={() => {
                            setFocusMode("selected");
                            setUseAllCharacters(false);
                        }}
                    >
                        Selected
                    </Button>
                    <Button
                        variant={focusMode === "1-to-1" ? "default" : "outline"}
                        size="sm"
                        className="flex-1 text-xs h-8"
                        onClick={() => {
                            setFocusMode("1-to-1");
                            setUseAllCharacters(false);
                            setSelectedCharacters([]);
                        }}
                    >
                        1-to-1
                    </Button>
                </div>

                {/* Character Selection based on mode */}
                {focusMode === "all" && (
                    <div className="p-2 bg-gray-50 rounded text-sm text-gray-600">
                        Analyzing all {characters.length} characters
                    </div>
                )}

                {focusMode === "selected" && (
                    <div className="max-h-32 overflow-y-auto border rounded p-2 space-y-2">
                        {loadingCharacters ? (
                            <p className="text-sm text-gray-500 italic">
                                Loading characters...
                            </p>
                        ) : characters.length === 0 ? (
                            <p className="text-sm text-gray-500 italic">
                                No characters found. Run Entity Extractor first.
                            </p>
                        ) : (
                            characters.map((char) => (
                                <div
                                    key={char.vertex_id}
                                    className="flex items-center space-x-2"
                                >
                                    <Checkbox
                                        id={`char-${char.vertex_id}`}
                                        checked={selectedCharacters.includes(
                                            char.vertex_id
                                        )}
                                        onCheckedChange={(checked) => {
                                            if (checked) {
                                                setSelectedCharacters([
                                                    ...selectedCharacters,
                                                    char.vertex_id,
                                                ]);
                                            } else {
                                                setSelectedCharacters(
                                                    selectedCharacters.filter(
                                                        (id) =>
                                                            id !==
                                                            char.vertex_id
                                                    )
                                                );
                                            }
                                        }}
                                    />
                                    <Label
                                        htmlFor={`char-${char.vertex_id}`}
                                        className="text-sm cursor-pointer"
                                    >
                                        {char.name}
                                    </Label>
                                </div>
                            ))
                        )}
                    </div>
                )}

                {focusMode === "1-to-1" && (
                    <div className="space-y-2">
                        <p className="text-xs text-gray-500">
                            Select exactly 2 characters for focused analysis:
                        </p>
                        {loadingCharacters && (
                            <p className="text-xs text-blue-500 italic">
                                Loading characters...
                            </p>
                        )}
                        {!loadingCharacters && characters.length === 0 && (
                            <p className="text-xs text-amber-600 italic">
                                No characters found. Run Entity Extractor first.
                            </p>
                        )}
                        {characters.length > 10 && (
                            <input
                                type="text"
                                placeholder="Search characters..."
                                value={characterSearch}
                                onChange={(e) =>
                                    setCharacterSearch(e.target.value)
                                }
                                className="w-full px-2 py-1 text-xs border rounded"
                            />
                        )}
                        <div className="grid grid-cols-2 gap-2">
                            <Select
                                value={selectedCharacters[0] || ""}
                                onValueChange={(value) => {
                                    const newSelected = [...selectedCharacters];
                                    newSelected[0] = value;
                                    setSelectedCharacters(
                                        newSelected.filter(Boolean)
                                    );
                                }}
                            >
                                <SelectTrigger className="h-8 text-xs w-full">
                                    <SelectValue placeholder="Character 1" />
                                </SelectTrigger>
                                <SelectContent className="max-h-60">
                                    {filteredCharacters.map((char) => (
                                        <SelectItem
                                            key={char.vertex_id}
                                            value={char.vertex_id}
                                            disabled={
                                                char.vertex_id ===
                                                selectedCharacters[1]
                                            }
                                        >
                                            {char.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <Select
                                value={selectedCharacters[1] || ""}
                                onValueChange={(value) => {
                                    const newSelected = [...selectedCharacters];
                                    newSelected[1] = value;
                                    setSelectedCharacters(
                                        newSelected.filter(Boolean)
                                    );
                                }}
                            >
                                <SelectTrigger className="h-8 text-xs w-full">
                                    <SelectValue placeholder="Character 2" />
                                </SelectTrigger>
                                <SelectContent className="max-h-60">
                                    {filteredCharacters.map((char) => (
                                        <SelectItem
                                            key={char.vertex_id}
                                            value={char.vertex_id}
                                            disabled={
                                                char.vertex_id ===
                                                selectedCharacters[0]
                                            }
                                        >
                                            {char.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        {selectedCharacters.length === 2 && (
                            <div className="p-2 bg-rose-50 rounded text-xs text-rose-700 flex items-center gap-2">
                                Analyzing:{" "}
                                {
                                    characters.find(
                                        (c) =>
                                            c.vertex_id ===
                                            selectedCharacters[0]
                                    )?.name
                                }{" "}
                                ↔{" "}
                                {
                                    characters.find(
                                        (c) =>
                                            c.vertex_id ===
                                            selectedCharacters[1]
                                    )?.name
                                }
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Chapter Selection */}
            <div>
                <div className="flex items-center gap-2 mb-2">
                    <Label className="text-sm font-medium">Chapters:</Label>
                </div>
                <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                        <Checkbox
                            id="all-chapters-sentiment"
                            checked={useAllChapters}
                            onCheckedChange={(checked) => {
                                setUseAllChapters(checked as boolean);
                                if (checked) {
                                    setSelectedChapters([]);
                                }
                            }}
                        />
                        <Label
                            htmlFor="all-chapters-sentiment"
                            className="text-sm cursor-pointer"
                        >
                            All Chapters ({chapters.length} chapters)
                        </Label>
                    </div>
                    {!useAllChapters && (
                        <div className="max-h-32 overflow-y-auto border rounded p-2 space-y-2">
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
                                            id={`chapter-sentiment-${chapter.order}`}
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
                                            htmlFor={`chapter-sentiment-${chapter.order}`}
                                            className="text-sm cursor-pointer"
                                        >
                                            {chapter.chapter_name ||
                                                `Chapter ${chapter.order + 1}`}
                                        </Label>
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2">
                <Button
                    onClick={handleStart}
                    disabled={loading || scanningChanges}
                    className="flex-1"
                >
                    {loading ? (
                        <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Analyzing...
                        </>
                    ) : (
                        <>
                            <Play className="h-4 w-4 mr-2" />
                            Extract Interactions
                        </>
                    )}
                </Button>
                <Tooltip>
                    <TooltipTrigger asChild>
                        <Button
                            variant="outline"
                            onClick={handleStart}
                            disabled={loading || scanningChanges}
                            title="Reassess Relationships"
                        >
                            {loading ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <RefreshCw className="h-4 w-4" />
                            )}
                        </Button>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                        <p className="font-semibold">Reassess Relationships</p>
                        <p className="text-xs text-gray-400 mt-1">
                            Re-run the analysis for the selected mode. Use this
                            when:
                        </p>
                        <ul className="text-xs text-gray-400 mt-1 list-disc list-inside">
                            <li>You've added new chapters</li>
                            <li>You've edited existing chapters</li>
                            <li>You want to refresh the analysis</li>
                        </ul>
                        <p className="text-xs text-gray-500 mt-1 italic">
                            Will re-analyze all chapters and update stored data.
                        </p>
                    </TooltipContent>
                </Tooltip>
                {/* Only show delete button when there are V1 interactions to delete */}
                {interactions.length > 0 && (
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button
                                variant="outline"
                                onClick={handleDeleteAllInteractions}
                                disabled={
                                    loading ||
                                    scanningChanges ||
                                    deletingInteractions
                                }
                                className="text-red-500 hover:text-red-700 hover:bg-red-50"
                            >
                                {deletingInteractions ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    <Trash2 className="h-4 w-4" />
                                )}
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs">
                            <p className="font-semibold text-red-600">
                                Clear All Interactions
                            </p>
                            <p className="text-xs text-gray-400">
                                Delete all stored interaction records from the
                                database (reset before re-extraction)
                            </p>
                        </TooltipContent>
                    </Tooltip>
                )}
            </div>

            {/* Results Section */}
            {(interactions.length > 0 ||
                aggregatedRelationships.length > 0) && (
                <div className="border rounded-lg overflow-hidden w-full">
                    {/* Summary Header */}
                    <div className="p-3 bg-linear-to-r from-rose-50 to-pink-50 border-b">
                        <div className="flex items-center justify-between mb-2 gap-2">
                            <h4 className="text-sm font-semibold text-rose-900 shrink-0">
                                Analysis Results
                            </h4>
                            <div className="flex gap-2 text-xs flex-wrap justify-end">
                                {/* Only show interactions count for V1 */}
                                <Badge
                                    variant="secondary"
                                    className="bg-purple-100 text-purple-700"
                                >
                                    {aggregatedRelationships.length}{" "}
                                    relationships
                                </Badge>
                                {/* Show chapter count for V2 */}
                                {aggregatedRelationships[0]
                                    ?.chapter_analyses && (
                                    <Badge
                                        variant="secondary"
                                        className="bg-indigo-100 text-indigo-700"
                                    >
                                        {
                                            aggregatedRelationships[0]
                                                .chapter_analyses.length
                                        }{" "}
                                        chapters
                                    </Badge>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* TODO: FIX THE BOTCHED UI */}

                    {/* View Mode Tabs - For V2, only show Relationships tab */}
                    <ScrollArea className="h-[350px] w-full">
                        <div className="p-2 space-y-2 w-full max-w-full">
                            {aggregatedRelationships.map((rel) => {
                                const key = getRelationshipKey(rel);
                                const isExpanded = expandedItems.has(key);

                                return (
                                    <Collapsible
                                        key={key}
                                        open={isExpanded}
                                        onOpenChange={() => toggleExpanded(key)}
                                        className="w-full"
                                    >
                                        <div className="border rounded-lg w-full overflow-hidden">
                                            <CollapsibleTrigger className="w-full">
                                                <div className="p-3 hover:bg-gray-50 cursor-pointer">
                                                    {/* Responsive header - stacks on small screens */}
                                                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                                                        <div className="flex items-center gap-1.5 min-w-0">
                                                            {isExpanded ? (
                                                                <ChevronDown className="h-4 w-4 text-gray-400 shrink-0" />
                                                            ) : (
                                                                <ChevronRight className="h-4 w-4 text-gray-400 shrink-0" />
                                                            )}
                                                            <span className="font-medium text-sm">
                                                                {rel.source}
                                                            </span>
                                                            <ArrowRight className="h-3 w-3 text-gray-400 shrink-0" />
                                                            <span className="font-medium text-sm">
                                                                {rel.target}
                                                            </span>
                                                        </div>
                                                        <div className="flex items-center gap-1.5 ml-auto">
                                                            <Badge
                                                                variant="outline"
                                                                className="text-xs whitespace-nowrap"
                                                            >
                                                                {isV2Results
                                                                    ? `${
                                                                          rel
                                                                              .chapter_analyses
                                                                              ?.length ||
                                                                          rel.interaction_count
                                                                      } ch`
                                                                    : `${rel.interaction_count} int`}
                                                            </Badge>
                                                            <div
                                                                className={`px-1.5 py-0.5 rounded text-xs font-semibold whitespace-nowrap ${getSentimentColor(
                                                                    rel.sentiment_score
                                                                )}`}
                                                            >
                                                                {rel.sentiment_score >
                                                                0
                                                                    ? "+"
                                                                    : ""}
                                                                {
                                                                    rel.sentiment_score
                                                                }
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </CollapsibleTrigger>
                                            <CollapsibleContent className="w-full">
                                                <div className="p-3 border-t bg-gray-50/50 space-y-3 w-full overflow-x-hidden">
                                                    {/* Relationship Type & Tone */}
                                                    <div className="flex flex-wrap gap-2 w-full">
                                                        <Badge className="whitespace-normal text-wrap">
                                                            {rel.relationship_type.replace(
                                                                /_/g,
                                                                " "
                                                            )}
                                                        </Badge>
                                                        <Badge
                                                            variant="outline"
                                                            className="capitalize whitespace-normal text-wrap max-w-full"
                                                        >
                                                            {rel.emotional_tone}
                                                        </Badge>
                                                        {rel.chapter_range && (
                                                            <Badge
                                                                variant="secondary"
                                                                className="text-xs"
                                                            >
                                                                Ch
                                                                {rel
                                                                    .chapter_range
                                                                    .first +
                                                                    1}{" "}
                                                                - Ch
                                                                {rel
                                                                    .chapter_range
                                                                    .last + 1}
                                                            </Badge>
                                                        )}
                                                    </div>

                                                    {/* Tone Breakdown */}
                                                    {rel.tone_breakdown &&
                                                        Object.keys(
                                                            rel.tone_breakdown
                                                        ).length > 1 && (
                                                            <div>
                                                                <Label className="text-xs font-semibold text-gray-600">
                                                                    Tone
                                                                    Distribution:
                                                                </Label>
                                                                <div className="flex flex-wrap gap-1 mt-1">
                                                                    {Object.entries(
                                                                        rel.tone_breakdown
                                                                    ).map(
                                                                        ([
                                                                            tone,
                                                                            count,
                                                                        ]) => (
                                                                            <span
                                                                                key={
                                                                                    tone
                                                                                }
                                                                                className="text-xs px-2 py-0.5 bg-gray-100 rounded"
                                                                            >
                                                                                {
                                                                                    tone
                                                                                }

                                                                                :{" "}
                                                                                {
                                                                                    count
                                                                                }
                                                                            </span>
                                                                        )
                                                                    )}
                                                                </div>
                                                            </div>
                                                        )}

                                                    {/* Context */}
                                                    {rel.context && (
                                                        <div className="w-full">
                                                            <Label className="text-xs font-semibold text-gray-600">
                                                                Context:
                                                            </Label>
                                                            <p
                                                                className="text-xs text-gray-700 mt-1 leading-relaxed w-full"
                                                                style={{
                                                                    wordWrap:
                                                                        "break-word",
                                                                    overflowWrap:
                                                                        "break-word",
                                                                    whiteSpace:
                                                                        "pre-wrap",
                                                                }}
                                                            >
                                                                {rel.context}
                                                            </p>
                                                        </div>
                                                    )}

                                                    {/* Evidence Trail */}
                                                    {rel.text_evidence &&
                                                        rel.text_evidence
                                                            .length > 0 && (
                                                            <div className="space-y-2">
                                                                <Label className="text-xs font-semibold text-gray-600">
                                                                    Evidence
                                                                    Trail (
                                                                    {
                                                                        rel
                                                                            .text_evidence
                                                                            .length
                                                                    }
                                                                    ):
                                                                </Label>
                                                                <div className="space-y-2 max-h-40 overflow-y-auto overflow-x-hidden">
                                                                    {rel.text_evidence.map(
                                                                        (
                                                                            evidence,
                                                                            i
                                                                        ) => (
                                                                            <div
                                                                                key={
                                                                                    i
                                                                                }
                                                                                className="bg-white border rounded p-2 overflow-hidden"
                                                                            >
                                                                                <div className="flex items-start gap-2">
                                                                                    <Quote className="h-3 w-3 text-gray-400 mt-0.5 shrink-0" />
                                                                                    <div className="flex-1 min-w-0 overflow-hidden">
                                                                                        <p
                                                                                            className="text-xs italic text-gray-700 wrap-break-word"
                                                                                            style={{
                                                                                                wordBreak:
                                                                                                    "break-word",
                                                                                            }}
                                                                                        >
                                                                                            "
                                                                                            {
                                                                                                evidence.quote
                                                                                            }

                                                                                            "
                                                                                        </p>
                                                                                        <div className="flex items-center gap-2 mt-1">
                                                                                            <span className="text-xs text-gray-500">
                                                                                                {evidence.chapter ||
                                                                                                    evidence.location ||
                                                                                                    `Ch${
                                                                                                        (evidence.chapter_number ||
                                                                                                            0) +
                                                                                                        1
                                                                                                    }`}
                                                                                            </span>
                                                                                            {evidence.interaction_type && (
                                                                                                <Badge
                                                                                                    variant="outline"
                                                                                                    className="text-xs h-4"
                                                                                                >
                                                                                                    {
                                                                                                        evidence.interaction_type
                                                                                                    }
                                                                                                </Badge>
                                                                                            )}
                                                                                            {evidence.sentiment_modifier !==
                                                                                                undefined && (
                                                                                                <span
                                                                                                    className={`text-xs font-medium ${
                                                                                                        evidence.sentiment_modifier >
                                                                                                        0
                                                                                                            ? "text-green-600"
                                                                                                            : evidence.sentiment_modifier <
                                                                                                              0
                                                                                                            ? "text-red-600"
                                                                                                            : "text-gray-600"
                                                                                                    }`}
                                                                                                >
                                                                                                    {evidence.sentiment_modifier >
                                                                                                    0
                                                                                                        ? "+"
                                                                                                        : ""}
                                                                                                    {
                                                                                                        evidence.sentiment_modifier
                                                                                                    }
                                                                                                </span>
                                                                                            )}
                                                                                        </div>
                                                                                    </div>
                                                                                </div>
                                                                            </div>
                                                                        )
                                                                    )}
                                                                </div>
                                                            </div>
                                                        )}
                                                </div>
                                            </CollapsibleContent>
                                        </div>
                                    </Collapsible>
                                );
                            })}
                        </div>
                    </ScrollArea>
                </div>
            )}

            {/* Change Scanner Results */}
            {changeSummary && (
                <div className="border rounded-lg">
                    <div className="p-3 bg-amber-50 border-b">
                        <div className="flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4 text-amber-600" />
                            <h4 className="text-sm font-semibold text-amber-900">
                                Relationship Changes Detected
                            </h4>
                        </div>
                        <div className="flex gap-3 mt-2 text-xs">
                            <span className="text-green-700">
                                +{changeSummary.new_count} new
                            </span>
                            <span className="text-amber-700">
                                ~{changeSummary.modified_count} modified
                            </span>
                            <span className="text-red-700">
                                -{changeSummary.removed_count} removed
                            </span>
                            <span className="text-gray-500">
                                {changeSummary.unchanged_count} unchanged
                            </span>
                        </div>
                    </div>

                    {changes && (
                        <ScrollArea className="h-[200px]">
                            <div className="p-2 space-y-2">
                                {changes.new_relationships.map((rel, i) => (
                                    <div
                                        key={`new-${i}`}
                                        className="p-2 bg-green-50 border border-green-200 rounded text-sm"
                                    >
                                        <span className="text-green-700 font-medium">
                                            NEW:
                                        </span>{" "}
                                        {rel.source} → {rel.target} (
                                        {rel.relationship_type})
                                    </div>
                                ))}

                                {changes.modified_relationships.map(
                                    (rel, i) => (
                                        <div
                                            key={`mod-${i}`}
                                            className="p-2 bg-amber-50 border border-amber-200 rounded text-sm"
                                        >
                                            <span className="text-amber-700 font-medium">
                                                CHANGED:
                                            </span>{" "}
                                            {rel.source} → {rel.target}
                                            <div className="text-xs text-amber-600 mt-1">
                                                {rel.old_emotional_tone} →{" "}
                                                {rel.new_emotional_tone} (
                                                {rel.old_sentiment_score} →{" "}
                                                {rel.new_sentiment_score})
                                            </div>
                                        </div>
                                    )
                                )}

                                {changes.potentially_removed.map((rel, i) => (
                                    <div
                                        key={`rem-${i}`}
                                        className="p-2 bg-red-50 border border-red-200 rounded text-sm"
                                    >
                                        <span className="text-red-700 font-medium">
                                            REMOVED?:
                                        </span>{" "}
                                        {rel.source} → {rel.target} (
                                        {rel.relationship_type})
                                        {rel.note && (
                                            <p className="text-xs text-red-600 mt-1">
                                                {rel.note}
                                            </p>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </ScrollArea>
                    )}
                </div>
            )}

            {/* Confirmation Dialog */}
            <Dialog
                open={showConfirmDialog}
                onOpenChange={setShowConfirmDialog}
            >
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>
                            Extract Character Interactions
                        </DialogTitle>
                        <DialogDescription>
                            This will analyze your manuscript chapter-by-chapter
                            to extract individual character interactions, which
                            build up into relationship scores with full evidence
                            trails.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-2 py-4">
                        <div className="text-sm">
                            <strong>Mode:</strong>{" "}
                            {focusMode === "all"
                                ? "All Characters"
                                : focusMode === "1-to-1"
                                ? "1-to-1 Focus"
                                : `${selectedCharacters.length} Selected`}
                        </div>
                        {focusMode === "1-to-1" &&
                            selectedCharacters.length === 2 && (
                                <div className="text-sm p-2 bg-rose-50 rounded text-rose-700">
                                    <strong>Analyzing:</strong>{" "}
                                    {
                                        characters.find(
                                            (c) =>
                                                c.vertex_id ===
                                                selectedCharacters[0]
                                        )?.name
                                    }{" "}
                                    ↔{" "}
                                    {
                                        characters.find(
                                            (c) =>
                                                c.vertex_id ===
                                                selectedCharacters[1]
                                        )?.name
                                    }
                                </div>
                            )}
                        <div className="text-sm">
                            <strong>Chapters:</strong>{" "}
                            {useAllChapters
                                ? `All (${chapters.length})`
                                : `${selectedChapters.length} selected`}
                        </div>
                        <div className="text-sm">
                            <strong>Model:</strong> {selectedModel}
                        </div>
                        <div className="p-2 bg-blue-50 rounded text-xs text-blue-700 space-y-1">
                            <p>
                                <strong>New approach:</strong>
                            </p>
                            <ul className="list-disc pl-4 space-y-0.5">
                                <li>Processes each chapter individually</li>
                                <li>
                                    Creates interaction records for every
                                    character moment
                                </li>
                                <li>
                                    Aggregates interactions into relationship
                                    scores
                                </li>
                                <li>
                                    Tracks how relationships evolve chapter by
                                    chapter
                                </li>
                            </ul>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setShowConfirmDialog(false)}
                        >
                            Cancel
                        </Button>
                        <Button onClick={handleConfirm}>
                            <Heart className="h-4 w-4 mr-2" />
                            Extract Interactions
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

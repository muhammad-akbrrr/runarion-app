import { useState, useEffect } from "react";
import { HelpCircle } from "lucide-react";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/Components/ui/tooltip";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/Components/ui/select";

interface Entity {
    vertex_id: string; // String to avoid JS precision loss with large Apache AGE IDs
    name: string;
    type: string;
    properties: Record<string, any>;
}

interface SummaryTabProps {
    entity: Entity;
    workspaceId: string;
    projectId: string;
}

interface ChapterSummary {
    chapter_number: number;
    chapter_name: string;
    activity: string;
    key_moments?: string[];
}

export default function SummaryTab({
    entity,
    workspaceId,
    projectId,
}: SummaryTabProps) {
    const [summaries, setSummaries] = useState<ChapterSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedChapter, setSelectedChapter] = useState<string>("all");

    useEffect(() => {
        loadSummaries();
    }, [entity.vertex_id]);

    useEffect(() => {
        // Reset to "all" when entity changes or when summaries load
        if (summaries.length > 0) {
            setSelectedChapter("all");
        }
    }, [entity.vertex_id, summaries.length]);

    const loadSummaries = async () => {
        setLoading(true);
        try {
            // Fetch fresh entity data from server to get latest summaries
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/records/entities/${entity.vertex_id}`
            );

            let entitySummaries: any[] = [];

            if (response.ok) {
                const data = await response.json();
                console.log("API response:", data);
                // API returns {success: true, entity: {...}} or just the entity
                const freshEntity = data?.entity || data;
                console.log("Fresh entity:", freshEntity);
                entitySummaries = freshEntity?.properties?._summaries || [];
            } else {
                // Fallback to prop data if fetch fails
                console.log(
                    "Fetch failed with status:",
                    response.status,
                    "- using prop data"
                );
                entitySummaries = entity.properties?._summaries || [];
            }

            console.log("Raw summaries:", entitySummaries);

            if (Array.isArray(entitySummaries) && entitySummaries.length > 0) {
                // Filter out invalid entries and sort by chapter number
                const validSummaries = entitySummaries.filter(
                    (s: any) => s && s.chapter_number != null
                );
                console.log("Valid summaries after filter:", validSummaries);
                const sorted = [...validSummaries].sort(
                    (a, b) => (a.chapter_number || 0) - (b.chapter_number || 0)
                );
                setSummaries(sorted);
            } else {
                setSummaries([]);
            }
        } catch (error) {
            console.error("Error loading summaries:", error);
            // Fallback to prop data on error
            const entitySummaries = entity.properties?._summaries || [];
            if (Array.isArray(entitySummaries) && entitySummaries.length > 0) {
                const validSummaries = entitySummaries.filter(
                    (s: any) => s && s.chapter_number != null
                );
                setSummaries(validSummaries);
            } else {
                setSummaries([]);
            }
        } finally {
            setLoading(false);
        }
    };

    const getFilteredSummaries = () => {
        if (selectedChapter === "all") {
            return summaries;
        }
        return summaries.filter(
            (s) =>
                s.chapter_number != null &&
                s.chapter_number.toString() === selectedChapter
        );
    };

    if (loading) {
        return (
            <div className="p-4">
                <p className="text-sm text-gray-500">Loading summaries...</p>
            </div>
        );
    }

    if (summaries.length === 0) {
        return (
            <div className="p-4 space-y-4">
                <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold">
                        Chapter Activity Summary
                    </h3>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs">
                            <p>
                                This tab shows how {entity.name} appears across
                                chapters. Summaries are generated when you run
                                the Summarizer in the Auditor tab. Select this
                                entity's category and run summarization to
                                generate chapter-by-chapter activity.
                            </p>
                        </TooltipContent>
                    </Tooltip>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <p className="text-sm text-gray-600">
                        No summaries available yet. Run the Summarizer in the
                        Auditor tab with category "{entity.type}" selected to
                        generate chapter-by-chapter activity for this entity.
                    </p>
                </div>
            </div>
        );
    }

    const filteredSummaries = getFilteredSummaries();

    return (
        <div className="p-4 space-y-4">
            <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold">
                        Chapter Activity Summary
                    </h3>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs">
                            <p>
                                Chapter-by-chapter breakdown of how{" "}
                                {entity.name} appears in the story. Generated by
                                the Summarizer when you analyze this entity's
                                category.
                            </p>
                        </TooltipContent>
                    </Tooltip>
                </div>

                {/* Chapter Dropdown */}
                <Select
                    value={selectedChapter}
                    onValueChange={setSelectedChapter}
                >
                    <SelectTrigger className="w-[180px] h-8 text-xs">
                        <SelectValue placeholder="Select chapter" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">
                            All Chapters ({summaries.length})
                        </SelectItem>
                        {summaries.map((summary, idx) =>
                            summary?.chapter_number != null ? (
                                <SelectItem
                                    key={`ch-${summary.chapter_number}`}
                                    value={String(summary.chapter_number)}
                                >
                                    Chapter {summary.chapter_number}:{" "}
                                    {summary.chapter_name || "Untitled"}
                                </SelectItem>
                            ) : null
                        )}
                    </SelectContent>
                </Select>
            </div>

            {/* Summary badge showing appearance count */}
            <div className="flex items-center gap-2 text-xs text-gray-500">
                <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                    Appears in {summaries.length} chapter
                    {summaries.length !== 1 ? "s" : ""}
                </span>
                {selectedChapter !== "all" && (
                    <span className="text-gray-400">
                        Showing Chapter {selectedChapter}
                    </span>
                )}
            </div>

            <div className="space-y-4">
                {filteredSummaries.map((summary, index) =>
                    summary ? (
                        <div
                            key={index}
                            className="border rounded-lg p-4 bg-white shadow-sm"
                        >
                            <div className="flex items-center justify-between mb-2">
                                <h4 className="text-sm font-medium text-gray-900">
                                    Chapter {summary.chapter_number ?? "?"}:{" "}
                                    {summary.chapter_name || "Untitled"}
                                </h4>
                            </div>
                            <p className="text-sm text-gray-700 mb-3 leading-relaxed">
                                {summary.activity ||
                                    "No activity description available."}
                            </p>
                            {summary.key_moments &&
                                Array.isArray(summary.key_moments) &&
                                summary.key_moments.length > 0 && (
                                    <div className="mt-3 pt-3 border-t border-gray-100">
                                        <p className="text-xs font-semibold text-gray-600 mb-2">
                                            Key Moments:
                                        </p>
                                        <ul className="text-xs text-gray-600 space-y-1.5">
                                            {summary.key_moments.map(
                                                (moment, i) => (
                                                    <li
                                                        key={i}
                                                        className="flex items-start gap-2"
                                                    >
                                                        <span className="text-blue-500 mt-0.5">
                                                            •
                                                        </span>
                                                        <span>{moment}</span>
                                                    </li>
                                                )
                                            )}
                                        </ul>
                                    </div>
                                )}
                        </div>
                    ) : null
                )}
            </div>
        </div>
    );
}

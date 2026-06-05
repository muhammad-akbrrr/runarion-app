import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
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
    TooltipProvider,
    TooltipTrigger,
} from "@/Components/ui/tooltip";
import {
    Edit,
    Trash2,
    Search,
    CheckSquare,
    Square,
} from "lucide-react";
import type { Entity, Relationship, SortBy, FilterBy } from "../types";

interface AllRelationshipsViewProps {
    entity: Entity;
    filteredAndSorted: Relationship[];
    entityRelationships: Relationship[];
    relationshipTypes: string[];
    searchQuery: string;
    setSearchQuery: (query: string) => void;
    filterBy: FilterBy;
    setFilterBy: (filter: FilterBy) => void;
    sortBy: SortBy;
    setSortBy: (sort: SortBy) => void;
    multiSelectMode: boolean;
    selectedEdgeIds: Set<string>;
    toggleSelectEdge: (edgeId: string) => void;
    onSelectRelationship: (rel: Relationship) => void;
    onDeleteRelationship: (edgeId: any) => void;
}

export default function AllRelationshipsView({
    entity,
    filteredAndSorted,
    entityRelationships,
    relationshipTypes,
    searchQuery,
    setSearchQuery,
    filterBy,
    setFilterBy,
    sortBy,
    setSortBy,
    multiSelectMode,
    selectedEdgeIds,
    toggleSelectEdge,
    onSelectRelationship,
    onDeleteRelationship,
}: AllRelationshipsViewProps) {
    return (
        <>
            {/* Filters and Search */}
            <div className="space-y-2">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                    <Input
                        placeholder="Search relationships..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10"
                    />
                </div>
                <div className="flex gap-2">
                    <Select
                        value={filterBy}
                        onValueChange={(v) => setFilterBy(v as FilterBy)}
                    >
                        <SelectTrigger className="flex-1">
                            <SelectValue placeholder="Filter by type" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All Types</SelectItem>
                            {relationshipTypes.map((type) => (
                                <SelectItem key={type} value={type}>
                                    {type.replace("_", " ")}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <Select
                        value={sortBy}
                        onValueChange={(v) => setSortBy(v as SortBy)}
                    >
                        <SelectTrigger className="w-40">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="name">Sort by Name</SelectItem>
                            <SelectItem value="type">Sort by Type</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </div>

            {/* Relationships List */}
            <div className="flex-1 overflow-y-auto space-y-2">
                {filteredAndSorted.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                        {entityRelationships.length === 0
                            ? "No relationships yet. Click 'Add Relationship' to create one."
                            : "No relationships match your filters."}
                    </div>
                ) : (
                    filteredAndSorted.map((rel) => {
                        const isSource = rel.source === entity.name;
                        const otherEntity = isSource ? rel.target : rel.source;
                        const direction = isSource ? "→" : "←";
                        const isSelected = selectedEdgeIds.has(rel.edge_id);

                        return (
                            <div
                                key={rel.edge_id}
                                className={`border rounded-lg p-3 hover:bg-gray-50 cursor-pointer transition-colors ${
                                    isSelected
                                        ? "bg-blue-50 border-blue-300"
                                        : ""
                                }`}
                                onClick={() => {
                                    if (multiSelectMode) {
                                        toggleSelectEdge(rel.edge_id);
                                    } else {
                                        onSelectRelationship(rel);
                                    }
                                }}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex items-start gap-2 flex-1">
                                        {multiSelectMode && (
                                            <div className="pt-0.5">
                                                {isSelected ? (
                                                    <CheckSquare className="h-4 w-4 text-blue-600" />
                                                ) : (
                                                    <Square className="h-4 w-4 text-gray-400" />
                                                )}
                                            </div>
                                        )}
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2 text-sm">
                                                {!isSource && (
                                                    <span className="text-gray-400">
                                                        {direction}
                                                    </span>
                                                )}
                                                <span className="font-medium">
                                                    {otherEntity}
                                                </span>
                                                {isSource && (
                                                    <span className="text-gray-400">
                                                        {direction}
                                                    </span>
                                                )}
                                            </div>
                                            <div className="flex items-center gap-2 mt-1">
                                                <span className="text-xs text-gray-500">
                                                    {rel.relationship_type.replace(
                                                        "_",
                                                        " "
                                                    )}
                                                </span>
                                                {rel.properties &&
                                                    (() => {
                                                        const props =
                                                            rel.properties;
                                                        const sentimentScore =
                                                            props.sentiment_score !==
                                                            undefined
                                                                ? props.sentiment_score
                                                                : null;
                                                        const emotionalTone =
                                                            props.emotional_tone;
                                                        const context =
                                                            props.context;
                                                        const interactionCount =
                                                            props.interaction_count;

                                                        if (
                                                            sentimentScore !==
                                                            null
                                                        ) {
                                                            return (
                                                                <TooltipProvider>
                                                                    <Tooltip>
                                                                        <TooltipTrigger
                                                                            asChild
                                                                        >
                                                                            <span
                                                                                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold cursor-help ${
                                                                                    sentimentScore <
                                                                                    -50
                                                                                        ? "bg-red-100 text-red-700"
                                                                                        : sentimentScore <
                                                                                          0
                                                                                        ? "bg-orange-100 text-orange-700"
                                                                                        : sentimentScore ===
                                                                                          0
                                                                                        ? "bg-gray-100 text-gray-700"
                                                                                        : sentimentScore <
                                                                                          50
                                                                                        ? "bg-lime-100 text-lime-700"
                                                                                        : "bg-green-100 text-green-700"
                                                                                }`}
                                                                            >
                                                                                {sentimentScore >
                                                                                0
                                                                                    ? "+"
                                                                                    : ""}
                                                                                {
                                                                                    sentimentScore
                                                                                }
                                                                            </span>
                                                                        </TooltipTrigger>
                                                                        <TooltipContent
                                                                            side="top"
                                                                            className="max-w-xs p-3"
                                                                        >
                                                                            <div className="space-y-2">
                                                                                <div className="font-semibold text-sm">
                                                                                    Sentiment:{" "}
                                                                                    {sentimentScore >
                                                                                    0
                                                                                        ? "+"
                                                                                        : ""}
                                                                                    {
                                                                                        sentimentScore
                                                                                    }
                                                                                </div>
                                                                                {emotionalTone && (
                                                                                    <div className="text-xs">
                                                                                        <span className="text-gray-500">
                                                                                            Tone:
                                                                                        </span>{" "}
                                                                                        <span className="capitalize">
                                                                                            {
                                                                                                emotionalTone
                                                                                            }
                                                                                        </span>
                                                                                    </div>
                                                                                )}
                                                                                {interactionCount && (
                                                                                    <div className="text-xs">
                                                                                        <span className="text-gray-500">
                                                                                            Based
                                                                                            on:
                                                                                        </span>{" "}
                                                                                        {
                                                                                            interactionCount
                                                                                        }{" "}
                                                                                        interactions
                                                                                    </div>
                                                                                )}
                                                                                {context && (
                                                                                    <div className="text-xs text-gray-600 border-t pt-2 mt-2">
                                                                                        {
                                                                                            context
                                                                                        }
                                                                                    </div>
                                                                                )}
                                                                                <div className="text-[10px] text-gray-400 pt-1">
                                                                                    Click
                                                                                    for
                                                                                    full
                                                                                    details
                                                                                </div>
                                                                            </div>
                                                                        </TooltipContent>
                                                                    </Tooltip>
                                                                </TooltipProvider>
                                                            );
                                                        }
                                                        return null;
                                                    })()}
                                            </div>
                                        </div>
                                    </div>
                                    {!multiSelectMode && (
                                        <div className="flex gap-1">
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    onSelectRelationship(rel);
                                                }}
                                                className="h-7 w-7 p-0"
                                            >
                                                <Edit className="h-3 w-3" />
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    onDeleteRelationship(
                                                        rel.edge_id
                                                    );
                                                }}
                                                className="h-7 w-7 p-0 text-red-500 hover:text-red-700"
                                            >
                                                <Trash2 className="h-3 w-3" />
                                            </Button>
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })
                )}
            </div>
        </>
    );
}

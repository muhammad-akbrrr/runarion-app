import { Label } from "@/Components/ui/label";
import {
    ChevronDown,
    ChevronRight,
    Edit,
    Trash2,
    Plus,
    X,
    Loader2,
} from "lucide-react";
import type {
    Interaction,
    SentimentBreakdownItem,
    Relationship,
    InteractionsViewMode,
} from "../types";
import {
    INTERACTION_TYPES,
    INTERACTION_TONES,
    POSITIVE_INTERACTION_TYPES,
    NEGATIVE_INTERACTION_TYPES,
} from "../constants";

interface InteractionsSectionProps {
    selectedRelationship: Relationship;
    interactions: Interaction[];
    loadingInteractions: boolean;
    interactionsExpanded: boolean;
    setInteractionsExpanded: (expanded: boolean) => void;
    interactionsViewMode: InteractionsViewMode;
    setInteractionsViewMode: (mode: InteractionsViewMode) => void;
    expandedChapters: Set<number>;
    toggleChapter: (chapterNum: number) => void;
    sentimentBreakdown: SentimentBreakdownItem[];
    clampedTotalSentiment: number;
    rawTotalSentiment: number;
    interactionsByChapter: [number, Interaction[]][];
    // Create interaction
    showCreateInteraction: boolean;
    setShowCreateInteraction: (show: boolean) => void;
    creatingInteraction: boolean;
    newInteraction: {
        interaction_type: string;
        emotional_tone: string;
        chapter_number: number;
        context: string;
        text_evidence: string;
    };
    setNewInteraction: (interaction: {
        interaction_type: string;
        emotional_tone: string;
        chapter_number: number;
        context: string;
        text_evidence: string;
    }) => void;
    onCreateInteraction: () => void;
    // Edit interaction
    editingInteraction: Interaction | null;
    setEditingInteraction: (interaction: Interaction | null) => void;
    savingInteraction: boolean;
    onUpdateInteraction: () => void;
    // Delete interaction
    deletingInteraction: string | null;
    onDeleteInteraction: (vertexId: string) => void;
}

export default function InteractionsSection({
    selectedRelationship,
    interactions,
    loadingInteractions,
    interactionsExpanded,
    setInteractionsExpanded,
    interactionsViewMode,
    setInteractionsViewMode,
    expandedChapters,
    toggleChapter,
    sentimentBreakdown,
    clampedTotalSentiment,
    rawTotalSentiment,
    interactionsByChapter,
    showCreateInteraction,
    setShowCreateInteraction,
    creatingInteraction,
    newInteraction,
    setNewInteraction,
    onCreateInteraction,
    editingInteraction,
    setEditingInteraction,
    savingInteraction,
    onUpdateInteraction,
    deletingInteraction,
    onDeleteInteraction,
}: InteractionsSectionProps) {
    const props = selectedRelationship.properties || {};
    const isV2 = props.analysis_version === "v2";

    // Only render sentiment breakdown for non-V2 relationships
    const showSentimentBreakdown =
        props.sentiment_score !== undefined &&
        !isV2 &&
        interactionsViewMode === "all";

    // Only show interactions list for non-V2 relationships
    const showInteractionsList =
        (interactions.length > 0 || showCreateInteraction) && !isV2;

    if (!showSentimentBreakdown && !showInteractionsList) {
        return null;
    }

    return (
        <>
            {/* CK3-Style Sentiment Breakdown */}
            {showSentimentBreakdown && (
                <div className="border rounded-lg p-3 bg-linear-to-r from-red-50 via-gray-50 to-green-50">
                    <div className="flex items-center justify-between mb-3">
                        <div>
                            <Label className="text-sm font-semibold">
                                Sentiment Breakdown
                            </Label>
                            {props.directional && (
                                <p className="text-xs text-gray-500 mt-0.5">
                                    How {selectedRelationship.source} perceives{" "}
                                    {selectedRelationship.target}
                                </p>
                            )}
                        </div>
                        <div className="text-right">
                            <span
                                className={`text-xl font-bold ${
                                    clampedTotalSentiment < 0
                                        ? "text-red-600"
                                        : clampedTotalSentiment > 0
                                        ? "text-green-600"
                                        : "text-gray-600"
                                }`}
                            >
                                {clampedTotalSentiment > 0 ? "+" : ""}
                                {clampedTotalSentiment}
                            </span>
                            {Math.abs(rawTotalSentiment) > 100 && (
                                <p className="text-[10px] text-gray-400">
                                    (raw: {rawTotalSentiment > 0 ? "+" : ""}
                                    {rawTotalSentiment})
                                </p>
                            )}
                        </div>
                    </div>

                    {/* Sentiment bar */}
                    <div className="h-3 bg-gray-200 rounded-full overflow-hidden mb-3">
                        <div
                            className={`h-full transition-all duration-300 ${
                                clampedTotalSentiment < 0
                                    ? "bg-linear-to-r from-red-600 to-red-400"
                                    : "bg-linear-to-r from-green-400 to-green-600"
                            }`}
                            style={{
                                width: `${Math.min(
                                    100,
                                    Math.abs(clampedTotalSentiment) / 2
                                )}%`,
                                marginLeft:
                                    clampedTotalSentiment >= 0
                                        ? "50%"
                                        : `${
                                              50 -
                                              Math.min(
                                                  50,
                                                  Math.abs(
                                                      clampedTotalSentiment
                                                  ) / 2
                                              )
                                          }%`,
                            }}
                        />
                    </div>

                    {/* Breakdown items */}
                    {loadingInteractions ? (
                        <div className="flex items-center justify-center py-2">
                            <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                            <span className="ml-2 text-sm text-gray-500">
                                Loading breakdown...
                            </span>
                        </div>
                    ) : sentimentBreakdown.length > 0 ? (
                        <div className="space-y-2">
                            {sentimentBreakdown
                                .slice(0, interactionsExpanded ? undefined : 5)
                                .map((item, idx) => (
                                    <div
                                        key={idx}
                                        className="text-xs py-1.5 border-b border-gray-100 last:border-0"
                                    >
                                        <div className="flex items-center gap-2">
                                            <span
                                                className={`font-bold min-w-10 ${
                                                    item.value < 0
                                                        ? "text-red-600"
                                                        : item.value > 0
                                                        ? "text-green-600"
                                                        : "text-gray-500"
                                                }`}
                                            >
                                                {item.value > 0 ? "+" : ""}
                                                {item.value}
                                            </span>
                                            <span className="text-gray-700 font-medium">
                                                {item.label}
                                            </span>
                                            {item.chapter !== undefined && (
                                                <span className="text-gray-400 text-[10px] ml-auto">
                                                    Ch.{item.chapter + 1}
                                                </span>
                                            )}
                                        </div>
                                        {item.reasoning && (
                                            <p className="text-gray-500 mt-1 pl-12 italic text-[11px]">
                                                "{item.reasoning}"
                                            </p>
                                        )}
                                    </div>
                                ))}
                            {sentimentBreakdown.length > 5 && (
                                <button
                                    onClick={() =>
                                        setInteractionsExpanded(
                                            !interactionsExpanded
                                        )
                                    }
                                    className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1 mt-1"
                                >
                                    {interactionsExpanded ? (
                                        <>
                                            <ChevronDown className="h-3 w-3" />
                                            Show less
                                        </>
                                    ) : (
                                        <>
                                            <ChevronRight className="h-3 w-3" />
                                            Show {sentimentBreakdown.length - 5}{" "}
                                            more
                                        </>
                                    )}
                                </button>
                            )}
                        </div>
                    ) : (
                        <p className="text-xs text-gray-500 text-center py-2">
                            No interaction breakdown available
                        </p>
                    )}
                </div>
            )}

            {/* Expandable Interactions List */}
            {showInteractionsList && (
                <div className="border rounded-lg overflow-hidden">
                    {/* Header */}
                    <div className="flex items-center justify-between p-3 bg-gray-50 border-b">
                        <button
                            onClick={() =>
                                setInteractionsExpanded(!interactionsExpanded)
                            }
                            className="flex items-center gap-2 hover:text-blue-600 transition-colors"
                        >
                            {interactionsExpanded ? (
                                <ChevronDown className="h-4 w-4" />
                            ) : (
                                <ChevronRight className="h-4 w-4" />
                            )}
                            <span className="font-medium text-sm">
                                Interactions ({interactions.length})
                            </span>
                        </button>

                        <div className="flex items-center gap-2">
                            {interactionsExpanded && (
                                <>
                                    <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5">
                                        <button
                                            onClick={() =>
                                                setInteractionsViewMode("all")
                                            }
                                            className={`px-2 py-1 text-xs rounded-md transition-colors ${
                                                interactionsViewMode === "all"
                                                    ? "bg-white shadow-sm font-medium"
                                                    : "text-gray-600 hover:text-gray-900"
                                            }`}
                                        >
                                            All
                                        </button>
                                        <button
                                            onClick={() =>
                                                setInteractionsViewMode(
                                                    "by-chapter"
                                                )
                                            }
                                            className={`px-2 py-1 text-xs rounded-md transition-colors ${
                                                interactionsViewMode ===
                                                "by-chapter"
                                                    ? "bg-white shadow-sm font-medium"
                                                    : "text-gray-600 hover:text-gray-900"
                                            }`}
                                        >
                                            By Chapter
                                        </button>
                                    </div>
                                    <button
                                        onClick={() =>
                                            setShowCreateInteraction(true)
                                        }
                                        className="p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                                        title="Add Interaction"
                                    >
                                        <Plus className="h-4 w-4" />
                                    </button>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Create Interaction Form */}
                    {showCreateInteraction && interactionsExpanded && (
                        <CreateInteractionForm
                            newInteraction={newInteraction}
                            setNewInteraction={setNewInteraction}
                            creatingInteraction={creatingInteraction}
                            onCreateInteraction={onCreateInteraction}
                            onClose={() => setShowCreateInteraction(false)}
                        />
                    )}

                    {/* Edit Interaction Form */}
                    {editingInteraction && interactionsExpanded && (
                        <EditInteractionForm
                            editingInteraction={editingInteraction}
                            setEditingInteraction={setEditingInteraction}
                            savingInteraction={savingInteraction}
                            onUpdateInteraction={onUpdateInteraction}
                        />
                    )}

                    {/* Interactions Content */}
                    {interactionsExpanded && (
                        <div
                            className="max-h-80 overflow-y-auto"
                            key={interactionsViewMode}
                        >
                            {interactionsViewMode === "all" ? (
                                <AllInteractionsView
                                    interactions={interactions}
                                    deletingInteraction={deletingInteraction}
                                    onDeleteInteraction={onDeleteInteraction}
                                    onEditInteraction={setEditingInteraction}
                                />
                            ) : (
                                <ByChapterView
                                    interactionsByChapter={interactionsByChapter}
                                    expandedChapters={expandedChapters}
                                    toggleChapter={toggleChapter}
                                    deletingInteraction={deletingInteraction}
                                    onDeleteInteraction={onDeleteInteraction}
                                    onEditInteraction={setEditingInteraction}
                                />
                            )}
                        </div>
                    )}
                </div>
            )}
        </>
    );
}

// Sub-components

function CreateInteractionForm({
    newInteraction,
    setNewInteraction,
    creatingInteraction,
    onCreateInteraction,
    onClose,
}: {
    newInteraction: {
        interaction_type: string;
        emotional_tone: string;
        chapter_number: number;
        context: string;
        text_evidence: string;
    };
    setNewInteraction: (i: typeof newInteraction) => void;
    creatingInteraction: boolean;
    onCreateInteraction: () => void;
    onClose: () => void;
}) {
    return (
        <div className="p-4 bg-blue-50 border-b space-y-3">
            <div className="flex items-center justify-between">
                <span className="font-medium text-sm text-blue-800">
                    New Interaction
                </span>
                <button
                    onClick={onClose}
                    className="text-gray-500 hover:text-gray-700"
                >
                    <X className="h-4 w-4" />
                </button>
            </div>

            <div className="grid grid-cols-2 gap-2">
                <div>
                    <label className="text-xs text-gray-600">Type</label>
                    <select
                        value={newInteraction.interaction_type}
                        onChange={(e) =>
                            setNewInteraction({
                                ...newInteraction,
                                interaction_type: e.target.value,
                            })
                        }
                        className="w-full text-sm border rounded px-2 py-1"
                    >
                        {INTERACTION_TYPES.map((type) => (
                            <option key={type} value={type}>
                                {type}
                            </option>
                        ))}
                    </select>
                </div>
                <div>
                    <label className="text-xs text-gray-600">Tone</label>
                    <select
                        value={newInteraction.emotional_tone}
                        onChange={(e) =>
                            setNewInteraction({
                                ...newInteraction,
                                emotional_tone: e.target.value,
                            })
                        }
                        className="w-full text-sm border rounded px-2 py-1"
                    >
                        {INTERACTION_TONES.map((tone) => (
                            <option key={tone} value={tone}>
                                {tone.charAt(0).toUpperCase() + tone.slice(1)}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            <div>
                <label className="text-xs text-gray-600">Chapter</label>
                <input
                    type="number"
                    min="0"
                    value={newInteraction.chapter_number}
                    onChange={(e) =>
                        setNewInteraction({
                            ...newInteraction,
                            chapter_number: parseInt(e.target.value) || 0,
                        })
                    }
                    className="w-full text-sm border rounded px-2 py-1"
                    placeholder="Chapter number (0-indexed)"
                />
            </div>

            <div>
                <label className="text-xs text-gray-600">Context</label>
                <input
                    type="text"
                    value={newInteraction.context}
                    onChange={(e) =>
                        setNewInteraction({
                            ...newInteraction,
                            context: e.target.value,
                        })
                    }
                    className="w-full text-sm border rounded px-2 py-1"
                    placeholder="Brief description of the interaction"
                />
            </div>

            <div>
                <label className="text-xs text-gray-600">
                    Text Evidence (optional)
                </label>
                <input
                    type="text"
                    value={newInteraction.text_evidence}
                    onChange={(e) =>
                        setNewInteraction({
                            ...newInteraction,
                            text_evidence: e.target.value,
                        })
                    }
                    className="w-full text-sm border rounded px-2 py-1"
                    placeholder="Quote from the text"
                />
            </div>

            <div className="flex gap-2">
                <button
                    onClick={onClose}
                    className="flex-1 px-3 py-1.5 text-sm border rounded hover:bg-gray-100"
                >
                    Cancel
                </button>
                <button
                    onClick={onCreateInteraction}
                    disabled={creatingInteraction || !newInteraction.context}
                    className="flex-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                >
                    {creatingInteraction ? "Creating..." : "Create"}
                </button>
            </div>
        </div>
    );
}

function EditInteractionForm({
    editingInteraction,
    setEditingInteraction,
    savingInteraction,
    onUpdateInteraction,
}: {
    editingInteraction: Interaction;
    setEditingInteraction: (i: Interaction | null) => void;
    savingInteraction: boolean;
    onUpdateInteraction: () => void;
}) {
    return (
        <div className="p-4 bg-amber-50 border-b space-y-3">
            <div className="flex items-center justify-between">
                <span className="font-medium text-sm text-amber-800">
                    Edit Interaction
                </span>
                <button
                    onClick={() => setEditingInteraction(null)}
                    className="text-gray-500 hover:text-gray-700"
                >
                    <X className="h-4 w-4" />
                </button>
            </div>

            <div className="grid grid-cols-2 gap-2">
                <div>
                    <label className="text-xs text-gray-600">Type</label>
                    <select
                        value={editingInteraction.interaction_type}
                        onChange={(e) =>
                            setEditingInteraction({
                                ...editingInteraction,
                                interaction_type: e.target.value,
                            })
                        }
                        className="w-full text-sm border rounded px-2 py-1"
                    >
                        {INTERACTION_TYPES.map((type) => (
                            <option key={type} value={type}>
                                {type}
                            </option>
                        ))}
                    </select>
                </div>
                <div>
                    <label className="text-xs text-gray-600">Tone</label>
                    <select
                        value={editingInteraction.emotional_tone}
                        onChange={(e) =>
                            setEditingInteraction({
                                ...editingInteraction,
                                emotional_tone: e.target.value,
                            })
                        }
                        className="w-full text-sm border rounded px-2 py-1"
                    >
                        {INTERACTION_TONES.map((tone) => (
                            <option key={tone} value={tone}>
                                {tone.charAt(0).toUpperCase() + tone.slice(1)}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            <div>
                <label className="text-xs text-gray-600">
                    Sentiment Modifier ({editingInteraction.sentiment_modifier ?? 0})
                </label>
                <input
                    type="range"
                    min="-100"
                    max="100"
                    value={editingInteraction.sentiment_modifier ?? 0}
                    onChange={(e) =>
                        setEditingInteraction({
                            ...editingInteraction,
                            sentiment_modifier: parseInt(e.target.value),
                        })
                    }
                    className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-400">
                    <span>-100 (hostile)</span>
                    <span>+100 (friendly)</span>
                </div>
            </div>

            <div>
                <label className="text-xs text-gray-600">Context</label>
                <input
                    type="text"
                    value={editingInteraction.context || ""}
                    onChange={(e) =>
                        setEditingInteraction({
                            ...editingInteraction,
                            context: e.target.value,
                        })
                    }
                    className="w-full text-sm border rounded px-2 py-1"
                />
            </div>

            <div>
                <label className="text-xs text-gray-600">Text Evidence</label>
                <input
                    type="text"
                    value={editingInteraction.text_evidence || ""}
                    onChange={(e) =>
                        setEditingInteraction({
                            ...editingInteraction,
                            text_evidence: e.target.value,
                        })
                    }
                    className="w-full text-sm border rounded px-2 py-1"
                />
            </div>

            <div className="flex gap-2">
                <button
                    onClick={() => setEditingInteraction(null)}
                    className="flex-1 px-3 py-1.5 text-sm border rounded hover:bg-gray-100"
                >
                    Cancel
                </button>
                <button
                    onClick={onUpdateInteraction}
                    disabled={savingInteraction}
                    className="flex-1 px-3 py-1.5 text-sm bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50"
                >
                    {savingInteraction ? "Saving..." : "Save Changes"}
                </button>
            </div>
        </div>
    );
}

function AllInteractionsView({
    interactions,
    deletingInteraction,
    onDeleteInteraction,
    onEditInteraction,
}: {
    interactions: Interaction[];
    deletingInteraction: string | null;
    onDeleteInteraction: (vertexId: string) => void;
    onEditInteraction: (interaction: Interaction) => void;
}) {
    return (
        <div className="divide-y">
            {interactions.map((interaction, idx) => (
                <InteractionItem
                    key={interaction.vertex_id || idx}
                    interaction={interaction}
                    deletingInteraction={deletingInteraction}
                    onDeleteInteraction={onDeleteInteraction}
                    onEditInteraction={onEditInteraction}
                />
            ))}
        </div>
    );
}

function ByChapterView({
    interactionsByChapter,
    expandedChapters,
    toggleChapter,
    deletingInteraction,
    onDeleteInteraction,
    onEditInteraction,
}: {
    interactionsByChapter: [number, Interaction[]][];
    expandedChapters: Set<number>;
    toggleChapter: (chapterNum: number) => void;
    deletingInteraction: string | null;
    onDeleteInteraction: (vertexId: string) => void;
    onEditInteraction: (interaction: Interaction) => void;
}) {
    return (
        <div className="divide-y">
            {interactionsByChapter.map(([chapterNum, chapterInteractions]) => (
                <div key={chapterNum} className="border-b last:border-b-0">
                    <button
                        onClick={() => toggleChapter(chapterNum)}
                        className="w-full flex items-center justify-between p-3 bg-blue-50 hover:bg-blue-100 transition-colors"
                    >
                        <div className="flex items-center gap-2">
                            {expandedChapters.has(chapterNum) ? (
                                <ChevronDown className="h-4 w-4 text-blue-600" />
                            ) : (
                                <ChevronRight className="h-4 w-4 text-blue-600" />
                            )}
                            <span className="font-medium text-sm text-blue-800">
                                {chapterNum >= 0
                                    ? `Chapter ${chapterNum + 1}`
                                    : "Unknown Chapter"}
                            </span>
                            <span className="text-xs text-blue-600 bg-blue-100 px-2 py-0.5 rounded-full">
                                {chapterInteractions.length} interactions
                            </span>
                        </div>
                        {(() => {
                            const chapterSentiment = chapterInteractions.reduce(
                                (sum, i) => sum + (i.sentiment_modifier || 0),
                                0
                            );
                            return (
                                <span
                                    className={`text-xs font-bold px-2 py-0.5 rounded ${
                                        chapterSentiment > 0
                                            ? "bg-green-100 text-green-700"
                                            : chapterSentiment < 0
                                            ? "bg-red-100 text-red-700"
                                            : "bg-gray-100 text-gray-700"
                                    }`}
                                >
                                    {chapterSentiment > 0 ? "+" : ""}
                                    {chapterSentiment}
                                </span>
                            );
                        })()}
                    </button>

                    {expandedChapters.has(chapterNum) && (
                        <div className="divide-y bg-white">
                            {chapterInteractions.map((interaction, idx) => (
                                <InteractionItem
                                    key={interaction.vertex_id || idx}
                                    interaction={interaction}
                                    deletingInteraction={deletingInteraction}
                                    onDeleteInteraction={onDeleteInteraction}
                                    onEditInteraction={onEditInteraction}
                                    indented
                                />
                            ))}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}

function InteractionItem({
    interaction,
    deletingInteraction,
    onDeleteInteraction,
    onEditInteraction,
    indented = false,
}: {
    interaction: Interaction;
    deletingInteraction: string | null;
    onDeleteInteraction: (vertexId: string) => void;
    onEditInteraction: (interaction: Interaction) => void;
    indented?: boolean;
}) {
    const isPositive = POSITIVE_INTERACTION_TYPES.includes(
        interaction.interaction_type
    );
    const isNegative = NEGATIVE_INTERACTION_TYPES.includes(
        interaction.interaction_type
    );

    return (
        <div className={`p-3 hover:bg-gray-50 group ${indented ? "pl-8" : ""}`}>
            <div className="flex items-start justify-between gap-2">
                <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                        <span
                            className={`text-xs font-semibold px-2 py-0.5 rounded ${
                                isPositive
                                    ? "bg-green-100 text-green-700"
                                    : isNegative
                                    ? "bg-red-100 text-red-700"
                                    : "bg-gray-100 text-gray-700"
                            }`}
                        >
                            {interaction.interaction_type}
                        </span>
                        <span className="text-xs text-gray-500 capitalize">
                            {interaction.emotional_tone}
                        </span>
                        {interaction.chapter_number !== undefined && !indented && (
                            <span className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded">
                                Ch. {interaction.chapter_number + 1}
                            </span>
                        )}
                        {interaction.sentiment_modifier !== undefined && (
                            <span
                                className={`text-xs font-medium ${
                                    interaction.sentiment_modifier > 0
                                        ? "text-green-600"
                                        : interaction.sentiment_modifier < 0
                                        ? "text-red-600"
                                        : "text-gray-500"
                                }`}
                            >
                                {interaction.sentiment_modifier > 0 ? "+" : ""}
                                {interaction.sentiment_modifier}
                            </span>
                        )}
                    </div>
                    {interaction.context && (
                        <p className="text-sm text-gray-700 mt-1">
                            {interaction.context}
                        </p>
                    )}
                    {interaction.text_evidence && (
                        <p className="text-xs text-gray-500 mt-1 italic">
                            "{interaction.text_evidence}"
                        </p>
                    )}
                    {interaction.sentiment_reasoning && (
                        <p className="text-xs text-blue-600 mt-1.5 bg-blue-50 px-2 py-1 rounded">
                            💡 {interaction.sentiment_reasoning}
                        </p>
                    )}
                </div>
                {interaction.vertex_id && (
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-all">
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                onEditInteraction(interaction);
                            }}
                            className="p-1 text-gray-400 hover:text-blue-500"
                            title="Edit interaction"
                        >
                            <Edit className="h-4 w-4" />
                        </button>
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                onDeleteInteraction(String(interaction.vertex_id));
                            }}
                            disabled={
                                deletingInteraction ===
                                String(interaction.vertex_id)
                            }
                            className="p-1 text-gray-400 hover:text-red-500"
                            title="Delete interaction"
                        >
                            {deletingInteraction ===
                            String(interaction.vertex_id) ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <Trash2 className="h-4 w-4" />
                            )}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

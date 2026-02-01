import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { Label } from "@/Components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/Components/ui/select";
import { Textarea } from "@/Components/ui/textarea";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/Components/ui/tooltip";
import {
    Edit,
    Trash2,
    Plus,
    X,
    ChevronDown,
    ChevronRight,
    Loader2,
    RefreshCw,
} from "lucide-react";
import type {
    Entity,
    Relationship,
    ChapterAnalysis,
    Interaction,
    SentimentBreakdownItem,
    InteractionsViewMode,
} from "../types";
import {
    STANDARD_RELATIONSHIP_TYPES,
    STANDARD_EMOTIONAL_TONES,
} from "../constants";
import InteractionsSection from "./InteractionsSection";

interface OneToOneViewProps {
    entity: Entity;
    selectedRelationship: Relationship | null;
    allCharacters: string[];
    getRelationshipWith: (characterName: string) => Relationship | null;
    onSelectRelationship: (rel: Relationship) => void;
    setSelectedRelationship: (rel: Relationship | null) => void;
    // Edit state
    isEditing: boolean;
    setIsEditing: (editing: boolean) => void;
    editedType: string;
    setEditedType: (type: string) => void;
    useCustomType: boolean;
    setUseCustomType: (use: boolean) => void;
    customType: string;
    setCustomType: (type: string) => void;
    useCustomTone: boolean;
    setUseCustomTone: (use: boolean) => void;
    customTone: string;
    setCustomTone: (tone: string) => void;
    context: string;
    setContext: (context: string) => void;
    emotionalTone: string;
    setEmotionalTone: (tone: string) => void;
    sentimentScore: number | "";
    setSentimentScore: (score: number | "") => void;
    editedProperties: Record<string, any>;
    setEditedProperties: (props: Record<string, any>) => void;
    newPropertyKey: string;
    setNewPropertyKey: (key: string) => void;
    newPropertyValue: string;
    setNewPropertyValue: (value: string) => void;
    saving: boolean;
    onAddProperty: () => void;
    onEditRelationship: () => void;
    onDeleteRelationship: (edgeId: any) => void;
    onCancelEdit: () => void;
    // Chapter analyses
    expandedChapters: Set<number>;
    setExpandedChapters: (chapters: Set<number>) => void;
    editingChapter: ChapterAnalysis | null;
    setEditingChapter: (chapter: ChapterAnalysis | null) => void;
    savingChapter: boolean;
    showAddChapter: boolean;
    setShowAddChapter: (show: boolean) => void;
    deletingChapter: number | null;
    onAddChapter: (chapter: ChapterAnalysis) => void;
    onEditChapter: (chapter: ChapterAnalysis) => void;
    onDeleteChapter: (chapterNumber: number) => void;
    // Interactions
    interactions: Interaction[];
    loadingInteractions: boolean;
    interactionsExpanded: boolean;
    setInteractionsExpanded: (expanded: boolean) => void;
    interactionsViewMode: InteractionsViewMode;
    setInteractionsViewMode: (mode: InteractionsViewMode) => void;
    interactionExpandedChapters: Set<number>;
    toggleInteractionChapter: (chapterNum: number) => void;
    sentimentBreakdown: SentimentBreakdownItem[];
    clampedTotalSentiment: number;
    rawTotalSentiment: number;
    interactionsByChapter: [number, Interaction[]][];
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
    editingInteraction: Interaction | null;
    setEditingInteraction: (interaction: Interaction | null) => void;
    savingInteraction: boolean;
    onUpdateInteraction: () => void;
    deletingInteraction: string | null;
    onDeleteInteraction: (vertexId: string) => void;
    // Reassess
    reassessing: boolean;
    onReassessRelationship: () => void;
}

export default function OneToOneView({
    entity,
    selectedRelationship,
    allCharacters,
    getRelationshipWith,
    onSelectRelationship,
    setSelectedRelationship,
    isEditing,
    setIsEditing,
    editedType,
    setEditedType,
    useCustomType,
    setUseCustomType,
    customType,
    setCustomType,
    useCustomTone,
    setUseCustomTone,
    customTone,
    setCustomTone,
    context,
    setContext,
    emotionalTone,
    setEmotionalTone,
    sentimentScore,
    setSentimentScore,
    editedProperties,
    setEditedProperties,
    newPropertyKey,
    setNewPropertyKey,
    newPropertyValue,
    setNewPropertyValue,
    saving,
    onAddProperty,
    onEditRelationship,
    onDeleteRelationship,
    onCancelEdit,
    expandedChapters,
    setExpandedChapters,
    editingChapter,
    setEditingChapter,
    savingChapter,
    showAddChapter,
    setShowAddChapter,
    deletingChapter,
    onAddChapter,
    onEditChapter,
    onDeleteChapter,
    interactions,
    loadingInteractions,
    interactionsExpanded,
    setInteractionsExpanded,
    interactionsViewMode,
    setInteractionsViewMode,
    interactionExpandedChapters,
    toggleInteractionChapter,
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
    reassessing,
    onReassessRelationship,
}: OneToOneViewProps) {
    return (
        <div className="flex-1 overflow-y-auto space-y-4">
            {/* Character Selector */}
            <div className="space-y-2">
                <Label>Select Character</Label>
                <Select
                    value={
                        selectedRelationship
                            ? selectedRelationship.source === entity.name
                                ? selectedRelationship.target
                                : selectedRelationship.source
                            : ""
                    }
                    onValueChange={(characterName) => {
                        const rel = getRelationshipWith(characterName);
                        if (rel) {
                            onSelectRelationship(rel);
                        } else {
                            setSelectedRelationship(null);
                        }
                    }}
                >
                    <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select a character..." />
                    </SelectTrigger>
                    <SelectContent>
                        {allCharacters.map((char) => (
                            <SelectItem key={char} value={char}>
                                {char}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>

            {selectedRelationship ? (
                <>
                    {isEditing ? (
                        <EditMode
                            selectedRelationship={selectedRelationship}
                            editedType={editedType}
                            setEditedType={setEditedType}
                            useCustomType={useCustomType}
                            setUseCustomType={setUseCustomType}
                            customType={customType}
                            setCustomType={setCustomType}
                            useCustomTone={useCustomTone}
                            setUseCustomTone={setUseCustomTone}
                            customTone={customTone}
                            setCustomTone={setCustomTone}
                            context={context}
                            setContext={setContext}
                            emotionalTone={emotionalTone}
                            setEmotionalTone={setEmotionalTone}
                            sentimentScore={sentimentScore}
                            setSentimentScore={setSentimentScore}
                            editedProperties={editedProperties}
                            setEditedProperties={setEditedProperties}
                            newPropertyKey={newPropertyKey}
                            setNewPropertyKey={setNewPropertyKey}
                            newPropertyValue={newPropertyValue}
                            setNewPropertyValue={setNewPropertyValue}
                            saving={saving}
                            onAddProperty={onAddProperty}
                            onEditRelationship={onEditRelationship}
                            onCancelEdit={onCancelEdit}
                        />
                    ) : (
                        <ViewMode
                            entity={entity}
                            selectedRelationship={selectedRelationship}
                            setIsEditing={setIsEditing}
                            onDeleteRelationship={onDeleteRelationship}
                            expandedChapters={expandedChapters}
                            setExpandedChapters={setExpandedChapters}
                            editingChapter={editingChapter}
                            setEditingChapter={setEditingChapter}
                            savingChapter={savingChapter}
                            showAddChapter={showAddChapter}
                            setShowAddChapter={setShowAddChapter}
                            deletingChapter={deletingChapter}
                            onAddChapter={onAddChapter}
                            onEditChapter={onEditChapter}
                            onDeleteChapter={onDeleteChapter}
                            interactions={interactions}
                            loadingInteractions={loadingInteractions}
                            interactionsExpanded={interactionsExpanded}
                            setInteractionsExpanded={setInteractionsExpanded}
                            interactionsViewMode={interactionsViewMode}
                            setInteractionsViewMode={setInteractionsViewMode}
                            interactionExpandedChapters={interactionExpandedChapters}
                            toggleInteractionChapter={toggleInteractionChapter}
                            sentimentBreakdown={sentimentBreakdown}
                            clampedTotalSentiment={clampedTotalSentiment}
                            rawTotalSentiment={rawTotalSentiment}
                            interactionsByChapter={interactionsByChapter}
                            showCreateInteraction={showCreateInteraction}
                            setShowCreateInteraction={setShowCreateInteraction}
                            creatingInteraction={creatingInteraction}
                            newInteraction={newInteraction}
                            setNewInteraction={setNewInteraction}
                            onCreateInteraction={onCreateInteraction}
                            editingInteraction={editingInteraction}
                            setEditingInteraction={setEditingInteraction}
                            savingInteraction={savingInteraction}
                            onUpdateInteraction={onUpdateInteraction}
                            deletingInteraction={deletingInteraction}
                            onDeleteInteraction={onDeleteInteraction}
                            reassessing={reassessing}
                            onReassessRelationship={onReassessRelationship}
                        />
                    )}
                </>
            ) : (
                <div className="text-center py-8 text-gray-500">
                    Select a character to view relationship details.
                </div>
            )}
        </div>
    );
}

// Edit Mode Component
function EditMode({
    selectedRelationship,
    editedType,
    setEditedType,
    useCustomType,
    setUseCustomType,
    customType,
    setCustomType,
    useCustomTone,
    setUseCustomTone,
    customTone,
    setCustomTone,
    context,
    setContext,
    emotionalTone,
    setEmotionalTone,
    sentimentScore,
    setSentimentScore,
    editedProperties,
    setEditedProperties,
    newPropertyKey,
    setNewPropertyKey,
    newPropertyValue,
    setNewPropertyValue,
    saving,
    onAddProperty,
    onEditRelationship,
    onCancelEdit,
}: {
    selectedRelationship: Relationship;
    editedType: string;
    setEditedType: (type: string) => void;
    useCustomType: boolean;
    setUseCustomType: (use: boolean) => void;
    customType: string;
    setCustomType: (type: string) => void;
    useCustomTone: boolean;
    setUseCustomTone: (use: boolean) => void;
    customTone: string;
    setCustomTone: (tone: string) => void;
    context: string;
    setContext: (context: string) => void;
    emotionalTone: string;
    setEmotionalTone: (tone: string) => void;
    sentimentScore: number | "";
    setSentimentScore: (score: number | "") => void;
    editedProperties: Record<string, any>;
    setEditedProperties: (props: Record<string, any>) => void;
    newPropertyKey: string;
    setNewPropertyKey: (key: string) => void;
    newPropertyValue: string;
    setNewPropertyValue: (value: string) => void;
    saving: boolean;
    onAddProperty: () => void;
    onEditRelationship: () => void;
    onCancelEdit: () => void;
}) {
    return (
        <div className="space-y-4 border rounded-lg p-4">
            <div className="space-y-2">
                <Label>Relationship Type</Label>
                <div className="space-y-2">
                    <div className="flex items-center gap-2">
                        <input
                            type="checkbox"
                            id="useCustomRelType"
                            checked={useCustomType}
                            onChange={(e) => setUseCustomType(e.target.checked)}
                            className="rounded"
                        />
                        <Label
                            htmlFor="useCustomRelType"
                            className="text-sm font-normal"
                        >
                            Use custom relationship type
                        </Label>
                    </div>

                    {useCustomType ? (
                        <Input
                            value={customType}
                            onChange={(e) => setCustomType(e.target.value)}
                            placeholder="e.g., ALLIED_WITH, RIVAL_OF"
                        />
                    ) : (
                        <Select value={editedType} onValueChange={setEditedType}>
                            <SelectTrigger className="w-full">
                                <SelectValue placeholder="Select relationship type" />
                            </SelectTrigger>
                            <SelectContent>
                                {STANDARD_RELATIONSHIP_TYPES.map((type) => (
                                    <SelectItem key={type} value={type}>
                                        {type.replace("_", " ")}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    )}
                </div>
            </div>

            {/* Context Field */}
            <div className="space-y-2">
                <div className="space-y-1">
                    <Label htmlFor="context">Context</Label>
                    <p className="text-xs text-gray-500">
                        How they interact or the reason for this relationship
                    </p>
                </div>
                <Textarea
                    id="context"
                    value={context}
                    onChange={(e) => setContext(e.target.value)}
                    placeholder="Describe the context of this relationship..."
                    className="min-h-20"
                />
            </div>

            {/* Emotional Tone Field */}
            <div className="space-y-2">
                <Label htmlFor="emotional-tone">Emotional Tone</Label>
                <div className="space-y-2">
                    <div className="flex items-center gap-2">
                        <input
                            type="checkbox"
                            id="useCustomTone"
                            checked={useCustomTone}
                            onChange={(e) => setUseCustomTone(e.target.checked)}
                            className="rounded"
                        />
                        <Label
                            htmlFor="useCustomTone"
                            className="text-sm font-normal"
                        >
                            Use custom emotional tone
                        </Label>
                    </div>

                    {useCustomTone ? (
                        <Input
                            value={customTone}
                            onChange={(e) => setCustomTone(e.target.value)}
                            placeholder="e.g., Protective, Brotherly, Tense..."
                        />
                    ) : (
                        <Select
                            value={emotionalTone}
                            onValueChange={setEmotionalTone}
                        >
                            <SelectTrigger id="emotional-tone" className="w-full">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {STANDARD_EMOTIONAL_TONES.map((tone) => (
                                    <SelectItem key={tone} value={tone}>
                                        {tone.charAt(0).toUpperCase() +
                                            tone.slice(1)}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    )}
                </div>
            </div>

            {/* Sentiment Score Field */}
            <div className="space-y-2">
                <div className="space-y-1">
                    <Label htmlFor="sentiment-score">Sentiment Score</Label>
                    <p className="text-xs text-gray-500">
                        Relationship sentiment from -100 (very negative) to +100
                        (very positive)
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Input
                        id="sentiment-score"
                        type="number"
                        min="-100"
                        max="100"
                        value={sentimentScore}
                        onChange={(e) => {
                            const val =
                                e.target.value === ""
                                    ? ""
                                    : parseInt(e.target.value, 10);
                            setSentimentScore(val);
                        }}
                        placeholder="0"
                        className="w-24"
                    />
                    <div className="flex-1">
                        <input
                            type="range"
                            min="-100"
                            max="100"
                            value={sentimentScore === "" ? 0 : sentimentScore}
                            onChange={(e) =>
                                setSentimentScore(parseInt(e.target.value, 10))
                            }
                            className="w-full"
                        />
                    </div>
                    <span
                        className={`text-sm font-medium w-8 text-right ${
                            (sentimentScore === "" ? 0 : sentimentScore) < 0
                                ? "text-red-600"
                                : (sentimentScore === "" ? 0 : sentimentScore) > 0
                                ? "text-green-600"
                                : "text-gray-600"
                        }`}
                    >
                        {sentimentScore === "" ? 0 : sentimentScore}
                    </span>
                </div>
            </div>

            <div className="space-y-2">
                <div className="space-y-1">
                    <Label>Properties</Label>
                    <p className="text-xs text-gray-500">
                        Add custom properties to store additional information.
                    </p>
                </div>
                <div className="space-y-2">
                    {Object.entries(editedProperties).map(([key, value]) => (
                        <div
                            key={key}
                            className="flex items-center gap-2 p-2 bg-gray-50 rounded"
                        >
                            <span className="font-medium text-sm flex-1">
                                {key}: {String(value)}
                            </span>
                            <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                    const newProps = { ...editedProperties };
                                    delete newProps[key];
                                    setEditedProperties(newProps);
                                }}
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        </div>
                    ))}

                    {/* Add Property Inputs */}
                    <div className="flex gap-2 pt-2 border-t">
                        <Input
                            placeholder="Property name"
                            value={newPropertyKey}
                            onChange={(e) => setNewPropertyKey(e.target.value)}
                            onKeyPress={(e) => {
                                if (e.key === "Enter") {
                                    e.preventDefault();
                                    onAddProperty();
                                }
                            }}
                        />
                        <Input
                            placeholder="Property value"
                            value={newPropertyValue}
                            onChange={(e) => setNewPropertyValue(e.target.value)}
                            onKeyPress={(e) => {
                                if (e.key === "Enter") {
                                    e.preventDefault();
                                    onAddProperty();
                                }
                            }}
                        />
                        <Button
                            type="button"
                            variant="outline"
                            onClick={onAddProperty}
                        >
                            <Plus className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
                <Button variant="outline" onClick={onCancelEdit}>
                    Cancel
                </Button>
                <Button onClick={onEditRelationship} disabled={saving}>
                    {saving ? "Saving..." : "Save Changes"}
                </Button>
            </div>
        </div>
    );
}

// View Mode Component
function ViewMode({
    entity,
    selectedRelationship,
    setIsEditing,
    onDeleteRelationship,
    expandedChapters,
    setExpandedChapters,
    editingChapter,
    setEditingChapter,
    savingChapter,
    showAddChapter,
    setShowAddChapter,
    deletingChapter,
    onAddChapter,
    onEditChapter,
    onDeleteChapter,
    interactions,
    loadingInteractions,
    interactionsExpanded,
    setInteractionsExpanded,
    interactionsViewMode,
    setInteractionsViewMode,
    interactionExpandedChapters,
    toggleInteractionChapter,
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
    reassessing,
    onReassessRelationship,
}: {
    entity: Entity;
    selectedRelationship: Relationship;
    setIsEditing: (editing: boolean) => void;
    onDeleteRelationship: (edgeId: any) => void;
    expandedChapters: Set<number>;
    setExpandedChapters: (chapters: Set<number>) => void;
    editingChapter: ChapterAnalysis | null;
    setEditingChapter: (chapter: ChapterAnalysis | null) => void;
    savingChapter: boolean;
    showAddChapter: boolean;
    setShowAddChapter: (show: boolean) => void;
    deletingChapter: number | null;
    onAddChapter: (chapter: ChapterAnalysis) => void;
    onEditChapter: (chapter: ChapterAnalysis) => void;
    onDeleteChapter: (chapterNumber: number) => void;
    interactions: Interaction[];
    loadingInteractions: boolean;
    interactionsExpanded: boolean;
    setInteractionsExpanded: (expanded: boolean) => void;
    interactionsViewMode: InteractionsViewMode;
    setInteractionsViewMode: (mode: InteractionsViewMode) => void;
    interactionExpandedChapters: Set<number>;
    toggleInteractionChapter: (chapterNum: number) => void;
    sentimentBreakdown: SentimentBreakdownItem[];
    clampedTotalSentiment: number;
    rawTotalSentiment: number;
    interactionsByChapter: [number, Interaction[]][];
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
    editingInteraction: Interaction | null;
    setEditingInteraction: (interaction: Interaction | null) => void;
    savingInteraction: boolean;
    onUpdateInteraction: () => void;
    deletingInteraction: string | null;
    onDeleteInteraction: (vertexId: string) => void;
    reassessing: boolean;
    onReassessRelationship: () => void;
}) {
    const props = selectedRelationship.properties || {};
    const hasDeconstructorProps =
        props.context || props.emotional_tone || props.sentiment_score !== undefined;

    // Parse chapter analyses
    let chapters: ChapterAnalysis[] = [];
    if (props.chapter_analyses) {
        try {
            chapters =
                typeof props.chapter_analyses === "string"
                    ? JSON.parse(props.chapter_analyses)
                    : Array.isArray(props.chapter_analyses)
                    ? props.chapter_analyses
                    : [];
        } catch (e) {
            chapters = [];
        }
    }

    return (
        <div className="border rounded-lg p-4 space-y-4">
            <div className="space-y-2">
                <Label>Relationship</Label>
                <div className="p-3 bg-gray-50 rounded">
                    <div className="flex items-center gap-2">
                        <span className="font-medium">
                            {selectedRelationship.source === entity.name
                                ? entity.name
                                : selectedRelationship.source}
                        </span>
                        <span className="text-gray-400">→</span>
                        <span className="font-medium">
                            {selectedRelationship.target === entity.name
                                ? entity.name
                                : selectedRelationship.target}
                        </span>
                    </div>
                    <p className="text-sm text-gray-600 mt-2">
                        Type: {selectedRelationship.relationship_type.replace("_", " ")}
                    </p>
                </div>
            </div>

            {/* Display Context, Emotional Tone, and Sentiment Score */}
            {hasDeconstructorProps && (
                <div className="space-y-3">
                    {props.context && (
                        <div className="space-y-2">
                            <Label>Context</Label>
                            <p className="text-sm text-gray-700 p-2 bg-blue-50 rounded">
                                {props.context}
                            </p>
                        </div>
                    )}

                    <div className="flex gap-4">
                        {props.emotional_tone && (
                            <div className="flex-1">
                                <Label>Emotional Tone</Label>
                                <p className="text-sm text-gray-700 mt-1 capitalize">
                                    {props.emotional_tone}
                                </p>
                            </div>
                        )}

                        {props.sentiment_score !== undefined && (
                            <div className="flex-1">
                                <Label>Sentiment Score</Label>
                                <p
                                    className={`text-sm font-semibold mt-1 ${
                                        props.sentiment_score < 0
                                            ? "text-red-600"
                                            : props.sentiment_score > 0
                                            ? "text-green-600"
                                            : "text-gray-600"
                                    }`}
                                >
                                    {props.sentiment_score > 0 ? "+" : ""}
                                    {props.sentiment_score}
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* V2 Chapter-by-Chapter Analysis */}
            {chapters.length > 0 && (
                <ChapterAnalysisSection
                    selectedRelationship={selectedRelationship}
                    chapters={chapters}
                    expandedChapters={expandedChapters}
                    setExpandedChapters={setExpandedChapters}
                    editingChapter={editingChapter}
                    setEditingChapter={setEditingChapter}
                    savingChapter={savingChapter}
                    showAddChapter={showAddChapter}
                    setShowAddChapter={setShowAddChapter}
                    deletingChapter={deletingChapter}
                    onAddChapter={onAddChapter}
                    onEditChapter={onEditChapter}
                    onDeleteChapter={onDeleteChapter}
                />
            )}

            {/* Interactions Section */}
            <InteractionsSection
                selectedRelationship={selectedRelationship}
                interactions={interactions}
                loadingInteractions={loadingInteractions}
                interactionsExpanded={interactionsExpanded}
                setInteractionsExpanded={setInteractionsExpanded}
                interactionsViewMode={interactionsViewMode}
                setInteractionsViewMode={setInteractionsViewMode}
                expandedChapters={interactionExpandedChapters}
                toggleChapter={toggleInteractionChapter}
                sentimentBreakdown={sentimentBreakdown}
                clampedTotalSentiment={clampedTotalSentiment}
                rawTotalSentiment={rawTotalSentiment}
                interactionsByChapter={interactionsByChapter}
                showCreateInteraction={showCreateInteraction}
                setShowCreateInteraction={setShowCreateInteraction}
                creatingInteraction={creatingInteraction}
                newInteraction={newInteraction}
                setNewInteraction={setNewInteraction}
                onCreateInteraction={onCreateInteraction}
                editingInteraction={editingInteraction}
                setEditingInteraction={setEditingInteraction}
                savingInteraction={savingInteraction}
                onUpdateInteraction={onUpdateInteraction}
                deletingInteraction={deletingInteraction}
                onDeleteInteraction={onDeleteInteraction}
            />

            {/* Display other properties */}
            {(() => {
                const otherProps = { ...props };
                delete otherProps.context;
                delete otherProps.emotional_tone;
                delete otherProps.sentiment_score;
                delete otherProps.interaction_count;
                delete otherProps.aggregated_from_interactions;
                delete otherProps.last_updated;
                delete otherProps.analysis_version;
                delete otherProps.chapter_analyses;
                delete otherProps.directional;
                delete otherProps.relationship_progression;
                delete otherProps.overall_summary;

                if (Object.keys(otherProps).length > 0) {
                    return (
                        <div>
                            <Label>Additional Properties</Label>
                            <div className="space-y-2 mt-2">
                                {Object.entries(otherProps).map(([key, value]) => (
                                    <div
                                        key={key}
                                        className="p-2 bg-gray-50 rounded text-sm"
                                    >
                                        <span className="font-medium">{key}:</span>{" "}
                                        <span className="text-gray-600">
                                            {String(value)}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    );
                }
                return null;
            })()}

            <div className="flex gap-2 pt-2">
                <Button
                    variant="outline"
                    onClick={() => setIsEditing(true)}
                    className="flex-1"
                >
                    <Edit className="h-4 w-4 mr-2" />
                    Edit
                </Button>
                <TooltipProvider>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button
                                variant="outline"
                                onClick={onReassessRelationship}
                                disabled={reassessing}
                                className="flex-1"
                            >
                                {reassessing ? (
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                ) : (
                                    <RefreshCw className="h-4 w-4 mr-2" />
                                )}
                                Reassess
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs">
                            <p className="font-semibold">♻️ Reassess Relationship</p>
                            <p className="text-xs text-gray-400 mt-1">
                                Re-run AI analysis for this pair across all chapters.
                            </p>
                            <p className="text-xs text-gray-500 mt-1 italic">
                                Use after adding or editing chapters.
                            </p>
                        </TooltipContent>
                    </Tooltip>
                </TooltipProvider>
                <Button
                    variant="outline"
                    onClick={() =>
                        onDeleteRelationship(selectedRelationship.edge_id)
                    }
                    className="text-red-500 hover:text-red-700"
                >
                    <Trash2 className="h-4 w-4" />
                </Button>
            </div>
        </div>
    );
}

// Chapter Analysis Section Component
function ChapterAnalysisSection({
    selectedRelationship,
    chapters,
    expandedChapters,
    setExpandedChapters,
    editingChapter,
    setEditingChapter,
    savingChapter,
    showAddChapter,
    setShowAddChapter,
    deletingChapter,
    onAddChapter,
    onEditChapter,
    onDeleteChapter,
}: {
    selectedRelationship: Relationship;
    chapters: ChapterAnalysis[];
    expandedChapters: Set<number>;
    setExpandedChapters: (chapters: Set<number>) => void;
    editingChapter: ChapterAnalysis | null;
    setEditingChapter: (chapter: ChapterAnalysis | null) => void;
    savingChapter: boolean;
    showAddChapter: boolean;
    setShowAddChapter: (show: boolean) => void;
    deletingChapter: number | null;
    onAddChapter: (chapter: ChapterAnalysis) => void;
    onEditChapter: (chapter: ChapterAnalysis) => void;
    onDeleteChapter: (chapterNumber: number) => void;
}) {
    const props = selectedRelationship.properties || {};

    return (
        <div className="border rounded-lg overflow-hidden">
            <div className="p-3 bg-linear-to-r from-indigo-50 to-purple-50 border-b">
                <div className="flex items-center justify-between">
                    <div>
                        <Label className="text-sm font-semibold text-indigo-900">
                            Chapter-by-Chapter Analysis
                        </Label>
                        <p className="text-xs text-indigo-600 mt-0.5">
                            How {selectedRelationship.source} →{" "}
                            {selectedRelationship.target} evolves
                        </p>
                    </div>
                    <div className="text-right">
                        <span
                            className={`text-xl font-bold ${
                                (props.sentiment_score || 0) < 0
                                    ? "text-red-600"
                                    : (props.sentiment_score || 0) > 0
                                    ? "text-green-600"
                                    : "text-gray-600"
                            }`}
                        >
                            {(props.sentiment_score || 0) > 0 ? "+" : ""}
                            {props.sentiment_score || 0}
                        </span>
                        <p className="text-[10px] text-gray-500">Overall</p>
                    </div>
                </div>

                {props.relationship_progression && (
                    <p className="text-xs text-indigo-700 mt-2 italic">
                        📈 {props.relationship_progression}
                    </p>
                )}
            </div>

            {/* Chapter list */}
            <div className="divide-y divide-gray-100">
                {chapters.map((ch, idx) => {
                    const isExpanded = expandedChapters.has(ch.chapter_number);
                    const evidence =
                        ch.key_evidence ||
                        (ch.key_moment ? [{ quote: ch.key_moment, context: "" }] : []);
                    const isDeleting = deletingChapter === ch.chapter_number;

                    return (
                        <div key={idx} className="border-b border-gray-100 last:border-0">
                            <div className="p-2 hover:bg-gray-50 transition-colors">
                                <div className="flex items-start gap-2">
                                    <button
                                        onClick={() => {
                                            const newExpanded = new Set(expandedChapters);
                                            if (isExpanded) {
                                                newExpanded.delete(ch.chapter_number);
                                            } else {
                                                newExpanded.add(ch.chapter_number);
                                            }
                                            setExpandedChapters(newExpanded);
                                        }}
                                        className="mt-1 shrink-0"
                                    >
                                        {isExpanded ? (
                                            <ChevronDown className="h-4 w-4 text-gray-400" />
                                        ) : (
                                            <ChevronRight className="h-4 w-4 text-gray-400" />
                                        )}
                                    </button>

                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span className="font-medium text-sm">
                                                {ch.chapter_name}
                                            </span>
                                            <span
                                                className={`text-xs px-1.5 py-0.5 rounded font-semibold ${
                                                    ch.sentiment_score < -20
                                                        ? "bg-red-100 text-red-700"
                                                        : ch.sentiment_score < 0
                                                        ? "bg-orange-100 text-orange-700"
                                                        : ch.sentiment_score < 20
                                                        ? "bg-gray-100 text-gray-700"
                                                        : ch.sentiment_score < 50
                                                        ? "bg-green-100 text-green-700"
                                                        : "bg-emerald-100 text-emerald-700"
                                                }`}
                                            >
                                                {ch.sentiment_score > 0 ? "+" : ""}
                                                {ch.sentiment_score}
                                            </span>
                                        </div>

                                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                                            <span className="text-xs text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded">
                                                {ch.emotional_tone}
                                            </span>
                                            <span className="text-[10px] text-gray-400 uppercase">
                                                {ch.relationship_type}
                                            </span>
                                        </div>

                                        {!isExpanded && ch.summary && (
                                            <p className="text-xs text-gray-500 mt-1 line-clamp-1">
                                                {ch.summary}
                                            </p>
                                        )}
                                    </div>

                                    <div className="flex items-center gap-0.5 shrink-0">
                                        <button
                                            onClick={() => setEditingChapter(ch)}
                                            className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                                            title="Edit Chapter Analysis"
                                        >
                                            <Edit className="h-4 w-4" />
                                        </button>
                                        <button
                                            onClick={() => onDeleteChapter(ch.chapter_number)}
                                            disabled={isDeleting}
                                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                                            title="Delete Chapter Analysis"
                                        >
                                            {isDeleting ? (
                                                <Loader2 className="h-4 w-4 animate-spin" />
                                            ) : (
                                                <Trash2 className="h-4 w-4" />
                                            )}
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {isExpanded && (
                                <div className="px-3 pb-3 ml-6 space-y-3 border-l-2 border-indigo-200 bg-gray-50/50">
                                    <div>
                                        <p className="text-xs font-medium text-gray-700 mb-1">
                                            Summary
                                        </p>
                                        <p className="text-sm text-gray-600 leading-relaxed">
                                            {ch.summary}
                                        </p>
                                    </div>

                                    {evidence.length > 0 && (
                                        <div>
                                            <p className="text-xs font-medium text-gray-700 mb-2">
                                                Key Evidence ({evidence.length} quotes)
                                            </p>
                                            <div className="space-y-2">
                                                {evidence.map((ev, evIdx) => (
                                                    <div
                                                        key={evIdx}
                                                        className="bg-white rounded p-2 border border-gray-100"
                                                    >
                                                        <p className="text-xs text-gray-700 italic">
                                                            "{ev.quote}"
                                                        </p>
                                                        {ev.context && (
                                                            <p className="text-[10px] text-gray-500 mt-1">
                                                                → {ev.context}
                                                            </p>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Add Chapter Form */}
            {showAddChapter && (
                <AddChapterForm
                    chapters={chapters}
                    selectedRelationship={selectedRelationship}
                    savingChapter={savingChapter}
                    onAddChapter={onAddChapter}
                    onClose={() => setShowAddChapter(false)}
                />
            )}

            {/* Edit Chapter Form */}
            {editingChapter && (
                <EditChapterForm
                    editingChapter={editingChapter}
                    setEditingChapter={setEditingChapter}
                    savingChapter={savingChapter}
                    onEditChapter={onEditChapter}
                />
            )}

            {/* Add Chapter Button */}
            {!showAddChapter && !editingChapter && (
                <div className="p-2 border-t">
                    <button
                        onClick={() => setShowAddChapter(true)}
                        className="w-full py-2 px-3 text-sm text-indigo-600 hover:bg-indigo-50 rounded-lg border border-dashed border-indigo-200 flex items-center justify-center gap-2 transition-colors"
                    >
                        <Plus className="h-4 w-4" />
                        Add Chapter Analysis
                    </button>
                </div>
            )}
        </div>
    );
}

function AddChapterForm({
    chapters,
    selectedRelationship,
    savingChapter,
    onAddChapter,
    onClose,
}: {
    chapters: ChapterAnalysis[];
    selectedRelationship: Relationship;
    savingChapter: boolean;
    onAddChapter: (chapter: ChapterAnalysis) => void;
    onClose: () => void;
}) {
    return (
        <div className="p-3 bg-blue-50 border-t space-y-3">
            <div className="flex items-center justify-between">
                <span className="font-medium text-sm text-blue-800">
                    Add Chapter Analysis
                </span>
                <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
                    <X className="h-4 w-4" />
                </button>
            </div>
            <div className="grid grid-cols-2 gap-2">
                <div>
                    <label className="text-xs text-gray-600">Chapter Number</label>
                    <Input
                        type="number"
                        min="1"
                        defaultValue={chapters.length + 1}
                        id="new-chapter-number"
                        className="h-8 text-sm"
                    />
                </div>
                <div>
                    <label className="text-xs text-gray-600">Sentiment Score</label>
                    <Input
                        type="number"
                        min="-100"
                        max="100"
                        defaultValue="0"
                        id="new-chapter-score"
                        className="h-8 text-sm"
                    />
                </div>
            </div>
            <div>
                <label className="text-xs text-gray-600">Emotional Tone</label>
                <Input
                    placeholder="e.g., Protective, Tense, Warm..."
                    id="new-chapter-tone"
                    className="h-8 text-sm"
                />
            </div>
            <div>
                <label className="text-xs text-gray-600">Summary</label>
                <Textarea
                    placeholder="Describe how the source character engages with the target in this chapter..."
                    id="new-chapter-summary"
                    rows={3}
                    className="text-sm"
                />
            </div>
            <Button
                size="sm"
                onClick={async () => {
                    const chNum = parseInt(
                        (document.getElementById("new-chapter-number") as HTMLInputElement)
                            ?.value || "1"
                    );
                    const score = parseInt(
                        (document.getElementById("new-chapter-score") as HTMLInputElement)
                            ?.value || "0"
                    );
                    const tone =
                        (document.getElementById("new-chapter-tone") as HTMLInputElement)
                            ?.value || "neutral";
                    const summary =
                        (
                            document.getElementById(
                                "new-chapter-summary"
                            ) as HTMLTextAreaElement
                        )?.value || "";

                    const newCh: ChapterAnalysis = {
                        chapter_number: chNum,
                        chapter_name: `Chapter ${chNum}`,
                        sentiment_score: Math.max(-100, Math.min(100, score)),
                        relationship_type:
                            selectedRelationship?.properties?.relationship_type ||
                            "INTERACTS_WITH",
                        emotional_tone: tone,
                        summary: summary,
                        key_evidence: [],
                    };

                    await onAddChapter(newCh);
                }}
                disabled={savingChapter}
                className="w-full"
            >
                {savingChapter ? (
                    <>
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        Saving...
                    </>
                ) : (
                    "Add Chapter"
                )}
            </Button>
        </div>
    );
}

function EditChapterForm({
    editingChapter,
    setEditingChapter,
    savingChapter,
    onEditChapter,
}: {
    editingChapter: ChapterAnalysis;
    setEditingChapter: (chapter: ChapterAnalysis | null) => void;
    savingChapter: boolean;
    onEditChapter: (chapter: ChapterAnalysis) => void;
}) {
    return (
        <div className="p-3 bg-amber-50 border-t space-y-3">
            <div className="flex items-center justify-between">
                <span className="font-medium text-sm text-amber-800">
                    Edit {editingChapter.chapter_name}
                </span>
                <button
                    onClick={() => setEditingChapter(null)}
                    className="text-gray-500 hover:text-gray-700"
                >
                    <X className="h-4 w-4" />
                </button>
            </div>
            <div className="grid grid-cols-2 gap-2">
                <div>
                    <label className="text-xs text-gray-600">Chapter Number</label>
                    <Input
                        type="number"
                        value={editingChapter.chapter_number}
                        onChange={(e) =>
                            setEditingChapter({
                                ...editingChapter,
                                chapter_number: parseInt(e.target.value) || 1,
                                chapter_name: `Chapter ${e.target.value || 1}`,
                            })
                        }
                        className="h-8 text-sm"
                    />
                </div>
                <div>
                    <label className="text-xs text-gray-600">Sentiment Score</label>
                    <Input
                        type="number"
                        min="-100"
                        max="100"
                        value={editingChapter.sentiment_score}
                        onChange={(e) =>
                            setEditingChapter({
                                ...editingChapter,
                                sentiment_score: Math.max(
                                    -100,
                                    Math.min(100, parseInt(e.target.value) || 0)
                                ),
                            })
                        }
                        className="h-8 text-sm"
                    />
                </div>
            </div>
            <div>
                <label className="text-xs text-gray-600">Emotional Tone</label>
                <Input
                    value={editingChapter.emotional_tone}
                    onChange={(e) =>
                        setEditingChapter({
                            ...editingChapter,
                            emotional_tone: e.target.value,
                        })
                    }
                    className="h-8 text-sm"
                />
            </div>
            <div>
                <label className="text-xs text-gray-600">Summary</label>
                <Textarea
                    value={editingChapter.summary}
                    onChange={(e) =>
                        setEditingChapter({
                            ...editingChapter,
                            summary: e.target.value,
                        })
                    }
                    rows={3}
                    className="text-sm"
                />
            </div>
            <div className="flex gap-2">
                <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setEditingChapter(null)}
                    className="flex-1"
                >
                    Cancel
                </Button>
                <Button
                    size="sm"
                    onClick={() => onEditChapter(editingChapter)}
                    disabled={savingChapter}
                    className="flex-1"
                >
                    {savingChapter ? (
                        <>
                            <Loader2 className="h-4 w-4 animate-spin mr-2" />
                            Saving...
                        </>
                    ) : (
                        "Save Changes"
                    )}
                </Button>
            </div>
        </div>
    );
}

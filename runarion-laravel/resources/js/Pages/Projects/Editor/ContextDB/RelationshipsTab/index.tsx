import { useState, useMemo, useEffect } from "react";
import { Button } from "@/Components/ui/button";
import { CheckSquare, Square, Plus, Trash2, Loader2 } from "lucide-react";
import type {
    RelationshipsTabProps,
    Relationship,
    Interaction,
    EmotionalTone,
    ChapterAnalysis,
    SentimentBreakdownItem,
    ViewMode,
    SortBy,
    FilterBy,
    InteractionsViewMode,
} from "./types";
import {
    STANDARD_RELATIONSHIP_TYPES,
    STANDARD_EMOTIONAL_TONES,
} from "./constants";
import EmotionalTonesManager from "./Components/EmotionalTonesManager";
import AllRelationshipsView from "./Components/AllRelationshipsView";
import OneToOneView from "./Components/OneToOneView";
import { http } from "@/Lib/http";
import { toast } from "sonner";
import { useConfirm } from "@/Components/ConfirmDialogProvider";

export default function RelationshipsTab({
    entity,
    entityRelationships,
    allRelationships,
    allEntities = [],
    workspaceId,
    projectId,
    onRelationshipCreated,
    onRelationshipDeleted,
    onRelationshipUpdated,
    onSavingChange,
}: RelationshipsTabProps) {
    const confirm = useConfirm();
    // View state
    const [viewMode, setViewMode] = useState<ViewMode>("all");
    const [selectedRelationship, setSelectedRelationship] =
        useState<Relationship | null>(null);
    const [sortBy, setSortBy] = useState<SortBy>("name");
    const [filterBy, setFilterBy] = useState<FilterBy>("all");
    const [searchQuery, setSearchQuery] = useState("");

    // Edit state
    const [isEditing, setIsEditing] = useState(false);
    const [editedType, setEditedType] = useState("");
    const [useCustomType, setUseCustomType] = useState(false);
    const [customType, setCustomType] = useState("");
    const [useCustomTone, setUseCustomTone] = useState(false);
    const [customTone, setCustomTone] = useState("");
    const [editedProperties, setEditedProperties] = useState<
        Record<string, any>
    >({});
    const [newPropertyKey, setNewPropertyKey] = useState("");
    const [newPropertyValue, setNewPropertyValue] = useState("");
    const [saving, setSaving] = useState(false);

    // Dedicated fields for deconstructor properties
    const [context, setContext] = useState("");
    const [emotionalTone, setEmotionalTone] = useState("neutral");
    const [sentimentScore, setSentimentScore] = useState<number | "">(0);

    // Multi-select mode
    const [multiSelectMode, setMultiSelectMode] = useState(false);
    const [selectedEdgeIds, setSelectedEdgeIds] = useState<Set<string>>(
        new Set(),
    );
    const [deletingMultiple, setDeletingMultiple] = useState(false);

    // Interactions for CK3-style breakdown
    const [interactions, setInteractions] = useState<Interaction[]>([]);
    const [loadingInteractions, setLoadingInteractions] = useState(false);
    const [interactionsExpanded, setInteractionsExpanded] = useState(false);
    const [interactionsViewMode, setInteractionsViewMode] =
        useState<InteractionsViewMode>("all");
    const [expandedChapters, setExpandedChapters] = useState<Set<number>>(
        new Set(),
    );
    const [deletingInteraction, setDeletingInteraction] = useState<
        string | null
    >(null);
    const [showCreateInteraction, setShowCreateInteraction] = useState(false);
    const [creatingInteraction, setCreatingInteraction] = useState(false);
    const [newInteraction, setNewInteraction] = useState({
        interaction_type: "INTERACTS_WITH",
        emotional_tone: "neutral",
        chapter_number: 0,
        context: "",
        text_evidence: "",
    });
    const [editingInteraction, setEditingInteraction] =
        useState<Interaction | null>(null);
    const [savingInteraction, setSavingInteraction] = useState(false);

    // Chapter Analysis Editing
    const [editingChapter, setEditingChapter] =
        useState<ChapterAnalysis | null>(null);
    const [savingChapter, setSavingChapter] = useState(false);
    const [showAddChapter, setShowAddChapter] = useState(false);
    const [deletingChapter, setDeletingChapter] = useState<number | null>(null);

    // Emotional Tones Management
    const [emotionalTones, setEmotionalTones] = useState<EmotionalTone[]>([]);
    const [loadingTones, setLoadingTones] = useState(false);
    const [showTonesManager, setShowTonesManager] = useState(false);
    const [newToneName, setNewToneName] = useState("");
    const [creatingTone, setCreatingTone] = useState(false);
    const [deletingTone, setDeletingTone] = useState<number | null>(null);

    // Reassess relationship
    const [reassessing, setReassessing] = useState(false);

    // Get unique relationship types for filter
    const relationshipTypes = useMemo(() => {
        const types = new Set<string>();
        entityRelationships.forEach((rel) => {
            types.add(rel.relationship_type);
        });
        return Array.from(types).sort();
    }, [entityRelationships]);

    // Filter and sort relationships
    const filteredAndSorted = useMemo(() => {
        let filtered = [...entityRelationships];

        if (filterBy !== "all") {
            filtered = filtered.filter(
                (rel) => rel.relationship_type === filterBy,
            );
        }

        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            filtered = filtered.filter((rel) => {
                const otherEntity =
                    rel.source === entity.name ? rel.target : rel.source;
                return (
                    otherEntity.toLowerCase().includes(query) ||
                    rel.relationship_type.toLowerCase().includes(query)
                );
            });
        }

        filtered.sort((a, b) => {
            const aOther = a.source === entity.name ? a.target : a.source;
            const bOther = b.source === entity.name ? b.target : b.source;

            switch (sortBy) {
                case "name":
                    return aOther.localeCompare(bOther);
                case "type":
                    return a.relationship_type.localeCompare(
                        b.relationship_type,
                    );
                default:
                    return 0;
            }
        });

        return filtered;
    }, [entityRelationships, filterBy, searchQuery, sortBy, entity.name]);

    const allVisibleSelected =
        filteredAndSorted.length > 0 &&
        filteredAndSorted.every((rel) => selectedEdgeIds.has(rel.edge_id));

    // Get all characters for 1-to-1 view
    const allCharacters = useMemo(() => {
        const chars = new Set<string>();
        allRelationships.forEach((rel) => {
            if (rel.source !== entity.name) chars.add(rel.source);
            if (rel.target !== entity.name) chars.add(rel.target);
        });
        return Array.from(chars).sort();
    }, [allRelationships, entity.name]);

    // Get relationship between this entity and another character
    const getRelationshipWith = (
        characterName: string,
    ): Relationship | null => {
        return (
            entityRelationships.find(
                (rel) =>
                    (rel.source === entity.name &&
                        rel.target === characterName) ||
                    (rel.source === characterName &&
                        rel.target === entity.name),
            ) || null
        );
    };

    const handleSelectRelationship = (rel: Relationship) => {
        setSelectedRelationship(rel);
        setViewMode("one-to-one");
        setIsEditing(false);
        const relType = rel.relationship_type.replace(/"/g, "");
        setEditedType(relType);
        setUseCustomType(!STANDARD_RELATIONSHIP_TYPES.includes(relType));
        setCustomType(relType);

        const props = rel.properties || {};
        const currentTone = props.emotional_tone || "neutral";
        setContext(props.context || "");
        setEmotionalTone(currentTone);
        setUseCustomTone(
            !STANDARD_EMOTIONAL_TONES.includes(currentTone.toLowerCase()),
        );
        setCustomTone(currentTone);
        setSentimentScore(
            props.sentiment_score !== undefined ? props.sentiment_score : 0,
        );

        const otherProps = { ...props };
        delete otherProps.context;
        delete otherProps.emotional_tone;
        delete otherProps.sentiment_score;
        delete otherProps.analysis_version;
        delete otherProps.chapter_analyses;
        delete otherProps.directional;
        delete otherProps.relationship_progression;
        delete otherProps.overall_summary;
        delete otherProps.last_updated;
        delete otherProps.interaction_count;
        delete otherProps.aggregated_from_interactions;
        setEditedProperties(otherProps);
        setNewPropertyKey("");
        setNewPropertyValue("");
    };

    const handleAddProperty = () => {
        if (newPropertyKey.trim()) {
            setEditedProperties({
                ...editedProperties,
                [newPropertyKey]: newPropertyValue || "",
            });
            setNewPropertyKey("");
            setNewPropertyValue("");
        }
    };

    const handleEditRelationship = async () => {
        if (!selectedRelationship) return;

        const finalType = useCustomType ? customType : editedType;
        if (!finalType.trim()) {
            toast.warning("Please enter a relationship type");
            return;
        }

        const finalTone = useCustomTone ? customTone : emotionalTone;
        const allProperties = {
            ...editedProperties,
            context: context,
            emotional_tone: finalTone,
            sentiment_score: sentimentScore === "" ? 0 : sentimentScore,
        };

        setSaving(true);
        onSavingChange?.(true);
        try {
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/records/relationships/${selectedRelationship.edge_id}`,
                {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                    },
                    data: {
                        project_id: projectId,
                        type: finalType,
                        properties: allProperties,
                    },
                },
            );

            if (response.status >= 200 && response.status < 300) {
                setIsEditing(false);
                onRelationshipUpdated();
                const updatedRel = {
                    ...selectedRelationship,
                    relationship_type: finalType,
                    properties: allProperties,
                };
                setSelectedRelationship(updatedRel);
                setContext(allProperties.context || "");
                setEmotionalTone(allProperties.emotional_tone || "neutral");
                setSentimentScore(
                    allProperties.sentiment_score !== undefined
                        ? allProperties.sentiment_score
                        : 0,
                );
            } else {
                let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                try {
                    const error = response.data;
                    errorMessage = error.error || error.message || errorMessage;
                    if (error.details) {
                        errorMessage += `\n\nDetails: ${
                            typeof error.details === "string"
                                ? error.details
                                : JSON.stringify(error.details)
                        }`;
                    }
                } catch (e) {
                    console.error("Error parsing response:", e);
                }
                toast.error(errorMessage);
            }
        } catch (error: any) {
            console.error("Error updating relationship:", error);
            toast.error(
                `Failed to update relationship: ${error?.message || String(error)}`,
            );
        } finally {
            setSaving(false);
            onSavingChange?.(false);
        }
    };

    const handleCancelEdit = () => {
        if (!selectedRelationship) return;
        setIsEditing(false);
        const relType = selectedRelationship.relationship_type.replace(
            /"/g,
            "",
        );
        setEditedType(relType);
        setUseCustomType(!STANDARD_RELATIONSHIP_TYPES.includes(relType));
        setCustomType(relType);

        const props = selectedRelationship.properties || {};
        const currentTone = props.emotional_tone || "neutral";
        setContext(props.context || "");
        setEmotionalTone(currentTone);
        setUseCustomTone(
            !STANDARD_EMOTIONAL_TONES.includes(currentTone.toLowerCase()),
        );
        setCustomTone(currentTone);
        setSentimentScore(
            props.sentiment_score !== undefined ? props.sentiment_score : 0,
        );

        const otherProps = { ...props };
        delete otherProps.context;
        delete otherProps.emotional_tone;
        delete otherProps.sentiment_score;
        delete otherProps.analysis_version;
        delete otherProps.chapter_analyses;
        delete otherProps.directional;
        delete otherProps.relationship_progression;
        delete otherProps.overall_summary;
        delete otherProps.last_updated;
        delete otherProps.interaction_count;
        delete otherProps.aggregated_from_interactions;
        setEditedProperties(otherProps);
    };

    const handleDeleteRelationship = async (edgeId: string | number) => {
        if (
            !(await confirm({
                title: "Delete relationship?",
                description:
                    "Are you sure you want to delete this relationship?",
                actionLabel: "Delete relationship",
            }))
        ) {
            return;
        }

        onSavingChange?.(true);
        try {
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/records/relationships/${edgeId}`,
                {
                    method: "DELETE",
                    headers: {
                        Accept: "application/json",
                    },
                },
            );

            if (response.status >= 200 && response.status < 300) {
                if (selectedRelationship?.edge_id === String(edgeId)) {
                    setSelectedRelationship(null);
                    setViewMode("all");
                }
                onRelationshipDeleted();
            } else {
                let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                try {
                    const error = response.data;
                    errorMessage = error.error || error.message || errorMessage;
                } catch (e) {
                    console.error("Error parsing response:", e);
                }
                toast.error(errorMessage);
            }
        } catch (error: any) {
            console.error("Error deleting relationship:", error);
            toast.error(
                `Failed to delete relationship: ${error?.message || String(error)}`,
            );
        } finally {
            onSavingChange?.(false);
        }
    };

    // Fetch interactions when relationship is selected
    const fetchInteractions = async (
        sourceChar: string,
        targetChar: string,
    ) => {
        setLoadingInteractions(true);
        try {
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/auditor/interactions?source_character=${encodeURIComponent(
                    sourceChar,
                )}&target_character=${encodeURIComponent(targetChar)}`,
                {
                    headers: {
                        Accept: "application/json",
                    },
                },
            );
            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                setInteractions(data.interactions || []);
            } else {
                console.error("Failed to fetch interactions");
                setInteractions([]);
            }
        } catch (error) {
            console.error("Error fetching interactions:", error);
            setInteractions([]);
        } finally {
            setLoadingInteractions(false);
        }
    };

    // Load interactions when relationship changes
    useEffect(() => {
        if (selectedRelationship && viewMode === "one-to-one") {
            fetchInteractions(
                selectedRelationship.source,
                selectedRelationship.target,
            );
        } else {
            setInteractions([]);
        }
    }, [selectedRelationship, viewMode]);

    // Multi-select functions
    const toggleSelectEdge = (edgeId: string) => {
        const newSelected = new Set(selectedEdgeIds);
        if (newSelected.has(edgeId)) {
            newSelected.delete(edgeId);
        } else {
            newSelected.add(edgeId);
        }
        setSelectedEdgeIds(newSelected);
    };

    const selectAllVisible = () => {
        const allIds = new Set(filteredAndSorted.map((rel) => rel.edge_id));
        setSelectedEdgeIds(allIds);
    };

    const deselectAll = () => {
        setSelectedEdgeIds(new Set());
    };

    const handleDeleteMultiple = async () => {
        if (selectedEdgeIds.size === 0) return;
        if (
            !(await confirm({
                title: "Delete selected relationships?",
                description: `Are you sure you want to delete ${selectedEdgeIds.size} relationships?`,
                actionLabel: "Delete relationships",
            }))
        ) {
            return;
        }

        setDeletingMultiple(true);
        onSavingChange?.(true);
        let successCount = 0;
        let errorCount = 0;

        for (const edgeId of selectedEdgeIds) {
            try {
                const response = await http(
                    `/${workspaceId}/projects/${projectId}/editor/records/relationships/${edgeId}`,
                    {
                        method: "DELETE",
                        headers: {
                            Accept: "application/json",
                        },
                    },
                );
                if (response.status >= 200 && response.status < 300) {
                    successCount++;
                } else {
                    errorCount++;
                }
            } catch (error) {
                errorCount++;
            }
        }

        setDeletingMultiple(false);
        onSavingChange?.(false);
        setSelectedEdgeIds(new Set());
        setMultiSelectMode(false);

        if (successCount > 0) {
            onRelationshipDeleted();
        }
        if (errorCount > 0) {
            toast.info(
                `Deleted ${successCount} relationships. ${errorCount} failed.`,
            );
        }
    };

    // Interaction CRUD
    const handleDeleteInteraction = async (vertexId: string) => {
        if (
            !(await confirm({
                title: "Delete interaction?",
                description:
                    "Are you sure you want to delete this interaction?",
                actionLabel: "Delete interaction",
            }))
        ) {
            return;
        }

        setDeletingInteraction(vertexId);
        onSavingChange?.(true);

        try {
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/auditor/interactions/${vertexId}`,
                {
                    method: "DELETE",
                    headers: {
                        Accept: "application/json",
                    },
                },
            );

            if (response.status >= 200 && response.status < 300) {
                setInteractions((prev) =>
                    prev.filter((i) => String(i.vertex_id) !== vertexId),
                );
            } else {
                const error = response.data;
                toast.error(
                    `Failed to delete interaction: ${error.error || "Unknown error"}`,
                );
            }
        } catch (e) {
            console.error("Error deleting interaction:", e);
            toast.error("Failed to delete interaction");
        } finally {
            setDeletingInteraction(null);
            onSavingChange?.(false);
        }
    };

    const handleCreateInteraction = async () => {
        if (!selectedRelationship) return;

        setCreatingInteraction(true);
        onSavingChange?.(true);

        try {
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/auditor/interactions`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                    },
                    data: {
                        source_character: selectedRelationship.source,
                        target_character: selectedRelationship.target,
                        chapter_number: newInteraction.chapter_number,
                        interaction_type: newInteraction.interaction_type,
                        emotional_tone: newInteraction.emotional_tone,
                        context: newInteraction.context,
                        text_evidence: newInteraction.text_evidence,
                    },
                },
            );

            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                setInteractions((prev) => [...prev, data.interaction]);
                setNewInteraction({
                    interaction_type: "INTERACTS_WITH",
                    emotional_tone: "neutral",
                    chapter_number: 0,
                    context: "",
                    text_evidence: "",
                });
                setShowCreateInteraction(false);
            } else {
                const error = response.data;
                toast.error(
                    `Failed to create interaction: ${error.error || "Unknown error"}`,
                );
            }
        } catch (e) {
            console.error("Error creating interaction:", e);
            toast.error("Failed to create interaction");
        } finally {
            setCreatingInteraction(false);
            onSavingChange?.(false);
        }
    };

    const handleUpdateInteraction = async () => {
        if (!editingInteraction?.vertex_id) return;

        setSavingInteraction(true);
        onSavingChange?.(true);

        try {
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/auditor/interactions/${editingInteraction.vertex_id}`,
                {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                    },
                    data: {
                        interaction_type: editingInteraction.interaction_type,
                        emotional_tone: editingInteraction.emotional_tone,
                        sentiment_modifier:
                            editingInteraction.sentiment_modifier,
                        context: editingInteraction.context,
                        text_evidence: editingInteraction.text_evidence,
                    },
                },
            );

            if (response.status >= 200 && response.status < 300) {
                setInteractions((prev) =>
                    prev.map((i) =>
                        String(i.vertex_id) ===
                        String(editingInteraction.vertex_id)
                            ? editingInteraction
                            : i,
                    ),
                );
                setEditingInteraction(null);
            } else {
                const error = response.data;
                toast.error(
                    `Failed to update interaction: ${error.error || "Unknown error"}`,
                );
            }
        } catch (e) {
            console.error("Error updating interaction:", e);
            toast.error("Failed to update interaction");
        } finally {
            setSavingInteraction(false);
            onSavingChange?.(false);
        }
    };

    // Chapter Analysis CRUD
    const handleSaveChapterAnalyses = async (chapters: ChapterAnalysis[]) => {
        if (!selectedRelationship) return;

        setSavingChapter(true);
        onSavingChange?.(true);

        try {
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/auditor/relationships/${selectedRelationship.edge_id}/chapter-analyses`,
                {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                    },
                    data: {
                        project_id: projectId,
                        chapter_analyses: chapters,
                        recalculate_overall: true,
                    },
                },
            );

            if (response.status >= 200 && response.status < 300) {
                if (selectedRelationship.properties) {
                    selectedRelationship.properties.chapter_analyses =
                        JSON.stringify(chapters);
                }
                setEditingChapter(null);
                setShowAddChapter(false);
                onRelationshipUpdated();
            } else {
                const error = response.data;
                toast.error(
                    `Failed to update chapters: ${error.error || "Unknown error"}`,
                );
            }
        } catch (e) {
            console.error("Error updating chapters:", e);
            toast.error("Failed to update chapters");
        } finally {
            setSavingChapter(false);
            onSavingChange?.(false);
        }
    };

    const handleDeleteChapter = async (chapterNumber: number) => {
        if (!selectedRelationship) return;
        if (
            !(await confirm({
                title: "Delete chapter analysis?",
                description:
                    "Are you sure you want to delete this chapter analysis?",
                actionLabel: "Delete analysis",
            }))
        )
            return;

        setDeletingChapter(chapterNumber);

        try {
            const props = selectedRelationship.properties || {};
            let chapters: ChapterAnalysis[] = [];
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

            const updatedChapters = chapters.filter(
                (ch) => ch.chapter_number !== chapterNumber,
            );

            await handleSaveChapterAnalyses(updatedChapters);
        } finally {
            setDeletingChapter(null);
        }
    };

    const handleAddChapter = async (newChapter: ChapterAnalysis) => {
        if (!selectedRelationship) return;

        const props = selectedRelationship.properties || {};
        let chapters: ChapterAnalysis[] = [];
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

        chapters.push(newChapter);
        chapters.sort((a, b) => a.chapter_number - b.chapter_number);

        await handleSaveChapterAnalyses(chapters);
    };

    const handleEditChapter = async (updatedChapter: ChapterAnalysis) => {
        if (!selectedRelationship) return;

        const props = selectedRelationship.properties || {};
        let chapters: ChapterAnalysis[] = [];
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

        const updatedChapters = chapters.map((ch) =>
            ch.chapter_number === updatedChapter.chapter_number
                ? updatedChapter
                : ch,
        );

        await handleSaveChapterAnalyses(updatedChapters);
    };

    // Emotional Tones Management
    const fetchEmotionalTones = async () => {
        setLoadingTones(true);
        try {
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/auditor/emotional-tones`,
                {
                    headers: {
                        Accept: "application/json",
                    },
                },
            );

            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                setEmotionalTones(data.tones || []);
            }
        } catch (e) {
            console.error("Error fetching emotional tones:", e);
        } finally {
            setLoadingTones(false);
        }
    };

    const handleCreateTone = async () => {
        if (!newToneName.trim()) return;

        setCreatingTone(true);
        onSavingChange?.(true);
        try {
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/auditor/emotional-tones`,
                {
                    method: "POST",
                    data: {
                        name: newToneName.trim(),
                    },
                },
            );

            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                setEmotionalTones((prev) => [...prev, data.tone]);
                setNewToneName("");
            } else {
                const error = response.data;
                toast.error(
                    `Failed to create tone: ${error.error || "Unknown error"}`,
                );
            }
        } catch (e) {
            console.error("Error creating emotional tone:", e);
            toast.error("Failed to create emotional tone");
        } finally {
            setCreatingTone(false);
            onSavingChange?.(false);
        }
    };

    const handleDeleteTone = async (toneId: number) => {
        if (
            !(await confirm({
                title: "Delete emotional tone?",
                description:
                    "Are you sure you want to delete this emotional tone?",
                actionLabel: "Delete tone",
            }))
        )
            return;

        setDeletingTone(toneId);
        onSavingChange?.(true);
        try {
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/auditor/emotional-tones/${toneId}`,
                {
                    method: "DELETE",
                    headers: {
                        Accept: "application/json",
                    },
                },
            );

            if (response.status >= 200 && response.status < 300) {
                setEmotionalTones((prev) =>
                    prev.filter((t) => t.id !== toneId),
                );
            } else {
                const error = response.data;
                toast.error(
                    `Failed to delete tone: ${error.error || "Unknown error"}`,
                );
            }
        } catch (e) {
            console.error("Error deleting emotional tone:", e);
            toast.error("Failed to delete emotional tone");
        } finally {
            setDeletingTone(null);
            onSavingChange?.(false);
        }
    };

    // Reassess a relationship
    const handleReassessRelationship = async () => {
        if (!selectedRelationship) return;

        const source = selectedRelationship.source;
        const target = selectedRelationship.target;

        if (
            !(await confirm({
                title: "Reassess relationship?",
                description: `Re-analyze the relationship between ${source} and ${target}?\n\nThis will re-run the AI analysis across all chapters and update the stored data.`,
                actionLabel: "Reassess relationship",
            }))
        ) {
            return;
        }

        setReassessing(true);
        onSavingChange?.(true);

        try {
            const sourceEntity = allEntities?.find(
                (e) =>
                    e.name === source && e.type.toLowerCase() === "character",
            );
            const targetEntity = allEntities?.find(
                (e) =>
                    e.name === target && e.type.toLowerCase() === "character",
            );

            if (!sourceEntity || !targetEntity) {
                toast.info(
                    "Could not find character entities for reassessment.",
                );
                return;
            }

            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/auditor/extract-relationships`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                    },
                    data: {
                        character_ids: [
                            sourceEntity.vertex_id,
                            targetEntity.vertex_id,
                        ],
                        focus_mode: "1-to-1",
                        model: "gemini-2.5-flash",
                        provider: "gemini",
                    },
                },
            );

            if (response.status >= 200 && response.status < 300) {
                toast.success(`Successfully reassessed ${source} ↔ ${target}!`);
                onRelationshipUpdated();
            } else {
                const error = response.data;
                toast.error(
                    `Failed to reassess: ${error.error || "Unknown error"}`,
                );
            }
        } catch (e: any) {
            console.error("Error reassessing relationship:", e);
            toast.error(`Failed to reassess: ${e?.message || String(e)}`);
        } finally {
            setReassessing(false);
            onSavingChange?.(false);
        }
    };

    // Fetch emotional tones when tones manager is opened
    useEffect(() => {
        if (showTonesManager) {
            fetchEmotionalTones();
        }
    }, [showTonesManager]);

    // Calculate CK3-style breakdown from interactions
    const sentimentBreakdown = useMemo<SentimentBreakdownItem[]>(() => {
        if (!interactions.length) return [];

        const typeModifiers: Record<string, number> = {
            SAVES: 30,
            PROTECTS: 25,
            COMFORTS: 20,
            SUPPORTS: 15,
            PRAISES: 15,
            WARNS: 5,
            QUESTIONS: 0,
            ARGUES: -10,
            MOCKS: -15,
            INSULTS: -25,
            THREATENS: -35,
            ATTACKS: -50,
            BETRAYS: -50,
        };

        const toneModifiers: Record<string, number> = {
            affectionate: 10,
            warm: 5,
            friendly: 5,
            cordial: 2,
            neutral: 0,
            cold: -5,
            antagonistic: -10,
            hostile: -15,
        };

        return interactions.map((interaction) => {
            const totalModifier =
                interaction.sentiment_modifier !== undefined
                    ? interaction.sentiment_modifier
                    : (typeModifiers[
                          interaction.interaction_type?.toUpperCase()
                      ] || 0) +
                      (toneModifiers[
                          interaction.emotional_tone?.toLowerCase()
                      ] || 0);

            return {
                label: `${interaction.interaction_type || "INTERACTION"} (${
                    interaction.emotional_tone || "neutral"
                })`,
                value: totalModifier,
                description: interaction.context || interaction.text_evidence,
                chapter: interaction.chapter_number,
                reasoning: interaction.sentiment_reasoning,
            };
        });
    }, [interactions]);

    // Calculate clamped and raw totals
    const clampedTotalSentiment = useMemo(() => {
        const rawTotal = sentimentBreakdown.reduce(
            (sum, item) => sum + item.value,
            0,
        );
        return Math.max(-100, Math.min(100, rawTotal));
    }, [sentimentBreakdown]);

    const rawTotalSentiment = useMemo(() => {
        return sentimentBreakdown.reduce((sum, item) => sum + item.value, 0);
    }, [sentimentBreakdown]);

    // Group interactions by chapter
    const interactionsByChapter = useMemo(() => {
        const grouped: Map<number, Interaction[]> = new Map();

        interactions.forEach((interaction) => {
            const chapter = interaction.chapter_number ?? -1;
            if (!grouped.has(chapter)) {
                grouped.set(chapter, []);
            }
            grouped.get(chapter)!.push(interaction);
        });

        return Array.from(grouped.entries()).sort((a, b) => a[0] - b[0]);
    }, [interactions]);

    // Toggle chapter expansion for interactions
    const toggleInteractionChapter = (chapterNum: number) => {
        setExpandedChapters((prev) => {
            const next = new Set(prev);
            if (next.has(chapterNum)) {
                next.delete(chapterNum);
            } else {
                next.add(chapterNum);
            }
            return next;
        });
    };

    return (
        <div className="space-y-4 h-full flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h3 className="font-semibold">
                    Relationships ({entityRelationships.length})
                </h3>
                <div className="flex gap-2">
                    {viewMode === "all" && (
                        <Button
                            size="sm"
                            className="w-8 p-2"
                            variant={multiSelectMode ? "default" : "outline"}
                            onClick={() => {
                                setMultiSelectMode(!multiSelectMode);
                                if (multiSelectMode) {
                                    setSelectedEdgeIds(new Set());
                                }
                            }}
                        >
                            {multiSelectMode ? (
                                <CheckSquare className="h-4 w-4" />
                            ) : (
                                <Square className="h-4 w-4" />
                            )}
                        </Button>
                    )}
                    <Button size="sm" onClick={onRelationshipCreated}>
                        <Plus className="h-4 w-4" />
                        Add Relationship
                    </Button>
                </div>
            </div>

            {/* Multi-select toolbar */}
            {multiSelectMode && viewMode === "all" && (
                <div className="flex items-center justify-between bg-slate-50 p-2 rounded-md border border-slate-400">
                    <div className="flex items-center gap-2">
                        <span className="text-sm justify-start font-medium">
                            {selectedEdgeIds.size} selected
                        </span>
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={
                                allVisibleSelected
                                    ? deselectAll
                                    : selectAllVisible
                            }
                            className="text-xs p-1.5 h-auto"
                        >
                            {allVisibleSelected ? "Deselect All" : "Select All"}
                        </Button>
                    </div>
                    <Button
                        size="sm"
                        variant="destructive"
                        onClick={handleDeleteMultiple}
                        disabled={
                            selectedEdgeIds.size === 0 || deletingMultiple
                        }
                    >
                        {deletingMultiple ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <Trash2 className="h-4 w-4" />
                        )}
                    </Button>
                </div>
            )}

            {/* View Mode Toggle */}
            <div className="flex gap-2">
                <Button
                    variant={viewMode === "all" ? "default" : "outline"}
                    size="sm"
                    onClick={() => {
                        setViewMode("all");
                        setSelectedRelationship(null);
                    }}
                >
                    All Relationships
                </Button>
                <Button
                    variant={viewMode === "one-to-one" ? "default" : "outline"}
                    size="sm"
                    onClick={() => {
                        setViewMode("one-to-one");
                        if (!selectedRelationship && allCharacters.length > 0) {
                            const firstRel = getRelationshipWith(
                                allCharacters[0],
                            );
                            if (firstRel) {
                                handleSelectRelationship(firstRel);
                            }
                        }
                    }}
                >
                    1-to-1 View
                </Button>

                {/* Emotional Tones Manager Button */}
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowTonesManager(!showTonesManager)}
                    className="ml-auto"
                >
                    Tones
                </Button>
            </div>

            {/* Emotional Tones Manager Panel */}
            {showTonesManager && (
                <EmotionalTonesManager
                    emotionalTones={emotionalTones}
                    loadingTones={loadingTones}
                    newToneName={newToneName}
                    setNewToneName={setNewToneName}
                    creatingTone={creatingTone}
                    deletingTone={deletingTone}
                    onCreateTone={handleCreateTone}
                    onDeleteTone={handleDeleteTone}
                    onClose={() => setShowTonesManager(false)}
                />
            )}

            {viewMode === "all" ? (
                <AllRelationshipsView
                    entity={entity}
                    filteredAndSorted={filteredAndSorted}
                    entityRelationships={entityRelationships}
                    relationshipTypes={relationshipTypes}
                    searchQuery={searchQuery}
                    setSearchQuery={setSearchQuery}
                    filterBy={filterBy}
                    setFilterBy={setFilterBy}
                    sortBy={sortBy}
                    setSortBy={setSortBy}
                    multiSelectMode={multiSelectMode}
                    selectedEdgeIds={selectedEdgeIds}
                    toggleSelectEdge={toggleSelectEdge}
                    onSelectRelationship={handleSelectRelationship}
                    onDeleteRelationship={handleDeleteRelationship}
                />
            ) : (
                <OneToOneView
                    entity={entity}
                    selectedRelationship={selectedRelationship}
                    allCharacters={allCharacters}
                    getRelationshipWith={getRelationshipWith}
                    onSelectRelationship={handleSelectRelationship}
                    setSelectedRelationship={setSelectedRelationship}
                    isEditing={isEditing}
                    setIsEditing={setIsEditing}
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
                    onAddProperty={handleAddProperty}
                    onEditRelationship={handleEditRelationship}
                    onDeleteRelationship={handleDeleteRelationship}
                    onCancelEdit={handleCancelEdit}
                    expandedChapters={expandedChapters}
                    setExpandedChapters={setExpandedChapters}
                    editingChapter={editingChapter}
                    setEditingChapter={setEditingChapter}
                    savingChapter={savingChapter}
                    showAddChapter={showAddChapter}
                    setShowAddChapter={setShowAddChapter}
                    deletingChapter={deletingChapter}
                    onAddChapter={handleAddChapter}
                    onEditChapter={handleEditChapter}
                    onDeleteChapter={handleDeleteChapter}
                    interactions={interactions}
                    loadingInteractions={loadingInteractions}
                    interactionsExpanded={interactionsExpanded}
                    setInteractionsExpanded={setInteractionsExpanded}
                    interactionsViewMode={interactionsViewMode}
                    setInteractionsViewMode={setInteractionsViewMode}
                    interactionExpandedChapters={expandedChapters}
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
                    onCreateInteraction={handleCreateInteraction}
                    editingInteraction={editingInteraction}
                    setEditingInteraction={setEditingInteraction}
                    savingInteraction={savingInteraction}
                    onUpdateInteraction={handleUpdateInteraction}
                    deletingInteraction={deletingInteraction}
                    onDeleteInteraction={handleDeleteInteraction}
                    reassessing={reassessing}
                    onReassessRelationship={handleReassessRelationship}
                />
            )}
        </div>
    );
}

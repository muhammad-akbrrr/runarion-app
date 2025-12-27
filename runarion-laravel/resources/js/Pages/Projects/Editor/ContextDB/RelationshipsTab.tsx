import { useState, useMemo, useEffect } from "react";
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
import { Edit, Trash2, Plus, Search, ArrowUpDown, X, ChevronDown, ChevronRight, CheckSquare, Square, Loader2, Info, RefreshCw } from "lucide-react";
import { Textarea } from "@/Components/ui/textarea";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/Components/ui/tooltip";

// Interaction type with sentiment modifiers (CK3-style)
interface Interaction {
    vertex_id: string;
    source_character: string;
    target_character: string;
    interaction_type: string;
    emotional_tone: string;
    context?: string;
    text_evidence?: string;
    chapter_number?: number;
    sentiment_modifier?: number;
    sentiment_reasoning?: string;  // AI's explanation for the score
    ai_scored?: boolean;  // Whether AI directly scored this
}

// Sentiment breakdown item for CK3-style display
interface SentimentBreakdownItem {
    label: string;
    value: number;
    description?: string;
    chapter?: number;
    reasoning?: string;  // AI reasoning for the score
}

interface Entity {
    vertex_id: string;  // String to avoid JS precision loss with large Apache AGE IDs
    name: string;
    type: string;
    properties: Record<string, any>;
}

// V2 Chapter Analysis structure
interface KeyEvidence {
    quote: string;
    context?: string;
}

interface EmotionalTone {
    id: number;
    name: string;
    is_base: boolean;  // Base tones can't be deleted
    created_at?: string;
}

interface ChapterAnalysis {
    chapter_number: number;
    chapter_name: string;
    sentiment_score: number;
    relationship_type: string;
    emotional_tone: string;
    summary: string;
    key_moment?: string;  // Legacy field
    key_evidence?: KeyEvidence[];  // New detailed evidence
}

interface Relationship {
    edge_id: string;  // String to avoid JS precision loss with large Apache AGE IDs
    source: string;
    target: string;
    relationship_type: string;
    properties?: Record<string, any> & {
        // V2 fields
        sentiment_score?: number;
        emotional_tone?: string;
        context?: string;
        relationship_progression?: string;
        chapter_analyses?: string;  // JSON string of ChapterAnalysis[]
        analysis_version?: string;  // 'v2' for chapter-based
    };
}

interface RelationshipsTabProps {
    entity: Entity;
    entityRelationships: Relationship[];
    allRelationships: Relationship[];
    allEntities?: Entity[];
    workspaceId: string;
    projectId: string;
    onRelationshipCreated: () => void;
    onRelationshipDeleted: () => void;
    onRelationshipUpdated: () => void;
}

type ViewMode = "all" | "one-to-one";
type SortBy = "name" | "type" | "recent";
type FilterBy = "all" | string;

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
}: RelationshipsTabProps) {
    const [viewMode, setViewMode] = useState<ViewMode>("all");
    const [selectedRelationship, setSelectedRelationship] = useState<Relationship | null>(null);
    const [sortBy, setSortBy] = useState<SortBy>("name");
    const [filterBy, setFilterBy] = useState<FilterBy>("all");
    const [searchQuery, setSearchQuery] = useState("");
    const [isEditing, setIsEditing] = useState(false);
    const [editedType, setEditedType] = useState("");
    const [useCustomType, setUseCustomType] = useState(false);
    const [customType, setCustomType] = useState("");
    const [useCustomTone, setUseCustomTone] = useState(false);
    const [customTone, setCustomTone] = useState("");
    const [editedProperties, setEditedProperties] = useState<Record<string, any>>({});
    const [newPropertyKey, setNewPropertyKey] = useState("");
    const [newPropertyValue, setNewPropertyValue] = useState("");
    const [saving, setSaving] = useState(false);
    
    // Dedicated fields for deconstructor properties
    const [context, setContext] = useState("");
    const [emotionalTone, setEmotionalTone] = useState("neutral");
    const [sentimentScore, setSentimentScore] = useState<number | "">(0);
    
    // Multi-select mode
    const [multiSelectMode, setMultiSelectMode] = useState(false);
    const [selectedEdgeIds, setSelectedEdgeIds] = useState<Set<string>>(new Set());
    const [deletingMultiple, setDeletingMultiple] = useState(false);
    
    // Interactions for CK3-style breakdown
    const [interactions, setInteractions] = useState<Interaction[]>([]);
    const [loadingInteractions, setLoadingInteractions] = useState(false);
    const [interactionsExpanded, setInteractionsExpanded] = useState(false);
    const [interactionsViewMode, setInteractionsViewMode] = useState<"all" | "by-chapter">("all");
    const [expandedChapters, setExpandedChapters] = useState<Set<number>>(new Set());
    const [deletingInteraction, setDeletingInteraction] = useState<string | null>(null);
    const [showCreateInteraction, setShowCreateInteraction] = useState(false);
    const [creatingInteraction, setCreatingInteraction] = useState(false);
    const [newInteraction, setNewInteraction] = useState({
        interaction_type: "INTERACTS_WITH",
        emotional_tone: "neutral",
        chapter_number: 0,
        context: "",
        text_evidence: ""
    });
    const [editingInteraction, setEditingInteraction] = useState<Interaction | null>(null);
    const [savingInteraction, setSavingInteraction] = useState(false);
    
    // Chapter Analysis Editing
    const [editingChapter, setEditingChapter] = useState<ChapterAnalysis | null>(null);
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
    
    // Standard relationship types
    const standardRelationshipTypes = [
        "INTERACTS_WITH",
        "KNOWS",
        "LOVES",
        "HATES",
        "FOLLOWS",
        "LEADS",
        "ALLIED_WITH",
        "RIVAL_OF",
        "MENTOR_TO",
        "PROTECTS",
        "BETRAYS",
        "TRUSTS",
        "FEARS",
        "RESPECTS",
        "DESPISES"
    ];

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

        // Filter by type
        if (filterBy !== "all") {
            filtered = filtered.filter((rel) => rel.relationship_type === filterBy);
        }

        // Search filter
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            filtered = filtered.filter((rel) => {
                const otherEntity = rel.source === entity.name ? rel.target : rel.source;
                return (
                    otherEntity.toLowerCase().includes(query) ||
                    rel.relationship_type.toLowerCase().includes(query)
                );
            });
        }

        // Sort
        filtered.sort((a, b) => {
            const aOther = a.source === entity.name ? a.target : a.source;
            const bOther = b.source === entity.name ? b.target : b.source;

            switch (sortBy) {
                case "name":
                    return aOther.localeCompare(bOther);
                case "type":
                    return a.relationship_type.localeCompare(b.relationship_type);
                default:
                    return 0;
            }
        });

        return filtered;
    }, [entityRelationships, filterBy, searchQuery, sortBy, entity.name]);

    // Get all characters for 1-to-1 view
    const allCharacters = useMemo(() => {
        const chars = new Set<string>();
        allRelationships.forEach((rel) => {
            if (rel.source !== entity.name) chars.add(rel.source);
            if (rel.target !== entity.name) chars.add(rel.target);
        });
        return Array.from(chars).sort();
    }, [allRelationships, entity.name]);

    const handleSelectRelationship = (rel: Relationship) => {
        setSelectedRelationship(rel);
        setViewMode("one-to-one");
        setIsEditing(false);
        const relType = rel.relationship_type.replace(/"/g, ''); // Remove quotes
        setEditedType(relType);
        setUseCustomType(!standardRelationshipTypes.includes(relType));
        setCustomType(relType);
        
        // Standard emotional tones for the dropdown
        const standardTones = ["friendly", "hostile", "neutral", "romantic", "familial", "professional", "protective", "suspicious", "warm", "cold", "playful", "tense"];
        
        // Extract deconstructor properties
        const props = rel.properties || {};
        const currentTone = props.emotional_tone || "neutral";
        setContext(props.context || "");
        setEmotionalTone(currentTone);
        setUseCustomTone(!standardTones.includes(currentTone.toLowerCase()));
        setCustomTone(currentTone);
        setSentimentScore(props.sentiment_score !== undefined ? props.sentiment_score : 0);
        
        // Store other properties (excluding deconstructor ones and V2 internal properties)
        const otherProps = { ...props };
        delete otherProps.context;
        delete otherProps.emotional_tone;
        delete otherProps.sentiment_score;
        // Hide V2-specific internal properties
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
            alert("Please enter a relationship type");
            return;
        }

        // Merge deconstructor properties with other properties
        const finalTone = useCustomTone ? customTone : emotionalTone;
        const allProperties = {
            ...editedProperties,
            context: context,
            emotional_tone: finalTone,
            sentiment_score: sentimentScore === "" ? 0 : sentimentScore,
        };

        setSaving(true);
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/records/relationships/${selectedRelationship.edge_id}`,
                {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                    body: JSON.stringify({
                        project_id: projectId,
                        type: finalType,
                        properties: allProperties,
                    }),
                }
            );

            if (response.ok) {
                setIsEditing(false);
                onRelationshipUpdated();
                // Reload the relationship data
                const updatedRel = { ...selectedRelationship, relationship_type: finalType, properties: allProperties };
                setSelectedRelationship(updatedRel);
                
                // Update local state
                setContext(allProperties.context || "");
                setEmotionalTone(allProperties.emotional_tone || "neutral");
                setSentimentScore(allProperties.sentiment_score !== undefined ? allProperties.sentiment_score : 0);
            } else {
                let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                try {
                    const error = await response.json();
                    errorMessage = error.error || error.message || errorMessage;
                    if (error.details) {
                        errorMessage += `\n\nDetails: ${typeof error.details === 'string' ? error.details : JSON.stringify(error.details)}`;
                    }
                } catch (e) {
                    console.error("Error parsing response:", e);
                }
                alert(`Error: ${errorMessage}`);
            }
        } catch (error: any) {
            console.error("Error updating relationship:", error);
            alert(`Failed to update relationship: ${error?.message || String(error)}`);
        } finally {
            setSaving(false);
        }
    };

    const handleDeleteRelationship = async (edgeId: number) => {
        if (!confirm("Are you sure you want to delete this relationship?")) {
            return;
        }

        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/records/relationships/${edgeId}`,
                {
                    method: "DELETE",
                    headers: {
                        "Accept": "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                }
            );

            if (response.ok) {
                if (selectedRelationship?.edge_id === edgeId) {
                    setSelectedRelationship(null);
                    setViewMode("all");
                }
                onRelationshipDeleted();
            } else {
                let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                try {
                    const error = await response.json();
                    errorMessage = error.error || error.message || errorMessage;
                } catch (e) {
                    console.error("Error parsing response:", e);
                }
                alert(`Error: ${errorMessage}`);
            }
        } catch (error: any) {
            console.error("Error deleting relationship:", error);
            alert(`Failed to delete relationship: ${error?.message || String(error)}`);
        }
    };

    // Get relationship between this entity and another character
    const getRelationshipWith = (characterName: string): Relationship | null => {
        return (
            entityRelationships.find(
                (rel) =>
                    (rel.source === entity.name && rel.target === characterName) ||
                    (rel.source === characterName && rel.target === entity.name)
            ) || null
        );
    };
    
    // Fetch interactions when relationship is selected
    const fetchInteractions = async (sourceChar: string, targetChar: string) => {
        setLoadingInteractions(true);
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/interactions?source_character=${encodeURIComponent(sourceChar)}&target_character=${encodeURIComponent(targetChar)}`,
                {
                    headers: {
                        "Accept": "application/json",
                    },
                }
            );
            if (response.ok) {
                const data = await response.json();
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
            fetchInteractions(selectedRelationship.source, selectedRelationship.target);
        } else {
            setInteractions([]);
        }
    }, [selectedRelationship, viewMode]);
    
    // Multi-select toggle
    const toggleSelectEdge = (edgeId: string) => {
        const newSelected = new Set(selectedEdgeIds);
        if (newSelected.has(edgeId)) {
            newSelected.delete(edgeId);
        } else {
            newSelected.add(edgeId);
        }
        setSelectedEdgeIds(newSelected);
    };
    
    // Select all visible
    const selectAllVisible = () => {
        const allIds = new Set(filteredAndSorted.map(rel => rel.edge_id));
        setSelectedEdgeIds(allIds);
    };
    
    // Deselect all
    const deselectAll = () => {
        setSelectedEdgeIds(new Set());
    };
    
    // Delete multiple selected relationships
    const handleDeleteMultiple = async () => {
        if (selectedEdgeIds.size === 0) return;
        if (!confirm(`Are you sure you want to delete ${selectedEdgeIds.size} relationships?`)) {
            return;
        }

        setDeletingMultiple(true);
        let successCount = 0;
        let errorCount = 0;

        for (const edgeId of selectedEdgeIds) {
            try {
                const response = await fetch(
                    `/${workspaceId}/projects/${projectId}/editor/records/relationships/${edgeId}`,
                    {
                        method: "DELETE",
                        headers: {
                            "Accept": "application/json",
                            "X-CSRF-TOKEN":
                                document
                                    .querySelector('meta[name="csrf-token"]')
                                    ?.getAttribute("content") || "",
                        },
                    }
                );
                if (response.ok) {
                    successCount++;
                } else {
                    errorCount++;
                }
            } catch (error) {
                errorCount++;
            }
        }

        setDeletingMultiple(false);
        setSelectedEdgeIds(new Set());
        setMultiSelectMode(false);
        
        if (successCount > 0) {
            onRelationshipDeleted();
        }
        if (errorCount > 0) {
            alert(`Deleted ${successCount} relationships. ${errorCount} failed.`);
        }
    };
    
    // Delete a single interaction
    const handleDeleteInteraction = async (vertexId: string) => {
        if (!confirm("Are you sure you want to delete this interaction?")) {
            return;
        }
        
        setDeletingInteraction(vertexId);
        
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/interactions/${vertexId}`,
                {
                    method: "DELETE",
                    headers: {
                        "Accept": "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                }
            );
            
            if (response.ok) {
                // Remove from local state
                setInteractions(prev => prev.filter(i => String(i.vertex_id) !== vertexId));
            } else {
                const error = await response.json();
                alert(`Failed to delete interaction: ${error.error || 'Unknown error'}`);
            }
        } catch (e) {
            console.error("Error deleting interaction:", e);
            alert("Failed to delete interaction");
        } finally {
            setDeletingInteraction(null);
        }
    };
    
    // Create a new interaction
    const handleCreateInteraction = async () => {
        if (!selectedRelationship) return;
        
        setCreatingInteraction(true);
        
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/interactions`,
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
                        source_character: selectedRelationship.source,
                        target_character: selectedRelationship.target,
                        chapter_number: newInteraction.chapter_number,
                        interaction_type: newInteraction.interaction_type,
                        emotional_tone: newInteraction.emotional_tone,
                        context: newInteraction.context,
                        text_evidence: newInteraction.text_evidence
                    })
                }
            );
            
            if (response.ok) {
                const data = await response.json();
                // Add to local state
                setInteractions(prev => [...prev, data.interaction]);
                // Reset form and close modal
                setNewInteraction({
                    interaction_type: "INTERACTS_WITH",
                    emotional_tone: "neutral",
                    chapter_number: 0,
                    context: "",
                    text_evidence: ""
                });
                setShowCreateInteraction(false);
            } else {
                const error = await response.json();
                alert(`Failed to create interaction: ${error.error || 'Unknown error'}`);
            }
        } catch (e) {
            console.error("Error creating interaction:", e);
            alert("Failed to create interaction");
        } finally {
            setCreatingInteraction(false);
        }
    };
    
    // Update an existing interaction
    const handleUpdateInteraction = async () => {
        if (!editingInteraction?.vertex_id) return;
        
        setSavingInteraction(true);
        
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/interactions/${editingInteraction.vertex_id}`,
                {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                    body: JSON.stringify({
                        interaction_type: editingInteraction.interaction_type,
                        emotional_tone: editingInteraction.emotional_tone,
                        sentiment_modifier: editingInteraction.sentiment_modifier,
                        context: editingInteraction.context,
                        text_evidence: editingInteraction.text_evidence
                    })
                }
            );
            
            if (response.ok) {
                // Update in local state
                setInteractions(prev => prev.map(i => 
                    String(i.vertex_id) === String(editingInteraction.vertex_id) 
                        ? editingInteraction 
                        : i
                ));
                setEditingInteraction(null);
            } else {
                const error = await response.json();
                alert(`Failed to update interaction: ${error.error || 'Unknown error'}`);
            }
        } catch (e) {
            console.error("Error updating interaction:", e);
            alert("Failed to update interaction");
        } finally {
            setSavingInteraction(false);
        }
    };
    
    // =========================================================================
    // Chapter Analysis CRUD Operations
    // =========================================================================
    
    const handleSaveChapterAnalyses = async (chapters: ChapterAnalysis[]) => {
        if (!selectedRelationship) return;
        
        setSavingChapter(true);
        
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/relationships/${selectedRelationship.edge_id}/chapter-analyses`,
                {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                    body: JSON.stringify({
                        project_id: projectId,
                        chapter_analyses: chapters,
                        recalculate_overall: true
                    })
                }
            );
            
            if (response.ok) {
                // Update local relationship properties
                if (selectedRelationship.properties) {
                    selectedRelationship.properties.chapter_analyses = JSON.stringify(chapters);
                }
                setEditingChapter(null);
                setShowAddChapter(false);
                onRelationshipUpdated();
            } else {
                const error = await response.json();
                alert(`Failed to update chapters: ${error.error || 'Unknown error'}`);
            }
        } catch (e) {
            console.error("Error updating chapters:", e);
            alert("Failed to update chapters");
        } finally {
            setSavingChapter(false);
        }
    };
    
    const handleDeleteChapter = async (chapterNumber: number) => {
        if (!selectedRelationship) return;
        if (!confirm("Are you sure you want to delete this chapter analysis?")) return;
        
        setDeletingChapter(chapterNumber);
        
        try {
            const props = selectedRelationship.properties || {};
            let chapters: ChapterAnalysis[] = [];
            try {
                chapters = typeof props.chapter_analyses === 'string' 
                    ? JSON.parse(props.chapter_analyses) 
                    : (Array.isArray(props.chapter_analyses) ? props.chapter_analyses : []);
            } catch (e) {
                chapters = [];
            }
            
            // Remove the chapter
            const updatedChapters = chapters.filter(ch => ch.chapter_number !== chapterNumber);
            
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
            chapters = typeof props.chapter_analyses === 'string' 
                ? JSON.parse(props.chapter_analyses) 
                : (Array.isArray(props.chapter_analyses) ? props.chapter_analyses : []);
        } catch (e) {
            chapters = [];
        }
        
        // Add new chapter
        chapters.push(newChapter);
        
        // Sort by chapter number
        chapters.sort((a, b) => a.chapter_number - b.chapter_number);
        
        await handleSaveChapterAnalyses(chapters);
    };
    
    const handleEditChapter = async (updatedChapter: ChapterAnalysis) => {
        if (!selectedRelationship) return;
        
        const props = selectedRelationship.properties || {};
        let chapters: ChapterAnalysis[] = [];
        try {
            chapters = typeof props.chapter_analyses === 'string' 
                ? JSON.parse(props.chapter_analyses) 
                : (Array.isArray(props.chapter_analyses) ? props.chapter_analyses : []);
        } catch (e) {
            chapters = [];
        }
        
        // Update the chapter
        const updatedChapters = chapters.map(ch => 
            ch.chapter_number === updatedChapter.chapter_number ? updatedChapter : ch
        );
        
        await handleSaveChapterAnalyses(updatedChapters);
    };
    
    // =========================================================================
    // Emotional Tones Management
    // =========================================================================
    
    const fetchEmotionalTones = async () => {
        setLoadingTones(true);
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/emotional-tones`,
                {
                    headers: {
                        "Accept": "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                }
            );
            
            if (response.ok) {
                const data = await response.json();
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
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/emotional-tones`,
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
                        name: newToneName.trim()
                    })
                }
            );
            
            if (response.ok) {
                const data = await response.json();
                setEmotionalTones(prev => [...prev, data.tone]);
                setNewToneName("");
            } else {
                const error = await response.json();
                alert(`Failed to create tone: ${error.error || 'Unknown error'}`);
            }
        } catch (e) {
            console.error("Error creating emotional tone:", e);
            alert("Failed to create emotional tone");
        } finally {
            setCreatingTone(false);
        }
    };
    
    const handleDeleteTone = async (toneId: number) => {
        if (!confirm("Are you sure you want to delete this emotional tone?")) return;
        
        setDeletingTone(toneId);
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/emotional-tones/${toneId}`,
                {
                    method: "DELETE",
                    headers: {
                        "Accept": "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                }
            );
            
            if (response.ok) {
                setEmotionalTones(prev => prev.filter(t => t.id !== toneId));
            } else {
                const error = await response.json();
                alert(`Failed to delete tone: ${error.error || 'Unknown error'}`);
            }
        } catch (e) {
            console.error("Error deleting emotional tone:", e);
            alert("Failed to delete emotional tone");
        } finally {
            setDeletingTone(null);
        }
    };
    
    // Reassess a relationship - re-run V2 extraction for this pair
    const handleReassessRelationship = async () => {
        if (!selectedRelationship) return;
        
        const source = selectedRelationship.source;
        const target = selectedRelationship.target;
        
        if (!confirm(`Re-analyze the relationship between ${source} and ${target}?\n\nThis will re-run the AI analysis across all chapters and update the stored data.`)) {
            return;
        }
        
        setReassessing(true);
        
        try {
            // Find vertex IDs for the characters
            const sourceEntity = allEntities?.find(e => e.name === source && e.type.toLowerCase() === 'character');
            const targetEntity = allEntities?.find(e => e.name === target && e.type.toLowerCase() === 'character');
            
            if (!sourceEntity || !targetEntity) {
                alert("Could not find character entities for reassessment.");
                return;
            }
            
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/extract-relationships`,
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
                        character_ids: [sourceEntity.vertex_id, targetEntity.vertex_id],
                        focus_mode: "1-to-1",
                        model: "gemini-2.0-flash",
                        provider: "gemini"
                    })
                }
            );
            
            if (response.ok) {
                alert(`✓ Successfully reassessed ${source} ↔ ${target}!`);
                onRelationshipUpdated();
            } else {
                const error = await response.json();
                alert(`Failed to reassess: ${error.error || 'Unknown error'}`);
            }
        } catch (e: any) {
            console.error("Error reassessing relationship:", e);
            alert(`Failed to reassess: ${e?.message || String(e)}`);
        } finally {
            setReassessing(false);
        }
    };
    
    // Fetch emotional tones when tones manager is opened
    useEffect(() => {
        if (showTonesManager) {
            fetchEmotionalTones();
        }
    }, [showTonesManager]);
    
    // Calculate CK3-style breakdown from interactions
    // Now using AI-provided scores directly when available
    const sentimentBreakdown = useMemo<SentimentBreakdownItem[]>(() => {
        if (!interactions.length) return [];
        
        // Legacy fallback modifiers (only used if AI doesn't provide score)
        const typeModifiers: Record<string, number> = {
            "SAVES": 30, "PROTECTS": 25, "COMFORTS": 20, "SUPPORTS": 15,
            "PRAISES": 15, "WARNS": 5, "QUESTIONS": 0, "ARGUES": -10,
            "MOCKS": -15, "INSULTS": -25, "THREATENS": -35, "ATTACKS": -50, "BETRAYS": -50,
        };
        
        const toneModifiers: Record<string, number> = {
            "affectionate": 10, "warm": 5, "friendly": 5, "cordial": 2,
            "neutral": 0, "cold": -5, "antagonistic": -10, "hostile": -15,
        };
        
        return interactions.map(interaction => {
            // Prefer AI-provided score, fall back to formula
            const totalModifier = interaction.sentiment_modifier !== undefined 
                ? interaction.sentiment_modifier 
                : (typeModifiers[interaction.interaction_type?.toUpperCase()] || 0) + 
                  (toneModifiers[interaction.emotional_tone?.toLowerCase()] || 0);
            
            return {
                label: `${interaction.interaction_type || "INTERACTION"} (${interaction.emotional_tone || "neutral"})`,
                value: totalModifier,
                description: interaction.context || interaction.text_evidence,
                chapter: interaction.chapter_number,
                reasoning: interaction.sentiment_reasoning,  // Include AI reasoning
            };
        });
    }, [interactions]);
    
    // Calculate CLAMPED total sentiment (ensures -100 to +100 range)
    const clampedTotalSentiment = useMemo(() => {
        const rawTotal = sentimentBreakdown.reduce((sum, item) => sum + item.value, 0);
        return Math.max(-100, Math.min(100, rawTotal));
    }, [sentimentBreakdown]);
    
    // Raw total for display comparison
    const rawTotalSentiment = useMemo(() => {
        return sentimentBreakdown.reduce((sum, item) => sum + item.value, 0);
    }, [sentimentBreakdown]);

    // Group interactions by chapter for "By Chapter" view
    const interactionsByChapter = useMemo(() => {
        const grouped: Map<number, Interaction[]> = new Map();
        
        interactions.forEach((interaction) => {
            const chapter = interaction.chapter_number ?? -1;
            if (!grouped.has(chapter)) {
                grouped.set(chapter, []);
            }
            grouped.get(chapter)!.push(interaction);
        });
        
        // Sort by chapter number
        return Array.from(grouped.entries()).sort((a, b) => a[0] - b[0]);
    }, [interactions]);

    // Toggle chapter expansion
    const toggleChapter = (chapterNum: number) => {
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
                            variant={multiSelectMode ? "default" : "outline"}
                            onClick={() => {
                                setMultiSelectMode(!multiSelectMode);
                                if (multiSelectMode) {
                                    setSelectedEdgeIds(new Set());
                                }
                            }}
                        >
                            {multiSelectMode ? <CheckSquare className="h-4 w-4" /> : <Square className="h-4 w-4" />}
                        </Button>
                    )}
                    <Button size="sm" onClick={onRelationshipCreated}>
                        <Plus className="h-4 w-4 mr-2" />
                        Add Relationship
                    </Button>
                </div>
            </div>
            
            {/* Multi-select toolbar */}
            {multiSelectMode && viewMode === "all" && (
                <div className="flex items-center justify-between bg-blue-50 p-2 rounded-lg border border-blue-200">
                    <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-blue-800">
                            {selectedEdgeIds.size} selected
                        </span>
                        <Button size="sm" variant="ghost" onClick={selectAllVisible} className="text-xs h-6">
                            Select All
                        </Button>
                        <Button size="sm" variant="ghost" onClick={deselectAll} className="text-xs h-6">
                            Deselect All
                        </Button>
                    </div>
                    <Button 
                        size="sm" 
                        variant="destructive" 
                        onClick={handleDeleteMultiple}
                        disabled={selectedEdgeIds.size === 0 || deletingMultiple}
                    >
                        {deletingMultiple ? (
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                            <Trash2 className="h-4 w-4 mr-2" />
                        )}
                        Delete Selected
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
                            // Auto-select first character if available
                            const firstRel = getRelationshipWith(allCharacters[0]);
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
                    🎭 Tones
                </Button>
            </div>
            
            {/* Emotional Tones Manager Panel */}
            {showTonesManager && (
                <div className="border rounded-lg p-3 bg-purple-50 space-y-3">
                    <div className="flex items-center justify-between">
                        <h4 className="font-medium text-sm text-purple-800">Emotional Tones</h4>
                        <button
                            onClick={() => setShowTonesManager(false)}
                            className="text-gray-500 hover:text-gray-700"
                        >
                            <X className="h-4 w-4" />
                        </button>
                    </div>
                    
                    {/* Create New Tone */}
                    <div className="flex gap-2">
                        <Input
                            placeholder="New tone name..."
                            value={newToneName}
                            onChange={(e) => setNewToneName(e.target.value)}
                            className="flex-1 text-sm h-8"
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') handleCreateTone();
                            }}
                        />
                        <Button
                            size="sm"
                            onClick={handleCreateTone}
                            disabled={creatingTone || !newToneName.trim()}
                            className="h-8"
                        >
                            {creatingTone ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <Plus className="h-4 w-4" />
                            )}
                        </Button>
                    </div>
                    
                    {/* Tones List */}
                    {loadingTones ? (
                        <div className="flex items-center justify-center py-4">
                            <Loader2 className="h-5 w-5 animate-spin text-purple-600" />
                        </div>
                    ) : (
                        <div className="max-h-40 overflow-y-auto space-y-1">
                            {emotionalTones.length === 0 ? (
                                <p className="text-xs text-gray-500 text-center py-2">
                                    No custom tones yet. AI can create them during analysis.
                                </p>
                            ) : (
                                emotionalTones.map((tone) => (
                                    <div
                                        key={tone.id}
                                        className={`flex items-center justify-between px-2 py-1.5 rounded text-xs ${
                                            tone.is_base 
                                                ? 'bg-white/50 text-gray-600' 
                                                : 'bg-white text-gray-800'
                                        }`}
                                    >
                                        <span className="capitalize">
                                            {tone.name}
                                            {tone.is_base && (
                                                <span className="ml-1 text-[10px] text-gray-400">(base)</span>
                                            )}
                                        </span>
                                        {!tone.is_base && (
                                            <button
                                                onClick={() => handleDeleteTone(tone.id)}
                                                disabled={deletingTone === tone.id}
                                                className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                                                title="Delete Tone"
                                            >
                                                {deletingTone === tone.id ? (
                                                    <Loader2 className="h-3 w-3 animate-spin" />
                                                ) : (
                                                    <Trash2 className="h-3 w-3" />
                                                )}
                                            </button>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                    
                    <p className="text-[10px] text-gray-500">
                        Base tones cannot be deleted. AI can create custom tones during analysis.
                    </p>
                </div>
            )}

            {viewMode === "all" ? (
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
                            <Select value={filterBy} onValueChange={(v) => setFilterBy(v as FilterBy)}>
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
                            <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortBy)}>
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
                                            isSelected ? "bg-blue-50 border-blue-300" : ""
                                        }`}
                                        onClick={() => {
                                            if (multiSelectMode) {
                                                toggleSelectEdge(rel.edge_id);
                                            } else {
                                                handleSelectRelationship(rel);
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
                                                            {rel.relationship_type.replace("_", " ")}
                                                        </span>
                                                        {rel.properties && (() => {
                                                            const props = rel.properties;
                                                            const sentimentScore = props.sentiment_score !== undefined ? props.sentiment_score : null;
                                                            const emotionalTone = props.emotional_tone;
                                                            const context = props.context;
                                                            const interactionCount = props.interaction_count;
                                                            
                                                            if (sentimentScore !== null) {
                                                                return (
                                                                    <TooltipProvider>
                                                                        <Tooltip>
                                                                            <TooltipTrigger asChild>
                                                                                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold cursor-help ${
                                                                                    sentimentScore < -50 ? "bg-red-100 text-red-700" :
                                                                                    sentimentScore < 0 ? "bg-orange-100 text-orange-700" :
                                                                                    sentimentScore === 0 ? "bg-gray-100 text-gray-700" :
                                                                                    sentimentScore < 50 ? "bg-lime-100 text-lime-700" :
                                                                                    "bg-green-100 text-green-700"
                                                                                }`}>
                                                                                    {sentimentScore > 0 ? "+" : ""}{sentimentScore}
                                                                                </span>
                                                                            </TooltipTrigger>
                                                                            <TooltipContent side="top" className="max-w-xs p-3">
                                                                                <div className="space-y-2">
                                                                                    <div className="font-semibold text-sm">
                                                                                        Sentiment: {sentimentScore > 0 ? "+" : ""}{sentimentScore}
                                                                                    </div>
                                                                                    {emotionalTone && (
                                                                                        <div className="text-xs">
                                                                                            <span className="text-gray-500">Tone:</span>{" "}
                                                                                            <span className="capitalize">{emotionalTone}</span>
                                                                                        </div>
                                                                                    )}
                                                                                    {interactionCount && (
                                                                                        <div className="text-xs">
                                                                                            <span className="text-gray-500">Based on:</span>{" "}
                                                                                            {interactionCount} interactions
                                                                                        </div>
                                                                                    )}
                                                                                    {context && (
                                                                                        <div className="text-xs text-gray-600 border-t pt-2 mt-2">
                                                                                            {context}
                                                                                        </div>
                                                                                    )}
                                                                                    <div className="text-[10px] text-gray-400 pt-1">
                                                                                        Click for full details
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
                                                            handleSelectRelationship(rel);
                                                            setViewMode("one-to-one");
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
                                                            handleDeleteRelationship(rel.edge_id);
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
            ) : (
                /* 1-to-1 View */
                <div className="flex-1 overflow-y-auto space-y-4">
                    {/* Character Selector */}
                    <div>
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
                                    handleSelectRelationship(rel);
                                } else {
                                    setSelectedRelationship(null);
                                    setEditedType("");
                                    setEditedProperties({});
                                }
                            }}
                        >
                            <SelectTrigger>
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
                                /* Edit Mode */
                                <div className="space-y-4 border rounded-lg p-4">
                                    <div>
                                        <Label>Relationship Type</Label>
                                        <div className="space-y-2 mt-2">
                                            <div className="flex items-center gap-2">
                                                <input
                                                    type="checkbox"
                                                    id="useCustomRelType"
                                                    checked={useCustomType}
                                                    onChange={(e) => setUseCustomType(e.target.checked)}
                                                    className="rounded"
                                                />
                                                <Label htmlFor="useCustomRelType" className="text-sm font-normal">
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
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Select relationship type" />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {standardRelationshipTypes.map((type) => (
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
                                    <div>
                                        <Label htmlFor="context">Context</Label>
                                        <p className="text-xs text-gray-500 mb-1">
                                            How they interact or the reason for this relationship
                                        </p>
                                        <Textarea
                                            id="context"
                                            value={context}
                                            onChange={(e) => setContext(e.target.value)}
                                            placeholder="Describe the context of this relationship..."
                                            className="min-h-20"
                                        />
                                    </div>

                                    {/* Emotional Tone Field */}
                                    <div>
                                        <Label htmlFor="emotional-tone">Emotional Tone</Label>
                                        <div className="space-y-2 mt-2">
                                            <div className="flex items-center gap-2">
                                                <input
                                                    type="checkbox"
                                                    id="useCustomTone"
                                                    checked={useCustomTone}
                                                    onChange={(e) => setUseCustomTone(e.target.checked)}
                                                    className="rounded"
                                                />
                                                <Label htmlFor="useCustomTone" className="text-sm font-normal">
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
                                                <Select value={emotionalTone} onValueChange={setEmotionalTone}>
                                                    <SelectTrigger id="emotional-tone">
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="friendly">Friendly</SelectItem>
                                                        <SelectItem value="hostile">Hostile</SelectItem>
                                                        <SelectItem value="neutral">Neutral</SelectItem>
                                                        <SelectItem value="romantic">Romantic</SelectItem>
                                                        <SelectItem value="familial">Familial</SelectItem>
                                                        <SelectItem value="professional">Professional</SelectItem>
                                                        <SelectItem value="protective">Protective</SelectItem>
                                                        <SelectItem value="suspicious">Suspicious</SelectItem>
                                                        <SelectItem value="warm">Warm</SelectItem>
                                                        <SelectItem value="cold">Cold</SelectItem>
                                                        <SelectItem value="playful">Playful</SelectItem>
                                                        <SelectItem value="tense">Tense</SelectItem>
                                                    </SelectContent>
                                                </Select>
                                            )}
                                        </div>
                                    </div>

                                    {/* Sentiment Score Field */}
                                    <div>
                                        <Label htmlFor="sentiment-score">Sentiment Score</Label>
                                        <p className="text-xs text-gray-500 mb-1">
                                            Relationship sentiment from -100 (very negative) to +100 (very positive)
                                        </p>
                                        <div className="flex items-center gap-2">
                                            <Input
                                                id="sentiment-score"
                                                type="number"
                                                min="-100"
                                                max="100"
                                                value={sentimentScore}
                                                onChange={(e) => {
                                                    const val = e.target.value === "" ? "" : parseInt(e.target.value, 10);
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
                                                    onChange={(e) => setSentimentScore(parseInt(e.target.value, 10))}
                                                    className="w-full"
                                                />
                                            </div>
                                            <span className={`text-sm font-medium w-16 text-right ${
                                                (sentimentScore === "" ? 0 : sentimentScore) < 0 ? "text-red-600" :
                                                (sentimentScore === "" ? 0 : sentimentScore) > 0 ? "text-green-600" :
                                                "text-gray-600"
                                            }`}>
                                                {sentimentScore === "" ? 0 : sentimentScore}
                                            </span>
                                        </div>
                                    </div>

                                    <div>
                                        <Label>Properties</Label>
                                        <p className="text-sm text-gray-500 mb-2">
                                            Add custom properties to store additional information.
                                        </p>
                                        <div className="space-y-2 mt-2">
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
                                                    placeholder="Property name (e.g., intensity)"
                                                    value={newPropertyKey}
                                                    onChange={(e) => setNewPropertyKey(e.target.value)}
                                                    onKeyPress={(e) => {
                                                        if (e.key === "Enter") {
                                                            e.preventDefault();
                                                            handleAddProperty();
                                                        }
                                                    }}
                                                />
                                                <Input
                                                    placeholder="Property value (e.g., high)"
                                                    value={newPropertyValue}
                                                    onChange={(e) => setNewPropertyValue(e.target.value)}
                                                    onKeyPress={(e) => {
                                                        if (e.key === "Enter") {
                                                            e.preventDefault();
                                                            handleAddProperty();
                                                        }
                                                    }}
                                                />
                                                <Button
                                                    type="button"
                                                    variant="outline"
                                                    onClick={handleAddProperty}
                                                >
                                                    <Plus className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex gap-2">
                                        <Button
                                            variant="outline"
                                            onClick={() => {
                                                setIsEditing(false);
                                                const relType = selectedRelationship.relationship_type.replace(/"/g, '');
                                                setEditedType(relType);
                                                setUseCustomType(!standardRelationshipTypes.includes(relType));
                                                setCustomType(relType);
                                                
                                                // Standard emotional tones for the dropdown
                                                const standardTones = ["friendly", "hostile", "neutral", "romantic", "familial", "professional", "protective", "suspicious", "warm", "cold", "playful", "tense"];
                                                
                                                // Reset deconstructor properties
                                                const props = selectedRelationship.properties || {};
                                                const currentTone = props.emotional_tone || "neutral";
                                                setContext(props.context || "");
                                                setEmotionalTone(currentTone);
                                                setUseCustomTone(!standardTones.includes(currentTone.toLowerCase()));
                                                setCustomTone(currentTone);
                                                setSentimentScore(props.sentiment_score !== undefined ? props.sentiment_score : 0);
                                                
                                                // Reset other properties (excluding V2 internal properties)
                                                const otherProps = { ...props };
                                                delete otherProps.context;
                                                delete otherProps.emotional_tone;
                                                delete otherProps.sentiment_score;
                                                // Hide V2-specific internal properties
                                                delete otherProps.analysis_version;
                                                delete otherProps.chapter_analyses;
                                                delete otherProps.directional;
                                                delete otherProps.relationship_progression;
                                                delete otherProps.overall_summary;
                                                delete otherProps.last_updated;
                                                delete otherProps.interaction_count;
                                                delete otherProps.aggregated_from_interactions;
                                                setEditedProperties(otherProps);
                                            }}
                                        >
                                            Cancel
                                        </Button>
                                        <Button onClick={handleEditRelationship} disabled={saving}>
                                            {saving ? "Saving..." : "Save Changes"}
                                        </Button>
                                    </div>
                                </div>
                            ) : (
                                /* View Mode */
                                <div className="border rounded-lg p-4 space-y-4">
                                    <div>
                                        <Label>Relationship</Label>
                                        <div className="mt-2 p-3 bg-gray-50 rounded">
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

                                    {/* Display Context, Emotional Tone, and Sentiment Score prominently */}
                                    {(() => {
                                        const props = selectedRelationship.properties || {};
                                        const hasDeconstructorProps = props.context || props.emotional_tone || props.sentiment_score !== undefined;
                                        
                                        if (hasDeconstructorProps) {
                                            return (
                                                <div className="space-y-3">
                                                    {props.context && (
                                                        <div>
                                                            <Label>Context</Label>
                                                            <p className="text-sm text-gray-700 mt-1 p-2 bg-blue-50 rounded">
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
                                                                <p className={`text-sm font-semibold mt-1 ${
                                                                    props.sentiment_score < 0 ? "text-red-600" :
                                                                    props.sentiment_score > 0 ? "text-green-600" :
                                                                    "text-gray-600"
                                                                }`}>
                                                                    {props.sentiment_score > 0 ? "+" : ""}{props.sentiment_score}
                                                                </p>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        }
                                        return null;
                                    })()}

                                    {/* V2 Chapter-by-Chapter Analysis */}
                                    {(() => {
                                        const props = selectedRelationship.properties || {};
                                        // Check if this relationship has chapter analyses (V2 format)
                                        // Be flexible - check for chapter_analyses even without analysis_version flag
                                        if (props.chapter_analyses) {
                                            let chapters: ChapterAnalysis[] = [];
                                            try {
                                                chapters = typeof props.chapter_analyses === 'string' 
                                                    ? JSON.parse(props.chapter_analyses) 
                                                    : (Array.isArray(props.chapter_analyses) ? props.chapter_analyses : []);
                                            } catch (e) {
                                                console.log('Failed to parse chapter_analyses:', e, props.chapter_analyses);
                                                chapters = [];
                                            }
                                            console.log('Chapter analyses found:', chapters.length, chapters);
                                            
                                            if (chapters.length > 0) {
                                                return (
                                                    <div className="border rounded-lg overflow-hidden">
                                                        <div className="p-3 bg-linear-to-r from-indigo-50 to-purple-50 border-b">
                                                            <div className="flex items-center justify-between">
                                                                <div>
                                                                    <Label className="text-sm font-semibold text-indigo-900">
                                                                        Chapter-by-Chapter Analysis
                                                                    </Label>
                                                                    <p className="text-xs text-indigo-600 mt-0.5">
                                                                        How {selectedRelationship.source} → {selectedRelationship.target} evolves
                                                                    </p>
                                                                </div>
                                                                <div className="text-right">
                                                                    <span className={`text-xl font-bold ${
                                                                        (props.sentiment_score || 0) < 0 ? "text-red-600" :
                                                                        (props.sentiment_score || 0) > 0 ? "text-green-600" :
                                                                        "text-gray-600"
                                                                    }`}>
                                                                        {(props.sentiment_score || 0) > 0 ? "+" : ""}{props.sentiment_score || 0}
                                                                    </span>
                                                                    <p className="text-[10px] text-gray-500">Overall</p>
                                                                </div>
                                                            </div>
                                                            
                                                            {/* Progression note */}
                                                            {props.relationship_progression && (
                                                                <p className="text-xs text-indigo-700 mt-2 italic">
                                                                    📈 {props.relationship_progression}
                                                                </p>
                                                            )}
                                                        </div>
                                                        
                                                        {/* Collapsible Chapter list with Edit/Delete */}
                                                        <div className="divide-y divide-gray-100">
                                                            {chapters.map((ch, idx) => {
                                                                const isExpanded = expandedChapters.has(ch.chapter_number);
                                                                const evidence = ch.key_evidence || (ch.key_moment ? [{quote: ch.key_moment, context: ''}] : []);
                                                                const isDeleting = deletingChapter === ch.chapter_number;
                                                                
                                                                return (
                                                                    <div key={idx} className="border-b border-gray-100 last:border-0">
                                                                        {/* Collapsible Header - Responsive Layout */}
                                                                        <div className="p-2 hover:bg-gray-50 transition-colors">
                                                                            <div className="flex items-start gap-2">
                                                                                {/* Expand/Collapse Button */}
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
                                                                                
                                                                                {/* Content Area */}
                                                                                <div className="flex-1 min-w-0">
                                                                                    {/* Row 1: Chapter name + Score */}
                                                                                    <div className="flex items-center gap-2 flex-wrap">
                                                                                        <span className="font-medium text-sm">{ch.chapter_name}</span>
                                                                                        <span className={`text-xs px-1.5 py-0.5 rounded font-semibold ${
                                                                                            ch.sentiment_score < -20 ? "bg-red-100 text-red-700" :
                                                                                            ch.sentiment_score < 0 ? "bg-orange-100 text-orange-700" :
                                                                                            ch.sentiment_score < 20 ? "bg-gray-100 text-gray-700" :
                                                                                            ch.sentiment_score < 50 ? "bg-green-100 text-green-700" :
                                                                                            "bg-emerald-100 text-emerald-700"
                                                                                        }`}>
                                                                                            {ch.sentiment_score > 0 ? "+" : ""}{ch.sentiment_score}
                                                                                        </span>
                                                                                    </div>
                                                                                    
                                                                                    {/* Row 2: Emotional tone + Type */}
                                                                                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                                                                                        <span className="text-xs text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded">
                                                                                            {ch.emotional_tone}
                                                                                        </span>
                                                                                        <span className="text-[10px] text-gray-400 uppercase">
                                                                                        {ch.relationship_type}
                                                                                    </span>
                                                                                </div>
                                                                                
                                                                                {/* Preview when collapsed */}
                                                                                    {!isExpanded && ch.summary && (
                                                                                        <p className="text-xs text-gray-500 mt-1 line-clamp-1">
                                                                                        {ch.summary}
                                                                                    </p>
                                                                                )}
                                                                                </div>
                                                                            
                                                                                {/* Edit/Delete Buttons - Always visible */}
                                                                                <div className="flex items-center gap-0.5 shrink-0">
                                                                                <button
                                                                                    onClick={() => setEditingChapter(ch)}
                                                                                    className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                                                                                    title="Edit Chapter Analysis"
                                                                                >
                                                                                        <Edit className="h-4 w-4" />
                                                                                </button>
                                                                                <button
                                                                                    onClick={() => handleDeleteChapter(ch.chapter_number)}
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
                                                                        
                                                                        {/* Expanded Content */}
                                                                        {isExpanded && (
                                                                            <div className="px-3 pb-3 ml-6 space-y-3 border-l-2 border-indigo-200 bg-gray-50/50">
                                                                                {/* Full Summary */}
                                                                                <div>
                                                                                    <p className="text-xs font-medium text-gray-700 mb-1">Summary</p>
                                                                                    <p className="text-sm text-gray-600 leading-relaxed">
                                                                                        {ch.summary}
                                                                                    </p>
                                                                                </div>
                                                                                
                                                                                {/* Evidence Quotes */}
                                                                                {evidence.length > 0 && (
                                                                                    <div>
                                                                                        <p className="text-xs font-medium text-gray-700 mb-2">
                                                                                            Key Evidence ({evidence.length} quotes)
                                                                                        </p>
                                                                                        <div className="space-y-2">
                                                                                            {evidence.map((ev, evIdx) => (
                                                                                                <div key={evIdx} className="bg-white rounded p-2 border border-gray-100">
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
                                                            <div className="p-3 bg-blue-50 border-t space-y-3">
                                                                <div className="flex items-center justify-between">
                                                                    <span className="font-medium text-sm text-blue-800">Add Chapter Analysis</span>
                                                                    <button
                                                                        onClick={() => setShowAddChapter(false)}
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
                                                                        const chNum = parseInt((document.getElementById('new-chapter-number') as HTMLInputElement)?.value || '1');
                                                                        const score = parseInt((document.getElementById('new-chapter-score') as HTMLInputElement)?.value || '0');
                                                                        const tone = (document.getElementById('new-chapter-tone') as HTMLInputElement)?.value || 'neutral';
                                                                        const summary = (document.getElementById('new-chapter-summary') as HTMLTextAreaElement)?.value || '';
                                                                        
                                                                        const newCh: ChapterAnalysis = {
                                                                            chapter_number: chNum,
                                                                            chapter_name: `Chapter ${chNum}`,
                                                                            sentiment_score: Math.max(-100, Math.min(100, score)),
                                                                            relationship_type: selectedRelationship?.properties?.relationship_type || 'INTERACTS_WITH',
                                                                            emotional_tone: tone,
                                                                            summary: summary,
                                                                            key_evidence: []
                                                                        };
                                                                        
                                                                        await handleAddChapter(newCh);
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
                                                                        'Add Chapter'
                                                                    )}
                                                                </Button>
                                                            </div>
                                                        )}
                                                        
                                                        {/* Edit Chapter Form */}
                                                        {editingChapter && (
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
                                                                            onChange={(e) => setEditingChapter({
                                                                                ...editingChapter,
                                                                                chapter_number: parseInt(e.target.value) || 1,
                                                                                chapter_name: `Chapter ${e.target.value || 1}`
                                                                            })}
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
                                                                            onChange={(e) => setEditingChapter({
                                                                                ...editingChapter,
                                                                                sentiment_score: Math.max(-100, Math.min(100, parseInt(e.target.value) || 0))
                                                                            })}
                                                                            className="h-8 text-sm"
                                                                        />
                                                                    </div>
                                                                </div>
                                                                <div>
                                                                    <label className="text-xs text-gray-600">Emotional Tone</label>
                                                                    <Input
                                                                        value={editingChapter.emotional_tone}
                                                                        onChange={(e) => setEditingChapter({
                                                                            ...editingChapter,
                                                                            emotional_tone: e.target.value
                                                                        })}
                                                                        className="h-8 text-sm"
                                                                    />
                                                                </div>
                                                                <div>
                                                                    <label className="text-xs text-gray-600">Summary</label>
                                                                    <Textarea
                                                                        value={editingChapter.summary}
                                                                        onChange={(e) => setEditingChapter({
                                                                            ...editingChapter,
                                                                            summary: e.target.value
                                                                        })}
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
                                                                        onClick={() => handleEditChapter(editingChapter)}
                                                                        disabled={savingChapter}
                                                                        className="flex-1"
                                                                    >
                                                                        {savingChapter ? (
                                                                            <>
                                                                                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                                                                Saving...
                                                                            </>
                                                                        ) : (
                                                                            'Save Changes'
                                                                        )}
                                                                    </Button>
                                                                </div>
                                                            </div>
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
                                        }
                                        return null;
                                    })()}

                                    {/* CK3-Style Sentiment Breakdown - only show in "All" view mode and for non-V2 relationships */}
                                    {selectedRelationship.properties?.sentiment_score !== undefined && 
                                     selectedRelationship.properties?.analysis_version !== 'v2' &&
                                     interactionsViewMode === "all" && (
                                        <div className="border rounded-lg p-3 bg-linear-to-r from-red-50 via-gray-50 to-green-50">
                                            <div className="flex items-center justify-between mb-3">
                                                <div>
                                                    <Label className="text-sm font-semibold">Sentiment Breakdown</Label>
                                                    {/* Show direction if available */}
                                                    {selectedRelationship.properties?.directional && (
                                                        <p className="text-xs text-gray-500 mt-0.5">
                                                            How {selectedRelationship.source} perceives {selectedRelationship.target}
                                                        </p>
                                                    )}
                                                </div>
                                                <div className="text-right">
                                                    <span className={`text-xl font-bold ${
                                                        clampedTotalSentiment < 0 ? "text-red-600" :
                                                        clampedTotalSentiment > 0 ? "text-green-600" :
                                                        "text-gray-600"
                                                    }`}>
                                                        {clampedTotalSentiment > 0 ? "+" : ""}{clampedTotalSentiment}
                                                    </span>
                                                    {/* Show raw total if different from clamped */}
                                                    {Math.abs(rawTotalSentiment) > 100 && (
                                                        <p className="text-[10px] text-gray-400">
                                                            (raw: {rawTotalSentiment > 0 ? "+" : ""}{rawTotalSentiment})
                                                        </p>
                                                    )}
                                                </div>
                                            </div>
                                            
                                            {/* Sentiment bar - using clamped value */}
                                            <div className="h-3 bg-gray-200 rounded-full overflow-hidden mb-3">
                                                <div 
                                                    className={`h-full transition-all duration-300 ${
                                                        clampedTotalSentiment < 0 
                                                            ? "bg-linear-to-r from-red-600 to-red-400" 
                                                            : "bg-linear-to-r from-green-400 to-green-600"
                                                    }`}
                                                    style={{
                                                        width: `${Math.min(100, Math.abs(clampedTotalSentiment) / 2)}%`,
                                                        marginLeft: clampedTotalSentiment >= 0 ? "50%" : `${50 - Math.min(50, Math.abs(clampedTotalSentiment) / 2)}%`
                                                    }}
                                                />
                                            </div>
                                            
                                            {/* Breakdown items with reasoning */}
                                            {loadingInteractions ? (
                                                <div className="flex items-center justify-center py-2">
                                                    <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                                                    <span className="ml-2 text-sm text-gray-500">Loading breakdown...</span>
                                                </div>
                                            ) : sentimentBreakdown.length > 0 ? (
                                                <div className="space-y-2">
                                                    {sentimentBreakdown.slice(0, interactionsExpanded ? undefined : 5).map((item, idx) => (
                                                        <div key={idx} className="text-xs py-1.5 border-b border-gray-100 last:border-0">
                                                            <div className="flex items-center gap-2">
                                                                <span className={`font-bold min-w-10 ${
                                                                    item.value < 0 ? "text-red-600" : 
                                                                    item.value > 0 ? "text-green-600" : 
                                                                    "text-gray-500"
                                                                }`}>
                                                                    {item.value > 0 ? "+" : ""}{item.value}
                                                                </span>
                                                                <span className="text-gray-700 font-medium">{item.label}</span>
                                                                {item.chapter !== undefined && (
                                                                    <span className="text-gray-400 text-[10px] ml-auto">Ch.{item.chapter + 1}</span>
                                                                )}
                                                            </div>
                                                            {/* Show AI reasoning if available */}
                                                            {item.reasoning && (
                                                                <p className="text-gray-500 mt-1 pl-12 italic text-[11px]">
                                                                    "{item.reasoning}"
                                                                </p>
                                                            )}
                                                        </div>
                                                    ))}
                                                    {sentimentBreakdown.length > 5 && (
                                                        <button 
                                                            onClick={() => setInteractionsExpanded(!interactionsExpanded)}
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
                                                                    Show {sentimentBreakdown.length - 5} more
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
                                    
                                    {/* Expandable Interactions List with View Toggle - ONLY show for non-V2 relationships */}
                                    {(interactions.length > 0 || showCreateInteraction) && 
                                     selectedRelationship.properties?.analysis_version !== 'v2' && (
                                        <div className="border rounded-lg overflow-hidden">
                                            {/* Header with expand toggle and view mode */}
                                            <div className="flex items-center justify-between p-3 bg-gray-50 border-b">
                                                <button
                                                    onClick={() => setInteractionsExpanded(!interactionsExpanded)}
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
                                                                    onClick={() => setInteractionsViewMode("all")}
                                                                    className={`px-2 py-1 text-xs rounded-md transition-colors ${
                                                                        interactionsViewMode === "all"
                                                                            ? "bg-white shadow-sm font-medium"
                                                                            : "text-gray-600 hover:text-gray-900"
                                                                    }`}
                                                                >
                                                                    All
                                                                </button>
                                                                <button
                                                                    onClick={() => setInteractionsViewMode("by-chapter")}
                                                                    className={`px-2 py-1 text-xs rounded-md transition-colors ${
                                                                        interactionsViewMode === "by-chapter"
                                                                            ? "bg-white shadow-sm font-medium"
                                                                            : "text-gray-600 hover:text-gray-900"
                                                                    }`}
                                                                >
                                                                    By Chapter
                                                                </button>
                                                            </div>
                                                            <button
                                                                onClick={() => setShowCreateInteraction(true)}
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
                                                <div className="p-4 bg-blue-50 border-b space-y-3">
                                                    <div className="flex items-center justify-between">
                                                        <span className="font-medium text-sm text-blue-800">New Interaction</span>
                                                        <button
                                                            onClick={() => setShowCreateInteraction(false)}
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
                                                                onChange={(e) => setNewInteraction({...newInteraction, interaction_type: e.target.value})}
                                                                className="w-full text-sm border rounded px-2 py-1"
                                                            >
                                                                <option value="SAVES">SAVES</option>
                                                                <option value="PROTECTS">PROTECTS</option>
                                                                <option value="COMFORTS">COMFORTS</option>
                                                                <option value="SUPPORTS">SUPPORTS</option>
                                                                <option value="PRAISES">PRAISES</option>
                                                                <option value="WARNS">WARNS</option>
                                                                <option value="QUESTIONS">QUESTIONS</option>
                                                                <option value="ARGUES">ARGUES</option>
                                                                <option value="MOCKS">MOCKS</option>
                                                                <option value="INSULTS">INSULTS</option>
                                                                <option value="THREATENS">THREATENS</option>
                                                                <option value="ATTACKS">ATTACKS</option>
                                                                <option value="INTERACTS_WITH">INTERACTS_WITH</option>
                                                            </select>
                                                        </div>
                                                        <div>
                                                            <label className="text-xs text-gray-600">Tone</label>
                                                            <select
                                                                value={newInteraction.emotional_tone}
                                                                onChange={(e) => setNewInteraction({...newInteraction, emotional_tone: e.target.value})}
                                                                className="w-full text-sm border rounded px-2 py-1"
                                                            >
                                                                <option value="affectionate">Affectionate</option>
                                                                <option value="warm">Warm</option>
                                                                <option value="friendly">Friendly</option>
                                                                <option value="cordial">Cordial</option>
                                                                <option value="neutral">Neutral</option>
                                                                <option value="cold">Cold</option>
                                                                <option value="antagonistic">Antagonistic</option>
                                                                <option value="hostile">Hostile</option>
                                                            </select>
                                                        </div>
                                                    </div>
                                                    
                                                    <div>
                                                        <label className="text-xs text-gray-600">Chapter</label>
                                                        <input
                                                            type="number"
                                                            min="0"
                                                            value={newInteraction.chapter_number}
                                                            onChange={(e) => setNewInteraction({...newInteraction, chapter_number: parseInt(e.target.value) || 0})}
                                                            className="w-full text-sm border rounded px-2 py-1"
                                                            placeholder="Chapter number (0-indexed)"
                                                        />
                                                    </div>
                                                    
                                                    <div>
                                                        <label className="text-xs text-gray-600">Context</label>
                                                        <input
                                                            type="text"
                                                            value={newInteraction.context}
                                                            onChange={(e) => setNewInteraction({...newInteraction, context: e.target.value})}
                                                            className="w-full text-sm border rounded px-2 py-1"
                                                            placeholder="Brief description of the interaction"
                                                        />
                                                    </div>
                                                    
                                                    <div>
                                                        <label className="text-xs text-gray-600">Text Evidence (optional)</label>
                                                        <input
                                                            type="text"
                                                            value={newInteraction.text_evidence}
                                                            onChange={(e) => setNewInteraction({...newInteraction, text_evidence: e.target.value})}
                                                            className="w-full text-sm border rounded px-2 py-1"
                                                            placeholder="Quote from the text"
                                                        />
                                                    </div>
                                                    
                                                                    <div className="flex gap-2">
                                                                        <button
                                                                            onClick={() => setShowCreateInteraction(false)}
                                                                            className="flex-1 px-3 py-1.5 text-sm border rounded hover:bg-gray-100"
                                                                        >
                                                                            Cancel
                                                                        </button>
                                                                        <button
                                                                            onClick={handleCreateInteraction}
                                                                            disabled={creatingInteraction || !newInteraction.context}
                                                                            className="flex-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                                                                        >
                                                                            {creatingInteraction ? "Creating..." : "Create"}
                                                                        </button>
                                                                    </div>
                                                                </div>
                                                            )}
                                                            
                                                            {/* Edit Interaction Form */}
                                                            {editingInteraction && interactionsExpanded && (
                                                                <div className="p-4 bg-amber-50 border-b space-y-3">
                                                                    <div className="flex items-center justify-between">
                                                                        <span className="font-medium text-sm text-amber-800">Edit Interaction</span>
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
                                                                                onChange={(e) => setEditingInteraction({...editingInteraction, interaction_type: e.target.value})}
                                                                                className="w-full text-sm border rounded px-2 py-1"
                                                                            >
                                                                                <option value="SAVES">SAVES</option>
                                                                                <option value="PROTECTS">PROTECTS</option>
                                                                                <option value="COMFORTS">COMFORTS</option>
                                                                                <option value="SUPPORTS">SUPPORTS</option>
                                                                                <option value="PRAISES">PRAISES</option>
                                                                                <option value="WARNS">WARNS</option>
                                                                                <option value="QUESTIONS">QUESTIONS</option>
                                                                                <option value="ARGUES">ARGUES</option>
                                                                                <option value="MOCKS">MOCKS</option>
                                                                                <option value="INSULTS">INSULTS</option>
                                                                                <option value="THREATENS">THREATENS</option>
                                                                                <option value="ATTACKS">ATTACKS</option>
                                                                                <option value="INTERACTS_WITH">INTERACTS_WITH</option>
                                                                            </select>
                                                                        </div>
                                                                        <div>
                                                                            <label className="text-xs text-gray-600">Tone</label>
                                                                            <select
                                                                                value={editingInteraction.emotional_tone}
                                                                                onChange={(e) => setEditingInteraction({...editingInteraction, emotional_tone: e.target.value})}
                                                                                className="w-full text-sm border rounded px-2 py-1"
                                                                            >
                                                                                <option value="affectionate">Affectionate</option>
                                                                                <option value="warm">Warm</option>
                                                                                <option value="friendly">Friendly</option>
                                                                                <option value="cordial">Cordial</option>
                                                                                <option value="neutral">Neutral</option>
                                                                                <option value="cold">Cold</option>
                                                                                <option value="antagonistic">Antagonistic</option>
                                                                                <option value="hostile">Hostile</option>
                                                                            </select>
                                                                        </div>
                                                                    </div>
                                                                    
                                                                    <div>
                                                                        <label className="text-xs text-gray-600">Sentiment Modifier ({editingInteraction.sentiment_modifier ?? 0})</label>
                                                                        <input
                                                                            type="range"
                                                                            min="-100"
                                                                            max="100"
                                                                            value={editingInteraction.sentiment_modifier ?? 0}
                                                                            onChange={(e) => setEditingInteraction({...editingInteraction, sentiment_modifier: parseInt(e.target.value)})}
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
                                                                            onChange={(e) => setEditingInteraction({...editingInteraction, context: e.target.value})}
                                                                            className="w-full text-sm border rounded px-2 py-1"
                                                                        />
                                                                    </div>
                                                                    
                                                                    <div>
                                                                        <label className="text-xs text-gray-600">Text Evidence</label>
                                                                        <input
                                                                            type="text"
                                                                            value={editingInteraction.text_evidence || ""}
                                                                            onChange={(e) => setEditingInteraction({...editingInteraction, text_evidence: e.target.value})}
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
                                                                            onClick={handleUpdateInteraction}
                                                                            disabled={savingInteraction}
                                                                            className="flex-1 px-3 py-1.5 text-sm bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50"
                                                                        >
                                                                            {savingInteraction ? "Saving..." : "Save Changes"}
                                                                        </button>
                                                                    </div>
                                                                </div>
                                                            )}

                                            {/* INTERACTIONS CONTENT - switches between All and By Chapter views */}
                                            {interactionsExpanded && (
                                                <div className="max-h-80 overflow-y-auto" key={interactionsViewMode}>
                                                    {interactionsViewMode === "all" ? (
                                                        /* All Interactions View - flat list */
                                                        <div className="divide-y">
                                                        {interactions.map((interaction, idx) => (
                                                                <div key={interaction.vertex_id || idx} className="p-3 hover:bg-gray-50 group">
                                                                    <div className="flex items-start justify-between gap-2">
                                                                        <div className="flex-1">
                                                                            <div className="flex items-center gap-2 flex-wrap">
                                                                                <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                                                                                    ["SAVES", "PROTECTS", "COMFORTS", "SUPPORTS", "PRAISES"].includes(interaction.interaction_type)
                                                                                        ? "bg-green-100 text-green-700"
                                                                                        : ["THREATENS", "ATTACKS", "INSULTS", "MOCKS", "BETRAYS"].includes(interaction.interaction_type)
                                                                                        ? "bg-red-100 text-red-700"
                                                                                        : "bg-gray-100 text-gray-700"
                                                                                }`}>
                                                                                    {interaction.interaction_type}
                                                                                </span>
                                                                                <span className="text-xs text-gray-500 capitalize">
                                                                                    {interaction.emotional_tone}
                                                                                </span>
                                                                                {interaction.chapter_number !== undefined && (
                                                                                    <span className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded">
                                                                                        Ch. {interaction.chapter_number + 1}
                                                                                    </span>
                                                                                )}
                                                                                {interaction.sentiment_modifier !== undefined && (
                                                                                    <span className={`text-xs font-medium ${
                                                                                        interaction.sentiment_modifier > 0 ? "text-green-600" :
                                                                                        interaction.sentiment_modifier < 0 ? "text-red-600" :
                                                                                        "text-gray-500"
                                                                                    }`}>
                                                                                        {interaction.sentiment_modifier > 0 ? "+" : ""}{interaction.sentiment_modifier}
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
                                                                            {/* Show AI reasoning if available */}
                                                                            {interaction.sentiment_reasoning && (
                                                                                <p className="text-xs text-blue-600 mt-1.5 bg-blue-50 px-2 py-1 rounded">
                                                                                    💡 {interaction.sentiment_reasoning}
                                                                                </p>
                                                                            )}
                                                                        </div>
                                                                        {/* Edit & Delete buttons */}
                                                                        {interaction.vertex_id && (
                                                                            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-all">
                                                                                <button
                                                                                    onClick={(e) => {
                                                                                        e.stopPropagation();
                                                                                        setEditingInteraction(interaction);
                                                                                    }}
                                                                                    className="p-1 text-gray-400 hover:text-blue-500"
                                                                                    title="Edit interaction"
                                                                                >
                                                                                    <Edit className="h-4 w-4" />
                                                                                </button>
                                                                                <button
                                                                                    onClick={(e) => {
                                                                                        e.stopPropagation();
                                                                                        handleDeleteInteraction(String(interaction.vertex_id));
                                                                                    }}
                                                                                    disabled={deletingInteraction === String(interaction.vertex_id)}
                                                                                    className="p-1 text-gray-400 hover:text-red-500"
                                                                                    title="Delete interaction"
                                                                                >
                                                                                    {deletingInteraction === String(interaction.vertex_id) ? (
                                                                                        <Loader2 className="h-4 w-4 animate-spin" />
                                                                                    ) : (
                                                                                        <Trash2 className="h-4 w-4" />
                                                                                    )}
                                                                                </button>
                                                                            </div>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    ) : (
                                                        /* BY CHAPTER VIEW - chapter headers with collapsible content */
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
                                                                                {chapterNum >= 0 ? `Chapter ${chapterNum + 1}` : "Unknown Chapter"}
                                                                            </span>
                                                                            <span className="text-xs text-blue-600 bg-blue-100 px-2 py-0.5 rounded-full">
                                                                                {chapterInteractions.length} interactions
                                                                            </span>
                                                                        </div>
                                                                        {/* Chapter sentiment summary */}
                                                                        {(() => {
                                                                            const chapterSentiment = chapterInteractions.reduce(
                                                                                (sum, i) => sum + (i.sentiment_modifier || 0), 0
                                                                            );
                                                                            return (
                                                                                <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                                                                                    chapterSentiment > 0 ? "bg-green-100 text-green-700" :
                                                                                    chapterSentiment < 0 ? "bg-red-100 text-red-700" :
                                                                                    "bg-gray-100 text-gray-700"
                                                                                }`}>
                                                                                    {chapterSentiment > 0 ? "+" : ""}{chapterSentiment}
                                                                                </span>
                                                                            );
                                                                        })()}
                                                                    </button>
                                                                    
                                                                    {expandedChapters.has(chapterNum) && (
                                                                        <div className="divide-y bg-white">
                                                                            {chapterInteractions.map((interaction, idx) => (
                                                                                <div key={interaction.vertex_id || idx} className="p-3 pl-8 hover:bg-gray-50 group">
                                                                                    <div className="flex items-start justify-between gap-2">
                                                                                        <div className="flex-1">
                                                                                            <div className="flex items-center gap-2 flex-wrap">
                                                                                                <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                                                                                                    ["SAVES", "PROTECTS", "COMFORTS", "SUPPORTS", "PRAISES"].includes(interaction.interaction_type)
                                                                                                        ? "bg-green-100 text-green-700"
                                                                                                        : ["THREATENS", "ATTACKS", "INSULTS", "MOCKS", "BETRAYS"].includes(interaction.interaction_type)
                                                                                                        ? "bg-red-100 text-red-700"
                                                                                                        : "bg-gray-100 text-gray-700"
                                                                                                }`}>
                                                                                                    {interaction.interaction_type}
                                                                                                </span>
                                                                                                <span className="text-xs text-gray-500 capitalize">
                                                                                                    {interaction.emotional_tone}
                                                                                                </span>
                                                                                                {interaction.sentiment_modifier !== undefined && (
                                                                                                    <span className={`text-xs font-medium ${
                                                                                                        interaction.sentiment_modifier > 0 ? "text-green-600" :
                                                                                                        interaction.sentiment_modifier < 0 ? "text-red-600" :
                                                                                                        "text-gray-500"
                                                                                                    }`}>
                                                                                                        {interaction.sentiment_modifier > 0 ? "+" : ""}{interaction.sentiment_modifier}
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
                                                                                        </div>
                                                                                        {/* Edit & Delete buttons */}
                                                                                        {interaction.vertex_id && (
                                                                                            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-all">
                                                                                                <button
                                                                                                    onClick={(e) => {
                                                                                                        e.stopPropagation();
                                                                                                        setEditingInteraction(interaction);
                                                                                                    }}
                                                                                                    className="p-1 text-gray-400 hover:text-blue-500"
                                                                                                    title="Edit interaction"
                                                                                                >
                                                                                                    <Edit className="h-4 w-4" />
                                                                                                </button>
                                                                                                <button
                                                                                                    onClick={(e) => {
                                                                                                        e.stopPropagation();
                                                                                                        handleDeleteInteraction(String(interaction.vertex_id));
                                                                                                    }}
                                                                                                    disabled={deletingInteraction === String(interaction.vertex_id)}
                                                                                                    className="p-1 text-gray-400 hover:text-red-500"
                                                                                                    title="Delete interaction"
                                                                                                >
                                                                                                    {deletingInteraction === String(interaction.vertex_id) ? (
                                                                                                        <Loader2 className="h-4 w-4 animate-spin" />
                                                                                                    ) : (
                                                                                                        <Trash2 className="h-4 w-4" />
                                                                                                    )}
                                                                                                </button>
                                                                                            </div>
                                                                                        )}
                                                                                    </div>
                                                                                </div>
                                                                            ))}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Display other properties - hide V2-specific internal properties */}
                                    {(() => {
                                        const props = selectedRelationship.properties || {};
                                        const otherProps = { ...props };
                                        // Hide standard properties
                                        delete otherProps.context;
                                        delete otherProps.emotional_tone;
                                        delete otherProps.sentiment_score;
                                        delete otherProps.interaction_count;
                                        delete otherProps.aggregated_from_interactions;
                                        delete otherProps.last_updated;
                                        // Hide V2-specific internal properties
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
                                                        {Object.entries(otherProps).map(
                                                            ([key, value]) => (
                                                                <div
                                                                    key={key}
                                                                    className="p-2 bg-gray-50 rounded text-sm"
                                                                >
                                                                    <span className="font-medium">{key}:</span>{" "}
                                                                    <span className="text-gray-600">
                                                                        {String(value)}
                                                                    </span>
                                                                </div>
                                                            )
                                                        )}
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
                                                        onClick={handleReassessRelationship}
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
                                                handleDeleteRelationship(selectedRelationship.edge_id)
                                            }
                                            className="text-red-500 hover:text-red-700"
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </div>
                            )}
                        </>
                    ) : (
                        <div className="text-center py-8 text-gray-500">
                            Select a character to view relationship details.
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}


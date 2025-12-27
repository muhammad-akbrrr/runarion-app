import { useState, useEffect } from "react";
import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { Label } from "@/Components/ui/label";
import { Textarea } from "@/Components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/Components/ui/select";
import { Lock, X, HelpCircle, ChevronDown, ChevronRight, BookOpen, Trash2 } from "lucide-react";
import { MagicWandButton } from "@/Components/MagicWandButton";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/Components/ui/tooltip";

// Baseline properties for each entity type (required by deconstructor)
const BASELINE_PROPERTIES: Record<string, Array<{key: string, label: string, type: 'text' | 'textarea' | 'array', placeholder?: string, tooltip?: string}>> = {
    character: [
        { 
            key: 'traits', 
            label: 'Traits', 
            type: 'array', 
            placeholder: '["brave", "intelligent"]',
            tooltip: 'Array of character traits. Format: JSON array like ["brave", "intelligent", "loyal"]. Used by deconstructor to understand character personality.'
        },
        { 
            key: 'role', 
            label: 'Role', 
            type: 'text', 
            placeholder: 'e.g., protagonist, antagonist',
            tooltip: 'Character\'s role in the story. Examples: protagonist, antagonist, supporting, mentor, etc. Helps deconstructor understand narrative function.'
        },
        { 
            key: 'emotional_state', 
            label: 'Emotional State', 
            type: 'text', 
            placeholder: 'e.g., determined, conflicted',
            tooltip: 'Current or typical emotional state of the character. Examples: determined, conflicted, hopeful, despairing. Used for character consistency tracking.'
        },
    ],
    location: [
        { 
            key: 'description', 
            label: 'Description', 
            type: 'textarea', 
            placeholder: 'Physical description of the location',
            tooltip: 'Detailed physical description of the location. Include sensory details, layout, notable features. Used by deconstructor for scene analysis.'
        },
        { 
            key: 'atmosphere', 
            label: 'Atmosphere', 
            type: 'text', 
            placeholder: 'Mood/feeling of the location',
            tooltip: 'The mood or emotional feeling of this location. Examples: ominous, peaceful, chaotic, mysterious. Helps deconstructor understand scene tone.'
        },
    ],
    item: [
        { 
            key: 'description', 
            label: 'Description', 
            type: 'textarea', 
            placeholder: 'Physical description of the item',
            tooltip: 'Physical description of the item. Include appearance, size, material, condition. Used by deconstructor for object tracking.'
        },
        { 
            key: 'significance', 
            label: 'Significance', 
            type: 'text', 
            placeholder: 'Plot importance or symbolic meaning',
            tooltip: 'Why this item matters to the story. Could be plot-critical (MacGuffin), symbolic, or character-significant. Helps deconstructor understand narrative importance.'
        },
    ],
    theme: [
        { 
            key: 'significance', 
            label: 'Significance', 
            type: 'textarea', 
            placeholder: 'Overall importance and meaning',
            tooltip: 'The overall importance and meaning of this theme in the story. Explain what the theme represents and why it matters. Used by deconstructor for thematic analysis.'
        },
        { 
            key: 'symbolic_meaning', 
            label: 'Symbolic Meaning', 
            type: 'textarea', 
            placeholder: 'What the theme symbolizes',
            tooltip: 'What this theme symbolizes or represents. Could be abstract concepts, social commentary, or deeper meanings. Helps deconstructor understand thematic depth.'
        },
        { 
            key: 'character_connections', 
            label: 'Character Connections', 
            type: 'array', 
            placeholder: '["Character1", "Character2"]',
            tooltip: 'Characters who embody, challenge, or relate to this theme. Format: JSON array of character names like ["Protagonist", "Mentor"]. Used for character-theme analysis.'
        },
        { 
            key: 'narrative_function', 
            label: 'Narrative Function', 
            type: 'textarea', 
            placeholder: 'How it drives the story',
            tooltip: 'How this theme drives or influences the plot. Explain its role in story progression, character development, or conflict. Used by deconstructor for plot analysis.'
        },
        { 
            key: 'evolution', 
            label: 'Evolution', 
            type: 'textarea', 
            placeholder: 'How it changes throughout the narrative',
            tooltip: 'How this theme develops or changes throughout the story. Track its progression, deepening, or transformation. Helps deconstructor understand thematic arc.'
        },
        { 
            key: 'literary_techniques', 
            label: 'Literary Techniques', 
            type: 'array', 
            placeholder: '["metaphor", "symbolism"]',
            tooltip: 'Literary techniques used to convey this theme. Format: JSON array like ["metaphor", "symbolism", "foreshadowing"]. Used for style analysis.'
        },
        { 
            key: 'thematic_statement', 
            label: 'Thematic Statement', 
            type: 'textarea', 
            placeholder: 'Central message or insight',
            tooltip: 'The central message or insight this theme conveys. What is the story saying about this theme? Used by deconstructor for thematic interpretation.'
        },
    ],
    plot_point: [
        { 
            key: 'description', 
            label: 'Description', 
            type: 'textarea', 
            placeholder: 'Description of the plot point/thread',
            tooltip: 'Description of this plot point or thread. Explain what happens, who is involved, and its importance. Used by deconstructor for plot structure analysis.'
        },
        { 
            key: 'type', 
            label: 'Type', 
            type: 'text', 
            placeholder: 'e.g., main_plot, subplot',
            tooltip: 'Type of plot thread. Examples: main_plot, subplot, romance_subplot, mystery_thread. Helps deconstructor categorize plot elements.'
        },
        { 
            key: 'status', 
            label: 'Status', 
            type: 'text', 
            placeholder: 'e.g., resolved, ongoing, abandoned',
            tooltip: 'Current status of this plot thread. Options: resolved, ongoing, abandoned, incomplete. Used by deconstructor for plot coherence checking.'
        },
        { 
            key: 'resolution_quality', 
            label: 'Resolution Quality', 
            type: 'text', 
            placeholder: 'e.g., satisfying, weak, incomplete',
            tooltip: 'Quality of resolution if the thread is resolved. Options: satisfying, weak, incomplete, rushed. Helps deconstructor assess plot quality.'
        },
        // scenes field is deconstructor-only, not shown to users
    ],
    record_keeper: [
        { 
            key: 'chapter_number', 
            label: 'Chapter Number', 
            type: 'text', 
            placeholder: 'e.g., 1, 2, 3',
            tooltip: 'The chapter number this record summarizes. Used to organize chapter-by-chapter summaries in the Record Keeper.'
        },
        { 
            key: 'chapter_title', 
            label: 'Chapter Title', 
            type: 'text', 
            placeholder: 'e.g., The Journey Begins',
            tooltip: 'The title or name of this chapter. Helps identify and organize chapter summaries.'
        },
        { 
            key: 'summary', 
            label: 'Summary', 
            type: 'textarea', 
            placeholder: 'Comprehensive summary of what happened in this chapter...',
            tooltip: 'A detailed summary of all events, plot developments, and key moments in this chapter. This is the main content of the Record Keeper entry.'
        },
        { 
            key: 'character_activity', 
            label: 'Character Activity', 
            type: 'array', 
            placeholder: '[{"name": "Character1", "actions": "did X, said Y"}]',
            tooltip: 'Characters who appear in this chapter and what they did. Format: JSON array of objects with "name" and "actions" fields. Example: [{"name": "John", "actions": "fought the dragon, rescued the princess"}]'
        },
        { 
            key: 'key_events', 
            label: 'Key Events', 
            type: 'array', 
            placeholder: '["Event 1", "Event 2"]',
            tooltip: 'Major plot events that occurred in this chapter. Format: JSON array of event descriptions. Example: ["The hero discovers the ancient artifact", "The villain reveals their true identity"]'
        },
        { 
            key: 'themes_mentioned', 
            label: 'Themes Mentioned', 
            type: 'array', 
            placeholder: '["Theme1", "Theme2"]',
            tooltip: 'Themes or motifs that appear or are developed in this chapter. Format: JSON array of theme names. Example: ["sacrifice", "redemption", "betrayal"]'
        },
        { 
            key: 'locations_mentioned', 
            label: 'Locations Mentioned', 
            type: 'array', 
            placeholder: '["Location1", "Location2"]',
            tooltip: 'Locations or settings featured in this chapter. Format: JSON array of location names. Example: ["The Forest of Shadows", "The Castle"]'
        },
    ],
};

// Protected fields that cannot be deleted (required by deconstructor)
const PROTECTED_FIELDS: Record<string, string[]> = {
    character: ['traits', 'role', 'emotional_state'],
    location: ['description', 'atmosphere'],
    item: ['description', 'significance'],
    theme: ['significance', 'symbolic_meaning', 'narrative_function'],
    plot_point: ['description', 'type', 'status'],
    record_keeper: ['chapter_number', 'chapter_title', 'summary', 'character_activity', 'key_events', 'themes_mentioned', 'locations_mentioned'],
};

interface Entity {
    vertex_id: string;  // String to avoid JS precision loss with large Apache AGE IDs
    name: string;
    type: string;
    properties: Record<string, any>;
}

interface EntityFormProps {
    workspaceId: string;
    projectId: string;
    entity?: Entity | null;
    onSaved: () => void;
    onCancel: () => void;
}

const SYSTEM_TYPES = [
    { value: "character", label: "Character" },
    { value: "location", label: "Location" },
    { value: "item", label: "Item" },
    { value: "theme", label: "Theme" },
    { value: "plot_point", label: "Plot Point" },
    { value: "record_keeper", label: "Record Keeper" },
];

interface CollectionType {
    id: string;
    name: string;
    vertex_label: string;
    is_system: boolean;
    field_schema: any[];
}

export default function EntityForm({
    workspaceId,
    projectId,
    entity,
    onSaved,
    onCancel,
}: EntityFormProps) {
    const [name, setName] = useState("");
    const [type, setType] = useState("character");
    const [properties, setProperties] = useState<Record<string, any>>({});
    const [customPropertyKey, setCustomPropertyKey] = useState("");
    const [customPropertyValue, setCustomPropertyValue] = useState("");
    const [saving, setSaving] = useState(false);
    const [availableTypes, setAvailableTypes] = useState<Array<{value: string, label: string, vertex_label?: string}>>(SYSTEM_TYPES);
    const [expandedSummaries, setExpandedSummaries] = useState<Set<number>>(new Set());

    // Load collection types
    useEffect(() => {
        const loadCollectionTypes = async () => {
            try {
                const response = await fetch(
                    `/${workspaceId}/projects/${projectId}/editor/records/collection-types`,
                    {
                        headers: {
                            "Accept": "application/json",
                        },
                    }
                );
                
                if (response.ok) {
                    const data = await response.json();
                    const customTypes = (data.collection_types?.custom || []).map((type: CollectionType) => ({
                        value: type.name.toLowerCase().replace(/\s+/g, '_'), // Use lowercase for entity_type
                        label: type.name,
                        vertex_label: type.vertex_label, // Store vertex_label for API
                    }));
                    setAvailableTypes([...SYSTEM_TYPES, ...customTypes]);
                }
            } catch (error) {
                console.error("Error loading collection types:", error);
            }
        };
        
        loadCollectionTypes();
    }, [workspaceId, projectId]);

    useEffect(() => {
        if (entity) {
            setName(entity.name);
            setType(entity.type);
            setProperties(entity.properties || {});
        }
    }, [entity]);

    // Initialize baseline properties when type changes (only for new entities)
    useEffect(() => {
        if (!entity) {
            // When creating new entity, initialize baseline properties for selected type
            const baselineFields = BASELINE_PROPERTIES[type] || [];
            
            // Create fresh baseline properties for the selected type
            const baselineProps: Record<string, any> = {};
            baselineFields.forEach(field => {
                baselineProps[field.key] = field.type === 'array' ? [] : '';
            });
            
            // Preserve existing custom properties (non-baseline) from previous type
            setProperties(prevProps => {
                const allBaselineKeys = Object.values(BASELINE_PROPERTIES).flatMap(fields => fields.map(f => f.key));
                const existingCustomProps: Record<string, any> = {};
                Object.entries(prevProps).forEach(([key, value]) => {
                    if (!allBaselineKeys.includes(key)) {
                        existingCustomProps[key] = value;
                    }
                });
                return { ...baselineProps, ...existingCustomProps };
            });
        }
    }, [type, entity]); // Depend on type and entity

    const handleAddProperty = () => {
        if (customPropertyKey.trim()) {
            setProperties({
                ...properties,
                [customPropertyKey]: customPropertyValue,
            });
            setCustomPropertyKey("");
            setCustomPropertyValue("");
        }
    };

    const handleRemoveProperty = (key: string) => {
        // Check if field is protected
        const protectedFields = PROTECTED_FIELDS[type] || [];
        if (protectedFields.includes(key)) {
            alert(`Cannot remove "${key}" - this field is required by the deconstructor.`);
            return;
        }
        const newProperties = { ...properties };
        delete newProperties[key];
        setProperties(newProperties);
    };

    const handlePropertyChange = (key: string, value: any) => {
        setProperties({
            ...properties,
            [key]: value,
        });
    };

    const isFieldProtected = (key: string): boolean => {
        const protectedFields = PROTECTED_FIELDS[type] || [];
        return protectedFields.includes(key);
    };

    const getBaselineFields = () => {
        return BASELINE_PROPERTIES[type] || [];
    };

    const getCustomProperties = () => {
        const baselineKeys = getBaselineFields().map(f => f.key);
        // Exclude _summaries from custom properties - it has its own section
        return Object.entries(properties).filter(([key]) => !baselineKeys.includes(key) && key !== '_summaries');
    };

    // Get summaries array from properties
    const getSummaries = (): Array<{chapter_number: number, chapter_name?: string, activity?: string, key_moments?: string[]}> => {
        const summaries = properties._summaries;
        if (Array.isArray(summaries)) {
            return summaries;
        }
        return [];
    };

    // Toggle summary expansion
    const toggleSummaryExpansion = (chapterNumber: number) => {
        setExpandedSummaries(prev => {
            const next = new Set(prev);
            if (next.has(chapterNumber)) {
                next.delete(chapterNumber);
            } else {
                next.add(chapterNumber);
            }
            return next;
        });
    };

    // Update a specific summary
    const handleSummaryChange = (chapterNumber: number, field: string, value: any) => {
        const summaries = getSummaries();
        const updatedSummaries = summaries.map(s => 
            s.chapter_number === chapterNumber ? { ...s, [field]: value } : s
        );
        handlePropertyChange('_summaries', updatedSummaries);
    };

    // Delete a specific summary
    const handleDeleteSummary = (chapterNumber: number) => {
        if (!confirm(`Are you sure you want to delete the summary for Chapter ${chapterNumber}?`)) {
            return;
        }
        const summaries = getSummaries();
        const updatedSummaries = summaries.filter(s => s.chapter_number !== chapterNumber);
        handlePropertyChange('_summaries', updatedSummaries);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);

        try {
            const url = entity
                ? `/${workspaceId}/projects/${projectId}/editor/records/entities/${entity.vertex_id}`
                : `/${workspaceId}/projects/${projectId}/editor/records/entities`;

            const method = entity ? "PUT" : "POST";

            // Find the selected type to get vertex_label if it's a custom type
            const selectedTypeInfo = availableTypes.find(t => t.value === type);
            const vertexLabel = selectedTypeInfo?.vertex_label;

            const response = await fetch(url, {
                method,
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-CSRF-TOKEN": document
                        .querySelector('meta[name="csrf-token"]')
                        ?.getAttribute("content") || "",
                },
                body: JSON.stringify({
                    name,
                    type,
                    properties,
                    vertex_label: vertexLabel, // Pass vertex_label for custom types
                }),
            });

            if (response.ok) {
                onSaved();
            } else {
                let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                try {
                    const error = await response.json();
                    console.error("Entity save error:", error);
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
            console.error("Error saving entity:", error);
            alert(`Failed to save entity: ${error?.message || String(error)}`);
        } finally {
            setSaving(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div>
                <Label htmlFor="name">Entity Name *</Label>
                <div className="flex gap-2">
                    <Input
                        id="name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        required
                        placeholder="Enter entity name"
                        className="flex-1"
                    />
                    <MagicWandButton
                        text={name}
                        onEnhanced={(enhanced) => setName(enhanced)}
                        enhancementMode="entity_name"
                        workspaceId={workspaceId}
                        projectId={projectId}
                        size="icon"
                        variant="outline"
                    />
                </div>
            </div>

            <div>
                <Label htmlFor="type">Entity Type *</Label>
                <Select value={type} onValueChange={setType} disabled={!!entity}>
                    <SelectTrigger>
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        {availableTypes.map((t) => (
                            <SelectItem key={t.value} value={t.value}>
                                {t.label}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>

            {/* Baseline Properties Section */}
            {getBaselineFields().length > 0 && (
                <div>
                    <Label>Baseline Properties</Label>
                    <p className="text-xs text-gray-500 mb-2">
                        These fields are required by the deconstructor. You can edit values but cannot remove them.
                    </p>
                    <div className="space-y-3 mt-2">
                        {getBaselineFields().map((field) => {
                            const value = properties[field.key] ?? (field.type === 'array' ? [] : '');
                            const isProtected = isFieldProtected(field.key);
                            
                            return (
                                <div
                                    key={field.key}
                                    className={`p-3 rounded border ${
                                        isProtected ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200'
                                    }`}
                                >
                                    <div className="flex items-center gap-2 mb-2">
                                        {isProtected && (
                                            <Lock className="h-3 w-3 text-blue-600" title="Protected field (required by deconstructor)" />
                                        )}
                                        <Label className="text-sm font-medium">{field.label}</Label>
                                        {field.tooltip && (
                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <HelpCircle className="h-3.5 w-3.5 text-gray-400 hover:text-gray-600 cursor-help" />
                                                </TooltipTrigger>
                                                <TooltipContent className="max-w-xs">
                                                    <p className="text-xs">{field.tooltip}</p>
                                                </TooltipContent>
                                            </Tooltip>
                                        )}
                                    </div>
                                    
                                    {field.type === 'array' ? (
                                        <div className="space-y-2">
                                            <Textarea
                                                value={
                                                    Array.isArray(value) 
                                                        ? JSON.stringify(value, null, 2) 
                                                        : (typeof value === 'string' ? value : (value ? String(value) : '[]'))
                                                }
                                                onChange={(e) => {
                                                    // Store the raw input value as string while typing
                                                    handlePropertyChange(field.key, e.target.value);
                                                }}
                                                onBlur={(e) => {
                                                    // On blur, parse and validate
                                                    const inputValue = e.target.value.trim();
                                                    if (!inputValue || inputValue === '[]') {
                                                        handlePropertyChange(field.key, []);
                                                        return;
                                                    }
                                                    
                                                    try {
                                                        const parsed = JSON.parse(inputValue);
                                                        if (Array.isArray(parsed)) {
                                                            handlePropertyChange(field.key, parsed);
                                                        } else {
                                                            // If not array, wrap in array
                                                            handlePropertyChange(field.key, [parsed]);
                                                        }
                                                    } catch {
                                                        // If invalid JSON, try to parse as comma-separated
                                                        if (inputValue.includes(',')) {
                                                            const items = inputValue.split(',').map(s => s.trim().replace(/^["'\[\]]|["'\[\]]$/g, ''));
                                                            handlePropertyChange(field.key, items.filter(item => item));
                                                        } else if (inputValue) {
                                                            // Single item - remove quotes if present
                                                            const cleaned = inputValue.trim().replace(/^["'\[\]]|["'\[\]]$/g, '');
                                                            handlePropertyChange(field.key, cleaned ? [cleaned] : []);
                                                        } else {
                                                            handlePropertyChange(field.key, []);
                                                        }
                                                    }
                                                }}
                                                placeholder={field.placeholder}
                                                className="min-h-[60px] text-sm font-mono"
                                            />
                                            <p className="text-xs text-gray-500">
                                                Format: JSON array (e.g., ["item1", "item2"]) or comma-separated values. Will auto-format on blur.
                                            </p>
                                        </div>
                                    ) : field.type === 'textarea' ? (
                                        <div className="flex gap-2">
                                            <Textarea
                                                value={String(value)}
                                                onChange={(e) => handlePropertyChange(field.key, e.target.value)}
                                                placeholder={field.placeholder}
                                                className="min-h-20 text-sm flex-1"
                                            />
                                            <MagicWandButton
                                                text={String(value)}
                                                onEnhanced={(enhanced) => handlePropertyChange(field.key, enhanced)}
                                                enhancementMode="property"
                                                workspaceId={workspaceId}
                                                projectId={projectId}
                                                size="icon"
                                                variant="outline"
                                                className="self-start mt-1"
                                            />
                                        </div>
                                    ) : (
                                        <div className="flex gap-2">
                                            <Input
                                                value={String(value)}
                                                onChange={(e) => handlePropertyChange(field.key, e.target.value)}
                                                placeholder={field.placeholder}
                                                className="text-sm flex-1"
                                            />
                                            <MagicWandButton
                                                text={String(value)}
                                                onEnhanced={(enhanced) => handlePropertyChange(field.key, enhanced)}
                                                enhancementMode="property"
                                                workspaceId={workspaceId}
                                                projectId={projectId}
                                                size="icon"
                                                variant="outline"
                                            />
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Custom Properties Section */}
            <div>
                <Label>Custom Properties</Label>
                <p className="text-sm text-gray-500 mb-2">
                    Add additional properties beyond the baseline fields. These can be added or removed freely.
                </p>
                <div className="space-y-2 mt-2">
                    {getCustomProperties().map(([key, value]) => (
                        <div
                            key={key}
                            className="flex items-center gap-2 p-2 bg-gray-50 rounded"
                        >
                            <span className="font-medium text-sm flex-1">{key}:</span>
                            <Input
                                value={String(value)}
                                onChange={(e) => handlePropertyChange(key, e.target.value)}
                                className="flex-1 text-sm"
                                placeholder="Enter value"
                            />
                            <MagicWandButton
                                text={String(value)}
                                onEnhanced={(enhanced) => handlePropertyChange(key, enhanced)}
                                enhancementMode="property"
                                workspaceId={workspaceId}
                                projectId={projectId}
                                size="icon"
                                variant="outline"
                            />
                            <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => handleRemoveProperty(key)}
                                title="Remove custom property"
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        </div>
                    ))}

                    <div className="flex gap-2 pt-2 border-t">
                        <Input
                            placeholder="Property name (e.g., age, notes)"
                            value={customPropertyKey}
                            onChange={(e) => setCustomPropertyKey(e.target.value)}
                            onKeyPress={(e) => {
                                if (e.key === "Enter") {
                                    e.preventDefault();
                                    handleAddProperty();
                                }
                            }}
                        />
                        <Input
                            placeholder="Property value"
                            value={customPropertyValue}
                            onChange={(e) => setCustomPropertyValue(e.target.value)}
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
                            Add
                        </Button>
                    </div>
                </div>
            </div>

            {/* Chapter Summaries Section - Only show if entity has summaries */}
            {getSummaries().length > 0 && (
                <div>
                    <div className="flex items-center gap-2 mb-2">
                        <BookOpen className="h-4 w-4 text-blue-600" />
                        <Label>Chapter Summaries ({getSummaries().length})</Label>
                    </div>
                    <p className="text-xs text-gray-500 mb-3">
                        Edit the AI-generated chapter summaries for this entity. These track how the entity appears across chapters.
                    </p>
                    <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
                        {getSummaries()
                            .sort((a, b) => (a.chapter_number || 0) - (b.chapter_number || 0))
                            .map((summary) => {
                                const isExpanded = expandedSummaries.has(summary.chapter_number);
                                return (
                                    <div
                                        key={`summary-${summary.chapter_number}`}
                                        className="border rounded-lg overflow-hidden bg-white"
                                    >
                                        {/* Summary Header - Collapsible */}
                                        <button
                                            type="button"
                                            onClick={() => toggleSummaryExpansion(summary.chapter_number)}
                                            className="w-full flex items-center justify-between p-3 bg-linear-to-r from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 transition-colors"
                                        >
                                            <div className="flex items-center gap-2">
                                                {isExpanded ? (
                                                    <ChevronDown className="h-4 w-4 text-blue-600" />
                                                ) : (
                                                    <ChevronRight className="h-4 w-4 text-blue-600" />
                                                )}
                                                <span className="font-medium text-sm text-gray-800">
                                                    Chapter {summary.chapter_number}: {summary.chapter_name || 'Untitled'}
                                                </span>
                                            </div>
                                            <Button
                                                type="button"
                                                variant="ghost"
                                                size="sm"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleDeleteSummary(summary.chapter_number);
                                                }}
                                                className="h-7 w-7 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                                                title="Delete this chapter summary"
                                            >
                                                <Trash2 className="h-3.5 w-3.5" />
                                            </Button>
                                        </button>

                                        {/* Summary Content - Expandable */}
                                        {isExpanded && (
                                            <div className="p-3 space-y-3 border-t bg-gray-50/50">
                                                {/* Activity */}
                                                <div>
                                                    <Label className="text-xs text-gray-600 mb-1 block">Activity</Label>
                                                    <Textarea
                                                        value={summary.activity || ''}
                                                        onChange={(e) => handleSummaryChange(summary.chapter_number, 'activity', e.target.value)}
                                                        placeholder="Describe what this entity does in this chapter..."
                                                        className="min-h-[100px] text-sm"
                                                    />
                                                </div>

                                                {/* Key Moments */}
                                                <div>
                                                    <Label className="text-xs text-gray-600 mb-1 block">Key Moments</Label>
                                                    <Textarea
                                                        value={
                                                            Array.isArray(summary.key_moments)
                                                                ? summary.key_moments.join('\n')
                                                                : (summary.key_moments || '')
                                                        }
                                                        onChange={(e) => {
                                                            // Split by newlines and filter empty lines
                                                            const moments = e.target.value.split('\n').filter(m => m.trim());
                                                            handleSummaryChange(summary.chapter_number, 'key_moments', moments.length > 0 ? moments : e.target.value.split('\n'));
                                                        }}
                                                        placeholder="Enter key moments, one per line..."
                                                        className="min-h-20 text-sm font-mono"
                                                    />
                                                    <p className="text-xs text-gray-500 mt-1">One key moment per line</p>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                    </div>
                </div>
            )}

            <div className="flex justify-end gap-2 pt-4">
                <Button type="button" variant="outline" onClick={onCancel}>
                    Cancel
                </Button>
                <Button type="submit" disabled={saving}>
                    {saving ? "Saving..." : entity ? "Update" : "Create"}
                </Button>
            </div>
        </form>
    );
}


import { useState, useEffect } from "react";
import { http } from "@/Lib/http";
import {
    X,
    Edit,
    Lock,
    ChevronDown,
    ChevronRight,
    BookOpen,
    Trash2,
} from "lucide-react";
import { Button } from "@/Components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/Components/ui/tabs";
import { Input } from "@/Components/ui/input";
import { Label } from "@/Components/ui/label";
import { Textarea } from "@/Components/ui/textarea";
import { useConfirm } from "@/Components/ConfirmDialogProvider";
import RelationshipsTab from "./RelationshipsTab";
import SettingsTab from "./SettingsTab";
import SummaryTab from "./SummaryTab";
import { toast } from "sonner";

// Protected fields that cannot be deleted (required by deconstructor)
const PROTECTED_FIELDS: Record<string, string[]> = {
    character: ["traits", "role", "emotional_state"],
    location: ["description", "atmosphere"],
    item: ["description", "significance"],
    // Theme and PlotPoint don't have deconstructor-required fields yet
    theme: [],
    plot_point: [],
};

interface Entity {
    vertex_id: string; // String to avoid JS precision loss with large Apache AGE IDs
    name: string;
    type: string;
    properties: Record<string, any>;
}

interface Relationship {
    edge_id: string; // String to avoid JS precision loss with large Apache AGE IDs
    source: string;
    target: string;
    relationship_type: string;
    properties?: Record<string, any>;
}

interface EntityDetailSidebarProps {
    entity: Entity | null;
    workspaceId: string;
    projectId: string;
    relationships: Relationship[];
    allEntities?: Entity[];
    onClose: () => void;
    onEntityUpdated: () => void;
    onRelationshipCreated: () => void;
    onRelationshipDeleted: () => void;
    onSavingChange?: (isSaving: boolean) => void;
}

export default function EntityDetailSidebar({
    entity,
    workspaceId,
    projectId,
    relationships,
    allEntities = [],
    onClose,
    onEntityUpdated,
    onRelationshipCreated,
    onRelationshipDeleted,
    onSavingChange,
}: EntityDetailSidebarProps) {
    const confirm = useConfirm();
    const [activeTab, setActiveTab] = useState("details");
    const [isEditing, setIsEditing] = useState(false);
    const [editedName, setEditedName] = useState("");
    const [editedProperties, setEditedProperties] = useState<
        Record<string, any>
    >({});
    const [newPropertyKey, setNewPropertyKey] = useState("");
    const [newPropertyValue, setNewPropertyValue] = useState("");
    const [saving, setSaving] = useState(false);
    const [expandedSummaries, setExpandedSummaries] = useState<Set<number>>(
        new Set(),
    );

    // Get summaries from edited properties, filtering out the _summaries key from regular properties display
    const getSummaries = (): Array<{
        chapter_number: number;
        chapter_name?: string;
        activity?: string;
        key_moments?: string[];
    }> => {
        const summaries = editedProperties._summaries;
        if (Array.isArray(summaries)) {
            return summaries;
        }
        return [];
    };

    // Toggle summary expansion
    const toggleSummaryExpansion = (chapterNumber: number) => {
        setExpandedSummaries((prev) => {
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
    const handleSummaryChange = (
        chapterNumber: number,
        field: string,
        value: any,
    ) => {
        const summaries = getSummaries();
        const updatedSummaries = summaries.map((s) =>
            s.chapter_number === chapterNumber ? { ...s, [field]: value } : s,
        );
        setEditedProperties({
            ...editedProperties,
            _summaries: updatedSummaries,
        });
    };

    // Delete a specific summary
    const handleDeleteSummary = async (chapterNumber: number) => {
        if (
            !(await confirm({
                title: "Delete chapter summary?",
                description: `Are you sure you want to delete the summary for Chapter ${chapterNumber}?`,
                actionLabel: "Delete summary",
            }))
        ) {
            return;
        }
        const summaries = getSummaries();
        const updatedSummaries = summaries.filter(
            (s) => s.chapter_number !== chapterNumber,
        );
        setEditedProperties({
            ...editedProperties,
            _summaries:
                updatedSummaries.length > 0 ? updatedSummaries : undefined,
        });
    };

    // Get properties excluding internal properties (for display in regular properties section)
    // Internal properties start with _ (like _summaries, _settings, _property_changes, etc.)
    const getDisplayProperties = () => {
        return Object.fromEntries(
            Object.entries(editedProperties).filter(
                ([key]) => !key.startsWith("_"),
            ),
        );
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

    // Filter relationships for this entity (only character entities have relationships)
    // Relationships can match by name OR by vertex_id
    const entityRelationships =
        entity && entity.name
            ? relationships.filter((rel) => {
                  // Match by entity name
                  const nameMatch =
                      rel.source === entity.name || rel.target === entity.name;
                  return nameMatch;
              })
            : [];

    // Debug logging
    console.log(
        "EntityDetailSidebar - Relationships debug:",
        JSON.stringify(
            {
                entityName: entity?.name,
                entityVertexId: entity?.vertex_id,
                relationshipsCount: relationships.length,
                entityRelationshipsCount: entityRelationships.length,
                allRelationships: relationships.map((r) => ({
                    source: r.source,
                    target: r.target,
                    type: r.relationship_type,
                })),
                filteredRelationships: entityRelationships.map((r) => ({
                    source: r.source,
                    target: r.target,
                    type: r.relationship_type,
                })),
            },
            null,
            2,
        ),
    );

    // Log each relationship to see its structure
    relationships.forEach((rel, idx) => {
        console.log(
            `Relationship ${idx}:`,
            JSON.stringify(
                {
                    source: rel.source,
                    target: rel.target,
                    type: rel.relationship_type,
                    matchesEntity:
                        rel.source === entity?.name ||
                        rel.target === entity?.name,
                    entityName: entity?.name,
                },
                null,
                2,
            ),
        );
    });

    // Check if this entity type supports relationships (only characters)
    const supportsRelationships = entity?.type?.toLowerCase() === "character";

    // Check if this entity type supports the Summary tab
    // Record Keeper entries don't have _summaries - they store data directly in properties
    const supportsSummaryTab = entity?.type?.toLowerCase() !== "record_keeper";

    // Get protected fields for this entity type
    const entityTypeKey = entity?.type?.toLowerCase() || "";
    const protectedFields = PROTECTED_FIELDS[entityTypeKey] || [];
    const isFieldProtected = (fieldName: string) =>
        protectedFields.includes(fieldName);

    useEffect(() => {
        if (entity) {
            setEditedName(entity.name);
            setEditedProperties(entity.properties || {});
            setIsEditing(false);
            setActiveTab("details");
        }
    }, [entity]);

    const handleSave = async () => {
        if (!entity) return;

        setSaving(true);
        onSavingChange?.(true);
        try {
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/records/entities/${entity.vertex_id}`,
                {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                    },
                    data: {
                        name: editedName,
                        properties: editedProperties,
                    },
                },
            );

            if (response.status >= 200 && response.status < 300) {
                setIsEditing(false);
                // Reload entity data to get updated properties
                const updatedResponse = await http(
                    `/${workspaceId}/projects/${projectId}/editor/records/entities/${entity.vertex_id}`,
                    {
                        headers: {
                            Accept: "application/json",
                        },
                    },
                );
                if (updatedResponse.status >= 200 && updatedResponse.status < 300) {
                    const updatedData = updatedResponse.data;
                    if (updatedData.entity) {
                        setEditedProperties(
                            updatedData.entity.properties || {},
                        );
                    }
                }
                onEntityUpdated();
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
            console.error("Error updating entity:", error);
            toast.error(
                `Failed to update entity: ${error?.message || String(error)}`,
            );
        } finally {
            setSaving(false);
            onSavingChange?.(false);
        }
    };

    if (!entity) {
        console.log("EntityDetailSidebar: No entity provided");
        return null;
    }

    // Ensure entity has required fields
    if (!entity.vertex_id || !entity.name) {
        console.error("EntityDetailSidebar: Invalid entity data:", entity);
        return (
            <div className="fixed inset-y-0 right-0 w-96 bg-white shadow-xl z-50 flex flex-col border-l p-4">
                <p className="text-red-500">Error: Invalid entity data</p>
                <Button onClick={onClose}>Close</Button>
            </div>
        );
    }

    return (
        <div className="fixed inset-y-0 right-0 w-96 bg-white shadow-xl z-50 flex flex-col border-l animate-in slide-in-from-right duration-300">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b">
                <h2 className="text-lg font-semibold">{entity.name}</h2>
                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setIsEditing(!isEditing)}
                        className="h-8 w-8"
                        title={isEditing ? "Cancel editing" : "Edit entity"}
                    >
                        <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onClose}
                        className="h-8 w-8"
                    >
                        <X className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            {/* Tabs */}
            <Tabs
                value={activeTab}
                onValueChange={setActiveTab}
                className="flex-1 flex flex-col overflow-hidden"
            >
                <TabsList className="mx-4 mt-4">
                    <TabsTrigger value="details">Details</TabsTrigger>
                    {supportsSummaryTab && (
                        <TabsTrigger value="summary">Summary</TabsTrigger>
                    )}
                    <TabsTrigger value="settings">Settings</TabsTrigger>
                    {supportsRelationships && (
                        <TabsTrigger value="relationships">
                            Relationships ({entityRelationships.length})
                        </TabsTrigger>
                    )}
                </TabsList>

                {/* Details Tab */}
                <TabsContent
                    value="details"
                    className="flex-1 overflow-y-auto p-4 space-y-4"
                >
                    {isEditing ? (
                        <>
                            <div>
                                <Label htmlFor="entity-name">Name</Label>
                                <Input
                                    id="entity-name"
                                    value={editedName}
                                    onChange={(e) =>
                                        setEditedName(e.target.value)
                                    }
                                />
                            </div>

                            <div>
                                <Label>Type</Label>
                                <Input value={entity.type || ""} disabled />
                            </div>

                            <div>
                                <Label>Properties</Label>
                                <p className="text-sm text-gray-500 mb-2">
                                    Add custom properties to store additional
                                    information (e.g., age, description, notes).
                                </p>
                                <div className="space-y-2 mt-2">
                                    {Object.entries(getDisplayProperties()).map(
                                        ([key, value]) => {
                                            const isProtected =
                                                isFieldProtected(key);
                                            return (
                                                <div
                                                    key={key}
                                                    className={`flex items-center gap-2 p-2 rounded ${
                                                        isProtected
                                                            ? "bg-blue-50 border border-blue-200"
                                                            : "bg-gray-50"
                                                    }`}
                                                >
                                                    <div className="flex items-center gap-2 flex-1">
                                                        {isProtected && (
                                                            <span title="Protected field (required by deconstructor)">
                                                                <Lock className="h-3 w-3 text-blue-600" />
                                                            </span>
                                                        )}
                                                        <div className="flex-1">
                                                            <span className="font-medium text-sm">
                                                                {key}:
                                                            </span>
                                                            {Array.isArray(
                                                                value,
                                                            ) ? (
                                                                <Textarea
                                                                    value={JSON.stringify(
                                                                        value,
                                                                        null,
                                                                        2,
                                                                    )}
                                                                    onChange={(
                                                                        e,
                                                                    ) => {
                                                                        try {
                                                                            const parsed =
                                                                                JSON.parse(
                                                                                    e
                                                                                        .target
                                                                                        .value,
                                                                                );
                                                                            if (
                                                                                Array.isArray(
                                                                                    parsed,
                                                                                )
                                                                            ) {
                                                                                setEditedProperties(
                                                                                    {
                                                                                        ...editedProperties,
                                                                                        [key]: parsed,
                                                                                    },
                                                                                );
                                                                            }
                                                                        } catch {
                                                                            // Invalid JSON, keep as is
                                                                        }
                                                                    }}
                                                                    className="mt-1 text-sm min-h-[60px]"
                                                                    placeholder='Enter JSON array, e.g., ["trait1", "trait2"]'
                                                                />
                                                            ) : (
                                                                <Input
                                                                    value={String(
                                                                        value,
                                                                    )}
                                                                    onChange={(
                                                                        e,
                                                                    ) => {
                                                                        setEditedProperties(
                                                                            {
                                                                                ...editedProperties,
                                                                                [key]: e
                                                                                    .target
                                                                                    .value,
                                                                            },
                                                                        );
                                                                    }}
                                                                    className="mt-1 h-8 text-sm"
                                                                    placeholder="Enter value"
                                                                />
                                                            )}
                                                        </div>
                                                    </div>
                                                    {!isProtected && (
                                                        <Button
                                                            type="button"
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => {
                                                                const newProps =
                                                                    {
                                                                        ...editedProperties,
                                                                    };
                                                                delete newProps[
                                                                    key
                                                                ];
                                                                setEditedProperties(
                                                                    newProps,
                                                                );
                                                            }}
                                                            title="Remove property"
                                                        >
                                                            <X className="h-4 w-4" />
                                                        </Button>
                                                    )}
                                                </div>
                                            );
                                        },
                                    )}

                                    {/* Add Property Inputs */}
                                    <div className="flex gap-2 pt-2 border-t">
                                        <Input
                                            id="new-property-key"
                                            placeholder="Property name (e.g., age)"
                                            value={newPropertyKey}
                                            onChange={(e) =>
                                                setNewPropertyKey(
                                                    e.target.value,
                                                )
                                            }
                                            onKeyPress={(e) => {
                                                if (e.key === "Enter") {
                                                    e.preventDefault();
                                                    handleAddProperty();
                                                }
                                            }}
                                        />
                                        <Input
                                            id="new-property-value"
                                            placeholder="Property value (e.g., 30)"
                                            value={newPropertyValue}
                                            onChange={(e) =>
                                                setNewPropertyValue(
                                                    e.target.value,
                                                )
                                            }
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

                            {/* Chapter Summaries Editing Section */}
                            {getSummaries().length > 0 && (
                                <div className="pt-4 border-t">
                                    <div className="flex items-center gap-2 mb-2">
                                        <BookOpen className="h-4 w-4 text-blue-600" />
                                        <Label>
                                            Chapter Summaries (
                                            {getSummaries().length})
                                        </Label>
                                    </div>
                                    <p className="text-xs text-gray-500 mb-3">
                                        Edit how this entity appears across
                                        chapters.
                                    </p>
                                    <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                                        {getSummaries()
                                            .sort(
                                                (a, b) =>
                                                    (a.chapter_number || 0) -
                                                    (b.chapter_number || 0),
                                            )
                                            .map((summary) => {
                                                const isExpanded =
                                                    expandedSummaries.has(
                                                        summary.chapter_number,
                                                    );
                                                return (
                                                    <div
                                                        key={`summary-edit-${summary.chapter_number}`}
                                                        className="border rounded-lg overflow-hidden bg-white"
                                                    >
                                                        {/* Summary Header - Collapsible */}
                                                        <button
                                                            type="button"
                                                            onClick={() =>
                                                                toggleSummaryExpansion(
                                                                    summary.chapter_number,
                                                                )
                                                            }
                                                            className="w-full flex items-center justify-between p-2 bg-linear-to-r from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 transition-colors"
                                                        >
                                                            <div className="flex items-center gap-2">
                                                                {isExpanded ? (
                                                                    <ChevronDown className="h-3 w-3 text-blue-600" />
                                                                ) : (
                                                                    <ChevronRight className="h-3 w-3 text-blue-600" />
                                                                )}
                                                                <span className="font-medium text-xs text-gray-800">
                                                                    Ch.{" "}
                                                                    {
                                                                        summary.chapter_number
                                                                    }
                                                                    :{" "}
                                                                    {summary.chapter_name ||
                                                                        "Untitled"}
                                                                </span>
                                                            </div>
                                                            <Button
                                                                type="button"
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={(
                                                                    e,
                                                                ) => {
                                                                    e.stopPropagation();
                                                                    handleDeleteSummary(
                                                                        summary.chapter_number,
                                                                    );
                                                                }}
                                                                className="h-6 w-6 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                                                                title="Delete this chapter summary"
                                                            >
                                                                <Trash2 className="h-3 w-3" />
                                                            </Button>
                                                        </button>

                                                        {/* Summary Content - Expandable */}
                                                        {isExpanded && (
                                                            <div className="p-2 space-y-2 border-t bg-gray-50/50">
                                                                {/* Activity */}
                                                                <div>
                                                                    <Label className="text-xs text-gray-600 mb-1 block">
                                                                        Activity
                                                                    </Label>
                                                                    <Textarea
                                                                        value={
                                                                            summary.activity ||
                                                                            ""
                                                                        }
                                                                        onChange={(
                                                                            e,
                                                                        ) =>
                                                                            handleSummaryChange(
                                                                                summary.chapter_number,
                                                                                "activity",
                                                                                e
                                                                                    .target
                                                                                    .value,
                                                                            )
                                                                        }
                                                                        placeholder="Describe what this entity does in this chapter..."
                                                                        className="min-h-20 text-xs"
                                                                    />
                                                                </div>

                                                                {/* Key Moments */}
                                                                <div>
                                                                    <Label className="text-xs text-gray-600 mb-1 block">
                                                                        Key
                                                                        Moments
                                                                    </Label>
                                                                    <Textarea
                                                                        value={
                                                                            Array.isArray(
                                                                                summary.key_moments,
                                                                            )
                                                                                ? summary.key_moments.join(
                                                                                      "\n",
                                                                                  )
                                                                                : summary.key_moments ||
                                                                                  ""
                                                                        }
                                                                        onChange={(
                                                                            e,
                                                                        ) => {
                                                                            const moments =
                                                                                e.target.value.split(
                                                                                    "\n",
                                                                                );
                                                                            handleSummaryChange(
                                                                                summary.chapter_number,
                                                                                "key_moments",
                                                                                moments,
                                                                            );
                                                                        }}
                                                                        placeholder="Enter key moments, one per line..."
                                                                        className="min-h-[60px] text-xs font-mono"
                                                                    />
                                                                    <p className="text-xs text-gray-400 mt-0.5">
                                                                        One
                                                                        moment
                                                                        per line
                                                                    </p>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                );
                                            })}
                                    </div>
                                </div>
                            )}

                            <div className="flex gap-2 pt-4">
                                <Button
                                    variant="outline"
                                    onClick={() => {
                                        setIsEditing(false);
                                        setEditedName(entity.name);
                                        setEditedProperties(
                                            entity.properties || {},
                                        );
                                    }}
                                >
                                    Cancel
                                </Button>
                                <Button onClick={handleSave} disabled={saving}>
                                    {saving ? "Saving..." : "Save"}
                                </Button>
                            </div>
                        </>
                    ) : (
                        <>
                            <div>
                                <Label>Name</Label>
                                <p className="text-sm text-gray-700 mt-1">
                                    {entity.name}
                                </p>
                            </div>

                            <div>
                                <Label>Type</Label>
                                <p className="text-sm text-gray-700 mt-1 capitalize">
                                    {(entity.type || "").replace("_", " ")}
                                </p>
                            </div>

                            {Object.keys(entity.properties || {}).filter(
                                (k) => !k.startsWith("_"),
                            ).length > 0 && (
                                <div>
                                    <Label>Properties</Label>
                                    <p className="text-xs text-gray-500 mb-2">
                                        Fields with a lock icon are protected
                                        and cannot be deleted (required by
                                        deconstructor).
                                    </p>
                                    <div className="space-y-2 mt-2">
                                        {Object.entries(entity.properties || {})
                                            .filter(
                                                ([key]) => !key.startsWith("_"),
                                            )
                                            .map(([key, value]) => {
                                                const isProtected =
                                                    isFieldProtected(key);
                                                return (
                                                    <div
                                                        key={key}
                                                        className={`p-2 rounded text-sm flex items-start gap-2 ${
                                                            isProtected
                                                                ? "bg-blue-50 border border-blue-200"
                                                                : "bg-gray-50"
                                                        }`}
                                                    >
                                                        {isProtected && (
                                                            <span title="Protected field (required by deconstructor)">
                                                                <Lock className="h-3 w-3 text-blue-600 mt-0.5 shrink-0" />
                                                            </span>
                                                        )}
                                                        <div className="flex-1">
                                                            <span className="font-medium">
                                                                {key}:
                                                            </span>{" "}
                                                            <span className="text-gray-600">
                                                                {Array.isArray(
                                                                    value,
                                                                )
                                                                    ? JSON.stringify(
                                                                          value,
                                                                      )
                                                                    : String(
                                                                          value,
                                                                      )}
                                                            </span>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </TabsContent>

                {/* Summary Tab (not shown for Record Keeper entries) */}
                {supportsSummaryTab && (
                    <TabsContent
                        value="summary"
                        className="flex-1 overflow-y-auto"
                    >
                        <SummaryTab
                            entity={entity}
                            workspaceId={workspaceId}
                            projectId={projectId}
                        />
                    </TabsContent>
                )}

                {/* Settings Tab */}
                <TabsContent
                    value="settings"
                    className="flex-1 overflow-y-auto"
                >
                    <SettingsTab
                        entity={entity}
                        workspaceId={workspaceId}
                        projectId={projectId}
                        onSettingsUpdated={onEntityUpdated}
                    />
                </TabsContent>

                {/* Relationships Tab (only for characters) */}
                {supportsRelationships && (
                    <TabsContent
                        value="relationships"
                        className="flex-1 overflow-y-auto p-4"
                    >
                        <RelationshipsTab
                            entity={entity}
                            entityRelationships={entityRelationships}
                            allRelationships={relationships}
                            allEntities={allEntities}
                            workspaceId={workspaceId}
                            projectId={projectId}
                            onRelationshipCreated={onRelationshipCreated}
                            onRelationshipDeleted={onRelationshipDeleted}
                            onRelationshipUpdated={onRelationshipDeleted}
                            onSavingChange={onSavingChange}
                        />
                    </TabsContent>
                )}
            </Tabs>
        </div>
    );
}

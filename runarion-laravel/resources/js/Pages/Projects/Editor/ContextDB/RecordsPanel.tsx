import { useState, useEffect } from "react";
import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { 
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";
import { Plus, Search, X } from "lucide-react";
import EntityList from "./EntityList";
import EntityForm from "./EntityForm";
import RelationshipForm from "./RelationshipForm";
import CollectionTypeForm from "./CollectionTypeForm";
import EntityDetailSidebar from "./EntityDetailSidebar";
import { http } from "@/Lib/http";
import { toast } from "sonner";
import { useConfirm } from "@/Components/ConfirmDialogProvider";

interface Entity {
    vertex_id: string;  // String to avoid JS precision loss with large Apache AGE IDs
    name: string;
    type: string;
    properties: Record<string, any>;
}

interface Relationship {
    edge_id: string;  // String to avoid JS precision loss with large Apache AGE IDs
    source: string;
    target: string;
    relationship_type: string;
    properties: Record<string, any>;
}

interface RecordsPanelProps {
    workspaceId: string;
    projectId: string;
    onSavingChange?: (isSaving: boolean) => void;
}

export default function RecordsPanel({ workspaceId, projectId, onSavingChange }: RecordsPanelProps) {
    const confirm = useConfirm();
    const [entities, setEntities] = useState<Entity[]>([]);
    const [relationships, setRelationships] = useState<Relationship[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedType, setSelectedType] = useState<string>("all");
    const [searchQuery, setSearchQuery] = useState("");
    const [isEntityFormOpen, setIsEntityFormOpen] = useState(false);
    const [isRelationshipFormOpen, setIsRelationshipFormOpen] = useState(false);
    const [isCollectionTypeFormOpen, setIsCollectionTypeFormOpen] = useState(false);
    const [editingEntity, setEditingEntity] = useState<Entity | null>(null);
    const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [collectionTypes, setCollectionTypes] = useState<Array<{value: string, label: string}>>([
        { value: "all", label: "All Types" },
        { value: "character", label: "Characters" },
        { value: "location", label: "Locations" },
        { value: "item", label: "Items" },
        { value: "theme", label: "Themes" },
        { value: "plot_point", label: "Plot Points" },
    ]);

    // Load entities
    const loadEntities = async () => {
        setLoading(true);
        try {
            const url = `/${workspaceId}/projects/${projectId}/editor/records/entities${selectedType !== "all" ? `?type=${selectedType}` : ""}`;
            const response = await http(url, {
                headers: {
                    "Accept": "application/json",
                },
            });
            
            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                const entitiesList = data.entities || [];
                
                // TEMPORARILY: Show all entities including duplicates so they can be deleted
                // TODO: Fix duplicate creation at source - entities should never be duplicated
                // Deduplicate by vertex_id but log duplicates for visibility
                const entityMap = new Map<string, Entity>();
                const duplicates: Entity[] = [];

                entitiesList.forEach((entity: Entity) => {
                    if (entityMap.has(entity.vertex_id)) {
                        duplicates.push(entity);
                        console.warn(`Duplicate entity found: vertex_id=${entity.vertex_id}, name="${entity.name}"`);
                    } else {
                        entityMap.set(entity.vertex_id, entity);
                    }
                });
                
                if (duplicates.length > 0) {
                    console.error(`Found ${duplicates.length} duplicate entities - these should not exist!`, duplicates);
                }
                
                // Filter out internal/metadata entities before setting state
                const visibleEntities = entitiesList.filter((entity: Entity) => {
                    const type = (entity.type || "").toLowerCase();
                    const name = (entity.name || "").toLowerCase();
                    
                    // Hide internal types
                    if (type.startsWith('_')) return false;
                    if (type.includes('scan') && type.includes('metadata')) return false;
                    if (type === 'auditscanmetadata' || type === 'audit_scan_metadata') return false;
                    if (name.includes('auditscanmetadata') || name.includes('_auditscanmetadata')) return false;
                    
                    return true;
                });
                
                setEntities(visibleEntities);
            } else {
                // Handle non-OK responses
                const errorData = response.data.catch(() => ({ error: "Unknown error" }));
                console.error("Failed to load entities:", response.status, errorData);
                setEntities([]); // Set empty array on error to prevent white screen
            }
        } catch (error) {
            console.error("Error loading entities:", error);
            setEntities([]); // Set empty array on error to prevent white screen
        } finally {
            setLoading(false);
        }
    };

    // Load relationships
    const loadRelationships = async () => {
        try {
            const url = `/${workspaceId}/projects/${projectId}/editor/records/relationships`;
            const response = await http(url, {
                headers: {
                    "Accept": "application/json",
                },
            });
            
            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                console.log("Loaded relationships:", JSON.stringify(data.relationships, null, 2));
                if (data.relationships?.[0]) {
                    console.log("First relationship structure:", JSON.stringify(data.relationships[0], null, 2));
                }
                setRelationships(data.relationships || []);
            } else {
                console.error("Failed to load relationships:", response.status, response.statusText);
            }
        } catch (error) {
            console.error("Error loading relationships:", error);
        }
    };

    // Load collection types
    const loadCollectionTypes = async () => {
        try {
            const url = `/${workspaceId}/projects/${projectId}/editor/records/collection-types`;
            const response = await http(url, {
                headers: {
                    "Accept": "application/json",
                },
            });
            
            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                const systemTypes = [
                    { value: "all", label: "All Types" },
                    { value: "character", label: "Characters" },
                    { value: "location", label: "Locations" },
                    { value: "item", label: "Items" },
                    { value: "theme", label: "Themes" },
                    { value: "plot_point", label: "Plot Points" },
                    { value: "record_keeper", label: "Record Keeper" },
                ];
                const customTypes = (data.collection_types?.custom || []).map((type: any) => ({
                    value: type.name.toLowerCase().replace(/\s+/g, '_'),
                    label: type.name,
                }));
                setCollectionTypes([...systemTypes, ...customTypes]);
            }
        } catch (error) {
            console.error("Error loading collection types:", error);
        }
    };

    useEffect(() => {
        loadCollectionTypes();
        loadEntities();
        loadRelationships();
    }, [workspaceId, projectId, selectedType]);

    // Listen for entity extraction events to refresh entities
    useEffect(() => {
        const handleEntitiesExtracted = (event: CustomEvent) => {
            console.log('Entities extracted, refreshing entity list...', event.detail);
            // Force reload entities with current selectedType
            loadEntities();
            loadRelationships();
        };

        window.addEventListener('entities-extracted', handleEntitiesExtracted as EventListener);
        
        return () => {
            window.removeEventListener('entities-extracted', handleEntitiesExtracted as EventListener);
        };
    }, [workspaceId, projectId, selectedType]); // Add selectedType to dependencies

    // Filter entities by search query AND by selected type
    const filteredEntities = entities.filter(entity => {
        // Search filter
        if (!entity.name.toLowerCase().includes(searchQuery.toLowerCase())) {
            return false;
        }
        // Type filter (if not "all")
        if (selectedType !== "all") {
            const normalizedFilter = selectedType.toLowerCase().replace(/_/g, ' ');
            const normalizedType = (entity.type || '').toLowerCase().replace(/_/g, ' ');
            if (normalizedFilter !== normalizedType) {
                return false;
            }
        }
        return true;
    });

    const handleCreateEntity = () => {
        setEditingEntity(null);
        setIsEntityFormOpen(true);
    };

    const handleEditEntity = (entity: Entity) => {
        // Edit now opens sidebar instead of modal
        setSelectedEntity(entity);
        setIsSidebarOpen(true);
    };

    const handleSelectEntity = (entity: Entity) => {
        console.log("Selecting entity:", entity);
        if (!entity || !entity.vertex_id) {
            console.error("Invalid entity selected:", entity);
            return;
        }
        // Ensure entity has type field
        if (!entity.type) {
            // Try to get type from the entities list
            const fullEntity = entities.find(e => e.vertex_id === entity.vertex_id);
            if (fullEntity) {
                entity.type = fullEntity.type;
            }
        }
        setSelectedEntity(entity);
        setIsSidebarOpen(true);
    };

    const handleCloseSidebar = () => {
        setIsSidebarOpen(false);
        setSelectedEntity(null);
    };

    const handleDeleteEntity = async (vertexId: string) => {
        if (
            !(await confirm({
                title: "Delete entity?",
                description: "Are you sure you want to delete this entity?",
                actionLabel: "Delete entity",
            }))
        ) {
            return;
        }

        onSavingChange?.(true);
        try {
            console.log(`Attempting to delete entity with vertex_id: ${vertexId}`);
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/records/entities/${vertexId}`,
                {
                    method: "DELETE",
                    headers: {
                        "Accept": "application/json",
                    },
                }
            );

            const responseData = response.data;
            console.log(`Delete response status: ${response.status}`, responseData);

            if (response.status >= 200 && response.status < 300) {
                if (responseData.success) {
                    console.log(`Successfully deleted entity ${vertexId}`);
                loadEntities();
                loadRelationships(); // Reload relationships in case any were deleted
                } else {
                    toast.error(
                        `Failed to delete entity: ${responseData.error || "Unknown error"}`,
                    );
                }
            } else {
                let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                if (responseData.error) {
                    errorMessage = responseData.error;
                } else if (responseData.details) {
                    errorMessage = responseData.details.error || errorMessage;
                }
                console.error("Delete failed:", errorMessage, responseData);
                toast.error(`Error deleting entity: ${errorMessage}`);
            }
        } catch (error) {
            console.error("Error deleting entity:", error);
            toast.error(`Failed to delete entity: ${error}`);
        } finally {
            onSavingChange?.(false);
        }
    };

    const handleBulkDelete = async (vertexIds: string[]) => {
        if (vertexIds.length === 0) {
            return;
        }

        onSavingChange?.(true);
        try {
            console.log(`Attempting to delete ${vertexIds.length} entities`);

            // Delete entities sequentially to avoid overwhelming the server
            let successCount = 0;
            let failCount = 0;
            const errors: string[] = [];

            for (const vertexId of vertexIds) {
                try {
                    const response = await http(
                        `/${workspaceId}/projects/${projectId}/editor/records/entities/${vertexId}`,
                        {
                            method: "DELETE",
                            headers: {
                                "Accept": "application/json",
                            },
                        }
                    );

                    const responseData = response.data;

                    if (response.status >= 200 && response.status < 300 && responseData.success) {
                        successCount++;
                    } else {
                        failCount++;
                        errors.push(`Entity ${vertexId}: ${responseData.error || 'Unknown error'}`);
                    }
                } catch (error) {
                    failCount++;
                    errors.push(`Entity ${vertexId}: ${error}`);
                }
            }

            // Reload entities and relationships after bulk delete
            loadEntities();
            loadRelationships();

            // Show results
            if (failCount === 0) {
                toast.success(
                    `Successfully deleted ${successCount} entity/entities.`,
                );
            } else {
                toast.info(
                    `Deleted ${successCount} entity/entities.\n` +
                    `Failed to delete ${failCount} entity/entities.\n\n` +
                    `Errors:\n${errors.slice(0, 5).join('\n')}${errors.length > 5 ? `\n... and ${errors.length - 5} more` : ''}`
                );
            }
        } catch (error) {
            console.error("Error in bulk delete:", error);
            toast.error(`Failed to delete entities: ${error}`);
        } finally {
            onSavingChange?.(false);
        }
    };

    const handleCreateRelationship = () => {
        setIsRelationshipFormOpen(true);
    };

    const handleEntitySaved = () => {
        setIsEntityFormOpen(false);
        setEditingEntity(null);
        loadEntities();
    };

    const handleRelationshipSaved = () => {
        setIsRelationshipFormOpen(false);
        loadRelationships();
    };

    const handleCollectionTypeSaved = () => {
        setIsCollectionTypeFormOpen(false);
        loadCollectionTypes();
    };

    const handleDeleteCollectionType = async (typeValue: string, typeLabel: string) => {
        if (
            !(await confirm({
                title: "Delete collection type?",
                description: `Are you sure you want to delete the "${typeLabel}" collection type? This cannot be undone.`,
                actionLabel: "Delete collection type",
            }))
        ) {
            return;
        }

        onSavingChange?.(true);
        try {
            // Find the type ID from the collection types
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/records/collection-types`,
                {
                    headers: {
                        "Accept": "application/json",
                    },
                }
            );

            if (response.status >= 200 && response.status < 300) {
                const data = response.data;
                const customType = data.collection_types?.custom?.find(
                    (t: any) => t.name.toLowerCase().replace(/\s+/g, '_') === typeValue
                );

                if (!customType) {
                    toast.info("Collection type not found");
                    return;
                }

                const deleteResponse = await http(
                    `/${workspaceId}/projects/${projectId}/editor/records/collection-types/${customType.id}`,
                    {
                        method: "DELETE",
                        headers: {
                            "Accept": "application/json",
                        },
                    }
                );

                if (deleteResponse.status >= 200 && deleteResponse.status < 300) {
                    loadCollectionTypes();
                    if (selectedType === typeValue) {
                        setSelectedType("all");
                    }
                } else {
                    const error = deleteResponse.data;
                    toast.error(
                        error.error || "Failed to delete collection type",
                    );
                }
            }
        } catch (error: any) {
            console.error("Error deleting collection type:", error);
            toast.error(
                `Failed to delete collection type: ${error?.message || String(error)}`,
            );
        } finally {
            onSavingChange?.(false);
        }
    };

    return (
        <div className="flex h-full">
            {/* Left Sidebar - Collection Types */}
            <div className="w-64 border-r bg-gray-50 p-4">
                <div className="mb-4">
                    <div className="flex items-center justify-between mb-2">
                        <h3 className="text-sm font-semibold text-gray-700">
                            Collection Type
                        </h3>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setIsCollectionTypeFormOpen(true)}
                            className="h-6 w-6 px-2 text-xs"
                        >
                            <Plus className="h-3 w-3" />
                        </Button>
                    </div>
                    <div className="space-y-1">
                        {collectionTypes.map((type) => {
                            const isSystemType = ["all", "character", "location", "item", "theme", "plot_point", "record_keeper"].includes(type.value);
                            const isCustom = !isSystemType;
                            
                            return (
                                <div
                                    key={type.value}
                                    className={`group flex items-center justify-between ${
                                        selectedType === type.value
                                            ? "bg-blue-100 text-blue-700 font-medium"
                                            : "text-gray-600 hover:bg-gray-100"
                                    } rounded`}
                                >
                                    <button
                                        onClick={() => setSelectedType(type.value)}
                                        className="flex-1 text-left px-3 py-2 text-sm"
                                    >
                                        {type.label}
                                    </button>
                                    {isCustom && (
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-6 w-6 opacity-0 group-hover:opacity-100 text-red-500 hover:text-red-700"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleDeleteCollectionType(type.value, type.label);
                                            }}
                                        >
                                            <X className="h-3 w-3" />
                                        </Button>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 flex flex-col">
                {/* Header */}
                <div className="border-b p-4 flex items-center justify-between">
                    <div className="flex-1 flex items-center gap-4">
                        <div className="relative flex-1 max-w-md">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                            <Input
                                placeholder="Search for entities..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="pl-10"
                            />
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={handleCreateRelationship}
                        >
                            <Plus className="h-4 w-4 mr-2" />
                            New Relationship
                        </Button>
                        <Button
                            onClick={handleCreateEntity}
                            size="sm"
                        >
                            <Plus className="h-4 w-4 mr-2" />
                            New Entity
                        </Button>
                    </div>
                </div>

                {/* Entity List */}
                <div className="flex-1 overflow-auto p-4">
                    {loading ? (
                        <div className="text-center py-8 text-gray-500">
                            Loading entities...
                        </div>
                    ) : filteredEntities.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                            {searchQuery
                                ? "No entities found matching your search."
                                : "No entities yet. Create your first entity!"}
                        </div>
                    ) : (
                        <EntityList
                            entities={filteredEntities}
                            relationships={relationships}
                            onEdit={handleEditEntity}
                            onDelete={handleDeleteEntity}
                            onBulkDelete={handleBulkDelete}
                            onSelect={handleSelectEntity}
                            selectedEntity={selectedEntity}
                            showGrouped={selectedType === "all"}
                        />
                    )}
                </div>
            </div>

            {/* Entity Form Dialog */}
            <Dialog open={isEntityFormOpen} onOpenChange={setIsEntityFormOpen}>
                <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>
                            {editingEntity ? "Edit Entity" : "Create New Entity"}
                        </DialogTitle>
                    </DialogHeader>
                    <EntityForm
                        workspaceId={workspaceId}
                        projectId={projectId}
                        entity={editingEntity}
                        onSaved={handleEntitySaved}
                        onCancel={() => setIsEntityFormOpen(false)}
                        onSavingChange={onSavingChange}
                    />
                </DialogContent>
            </Dialog>

            {/* Relationship Form Dialog */}
            <Dialog open={isRelationshipFormOpen} onOpenChange={setIsRelationshipFormOpen}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>
                            {selectedEntity && selectedEntity?.type?.toLowerCase() === 'character'
                                ? `Create Relationship for ${selectedEntity.name}`
                                : "Create New Relationship"}
                        </DialogTitle>
                    </DialogHeader>
                    <RelationshipForm
                        workspaceId={workspaceId}
                        projectId={projectId}
                        entities={entities}
                        defaultSource={selectedEntity && selectedEntity?.type?.toLowerCase() === 'character' ? selectedEntity.vertex_id.toString() : undefined}
                        onSaved={() => {
                            handleRelationshipSaved();
                            if (selectedEntity) {
                                // Keep sidebar open and refresh relationships
                                loadRelationships();
                            }
                        }}
                        onCancel={() => setIsRelationshipFormOpen(false)}
                        onSavingChange={onSavingChange}
                    />
                </DialogContent>
            </Dialog>

            {/* Collection Type Form Dialog */}
            <Dialog open={isCollectionTypeFormOpen} onOpenChange={setIsCollectionTypeFormOpen}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>Create New Collection Type</DialogTitle>
                    </DialogHeader>
                    <CollectionTypeForm
                        workspaceId={workspaceId}
                        projectId={projectId}
                        onSaved={handleCollectionTypeSaved}
                        onCancel={() => setIsCollectionTypeFormOpen(false)}
                        onSavingChange={onSavingChange}
                    />
                </DialogContent>
            </Dialog>

            {/* Backdrop overlay */}
            {isSidebarOpen && (
                <div
                    className="fixed inset-0 bg-black/20 z-40"
                    onClick={handleCloseSidebar}
                />
            )}

            {/* Entity Detail Sidebar */}
            {isSidebarOpen && selectedEntity && (
                <>
                    <EntityDetailSidebar
                        entity={selectedEntity}
                        workspaceId={workspaceId}
                        projectId={projectId}
                        onSavingChange={onSavingChange}
                    relationships={relationships.filter(
                        (rel) => {
                            // Only show character-to-character relationships
                            const sourceEntity = entities.find(e => e.name === rel.source);
                            const targetEntity = entities.find(e => e.name === rel.target);
                            
                            // If entities aren't found or don't have type, include the relationship (for now)
                            // This allows relationships to show even if entity types aren't set yet
                            if (!sourceEntity || !targetEntity || !sourceEntity?.type || !targetEntity?.type) {
                                console.log("Including relationship (missing entity or type):", {
                                    rel: { source: rel.source, target: rel.target },
                                    sourceEntity: sourceEntity ? { name: sourceEntity.name, type: sourceEntity.type } : null,
                                    targetEntity: targetEntity ? { name: targetEntity.name, type: targetEntity.type } : null
                                });
                                return true; // Include if type is missing (assume character for now)
                            }
                            
                            const isCharacterToCharacter = sourceEntity.type.toLowerCase() === 'character' && 
                                   targetEntity.type.toLowerCase() === 'character';
                            
                            if (!isCharacterToCharacter) {
                                console.log("Filtered out non-character relationship:", {
                                    rel: { source: rel.source, target: rel.target },
                                    sourceType: sourceEntity.type,
                                    targetType: targetEntity.type
                                });
                            }
                            
                            return isCharacterToCharacter;
                        }
                    )}
                    allEntities={entities}
                    onClose={handleCloseSidebar}
                        onEntityUpdated={async () => {
                            await loadEntities();
                            await loadRelationships();
                            // Refresh the selected entity data after entities are loaded
                            if (selectedEntity) {
                                try {
                                    const response = await http(`/${workspaceId}/projects/${projectId}/editor/records/entities/${selectedEntity.vertex_id}?project_id=${projectId}`, {
                                        headers: { "Accept": "application/json" },
                                    });
                                    const data = response.data;
                                    console.log("RecordsPanel: Reloaded entity after update:", data);
                                    if (data.entity) {
                                        console.log("RecordsPanel: Entity properties:", data.entity.properties);
                                        setSelectedEntity(data.entity);
                                    }
                                } catch (err) {
                                    console.error("Error refreshing entity:", err);
                                }
                            }
                        }}
                        onRelationshipCreated={() => {
                            setIsRelationshipFormOpen(true);
                        }}
                        onRelationshipDeleted={() => {
                            loadRelationships();
                        }}
                    />
                </>
            )}
        </div>
    );
}

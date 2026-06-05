import React, { useState, useEffect } from "react";
import { Trash2, ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "@/Components/ui/button";
import { Checkbox } from "@/Components/ui/checkbox";

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
}

interface EntityListProps {
    entities: Entity[];
    relationships: Relationship[];
    onEdit: (entity: Entity) => void;
    onDelete: (vertexId: string) => void;
    onBulkDelete?: (vertexIds: string[]) => void; // Optional bulk delete handler
    onSelect: (entity: Entity) => void;
    selectedEntity: Entity | null;
    showGrouped?: boolean; // If true, group by type when showing all
}

export default function EntityList({
    entities,
    onDelete,
    onBulkDelete,
    onSelect,
    selectedEntity,
    showGrouped = false,
}: EntityListProps) {
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    
    // Filter out internal/metadata entities (types starting with _ or internal tracking types)
    const visibleEntities = entities.filter(entity => {
        const type = (entity.type || "").toLowerCase();
        const name = (entity.name || "").toLowerCase();
        
        // Hide internal types:
        // - Types starting with underscore (_scan_metadata, _AuditScanMetadata)
        // - Audit/scan metadata entities by type or name
        if (type.startsWith('_')) return false;
        if (type.includes('scan') && type.includes('metadata')) return false;
        if (type === 'auditscanmetadata' || type === 'audit_scan_metadata') return false;
        if (name.includes('auditscanmetadata') || name.includes('_auditscanmetadata')) return false;
        
        return true;
    });
    
    // Group entities by type (calculate at top level)
    const groupedEntities = showGrouped
        ? visibleEntities.reduce((acc, entity) => {
              const type = entity.type || "other";
              if (!acc[type]) {
                  acc[type] = [];
              }
              acc[type].push(entity);
              return acc;
          }, {} as Record<string, Entity[]>)
        : null;
    
    // Initialize expandedCategories with all categories when grouped view is enabled
    const [expandedCategories, setExpandedCategories] = useState<Set<string>>(() => {
        if (showGrouped && groupedEntities) {
            return new Set(Object.keys(groupedEntities));
        }
        return new Set();
    });
    
    // Get activation keys from entity settings
    const getActivationKeys = (entity: Entity): string[] => {
        const settings = entity.properties?._settings;
        if (settings && settings.activationKeys && Array.isArray(settings.activationKeys)) {
            return settings.activationKeys;
        }
        return [];
    };

    // Format date (fallback to placeholder if not available)
    const getCreatedDate = (entity: Entity): string => {
        // Try to get from entity object (from metadata table)
        const created = (entity as any).created_at || 
                       entity.properties?.created_at || 
                       entity.properties?.createdAt;
        if (created) {
            try {
                const date = new Date(created);
                if (!isNaN(date.getTime())) {
                    return date.toLocaleDateString('en-US', { 
                        year: 'numeric', 
                        month: 'short', 
                        day: 'numeric' 
                    });
                }
            } catch {
                // Fall through to default
            }
        }
        // Default to a placeholder
        return "—"; // Use em dash for missing date
    };

    // Update selectedIds when entities change (remove deleted entities)
    useEffect(() => {
        const entityIds = new Set(visibleEntities.map(e => e.vertex_id));
        setSelectedIds(prev => {
            const filtered = new Set<string>();
            prev.forEach(id => {
                if (entityIds.has(id)) {
                    filtered.add(id);
                }
            });
            return filtered;
        });
    }, [entities]);
    
    // Expand all categories only when first switching to grouped view
    // Don't re-expand when entities change (preserve user's collapse state)
    useEffect(() => {
        if (showGrouped && groupedEntities) {
            // Only set initial expanded state, don't override user actions
            setExpandedCategories(prev => {
                if (prev.size === 0) {
                    // Initial state - expand all categories
                    return new Set(Object.keys(groupedEntities));
                }
                // User has interacted - preserve their collapsed/expanded choices
                return prev;
            });
        }
    }, [showGrouped]); // Deliberately NOT including groupedEntities to avoid resetting on data changes

    // Toggle selection for a single entity
    const toggleSelection = (vertexId: string, event?: React.MouseEvent) => {
        if (event) {
            event.stopPropagation();
        }
        setSelectedIds(prev => {
            const next = new Set(prev);
            if (next.has(vertexId)) {
                next.delete(vertexId);
            } else {
                next.add(vertexId);
            }
            return next;
        });
    };

    // Toggle select all
    const toggleSelectAll = () => {
        if (selectedIds.size === visibleEntities.length && visibleEntities.length > 0) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(visibleEntities.map(e => e.vertex_id)));
        }
    };

    // Handle bulk delete
    const handleBulkDelete = (event?: React.MouseEvent) => {
        if (event) {
            event.stopPropagation();
        }
        if (selectedIds.size === 0) {
            return;
        }
        if (!confirm(`Are you sure you want to delete ${selectedIds.size} selected entity/entities?`)) {
            return;
        }
        if (onBulkDelete) {
            onBulkDelete(Array.from(selectedIds));
            setSelectedIds(new Set());
        }
    };

    // If grouped, render by category
    if (showGrouped && groupedEntities) {
        const toggleCategory = (category: string) => {
            setExpandedCategories((prev) => {
                const next = new Set(prev);
                if (next.has(category)) {
                    next.delete(category);
                } else {
                    next.add(category);
                }
                return next;
            });
        };

        // Calculate totals for bulk actions
        const totalSelected = selectedIds.size;

        return (
            <div className="space-y-4">
                {/* Bulk Actions Bar for Grouped View */}
                {totalSelected > 0 && onBulkDelete && (
                    <div className="bg-blue-50 border rounded-lg px-4 py-2 flex items-center justify-between">
                        <span className="text-sm text-blue-900 font-medium">
                            {totalSelected} entity/entities selected
                        </span>
                        <Button
                            variant="destructive"
                            size="sm"
                            onClick={handleBulkDelete}
                        >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete Selected ({totalSelected})
                        </Button>
                    </div>
                )}

                {Object.entries(groupedEntities)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([category, categoryEntities]) => {
                        const isExpanded = expandedCategories.has(category);
                        return (
                            <div key={category} className="border rounded-lg overflow-hidden">
                                {/* Category Header */}
                                <div
                                    className="bg-gray-100 px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-gray-200 transition-colors"
                                    onClick={() => toggleCategory(category)}
                                >
                                    <div className="flex items-center gap-2">
                                        {isExpanded ? (
                                            <ChevronDown className="h-4 w-4 text-gray-600" />
                                        ) : (
                                            <ChevronRight className="h-4 w-4 text-gray-600" />
                                        )}
                                        <h3 className="font-semibold text-gray-900 capitalize">
                                            {category.replace(/_/g, " ")} ({categoryEntities.length})
                                        </h3>
                                    </div>
                                </div>

                                {/* Category Content */}
                                {isExpanded && (
                                    <div className="bg-white">
                                        {/* Table Header */}
                                        <div className="grid grid-cols-12 gap-4 px-4 py-3 border-b bg-gray-50 text-sm font-medium text-gray-700">
                                            <div className="col-span-1 flex items-center">
                                                <Checkbox
                                                    checked={categoryEntities.length > 0 && categoryEntities.every(e => selectedIds.has(e.vertex_id))}
                                                    onCheckedChange={() => {
                                                        const categoryIds = categoryEntities.map(e => e.vertex_id);
                                                        const allSelected = categoryIds.every(id => selectedIds.has(id));
                                                        setSelectedIds(prev => {
                                                            const next = new Set(prev);
                                                            if (allSelected) {
                                                                categoryIds.forEach(id => next.delete(id));
                                                            } else {
                                                                categoryIds.forEach(id => next.add(id));
                                                            }
                                                            return next;
                                                        });
                                                    }}
                                                    onClick={(e) => e.stopPropagation()}
                                                />
                                            </div>
                                            <div className="col-span-3">Name</div>
                                            <div className="col-span-3">Created At</div>
                                            <div className="col-span-4">Activation Keys</div>
                                            <div className="col-span-1 text-right">Delete</div>
                                        </div>

                                        {/* Table Rows */}
                                        <div className="divide-y">
                                            {categoryEntities.map((entity) => {
                                                const isSelected = selectedEntity?.vertex_id === entity.vertex_id;
                                                const activationKeys = getActivationKeys(entity);
                                                const createdDate = getCreatedDate(entity);

                                                return (
                                                    <div
                                                        key={entity.vertex_id}
                                                        className={`grid grid-cols-12 gap-4 px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors ${
                                                            isSelected ? "bg-blue-50" : ""
                                                        } ${selectedIds.has(entity.vertex_id) ? "bg-blue-100" : ""}`}
                                                        onClick={(e) => {
                                                            e.preventDefault();
                                                            e.stopPropagation();
                                                            onSelect(entity);
                                                        }}
                                                    >
                                                        <div className="col-span-1 flex items-center">
                                                            <Checkbox
                                                                checked={selectedIds.has(entity.vertex_id)}
                                                                onCheckedChange={() => toggleSelection(entity.vertex_id)}
                                                                onClick={(e) => e.stopPropagation()}
                                                            />
                                                        </div>
                                                        <div className="col-span-3">
                                                            <div className="font-medium text-gray-900">
                                                                {entity.name}
                                                            </div>
                                                        </div>
                                                        <div className="col-span-3 text-sm text-gray-600">
                                                            {createdDate}
                                                        </div>
                                                        <div className="col-span-4">
                                                            {activationKeys.length > 0 ? (
                                                                <div className="flex flex-wrap gap-1">
                                                                    {activationKeys.slice(0, 3).map((key, idx) => (
                                                                        <span
                                                                            key={idx}
                                                                            className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded"
                                                                        >
                                                                            {key}
                                                                        </span>
                                                                    ))}
                                                                    {activationKeys.length > 3 && (
                                                                        <span className="text-xs text-gray-500">
                                                                            +{activationKeys.length - 3}
                                                                        </span>
                                                                    )}
                                                                </div>
                                                            ) : (
                                                                <span className="text-sm text-gray-400 italic">
                                                                    No keys
                                                                </span>
                                                            )}
                                                        </div>
                                                        <div className="col-span-1 flex justify-end">
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={(e) => {
                                                                    e.preventDefault();
                                                                    e.stopPropagation();
                                                                    onDelete(entity.vertex_id);
                                                                }}
                                                                className="text-red-500 hover:text-red-700 hover:bg-red-50"
                                                            >
                                                                <Trash2 className="h-4 w-4" />
                                                            </Button>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
            </div>
        );
    }

    // Non-grouped view (table format)
    const allSelected = visibleEntities.length > 0 && visibleEntities.every(e => selectedIds.has(e.vertex_id));
    return (
        <div className="border rounded-lg overflow-hidden bg-white">
            {/* Bulk Actions Bar */}
            {selectedIds.size > 0 && onBulkDelete && (
                <div className="bg-blue-50 border-b px-4 py-2 flex items-center justify-between">
                    <span className="text-sm text-blue-900 font-medium">
                        {selectedIds.size} entity/entities selected
                    </span>
                    <Button
                        variant="destructive"
                        size="sm"
                        onClick={handleBulkDelete}
                    >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete Selected ({selectedIds.size})
                    </Button>
                </div>
            )}

            {/* Table Header */}
            <div className="grid grid-cols-12 gap-4 px-4 py-3 border-b bg-gray-50 text-sm font-medium text-gray-700">
                <div className="col-span-1 flex items-center">
                    <Checkbox
                        checked={allSelected}
                        onCheckedChange={toggleSelectAll}
                    />
                </div>
                <div className="col-span-3">Name</div>
                <div className="col-span-3">Created At</div>
                <div className="col-span-4">Activation Keys</div>
                <div className="col-span-1 text-right">Delete</div>
            </div>

            {/* Table Rows */}
            <div className="divide-y">
                {visibleEntities.map((entity) => {
                    const isSelected = selectedEntity?.vertex_id === entity.vertex_id;
                    const activationKeys = getActivationKeys(entity);
                    const createdDate = getCreatedDate(entity);

                    return (
                        <div
                            key={entity.vertex_id}
                            className={`grid grid-cols-12 gap-4 px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors ${
                                isSelected ? "bg-blue-50" : ""
                            } ${selectedIds.has(entity.vertex_id) ? "bg-blue-100" : ""}`}
                            onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                onSelect(entity);
                            }}
                        >
                            <div className="col-span-1 flex items-center">
                                <Checkbox
                                    checked={selectedIds.has(entity.vertex_id)}
                                    onCheckedChange={() => toggleSelection(entity.vertex_id)}
                                    onClick={(e) => e.stopPropagation()}
                                />
                            </div>
                            <div className="col-span-3">
                                <div className="font-medium text-gray-900">{entity.name}</div>
                                <div className="text-xs text-gray-500 mt-0.5 capitalize">
                                    {entity.type?.replace(/_/g, " ")}
                                </div>
                            </div>
                            <div className="col-span-3 text-sm text-gray-600">
                                {createdDate}
                            </div>
                            <div className="col-span-4">
                                {activationKeys.length > 0 ? (
                                    <div className="flex flex-wrap gap-1">
                                        {activationKeys.slice(0, 3).map((key, idx) => (
                                            <span
                                                key={idx}
                                                className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded"
                                            >
                                                {key}
                                            </span>
                                        ))}
                                        {activationKeys.length > 3 && (
                                            <span className="text-xs text-gray-500">
                                                +{activationKeys.length - 3}
                                            </span>
                                        )}
                                    </div>
                                ) : (
                                    <span className="text-sm text-gray-400 italic">No keys</span>
                                )}
                            </div>
                            <div className="col-span-1 flex justify-end">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        onDelete(entity.vertex_id);
                                    }}
                                    className="text-red-500 hover:text-red-700 hover:bg-red-50"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

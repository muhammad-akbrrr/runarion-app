import React, { useState, useEffect } from "react";
import { Entity } from "../types";
import { Book, Filter } from "lucide-react";
import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { formatEntityForContext } from "../utils/formatEntityForContext";

interface RecordsDrawerProps {
    workspaceId: string;
    projectId: string;
    onEntityDrop: (entity: Entity, position: { x: number; y: number }) => void;
}

export const RecordsDrawer: React.FC<RecordsDrawerProps> = ({
    workspaceId,
    projectId,
    onEntityDrop,
}) => {
    const [entities, setEntities] = useState<Entity[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedType, setSelectedType] = useState<string>("all");
    const [searchQuery, setSearchQuery] = useState("");
    const [entityTypes, setEntityTypes] = useState<
        Array<{ value: string; label: string; vertexLabel?: string }>
    >([{ value: "all", label: "All Types" }]);

    useEffect(() => {
        loadCollectionTypes();
        loadEntities();
    }, [selectedType, workspaceId, projectId]);

    const loadCollectionTypes = async () => {
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/records/collection-types`,
                {
                    headers: {
                        Accept: "application/json",
                    },
                },
            );

            if (response.ok) {
                const data = await response.json();
                // System types: use the id (character, location, etc.) which matches entity.type
                const systemTypes = (data.collection_types?.system || []).map(
                    (t: any) => ({
                        value: t.id, // e.g., 'character', 'location' - this matches entity.type
                        label: t.name,
                    }),
                );
                // Custom types: use vertex_label or name (normalized) as value
                // The entity.type field uses the vertex_label from the collection type
                const customTypes = (data.collection_types?.custom || []).map(
                    (t: any) => {
                        // Use vertex_label if available, otherwise normalize the name
                        const typeValue = (t.vertex_label || t.name)
                            .toLowerCase()
                            .replace(/\s+/g, "_");
                        return {
                            value: typeValue,
                            label: t.name,
                            vertexLabel: t.vertex_label || t.name, // Store for API calls
                        };
                    },
                );

                // Combine and set types
                setEntityTypes([
                    { value: "all", label: "All Types" },
                    ...systemTypes,
                    ...customTypes,
                ]);
            }
        } catch (error) {
            console.error("Error loading collection types:", error);
        }
    };

    const loadEntities = async () => {
        setLoading(true);
        try {
            // The backend expects the entity type as it appears in entity.type field
            // For system types, this is the ID (character, location, etc.)
            // For custom types, this is the vertex_label (normalized)
            const url = `/${workspaceId}/projects/${projectId}/editor/records/entities${
                selectedType !== "all"
                    ? `?type=${encodeURIComponent(selectedType)}`
                    : ""
            }`;
            const response = await fetch(url, {
                headers: {
                    Accept: "application/json",
                },
            });

            if (response.ok) {
                const data = await response.json();
                const entitiesList = data.entities || [];

                // Filter out internal/metadata entities
                const visibleEntities = entitiesList.filter(
                    (entity: Entity) => {
                        const type = (entity.type || "").toLowerCase();
                        const name = (entity.name || "").toLowerCase();

                        if (type.startsWith("_")) return false;
                        if (type.includes("scan") && type.includes("metadata"))
                            return false;
                        if (
                            type === "auditscanmetadata" ||
                            type === "audit_scan_metadata"
                        )
                            return false;
                        if (
                            name.includes("auditscanmetadata") ||
                            name.includes("_auditscanmetadata")
                        )
                            return false;

                        return true;
                    },
                );

                setEntities(visibleEntities);
            } else {
                console.error("Failed to load entities:", response.status);
                setEntities([]);
            }
        } catch (error) {
            console.error("Error loading entities:", error);
            setEntities([]);
        } finally {
            setLoading(false);
        }
    };

    const filteredEntities = entities.filter((entity) => {
        // Search filter
        if (
            searchQuery &&
            !entity.name.toLowerCase().includes(searchQuery.toLowerCase())
        ) {
            return false;
        }

        // Type filter is handled by backend, but we do client-side filtering as fallback
        if (selectedType !== "all") {
            const normalizedFilter = selectedType
                .toLowerCase()
                .replace(/_/g, " ");
            const normalizedType = (entity.type || "")
                .toLowerCase()
                .replace(/_/g, " ");

            // Match by normalized type name
            if (normalizedFilter !== normalizedType) {
                // Also check if the selected type's label matches
                const typeInfo = entityTypes.find(
                    (t) => t.value === selectedType,
                );
                if (typeInfo) {
                    const typeLabelNormalized = typeInfo.label
                        .toLowerCase()
                        .replace(/\s+/g, "_");
                    if (typeLabelNormalized !== normalizedType) {
                        return false;
                    }
                } else {
                    return false;
                }
            }
        }

        return true;
    });

    const handleDragStart = (e: React.DragEvent, entity: Entity) => {
        e.dataTransfer.setData("application/json", JSON.stringify(entity));
        e.dataTransfer.effectAllowed = "copy";
    };

    const getTypeColor = (type: string) => {
        const normalized = type.toLowerCase();
        if (normalized.includes("character"))
            return "bg-blue-100 text-blue-700 border-blue-300";
        if (normalized.includes("location"))
            return "bg-green-100 text-green-700 border-green-300";
        if (normalized.includes("item"))
            return "bg-yellow-100 text-yellow-700 border-yellow-300";
        if (normalized.includes("theme"))
            return "bg-purple-100 text-purple-700 border-purple-300";
        if (normalized.includes("plot"))
            return "bg-pink-100 text-pink-700 border-pink-300";
        return "bg-gray-100 text-gray-700 border-gray-300";
    };

    return (
        <div className="h-full w-64 bg-white border-r border-gray-300 flex flex-col overflow-hidden">
            <div className="p-3 border-b border-gray-200 bg-gray-50 flex flex-col gap-2">
                <h3 className="text-xs text-gray-600 uppercase tracking-wider flex items-center gap-2">
                    <Book className="w-3 h-3" /> Records
                </h3>
                <Input
                    type="text"
                    placeholder="Search..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="text-sm"
                />
                <div className="flex gap-1 overflow-x-auto pb-1">
                    {entityTypes.map((type) => (
                        <button
                            key={type.value}
                            onClick={() => setSelectedType(type.value)}
                            className={`text-xs whitespace-nowrap px-2 py-0.5 rounded-full border transition-colors ${
                                selectedType === type.value
                                    ? "bg-blue-600 text-white border-blue-700"
                                    : "bg-white text-gray-600 border-gray-300 hover:bg-gray-100"
                            }`}
                        >
                            {type.label}
                        </button>
                    ))}
                </div>
            </div>
            <div className="flex-1 overflow-y-auto p-3 space-y-2">
                {loading ? (
                    <p className="text-sm text-gray-500 text-center mt-10">
                        Loading...
                    </p>
                ) : filteredEntities.length === 0 ? (
                    <p className="text-sm text-gray-500 text-center mt-10">
                        No entities found
                    </p>
                ) : (
                    filteredEntities.map((entity) => (
                        <div
                            key={entity.vertex_id}
                            draggable
                            onDragStart={(e) => handleDragStart(e, entity)}
                            className="bg-white p-2 rounded border border-gray-200 hover:border-blue-400 cursor-grab active:cursor-grabbing transition-all shadow-sm hover:shadow"
                        >
                            <div className="flex items-center justify-between mb-1">
                                <span className="text-sm font-medium text-gray-800 truncate flex-1">
                                    {entity.name}
                                </span>
                                <span
                                    className={`text-[9px] px-1.5 py-0.5 rounded uppercase border ${getTypeColor(
                                        entity.type,
                                    )}`}
                                >
                                    {entity.type}
                                </span>
                            </div>
                            {entity.properties &&
                                Object.keys(entity.properties).length > 0 &&
                                (() => {
                                    // For Record Keeper, use summary; for others, find first string property
                                    const summary = entity.properties.summary;
                                    if (typeof summary === "string") {
                                        return (
                                            <p className="text-[10px] text-gray-600 mt-1 line-clamp-2">
                                                {summary}
                                            </p>
                                        );
                                    }
                                    // Find first string property
                                    const firstStringValue = Object.values(
                                        entity.properties,
                                    ).find(
                                        (v) =>
                                            typeof v === "string" &&
                                            v.length > 0,
                                    );
                                    if (firstStringValue) {
                                        return (
                                            <p className="text-[10px] text-gray-600 mt-1 line-clamp-2">
                                                {firstStringValue as string}
                                            </p>
                                        );
                                    }
                                    return null;
                                })()}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

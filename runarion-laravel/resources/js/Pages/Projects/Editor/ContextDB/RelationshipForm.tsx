import { useState, useEffect } from "react";
import { Button } from "@/Components/ui/button";
import { Label } from "@/Components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/Components/ui/select";
import { Input } from "@/Components/ui/input";

interface Entity {
    vertex_id: string;  // String to avoid JS precision loss with large Apache AGE IDs
    name: string;
    type: string;
}

interface RelationshipFormProps {
    workspaceId: string;
    projectId: string;
    entities: Entity[];
    defaultSource?: string; // Pre-select source entity (for creating from sidebar)
    onSaved: () => void;
    onCancel: () => void;
}

const RELATIONSHIP_TYPES = [
    { value: "INTERACTS_WITH", label: "Interacts With" },
    { value: "KNOWS", label: "Knows" },
    { value: "LOVES", label: "Loves" },
    { value: "HATES", label: "Hates" },
    { value: "LOCATED_IN", label: "Located In" },
    { value: "TRAVELS_TO", label: "Travels To" },
    { value: "OWNS", label: "Owns" },
    { value: "USES", label: "Uses" },
    { value: "CAUSES", label: "Causes" },
    { value: "LEADS_TO", label: "Leads To" },
];

export default function RelationshipForm({
    workspaceId,
    projectId,
    entities,
    defaultSource,
    onSaved,
    onCancel,
}: RelationshipFormProps) {
    console.log("RelationshipForm received entities:", entities);
    
    // Filter to only character entities (relationships are only for characters)
    // If type is missing, we'll include it (entities might not have type field yet)
    const characterEntities = entities.filter(
        (entity) => {
            // If type is missing, include it (might be a character that hasn't been updated yet)
            if (!entity?.type) {
                return true; // Include entities without type for now
            }
            return entity.type.toLowerCase() === "character";
        }
    );
    
    console.log("RelationshipForm - Total entities:", entities.length);
    console.log("RelationshipForm - Character entities:", characterEntities.length);
    const [source, setSource] = useState(defaultSource || "");
    const [target, setTarget] = useState("");
    const [relationshipType, setRelationshipType] = useState("INTERACTS_WITH");
    const [customType, setCustomType] = useState("");
    const [useCustomType, setUseCustomType] = useState(false);
    const [saving, setSaving] = useState(false);

    // Update source when defaultSource changes
    useEffect(() => {
        if (defaultSource) {
            setSource(defaultSource);
        }
    }, [defaultSource]);

    // Update source when defaultSource changes
    useEffect(() => {
        if (defaultSource) {
            setSource(defaultSource);
        }
    }, [defaultSource]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!source || !target) {
            alert("Please select both source and target entities");
            return;
        }

        if (source === target) {
            alert("Source and target entities must be different");
            return;
        }

        setSaving(true);

        try {
            const type = useCustomType ? customType : relationshipType;

            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/records/relationships`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "X-CSRF-TOKEN": document
                            .querySelector('meta[name="csrf-token"]')
                            ?.getAttribute("content") || "",
                    },
                    body: JSON.stringify({
                        source: parseInt(source), // Convert string to integer
                        target: parseInt(target), // Convert string to integer
                        type,
                    }),
                }
            );

            if (response.ok) {
                const result = await response.json();
                console.log("Relationship created successfully:", result);
                onSaved();
            } else {
                let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                try {
                    const error = await response.json();
                    console.error("Relationship creation error:", error);
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
            console.error("Error creating relationship:", error);
            alert(`Failed to create relationship: ${error?.message || String(error)}`);
        } finally {
            setSaving(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div>
                <Label htmlFor="source">Source Entity *</Label>
                <Select value={source} onValueChange={setSource} required>
                    <SelectTrigger>
                        <SelectValue placeholder="Select source entity" />
                    </SelectTrigger>
                    <SelectContent>
                        {characterEntities.length === 0 ? (
                            <div className="p-2 text-sm text-gray-500">
                                No character entities found. Create a character entity first.
                            </div>
                        ) : (
                            characterEntities.map((entity) => (
                                <SelectItem key={entity.vertex_id} value={entity.vertex_id.toString()}>
                                    {entity.name || `Entity ${entity.vertex_id}`}
                                </SelectItem>
                            ))
                        )}
                    </SelectContent>
                </Select>
            </div>

            <div>
                <Label htmlFor="relationshipType">Relationship Type *</Label>
                <div className="space-y-2">
                    <div className="flex items-center gap-2">
                        <input
                            type="checkbox"
                            id="useCustom"
                            checked={useCustomType}
                            onChange={(e) => setUseCustomType(e.target.checked)}
                            className="rounded"
                        />
                        <Label htmlFor="useCustom" className="text-sm font-normal">
                            Use custom relationship type
                        </Label>
                    </div>

                    {useCustomType ? (
                        <Input
                            value={customType}
                            onChange={(e) => setCustomType(e.target.value)}
                            placeholder="e.g., ALLIED_WITH, RIVAL_OF"
                            required
                        />
                    ) : (
                        <Select
                            value={relationshipType}
                            onValueChange={setRelationshipType}
                        >
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {RELATIONSHIP_TYPES.map((type) => (
                                    <SelectItem key={type.value} value={type.value}>
                                        {type.label}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    )}
                </div>
            </div>

            <div>
                <Label htmlFor="target">Target Entity *</Label>
                <Select value={target} onValueChange={setTarget} required>
                    <SelectTrigger>
                        <SelectValue placeholder="Select target entity" />
                    </SelectTrigger>
                    <SelectContent>
                        {characterEntities.length === 0 ? (
                            <div className="p-2 text-sm text-gray-500">
                                No character entities found.
                            </div>
                        ) : (
                            characterEntities
                                .filter((entity) => entity.vertex_id.toString() !== source)
                                .map((entity) => (
                                    <SelectItem key={entity.vertex_id} value={entity.vertex_id.toString()}>
                                        {entity.name || `Entity ${entity.vertex_id}`}
                                    </SelectItem>
                                ))
                        )}
                    </SelectContent>
                </Select>
            </div>

            <div className="flex justify-end gap-2 pt-4">
                <Button type="button" variant="outline" onClick={onCancel}>
                    Cancel
                </Button>
                <Button type="submit" disabled={saving}>
                    {saving ? "Creating..." : "Create Relationship"}
                </Button>
            </div>
        </form>
    );
}


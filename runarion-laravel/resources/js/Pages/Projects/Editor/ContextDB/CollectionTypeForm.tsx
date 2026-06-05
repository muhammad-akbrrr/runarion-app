import { useState } from "react";
import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { Label } from "@/Components/ui/label";
import { http } from "@/Lib/http";

interface CollectionTypeFormProps {
    workspaceId: string;
    projectId: string;
    onSaved: () => void;
    onCancel: () => void;
    onSavingChange?: (isSaving: boolean) => void;
}

export default function CollectionTypeForm({
    workspaceId,
    projectId,
    onSaved,
    onCancel,
    onSavingChange,
}: CollectionTypeFormProps) {
    const [name, setName] = useState("");
    const [saving, setSaving] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        onSavingChange?.(true);

        try {
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/records/collection-types`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                    },
                    data: {
                        name,
                        field_schema: [], // Will be implemented later
                    },
                }
            );

            if (response.status >= 200 && response.status < 300) {
                onSaved();
            } else {
                let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                try {
                    const error = response.data;
                    console.error("Collection type creation error:", error);
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
                alert(`Error: ${errorMessage}`);
            }
        } catch (error: any) {
            console.error("Error creating collection type:", error);
            alert(
                `Failed to create collection type: ${
                    error?.message || String(error)
                }`
            );
        } finally {
            setSaving(false);
            onSavingChange?.(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
                <Label htmlFor="name">Collection Type Name *</Label>
                <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    placeholder="e.g., Faction, Organization, Magic System"
                />
                <p className="text-sm text-gray-500 mt-1">
                    This will create a new category for entities (e.g.,
                    "Faction" for managing factions in your story).
                </p>
            </div>

            <div className="flex justify-end gap-2 pt-4">
                <Button type="button" variant="outline" onClick={onCancel}>
                    Cancel
                </Button>
                <Button type="submit" disabled={saving}>
                    {saving ? "Creating..." : "Create Collection Type"}
                </Button>
            </div>
        </form>
    );
}

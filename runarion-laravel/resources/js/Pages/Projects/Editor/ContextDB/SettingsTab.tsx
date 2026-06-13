import { useState, useEffect } from "react";
import { http } from "@/Lib/http";
import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { Label } from "@/Components/ui/label";
import { X, Plus, HelpCircle, Edit } from "lucide-react";
import { Switch } from "@/Components/ui/switch";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/Components/ui/tooltip";
import { toast } from "sonner";

interface Entity {
    vertex_id: string;  // String to avoid JS precision loss with large Apache AGE IDs
    name: string;
    type: string;
    properties: Record<string, any>;
}

interface SettingsTabProps {
    entity: Entity;
    workspaceId: string;
    projectId: string;
    onSettingsUpdated: () => void;
}

interface EntitySettings {
    activationKeys: string[];
    alwaysOn: boolean;
    phraseBias: {
        enabled: boolean;
        phrases: Array<{ phrase: string; bias: number }>;
        ensureCompletion: boolean;
        unbiasWhenGenerated: boolean;
    };
    searchRange: number;
    keyRelativeInsertion: {
        enabled: boolean;
        cascadingActivation: boolean;
        prefix: string;
        suffix: string;
        tokenBudget: number;
        reservedTokens: number;
        insertionOrder: number;
        insertionPosition: number;
    };
    trimDirection: 'top' | 'bottom' | 'none';
    maxTrimType: 'newline' | 'sentence' | 'token';
    insertionType: 'newline' | 'sentence' | 'token';
}

// Helper component for labels with tooltips
const LabelWithTooltip = ({ label, tooltip, className = "" }: { label: string; tooltip: string; className?: string }) => (
    <div className={`flex items-center gap-1 ${className}`}>
        <Label>{label}</Label>
        <Tooltip>
            <TooltipTrigger asChild>
                <HelpCircle className="h-3.5 w-3.5 text-gray-400 hover:text-gray-600 cursor-help" />
            </TooltipTrigger>
            <TooltipContent>
                <p className="max-w-xs">{tooltip}</p>
            </TooltipContent>
        </Tooltip>
    </div>
);

export default function SettingsTab({
    entity,
    workspaceId,
    projectId,
    onSettingsUpdated,
}: SettingsTabProps) {
    // Initialize settings from entity properties
    const getInitialSettings = (): EntitySettings => {
        const settings = entity.properties?._settings || {};
        return {
            activationKeys: settings.activationKeys || [],
            alwaysOn: settings.alwaysOn ?? false,
            phraseBias: {
                enabled: settings.phraseBias?.enabled ?? false,
                phrases: settings.phraseBias?.phrases || [],
                ensureCompletion: settings.phraseBias?.ensureCompletion ?? false,
                unbiasWhenGenerated: settings.phraseBias?.unbiasWhenGenerated ?? false,
            },
            searchRange: settings.searchRange ?? 5000,
            keyRelativeInsertion: {
                enabled: settings.keyRelativeInsertion?.enabled ?? true,
                cascadingActivation: settings.keyRelativeInsertion?.cascadingActivation ?? true,
                prefix: settings.keyRelativeInsertion?.prefix ?? '\\n',
                suffix: settings.keyRelativeInsertion?.suffix ?? '\\n',
                tokenBudget: settings.keyRelativeInsertion?.tokenBudget ?? 0,
                reservedTokens: settings.keyRelativeInsertion?.reservedTokens ?? 0,
                insertionOrder: settings.keyRelativeInsertion?.insertionOrder ?? 0,
                insertionPosition: settings.keyRelativeInsertion?.insertionPosition ?? -1,
            },
            trimDirection: settings.trimDirection || 'none',
            maxTrimType: settings.maxTrimType || 'newline',
            insertionType: settings.insertionType || 'newline',
        };
    };

    const [settings, setSettings] = useState<EntitySettings>(getInitialSettings());
    const [saving, setSaving] = useState(false);
    const [newActivationKey, setNewActivationKey] = useState("");
    const [newPhrase, setNewPhrase] = useState("");
    const [newPhraseBias, setNewPhraseBias] = useState(0);
    const [editingKeyIndex, setEditingKeyIndex] = useState<number | null>(null);
    const [editingKeyValue, setEditingKeyValue] = useState("");
    const [editingPhraseIndex, setEditingPhraseIndex] = useState<number | null>(null);
    const [editingPhraseValue, setEditingPhraseValue] = useState("");

    useEffect(() => {
        const initialSettings = getInitialSettings();
        setSettings(initialSettings);
        // Debug: log what we're loading
        console.log("SettingsTab: Loading settings from entity:", {
            entity: entity,
            entityProperties: entity.properties,
            _settings: entity.properties?._settings,
            activationKeys: initialSettings.activationKeys,
            allSettings: initialSettings,
        });
    }, [entity]);

    const handleSave = async () => {
        setSaving(true);
        try {
            // Merge settings into entity properties - preserve ALL existing properties
            const updatedProperties = {
                ...entity.properties,
                _settings: settings,
            };

            console.log("SettingsTab: Saving settings:", {
                originalProperties: entity.properties,
                settingsToSave: settings,
                updatedProperties: updatedProperties,
            });

            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/records/entities/${entity.vertex_id}`,
                {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    data: {
                        name: entity.name,
                        properties: updatedProperties,
                    },
                }
            );

            if (response.status >= 200 && response.status < 300) {
                const responseData = response.data;
                console.log("Settings saved successfully. Response:", responseData);
                // Trigger reload of entity data - this will refresh the entity with updated properties
                await onSettingsUpdated();
                // Small delay to ensure entity is reloaded
                setTimeout(() => {
                    console.log("SettingsTab: Entity should be reloaded now");
                }, 100);
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
            console.error("Error saving settings:", error);
            toast.error(
                `Failed to save settings: ${error?.message || String(error)}`,
            );
        } finally {
            setSaving(false);
        }
    };

    const handleAddActivationKey = () => {
        if (newActivationKey.trim()) {
            setSettings({
                ...settings,
                activationKeys: [...settings.activationKeys, newActivationKey.trim()],
            });
            setNewActivationKey("");
        }
    };

    const handleRemoveActivationKey = (index: number) => {
        setSettings({
            ...settings,
            activationKeys: settings.activationKeys.filter((_, i) => i !== index),
        });
    };

    const handleEditActivationKey = (index: number) => {
        setEditingKeyIndex(index);
        setEditingKeyValue(settings.activationKeys[index]);
    };

    const handleSaveActivationKey = (index: number) => {
        if (editingKeyValue.trim()) {
            const updatedKeys = [...settings.activationKeys];
            updatedKeys[index] = editingKeyValue.trim();
            setSettings({
                ...settings,
                activationKeys: updatedKeys,
            });
            setEditingKeyIndex(null);
            setEditingKeyValue("");
        }
    };

    const handleCancelEditKey = () => {
        setEditingKeyIndex(null);
        setEditingKeyValue("");
    };

    const handleAddPhrase = () => {
        if (newPhrase.trim()) {
            setSettings({
                ...settings,
                phraseBias: {
                    ...settings.phraseBias,
                    phrases: [
                        ...settings.phraseBias.phrases,
                        { phrase: newPhrase.trim(), bias: newPhraseBias },
                    ],
                },
            });
            setNewPhrase("");
            setNewPhraseBias(0);
        }
    };

    const handleRemovePhrase = (index: number) => {
        setSettings({
            ...settings,
            phraseBias: {
                ...settings.phraseBias,
                phrases: settings.phraseBias.phrases.filter((_, i) => i !== index),
            },
        });
    };

    const handleUpdatePhraseBias = (index: number, bias: number) => {
        const updatedPhrases = [...settings.phraseBias.phrases];
        updatedPhrases[index].bias = bias;
        setSettings({
            ...settings,
            phraseBias: {
                ...settings.phraseBias,
                phrases: updatedPhrases,
            },
        });
    };

    const handleEditPhrase = (index: number) => {
        setEditingPhraseIndex(index);
        setEditingPhraseValue(settings.phraseBias.phrases[index].phrase);
    };

    const handleSavePhrase = (index: number) => {
        if (editingPhraseValue.trim()) {
            const updatedPhrases = [...settings.phraseBias.phrases];
            updatedPhrases[index].phrase = editingPhraseValue.trim();
            setSettings({
                ...settings,
                phraseBias: {
                    ...settings.phraseBias,
                    phrases: updatedPhrases,
                },
            });
            setEditingPhraseIndex(null);
            setEditingPhraseValue("");
        }
    };

    const handleCancelEditPhrase = () => {
        setEditingPhraseIndex(null);
        setEditingPhraseValue("");
    };

    return (
        <div className="space-y-6 overflow-y-auto p-4">
            {/* Activation Keys Section */}
            <div className="space-y-3">
                <div>
                    <LabelWithTooltip
                        label="Activation Keys"
                        tooltip="Words or phrases that, when found in the context window, will activate this entity's information to be included in the generation prompt. For example, if you add 'protagonist' as a key, whenever that word appears in the context, this character's details will be included."
                        className="text-base font-semibold"
                    />
                </div>
                <div className="flex gap-2">
                    <Input
                        value={newActivationKey}
                        onChange={(e) => setNewActivationKey(e.target.value)}
                        placeholder="Type a key here"
                        onKeyPress={(e) => {
                            if (e.key === "Enter") {
                                e.preventDefault();
                                handleAddActivationKey();
                            }
                        }}
                    />
                    <Button type="button" onClick={handleAddActivationKey} size="icon">
                        <Plus className="h-4 w-4" />
                    </Button>
                </div>
                <div className="space-y-2">
                    {settings.activationKeys.length === 0 ? (
                        <p className="text-sm text-gray-500 italic">No activation keys yet. Add one above.</p>
                    ) : (
                        settings.activationKeys.map((key, index) => (
                            <div
                                key={index}
                                className="flex items-center justify-between p-2 bg-gray-50 rounded gap-2"
                            >
                                {editingKeyIndex === index ? (
                                    <>
                                        <Input
                                            value={editingKeyValue}
                                            onChange={(e) => setEditingKeyValue(e.target.value)}
                                            onKeyPress={(e) => {
                                                if (e.key === "Enter") {
                                                    e.preventDefault();
                                                    handleSaveActivationKey(index);
                                                } else if (e.key === "Escape") {
                                                    e.preventDefault();
                                                    handleCancelEditKey();
                                                }
                                            }}
                                            className="flex-1 h-8"
                                            autoFocus
                                        />
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => handleSaveActivationKey(index)}
                                        >
                                            <span className="text-xs">Save</span>
                                        </Button>
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="sm"
                                            onClick={handleCancelEditKey}
                                        >
                                            <X className="h-4 w-4" />
                                        </Button>
                                    </>
                                ) : (
                                    <>
                                        <span 
                                            className="text-sm flex-1 cursor-pointer hover:bg-gray-100 rounded px-2 py-1"
                                            onClick={() => handleEditActivationKey(index)}
                                            title="Click to edit"
                                        >
                                            {key}
                                        </span>
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => handleEditActivationKey(index)}
                                            title="Edit"
                                        >
                                            <Edit className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => handleRemoveActivationKey(index)}
                                            title="Remove"
                                        >
                                            <X className="h-4 w-4" />
                                        </Button>
                                    </>
                                )}
                            </div>
                        ))
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <Switch
                        checked={settings.alwaysOn}
                        onCheckedChange={(checked) =>
                            setSettings({ ...settings, alwaysOn: checked })
                        }
                    />
                    <LabelWithTooltip
                        label="Always On"
                        tooltip="When enabled, this entity's information will always be included in generation prompts, regardless of whether activation keys are found. Useful for main characters or important entities that should always influence generation."
                    />
                </div>
            </div>

            {/* Phrase Bias Section */}
            <div className="space-y-3 border-t pt-4">
                <div>
                    <LabelWithTooltip
                        label="Phrase Bias"
                        tooltip="Influence the AI's likelihood of generating specific words or phrases. Positive bias values increase the chance, negative values decrease it. This helps guide the AI's word choice during generation."
                        className="text-base font-semibold"
                    />
                </div>
                <div className="flex items-center gap-2">
                    <Switch
                        checked={settings.phraseBias.enabled}
                        onCheckedChange={(checked) =>
                            setSettings({
                                ...settings,
                                phraseBias: { ...settings.phraseBias, enabled: checked },
                            })
                        }
                    />
                    <Label>Enabled</Label>
                </div>
                {settings.phraseBias.enabled && (
                    <div className="space-y-3">
                        <div className="flex gap-2">
                            <Input
                                value={newPhrase}
                                onChange={(e) => setNewPhrase(e.target.value)}
                                placeholder="Enter phrase you want to bias"
                                onKeyPress={(e) => {
                                    if (e.key === "Enter") {
                                        e.preventDefault();
                                        handleAddPhrase();
                                    }
                                }}
                            />
                            <div className="flex items-center gap-1">
                                <Input
                                    type="number"
                                    value={newPhraseBias}
                                    onChange={(e) => setNewPhraseBias(parseInt(e.target.value) || 0)}
                                    placeholder="Bias"
                                    className="w-24"
                                />
                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <HelpCircle className="h-3.5 w-3.5 text-gray-400 hover:text-gray-600 cursor-help" />
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        <p className="max-w-xs">Bias value: positive numbers increase likelihood, negative decrease. Range typically -100 to +100.</p>
                                    </TooltipContent>
                                </Tooltip>
                            </div>
                            <Button type="button" onClick={handleAddPhrase} size="icon">
                                <Plus className="h-4 w-4" />
                            </Button>
                        </div>
                        <div className="space-y-2">
                            {settings.phraseBias.phrases.length === 0 ? (
                                <p className="text-sm text-gray-500 italic">No phrases yet. Add one above.</p>
                            ) : (
                                settings.phraseBias.phrases.map((item, index) => (
                                    <div
                                        key={index}
                                        className="flex items-center gap-2 p-2 bg-gray-50 rounded"
                                    >
                                        {editingPhraseIndex === index ? (
                                            <>
                                                <Input
                                                    value={editingPhraseValue}
                                                    onChange={(e) => setEditingPhraseValue(e.target.value)}
                                                    onKeyPress={(e) => {
                                                        if (e.key === "Enter") {
                                                            e.preventDefault();
                                                            handleSavePhrase(index);
                                                        } else if (e.key === "Escape") {
                                                            e.preventDefault();
                                                            handleCancelEditPhrase();
                                                        }
                                                    }}
                                                    className="flex-1 h-8"
                                                    autoFocus
                                                />
                                                <Button
                                                    type="button"
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleSavePhrase(index)}
                                                >
                                                    <span className="text-xs">Save</span>
                                                </Button>
                                                <Button
                                                    type="button"
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={handleCancelEditPhrase}
                                                >
                                                    <X className="h-4 w-4" />
                                                </Button>
                                            </>
                                        ) : (
                                            <>
                                                <span 
                                                    className="text-sm flex-1 cursor-pointer hover:bg-gray-100 rounded px-2 py-1"
                                                    onClick={() => handleEditPhrase(index)}
                                                    title="Click to edit phrase"
                                                >
                                                    {item.phrase}
                                                </span>
                                                <div className="flex items-center gap-2">
                                                    <Label className="text-xs">Bias:</Label>
                                                    <Input
                                                        type="number"
                                                        value={item.bias}
                                                        onChange={(e) =>
                                                            handleUpdatePhraseBias(
                                                                index,
                                                                parseInt(e.target.value) || 0
                                                            )
                                                        }
                                                        className="w-20 h-8"
                                                    />
                                                </div>
                                                <Button
                                                    type="button"
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleEditPhrase(index)}
                                                    title="Edit phrase"
                                                >
                                                    <Edit className="h-4 w-4" />
                                                </Button>
                                                <Button
                                                    type="button"
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleRemovePhrase(index)}
                                                    title="Remove"
                                                >
                                                    <X className="h-4 w-4" />
                                                </Button>
                                            </>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                        <div className="space-y-2">
                            <div className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={settings.phraseBias.ensureCompletion}
                                    onChange={(e) =>
                                        setSettings({
                                            ...settings,
                                            phraseBias: {
                                                ...settings.phraseBias,
                                                ensureCompletion: e.target.checked,
                                            },
                                        })
                                    }
                                    className="rounded"
                                />
                                <LabelWithTooltip
                                    label="Ensure Completion After Start"
                                    tooltip="Once the AI starts generating a biased phrase, it will be forced to complete it. Prevents partial or interrupted phrase generation."
                                    className="text-sm"
                                />
                            </div>
                            <div className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={settings.phraseBias.unbiasWhenGenerated}
                                    onChange={(e) =>
                                        setSettings({
                                            ...settings,
                                            phraseBias: {
                                                ...settings.phraseBias,
                                                unbiasWhenGenerated: e.target.checked,
                                            },
                                        })
                                    }
                                    className="rounded"
                                />
                                <LabelWithTooltip
                                    label="Unbias When Generated"
                                    tooltip="After the biased phrase is generated once, remove the bias to prevent over-repetition. Useful for ensuring variety in generation."
                                    className="text-sm"
                                />
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Search Range Section */}
            <div className="space-y-3 border-t pt-4">
                <div>
                    <LabelWithTooltip
                        label="Search Range"
                        tooltip="The number of tokens to search backward from the current cursor position when looking for activation keys. A larger range means the system will look further back in the text to find activation triggers. Range: 1,000 to 10,000 tokens."
                        className="text-base font-semibold"
                    />
                </div>
                <div className="flex items-center gap-4">
                    <span className="text-sm text-gray-600">~5,000</span>
                    <div className="flex-1">
                        <input
                            type="range"
                            min="1000"
                            max="10000"
                            step="1000"
                            value={settings.searchRange}
                            onChange={(e) =>
                                setSettings({
                                    ...settings,
                                    searchRange: parseInt(e.target.value),
                                })
                            }
                            className="w-full"
                        />
                    </div>
                    <span className="text-sm text-gray-600">Maximum: 10,000</span>
                </div>
                <div className="text-center text-sm text-gray-600">
                    Current: {settings.searchRange.toLocaleString()}
                </div>
            </div>

            {/* Key-Relative Insertion Section */}
            <div className="space-y-3 border-t pt-4">
                <div>
                    <LabelWithTooltip
                        label="Key-Relative Insertion"
                        tooltip="Controls how and where entity information is inserted into the prompt when activation keys are found. This determines the positioning and formatting of the entity's context in the generation prompt."
                        className="text-base font-semibold"
                    />
                </div>
                <div className="space-y-3">
                    <div className="flex items-center gap-2">
                        <Switch
                            checked={settings.keyRelativeInsertion.enabled}
                            onCheckedChange={(checked) =>
                                setSettings({
                                    ...settings,
                                    keyRelativeInsertion: {
                                        ...settings.keyRelativeInsertion,
                                        enabled: checked,
                                    },
                                })
                            }
                        />
                        <LabelWithTooltip
                            label="Key-Relative Insertion"
                            tooltip="When enabled, entity information will be inserted near where activation keys are found in the context. When disabled, entity info is added at a fixed position."
                        />
                    </div>
                    <div className="flex items-center gap-2">
                        <Switch
                            checked={settings.keyRelativeInsertion.cascadingActivation}
                            onCheckedChange={(checked) =>
                                setSettings({
                                    ...settings,
                                    keyRelativeInsertion: {
                                        ...settings.keyRelativeInsertion,
                                        cascadingActivation: checked,
                                    },
                                })
                            }
                        />
                        <LabelWithTooltip
                            label="Cascading Activation"
                            tooltip="When enabled, finding one activation key can trigger other related entities to also be included. Useful for character relationships or interconnected entities."
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <LabelWithTooltip
                                label="Prefix"
                                tooltip="Text to insert before the entity information. Common values: '\\n' (newline), '\\n\\n' (paragraph break), or custom text. Used for formatting."
                                className="text-sm"
                            />
                            <Input
                                value={settings.keyRelativeInsertion.prefix}
                                onChange={(e) =>
                                    setSettings({
                                        ...settings,
                                        keyRelativeInsertion: {
                                            ...settings.keyRelativeInsertion,
                                            prefix: e.target.value,
                                        },
                                    })
                                }
                                className="mt-1"
                            />
                        </div>
                        <div>
                            <LabelWithTooltip
                                label="Suffix"
                                tooltip="Text to insert after the entity information. Common values: '\\n' (newline), '\\n\\n' (paragraph break), or custom text. Used for formatting."
                                className="text-sm"
                            />
                            <Input
                                value={settings.keyRelativeInsertion.suffix}
                                onChange={(e) =>
                                    setSettings({
                                        ...settings,
                                        keyRelativeInsertion: {
                                            ...settings.keyRelativeInsertion,
                                            suffix: e.target.value,
                                        },
                                    })
                                }
                                className="mt-1"
                            />
                        </div>
                        <div>
                            <LabelWithTooltip
                                label="Token Budget"
                                tooltip="Maximum number of tokens allocated for this entity's information in the prompt. If the entity info exceeds this, it will be truncated. Set to 0 for unlimited."
                                className="text-sm"
                            />
                            <Input
                                type="number"
                                value={settings.keyRelativeInsertion.tokenBudget}
                                onChange={(e) =>
                                    setSettings({
                                        ...settings,
                                        keyRelativeInsertion: {
                                            ...settings.keyRelativeInsertion,
                                            tokenBudget: parseInt(e.target.value) || 0,
                                        },
                                    })
                                }
                                className="mt-1"
                            />
                        </div>
                        <div>
                            <LabelWithTooltip
                                label="Reserved Tokens"
                                tooltip="Number of tokens to reserve for this entity, even if not all are used. Helps ensure consistent prompt structure and prevents other entities from using this space."
                                className="text-sm"
                            />
                            <Input
                                type="number"
                                value={settings.keyRelativeInsertion.reservedTokens}
                                onChange={(e) =>
                                    setSettings({
                                        ...settings,
                                        keyRelativeInsertion: {
                                            ...settings.keyRelativeInsertion,
                                            reservedTokens: parseInt(e.target.value) || 0,
                                        },
                                    })
                                }
                                className="mt-1"
                            />
                        </div>
                        <div>
                            <LabelWithTooltip
                                label="Insertion Order"
                                tooltip="Priority order for inserting this entity's information when multiple entities are activated. Lower numbers are inserted first. Use this to control the sequence of entity information in prompts."
                                className="text-sm"
                            />
                            <Input
                                type="number"
                                value={settings.keyRelativeInsertion.insertionOrder}
                                onChange={(e) =>
                                    setSettings({
                                        ...settings,
                                        keyRelativeInsertion: {
                                            ...settings.keyRelativeInsertion,
                                            insertionOrder: parseInt(e.target.value) || 0,
                                        },
                                    })
                                }
                                className="mt-1"
                            />
                        </div>
                        <div>
                            <LabelWithTooltip
                                label="Insertion Position"
                                tooltip="Fixed position in the prompt to insert entity information (when key-relative insertion is disabled). -1 means automatic positioning. Positive numbers indicate token position from start."
                                className="text-sm"
                            />
                            <Input
                                type="number"
                                value={settings.keyRelativeInsertion.insertionPosition}
                                onChange={(e) =>
                                    setSettings({
                                        ...settings,
                                        keyRelativeInsertion: {
                                            ...settings.keyRelativeInsertion,
                                            insertionPosition: parseInt(e.target.value) || -1,
                                        },
                                    })
                                }
                                className="mt-1"
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* Trim Direction Section */}
            <div className="space-y-3 border-t pt-4">
                <div>
                    <LabelWithTooltip
                        label="Trim Direction"
                        tooltip="When entity information needs to be trimmed (due to token limits), this determines which part gets removed. 'Top' removes from the beginning, 'Bottom' removes from the end, 'No Trim' prevents trimming."
                        className="text-base font-semibold"
                    />
                </div>
                <div className="flex gap-2">
                    <Button
                        type="button"
                        variant={settings.trimDirection === "top" ? "default" : "outline"}
                        onClick={() => setSettings({ ...settings, trimDirection: "top" })}
                    >
                        Top
                    </Button>
                    <Button
                        type="button"
                        variant={settings.trimDirection === "bottom" ? "default" : "outline"}
                        onClick={() => setSettings({ ...settings, trimDirection: "bottom" })}
                    >
                        Bottom
                    </Button>
                    <Button
                        type="button"
                        variant={settings.trimDirection === "none" ? "default" : "outline"}
                        onClick={() => setSettings({ ...settings, trimDirection: "none" })}
                    >
                        No Trim
                    </Button>
                </div>
            </div>

            {/* Maximum Trim Type Section */}
            <div className="space-y-3 border-t pt-4">
                <div>
                    <LabelWithTooltip
                        label="Maximum Trim Type"
                        tooltip="The granularity of trimming when entity information exceeds token limits. 'Newline' trims at line breaks, 'Sentence' trims at sentence boundaries, 'Token' trims at individual token boundaries. More granular options preserve better context."
                        className="text-base font-semibold"
                    />
                </div>
                <div className="flex gap-2">
                    <Button
                        type="button"
                        variant={settings.maxTrimType === "newline" ? "default" : "outline"}
                        onClick={() => setSettings({ ...settings, maxTrimType: "newline" })}
                    >
                        Newline
                    </Button>
                    <Button
                        type="button"
                        variant={settings.maxTrimType === "sentence" ? "default" : "outline"}
                        onClick={() => setSettings({ ...settings, maxTrimType: "sentence" })}
                    >
                        Sentence
                    </Button>
                    <Button
                        type="button"
                        variant={settings.maxTrimType === "token" ? "default" : "outline"}
                        onClick={() => setSettings({ ...settings, maxTrimType: "token" })}
                    >
                        Token
                    </Button>
                </div>
            </div>

            {/* Insertion Type Section */}
            <div className="space-y-3 border-t pt-4">
                <div>
                    <LabelWithTooltip
                        label="Insertion Type"
                        tooltip="How entity information is inserted into the prompt. 'Newline' inserts at line breaks, 'Sentence' inserts at sentence boundaries, 'Token' inserts at token boundaries. Affects formatting and readability of the prompt."
                        className="text-base font-semibold"
                    />
                </div>
                <div className="flex gap-2">
                    <Button
                        type="button"
                        variant={settings.insertionType === "newline" ? "default" : "outline"}
                        onClick={() => setSettings({ ...settings, insertionType: "newline" })}
                    >
                        Newline
                    </Button>
                    <Button
                        type="button"
                        variant={settings.insertionType === "sentence" ? "default" : "outline"}
                        onClick={() => setSettings({ ...settings, insertionType: "sentence" })}
                    >
                        Sentence
                    </Button>
                    <Button
                        type="button"
                        variant={settings.insertionType === "token" ? "default" : "outline"}
                        onClick={() => setSettings({ ...settings, insertionType: "token" })}
                    >
                        Token
                    </Button>
                </div>
            </div>

            {/* Save Button */}
            <div className="flex justify-end pt-4 border-t">
                <Button onClick={handleSave} disabled={saving}>
                    {saving ? "Saving..." : "Save Settings"}
                </Button>
            </div>
        </div>
    );
}

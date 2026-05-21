import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { X, Plus, Trash2, Loader2 } from "lucide-react";
import type { EmotionalTone } from "../types";

interface EmotionalTonesManagerProps {
    emotionalTones: EmotionalTone[];
    loadingTones: boolean;
    newToneName: string;
    setNewToneName: (name: string) => void;
    creatingTone: boolean;
    deletingTone: number | null;
    onCreateTone: () => void;
    onDeleteTone: (toneId: number) => void;
    onClose: () => void;
}

export default function EmotionalTonesManager({
    emotionalTones,
    loadingTones,
    newToneName,
    setNewToneName,
    creatingTone,
    deletingTone,
    onCreateTone,
    onDeleteTone,
    onClose,
}: EmotionalTonesManagerProps) {
    return (
        <div className="border rounded-lg p-3 bg-purple-50 space-y-3">
            <div className="flex items-center justify-between">
                <h4 className="font-medium text-sm text-purple-800">
                    Emotional Tones
                </h4>
                <button
                    onClick={onClose}
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
                        if (e.key === "Enter") onCreateTone();
                    }}
                />
                <Button
                    size="sm"
                    onClick={onCreateTone}
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
                            No custom tones yet. AI can create them during
                            analysis.
                        </p>
                    ) : (
                        emotionalTones.map((tone) => (
                            <div
                                key={tone.id}
                                className={`flex items-center justify-between px-2 py-1.5 rounded text-xs ${
                                    tone.is_base
                                        ? "bg-white/50 text-gray-600"
                                        : "bg-white text-gray-800"
                                }`}
                            >
                                <span className="capitalize">
                                    {tone.name}
                                    {tone.is_base && (
                                        <span className="ml-1 text-[10px] text-gray-400">
                                            (base)
                                        </span>
                                    )}
                                </span>
                                {!tone.is_base && (
                                    <button
                                        onClick={() => onDeleteTone(tone.id)}
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
                Base tones cannot be deleted. AI can create custom tones during
                analysis.
            </p>
        </div>
    );
}

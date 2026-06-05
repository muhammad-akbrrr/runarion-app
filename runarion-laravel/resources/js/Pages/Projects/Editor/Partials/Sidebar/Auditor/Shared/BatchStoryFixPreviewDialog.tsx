import { useState } from "react";
import { Button } from "@/Components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";
import { Label } from "@/Components/ui/label";
import { Textarea } from "@/Components/ui/textarea";
import { Checkbox } from "@/Components/ui/checkbox";
import {
    Wand2,
    CheckCircle,
    ChevronDown,
    ChevronUp,
    Edit2,
} from "lucide-react";
import type { BatchFixItem } from "../types";

interface BatchStoryFixPreviewDialogProps {
    open: boolean;
    fixes: BatchFixItem[];
    onFixEdit: (index: number, newText: string) => void;
    onFixToggle: (index: number, enabled: boolean) => void;
    onConfirm: () => void;
    onClose: () => void;
    isApplying: boolean;
}

export default function BatchStoryFixPreviewDialog({
    open,
    fixes,
    onFixEdit,
    onFixToggle,
    onConfirm,
    onClose,
    isApplying,
}: BatchStoryFixPreviewDialogProps) {
    const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
    const [editingIndex, setEditingIndex] = useState<number | null>(null);

    const enabledCount = fixes.filter((f) => f.enabled).length;

    const handleToggleExpand = (index: number) => {
        setExpandedIndex(expandedIndex === index ? null : index);
        setEditingIndex(null);
    };

    const handleStartEdit = (index: number, e: React.MouseEvent) => {
        e.stopPropagation();
        setExpandedIndex(index);
        setEditingIndex(index);
    };

    const handleFinishEdit = () => {
        setEditingIndex(null);
    };

    return (
        <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
            <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Wand2 className="h-4 w-4 text-purple-600" />
                        Review Batch Story Fixes ({fixes.length} fixes)
                    </DialogTitle>
                    <DialogDescription>
                        Review and optionally edit each fix before applying.
                        Toggle off any fixes you don&apos;t want to apply.
                    </DialogDescription>
                </DialogHeader>

                <div className="flex-1 overflow-y-auto space-y-3 pr-2">
                    {fixes.map((fix, idx) => (
                        <div
                            key={idx}
                            className={`border rounded-lg transition-all ${
                                fix.enabled
                                    ? "border-purple-200 bg-white"
                                    : "border-gray-200 bg-gray-50 opacity-60"
                            }`}
                        >
                            {/* Fix Header - Always visible */}
                            <div
                                className="flex items-center gap-3 p-3 cursor-pointer"
                                onClick={() => handleToggleExpand(idx)}
                            >
                                <Checkbox
                                    checked={fix.enabled}
                                    onCheckedChange={(checked) => {
                                        onFixToggle(idx, !!checked);
                                    }}
                                    onClick={(e) => e.stopPropagation()}
                                    className="data-[state=checked]:bg-purple-600"
                                />

                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm font-medium text-gray-900 truncate">
                                            {fix.issue?.title ||
                                                `Fix ${idx + 1}`}
                                        </span>
                                    </div>
                                    {fix.issue?.description && (
                                        <p className="text-xs text-gray-500 truncate mt-0.5">
                                            {fix.issue.description}
                                        </p>
                                    )}
                                </div>

                                <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                                    {fix.chapterName}
                                </span>

                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-8 w-8 p-0"
                                    onClick={(e) => handleStartEdit(idx, e)}
                                >
                                    <Edit2 className="h-3 w-3 text-gray-500" />
                                </Button>

                                {expandedIndex === idx ? (
                                    <ChevronUp className="h-4 w-4 text-gray-400" />
                                ) : (
                                    <ChevronDown className="h-4 w-4 text-gray-400" />
                                )}
                            </div>

                            {/* Expanded Content */}
                            {expandedIndex === idx && (
                                <div className="p-3 space-y-3 border-t border-gray-100">
                                    {/* Original Text */}
                                    <div className="space-y-1">
                                        <Label className="text-xs text-gray-500">
                                            Original Text (will be replaced)
                                        </Label>
                                        <div className="p-2 bg-red-50 rounded text-xs font-mono border border-red-200 max-h-24 overflow-y-auto whitespace-pre-wrap">
                                            {fix.oldText || (
                                                <span className="text-gray-400 italic">
                                                    (text not found)
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Revised Text */}
                                    <div className="space-y-1">
                                        <Label className="text-xs text-gray-500">
                                            Revised Text{" "}
                                            {editingIndex === idx &&
                                                "(editing)"}
                                        </Label>
                                        {editingIndex === idx ? (
                                            <div className="space-y-2">
                                                <Textarea
                                                    value={fix.editedText}
                                                    onChange={(e) =>
                                                        onFixEdit(
                                                            idx,
                                                            e.target.value
                                                        )
                                                    }
                                                    className="min-h-20 font-mono text-xs bg-green-50 border-green-200"
                                                    autoFocus
                                                />
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    onClick={handleFinishEdit}
                                                >
                                                    Done Editing
                                                </Button>
                                            </div>
                                        ) : (
                                            <div className="p-2 bg-green-50 rounded text-xs font-mono border border-green-200 max-h-24 overflow-y-auto whitespace-pre-wrap">
                                                {fix.editedText}
                                            </div>
                                        )}
                                    </div>

                                    {/* AI Explanation */}
                                    {fix.explanation && (
                                        <div className="space-y-1">
                                            <Label className="text-xs text-gray-500">
                                                AI Explanation
                                            </Label>
                                            <p className="text-xs text-gray-600 italic bg-blue-50 p-2 rounded">
                                                {fix.explanation}
                                            </p>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                <div className="p-2 bg-yellow-50 rounded border border-yellow-200 text-xs text-yellow-700">
                    <strong>Tip:</strong> Fixes will be applied from bottom to
                    top of the document to prevent position shifts. Toggle off
                    any fixes you want to skip.
                </div>

                <DialogFooter className="gap-2">
                    <Button
                        variant="outline"
                        onClick={onClose}
                        disabled={isApplying}
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={onConfirm}
                        disabled={enabledCount === 0 || isApplying}
                        className="bg-purple-600 hover:bg-purple-700"
                    >
                        {isApplying ? (
                            <>Applying...</>
                        ) : (
                            <>
                                <CheckCircle className="h-4 w-4 mr-2" />
                                Apply {enabledCount} Fix
                                {enabledCount !== 1 ? "es" : ""}
                            </>
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

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
import { Wand2, CheckCircle } from "lucide-react";
import type { StoryTextPreviewData } from "../types";

interface StoryFixPreviewDialogProps {
    previewData: StoryTextPreviewData | null;
    editedText: string;
    onEditedTextChange: (text: string) => void;
    onConfirm: () => void;
    onClose: () => void;
}

export default function StoryFixPreviewDialog({
    previewData,
    editedText,
    onEditedTextChange,
    onConfirm,
    onClose,
}: StoryFixPreviewDialogProps) {
    return (
        <Dialog open={previewData !== null} onOpenChange={(open) => !open && onClose()}>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Wand2 className="h-4 w-4 text-purple-600" />
                        Review Story Fix
                    </DialogTitle>
                    <DialogDescription>
                        Review the suggested text change for{" "}
                        <strong>{previewData?.chapterName}</strong>
                    </DialogDescription>
                </DialogHeader>

                {previewData && (
                    <div className="space-y-4 flex-1 overflow-y-auto">
                        <div className="p-2 bg-purple-50 rounded border border-purple-200">
                            <Label className="text-xs text-purple-700 font-medium">
                                Issue: {previewData.issue.title}
                            </Label>
                            {previewData.issue.description && (
                                <p className="text-xs text-purple-600 mt-1">
                                    {previewData.issue.description}
                                </p>
                            )}
                        </div>

                        <div>
                            <Label className="text-xs text-gray-500 flex items-center gap-1">
                                <span className="text-red-500">●</span> Original Text
                                (will be replaced)
                            </Label>
                            <div className="p-3 bg-red-50 rounded text-sm font-mono border border-red-200 max-h-32 overflow-y-auto whitespace-pre-wrap">
                                {previewData.oldText || (
                                    <span className="text-gray-400 italic">
                                        (text not found)
                                    </span>
                                )}
                            </div>
                        </div>

                        <div>
                            <Label className="text-xs text-gray-500 flex items-center gap-1">
                                <span className="text-green-500">●</span> Revised Text
                                (editable)
                            </Label>
                            <Textarea
                                value={editedText}
                                onChange={(e) => onEditedTextChange(e.target.value)}
                                className="min-h-[120px] font-mono text-sm bg-green-50 border-green-200"
                                placeholder="Enter the revised text..."
                            />
                        </div>

                        {previewData.explanation && (
                            <div>
                                <Label className="text-xs text-gray-500">
                                    AI Explanation
                                </Label>
                                <p className="text-sm text-gray-600 italic bg-blue-50 p-2 rounded">
                                    {previewData.explanation}
                                </p>
                            </div>
                        )}

                        <div className="p-2 bg-yellow-50 rounded border border-yellow-200 text-xs text-yellow-700">
                            <strong>Tip:</strong> The revised text will replace the
                            original text in your chapter. You can edit it before
                            applying.
                        </div>
                    </div>
                )}

                <DialogFooter className="gap-2">
                    <Button variant="outline" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button
                        onClick={onConfirm}
                        disabled={!editedText.trim()}
                        className="bg-purple-600 hover:bg-purple-700"
                    >
                        <CheckCircle className="h-4 w-4 mr-2" />
                        Apply Fix to Chapter
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

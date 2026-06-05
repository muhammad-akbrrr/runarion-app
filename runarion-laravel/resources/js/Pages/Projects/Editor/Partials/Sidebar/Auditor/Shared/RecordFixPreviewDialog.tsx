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
import { CheckCircle } from "lucide-react";
import type { RecordFixPreviewData } from "../types";

interface RecordFixPreviewDialogProps {
    previewData: RecordFixPreviewData | null;
    onClose: () => void;
}

export default function RecordFixPreviewDialog({
    previewData,
    onClose,
}: RecordFixPreviewDialogProps) {
    return (
        <Dialog open={previewData !== null} onOpenChange={(open) => !open && onClose()}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <CheckCircle className="h-4 w-4 text-green-600" />
                        Fix Applied Successfully
                    </DialogTitle>
                    <DialogDescription>
                        The following change was made to{" "}
                        <strong>{previewData?.issue.entity_name}</strong>
                    </DialogDescription>
                </DialogHeader>

                {previewData && (
                    <div className="space-y-4">
                        <div>
                            <Label className="text-xs text-gray-500">
                                Field Updated
                            </Label>
                            <p className="font-medium text-blue-700">
                                {previewData.field}
                            </p>
                        </div>

                        <div>
                            <Label className="text-xs text-gray-500">
                                Previous Value
                            </Label>
                            <div className="p-2 bg-red-50 rounded text-sm font-mono border border-red-200 max-h-24 overflow-y-auto">
                                {previewData.oldValue || (
                                    <span className="text-gray-400 italic">
                                        (no value)
                                    </span>
                                )}
                            </div>
                        </div>

                        <div>
                            <Label className="text-xs text-gray-500">
                                New Value
                            </Label>
                            <div className="p-2 bg-green-50 rounded text-sm font-mono border border-green-200 max-h-24 overflow-y-auto">
                                {previewData.newValue || (
                                    <span className="text-gray-400 italic">
                                        (no value)
                                    </span>
                                )}
                            </div>
                        </div>

                        {previewData.explanation && (
                            <div>
                                <Label className="text-xs text-gray-500">
                                    Explanation
                                </Label>
                                <p className="text-sm text-gray-600 italic bg-blue-50 p-2 rounded">
                                    {previewData.explanation}
                                </p>
                            </div>
                        )}

                        {previewData.oldValue === previewData.newValue && (
                            <div className="p-2 bg-yellow-50 rounded border border-yellow-200 text-sm text-yellow-700">
                                No change was needed - the value was already correct.
                            </div>
                        )}
                    </div>
                )}

                <DialogFooter>
                    <Button variant="outline" onClick={onClose}>
                        Close
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

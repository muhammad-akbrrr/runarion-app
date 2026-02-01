import React from "react";
import { ArrowRight, Zap } from "lucide-react";
import { Button } from "@/Components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/Components/ui/dialog";

interface ResultDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    generatedResult: string | null;
    onApply: () => void;
    onStayHere: () => void;
}

export const ResultDialog: React.FC<ResultDialogProps> = ({
    open,
    onOpenChange,
    generatedResult,
    onApply,
    onStayHere,
}) => {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Zap className="w-5 h-5 text-green-600" />{" "}
                        Generation Complete!
                    </DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                    <p className="text-sm text-gray-600">
                        Your graph has been executed successfully. What
                        would you like to do with the generated text?
                    </p>
                    <div className="bg-gray-50 p-3 rounded border border-gray-200 max-h-48 overflow-y-auto">
                        <p className="text-xs text-gray-500 mb-2 font-semibold">
                            Preview:
                        </p>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap line-clamp-6">
                            {generatedResult?.substring(0, 300)}
                            {generatedResult && generatedResult.length > 300
                                ? "..."
                                : ""}
                        </p>
                    </div>
                </div>
                <DialogFooter className="flex gap-2">
                    <Button
                        variant="outline"
                        onClick={onStayHere}
                    >
                        Stay Here
                    </Button>
                    <Button
                        onClick={onApply}
                        className="bg-green-600 hover:bg-green-700"
                    >
                        <ArrowRight className="w-4 h-4 mr-2" />
                        Apply to Editor
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};

import React from "react";
import { Eye } from "lucide-react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";

export interface InspectionData {
    nodeLabel: string;
    nodeInstruction: string;
    inputsText: string;
    storyPreview: string;
}

interface InspectorDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    inspectionData: InspectionData | null;
}

export const InspectorDialog: React.FC<InspectorDialogProps> = ({
    open,
    onOpenChange,
    inspectionData,
}) => {
    if (!inspectionData) return null;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 flex-wrap">
                        <Eye className="w-5 h-5 text-blue-600" /> Node
                        Inspector:{" "}
                        <span className="text-blue-600">
                            {inspectionData.nodeLabel}
                        </span>
                    </DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-gray-600 uppercase">
                                Compiled Inputs
                            </label>
                            <div className="bg-gray-100 p-3 rounded border border-gray-300 text-xs text-gray-700 font-mono h-64 overflow-y-auto whitespace-pre-wrap">
                                {inspectionData.inputsText ||
                                    "No inputs connected."}
                            </div>
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-gray-600 uppercase">
                                Global Story Context
                            </label>
                            <div className="bg-gray-100 p-3 rounded border border-gray-300 text-xs text-gray-600 italic h-64 overflow-y-auto">
                                "{inspectionData.storyPreview}"
                            </div>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <label className="text-xs font-bold text-gray-600 uppercase">
                            Node Instruction
                        </label>
                        <div className="bg-blue-50 p-3 min-h-12 rounded border border-blue-200 text-sm text-gray-800">
                            {inspectionData.nodeInstruction}
                        </div>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
};

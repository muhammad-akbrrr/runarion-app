import React from "react";
import { Loader2, Sparkles, Wand2 } from "lucide-react";
import { Button } from "@/Components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/Components/ui/dialog";
import { Textarea } from "@/Components/ui/textarea";

interface RefinerDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    refinerPrompt: string;
    setRefinerPrompt: (prompt: string) => void;
    selectedCount: number;
    isRefining: boolean;
    onRefine: () => void;
}

export const RefinerDialog: React.FC<RefinerDialogProps> = ({
    open,
    onOpenChange,
    refinerPrompt,
    setRefinerPrompt,
    selectedCount,
    isRefining,
    onRefine,
}) => {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Wand2 className="w-5 h-5 text-purple-600" /> Refine
                        Selection
                    </DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                    <p className="text-sm text-gray-600">
                        How should the AI modify the{" "}
                        {selectedCount} selected nodes? It can
                        split them, merge them, or add logic checks.
                    </p>
                    <Textarea
                        value={refinerPrompt}
                        onChange={(e) => setRefinerPrompt(e.target.value)}
                        placeholder="e.g. Break this interaction into 3 beats and add a tension check in the middle..."
                        className="min-h-32"
                    />
                </div>
                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={onRefine}
                        disabled={!refinerPrompt || isRefining}
                        className="bg-purple-600 hover:bg-purple-700"
                    >
                        {isRefining ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin mr-2" />{" "}
                                Refining...
                            </>
                        ) : (
                            <>
                                <Sparkles className="w-4 h-4 mr-2" />{" "}
                                Enhance Flow
                            </>
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};

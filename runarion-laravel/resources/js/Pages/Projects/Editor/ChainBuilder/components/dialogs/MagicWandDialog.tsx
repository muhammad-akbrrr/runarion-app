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

interface MagicWandDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    wandSeed: string;
    setWandSeed: (seed: string) => void;
    isGenerating: boolean;
    onGenerate: () => void;
}

export const MagicWandDialog: React.FC<MagicWandDialogProps> = ({
    open,
    onOpenChange,
    wandSeed,
    setWandSeed,
    isGenerating,
    onGenerate,
}) => {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Sparkles className="w-5 h-5 text-purple-600" />{" "}
                        Magic Prompt Writer
                    </DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                    <p className="text-sm text-gray-600">
                        Describe your goal for this step. The AI will read
                        the connected inputs and write a detailed
                        instruction for you.
                    </p>
                    <Textarea
                        value={wandSeed}
                        onChange={(e) => setWandSeed(e.target.value)}
                        placeholder="e.g. A tense dialogue where they discuss the artifact..."
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
                        onClick={onGenerate}
                        disabled={!wandSeed.trim() || isGenerating}
                        className="bg-purple-600 hover:bg-purple-700"
                    >
                        {isGenerating ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin mr-2" />{" "}
                                Generating...
                            </>
                        ) : (
                            <>
                                <Wand2 className="w-4 h-4 mr-2" /> Generate
                                Instruction
                            </>
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};

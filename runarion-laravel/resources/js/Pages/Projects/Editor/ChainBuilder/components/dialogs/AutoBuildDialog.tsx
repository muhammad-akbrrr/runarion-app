import React from "react";
import { Loader2, Sparkles, Zap } from "lucide-react";
import { Button } from "@/Components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/Components/ui/dialog";
import { Textarea } from "@/Components/ui/textarea";
import { GraphExecutionMode } from "../../types";
import { AutoBuildMagicWand } from "../AutoBuildMagicWand";

interface AutoBuildDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    autoBuildPrompt: string;
    setAutoBuildPrompt: (prompt: string) => void;
    autoBuildMode: GraphExecutionMode;
    setAutoBuildMode: (mode: GraphExecutionMode) => void;
    isBuildingGraph: boolean;
    onBuild: () => void;
    storyContext: string;
    workspaceId: string;
    projectId: string;
    aiModel: string;
}

export const AutoBuildDialog: React.FC<AutoBuildDialogProps> = ({
    open,
    onOpenChange,
    autoBuildPrompt,
    setAutoBuildPrompt,
    autoBuildMode,
    setAutoBuildMode,
    isBuildingGraph,
    onBuild,
    storyContext,
    workspaceId,
    projectId,
    aiModel,
}) => {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Sparkles className="w-5 h-5 text-pink-600" />{" "}
                        Auto-Build Workflow
                    </DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                    <p className="text-sm text-gray-600">
                        Describe the flow you want. The AI will generate
                        nodes, connections, and instructions automatically,
                        using your Records context.
                    </p>
                    <div className="flex gap-2 bg-gray-100 p-1 rounded-lg">
                        <button
                            onClick={() => setAutoBuildMode("sequence")}
                            className={`flex-1 py-2 text-xs rounded-md transition-colors ${
                                autoBuildMode === "sequence"
                                    ? "bg-white text-gray-900 shadow-sm"
                                    : "text-gray-600 hover:text-gray-900"
                            }`}
                        >
                            Sequence (Scene A → Scene B)
                        </button>
                        <button
                            onClick={() => setAutoBuildMode("final-only")}
                            className={`flex-1 py-2 text-xs rounded-md transition-colors ${
                                autoBuildMode === "final-only"
                                    ? "bg-white text-gray-900 shadow-sm"
                                    : "text-gray-600 hover:text-gray-900"
                            }`}
                        >
                            Final Only (Context → Final)
                        </button>
                    </div>
                    <div className="relative">
                        <Textarea
                            value={autoBuildPrompt}
                            onChange={(e) =>
                                setAutoBuildPrompt(e.target.value)
                            }
                            placeholder="e.g. A scene where Vex investigates the derelict ship and gets ambushed..."
                            className="min-h-32 max-h-96 overflow-y-auto overflow-x-hidden pr-12 resize-none break-all whitespace-pre-wrap"
                        />
                        <div className="absolute top-2 right-2">
                            <AutoBuildMagicWand
                                text={autoBuildPrompt}
                                onEnhanced={(enhanced) =>
                                    setAutoBuildPrompt(enhanced)
                                }
                                storyContext={storyContext}
                                workspaceId={workspaceId}
                                projectId={projectId}
                                aiModel={aiModel}
                                disabled={isBuildingGraph}
                            />
                        </div>
                    </div>
                </div>
                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={onBuild}
                        disabled={!autoBuildPrompt || isBuildingGraph}
                        className="bg-pink-600 hover:bg-pink-700"
                    >
                        {isBuildingGraph ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin mr-2" />{" "}
                                Building...
                            </>
                        ) : (
                            <>
                                <Zap className="w-4 h-4 mr-2" /> Build Graph
                            </>
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};

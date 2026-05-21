import React from "react";
import { GraphNodeType, GraphExecutionMode } from "../types";
import { Button } from "@/Components/ui/button";
import {
    Box,
    Type,
    Wand2,
    Trash2,
    Loader2,
    Sparkles,
    Zap,
    Layers,
    ArrowRightToLine,
} from "lucide-react";

interface ToolbarProps {
    selectedNodeIds: string[];
    executionMode: GraphExecutionMode;
    isFlowRunning: boolean;
    onAddNode: (type: GraphNodeType) => void;
    onDeleteSelected: () => void;
    onOpenAutoBuild: () => void;
    onOpenRefiner: () => void;
    onSetExecutionMode: (mode: GraphExecutionMode) => void;
    onExecuteFlow: () => void;
}

export const Toolbar: React.FC<ToolbarProps> = ({
    selectedNodeIds,
    executionMode,
    isFlowRunning,
    onAddNode,
    onDeleteSelected,
    onOpenAutoBuild,
    onOpenRefiner,
    onSetExecutionMode,
    onExecuteFlow,
}) => {
    return (
        <div className="w-full bg-white border-b border-gray-300 px-4 py-3 flex items-center justify-between shadow-sm z-50">
            <div className="flex items-center gap-3">
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onAddNode("prompt")}
                    title="Add Prompt Node"
                >
                    <Box className="w-4 h-4 mr-2 text-blue-600" /> Prompt
                </Button>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onAddNode("context")}
                    title="Add Context Node"
                >
                    <Type className="w-4 h-4 mr-2 text-green-600" /> Context
                </Button>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onAddNode("logic")}
                    title="Add Logic Node"
                >
                    <Wand2 className="w-4 h-4 mr-2 text-purple-600" /> Logic
                </Button>
                <div className="w-px h-6 bg-gray-300 mx-2" />
                <Button
                    variant="outline"
                    size="sm"
                    onClick={onOpenAutoBuild}
                    title="Auto-Build Graph"
                >
                    <Sparkles className="w-4 h-4 mr-2 text-pink-600" /> Auto-Build
                </Button>
                {selectedNodeIds.length > 0 && (
                    <>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={onDeleteSelected}
                            title="Delete selected nodes"
                            className="text-red-600 hover:text-red-700 hover:bg-red-50 border-red-300"
                        >
                            <Trash2 className="w-4 h-4 mr-2" /> Delete (
                            {selectedNodeIds.length})
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={onOpenRefiner}
                            title="Enhance selected nodes"
                        >
                            <Wand2 className="w-4 h-4 mr-2" /> Refine (
                            {selectedNodeIds.length})
                        </Button>
                    </>
                )}
                <div className="w-px h-6 bg-gray-300 mx-2" />
                <div className="flex bg-gray-100 rounded-lg p-0.5 border border-gray-300">
                    <button
                        onClick={() => onSetExecutionMode("final-only")}
                        className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all flex items-center gap-2 ${
                            executionMode === "final-only"
                                ? "bg-white text-gray-900 shadow-sm"
                                : "text-gray-600 hover:text-gray-900"
                        }`}
                    >
                        <ArrowRightToLine className="w-3 h-3" /> Final Only
                    </button>
                    <button
                        onClick={() => onSetExecutionMode("sequence")}
                        className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all flex items-center gap-2 ${
                            executionMode === "sequence"
                                ? "bg-white text-gray-900 shadow-sm"
                                : "text-gray-600 hover:text-gray-900"
                        }`}
                    >
                        <Layers className="w-3 h-3" /> Sequence
                    </button>
                </div>
                <div className="w-px h-6 bg-gray-300 mx-2" />
                <Button
                    onClick={onExecuteFlow}
                    disabled={isFlowRunning}
                    className="bg-green-600 hover:bg-green-700 text-white"
                >
                    {isFlowRunning ? (
                        <>
                            <Loader2 className="w-4 h-4 animate-spin mr-2" />{" "}
                            Running...
                        </>
                    ) : (
                        <>
                            <Zap className="w-4 h-4 mr-2" />
                            {executionMode === "final-only"
                                ? "Run & Write Final"
                                : "Run & Write All"}
                        </>
                    )}
                </Button>
            </div>
        </div>
    );
};

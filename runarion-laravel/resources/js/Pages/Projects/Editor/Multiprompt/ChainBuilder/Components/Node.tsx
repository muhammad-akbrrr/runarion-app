import React, { useState } from "react";
import { GraphNode, GraphNodeType } from "../types";
import {
    Box,
    Type,
    Wand2,
    Play,
    Trash2,
    Eye,
    CheckCircle2,
    AlertTriangle,
    Download,
    Sparkles,
    ChevronDown,
    ChevronUp,
} from "lucide-react";
import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";

interface NodeProps {
    node: GraphNode;
    isSelected: boolean;
    zIndex?: number;
    onSelect: (e: React.MouseEvent) => void;
    onDragStart: (e: React.MouseEvent) => void;
    onConnectorMouseUp?: (e: React.MouseEvent) => void;
    onUpdate: (updates: Partial<GraphNode["data"]>) => void;
    onDelete: () => void;
    onExecute: () => void;
    onInspect: () => void;
    onApplyResult?: (text: string) => void;
    onMagicWand?: (seed: string) => void;
    workspaceId?: string;
    projectId?: string;
}

const getNodeColors = (type: GraphNodeType) => {
    switch (type) {
        case "prompt":
            return {
                bg: "bg-blue-50",
                border: "border-blue-300",
                headerBg: "bg-blue-100",
                headerBorder: "border-blue-200",
                icon: "text-blue-600",
            };
        case "context":
            return {
                bg: "bg-green-50",
                border: "border-green-300",
                headerBg: "bg-green-100",
                headerBorder: "border-green-200",
                icon: "text-green-600",
            };
        case "logic":
            return {
                bg: "bg-purple-50",
                border: "border-purple-300",
                headerBg: "bg-purple-100",
                headerBorder: "border-purple-200",
                icon: "text-purple-600",
            };
    }
};

// Separate component for expandable output display
const OutputDisplay: React.FC<{
    output: string;
    onApplyResult?: (text: string) => void;
}> = ({ output, onApplyResult }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    return (
        <div className="mt-2 pt-2 border-t border-gray-300">
            <div className="flex justify-between items-center mb-1">
                <span className="text-[9px] font-bold text-green-600 uppercase">
                    Generated Output
                </span>
                <div className="flex gap-1 items-center">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-5 w-5 p-0 text-gray-500 hover:text-gray-700"
                        onClick={(e) => {
                            e.stopPropagation();
                            setIsExpanded(!isExpanded);
                        }}
                        title={isExpanded ? "Collapse" : "Expand"}
                    >
                        {isExpanded ? (
                            <ChevronUp className="w-3 h-3" />
                        ) : (
                            <ChevronDown className="w-3 h-3" />
                        )}
                    </Button>
                    {onApplyResult && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-5 w-5 p-0 text-gray-500 hover:text-gray-700"
                            onClick={(e) => {
                                e.stopPropagation();
                                onApplyResult(output);
                            }}
                            title="Insert to editor"
                        >
                            <Download className="w-3 h-3" />
                        </Button>
                    )}
                </div>
            </div>
            <div
                className={`text-[10px] text-gray-600 bg-white p-1.5 rounded border border-gray-200 font-mono ${
                    isExpanded ? "max-h-96 overflow-y-auto" : "line-clamp-3"
                }`}
                onClick={(e) => e.stopPropagation()}
            >
                {output}
            </div>
        </div>
    );
};

export const Node: React.FC<NodeProps> = ({
    node,
    isSelected,
    zIndex,
    onSelect,
    onDragStart,
    onConnectorMouseUp,
    onUpdate,
    onDelete,
    onExecute,
    onInspect,
    onApplyResult,
    onMagicWand,
    workspaceId,
    projectId,
}) => {
    const colors = getNodeColors(node.type);
    const isRunning = node.data.status === "running";
    const isCompleted = node.data.status === "completed";
    const isError = node.data.status === "error";

    return (
        <div
            data-node-id={node.id}
            className={`
                absolute w-[300px] rounded-lg shadow-md border-2
                transition-[box-shadow,border-color,background-color,ring-color] duration-150
                ${colors.bg} ${colors.border}
                ${isSelected ? "ring-2 ring-blue-500 shadow-lg" : ""}
                ${isRunning ? "ring-2 ring-yellow-400 animate-pulse" : ""}
                pointer-events-auto
            `}
            style={{
                transform: `translate(${node.position.x}px, ${node.position.y}px)`,
                zIndex: zIndex || "auto",
            }}
            onMouseDown={onSelect}
        >
            {/* Header */}
            <div
                className={`p-2 border-b flex items-center gap-2 justify-between ${colors.headerBg} ${colors.headerBorder} rounded-t-lg`}
            >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                    {node.type === "prompt" && (
                        <Box className={`w-4 h-4 ${colors.icon} shrink-0`} />
                    )}
                    {node.type === "context" && (
                        <Type className={`w-4 h-4 ${colors.icon} shrink-0`} />
                    )}
                    {node.type === "logic" && (
                        <Wand2 className={`w-4 h-4 ${colors.icon} shrink-0`} />
                    )}
                    <Input
                        value={node.data.label}
                        onChange={(e) => onUpdate({ label: e.target.value })}
                        className="h-auto py-0 px-1 bg-transparent border-none shadow-none text-xs font-semibold text-gray-800 focus-visible:ring-0 focus-visible:border-none flex-1 min-w-0"
                        placeholder="Node label"
                        onClick={(e) => e.stopPropagation()}
                        onMouseDown={(e) => e.stopPropagation()}
                    />
                </div>
                <div className="flex gap-1 shrink-0">
                    {(node.type === "prompt" || node.type === "logic") &&
                        onMagicWand &&
                        workspaceId &&
                        projectId && (
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    if (onMagicWand) {
                                        onMagicWand(node.data.content || "");
                                    }
                                }}
                                className="p-1 text-purple-600 hover:text-purple-700 hover:bg-purple-50 rounded transition-colors"
                                title={
                                    node.type === "logic"
                                        ? "AI Auto-Write Logic/Analysis Instruction"
                                        : "AI Auto-Write Instruction"
                                }
                            >
                                <Sparkles className="w-3 h-3" />
                            </button>
                        )}
                    {node.type !== "context" && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 p-0 text-green-600 hover:text-green-700"
                            onClick={(e) => {
                                e.stopPropagation();
                                onExecute();
                            }}
                            title="Execute this node"
                        >
                            <Play className="w-3 h-3" />
                        </Button>
                    )}
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 p-0 text-red-600 hover:text-red-700"
                        onClick={(e) => {
                            e.stopPropagation();
                            onDelete();
                        }}
                        title="Delete node"
                    >
                        <Trash2 className="w-3 h-3" />
                    </Button>
                </div>
            </div>

            {/* Content */}
            <div className="p-3 relative">
                <textarea
                    value={node.data.content}
                    onChange={(e) => onUpdate({ content: e.target.value })}
                    placeholder={
                        node.type === "prompt"
                            ? "Instructions for AI..."
                            : node.type === "context"
                              ? "Context data..."
                              : "Logic/analysis instructions..."
                    }
                    className="w-full bg-white rounded border border-gray-300 p-2 text-xs text-gray-700 resize-y min-h-20 focus:border-gray-400 focus:outline-none"
                    onClick={(e) => e.stopPropagation()}
                    onMouseDown={(e) => e.stopPropagation()}
                />

                {/* Output Display */}
                {node.data.output && (
                    <OutputDisplay
                        output={node.data.output}
                        onApplyResult={onApplyResult}
                    />
                )}

                {/* Status Indicators */}
                <div className="absolute -bottom-3 right-2 flex gap-1">
                    {isCompleted && (
                        <CheckCircle2 className="w-5 h-5 text-green-500 bg-white rounded-full" />
                    )}
                    {isError && (
                        <AlertTriangle className="w-5 h-5 text-red-500 bg-white rounded-full" />
                    )}
                </div>
                <div className="absolute -bottom-3 left-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 p-0 bg-white border border-gray-300 text-gray-500 hover:text-gray-700"
                        onClick={(e) => {
                            e.stopPropagation();
                            onInspect();
                        }}
                        title="Inspect inputs"
                    >
                        <Eye className="w-3 h-3" />
                    </Button>
                </div>
            </div>

            {/* Connectors */}
            <div
                className="absolute left-0 top-1/2 -translate-x-1/2 w-3 h-3 bg-gray-400 rounded-full border-2 border-white cursor-crosshair hover:bg-gray-500 transition-colors shadow-sm z-10"
                onMouseUp={(e) => {
                    e.stopPropagation();
                    if (onConnectorMouseUp) {
                        onConnectorMouseUp(e);
                    }
                }}
            />
            <div
                className="absolute right-0 top-1/2 translate-x-1/2 w-3 h-3 bg-gray-400 rounded-full border-2 border-white cursor-crosshair hover:bg-gray-500 transition-colors shadow-sm z-10"
                onMouseDown={(e) => {
                    e.stopPropagation();
                    onDragStart(e);
                }}
            />
        </div>
    );
};

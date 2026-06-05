import React from "react";
import { GraphNode, GraphEdge } from "../types";
import { Button } from "@/Components/ui/button";
import { ZoomIn, ZoomOut, Maximize, Undo2, Redo2 } from "lucide-react";

interface CanvasControlsProps {
    zoom: number;
    historyIndexRef: React.MutableRefObject<number>;
    historyRef: React.MutableRefObject<
        Array<{ nodes: GraphNode[]; edges: GraphEdge[] }>
    >;
    onUndo: () => void;
    onRedo: () => void;
    onZoomIn: () => void;
    onZoomOut: () => void;
    onResetView: () => void;
}

export const CanvasControls: React.FC<CanvasControlsProps> = ({
    zoom,
    historyIndexRef,
    historyRef,
    onUndo,
    onRedo,
    onZoomIn,
    onZoomOut,
    onResetView,
}) => {
    return (
        <div className="absolute bottom-4 right-4 z-50 flex flex-col items-end gap-2 pointer-events-auto">
            {/* Undo/Redo Controls */}
            <div className="bg-white p-1.5 rounded-lg border border-gray-300 shadow-lg flex flex-row gap-1">
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={onUndo}
                    disabled={historyIndexRef.current === 0}
                    title="Undo (Ctrl+Z)"
                >
                    <Undo2 className="w-4 h-4" />
                </Button>
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={onRedo}
                    disabled={
                        historyIndexRef.current >= historyRef.current.length - 1
                    }
                    title="Redo (Ctrl+Y)"
                >
                    <Redo2 className="w-4 h-4" />
                </Button>
            </div>
            {/* Zoom Controls */}
            <div className="bg-white p-1.5 rounded-lg border border-gray-300 shadow-lg flex flex-col gap-1">
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={onZoomIn}
                >
                    <ZoomIn className="w-4 h-4" />
                </Button>
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={onZoomOut}
                >
                    <ZoomOut className="w-4 h-4" />
                </Button>
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={onResetView}
                >
                    <Maximize className="w-4 h-4" />
                </Button>
                <div className="text-[9px] text-center text-gray-500 border-t border-gray-300 pt-1 mt-1">
                    {Math.round(zoom * 100)}%
                </div>
            </div>
        </div>
    );
};

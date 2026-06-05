import React from "react";
import { GraphNode, GraphEdge } from "../types";

interface EdgeProps {
    edge: GraphEdge;
    sourceNode: GraphNode | undefined;
    targetNode: GraphNode | undefined;
    isSelected: boolean;
    pan: { x: number; y: number };
    zoom: number;
    sourceHeight?: number;
    targetHeight?: number;
    onClick?: (edgeId: string) => void;
}

export const Edge: React.FC<EdgeProps> = ({
    edge,
    sourceNode,
    targetNode,
    isSelected,
    pan,
    zoom,
    sourceHeight,
    targetHeight,
    onClick,
}) => {
    if (!sourceNode || !targetNode) return null;

    // Node dimensions - use dynamic heights with fallback
    const nodeWidth = 300;
    const effectiveSourceHeight = sourceHeight || 82;
    const effectiveTargetHeight = targetHeight || 82;

    // Calculate edge positions in world coordinates
    // Connectors are at vertical center of the node + 3.5% offset downwards (capped at 8px)
    const sourceX = sourceNode.position.x + nodeWidth;
    const sourceOffset = Math.min(effectiveSourceHeight * 0.04, 8);
    const sourceY =
        sourceNode.position.y + effectiveSourceHeight / 2 + sourceOffset;
    const targetX = targetNode.position.x;
    const targetOffset = Math.min(effectiveTargetHeight * 0.04, 8);
    const targetY =
        targetNode.position.y + effectiveTargetHeight / 2 + targetOffset;

    // Transform to screen coordinates (account for pan/zoom)
    const screenSourceX = sourceX * zoom + pan.x;
    const screenSourceY = sourceY * zoom + pan.y;
    const screenTargetX = targetX * zoom + pan.x;
    const screenTargetY = targetY * zoom + pan.y;

    // Bezier curve control points (in screen space)
    const controlPoint1X = screenSourceX + 50 * zoom;
    const controlPoint1Y = screenSourceY;
    const controlPoint2X = screenTargetX - 50 * zoom;
    const controlPoint2Y = screenTargetY;

    const pathData = `M ${screenSourceX} ${screenSourceY} C ${controlPoint1X} ${controlPoint1Y}, ${controlPoint2X} ${controlPoint2Y}, ${screenTargetX} ${screenTargetY}`;

    return (
        <g
            onClick={(e) => {
                e.stopPropagation();
                onClick?.(edge.id);
            }}
            className="cursor-pointer"
        >
            {/* Invisible wider path for easier clicking */}
            <path
                d={pathData}
                stroke="transparent"
                strokeWidth={15}
                fill="none"
            />
            {/* Visible path with animated flow */}
            <path
                d={pathData}
                stroke={isSelected ? "#3b82f6" : "#6b7280"}
                strokeWidth={isSelected ? 3 : 2}
                fill="none"
                strokeDasharray="8 4"
                strokeLinecap="round"
                className="pointer-events-none transition-colors duration-150"
                style={{
                    animation: "flowAnimation 1s linear infinite",
                }}
            />
        </g>
    );
};

// Render connecting line (while dragging)
export const ConnectingLine: React.FC<{
    sourceX: number;
    sourceY: number;
    targetX: number;
    targetY: number;
    pan: { x: number; y: number };
    zoom: number;
}> = ({ sourceX, sourceY, targetX, targetY, pan, zoom }) => {
    // Transform world coordinates to screen coordinates
    const screenSourceX = sourceX * zoom + pan.x;
    const screenSourceY = sourceY * zoom + pan.y;
    const screenTargetX = targetX * zoom + pan.x;
    const screenTargetY = targetY * zoom + pan.y;

    const controlPoint1X = screenSourceX + 50 * zoom;
    const controlPoint1Y = screenSourceY;
    const controlPoint2X = screenTargetX - 50 * zoom;
    const controlPoint2Y = screenTargetY;

    const pathData = `M ${screenSourceX} ${screenSourceY} C ${controlPoint1X} ${controlPoint1Y}, ${controlPoint2X} ${controlPoint2Y}, ${screenTargetX} ${screenTargetY}`;

    return (
        <path
            d={pathData}
            stroke="#60a5fa"
            strokeWidth="2"
            strokeDasharray="8 4"
            strokeLinecap="round"
            fill="none"
            style={{
                animation: "flowAnimation 1s linear infinite",
            }}
        />
    );
};

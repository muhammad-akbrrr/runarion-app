import React from 'react';
import { GraphNode, GraphEdge } from '../types';

interface EdgeProps {
    edge: GraphEdge;
    sourceNode: GraphNode | undefined;
    targetNode: GraphNode | undefined;
    isSelected: boolean;
    pan: { x: number; y: number };
    zoom: number;
}

export const Edge: React.FC<EdgeProps> = ({
    edge,
    sourceNode,
    targetNode,
    isSelected,
    pan,
    zoom,
}) => {
    if (!sourceNode || !targetNode) return null;

    // Node dimensions
    const nodeWidth = 300;
    const nodeHeight = 50; // Approximate middle point

    // Calculate edge positions in world coordinates
    const sourceX = sourceNode.position.x + nodeWidth;
    const sourceY = sourceNode.position.y + nodeHeight;
    const targetX = targetNode.position.x;
    const targetY = targetNode.position.y + nodeHeight;

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
        <path
            d={pathData}
            stroke={isSelected ? '#3b82f6' : '#6b7280'}
            strokeWidth={isSelected ? 3 : 2}
            fill="none"
            markerEnd="url(#arrowhead)"
            className="transition-all"
        />
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
            strokeDasharray="5,5"
            fill="none"
        />
    );
};


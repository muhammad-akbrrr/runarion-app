// Chain Builder Type Definitions

export type GraphNodeType = 'prompt' | 'context' | 'logic';

export type GraphExecutionMode = 'final-only' | 'sequence';

export type NodeStatus = 'idle' | 'running' | 'completed' | 'error';

export interface GraphNodeData {
    label: string;
    content: string; // The user's prompt or context text
    output?: string; // The AI generation result
    status: NodeStatus;
    errorMessage?: string;
}

export interface GraphNode {
    id: string;
    type: GraphNodeType;
    position: { x: number; y: number };
    data: GraphNodeData;
    width?: number;
    height?: number;
}

export interface GraphEdge {
    id: string;
    source: string; // Node ID
    target: string; // Node ID
}

export interface GraphInput {
    label: string;
    text: string;
    type: GraphNodeType;
}

export interface GraphTemplate {
    id: string;
    name: string;
    nodes: GraphNode[];
    edges: GraphEdge[];
    projectId?: string;
    userId?: string;
    createdAt?: string;
}

// Entity from Records system
export interface Entity {
    vertex_id: string;
    name: string;
    type: string;
    properties: Record<string, any>;
}

// Project Chapter for story context
export interface ProjectChapter {
    order: number;
    chapter_name: string;
    content: string;
    summary?: string;
    plot_points?: Array<string>;
}


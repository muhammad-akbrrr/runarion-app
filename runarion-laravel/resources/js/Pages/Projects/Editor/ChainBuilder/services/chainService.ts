// Chain Builder API service

import { GraphNode, GraphInput, GraphExecutionMode, GraphNodeType } from '../types';

export interface ExecuteNodeRequest {
    node_prompt: string;
    inputs: GraphInput[];
    story_context: string;
    ai_model: string;
    author_profile?: string;
    settings?: Record<string, any>;
    node_type?: 'prompt' | 'logic'; // Specify if this is for a prompt or logic node
}

export interface GenerateGraphLayoutRequest {
    user_goal: string;
    story_context: string;
    entities: Array<{ name: string; type: string; properties: Record<string, any> }>;
    mode: GraphExecutionMode;
    ai_model: string;
}

export interface GenerateInstructionRequest {
    seed: string;
    inputs: GraphInput[];
    story_context: string;
    ai_model: string;
    node_type?: 'prompt' | 'logic'; // Optional: specify if this is for a prompt or logic node
}

export interface RefineSelectionRequest {
    selected_nodes: GraphNode[];
    selected_edges: Array<{ source: string; target: string }>;
    instruction: string;
    story_context: string;
    ai_model: string;
}

/**
 * Get CSRF token from meta tag
 */
const getCsrfToken = (): string => {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? (token as HTMLMetaElement).content : '';
};

/**
 * Execute a single graph node
 */
export const executeNode = async (
    request: ExecuteNodeRequest,
    workspaceId: string,
    projectId: string
): Promise<string> => {
    const response = await fetch(
        `/${workspaceId}/projects/${projectId}/editor/chain-builder/execute-node`,
        {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-CSRF-TOKEN': getCsrfToken(),
            },
            body: JSON.stringify(request),
        }
    );

    if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Unknown error' }));
        const errorMessage = error.error || error.message || `HTTP ${response.status}`;
        const errorDetails = error.details ? ` Details: ${JSON.stringify(error.details)}` : '';
        throw new Error(`${errorMessage}${errorDetails}`);
    }

    const data = await response.json();
    return data.result || '';
};

/**
 * Generate graph layout from user goal
 */
export const generateGraphLayout = async (
    request: GenerateGraphLayoutRequest,
    workspaceId: string,
    projectId: string
): Promise<{ nodes: GraphNode[]; edges: Array<{ source: string; target: string }> }> => {
    const response = await fetch(
        `/${workspaceId}/projects/${projectId}/editor/chain-builder/generate-layout`,
        {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-CSRF-TOKEN': getCsrfToken(),
            },
            body: JSON.stringify(request),
        }
    );

    if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Unknown error' }));
        const errorMessage = error.error || error.message || `HTTP ${response.status}`;
        const errorDetails = error.details ? ` Details: ${JSON.stringify(error.details)}` : '';
        throw new Error(`${errorMessage}${errorDetails}`);
    }

    const data = await response.json();
    return {
        nodes: data.nodes || [],
        edges: data.edges || [],
    };
};

/**
 * Generate instruction using Magic Wand
 */
export const generateInstruction = async (
    request: GenerateInstructionRequest,
    workspaceId: string,
    projectId: string
): Promise<string> => {
    const response = await fetch(
        `/${workspaceId}/projects/${projectId}/editor/chain-builder/generate-instruction`,
        {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-CSRF-TOKEN': getCsrfToken(),
            },
            body: JSON.stringify(request),
        }
    );

    if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Unknown error' }));
        const errorMessage = error.error || error.message || `HTTP ${response.status}`;
        const errorDetails = error.details ? ` Details: ${JSON.stringify(error.details)}` : '';
        throw new Error(`${errorMessage}${errorDetails}`);
    }

    const data = await response.json();
    return data.instruction || request.seed;
};

/**
 * Refine selected nodes
 */
export const refineSelection = async (
    request: RefineSelectionRequest,
    workspaceId: string,
    projectId: string
): Promise<{ nodes: GraphNode[]; edges: Array<{ source: string; target: string }> }> => {
    const response = await fetch(
        `/${workspaceId}/projects/${projectId}/editor/chain-builder/refine-selection`,
        {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-CSRF-TOKEN': getCsrfToken(),
            },
            body: JSON.stringify(request),
        }
    );

    if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Unknown error' }));
        const errorMessage = error.error || error.message || `HTTP ${response.status}`;
        const errorDetails = error.details ? ` Details: ${JSON.stringify(error.details)}` : '';
        throw new Error(`${errorMessage}${errorDetails}`);
    }

    const data = await response.json();
    return {
        nodes: data.nodes || [],
        edges: data.edges || [],
    };
};


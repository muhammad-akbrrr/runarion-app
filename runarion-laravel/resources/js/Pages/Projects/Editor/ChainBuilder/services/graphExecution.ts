// Graph execution engine

import { GraphNode, GraphEdge, GraphInput, GraphExecutionMode } from '../types';
import { topologicalSort, getLeafNodes } from '../utils/graphHelpers';
import { executeNode, ExecuteNodeRequest } from './chainService';

/**
 * Gather inputs for a target node from connected source nodes
 */
export const gatherNodeInputs = (
    targetNodeId: string,
    nodes: GraphNode[],
    edges: GraphEdge[],
    nodeOutputs: Map<string, string>
): GraphInput[] => {
    const incomingEdges = edges.filter(e => e.target === targetNodeId);
    const inputs: GraphInput[] = [];

    for (const edge of incomingEdges) {
        const sourceNode = nodes.find(n => n.id === edge.source);
        if (!sourceNode) continue;

        let text = '';
        if (nodeOutputs.has(edge.source)) {
            text = nodeOutputs.get(edge.source) || '';
        } else {
            // For context nodes, use content directly
            // For other nodes, use output if available
            text = sourceNode.type === 'context' 
                ? sourceNode.data.content 
                : (sourceNode.data.output || '');
        }

        if (text) {
            inputs.push({
                label: sourceNode.data.label,
                text: text,
                type: sourceNode.type,
            });
        }
    }

    return inputs;
};

/**
 * Execute full graph flow
 */
export const executeFullFlow = async (
    nodes: GraphNode[],
    edges: GraphEdge[],
    executionMode: GraphExecutionMode,
    storyContext: string,
    aiModel: string,
    authorProfile: string | undefined,
    settings: Record<string, any> | undefined,
    workspaceId: string,
    projectId: string,
    onNodeUpdate: (nodeId: string, updates: Partial<GraphNode['data']>) => void
): Promise<string[]> => {
    // Get execution order (topological sort)
    const executionOrder = topologicalSort(nodes, edges);
    
    // Flatten to single array for sequential execution
    const flatOrder: string[] = [];
    executionOrder.forEach(level => {
        flatOrder.push(...level);
    });

    // Initialize outputs map with context nodes
    const nodeOutputs = new Map<string, string>();
    nodes.forEach(n => {
        if (n.type === 'context') {
            nodeOutputs.set(n.id, n.data.content);
        }
    });

    // For sequence mode: incrementally build story context by appending each prompt node's output
    // For final-only mode: use static story context (all nodes see the same base story)
    let currentStoryContext = storyContext;

    // Execute nodes in order
    for (const nodeId of flatOrder) {
        const node = nodes.find(n => n.id === nodeId);
        if (!node || node.type === 'context') continue;

        // Update status to running
        onNodeUpdate(nodeId, { status: 'running' });

        try {
            // Gather inputs
            const inputs = gatherNodeInputs(nodeId, nodes, edges, nodeOutputs);

            // Execute node with current story context
            const request: ExecuteNodeRequest = {
                node_prompt: node.data.content,
                inputs,
                story_context: currentStoryContext,
                ai_model: aiModel,
                author_profile: authorProfile,
                settings,
                node_type: node.type === 'logic' ? 'logic' : 'prompt', // Pass node type to backend
            };

            const result = await executeNode(request, workspaceId, projectId);
            
            // Store output
            nodeOutputs.set(nodeId, result);
            onNodeUpdate(nodeId, { status: 'completed', output: result });

            // In SEQUENCE mode: Append prompt node outputs to story context for subsequent nodes
            // This allows each new scene/passage to see all previous scenes as part of the story
            if (executionMode === 'sequence' && node.type === 'prompt' && result) {
                // Append the new scene/passage to the growing story context
                const separator = currentStoryContext && !currentStoryContext.endsWith('\n') ? '\n\n' : '';
                currentStoryContext = currentStoryContext + separator + result;
                
                console.log(`[Sequence Mode] Appended node ${nodeId} output to story context. New context length: ${currentStoryContext.length}`);
            }
        } catch (error) {
            console.error(`Error executing node ${nodeId}:`, error);
            onNodeUpdate(nodeId, { 
                status: 'error', 
                errorMessage: error instanceof Error ? error.message : 'Unknown error' 
            });
            throw error;
        }
    }

    // Return results based on execution mode
    if (executionMode === 'final-only') {
        // Final-Only: Only return outputs from leaf prompt nodes (final story text)
        const leafNodes = getLeafNodes(nodes, edges);
        const finalTexts = leafNodes
            .filter(n => n.type === 'prompt') // Only prompt nodes produce story text
            .map(n => nodeOutputs.get(n.id))
            .filter(Boolean) as string[];
        return finalTexts;
    } else {
        // Sequence mode: return all prompt node outputs in execution order
        const sequenceTexts = flatOrder
            .map(id => {
                const node = nodes.find(n => n.id === id);
                if (node && node.type === 'prompt') {
                    return nodeOutputs.get(id);
                }
                return null;
            })
            .filter(Boolean) as string[];
        return sequenceTexts;
    }
};


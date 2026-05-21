// Graph manipulation and analysis utilities

import { GraphNode, GraphEdge } from '../types';

/**
 * Detect cycles in the graph using DFS
 */
export const detectCycles = (nodes: GraphNode[], edges: GraphEdge[]): boolean => {
    const adjacency = new Map<string, string[]>();
    nodes.forEach(n => adjacency.set(n.id, []));
    edges.forEach(e => {
        if (adjacency.has(e.source)) {
            adjacency.get(e.source)?.push(e.target);
        }
    });

    const visited = new Set<string>();
    const recStack = new Set<string>();

    const isCyclic = (nodeId: string): boolean => {
        if (!visited.has(nodeId)) {
            visited.add(nodeId);
            recStack.add(nodeId);
            const neighbors = adjacency.get(nodeId) || [];
            for (const neighbor of neighbors) {
                if (!visited.has(neighbor) && isCyclic(neighbor)) return true;
                if (recStack.has(neighbor)) return true;
            }
        }
        recStack.delete(nodeId);
        return false;
    };

    for (const node of nodes) {
        if (isCyclic(node.id)) return true;
    }
    return false;
};

/**
 * Topological sort using Kahn's algorithm
 * Returns execution order (nodes that can be executed in parallel are at same level)
 */
export const topologicalSort = (nodes: GraphNode[], edges: GraphEdge[]): string[][] => {
    const adjacency = new Map<string, string[]>();
    const inDegree = new Map<string, number>();
    
    nodes.forEach(n => {
        adjacency.set(n.id, []);
        inDegree.set(n.id, 0);
    });
    
    edges.forEach(e => {
        const current = adjacency.get(e.source) || [];
        current.push(e.target);
        adjacency.set(e.source, current);
        inDegree.set(e.target, (inDegree.get(e.target) || 0) + 1);
    });
    
    const queue: string[] = [];
    inDegree.forEach((degree, id) => {
        if (degree === 0) queue.push(id);
    });
    
    const executionOrder: string[][] = [];
    
    while (queue.length > 0) {
        const level: string[] = [];
        const levelSize = queue.length;
        
        for (let i = 0; i < levelSize; i++) {
            const u = queue.shift()!;
            level.push(u);
            const neighbors = adjacency.get(u) || [];
            for (const v of neighbors) {
                inDegree.set(v, (inDegree.get(v)! - 1));
                if (inDegree.get(v) === 0) {
                    queue.push(v);
                }
            }
        }
        executionOrder.push(level);
    }
    
    return executionOrder;
};

/**
 * Get all nodes that have no incoming edges (root nodes)
 */
export const getRootNodes = (nodes: GraphNode[], edges: GraphEdge[]): GraphNode[] => {
    const hasIncoming = new Set<string>();
    edges.forEach(e => hasIncoming.add(e.target));
    return nodes.filter(n => !hasIncoming.has(n.id));
};

/**
 * Get all nodes that have no outgoing edges (leaf nodes)
 */
export const getLeafNodes = (nodes: GraphNode[], edges: GraphEdge[]): GraphNode[] => {
    const hasOutgoing = new Set<string>();
    edges.forEach(e => hasOutgoing.add(e.source));
    return nodes.filter(n => !hasOutgoing.has(n.id));
};


import React, { useState, useRef, useEffect, useCallback } from 'react';
import { GraphNode, GraphEdge, GraphNodeType, GraphExecutionMode, Entity, ProjectChapter, GraphTemplate } from './types';
import { Node } from './components/Node';
import { Edge, ConnectingLine } from './components/Edge';
import { RecordsDrawer } from './components/RecordsDrawer';
import { detectCycles, topologicalSort, getLeafNodes } from './utils/graphHelpers';
import { screenToWorld, zoomAtPoint } from './utils/viewportHelpers';
import { getFullStoryContext } from './utils/storyContext';
import { formatEntityForContext } from './utils/formatEntityForContext';
import { executeFullFlow, gatherNodeInputs } from './services/graphExecution';
import { generateGraphLayout, generateInstruction, refineSelection } from './services/chainService';
import { Box, Type, Wand2, Play, Trash2, ZoomIn, ZoomOut, Maximize, X, Loader2, Sparkles, Zap, Layers, ArrowRightToLine, FolderOpen, Save, ArrowRight, Undo2, Redo2, FileText } from 'lucide-react';
import { router } from '@inertiajs/react';
import { Button } from '@/Components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/Components/ui/dialog';
import { Input } from '@/Components/ui/input';
import { Textarea } from '@/Components/ui/textarea';
import { Eye } from 'lucide-react';
import { MagicWandButton } from '@/Components/MagicWandButton';

// Custom Magic Wand for Auto-Build that uses story context
const AutoBuildMagicWand: React.FC<{
    text: string;
    onEnhanced: (enhanced: string) => void;
    storyContext: string;
    workspaceId: string;
    projectId: string;
    aiModel: string;
    disabled: boolean;
}> = ({ text, onEnhanced, storyContext, workspaceId, projectId, aiModel, disabled }) => {
    const [isEnhancing, setIsEnhancing] = useState(false);

    const handleEnhance = async () => {
        if (!text.trim() || isEnhancing || disabled) return;

        setIsEnhancing(true);
        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/enhance-auto-build-prompt`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'X-CSRF-TOKEN': csrfToken,
                    },
                    body: JSON.stringify({
                        text: text.trim(),
                        story_context: storyContext,
                        model: aiModel,
                    }),
                }
            );

            if (!response.ok) {
                const error = await response.json().catch(() => ({ error: 'Unknown error' }));
                throw new Error(error.error || `HTTP ${response.status}`);
            }

            const data = await response.json();
            if (data.success && data.enhanced_text) {
                onEnhanced(data.enhanced_text);
            } else {
                throw new Error(data.error || 'No enhanced text returned');
            }
        } catch (error) {
            console.error('Auto-Build Magic Wand error:', error);
            alert(`Failed to enhance prompt: ${error instanceof Error ? error.message : 'Unknown error'}`);
        } finally {
            setIsEnhancing(false);
        }
    };

    return (
        <button
            onClick={handleEnhance}
            disabled={disabled || isEnhancing || !text.trim()}
            className="h-8 w-8 border-purple-600 bg-purple-50 hover:bg-purple-100 hover:border-purple-700 text-purple-600 rounded-md flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Enhance prompt using story context"
        >
            {isEnhancing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
                <Sparkles className="w-4 h-4" />
            )}
        </button>
    );
};

interface ChainBuilderProps {
    workspaceId: string;
    projectId: string;
    project: any;
    chapters?: ProjectChapter[];
    aiModel?: string;
    authorProfile?: string;
    settings?: Record<string, any>;
    onApplyResult?: (text: string) => void;
}

export const ChainBuilder: React.FC<ChainBuilderProps> = ({
    workspaceId,
    projectId,
    project,
    chapters = [],
    aiModel = 'gemini-2.0-flash',
    authorProfile,
    settings,
    onApplyResult,
}) => {
    // Graph State
    const [nodes, setNodes] = useState<GraphNode[]>([
        {
            id: 'root',
            type: 'prompt',
            position: { x: 300, y: 100 },
            data: { label: 'Start Prompt', content: 'Describe the setting...', status: 'idle' },
        },
    ]);
    const [edges, setEdges] = useState<GraphEdge[]>([]);

    // Interaction State
    const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);
    const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
    const [connectingNodeId, setConnectingNodeId] = useState<string | null>(null);
    const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

    // Viewport State
    const [pan, setPan] = useState({ x: 0, y: 0 });
    const [zoom, setZoom] = useState(1);
    const [isPanning, setIsPanning] = useState(false);
    const [lastMousePan, setLastMousePan] = useState({ x: 0, y: 0 });

    // Execution & Settings State
    const [isFlowRunning, setIsFlowRunning] = useState(false);
    const [executionMode, setExecutionMode] = useState<GraphExecutionMode>('final-only');

    // Modals State
    const [isAutoBuildOpen, setIsAutoBuildOpen] = useState(false);
    const [autoBuildPrompt, setAutoBuildPrompt] = useState('');
    const [isBuildingGraph, setIsBuildingGraph] = useState(false);
    const [autoBuildMode, setAutoBuildMode] = useState<GraphExecutionMode>('sequence');

    const [isRefinerOpen, setIsRefinerOpen] = useState(false);
    const [refinerPrompt, setRefinerPrompt] = useState('');
    const [isRefiningGraph, setIsRefiningGraph] = useState(false);

    const [inspectedNodeId, setInspectedNodeId] = useState<string | null>(null);

    const [wandNodeId, setWandNodeId] = useState<string | null>(null);
    const [wandSeed, setWandSeed] = useState('');
    const [isWandGenerating, setIsWandGenerating] = useState(false);

    // Templates State - collapsed by default
    const [isTemplatesOpen, setIsTemplatesOpen] = useState(false);
    const [templates, setTemplates] = useState<GraphTemplate[]>(() => {
        const saved = localStorage.getItem(`chain_builder_templates_${projectId}`);
        return saved ? JSON.parse(saved) : [];
    });
    const [editingTemplateId, setEditingTemplateId] = useState<string | null>(null);
    const [templateName, setTemplateName] = useState('');

    // Result state for navigation
    const [generatedResult, setGeneratedResult] = useState<string | null>(null);
    const [showResultDialog, setShowResultDialog] = useState(false);

    const canvasRef = useRef<HTMLDivElement>(null);
    const svgRef = useRef<SVGSVGElement>(null);

    // Undo/Redo History
    const [history, setHistory] = useState<Array<{ nodes: GraphNode[]; edges: GraphEdge[] }>>([
        { nodes: [{ id: 'root', type: 'prompt', position: { x: 300, y: 100 }, data: { label: 'Start Prompt', content: 'Describe the setting...', status: 'idle' } }], edges: [] }
    ]);
    const [historyIndex, setHistoryIndex] = useState(0);
    const historyRef = useRef<Array<{ nodes: GraphNode[]; edges: GraphEdge[] }>>([
        { nodes: [{ id: 'root', type: 'prompt', position: { x: 300, y: 100 }, data: { label: 'Start Prompt', content: 'Describe the setting...', status: 'idle' } }], edges: [] }
    ]);
    const historyIndexRef = useRef(0);

    // Save state to history
    const saveToHistory = useCallback((newNodes: GraphNode[], newEdges: GraphEdge[]) => {
        const currentState = { nodes: JSON.parse(JSON.stringify(newNodes)), edges: JSON.parse(JSON.stringify(newEdges)) };
        const newHistory = historyRef.current.slice(0, historyIndexRef.current + 1);
        newHistory.push(currentState);
        // Limit history to 50 states
        if (newHistory.length > 50) {
            newHistory.shift();
        } else {
            historyIndexRef.current = newHistory.length - 1;
        }
        historyRef.current = newHistory;
        setHistory(newHistory);
        setHistoryIndex(historyIndexRef.current);
    }, []);

    // Undo function
    const undo = useCallback(() => {
        if (historyIndexRef.current > 0) {
            historyIndexRef.current -= 1;
            const state = historyRef.current[historyIndexRef.current];
            setNodes(JSON.parse(JSON.stringify(state.nodes)));
            setEdges(JSON.parse(JSON.stringify(state.edges)));
            setHistoryIndex(historyIndexRef.current);
            setSelectedNodeIds([]);
        }
    }, []);

    // Redo function
    const redo = useCallback(() => {
        if (historyIndexRef.current < historyRef.current.length - 1) {
            historyIndexRef.current += 1;
            const state = historyRef.current[historyIndexRef.current];
            setNodes(JSON.parse(JSON.stringify(state.nodes)));
            setEdges(JSON.parse(JSON.stringify(state.edges)));
            setHistoryIndex(historyIndexRef.current);
            setSelectedNodeIds([]);
        }
    }, []);

    // Delete multiple selected nodes at once (defined early for use in keyboard shortcuts)
    const deleteSelectedNodes = useCallback(() => {
        if (selectedNodeIds.length === 0) return;
        
        const idsToDelete = [...selectedNodeIds]; // Capture current selection
        
        setNodes((prev) => {
            const newNodes = prev.filter((n) => !idsToDelete.includes(n.id));
            setEdges((prevEdges) => {
                const newEdges = prevEdges.filter(
                    (e) => !idsToDelete.includes(e.source) && !idsToDelete.includes(e.target)
                );
                saveToHistory(newNodes, newEdges);
                return newEdges;
            });
            setSelectedNodeIds([]);
            return newNodes;
        });
    }, [selectedNodeIds, saveToHistory]);

    // Keyboard shortcuts for undo/redo and delete
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
                e.preventDefault();
                undo();
            } else if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
                e.preventDefault();
                redo();
            } else if ((e.key === 'Delete' || e.key === 'Backspace') && selectedNodeIds.length > 0) {
                // Only delete if not typing in an input/textarea
                const target = e.target as HTMLElement;
                if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA' && !target.isContentEditable) {
                    e.preventDefault();
                    deleteSelectedNodes();
                }
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [undo, redo, selectedNodeIds, deleteSelectedNodes]);

    // Load chapters if not provided
    const [loadedChapters, setLoadedChapters] = useState<ProjectChapter[]>(chapters);
    useEffect(() => {
        if (chapters.length === 0) {
            fetch(`/${workspaceId}/projects/${projectId}/editor/chapters`)
                .then((res) => res.json())
                .then((data) => {
                    if (data.chapters) {
                        setLoadedChapters(data.chapters);
                    }
                })
                .catch(console.error);
        }
    }, [workspaceId, projectId, chapters]);

    // Persistence - Load on mount only
    const hasLoadedRef = useRef(false);
    useEffect(() => {
        // Only load once on mount, not on every projectId change
        if (hasLoadedRef.current) return;
        
        const saved = localStorage.getItem(`chain_builder_${projectId}`);
        if (saved) {
            try {
                const data = JSON.parse(saved);
                // Load even if nodes array is empty (to restore deletions)
                if (data.nodes !== undefined) {
                    setNodes(data.nodes || []);
                    setEdges(data.edges || []);
                    setPan(data.pan || { x: 0, y: 0 });
                    setZoom(data.zoom || 1);
                }
            } catch (e) {
                console.error('Failed to load graph', e);
            }
        }
        // Always mark as loaded after attempting to load (or if no saved data)
        hasLoadedRef.current = true;
    }, [projectId]);

    // Initialize history with current state on mount
    useEffect(() => {
        if (nodes.length > 0 && historyRef.current.length === 1 && historyRef.current[0].nodes.length === 1 && historyRef.current[0].nodes[0].id === 'root') {
            // Only initialize if we still have the default root node
            const currentState = { nodes: JSON.parse(JSON.stringify(nodes)), edges: JSON.parse(JSON.stringify(edges)) };
            historyRef.current = [currentState];
            historyIndexRef.current = 0;
            setHistory([currentState]);
            setHistoryIndex(0);
        }
    }, []); // Only run once on mount

    // Persistence - Save on every change (debounced would be better but this ensures consistency)
    useEffect(() => {
        // Don't save if we haven't loaded yet (prevents overwriting with default state)
        if (!hasLoadedRef.current) return;
        
        // Save even if nodes array is empty (to persist deletions)
        localStorage.setItem(
            `chain_builder_${projectId}`,
            JSON.stringify({ nodes, edges, pan, zoom })
        );
    }, [nodes, edges, pan, zoom, projectId]);

    // Templates persistence
    useEffect(() => {
        localStorage.setItem(`chain_builder_templates_${projectId}`, JSON.stringify(templates));
    }, [templates, projectId]);

    // Node Operations
    const addNode = useCallback(
        (type: GraphNodeType, initialContent?: string, initialLabel?: string, xOffset?: number, yOffset?: number) => {
            const id = Math.random().toString(36).substr(2, 9);
            const centerX =
                xOffset ??
                (-pan.x + (canvasRef.current?.clientWidth || 800) / 2) / zoom - 150;
            const centerY =
                yOffset ??
                (-pan.y + (canvasRef.current?.clientHeight || 600) / 2) / zoom - 100;

            setNodes((prev) => {
                const newNodes = [
                    ...prev,
                    {
                        id,
                        type,
                        position: { x: centerX, y: centerY },
                        data: {
                            label:
                                initialLabel ||
                                (type === 'prompt'
                                    ? 'New Prompt'
                                    : type === 'context'
                                    ? 'Context Data'
                                    : 'Logic Gate'),
                            content: initialContent || '',
                            status: 'idle',
                        },
                    },
                ];
                saveToHistory(newNodes, edges);
                return newNodes;
            });
        },
        [pan, zoom, edges, saveToHistory]
    );

    const deleteNode = useCallback((id: string) => {
        setNodes((prev) => {
            const newNodes = prev.filter((n) => n.id !== id);
            setEdges((prevEdges) => {
                const newEdges = prevEdges.filter((e) => e.source !== id && e.target !== id);
                saveToHistory(newNodes, newEdges);
                return newEdges;
            });
            setSelectedNodeIds((prev) => prev.filter((sid) => sid !== id));
            return newNodes;
        });
    }, [saveToHistory]);

    const updateNodeData = useCallback((id: string, updates: Partial<GraphNode['data']>) => {
        setNodes((prev) =>
            prev.map((n) => (n.id === id ? { ...n, data: { ...n.data, ...updates } } : n))
        );
    }, []);

    // Viewport Handlers
    const handleWheel = useCallback(
        (e: React.WheelEvent) => {
            if (e.ctrlKey || e.metaKey || e.deltaY !== 0) {
                e.preventDefault();
                if (canvasRef.current) {
                    const rect = canvasRef.current.getBoundingClientRect();
                    const mouseX = e.clientX - rect.left;
                    const mouseY = e.clientY - rect.top;
                    const result = zoomAtPoint(zoom, e.deltaY, mouseX, mouseY, pan);
                    setZoom(result.zoom);
                    setPan(result.pan);
                }
            }
        },
        [zoom, pan]
    );

    const handleMouseDown = useCallback(
        (e: React.MouseEvent) => {
            if (e.button === 1 || (e.button === 0 && e.altKey)) {
                setIsPanning(true);
                setLastMousePan({ x: e.clientX, y: e.clientY });
                return;
            }

            if (e.target === canvasRef.current && !e.shiftKey) {
                setSelectedNodeIds([]);
            }
        },
        []
    );

    const handleMouseMove = useCallback(
        (e: React.MouseEvent) => {
            if (canvasRef.current) {
                const rect = canvasRef.current.getBoundingClientRect();
                setMousePos({
                    x: (e.clientX - rect.left - pan.x) / zoom,
                    y: (e.clientY - rect.top - pan.y) / zoom,
                });
            }

            if (isPanning) {
                const dx = e.clientX - lastMousePan.x;
                const dy = e.clientY - lastMousePan.y;
                setPan((prev) => ({ x: prev.x + dx, y: prev.y + dy }));
                setLastMousePan({ x: e.clientX, y: e.clientY });
            }

            if (draggingNodeId) {
                const dx = e.movementX / zoom;
                const dy = e.movementY / zoom;
                setNodes((prev) =>
                    prev.map((n) => {
                        if (n.id === draggingNodeId) {
                            return {
                                ...n,
                                position: { x: n.position.x + dx, y: n.position.y + dy },
                            };
                        }
                        if (
                            selectedNodeIds.includes(draggingNodeId) &&
                            selectedNodeIds.includes(n.id) &&
                            n.id !== draggingNodeId
                        ) {
                            return {
                                ...n,
                                position: { x: n.position.x + dx, y: n.position.y + dy },
                            };
                        }
                        return n;
                    })
                );
            }
        },
        [isPanning, lastMousePan, draggingNodeId, selectedNodeIds, pan, zoom]
    );

    const handleMouseUp = useCallback(() => {
        setIsPanning(false);
        if (draggingNodeId) {
            // Save to history when node drag ends
            saveToHistory(nodes, edges);
        }
        setDraggingNodeId(null);
        setConnectingNodeId(null);
    }, [draggingNodeId, nodes, edges, saveToHistory]);

    const handleNodeMouseDown = useCallback(
        (e: React.MouseEvent, id: string) => {
            e.stopPropagation();
            setDraggingNodeId(id);

            if (e.shiftKey) {
                setSelectedNodeIds((prev) => {
                    if (prev.includes(id)) return prev.filter((pid) => pid !== id);
                    return [...prev, id];
                });
            } else {
                if (!selectedNodeIds.includes(id)) {
                    setSelectedNodeIds([id]);
                }
            }
        },
        [selectedNodeIds]
    );

    const handleConnectorMouseDown = useCallback((e: React.MouseEvent, id: string) => {
        e.stopPropagation();
        setConnectingNodeId(id);
    }, []);

    const handleConnectorMouseUp = useCallback(
        (e: React.MouseEvent, targetId: string) => {
            e.stopPropagation();
            if (connectingNodeId && connectingNodeId !== targetId) {
                if (!edges.find((edge) => edge.source === connectingNodeId && edge.target === targetId)) {
                    setEdges((prev) => {
                        const newEdges = [
                            ...prev,
                            { id: `${connectingNodeId}-${targetId}`, source: connectingNodeId, target: targetId },
                        ];
                        saveToHistory(nodes, newEdges);
                        return newEdges;
                    });
                }
            }
            setConnectingNodeId(null);
        },
        [connectingNodeId, edges, nodes, saveToHistory]
    );

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
    }, []);

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            const entityData = e.dataTransfer.getData('application/json');
            if (entityData && canvasRef.current) {
                try {
                    const entity = JSON.parse(entityData) as Entity;
                    const rect = canvasRef.current.getBoundingClientRect();
                    const dropX = (e.clientX - rect.left - pan.x) / zoom - 150;
                    const dropY = (e.clientY - rect.top - pan.y) / zoom - 50;

                    const formattedContent = formatEntityForContext(entity);
                    addNode('context', formattedContent, entity.name, dropX, dropY);
                } catch (err) {
                    console.error('Invalid drop data', err);
                }
            }
        },
        [pan, zoom, addNode]
    );

    // Execution
    const executeFlow = useCallback(async () => {
        if (isFlowRunning) return;
        if (detectCycles(nodes, edges)) {
            alert('Cannot run flow: Infinite loop detected! Please check your connections.');
            return;
        }

        setIsFlowRunning(true);
        try {
            const storyContext = getFullStoryContext(loadedChapters);
            const results = await executeFullFlow(
                nodes,
                edges,
                executionMode,
                storyContext,
                aiModel,
                authorProfile,
                settings,
                workspaceId,
                projectId,
                updateNodeData
            );

            if (results.length > 0) {
                const deduplicateSequenceResults = (outputs: string[]) => {
                    const deduped: string[] = [];

                    outputs.forEach((raw, idx) => {
                        let current = (raw || '').trim();
                        if (!current) return;

                        // Compare against prior deduped outputs (most recent first)
                        for (let j = deduped.length - 1; j >= 0; j--) {
                            const previous = deduped[j]?.trim();
                            if (!previous) continue;

                            // If current starts with the full previous text, strip it
                            if (current.startsWith(previous)) {
                                current = current.slice(previous.length).trimStart();
                                break;
                            }

                            // If current contains the tail of previous (e.g., overlap), strip from that point
                            const tailWords = previous.split(/\s+/).filter(Boolean).slice(-30).join(' ');
                            if (tailWords) {
                                const overlapIndex = current.indexOf(tailWords);
                                if (overlapIndex === 0) {
                                    current = current.slice(tailWords.length).trimStart();
                                    break;
                                } else if (overlapIndex > 0) {
                                    // Found overlap in the middle, strip from overlap point
                                    current = current.slice(overlapIndex + tailWords.length).trimStart();
                                    break;
                                }
                            }
                            
                            // Also check if current ends with beginning of previous (reverse overlap)
                            const headWords = previous.split(/\s+/).filter(Boolean).slice(0, 30).join(' ');
                            if (headWords && current.endsWith(headWords)) {
                                current = current.slice(0, -headWords.length).trimEnd();
                                break;
                            }
                        }

                        if (current) {
                            deduped.push(current);
                        }
                    });

                    return deduped;
                };

                const sequenceSafeResults =
                    executionMode === 'sequence'
                        ? (() => {
                              const deduped = deduplicateSequenceResults(results);
                              return deduped.length ? deduped : results;
                          })()
                        : results;

                const resultText = sequenceSafeResults.join('\n\n');
                setGeneratedResult(resultText);
                
                // If callback provided, use it directly (e.g., when embedded in editor)
                // Otherwise show dialog for user to decide
                if (onApplyResult) {
                    onApplyResult(resultText);
                } else {
                    setShowResultDialog(true);
                }
            }
        } catch (error) {
            console.error('Error executing flow:', error);
            alert('Error executing flow: ' + (error instanceof Error ? error.message : 'Unknown error'));
        } finally {
            setIsFlowRunning(false);
        }
    }, [
        isFlowRunning,
        nodes,
        edges,
        executionMode,
        loadedChapters,
        aiModel,
        authorProfile,
        settings,
        workspaceId,
        projectId,
        updateNodeData,
        onApplyResult,
    ]);

    const executeNodeSingle = useCallback(
        async (nodeId: string) => {
            const node = nodes.find((n) => n.id === nodeId);
            if (!node) return;

            updateNodeData(nodeId, { status: 'running' });
            try {
                const outputsMap = new Map<string, string>();
                nodes.forEach((n) => {
                    if (n.type === 'context') {
                        outputsMap.set(n.id, n.data.content);
                    } else if (n.data.output) {
                        outputsMap.set(n.id, n.data.output);
                    }
                });

                const inputs = gatherNodeInputs(nodeId, nodes, edges, outputsMap);
                const storyContext = getFullStoryContext(loadedChapters);

                // Use the executeNode service
                const { executeNode } = await import('./services/chainService');
                const result = await executeNode(
                    {
                        node_prompt: node.data.content,
                        inputs,
                        story_context: storyContext,
                        ai_model: aiModel,
                        author_profile: authorProfile,
                        settings,
                    },
                    workspaceId,
                    projectId
                );

                updateNodeData(nodeId, { status: 'completed', output: result });
            } catch (error) {
                console.error('Node execution failed:', error);
                updateNodeData(nodeId, {
                    status: 'error',
                    errorMessage: error instanceof Error ? error.message : 'Unknown error',
                });
                alert('Node execution failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
            }
        },
        [nodes, edges, loadedChapters, aiModel, authorProfile, settings, workspaceId, projectId, updateNodeData]
    );

    // Auto-Build
    const handleAutoBuildGraph = useCallback(async () => {
        if (!autoBuildPrompt) return;
        setIsBuildingGraph(true);
        try {
            const storyContext = getFullStoryContext(loadedChapters);

            // Fetch entities
            const entitiesResponse = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/records/entities`
            );
            const entitiesData = await entitiesResponse.json();
            const entities = (entitiesData.entities || []).map((e: Entity) => ({
                name: e.name,
                type: e.type,
                properties: e.properties,
            }));

            // Log model selection for debugging
            console.log('Auto-Build: Using AI model', {
                aiModel,
                projectSettings: project.settings?.aiModel,
                settingsProp: settings?.aiModel,
            });

            const layout = await generateGraphLayout(
                {
                    user_goal: autoBuildPrompt,
                    story_context: storyContext,
                    entities,
                    mode: autoBuildMode,
                    ai_model: aiModel, // This should be the model from props
                },
                workspaceId,
                projectId
            );

            if (layout.nodes.length > 0) {
                setNodes(layout.nodes);
                setEdges(
                    layout.edges.map((e) => ({
                        id: `${e.source}-${e.target}`,
                        source: e.source,
                        target: e.target,
                    }))
                );
                setExecutionMode(autoBuildMode);
                setIsAutoBuildOpen(false);
                setAutoBuildPrompt('');
            }
        } catch (error) {
            console.error('Failed to build graph:', error);
            alert('Failed to build graph: ' + (error instanceof Error ? error.message : 'Unknown error'));
        } finally {
            setIsBuildingGraph(false);
        }
    }, [
        autoBuildPrompt,
        autoBuildMode,
        loadedChapters,
        aiModel,
        workspaceId,
        projectId,
    ]);

    // Refiner
    const handleRefineGraph = useCallback(async () => {
        if (!refinerPrompt || selectedNodeIds.length === 0) return;
        setIsRefiningGraph(true);

        try {
            const selectedNodes = nodes.filter((n) => selectedNodeIds.includes(n.id));
            const internalEdges = edges.filter(
                (e) => selectedNodeIds.includes(e.source) && selectedNodeIds.includes(e.target)
            );

            const incomingEdges = edges.filter(
                (e) => !selectedNodeIds.includes(e.source) && selectedNodeIds.includes(e.target)
            );
            const outgoingEdges = edges.filter(
                (e) => selectedNodeIds.includes(e.source) && !selectedNodeIds.includes(e.target)
            );

            const storyContext = getFullStoryContext(loadedChapters);

            const refinedSubgraph = await refineSelection(
                {
                    selected_nodes: selectedNodes,
                    selected_edges: internalEdges.map((e) => ({
                        source: e.source,
                        target: e.target,
                    })),
                    instruction: refinerPrompt,
                    story_context: storyContext,
                    ai_model: aiModel,
                },
                workspaceId,
                projectId
            );

            if (refinedSubgraph.nodes && refinedSubgraph.nodes.length > 0) {
                const remainingNodes = nodes.filter((n) => !selectedNodeIds.includes(n.id));
                const remainingEdges = edges.filter(
                    (e) => !selectedNodeIds.includes(e.source) && !selectedNodeIds.includes(e.target)
                );

                const newNodes = refinedSubgraph.nodes;
                const newInternalEdges = refinedSubgraph.edges || [];

                const sortedNewNodes = [...newNodes].sort((a, b) => a.position.y - b.position.y);
                const firstNewNode = sortedNewNodes[0];
                const lastNewNode = sortedNewNodes[sortedNewNodes.length - 1];

                const reconnectedEdges = [
                    ...remainingEdges,
                    ...newInternalEdges.map((e) => ({
                        id: `${e.source}-${e.target}`,
                        source: e.source,
                        target: e.target,
                    })),
                    ...incomingEdges.map((e) => ({ ...e, target: firstNewNode.id })),
                    ...outgoingEdges.map((e) => ({ ...e, source: lastNewNode.id })),
                ];

                setNodes([...remainingNodes, ...newNodes]);
                setEdges(reconnectedEdges);
                setSelectedNodeIds([]);
                setIsRefinerOpen(false);
                setRefinerPrompt('');
            }
        } catch (error) {
            console.error('Failed to refine selection:', error);
            alert('Failed to refine selection: ' + (error instanceof Error ? error.message : 'Unknown error'));
        } finally {
            setIsRefiningGraph(false);
        }
    }, [refinerPrompt, selectedNodeIds, nodes, edges, loadedChapters, aiModel, workspaceId, projectId]);

    // Magic Wand
    const handleWandGenerate = useCallback(async () => {
        if (!wandNodeId) return;
        
        // Get the node to determine its type
        const wandNode = nodes.find((n) => n.id === wandNodeId);
        if (!wandNode) return;
        
        const hasExistingContent = wandNode.data.content && wandNode.data.content.trim().length > 0;
        
        // If node has content, enhance it. If empty, create prompt from seed.
        if (hasExistingContent) {
            // Enhance existing content
            if (!wandSeed.trim()) {
                alert('Please enter enhancement instructions or leave empty to enhance automatically');
                return;
            }
            
            setIsWandGenerating(true);
            
            try {
                const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
                const response = await fetch(
                    `/${workspaceId}/projects/${projectId}/editor/enhance-text`,
                    {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                            'X-CSRF-TOKEN': csrfToken,
                        },
                        body: JSON.stringify({
                            text: wandNode.data.content.trim(),
                            enhancement_mode: wandSeed.trim() ? 'custom_instruction' : 'story_text',
                            model: aiModel,
                        }),
                    }
                );
                
                if (!response.ok) {
                    const error = await response.json().catch(() => ({ error: 'Unknown error' }));
                    throw new Error(error.error || `HTTP ${response.status}`);
                }
                
                const data = await response.json();
                if (data.success && data.enhanced_text) {
                    updateNodeData(wandNodeId, { content: data.enhanced_text.trim() });
                    setWandNodeId(null);
                    setWandSeed('');
                } else {
                    throw new Error('No enhanced text returned');
                }
            } catch (error) {
                console.error('Failed to enhance instruction:', error);
                const errorMessage = error instanceof Error ? error.message : 'Unknown error';
                alert(`Failed to enhance instruction: ${errorMessage}`);
            } finally {
                setIsWandGenerating(false);
            }
        } else {
            // Create new prompt from seed
            if (!wandSeed.trim()) {
                alert('Please enter a description of what you want to write');
                return;
            }
            
            setIsWandGenerating(true);

            try {
                const outputsMap = new Map<string, string>();
                nodes.filter((n) => n.type === 'context').forEach((n) => outputsMap.set(n.id, n.data.content));

                const inputs = gatherNodeInputs(wandNodeId, nodes, edges, outputsMap);
                const storyContext = getFullStoryContext(loadedChapters);

                const instruction = await generateInstruction(
                    {
                        seed: wandSeed.trim(),
                        inputs,
                        story_context: storyContext,
                        ai_model: aiModel,
                        node_type: wandNode.type === 'logic' ? 'logic' : 'prompt', // Pass node type to backend
                    },
                    workspaceId,
                    projectId
                );

                if (instruction && instruction.trim()) {
                    updateNodeData(wandNodeId, { content: instruction.trim() });
                    setWandNodeId(null);
                    setWandSeed('');
                } else {
                    throw new Error('Empty instruction returned');
                }
            } catch (error) {
                console.error('Failed to generate instruction:', error);
                const errorMessage = error instanceof Error ? error.message : 'Unknown error';
                alert(`Failed to auto-generate instruction: ${errorMessage}`);
            } finally {
                setIsWandGenerating(false);
            }
        }
    }, [wandNodeId, wandSeed, nodes, edges, loadedChapters, aiModel, workspaceId, projectId, updateNodeData]);

    // Inspector
    const getInspectionData = useCallback(() => {
        if (!inspectedNodeId) return null;
        const node = nodes.find((n) => n.id === inspectedNodeId);
        if (!node) return null;

        const outputsMap = new Map<string, string>();
        nodes.forEach((n) => outputsMap.set(n.id, n.data.output || ''));
        const inputs = gatherNodeInputs(inspectedNodeId, nodes, edges, outputsMap);

        const inputsText = inputs
            .map((input) => {
                const typeLabel =
                    input.type === 'context' ? 'BACKGROUND DATA' : 'PREVIOUS STEP OUTPUT';
                return `--- ${typeLabel} (${input.label}) ---\n${input.text}\n-------------------`;
            })
            .join('\n\n');

        const storyContext = getFullStoryContext(loadedChapters);
        return {
            nodeLabel: node.data.label,
            nodeInstruction: node.data.content,
            inputsText,
            storyPreview: storyContext.slice(-500) + '...',
        };
    }, [inspectedNodeId, nodes, edges, loadedChapters]);

    const inspectionData = getInspectionData();

    // Template handlers
    const handleSaveTemplate = useCallback(() => {
        if (!templateName.trim()) {
            alert('Please enter a template name');
            return;
        }

        const newTemplate: GraphTemplate = {
            id: editingTemplateId || Date.now().toString(),
            name: templateName.trim(),
            nodes: JSON.parse(JSON.stringify(nodes)),
            edges: JSON.parse(JSON.stringify(edges)),
            projectId,
            createdAt: editingTemplateId 
                ? templates.find(t => t.id === editingTemplateId)?.createdAt 
                : new Date().toISOString(),
        };

        if (editingTemplateId) {
            // Update existing template
            setTemplates(prev => prev.map(t => t.id === editingTemplateId ? newTemplate : t));
        } else {
            // Add new template
            setTemplates(prev => [...prev, newTemplate]);
        }

        setTemplateName('');
        setEditingTemplateId(null);
    }, [templateName, nodes, edges, projectId, editingTemplateId, templates]);

    const handleLoadTemplate = useCallback((template: GraphTemplate) => {
        if (confirm('Load this template? Current graph will be overwritten.')) {
            setNodes(JSON.parse(JSON.stringify(template.nodes)));
            setEdges(JSON.parse(JSON.stringify(template.edges)));
            setIsTemplatesOpen(false);
            saveToHistory(template.nodes, template.edges);
        }
    }, [saveToHistory]);

    const handleDeleteTemplate = useCallback((templateId: string) => {
        if (confirm('Delete this template?')) {
            setTemplates(prev => prev.filter(t => t.id !== templateId));
        }
    }, []);

    const handleEditTemplate = useCallback((template: GraphTemplate) => {
        if (confirm('Load this template for editing? Current graph will be overwritten.')) {
            setNodes(JSON.parse(JSON.stringify(template.nodes)));
            setEdges(JSON.parse(JSON.stringify(template.edges)));
            setEditingTemplateId(template.id);
            setTemplateName(template.name);
            saveToHistory(template.nodes, template.edges);
        }
    }, [saveToHistory]);

    const handleStartNewTemplate = useCallback(() => {
        setEditingTemplateId(null);
        setTemplateName('');
    }, []);

    return (
        <div className="flex flex-col w-full h-full bg-gray-50 overflow-hidden" style={{ minHeight: 'calc(100vh - 4rem)' }}>
            {/* Toolbar - Full Width Below Main Nav */}
            <div className="w-full bg-white border-b border-gray-300 px-4 py-3 flex items-center justify-between shadow-sm z-50">
                <div className="flex items-center gap-3">
                    <Button variant="outline" size="sm" onClick={() => addNode('prompt')} title="Add Prompt Node">
                        <Box className="w-4 h-4 mr-2 text-blue-600" /> Prompt
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => addNode('context')} title="Add Context Node">
                        <Type className="w-4 h-4 mr-2 text-green-600" /> Context
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => addNode('logic')} title="Add Logic Node">
                        <Wand2 className="w-4 h-4 mr-2 text-purple-600" /> Logic
                    </Button>
                    <div className="w-px h-6 bg-gray-300 mx-2" />
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setIsAutoBuildOpen(true)}
                        title="Auto-Build Graph"
                    >
                        <Sparkles className="w-4 h-4 mr-2 text-pink-600" /> Auto-Build
                    </Button>
                    {selectedNodeIds.length > 0 && (
                        <>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={deleteSelectedNodes}
                                title="Delete selected nodes"
                                className="text-red-600 hover:text-red-700 hover:bg-red-50 border-red-300"
                            >
                                <Trash2 className="w-4 h-4 mr-2" /> Delete ({selectedNodeIds.length})
                            </Button>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setIsRefinerOpen(true)}
                                title="Enhance selected nodes"
                            >
                                <Wand2 className="w-4 h-4 mr-2" /> Refine ({selectedNodeIds.length})
                            </Button>
                        </>
                    )}
                    <div className="w-px h-6 bg-gray-300 mx-2" />
                    <div className="flex bg-gray-100 rounded-lg p-0.5 border border-gray-300">
                        <button
                            onClick={() => setExecutionMode('final-only')}
                            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all flex items-center gap-2 ${
                                executionMode === 'final-only'
                                    ? 'bg-white text-gray-900 shadow-sm'
                                    : 'text-gray-600 hover:text-gray-900'
                            }`}
                        >
                            <ArrowRightToLine className="w-3 h-3" /> Final Only
                        </button>
                        <button
                            onClick={() => setExecutionMode('sequence')}
                            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all flex items-center gap-2 ${
                                executionMode === 'sequence'
                                    ? 'bg-white text-gray-900 shadow-sm'
                                    : 'text-gray-600 hover:text-gray-900'
                            }`}
                        >
                            <Layers className="w-3 h-3" /> Sequence
                        </button>
                    </div>
                    <div className="w-px h-6 bg-gray-300 mx-2" />
                    <Button
                        onClick={executeFlow}
                        disabled={isFlowRunning}
                        className="bg-green-600 hover:bg-green-700 text-white"
                    >
                        {isFlowRunning ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin mr-2" /> Running...
                            </>
                        ) : (
                            <>
                                <Zap className="w-4 h-4 mr-2" />
                                {executionMode === 'final-only' ? 'Run & Write Final' : 'Run & Write All'}
                            </>
                        )}
                    </Button>
                </div>
            </div>

            {/* Main Content Area - Records + Canvas + Templates */}
            <div className="flex flex-1 min-h-0 overflow-hidden">
                {/* Records Drawer - Full Height Left */}
                <RecordsDrawer
                    workspaceId={workspaceId}
                    projectId={projectId}
                    onEntityDrop={(entity, position) => {
                        const formattedContent = formatEntityForContext(entity);
                        addNode('context', formattedContent, entity.name, position.x, position.y);
                    }}
                />

                {/* Canvas - Takes Remaining Space */}
                <div
                    ref={canvasRef}
                    className="flex-1 cursor-grab active:cursor-grabbing overflow-hidden relative bg-gray-50"
                    onMouseDown={handleMouseDown}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
                    onWheel={handleWheel}
                    onDragOver={handleDragOver}
                    onDrop={handleDrop}
                >
                {/* Grid Background */}
                <div
                    className="absolute inset-0 pointer-events-none opacity-20"
                    style={{
                        backgroundImage: 'radial-gradient(circle, #9ca3af 1px, transparent 1px)',
                        backgroundSize: `${20 * zoom}px ${20 * zoom}px`,
                        backgroundPosition: `${pan.x}px ${pan.y}px`,
                    }}
                />

                {/* SVG for Edges */}
                <svg
                    ref={svgRef}
                    className="overflow-visible absolute inset-0 w-full h-full pointer-events-none"
                >
                    <defs>
                        <marker
                            id="arrowhead"
                            markerWidth="10"
                            markerHeight="7"
                            refX="10"
                            refY="3.5"
                            orient="auto"
                        >
                            <polygon points="0 0, 10 3.5, 0 7" fill="#6b7280" />
                        </marker>
                    </defs>
                    {edges.map((edge) => {
                        const sourceNode = nodes.find((n) => n.id === edge.source);
                        const targetNode = nodes.find((n) => n.id === edge.target);
                        const isSelected =
                            selectedNodeIds.includes(edge.source) &&
                            selectedNodeIds.includes(edge.target);
                        return (
                            <Edge
                                key={edge.id}
                                edge={edge}
                                sourceNode={sourceNode}
                                targetNode={targetNode}
                                isSelected={isSelected}
                                pan={pan}
                                zoom={zoom}
                            />
                        );
                    })}
                    {connectingNodeId && (
                        <ConnectingLine
                            sourceX={
                                (nodes.find((n) => n.id === connectingNodeId)?.position.x || 0) + 300
                            }
                            sourceY={
                                (nodes.find((n) => n.id === connectingNodeId)?.position.y || 0) + 50
                            }
                            targetX={mousePos.x}
                            targetY={mousePos.y}
                            pan={pan}
                            zoom={zoom}
                        />
                    )}
                </svg>

                {/* Nodes Container */}
                <div
                    style={{
                        transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                        transformOrigin: '0 0',
                    }}
                    className="w-full h-full absolute inset-0"
                >
                    {nodes.map((node) => (
                        <Node
                            key={node.id}
                            node={node}
                            isSelected={selectedNodeIds.includes(node.id)}
                            onSelect={(e) => handleNodeMouseDown(e, node.id)}
                            onDragStart={(e) => handleConnectorMouseDown(e, node.id)}
                            onConnectorMouseUp={(e) => handleConnectorMouseUp(e, node.id)}
                            onUpdate={(updates) => updateNodeData(node.id, updates)}
                            onDelete={() => deleteNode(node.id)}
                            onExecute={() => executeNodeSingle(node.id)}
                            onInspect={() => setInspectedNodeId(node.id)}
                            onApplyResult={onApplyResult}
                            onMagicWand={(currentContent) => {
                                setWandNodeId(node.id);
                                setWandSeed(currentContent || '');
                            }}
                            workspaceId={workspaceId}
                            projectId={projectId}
                            aiModel={aiModel}
                        />
                    ))}
                    </div>
                </div>

                {/* Undo/Redo & Zoom Controls */}
                <div className="absolute bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-auto">
                    {/* Undo/Redo Controls */}
                    <div className="bg-white p-1.5 rounded-lg border border-gray-300 shadow-lg flex flex-row gap-1">
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={undo}
                            disabled={historyIndexRef.current === 0}
                            title="Undo (Ctrl+Z)"
                        >
                            <Undo2 className="w-4 h-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={redo}
                            disabled={historyIndexRef.current >= historyRef.current.length - 1}
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
                            onClick={() => setZoom(Math.min(zoom + 0.1, 3))}
                        >
                            <ZoomIn className="w-4 h-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => setZoom(Math.max(zoom - 0.1, 0.2))}
                        >
                            <ZoomOut className="w-4 h-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => {
                                setZoom(1);
                                setPan({ x: 0, y: 0 });
                            }}
                        >
                            <Maximize className="w-4 h-4" />
                        </Button>
                        <div className="text-[9px] text-center text-gray-500 border-t border-gray-300 pt-1 mt-1">
                            {Math.round(zoom * 100)}%
                        </div>
                    </div>
                </div>

                {/* Templates Sidebar - Right Side (Collapsible) */}
                <div className="relative flex items-center h-full">
                    {/* Toggle Button - Always visible on right edge when collapsed */}
                    {!isTemplatesOpen && (
                    <button
                        onClick={() => setIsTemplatesOpen(true)}
                        className="absolute right-0 top-1/2 -translate-y-1/2 z-50 bg-white border-l border-t border-b border-gray-300 rounded-l-lg px-3 py-8 shadow-md hover:bg-gray-50 transition-colors flex items-center justify-center"
                        title="Open Templates"
                    >
                        <FileText className="w-5 h-5 text-gray-600" />
                    </button>
                )}

                {/* Templates Panel */}
                <div
                    className={`h-full bg-white border-l border-gray-300 flex flex-col shadow-lg transition-all duration-300 ${
                        isTemplatesOpen ? 'w-80' : 'w-0 overflow-hidden'
                    }`}
                >
                    {isTemplatesOpen && (
                        <>
                            <div className="p-4 border-b border-gray-300 flex items-center justify-between">
                                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                                    <FileText className="w-4 h-4" /> Templates
                                </h2>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-8 w-8"
                                    onClick={() => setIsTemplatesOpen(false)}
                                    title="Close Templates"
                                >
                                    <X className="w-4 h-4" />
                                </Button>
                            </div>
                            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                                {/* Save Template Form */}
                                <div className="space-y-2 pb-4 border-b border-gray-200">
                                    <label className="text-sm font-medium text-gray-700">
                                        {editingTemplateId ? 'Edit Template' : 'Save Current Graph as Template'}
                                    </label>
                                    <div className="flex gap-2">
                                        <Input
                                            value={templateName}
                                            onChange={(e) => setTemplateName(e.target.value)}
                                            placeholder="Template name..."
                                            className="flex-1"
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter') {
                                                    handleSaveTemplate();
                                                }
                                            }}
                                        />
                                        <Button
                                            onClick={handleSaveTemplate}
                                            disabled={!templateName.trim()}
                                            size="sm"
                                            className="bg-blue-600 hover:bg-blue-700"
                                        >
                                            <Save className="w-4 h-4" />
                                        </Button>
                                        {editingTemplateId && (
                                            <Button
                                                onClick={handleStartNewTemplate}
                                                variant="outline"
                                                size="sm"
                                            >
                                                Cancel
                                            </Button>
                                        )}
                                    </div>
                                </div>

                                {/* Templates List */}
                                <div className="space-y-2">
                                    <h3 className="text-sm font-semibold text-gray-700">Saved Templates</h3>
                                    {templates.length === 0 ? (
                                        <p className="text-sm text-gray-500 italic">No templates saved yet</p>
                                    ) : (
                                        <div className="space-y-2">
                                            {templates.map((template) => (
                                                <div
                                                    key={template.id}
                                                    className="border border-gray-200 rounded-lg p-3 hover:bg-gray-50 transition-colors"
                                                >
                                                    <div className="flex items-start justify-between mb-2">
                                                        <h4 className="text-sm font-medium text-gray-900 flex-1">
                                                            {template.name}
                                                        </h4>
                                                        <div className="flex gap-1">
                                                            <Button
                                                                variant="ghost"
                                                                size="icon"
                                                                className="h-6 w-6"
                                                                onClick={() => handleEditTemplate(template)}
                                                                title="Edit"
                                                            >
                                                                <Save className="w-3 h-3" />
                                                            </Button>
                                                            <Button
                                                                variant="ghost"
                                                                size="icon"
                                                                className="h-6 w-6 text-red-600 hover:text-red-700"
                                                                onClick={() => handleDeleteTemplate(template.id)}
                                                                title="Delete"
                                                            >
                                                                <Trash2 className="w-3 h-3" />
                                                            </Button>
                                                        </div>
                                                    </div>
                                                    <div className="text-xs text-gray-500 mb-2">
                                                        {template.nodes.length} node{template.nodes.length !== 1 ? 's' : ''}, {template.edges.length} edge{template.edges.length !== 1 ? 's' : ''}
                                                    </div>
                                                    <Button
                                                        onClick={() => handleLoadTemplate(template)}
                                                        size="sm"
                                                        variant="outline"
                                                        className="w-full"
                                                    >
                                                        <FolderOpen className="w-3 h-3 mr-2" />
                                                        Load
                                                    </Button>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>

            {/* Modals */}
            {/* Auto-Build Modal */}
            <Dialog open={isAutoBuildOpen} onOpenChange={setIsAutoBuildOpen}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Sparkles className="w-5 h-5 text-pink-600" /> Auto-Build Workflow
                        </DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                        <p className="text-sm text-gray-600">
                            Describe the flow you want. The AI will generate nodes, connections, and instructions
                            automatically, using your Records context.
                        </p>
                        <div className="flex gap-2 bg-gray-100 p-1 rounded-lg">
                            <button
                                onClick={() => setAutoBuildMode('sequence')}
                                className={`flex-1 py-2 text-xs rounded-md transition-colors ${
                                    autoBuildMode === 'sequence'
                                        ? 'bg-white text-gray-900 shadow-sm'
                                        : 'text-gray-600 hover:text-gray-900'
                                }`}
                            >
                                Sequence (Scene A → Scene B)
                            </button>
                            <button
                                onClick={() => setAutoBuildMode('final-only')}
                                className={`flex-1 py-2 text-xs rounded-md transition-colors ${
                                    autoBuildMode === 'final-only'
                                        ? 'bg-white text-gray-900 shadow-sm'
                                        : 'text-gray-600 hover:text-gray-900'
                                }`}
                            >
                                Final Only (Context → Final)
                            </button>
                        </div>
                        <div className="relative">
                            <Textarea
                                value={autoBuildPrompt}
                                onChange={(e) => setAutoBuildPrompt(e.target.value)}
                                placeholder="e.g. A scene where Vex investigates the derelict ship and gets ambushed..."
                                className="min-h-32 max-h-96 overflow-y-auto overflow-x-hidden pr-12 resize-none break-all whitespace-pre-wrap"
                            />
                            <div className="absolute top-2 right-2">
                                <AutoBuildMagicWand
                                    text={autoBuildPrompt}
                                    onEnhanced={(enhanced) => setAutoBuildPrompt(enhanced)}
                                    storyContext={getFullStoryContext(loadedChapters)}
                                    workspaceId={workspaceId}
                                    projectId={projectId}
                                    aiModel={aiModel}
                                    disabled={isBuildingGraph}
                                />
                            </div>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setIsAutoBuildOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            onClick={handleAutoBuildGraph}
                            disabled={!autoBuildPrompt || isBuildingGraph}
                            className="bg-pink-600 hover:bg-pink-700"
                        >
                            {isBuildingGraph ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin mr-2" /> Building...
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

            {/* Magic Wand Modal */}
            <Dialog open={!!wandNodeId} onOpenChange={() => setWandNodeId(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Sparkles className="w-5 h-5 text-purple-600" /> Magic Prompt Writer
                        </DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                        <p className="text-sm text-gray-600">
                            Describe your goal for this step. The AI will read the connected inputs and write a
                            detailed instruction for you.
                        </p>
                        <Textarea
                            value={wandSeed}
                            onChange={(e) => setWandSeed(e.target.value)}
                            placeholder="e.g. A tense dialogue where they discuss the artifact..."
                            className="min-h-32"
                        />
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setWandNodeId(null)}>
                            Cancel
                        </Button>
                        <Button
                            onClick={handleWandGenerate}
                            disabled={!wandSeed.trim() || isWandGenerating}
                            className="bg-purple-600 hover:bg-purple-700"
                        >
                            {isWandGenerating ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin mr-2" /> Generating...
                                </>
                            ) : (
                                <>
                                    <Wand2 className="w-4 h-4 mr-2" /> Generate Instruction
                                </>
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Refiner Modal */}
            <Dialog open={isRefinerOpen} onOpenChange={setIsRefinerOpen}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Wand2 className="w-5 h-5 text-purple-600" /> Refine Selection
                        </DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                        <p className="text-sm text-gray-600">
                            How should the AI modify the {selectedNodeIds.length} selected nodes? It can split them,
                            merge them, or add logic checks.
                        </p>
                        <Textarea
                            value={refinerPrompt}
                            onChange={(e) => setRefinerPrompt(e.target.value)}
                            placeholder="e.g. Break this interaction into 3 beats and add a tension check in the middle..."
                            className="min-h-32"
                        />
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setIsRefinerOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            onClick={handleRefineGraph}
                            disabled={!refinerPrompt || isRefiningGraph}
                            className="bg-purple-600 hover:bg-purple-700"
                        >
                            {isRefiningGraph ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin mr-2" /> Refining...
                                </>
                            ) : (
                                <>
                                    <Sparkles className="w-4 h-4 mr-2" /> Enhance Flow
                                </>
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Inspector Modal */}
            {inspectionData && (
                <Dialog open={!!inspectedNodeId} onOpenChange={() => setInspectedNodeId(null)}>
                    <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
                        <DialogHeader>
                            <DialogTitle className="flex items-center gap-2">
                                <Eye className="w-5 h-5 text-blue-600" /> Node Inspector:{' '}
                                <span className="text-blue-600">{inspectionData.nodeLabel}</span>
                            </DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-xs font-bold text-gray-600 uppercase">
                                        Compiled Inputs (What AI Sees)
                                    </label>
                                    <div className="bg-gray-100 p-3 rounded border border-gray-300 text-xs text-gray-700 font-mono h-64 overflow-y-auto whitespace-pre-wrap">
                                        {inspectionData.inputsText || 'No inputs connected.'}
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-bold text-gray-600 uppercase">
                                        Global Story Context (Last 500 chars)
                                    </label>
                                    <div className="bg-gray-100 p-3 rounded border border-gray-300 text-xs text-gray-600 italic h-64 overflow-y-auto">
                                        "{inspectionData.storyPreview}"
                                    </div>
                                </div>
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs font-bold text-gray-600 uppercase">Node Instruction</label>
                                <div className="bg-blue-50 p-3 rounded border border-blue-200 text-sm text-gray-800">
                                    {inspectionData.nodeInstruction}
                                </div>
                            </div>
                        </div>
                    </DialogContent>
                </Dialog>
            )}

            {/* Result Dialog - Apply to Editor */}
            <Dialog open={showResultDialog} onOpenChange={setShowResultDialog}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Zap className="w-5 h-5 text-green-600" /> Generation Complete!
                        </DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                        <p className="text-sm text-gray-600">
                            Your graph has been executed successfully. What would you like to do with the generated text?
                        </p>
                        <div className="bg-gray-50 p-3 rounded border border-gray-200 max-h-48 overflow-y-auto">
                            <p className="text-xs text-gray-500 mb-2 font-semibold">Preview:</p>
                            <p className="text-sm text-gray-700 whitespace-pre-wrap line-clamp-6">
                                {generatedResult?.substring(0, 300)}
                                {generatedResult && generatedResult.length > 300 ? '...' : ''}
                            </p>
                        </div>
                    </div>
                    <DialogFooter className="flex gap-2">
                        <Button
                            variant="outline"
                            onClick={() => {
                                setShowResultDialog(false);
                                setGeneratedResult(null);
                            }}
                        >
                            Stay Here
                        </Button>
                        <Button
                            onClick={() => {
                                // Store result in localStorage for editor to pick up
                                if (generatedResult) {
                                    localStorage.setItem(`chainbuilder_result_${projectId}`, generatedResult);
                                    localStorage.setItem(`chainbuilder_result_timestamp_${projectId}`, Date.now().toString());
                                }
                                
                                // Navigate to editor
                                router.visit(`/${workspaceId}/projects/${projectId}/editor`);
                            }}
                            className="bg-green-600 hover:bg-green-700"
                        >
                            <ArrowRight className="w-4 h-4 mr-2" />
                            Apply to Editor
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
};


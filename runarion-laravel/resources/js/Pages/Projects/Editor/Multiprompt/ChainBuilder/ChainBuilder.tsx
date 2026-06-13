import React, { useState, useRef, useEffect, useCallback } from "react";
import {
    GraphNode,
    GraphEdge,
    GraphNodeType,
    GraphExecutionMode,
    Entity,
    ProjectChapter,
    GraphTemplate,
    NodeStatus,
} from "./types";
import { Node } from "./Components/Node";
import { Edge, ConnectingLine } from "./Components/Edge";
import { RecordsDrawer } from "./Components/RecordsDrawer";
import { Toolbar } from "./Components/Toolbar";
import { CanvasControls } from "./Components/CanvasControls";
import { TemplatesSidebar } from "./Components/TemplatesSidebar";
import {
    AutoBuildDialog,
    MagicWandDialog,
    RefinerDialog,
    InspectorDialog,
    ResultDialog,
} from "./Components/Dialogs";
import { detectCycles } from "./Utils/graphHelpers";
import { zoomAtPoint, fitViewToNodes } from "./Utils/viewportHelpers";
import { getFullStoryContext } from "./Utils/storyContext";
import { formatEntityForContext } from "./Utils/formatEntityForContext";
import { executeFullFlow, gatherNodeInputs } from "./Services/graphExecution";
import {
    executeNode,
    generateGraphLayout,
    generateInstruction,
    refineSelection,
} from "./Services/chainService";
import { router } from "@inertiajs/react";
import { http } from "@/Lib/http";
import { toast } from "sonner";
import { useConfirm } from "@/Components/ConfirmDialogProvider";

interface ChainBuilderProps {
    workspaceId: string;
    projectId: string;
    project: any;
    chapters?: ProjectChapter[];
    persistedGraphState?: {
        nodes?: GraphNode[];
        edges?: GraphEdge[];
        pan?: { x: number; y: number };
        zoom?: number;
        execution_mode?: GraphExecutionMode;
    } | null;
    persistedTemplates?: GraphTemplate[];
    aiModel?: string;
    authorProfile?: string;
    settings?: Record<string, any>;
    onApplyResult?: (text: string) => void;
    onLoadingChange?: (isLoading: boolean) => void;
}

export const ChainBuilder: React.FC<ChainBuilderProps> = ({
    workspaceId,
    projectId,
    project,
    chapters = [],
    persistedGraphState = null,
    persistedTemplates = [],
    aiModel = "gemini-2.5-flash",
    authorProfile,
    settings,
    onApplyResult,
    onLoadingChange,
}) => {
    const confirm = useConfirm();
    // Graph State - Combined for atomic updates (fixes edge selectability after auto-build)
    interface GraphState {
        nodes: GraphNode[];
        edges: GraphEdge[];
    }

    const initialGraphState: GraphState = {
        nodes: [
            {
                id: "root",
                type: "prompt",
                position: { x: 300, y: 100 },
                data: {
                    label: "Start Prompt",
                    content: "Describe the setting...",
                    status: "idle",
                },
            },
        ],
        edges: [],
    };

    const [graphState, setGraphState] = useState<GraphState>(initialGraphState);

    // Destructure for convenience (read-only references)
    const { nodes, edges } = graphState;

    // Helper functions for common state updates
    const setNodes = useCallback(
        (updater: GraphNode[] | ((prev: GraphNode[]) => GraphNode[])) => {
            setGraphState((prev) => ({
                ...prev,
                nodes:
                    typeof updater === "function"
                        ? updater(prev.nodes)
                        : updater,
            }));
        },
        [],
    );

    const setEdges = useCallback(
        (updater: GraphEdge[] | ((prev: GraphEdge[]) => GraphEdge[])) => {
            setGraphState((prev) => ({
                ...prev,
                edges:
                    typeof updater === "function"
                        ? updater(prev.edges)
                        : updater,
            }));
        },
        [],
    );

    // Interaction State
    const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);
    const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
    const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
    const [connectingNodeId, setConnectingNodeId] = useState<string | null>(
        null,
    );
    const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

    // Z-order state for bringing nodes to front
    const [nodeZOrder, setNodeZOrder] = useState<Map<string, number>>(
        new Map(),
    );
    const zOrderCounterRef = useRef(0);

    // Node heights state for dynamic edge positioning
    const [nodeHeights, setNodeHeights] = useState<Map<string, number>>(
        new Map(),
    );

    // Viewport State
    const [pan, setPan] = useState({ x: 0, y: 0 });
    const [zoom, setZoom] = useState(1);
    const [isPanning, setIsPanning] = useState(false);
    const [lastMousePan, setLastMousePan] = useState({ x: 0, y: 0 });

    // Execution & Settings State
    const [isFlowRunning, setIsFlowRunning] = useState(false);
    const [executionMode, setExecutionMode] =
        useState<GraphExecutionMode>("final-only");

    // Modals State
    const [isAutoBuildOpen, setIsAutoBuildOpen] = useState(false);
    const [autoBuildPrompt, setAutoBuildPrompt] = useState("");
    const [isBuildingGraph, setIsBuildingGraph] = useState(false);
    const [autoBuildMode, setAutoBuildMode] =
        useState<GraphExecutionMode>("sequence");

    const [isRefinerOpen, setIsRefinerOpen] = useState(false);
    const [refinerPrompt, setRefinerPrompt] = useState("");
    const [isRefiningGraph, setIsRefiningGraph] = useState(false);

    const [inspectedNodeId, setInspectedNodeId] = useState<string | null>(null);

    const [wandNodeId, setWandNodeId] = useState<string | null>(null);
    const [wandSeed, setWandSeed] = useState("");
    const [isWandGenerating, setIsWandGenerating] = useState(false);

    // Templates State - collapsed by default
    const [isTemplatesOpen, setIsTemplatesOpen] = useState(false);
    const [templates, setTemplates] = useState<GraphTemplate[]>(() => {
        if (persistedTemplates.length > 0) {
            return persistedTemplates;
        }
        const saved = localStorage.getItem(
            `chain_builder_templates_${projectId}`,
        );
        return saved ? JSON.parse(saved) : [];
    });
    const [editingTemplateId, setEditingTemplateId] = useState<string | null>(
        null,
    );
    const [templateName, setTemplateName] = useState("");

    // Result state for navigation
    const [generatedResult, setGeneratedResult] = useState<string | null>(null);
    const [showResultDialog, setShowResultDialog] = useState(false);

    // Loading indicator state for localStorage saves
    const [isSavingLocal, setIsSavingLocal] = useState(false);
    const saveDebounceRef = useRef<NodeJS.Timeout | null>(null);

    const canvasRef = useRef<HTMLDivElement>(null);
    const svgRef = useRef<SVGSVGElement>(null);

    // Undo/Redo History (refs are source of truth)
    const historyRef = useRef<Array<GraphState>>([initialGraphState]);
    const historyIndexRef = useRef(0);

    // Save state to history
    const saveToHistory = useCallback(
        (newNodes: GraphNode[], newEdges: GraphEdge[]) => {
            const currentState = {
                nodes: JSON.parse(JSON.stringify(newNodes)),
                edges: JSON.parse(JSON.stringify(newEdges)),
            };
            const newHistory = historyRef.current.slice(
                0,
                historyIndexRef.current + 1,
            );
            newHistory.push(currentState);
            // Limit history to 50 states
            if (newHistory.length > 50) {
                newHistory.shift();
            } else {
                historyIndexRef.current = newHistory.length - 1;
            }
            historyRef.current = newHistory;
        },
        [],
    );

    // Undo function
    const undo = useCallback(() => {
        if (historyIndexRef.current > 0) {
            historyIndexRef.current -= 1;
            const state = historyRef.current[historyIndexRef.current];
            setGraphState(JSON.parse(JSON.stringify(state)));
            setSelectedNodeIds([]);
        }
    }, []);

    // Redo function
    const redo = useCallback(() => {
        if (historyIndexRef.current < historyRef.current.length - 1) {
            historyIndexRef.current += 1;
            const state = historyRef.current[historyIndexRef.current];
            setGraphState(JSON.parse(JSON.stringify(state)));
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
                    (e) =>
                        !idsToDelete.includes(e.source) &&
                        !idsToDelete.includes(e.target),
                );
                saveToHistory(newNodes, newEdges);
                return newEdges;
            });
            setSelectedNodeIds([]);
            return newNodes;
        });
    }, [selectedNodeIds, saveToHistory]);

    // Delete selected edge
    const deleteSelectedEdge = useCallback(() => {
        if (!selectedEdgeId) return;
        setEdges((prev) => {
            const newEdges = prev.filter((e) => e.id !== selectedEdgeId);
            saveToHistory(nodes, newEdges);
            return newEdges;
        });
        setSelectedEdgeId(null);
    }, [selectedEdgeId, nodes, saveToHistory]);

    // Bring a node to front (update z-order)
    const bringNodeToFront = useCallback((nodeId: string) => {
        zOrderCounterRef.current += 1;
        setNodeZOrder((prev) =>
            new Map(prev).set(nodeId, zOrderCounterRef.current),
        );
    }, []);

    // Keyboard shortcuts for undo/redo and delete
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
                e.preventDefault();
                undo();
            } else if (
                (e.ctrlKey || e.metaKey) &&
                (e.key === "y" || (e.key === "z" && e.shiftKey))
            ) {
                e.preventDefault();
                redo();
            } else if (e.key === "Delete" || e.key === "Backspace") {
                // Only delete if not typing in an input/textarea
                const target = e.target as HTMLElement;
                if (
                    target.tagName !== "INPUT" &&
                    target.tagName !== "TEXTAREA" &&
                    !target.isContentEditable
                ) {
                    if (selectedNodeIds.length > 0) {
                        e.preventDefault();
                        deleteSelectedNodes();
                    } else if (selectedEdgeId) {
                        e.preventDefault();
                        deleteSelectedEdge();
                    }
                }
            }
        };
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [
        undo,
        redo,
        selectedNodeIds,
        selectedEdgeId,
        deleteSelectedNodes,
        deleteSelectedEdge,
    ]);

    // Load chapters if not provided
    const [loadedChapters, setLoadedChapters] =
        useState<ProjectChapter[]>(chapters);
    useEffect(() => {
        if (chapters.length === 0) {
            http.get<{ chapters?: ProjectChapter[] }>(
                `/${workspaceId}/projects/${projectId}/editor/chapters`,
            )
                .then(({ data }) => {
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

        if (persistedGraphState?.nodes !== undefined) {
            setGraphState({
                nodes: persistedGraphState.nodes || [],
                edges: persistedGraphState.edges || [],
            });
            setPan(persistedGraphState.pan || { x: 0, y: 0 });
            setZoom(persistedGraphState.zoom || 1);
            if (persistedGraphState.execution_mode) {
                setExecutionMode(persistedGraphState.execution_mode);
            }
        } else {
            const saved = localStorage.getItem(`chain_builder_${projectId}`);
            if (saved) {
                try {
                    const data = JSON.parse(saved);
                    // Load even if nodes array is empty (to restore deletions)
                    if (data.nodes !== undefined) {
                        // Atomic update of both nodes and edges
                        setGraphState({
                            nodes: data.nodes || [],
                            edges: data.edges || [],
                        });
                        setPan(data.pan || { x: 0, y: 0 });
                        setZoom(data.zoom || 1);
                    }
                } catch (e) {
                    console.error("Failed to load graph", e);
                }
            }
        }
        // Always mark as loaded after attempting to load (or if no saved data)
        hasLoadedRef.current = true;
    }, [persistedGraphState, projectId]);

    // Initialize history with current state on mount
    useEffect(() => {
        if (
            nodes.length > 0 &&
            historyRef.current.length === 1 &&
            historyRef.current[0].nodes.length === 1 &&
            historyRef.current[0].nodes[0].id === "root"
        ) {
            // Only initialize if we still have the default root node
            const currentState: GraphState = JSON.parse(
                JSON.stringify(graphState),
            );
            historyRef.current = [currentState];
            historyIndexRef.current = 0;
        }
    }, []); // Only run once on mount

    // Persistence - Save on every change with debounced loading indicator
    useEffect(() => {
        // Don't save if we haven't loaded yet (prevents overwriting with default state)
        if (!hasLoadedRef.current) return;

        // Show saving indicator immediately
        setIsSavingLocal(true);

        // Clear any pending "done" timer
        if (saveDebounceRef.current) {
            clearTimeout(saveDebounceRef.current);
        }

        // Save even if nodes array is empty (to persist deletions)
        localStorage.setItem(
            `chain_builder_${projectId}`,
            JSON.stringify({ nodes, edges, pan, zoom }),
        );

        void http(
            `/${workspaceId}/projects/${projectId}/editor/multi-prompt/state`,
            {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                },
                data: {
                    graph_state: {
                        nodes,
                        edges,
                        pan,
                        zoom,
                        execution_mode: executionMode,
                    },
                    templates,
                },
            },
        ).catch((error) => {
            console.error("Failed to persist chain builder state", error);
        });

        // Debounce the "done" state - wait 1.5s after last change
        saveDebounceRef.current = setTimeout(() => {
            setIsSavingLocal(false);
        }, 1500);

        return () => {
            if (saveDebounceRef.current) {
                clearTimeout(saveDebounceRef.current);
            }
        };
    }, [nodes, edges, pan, zoom, projectId, workspaceId, executionMode, templates]);

    // Templates persistence
    useEffect(() => {
        localStorage.setItem(
            `chain_builder_templates_${projectId}`,
            JSON.stringify(templates),
        );
    }, [templates, projectId]);

    // Combine all loading states for parent notification
    const isAnyLoading =
        isSavingLocal ||
        isFlowRunning ||
        isBuildingGraph ||
        isRefiningGraph ||
        isWandGenerating;

    // Notify parent of loading state changes
    useEffect(() => {
        onLoadingChange?.(isAnyLoading);
    }, [isAnyLoading, onLoadingChange]);

    // Track node heights with ResizeObserver for dynamic edge positioning
    useEffect(() => {
        const observer = new ResizeObserver((entries) => {
            setNodeHeights((prev) => {
                const updates = new Map(prev);
                let hasChanges = false;

                entries.forEach((entry) => {
                    const nodeId = entry.target.getAttribute("data-node-id");
                    if (nodeId) {
                        const newHeight = entry.contentRect.height;
                        if (updates.get(nodeId) !== newHeight) {
                            updates.set(nodeId, newHeight);
                            hasChanges = true;
                        }
                    }
                });

                return hasChanges ? updates : prev;
            });
        });

        // Observe all node elements
        const nodeElements = document.querySelectorAll("[data-node-id]");
        nodeElements.forEach((el) => observer.observe(el));

        return () => observer.disconnect();
    }, [nodes.length]); // Re-setup when node count changes

    // Node Operations
    const addNode = useCallback(
        (
            type: GraphNodeType,
            initialContent?: string,
            initialLabel?: string,
            xOffset?: number,
            yOffset?: number,
        ) => {
            const id = Math.random().toString(36).substr(2, 9);
            const centerX =
                xOffset ??
                (-pan.x + (canvasRef.current?.clientWidth || 800) / 2) / zoom -
                    150;
            const centerY =
                yOffset ??
                (-pan.y + (canvasRef.current?.clientHeight || 600) / 2) / zoom -
                    100;

            setNodes((prev) => {
                const newNodes: GraphNode[] = [
                    ...prev,
                    {
                        id,
                        type,
                        position: { x: centerX, y: centerY },
                        data: {
                            label:
                                initialLabel ||
                                (type === "prompt"
                                    ? "New Prompt"
                                    : type === "context"
                                      ? "Context Data"
                                      : "Logic Gate"),
                            content: initialContent || "",
                            status: "idle" as NodeStatus,
                        },
                    },
                ];
                saveToHistory(newNodes, edges);
                return newNodes;
            });
        },
        [pan, zoom, edges, saveToHistory],
    );

    const deleteNode = useCallback(
        (id: string) => {
            setNodes((prev) => {
                const newNodes = prev.filter((n) => n.id !== id);
                setEdges((prevEdges) => {
                    const newEdges = prevEdges.filter(
                        (e) => e.source !== id && e.target !== id,
                    );
                    saveToHistory(newNodes, newEdges);
                    return newEdges;
                });
                setSelectedNodeIds((prev) => prev.filter((sid) => sid !== id));
                return newNodes;
            });
        },
        [saveToHistory],
    );

    const updateNodeData = useCallback(
        (id: string, updates: Partial<GraphNode["data"]>) => {
            setNodes((prev) =>
                prev.map((n) =>
                    n.id === id ? { ...n, data: { ...n.data, ...updates } } : n,
                ),
            );
        },
        [],
    );

    // Viewport Handlers
    const handleWheel = useCallback(
        (e: React.WheelEvent) => {
            if (e.ctrlKey || e.metaKey || e.deltaY !== 0) {
                e.preventDefault();
                if (canvasRef.current) {
                    const rect = canvasRef.current.getBoundingClientRect();
                    const mouseX = e.clientX - rect.left;
                    const mouseY = e.clientY - rect.top;
                    const result = zoomAtPoint(
                        zoom,
                        e.deltaY,
                        mouseX,
                        mouseY,
                        pan,
                    );
                    setZoom(result.zoom);
                    setPan(result.pan);
                }
            }
        },
        [zoom, pan],
    );

    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        // Middle mouse button panning (keep for power users)
        if (e.button === 1) {
            setIsPanning(true);
            setLastMousePan({ x: e.clientX, y: e.clientY });
            return;
        }

        // Left-click: check if it's a background click (not on a node)
        if (e.button === 0) {
            const target = e.target as HTMLElement;
            const clickedOnNode = target.closest("[data-node-id]");

            if (!clickedOnNode) {
                // Clicked on canvas background - start panning and deselect
                setIsPanning(true);
                setLastMousePan({ x: e.clientX, y: e.clientY });

                if (!e.shiftKey) {
                    setSelectedNodeIds([]);
                    setSelectedEdgeId(null); // Also deselect edges
                }
                return;
            }
        }
    }, []);

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
                                position: {
                                    x: n.position.x + dx,
                                    y: n.position.y + dy,
                                },
                            };
                        }
                        if (
                            selectedNodeIds.includes(draggingNodeId) &&
                            selectedNodeIds.includes(n.id) &&
                            n.id !== draggingNodeId
                        ) {
                            return {
                                ...n,
                                position: {
                                    x: n.position.x + dx,
                                    y: n.position.y + dy,
                                },
                            };
                        }
                        return n;
                    }),
                );
            }
        },
        [isPanning, lastMousePan, draggingNodeId, selectedNodeIds, pan, zoom],
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
            setSelectedEdgeId(null); // Deselect edges when clicking a node
            bringNodeToFront(id); // Bring clicked node to front

            if (e.shiftKey) {
                setSelectedNodeIds((prev) => {
                    if (prev.includes(id))
                        return prev.filter((pid) => pid !== id);
                    return [...prev, id];
                });
            } else {
                if (!selectedNodeIds.includes(id)) {
                    setSelectedNodeIds([id]);
                }
            }
        },
        [selectedNodeIds, bringNodeToFront],
    );

    const handleConnectorMouseDown = useCallback(
        (e: React.MouseEvent, id: string) => {
            e.stopPropagation();
            setConnectingNodeId(id);
        },
        [],
    );

    const handleConnectorMouseUp = useCallback(
        (e: React.MouseEvent, targetId: string) => {
            e.stopPropagation();
            if (connectingNodeId && connectingNodeId !== targetId) {
                if (
                    !edges.find(
                        (edge) =>
                            edge.source === connectingNodeId &&
                            edge.target === targetId,
                    )
                ) {
                    setEdges((prev) => {
                        const newEdges = [
                            ...prev,
                            {
                                id: `${connectingNodeId}-${targetId}`,
                                source: connectingNodeId,
                                target: targetId,
                            },
                        ];
                        saveToHistory(nodes, newEdges);
                        return newEdges;
                    });
                }
            }
            setConnectingNodeId(null);
        },
        [connectingNodeId, edges, nodes, saveToHistory],
    );

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
    }, []);

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            const entityData = e.dataTransfer.getData("application/json");
            if (entityData && canvasRef.current) {
                try {
                    const entity = JSON.parse(entityData) as Entity;
                    const rect = canvasRef.current.getBoundingClientRect();
                    const dropX = (e.clientX - rect.left - pan.x) / zoom - 150;
                    const dropY = (e.clientY - rect.top - pan.y) / zoom - 50;

                    const formattedContent = formatEntityForContext(entity);
                    addNode(
                        "context",
                        formattedContent,
                        entity.name,
                        dropX,
                        dropY,
                    );
                } catch (err) {
                    console.error("Invalid drop data", err);
                }
            }
        },
        [pan, zoom, addNode],
    );

    // Execution
    const executeFlow = useCallback(async () => {
        if (isFlowRunning) return;
        if (detectCycles(nodes, edges)) {
            toast.warning(
                "Cannot run flow: Infinite loop detected! Please check your connections.",
            );
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
                updateNodeData,
            );

            if (results.length > 0) {
                const deduplicateSequenceResults = (outputs: string[]) => {
                    const deduped: string[] = [];

                    outputs.forEach((raw) => {
                        let current = (raw || "").trim();
                        if (!current) return;

                        // Compare against prior deduped outputs (most recent first)
                        for (let j = deduped.length - 1; j >= 0; j--) {
                            const previous = deduped[j]?.trim();
                            if (!previous) continue;

                            // If current starts with the full previous text, strip it
                            if (current.startsWith(previous)) {
                                current = current
                                    .slice(previous.length)
                                    .trimStart();
                                break;
                            }

                            // If current contains the tail of previous (e.g., overlap), strip from that point
                            const tailWords = previous
                                .split(/\s+/)
                                .filter(Boolean)
                                .slice(-30)
                                .join(" ");
                            if (tailWords) {
                                const overlapIndex = current.indexOf(tailWords);
                                if (overlapIndex === 0) {
                                    current = current
                                        .slice(tailWords.length)
                                        .trimStart();
                                    break;
                                } else if (overlapIndex > 0) {
                                    // Found overlap in the middle, strip from overlap point
                                    current = current
                                        .slice(overlapIndex + tailWords.length)
                                        .trimStart();
                                    break;
                                }
                            }

                            // Also check if current ends with beginning of previous (reverse overlap)
                            const headWords = previous
                                .split(/\s+/)
                                .filter(Boolean)
                                .slice(0, 30)
                                .join(" ");
                            if (headWords && current.endsWith(headWords)) {
                                current = current
                                    .slice(0, -headWords.length)
                                    .trimEnd();
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
                    executionMode === "sequence"
                        ? (() => {
                              const deduped =
                                  deduplicateSequenceResults(results);
                              return deduped.length ? deduped : results;
                          })()
                        : results;

                const resultText = sequenceSafeResults.join("\n\n");
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
            console.error("Error executing flow:", error);
            toast.error(
                "Error executing flow: " +
                    (error instanceof Error ? error.message : "Unknown error"),
            );
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

            updateNodeData(nodeId, { status: "running" });
            try {
                const outputsMap = new Map<string, string>();
                nodes.forEach((n) => {
                    if (n.type === "context") {
                        outputsMap.set(n.id, n.data.content);
                    } else if (n.data.output) {
                        outputsMap.set(n.id, n.data.output);
                    }
                });

                const inputs = gatherNodeInputs(
                    nodeId,
                    nodes,
                    edges,
                    outputsMap,
                );
                const storyContext = getFullStoryContext(loadedChapters);

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
                    projectId,
                );

                updateNodeData(nodeId, { status: "completed", output: result });
            } catch (error) {
                console.error("Node execution failed:", error);
                updateNodeData(nodeId, {
                    status: "error",
                    errorMessage:
                        error instanceof Error
                            ? error.message
                            : "Unknown error",
                });
                toast.error(
                    "Node execution failed: " +
                        (error instanceof Error
                            ? error.message
                            : "Unknown error"),
                );
            }
        },
        [
            nodes,
            edges,
            loadedChapters,
            aiModel,
            authorProfile,
            settings,
            workspaceId,
            projectId,
            updateNodeData,
        ],
    );

    // Auto-Build
    const handleAutoBuildGraph = useCallback(async () => {
        if (!autoBuildPrompt) return;
        setIsBuildingGraph(true);
        try {
            const storyContext = getFullStoryContext(loadedChapters);

            // Fetch entities
            const entitiesResponse = await http(
                `/${workspaceId}/projects/${projectId}/editor/records/entities`,
            );
            const entitiesData = entitiesResponse.data;
            const entities = (entitiesData.entities || []).map((e: Entity) => ({
                name: e.name,
                type: e.type,
                properties: e.properties,
            }));

            // Log model selection for debugging
            console.log("Auto-Build: Using AI model", {
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
                    existing_nodes: nodes, // Pass current graph state to avoid stale conversation history
                    existing_edges: edges, // Pass current edges for context
                },
                workspaceId,
                projectId,
            );

            if (layout.nodes.length > 0) {
                // Atomic update of both nodes and edges to ensure edges are selectable
                setGraphState({
                    nodes: layout.nodes,
                    edges: layout.edges.map((e) => ({
                        id: `${e.source}-${e.target}`,
                        source: e.source,
                        target: e.target,
                    })),
                });
                setExecutionMode(autoBuildMode);
                setIsAutoBuildOpen(false);
                setAutoBuildPrompt("");
            }
        } catch (error) {
            console.error("Failed to build graph:", error);
            toast.error(
                "Failed to build graph: " +
                    (error instanceof Error ? error.message : "Unknown error"),
            );
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
            const selectedNodes = nodes.filter((n) =>
                selectedNodeIds.includes(n.id),
            );
            const internalEdges = edges.filter(
                (e) =>
                    selectedNodeIds.includes(e.source) &&
                    selectedNodeIds.includes(e.target),
            );

            const incomingEdges = edges.filter(
                (e) =>
                    !selectedNodeIds.includes(e.source) &&
                    selectedNodeIds.includes(e.target),
            );
            const outgoingEdges = edges.filter(
                (e) =>
                    selectedNodeIds.includes(e.source) &&
                    !selectedNodeIds.includes(e.target),
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
                projectId,
            );

            if (refinedSubgraph.nodes && refinedSubgraph.nodes.length > 0) {
                const remainingNodes = nodes.filter(
                    (n) => !selectedNodeIds.includes(n.id),
                );
                const remainingEdges = edges.filter(
                    (e) =>
                        !selectedNodeIds.includes(e.source) &&
                        !selectedNodeIds.includes(e.target),
                );

                const newNodes = refinedSubgraph.nodes;
                const newInternalEdges = refinedSubgraph.edges || [];

                const sortedNewNodes = [...newNodes].sort(
                    (a, b) => a.position.y - b.position.y,
                );
                const firstNewNode = sortedNewNodes[0];
                const lastNewNode = sortedNewNodes[sortedNewNodes.length - 1];

                const reconnectedEdges = [
                    ...remainingEdges,
                    ...newInternalEdges.map((e) => ({
                        id: `${e.source}-${e.target}`,
                        source: e.source,
                        target: e.target,
                    })),
                    ...incomingEdges.map((e) => ({
                        ...e,
                        target: firstNewNode.id,
                    })),
                    ...outgoingEdges.map((e) => ({
                        ...e,
                        source: lastNewNode.id,
                    })),
                ];

                // Atomic update of both nodes and edges
                setGraphState({
                    nodes: [...remainingNodes, ...newNodes],
                    edges: reconnectedEdges,
                });
                setSelectedNodeIds([]);
                setIsRefinerOpen(false);
                setRefinerPrompt("");
            }
        } catch (error) {
            console.error("Failed to refine selection:", error);
            toast.error(
                "Failed to refine selection: " +
                    (error instanceof Error ? error.message : "Unknown error"),
            );
        } finally {
            setIsRefiningGraph(false);
        }
    }, [
        refinerPrompt,
        selectedNodeIds,
        nodes,
        edges,
        loadedChapters,
        aiModel,
        workspaceId,
        projectId,
    ]);

    // Magic Wand
    const handleWandGenerate = useCallback(async () => {
        if (!wandNodeId) return;

        // Get the node to determine its type
        const wandNode = nodes.find((n) => n.id === wandNodeId);
        if (!wandNode) return;

        const hasExistingContent =
            wandNode.data.content && wandNode.data.content.trim().length > 0;

        // If node has content, enhance it. If empty, create prompt from seed.
        if (hasExistingContent) {
            // Enhance existing content
            if (!wandSeed.trim()) {
                toast.warning(
                    "Please enter enhancement instructions or leave empty to enhance automatically",
                );
                return;
            }

            setIsWandGenerating(true);

            try {
                const response = await http(
                    `/${workspaceId}/projects/${projectId}/editor/enhance-text`,
                    {
                        method: "POST",
                        data: {
                            text: wandNode.data.content.trim(),
                            enhancement_mode: wandSeed.trim()
                                ? "custom_instruction"
                                : "story_text",
                            model: aiModel,
                        },
                    },
                );

                if (!(response.status >= 200 && response.status < 300)) {
                    const error =
                        response.data && typeof response.data === "object"
                            ? response.data
                            : { error: "Unknown error" };
                    throw new Error(error.error || `HTTP ${response.status}`);
                }

                const data = response.data;
                if (data.success && data.enhanced_text) {
                    updateNodeData(wandNodeId, {
                        content: data.enhanced_text.trim(),
                    });
                    setWandNodeId(null);
                    setWandSeed("");
                } else {
                    throw new Error("No enhanced text returned");
                }
            } catch (error) {
                console.error("Failed to enhance instruction:", error);
                const errorMessage =
                    error instanceof Error ? error.message : "Unknown error";
                toast.error(`Failed to enhance instruction: ${errorMessage}`);
            } finally {
                setIsWandGenerating(false);
            }
        } else {
            // Create new prompt from seed
            if (!wandSeed.trim()) {
                toast.warning("Please enter a description of what you want to write");
                return;
            }

            setIsWandGenerating(true);

            try {
                const outputsMap = new Map<string, string>();
                nodes
                    .filter((n) => n.type === "context")
                    .forEach((n) => outputsMap.set(n.id, n.data.content));

                const inputs = gatherNodeInputs(
                    wandNodeId,
                    nodes,
                    edges,
                    outputsMap,
                );
                const storyContext = getFullStoryContext(loadedChapters);

                const instruction = await generateInstruction(
                    {
                        seed: wandSeed.trim(),
                        inputs,
                        story_context: storyContext,
                        ai_model: aiModel,
                        node_type:
                            wandNode.type === "logic" ? "logic" : "prompt", // Pass node type to backend
                    },
                    workspaceId,
                    projectId,
                );

                if (instruction && instruction.trim()) {
                    updateNodeData(wandNodeId, { content: instruction.trim() });
                    setWandNodeId(null);
                    setWandSeed("");
                } else {
                    throw new Error("Empty instruction returned");
                }
            } catch (error) {
                console.error("Failed to generate instruction:", error);
                const errorMessage =
                    error instanceof Error ? error.message : "Unknown error";
                toast.error(`Failed to auto-generate instruction: ${errorMessage}`);
            } finally {
                setIsWandGenerating(false);
            }
        }
    }, [
        wandNodeId,
        wandSeed,
        nodes,
        edges,
        loadedChapters,
        aiModel,
        workspaceId,
        projectId,
        updateNodeData,
    ]);

    // Inspector
    const getInspectionData = useCallback(() => {
        if (!inspectedNodeId) return null;
        const node = nodes.find((n) => n.id === inspectedNodeId);
        if (!node) return null;

        const outputsMap = new Map<string, string>();
        nodes.forEach((n) => outputsMap.set(n.id, n.data.output || ""));
        const inputs = gatherNodeInputs(
            inspectedNodeId,
            nodes,
            edges,
            outputsMap,
        );

        const inputsText = inputs
            .map((input) => {
                const typeLabel =
                    input.type === "context"
                        ? "BACKGROUND DATA"
                        : "PREVIOUS STEP OUTPUT";
                return `--- ${typeLabel} (${input.label}) ---\n${input.text}\n-------------------`;
            })
            .join("\n\n");

        const storyContext = getFullStoryContext(loadedChapters);
        return {
            nodeLabel: node.data.label,
            nodeInstruction: node.data.content,
            inputsText,
            storyPreview: storyContext.slice(-500) + "...",
        };
    }, [inspectedNodeId, nodes, edges, loadedChapters]);

    const inspectionData = getInspectionData();

    // Template handlers
    const handleSaveTemplate = useCallback(() => {
        if (!templateName.trim()) {
            toast.warning("Please enter a template name");
            return;
        }

        const newTemplate: GraphTemplate = {
            id: editingTemplateId || Date.now().toString(),
            name: templateName.trim(),
            nodes: JSON.parse(JSON.stringify(nodes)),
            edges: JSON.parse(JSON.stringify(edges)),
            projectId,
            createdAt: editingTemplateId
                ? templates.find((t) => t.id === editingTemplateId)?.createdAt
                : new Date().toISOString(),
        };

        if (editingTemplateId) {
            // Update existing template
            setTemplates((prev) =>
                prev.map((t) => (t.id === editingTemplateId ? newTemplate : t)),
            );
        } else {
            // Add new template
            setTemplates((prev) => [...prev, newTemplate]);
        }

        setTemplateName("");
        setEditingTemplateId(null);
    }, [templateName, nodes, edges, projectId, editingTemplateId, templates]);

    const handleLoadTemplate = useCallback(
        async (template: GraphTemplate) => {
            if (
                await confirm({
                    title: "Load template?",
                    description:
                        "Load this template? Current graph will be overwritten.",
                    actionLabel: "Load template",
                })
            ) {
                const newState: GraphState = {
                    nodes: JSON.parse(JSON.stringify(template.nodes)),
                    edges: JSON.parse(JSON.stringify(template.edges)),
                };
                setGraphState(newState);
                setIsTemplatesOpen(false);
                saveToHistory(template.nodes, template.edges);
            }
        },
        [confirm, saveToHistory],
    );

    const handleDeleteTemplate = useCallback(async (templateId: string) => {
        if (
            await confirm({
                title: "Delete template?",
                description: "Delete this template?",
                actionLabel: "Delete template",
            })
        ) {
            setTemplates((prev) => prev.filter((t) => t.id !== templateId));
        }
    }, [confirm]);

    const handleEditTemplate = useCallback(
        async (template: GraphTemplate) => {
            if (
                await confirm({
                    title: "Load template for editing?",
                    description:
                        "Load this template for editing? Current graph will be overwritten.",
                    actionLabel: "Load template",
                })
            ) {
                const newState: GraphState = {
                    nodes: JSON.parse(JSON.stringify(template.nodes)),
                    edges: JSON.parse(JSON.stringify(template.edges)),
                };
                setGraphState(newState);
                setEditingTemplateId(template.id);
                setTemplateName(template.name);
                saveToHistory(template.nodes, template.edges);
            }
        },
        [confirm, saveToHistory],
    );

    const handleStartNewTemplate = useCallback(() => {
        setEditingTemplateId(null);
        setTemplateName("");
    }, []);

    return (
        <div
            className="flex flex-col w-full h-full bg-gray-50 overflow-hidden"
            style={{ minHeight: "calc(100vh - 4rem)" }}
        >
            <Toolbar
                selectedNodeIds={selectedNodeIds}
                executionMode={executionMode}
                isFlowRunning={isFlowRunning}
                onAddNode={addNode}
                onDeleteSelected={deleteSelectedNodes}
                onOpenAutoBuild={() => setIsAutoBuildOpen(true)}
                onOpenRefiner={() => setIsRefinerOpen(true)}
                onSetExecutionMode={setExecutionMode}
                onExecuteFlow={executeFlow}
            />

            {/* Main Content Area - Records + Canvas + Templates */}
            <div className="flex flex-1 min-h-0 overflow-hidden">
                {/* Records Drawer - Full Height Left */}
                <RecordsDrawer
                    workspaceId={workspaceId}
                    projectId={projectId}
                    onEntityDrop={(entity, position) => {
                        const formattedContent = formatEntityForContext(entity);
                        addNode(
                            "context",
                            formattedContent,
                            entity.name,
                            position.x,
                            position.y,
                        );
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
                            backgroundImage:
                                "radial-gradient(circle, #9ca3af 1px, transparent 1px)",
                            backgroundSize: `${20 * zoom}px ${20 * zoom}px`,
                            backgroundPosition: `${pan.x}px ${pan.y}px`,
                        }}
                    />

                    {/* SVG for Edges */}
                    <svg
                        ref={svgRef}
                        className="overflow-visible absolute inset-0 w-full h-full"
                    >
                        <defs>
                            <style>
                                {`
                                    @keyframes flowAnimation {
                                        from { stroke-dashoffset: 12; }
                                        to { stroke-dashoffset: 0; }
                                    }
                                `}
                            </style>
                        </defs>
                        {edges.map((edge) => {
                            const sourceNode = nodes.find(
                                (n) => n.id === edge.source,
                            );
                            const targetNode = nodes.find(
                                (n) => n.id === edge.target,
                            );
                            const isEdgeSelected = selectedEdgeId === edge.id;
                            return (
                                <Edge
                                    key={edge.id}
                                    edge={edge}
                                    sourceNode={sourceNode}
                                    targetNode={targetNode}
                                    isSelected={isEdgeSelected}
                                    pan={pan}
                                    zoom={zoom}
                                    sourceHeight={nodeHeights.get(edge.source)}
                                    targetHeight={nodeHeights.get(edge.target)}
                                    onClick={(id) => {
                                        setSelectedEdgeId(id);
                                        setSelectedNodeIds([]); // Deselect nodes when edge is selected
                                    }}
                                />
                            );
                        })}
                        {connectingNodeId &&
                            (() => {
                                const connectingNode = nodes.find(
                                    (n) => n.id === connectingNodeId,
                                );
                                const connectingNodeHeight =
                                    nodeHeights.get(connectingNodeId) || 82;
                                const sourceOffset = Math.min(
                                    connectingNodeHeight * 0.035,
                                    8,
                                );
                                return (
                                    <ConnectingLine
                                        sourceX={
                                            (connectingNode?.position.x || 0) +
                                            300
                                        }
                                        sourceY={
                                            (connectingNode?.position.y || 0) +
                                            connectingNodeHeight / 2 +
                                            sourceOffset
                                        }
                                        targetX={mousePos.x}
                                        targetY={mousePos.y}
                                        pan={pan}
                                        zoom={zoom}
                                    />
                                );
                            })()}
                    </svg>

                    {/* Nodes Container */}
                    <div
                        style={{
                            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                            transformOrigin: "0 0",
                        }}
                        className="w-full h-full absolute inset-0 pointer-events-none"
                    >
                        {nodes.map((node) => (
                            <Node
                                key={node.id}
                                node={node}
                                isSelected={selectedNodeIds.includes(node.id)}
                                zIndex={nodeZOrder.get(node.id) || 0}
                                onSelect={(e) =>
                                    handleNodeMouseDown(e, node.id)
                                }
                                onDragStart={(e) =>
                                    handleConnectorMouseDown(e, node.id)
                                }
                                onConnectorMouseUp={(e) =>
                                    handleConnectorMouseUp(e, node.id)
                                }
                                onUpdate={(updates) =>
                                    updateNodeData(node.id, updates)
                                }
                                onDelete={() => deleteNode(node.id)}
                                onExecute={() => executeNodeSingle(node.id)}
                                onInspect={() => setInspectedNodeId(node.id)}
                                onApplyResult={onApplyResult}
                                onMagicWand={(currentContent) => {
                                    setWandNodeId(node.id);
                                    setWandSeed(currentContent || "");
                                }}
                                workspaceId={workspaceId}
                                projectId={projectId}
                            />
                        ))}
                    </div>
                </div>

                <CanvasControls
                    zoom={zoom}
                    historyIndexRef={historyIndexRef}
                    historyRef={historyRef}
                    onUndo={undo}
                    onRedo={redo}
                    onZoomIn={() => setZoom(Math.min(zoom + 0.1, 3))}
                    onZoomOut={() => setZoom(Math.max(zoom - 0.1, 0.2))}
                    onResetView={() => {
                        if (!canvasRef.current) return;

                        const { zoom: fitZoom, pan: fitPan } = fitViewToNodes(
                            nodes,
                            canvasRef.current.clientWidth,
                            canvasRef.current.clientHeight,
                        );

                        setZoom(fitZoom);
                        setPan(fitPan);
                    }}
                />

                <TemplatesSidebar
                    isOpen={isTemplatesOpen}
                    templates={templates}
                    templateName={templateName}
                    editingTemplateId={editingTemplateId}
                    onOpenChange={setIsTemplatesOpen}
                    onTemplateNameChange={setTemplateName}
                    onSaveTemplate={handleSaveTemplate}
                    onLoadTemplate={handleLoadTemplate}
                    onEditTemplate={handleEditTemplate}
                    onDeleteTemplate={handleDeleteTemplate}
                    onStartNewTemplate={handleStartNewTemplate}
                />
            </div>

            {/* Modals */}
            <AutoBuildDialog
                open={isAutoBuildOpen}
                onOpenChange={setIsAutoBuildOpen}
                autoBuildPrompt={autoBuildPrompt}
                setAutoBuildPrompt={setAutoBuildPrompt}
                autoBuildMode={autoBuildMode}
                setAutoBuildMode={setAutoBuildMode}
                isBuildingGraph={isBuildingGraph}
                onBuild={handleAutoBuildGraph}
                storyContext={getFullStoryContext(loadedChapters)}
                workspaceId={workspaceId}
                projectId={projectId}
                aiModel={aiModel}
            />

            <MagicWandDialog
                open={!!wandNodeId}
                onOpenChange={() => setWandNodeId(null)}
                wandSeed={wandSeed}
                setWandSeed={setWandSeed}
                isGenerating={isWandGenerating}
                onGenerate={handleWandGenerate}
            />

            <RefinerDialog
                open={isRefinerOpen}
                onOpenChange={setIsRefinerOpen}
                refinerPrompt={refinerPrompt}
                setRefinerPrompt={setRefinerPrompt}
                selectedCount={selectedNodeIds.length}
                isRefining={isRefiningGraph}
                onRefine={handleRefineGraph}
            />

            <InspectorDialog
                open={!!inspectedNodeId}
                onOpenChange={() => setInspectedNodeId(null)}
                inspectionData={inspectionData}
            />

            <ResultDialog
                open={showResultDialog}
                onOpenChange={setShowResultDialog}
                generatedResult={generatedResult}
                onApply={async () => {
                    if (generatedResult) {
                        try {
                            // Save content server-side first (avoids URL parameter size limits)
                            const response = await http(
                                `/${workspaceId}/projects/${projectId}/editor/chain-builder/apply-to-story`,
                                {
                                    method: "POST",
                                    headers: {
                                        "Content-Type": "application/json",
                                        Accept: "application/json",
                                    },
                                    data: {
                                        result_text: generatedResult,
                                        // chapter_order: optional, defaults to last chapter
                                    },
                                },
                            );

                            if (
                                response.status >= 200 &&
                                response.status < 300
                            ) {
                                // Content saved successfully, navigate to editor
                                // The editor will load fresh data from the database
                                router.visit(
                                    `/${workspaceId}/projects/${projectId}/editor`,
                                    {
                                        preserveState: false,
                                        preserveScroll: false,
                                    },
                                );
                            } else {
                                const error = response.data.catch(() => ({
                                    error: "Unknown error",
                                }));
                                console.error("Failed to apply result:", error);
                                toast.error(
                                    `Failed to save content: ${error.error || "Please try again."}`,
                                );
                            }
                        } catch (error) {
                            console.error("Error applying result:", error);
                            toast.error("Failed to save content. Please try again.");
                        }
                    } else {
                        router.visit(
                            `/${workspaceId}/projects/${projectId}/editor`,
                        );
                    }
                }}
                onStayHere={() => {
                    setShowResultDialog(false);
                    setGeneratedResult(null);
                }}
            />
        </div>
    );
};

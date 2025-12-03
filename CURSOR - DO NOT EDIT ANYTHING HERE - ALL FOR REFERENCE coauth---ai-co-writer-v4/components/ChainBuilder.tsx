
import React, { useState, useRef, MouseEvent, DragEvent, useEffect, useMemo } from 'react';
import { X, Play, Trash2, Loader2, CheckCircle2, Copy, Download, Box, Type, Wand2, Zap, Eye, Settings2, Layers, ArrowRightToLine, Book, Palette, Save, FolderOpen, MoreHorizontal, Sparkles, MousePointer2, AlertTriangle, ZoomIn, ZoomOut, Maximize, Filter } from 'lucide-react';
import { GraphNode, GraphEdge, ModelType, GraphNodeType, GraphExecutionMode, GraphInput, BibleItem, StyleProfile, GraphTemplate, BibleSchema } from '../types';
import { runGraphNode, generateNodeInstruction, generateGraphLayout, refineGraphSelection, formatBibleItemForContext } from '../services/geminiService';
import { Button } from './Button';

interface ChainBuilderProps {
  isOpen: boolean;
  onClose: () => void;
  storyContext: string;
  selectedModel: ModelType;
  onApplyResult: (text: string) => void;
  bibleItems: BibleItem[];
  bibleSchemas: BibleSchema[];
  activeStyleProfile: StyleProfile | null;
  // Template Props
  templates: GraphTemplate[];
  onSaveTemplate: (template: GraphTemplate) => void;
  onLoadTemplate: (template: GraphTemplate) => void;
  onDeleteTemplate: (id: string) => void;
  
  onPromoteNode: (name: string, description: string) => void;
}

export const ChainBuilder: React.FC<ChainBuilderProps> = ({
  isOpen,
  onClose,
  storyContext,
  selectedModel,
  onApplyResult,
  bibleItems,
  bibleSchemas,
  activeStyleProfile,
  templates,
  onSaveTemplate,
  onLoadTemplate,
  onDeleteTemplate,
  onPromoteNode
}) => {
  // Graph State
  const [nodes, setNodes] = useState<GraphNode[]>([
    { 
      id: 'root', 
      type: 'prompt', 
      position: { x: 300, y: 100 }, 
      data: { label: 'Start Prompt', content: 'Describe the setting...', status: 'idle' } 
    }
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
  
  // Inspection & Tools State
  const [inspectedNodeId, setInspectedNodeId] = useState<string | null>(null);
  const [isTemplatesOpen, setIsTemplatesOpen] = useState(false);
  const [templateName, setTemplateName] = useState('');
  
  // Bible Filter State
  const [activeBibleFilter, setActiveBibleFilter] = useState<string>('all');
  
  // Magic Wand State
  const [wandNodeId, setWandNodeId] = useState<string | null>(null);
  const [wandSeed, setWandSeed] = useState('');
  const [isWandGenerating, setIsWandGenerating] = useState(false);

  // Auto Build State
  const [isAutoBuildOpen, setIsAutoBuildOpen] = useState(false);
  const [autoBuildPrompt, setAutoBuildPrompt] = useState('');
  const [isBuildingGraph, setIsBuildingGraph] = useState(false);
  const [autoBuildMode, setAutoBuildMode] = useState<GraphExecutionMode>('sequence');

  // Graph Refiner State
  const [isRefinerOpen, setIsRefinerOpen] = useState(false);
  const [refinerPrompt, setRefinerPrompt] = useState('');
  const [isRefiningGraph, setIsRefiningGraph] = useState(false);

  const canvasRef = useRef<HTMLDivElement>(null);

  // Persistence (Auto-Save Graph State)
  useEffect(() => {
    if (isOpen) {
        const saved = localStorage.getItem('coauth_graph');
        if (saved) {
            try {
                const data = JSON.parse(saved);
                setNodes(data.nodes || []);
                setEdges(data.edges || []);
                setPan(data.pan || { x: 0, y: 0 });
                setZoom(data.zoom || 1);
            } catch (e) { console.error("Failed to load graph", e); }
        }
    }
  }, [isOpen]);

  useEffect(() => {
    if (nodes.length > 0) {
        localStorage.setItem('coauth_graph', JSON.stringify({ nodes, edges, pan, zoom }));
    }
  }, [nodes, edges, pan, zoom]);

  // --- Computed Categories ---
  const bibleCategories = useMemo(() => {
      const uniqueIds = Array.from(new Set(bibleItems.map(i => i.schemaId)));
      return ['all', ...uniqueIds];
  }, [bibleItems]);

  const filteredBibleItems = useMemo(() => {
      if (activeBibleFilter === 'all') return bibleItems;
      return bibleItems.filter(i => i.schemaId === activeBibleFilter);
  }, [bibleItems, activeBibleFilter]);
  
  const getCategoryName = (id: string) => {
      if (id === 'all') return 'All';
      const schema = bibleSchemas.find(s => s.id === id);
      return schema ? schema.name : id;
  };

  // --- Node Operations ---

  const addNode = (type: GraphNodeType, initialContent?: string, initialLabel?: string, xOffset?: number, yOffset?: number) => {
    const id = Math.random().toString(36).substr(2, 9);
    const centerX = xOffset ?? (-pan.x + (canvasRef.current?.clientWidth || 800) / 2) / zoom - 150;
    const centerY = yOffset ?? (-pan.y + (canvasRef.current?.clientHeight || 600) / 2) / zoom - 100;
    
    setNodes(prev => [...prev, {
      id,
      type,
      position: { x: centerX, y: centerY },
      data: { 
        label: initialLabel || (type === 'prompt' ? 'New Prompt' : type === 'context' ? 'Context Data' : 'Logic Gate'), 
        content: initialContent || '', 
        status: 'idle' 
      }
    }]);
  };

  const deleteNode = (id: string) => {
    setNodes(nodes.filter(n => n.id !== id));
    setEdges(edges.filter(e => e.source !== id && e.target !== id));
    setSelectedNodeIds(prev => prev.filter(sid => sid !== id));
  };

  const updateNodeData = (id: string, updates: Partial<GraphNode['data']>) => {
    setNodes(prev => prev.map(n => n.id === id ? { ...n, data: { ...n.data, ...updates } } : n));
  };

  // --- Template Handlers ---
  
  const handleSaveTemplate = () => {
      if (!templateName) return;
      onSaveTemplate({
          id: Date.now().toString(),
          name: templateName,
          nodes: nodes,
          edges: edges
      });
      setTemplateName('');
      setIsTemplatesOpen(false);
  };

  const handleLoadTemplate = (t: GraphTemplate) => {
      if(confirm("Load template? Current graph will be overwritten.")) {
          setNodes(t.nodes);
          setEdges(t.edges);
          setIsTemplatesOpen(false);
      }
  };

  // --- Magic Wand & Auto Build Logic ---

  const handleWandGenerate = async () => {
      if (!wandNodeId) return;
      setIsWandGenerating(true);
      
      try {
        const outputsMap = new Map<string, string>();
        nodes.filter(n => n.type === 'context').forEach(n => outputsMap.set(n.id, n.data.content));
        
        const inputs = gatherNodeInputs(wandNodeId, nodes, outputsMap);
        
        const instruction = await generateNodeInstruction(wandSeed, inputs, storyContext, selectedModel);
        
        updateNodeData(wandNodeId, { content: instruction });
        setWandNodeId(null);
        setWandSeed('');
      } catch (e) {
          alert("Failed to auto-generate instruction");
      } finally {
          setIsWandGenerating(false);
      }
  };

  const handleAutoBuildGraph = async () => {
      if (!autoBuildPrompt) return;
      setIsBuildingGraph(true);
      try {
          const layout = await generateGraphLayout(autoBuildPrompt, storyContext, bibleItems, autoBuildMode, selectedModel);
          if (layout.nodes.length > 0) {
              const hydratedNodes = layout.nodes.map(node => {
                  if (node.type === 'context') {
                      const match = bibleItems.find(i => i.name.toLowerCase() === node.data.label.toLowerCase());
                      if (match) {
                          return { 
                              ...node, 
                              data: { 
                                  ...node.data, 
                                  content: formatBibleItemForContext(match) 
                              } 
                          };
                      }
                  }
                  return node;
              });

              setNodes(hydratedNodes);
              setEdges(layout.edges);
              setExecutionMode(autoBuildMode); // Auto-switch execution mode to match build
              setIsAutoBuildOpen(false);
              setAutoBuildPrompt('');
          }
      } catch (e) {
          alert("Failed to build graph automatically.");
      } finally {
          setIsBuildingGraph(false);
      }
  };
  
  const handleRefineGraph = async () => {
      if (!refinerPrompt || selectedNodeIds.length === 0) return;
      setIsRefiningGraph(true);
      
      try {
          const selectedNodes = nodes.filter(n => selectedNodeIds.includes(n.id));
          const internalEdges = edges.filter(e => selectedNodeIds.includes(e.source) && selectedNodeIds.includes(e.target));
          
          const incomingEdges = edges.filter(e => !selectedNodeIds.includes(e.source) && selectedNodeIds.includes(e.target));
          const outgoingEdges = edges.filter(e => selectedNodeIds.includes(e.source) && !selectedNodeIds.includes(e.target));

          const refinedSubgraph = await refineGraphSelection(selectedNodes, internalEdges, refinerPrompt, storyContext, selectedModel);
          
          if (refinedSubgraph.nodes && refinedSubgraph.nodes.length > 0) {
              const remainingNodes = nodes.filter(n => !selectedNodeIds.includes(n.id));
              const remainingEdges = edges.filter(e => !selectedNodeIds.includes(e.source) && !selectedNodeIds.includes(e.target));
              
              const newNodes = refinedSubgraph.nodes;
              const newInternalEdges = refinedSubgraph.edges || [];
              
              const sortedNewNodes = [...newNodes].sort((a,b) => a.position.y - b.position.y);
              const firstNewNode = sortedNewNodes[0];
              const lastNewNode = sortedNewNodes[sortedNewNodes.length - 1];
              
              const reconnectedEdges = [
                  ...remainingEdges,
                  ...newInternalEdges,
                  ...incomingEdges.map(e => ({ ...e, target: firstNewNode.id })),
                  ...outgoingEdges.map(e => ({ ...e, source: lastNewNode.id }))
              ];

              setNodes([...remainingNodes, ...newNodes]);
              setEdges(reconnectedEdges);
              
              setSelectedNodeIds([]);
              setIsRefinerOpen(false);
              setRefinerPrompt('');
          }
      } catch (e) {
          alert("Failed to refine selection.");
      } finally {
          setIsRefiningGraph(false);
      }
  };

  // --- Viewport Handlers (Zoom/Pan) ---
  
  const handleWheel = (e: React.WheelEvent) => {
      if (e.ctrlKey || e.metaKey || e.deltaY !== 0) {
          const zoomSensitivity = 0.001;
          const delta = -e.deltaY * zoomSensitivity;
          const newZoom = Math.min(Math.max(zoom + delta, 0.2), 3);
          
          if (canvasRef.current) {
              const rect = canvasRef.current.getBoundingClientRect();
              const mouseX = e.clientX - rect.left;
              const mouseY = e.clientY - rect.top;
              const worldX = (mouseX - pan.x) / zoom;
              const worldY = (mouseY - pan.y) / zoom;
              const newPanX = mouseX - worldX * newZoom;
              const newPanY = mouseY - worldY * newZoom;
              
              setPan({ x: newPanX, y: newPanY });
              setZoom(newZoom);
          }
      }
  };

  const handleMouseDown = (e: MouseEvent) => {
    if (e.button === 1 || (e.button === 0 && e.altKey)) {
      setIsPanning(true);
      setLastMousePan({ x: e.clientX, y: e.clientY });
      return;
    }
    
    if (e.target === canvasRef.current && !e.shiftKey) {
        setSelectedNodeIds([]);
    }
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (canvasRef.current) {
        const rect = canvasRef.current.getBoundingClientRect();
        setMousePos({
            x: (e.clientX - rect.left - pan.x) / zoom,
            y: (e.clientY - rect.top - pan.y) / zoom
        });
    }

    if (isPanning) {
      const dx = e.clientX - lastMousePan.x;
      const dy = e.clientY - lastMousePan.y;
      setPan(prev => ({ x: prev.x + dx, y: prev.y + dy }));
      setLastMousePan({ x: e.clientX, y: e.clientY });
    }

    if (draggingNodeId) {
       setNodes(prev => prev.map(n => {
         const dx = e.movementX / zoom;
         const dy = e.movementY / zoom;
         
         if (n.id === draggingNodeId) {
             return { ...n, position: { x: n.position.x + dx, y: n.position.y + dy } };
         }
         if (selectedNodeIds.includes(draggingNodeId) && selectedNodeIds.includes(n.id) && n.id !== draggingNodeId) {
             return { ...n, position: { x: n.position.x + dx, y: n.position.y + dy } };
         }
         return n;
       }));
    }
  };

  const handleMouseUp = () => {
    setIsPanning(false);
    setDraggingNodeId(null);
    setConnectingNodeId(null);
  };

  const handleNodeMouseDown = (e: MouseEvent, id: string) => {
      e.stopPropagation();
      setDraggingNodeId(id);
      
      if (e.shiftKey) {
          setSelectedNodeIds(prev => {
              if (prev.includes(id)) return prev.filter(pid => pid !== id);
              return [...prev, id];
          });
      } else {
          if (!selectedNodeIds.includes(id)) {
              setSelectedNodeIds([id]);
          }
      }
  };

  const handleConnectorMouseDown = (e: MouseEvent, id: string) => {
      e.stopPropagation();
      setConnectingNodeId(id);
  };

  const handleConnectorMouseUp = (e: MouseEvent, targetId: string) => {
      e.stopPropagation();
      if (connectingNodeId && connectingNodeId !== targetId) {
          if (!edges.find(edge => edge.source === connectingNodeId && edge.target === targetId)) {
            setEdges([...edges, { id: `${connectingNodeId}-${targetId}`, source: connectingNodeId, target: targetId }]);
          }
      }
      setConnectingNodeId(null);
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault(); 
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    const bibleData = e.dataTransfer.getData('application/json');
    if (bibleData && canvasRef.current) {
      try {
        const item = JSON.parse(bibleData) as BibleItem;
        const rect = canvasRef.current.getBoundingClientRect();
        const dropX = (e.clientX - rect.left - pan.x) / zoom - 150;
        const dropY = (e.clientY - rect.top - pan.y) / zoom - 50;
        
        const formattedContent = formatBibleItemForContext(item);
        addNode('context', formattedContent, item.name, dropX, dropY);
      } catch (err) {
        console.error("Invalid drop data");
      }
    }
  };

  // --- Execution Helpers ---

  const detectCycles = (): boolean => {
      const adjacency = new Map<string, string[]>();
      nodes.forEach(n => adjacency.set(n.id, []));
      edges.forEach(e => {
          if (adjacency.has(e.source)) adjacency.get(e.source)?.push(e.target);
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
  
  const gatherNodeInputs = (targetNodeId: string, currentNodeState: GraphNode[], currentOutputs: Map<string, string>): GraphInput[] => {
      const incomingEdges = edges.filter(e => e.target === targetNodeId);
      const inputs: GraphInput[] = [];

      for (const edge of incomingEdges) {
          const sourceNode = currentNodeState.find(n => n.id === edge.source);
          if (!sourceNode) continue;
          
          let text = "";
          if (currentOutputs.has(edge.source)) {
              text = currentOutputs.get(edge.source) || "";
          } else {
              text = sourceNode.type === 'context' ? sourceNode.data.content : (sourceNode.data.output || "");
          }

          if (text) {
              inputs.push({
                  label: sourceNode.data.label,
                  text: text,
                  type: sourceNode.type
              });
          }
      }
      return inputs;
  };

  const executeFullFlow = async () => {
    if (isFlowRunning) return;
    if (detectCycles()) {
        alert("Cannot run flow: Infinite loop detected! Please check your connections.");
        return;
    }
    setIsFlowRunning(true);
    try {
      const adjacency = new Map<string, string[]>();
      const inDegree = new Map<string, number>();
      nodes.forEach(n => { adjacency.set(n.id, []); inDegree.set(n.id, 0); });
      edges.forEach(e => {
          const current = adjacency.get(e.source) || []; current.push(e.target); adjacency.set(e.source, current); inDegree.set(e.target, (inDegree.get(e.target) || 0) + 1);
      });
      const queue: string[] = [];
      inDegree.forEach((degree, id) => { if (degree === 0) queue.push(id); });
      const executionOrder: string[] = [];
      while (queue.length > 0) {
          const u = queue.shift()!;
          executionOrder.push(u);
          const neighbors = adjacency.get(u) || [];
          for (const v of neighbors) {
              inDegree.set(v, (inDegree.get(v)! - 1));
              if (inDegree.get(v) === 0) { queue.push(v); }
          }
      }
      const nodeOutputs = new Map<string, string>();
      nodes.filter(n => n.type === 'context').forEach(n => nodeOutputs.set(n.id, n.data.content));
      for (const nodeId of executionOrder) {
        const node = nodes.find(n => n.id === nodeId);
        if (!node) continue;
        if (node.type === 'context') continue; 
        updateNodeData(nodeId, { status: 'running' });
        const inputs = gatherNodeInputs(nodeId, nodes, nodeOutputs);
        const result = await runGraphNode(node.data.content, inputs, storyContext, selectedModel, activeStyleProfile);
        nodeOutputs.set(nodeId, result);
        updateNodeData(nodeId, { status: 'completed', output: result });
      }
      if (executionMode === 'final-only') {
          const leafNodes = nodes.filter(n => n.type !== 'context' && !edges.some(e => e.source === n.id));
          const finalTexts = leafNodes.map(n => nodeOutputs.get(n.id)).filter(Boolean);
          if (finalTexts.length > 0) onApplyResult(finalTexts.join('\n\n'));
      } else {
          const sequenceText = executionOrder.map(id => nodes.find(n => n.id === id)).filter(n => n && n.type === 'prompt').map(n => nodeOutputs.get(n!.id)).filter(Boolean).join('\n\n');
          if (sequenceText) onApplyResult(sequenceText);
      }
    } catch (e) { console.error(e); alert("Error executing flow."); } finally { setIsFlowRunning(false); }
  };

  const executeNodeSingle = async (nodeId: string) => {
    const node = nodes.find(n => n.id === nodeId);
    if (!node) return;
    updateNodeData(nodeId, { status: 'running' });
    try {
        const outputsMap = new Map<string, string>();
        nodes.forEach(n => {
             if (n.type === 'context') { outputsMap.set(n.id, n.data.content); } else if (n.data.output) { outputsMap.set(n.id, n.data.output); }
        });
        const inputs = gatherNodeInputs(nodeId, nodes, outputsMap);
        const result = await runGraphNode(node.data.content, inputs, storyContext, selectedModel, activeStyleProfile);
        updateNodeData(nodeId, { status: 'completed', output: result });
    } catch (e) { console.error(e); updateNodeData(nodeId, { status: 'error' }); alert("Node execution failed."); }
  };
  
  const getInspectionData = () => {
      if (!inspectedNodeId) return null;
      const node = nodes.find(n => n.id === inspectedNodeId);
      if (!node) return null;
      const outputsMap = new Map<string, string>();
      nodes.forEach(n => outputsMap.set(n.id, n.data.output || ""));
      const inputs = gatherNodeInputs(inspectedNodeId, nodes, outputsMap);
      const inputsText = inputs.map((input) => {
        const typeLabel = input.type === 'context' ? 'BACKGROUND DATA' : 'PREVIOUS STEP OUTPUT';
        return `--- ${typeLabel} (${input.label}) ---\n${input.text}\n-------------------`;
      }).join("\n\n");
      return { nodeLabel: node.data.label, nodeInstruction: node.data.content, inputsText, storyPreview: storyContext.slice(-500) + "..." };
  };

  const inspectionData = getInspectionData();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] bg-black/90 backdrop-blur-sm flex items-center justify-center">
      <div className="bg-[#0f1014] w-full h-full flex flex-col overflow-hidden relative">
        
        {/* --- Bible Drawer (Left) --- */}
        <div className="absolute top-20 left-4 bottom-20 w-64 bg-[#1a1b26] border border-gray-800 rounded-xl z-40 flex flex-col shadow-2xl overflow-hidden pointer-events-auto">
             <div className="p-3 border-b border-gray-800 bg-gray-900/50 flex flex-col gap-2">
                 <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2"><Book className="w-3 h-3" /> Bible Assets</h3>
                 {/* Category Filters */}
                 <div className="flex gap-1 overflow-x-auto no-scrollbar pb-1">
                     {bibleCategories.map(cat => (
                         <button 
                            key={cat} 
                            onClick={() => setActiveBibleFilter(cat)}
                            className={`text-[10px] whitespace-nowrap px-2 py-0.5 rounded-full border transition-colors ${activeBibleFilter === cat ? 'bg-gray-700 text-white border-gray-500' : 'bg-gray-800/50 text-gray-500 border-transparent hover:text-gray-300'}`}
                         >
                             {getCategoryName(cat)}
                         </button>
                     ))}
                 </div>
             </div>
             <div className="flex-1 overflow-y-auto p-3 space-y-2">
                 {filteredBibleItems.length === 0 ? (<p className="text-xs text-gray-600 text-center mt-10">No items found in this category.</p>) : (
                    filteredBibleItems.map(item => {
                        const schema = bibleSchemas.find(s => s.id === item.schemaId);
                        const schemaName = schema ? schema.name : item.schemaId;
                        return (
                            <div key={item.id} draggable onDragStart={(e) => e.dataTransfer.setData('application/json', JSON.stringify(item))} className="bg-gray-800/50 p-2 rounded border border-gray-700 hover:border-blue-500 cursor-grab active:cursor-grabbing group transition-all">
                                <div className="flex items-center justify-between"><span className="text-sm font-medium text-gray-200">{item.name}</span><span className={`text-[9px] px-1 rounded uppercase ${item.schemaId === 'character' ? 'bg-blue-900 text-blue-300' : item.schemaId === 'location' ? 'bg-green-900 text-green-300' : item.schemaId === 'item' ? 'bg-yellow-900 text-yellow-300' : 'bg-purple-900 text-purple-300'}`}>{schemaName}</span></div>
                                <p className="text-[10px] text-gray-500 mt-1 line-clamp-2">{item.data ? Object.values(item.data)[0] : (item as any).description}</p>
                                <div className="flex gap-1 mt-1">{item.events && item.events.length > 0 && <span className="text-[8px] bg-orange-900/50 text-orange-300 px-1 rounded">Timeline</span>}{item.relationships && item.relationships.length > 0 && <span className="text-[8px] bg-pink-900/50 text-pink-300 px-1 rounded">Relations</span>}</div>
                            </div>
                        );
                    })
                 )}
             </div>
        </div>

        {/* --- Toolbar (Top) --- */}
        <div className="absolute top-4 left-4 right-4 z-50 flex items-center justify-center pointer-events-none">
             <div className="flex gap-2 pointer-events-auto bg-[#1a1b26]/90 p-2 rounded-xl border border-gray-800 shadow-xl backdrop-blur items-center relative">
                <Button variant="ghost" onClick={() => addNode('prompt')} title="Add Prompt Node"><Box className="w-5 h-5 text-blue-400 mr-2" /> Prompt</Button>
                <Button variant="ghost" onClick={() => addNode('context')} title="Add Context Node"><Type className="w-5 h-5 text-green-400 mr-2" /> Context</Button>
                <Button variant="ghost" onClick={() => addNode('logic')} title="Add Logic Node"><Wand2 className="w-5 h-5 text-purple-400 mr-2" /> Logic</Button>
                <div className="w-px h-6 bg-gray-700 mx-2" />
                <Button variant="ghost" onClick={() => setIsAutoBuildOpen(true)} title="Auto-Build Graph"><Sparkles className="w-5 h-5 text-pink-400 mr-2" /> Auto-Build</Button>
                {selectedNodeIds.length > 0 && (<Button variant="ghost" onClick={() => setIsRefinerOpen(true)} title="Enhance selected nodes" className="bg-purple-900/20 text-purple-300 hover:bg-purple-900/40 border border-purple-500/30 animate-in fade-in zoom-in-95"><Wand2 className="w-5 h-5 mr-2" /> Refine Selection ({selectedNodeIds.length})</Button>)}
                <div className="w-px h-6 bg-gray-700 mx-2" />
                <div className="relative"><Button variant="ghost" onClick={() => setIsTemplatesOpen(!isTemplatesOpen)} title="Templates"><FolderOpen className="w-5 h-5 text-yellow-400 mr-2" /> Templates</Button>
                    {isTemplatesOpen && (
                        <div className="absolute top-12 left-0 w-64 bg-[#1a1b26] border border-gray-700 rounded-lg shadow-xl p-3 flex flex-col gap-2 animate-in fade-in zoom-in-95 origin-top-left">
                             <div className="flex gap-2 border-b border-gray-800 pb-2"><input value={templateName} onChange={e => setTemplateName(e.target.value)} placeholder="New Template Name" className="flex-1 bg-black/30 border border-gray-700 rounded text-xs px-2"/><button onClick={handleSaveTemplate} className="p-1 bg-blue-600 rounded hover:bg-blue-500"><Save className="w-3 h-3 text-white"/></button></div>
                             <div className="max-h-40 overflow-y-auto space-y-1">{templates.length === 0 && <p className="text-xs text-gray-500 text-center py-2">No saved templates</p>}{templates.map(t => (<div key={t.id} className="flex justify-between items-center bg-black/20 p-1.5 rounded hover:bg-white/5 group"><span className="text-xs text-gray-300">{t.name}</span><div className="flex gap-1 opacity-0 group-hover:opacity-100"><button onClick={() => handleLoadTemplate(t)} className="text-green-400 hover:text-green-300"><Download className="w-3 h-3"/></button><button onClick={() => onDeleteTemplate(t.id)} className="text-red-400 hover:text-red-300"><Trash2 className="w-3 h-3"/></button></div></div>))}</div>
                        </div>
                    )}
                </div>
                <div className="w-px h-6 bg-gray-700 mx-2" />
                <div className="flex bg-black/40 rounded-lg p-0.5 border border-gray-700">
                    <button onClick={() => setExecutionMode('final-only')} className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all flex items-center gap-2 ${executionMode === 'final-only' ? 'bg-gray-700 text-white shadow-sm' : 'text-gray-400 hover:text-gray-200'}`}><ArrowRightToLine className="w-3 h-3" /> Final Only</button>
                    <button onClick={() => setExecutionMode('sequence')} className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all flex items-center gap-2 ${executionMode === 'sequence' ? 'bg-gray-700 text-white shadow-sm' : 'text-gray-400 hover:text-gray-200'}`}><Layers className="w-3 h-3" /> Sequence</button>
                </div>
                <div className="w-px h-6 bg-gray-700 mx-2" />
                <Button onClick={executeFullFlow} disabled={isFlowRunning} className={`bg-green-600 hover:bg-green-500 text-white border-none shadow-[0_0_15px_rgba(34,197,94,0.3)] transition-all ${isFlowRunning ? 'opacity-50' : ''}`}>{isFlowRunning ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Zap className="w-4 h-4 mr-2 fill-current" />}{executionMode === 'final-only' ? 'Run & Write Final' : 'Run & Write All'}</Button>
             </div>
        </div>

        {/* --- Zoom Controls (Bottom Right) --- */}
        <div className="absolute bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-auto">
             <div className="bg-[#1a1b26]/90 p-1.5 rounded-lg border border-gray-800 shadow-xl backdrop-blur flex flex-col gap-1">
                 <button onClick={() => setZoom(Math.min(zoom + 0.1, 3))} className="p-2 hover:bg-gray-700 rounded text-gray-300"><ZoomIn className="w-4 h-4"/></button>
                 <button onClick={() => setZoom(Math.max(zoom - 0.1, 0.2))} className="p-2 hover:bg-gray-700 rounded text-gray-300"><ZoomOut className="w-4 h-4"/></button>
                 <button onClick={() => { setZoom(1); setPan({x:0, y:0}); }} className="p-2 hover:bg-gray-700 rounded text-gray-300"><Maximize className="w-4 h-4"/></button>
                 <div className="text-[9px] text-center text-gray-500 border-t border-gray-700 pt-1 mt-1">{Math.round(zoom * 100)}%</div>
             </div>
        </div>

        {/* --- Style Indicator (Top Right) --- */}
        {activeStyleProfile && (<div className="absolute top-4 right-20 z-50 bg-[#1a1b26]/90 p-2 rounded-lg border border-purple-500/30 flex items-center gap-2 shadow-lg backdrop-blur"><Palette className="w-4 h-4 text-purple-400" /><div className="flex flex-col"><span className="text-[10px] text-gray-500 uppercase">Style Active</span><span className="text-xs font-bold text-white">{activeStyleProfile.name}</span></div></div>)}

        <div className="absolute top-4 right-4 z-50 pointer-events-auto"><button onClick={onClose} className="bg-[#1a1b26]/90 p-3 rounded-full hover:bg-red-500/20 text-white border border-gray-800 transition-all"><X className="w-6 h-6" /></button></div>

        {/* Canvas */}
        <div ref={canvasRef} className="flex-1 w-full h-full cursor-grab active:cursor-grabbing overflow-hidden relative bg-[#0f1014]" onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onWheel={handleWheel} onDragOver={handleDragOver} onDrop={handleDrop}>
            <div className="absolute inset-0 pointer-events-none opacity-20" style={{ backgroundImage: 'radial-gradient(circle, #333 1px, transparent 1px)', backgroundSize: `${20 * zoom}px ${20 * zoom}px`, backgroundPosition: `${pan.x}px ${pan.y}px` }}/>
            <div style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, transformOrigin: '0 0' }} className="w-full h-full absolute inset-0">
                <svg className="overflow-visible absolute inset-0 w-full h-full pointer-events-none">
                    <defs><marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill="#4B5563" /></marker></defs>
                    {edges.map(edge => {
                        const sourceNode = nodes.find(n => n.id === edge.source);
                        const targetNode = nodes.find(n => n.id === edge.target);
                        if (!sourceNode || !targetNode) return null;
                        const sx = sourceNode.position.x + (sourceNode.width || 300);
                        const sy = sourceNode.position.y + 50; 
                        const tx = targetNode.position.x;
                        const ty = targetNode.position.y + 50;
                        const selected = selectedNodeIds.includes(edge.source) && selectedNodeIds.includes(edge.target);
                        return (<path key={edge.id} d={`M ${sx} ${sy} C ${sx + 50} ${sy}, ${tx - 50} ${ty}, ${tx} ${ty}`} stroke={selected ? '#8b5cf6' : '#4B5563'} strokeWidth={selected ? "3" : "2"} fill="none" markerEnd="url(#arrowhead)" style={{ transition: 'stroke 0.2s' }}/>);
                    })}
                    {connectingNodeId && mousePos && (() => {
                         const sourceNode = nodes.find(n => n.id === connectingNodeId);
                         if (sourceNode) {
                            const sx = sourceNode.position.x + (sourceNode.width || 300);
                            const sy = sourceNode.position.y + 50;
                            return (<path d={`M ${sx} ${sy} C ${sx + 50} ${sy}, ${mousePos.x - 50} ${mousePos.y}, ${mousePos.x} ${mousePos.y}`} stroke="#60A5FA" strokeWidth="2" strokeDasharray="5,5" fill="none" />)
                         }
                         return null;
                    })()}
                </svg>

                {/* Render Nodes */}
                {nodes.map(node => (
                    <div key={node.id} style={{ transform: `translate(${node.position.x}px, ${node.position.y}px)` }} className={`absolute w-[300px] rounded-lg shadow-lg border backdrop-blur-sm transition-shadow group ${node.type === 'prompt' ? 'bg-blue-950/40 border-blue-500/30' : node.type === 'context' ? 'bg-green-950/40 border-green-500/30' : 'bg-purple-950/40 border-purple-500/30'} ${selectedNodeIds.includes(node.id) ? 'ring-2 ring-white shadow-xl scale-[1.01]' : 'hover:border-opacity-100'} ${node.data.status === 'running' ? 'ring-2 ring-yellow-400 animate-pulse' : ''}`} onMouseDown={(e) => handleNodeMouseDown(e, node.id)}>
                         {/* Header */}
                         <div className={`p-2 border-b flex items-center justify-between ${node.type === 'prompt' ? 'border-blue-500/20 bg-blue-900/20' : node.type === 'context' ? 'border-green-500/20 bg-green-900/20' : 'border-purple-500/20 bg-purple-900/20'} rounded-t-lg`}>
                             <div className="flex items-center gap-2">
                                 {node.type === 'prompt' ? <Box className="w-4 h-4 text-blue-400"/> : node.type === 'context' ? <Type className="w-4 h-4 text-green-400"/> : <Wand2 className="w-4 h-4 text-purple-400"/>}
                                 <input value={node.data.label} onChange={(e) => updateNodeData(node.id, { label: e.target.value })} className="bg-transparent text-xs font-bold text-gray-200 focus:outline-none w-32"/>
                             </div>
                             <div className="flex gap-1">
                                 {/* Save Context to Bible */}
                                 {node.type === 'context' && (
                                     <button onClick={(e) => { e.stopPropagation(); onPromoteNode(node.data.label, node.data.content); }} className="p-1 text-green-400 hover:text-white rounded hover:bg-green-900/40 transition-colors" title="Save to World Bible">
                                         <Save className="w-3 h-3"/>
                                     </button>
                                 )}
                                 {node.type === 'prompt' && (<button onClick={(e) => { e.stopPropagation(); setWandNodeId(node.id); }} className="p-1 text-purple-400 hover:text-white rounded hover:bg-purple-900/40 transition-colors" title="AI Auto-Write Instruction"><Sparkles className="w-3 h-3"/></button>)}
                                 {node.type !== 'context' && (<button onClick={(e) => { e.stopPropagation(); executeNodeSingle(node.id); }} className="p-1 text-green-400 hover:text-white" title="Execute Only This Node"><Play className="w-3 h-3"/></button>)}
                                 <button onClick={(e) => { e.stopPropagation(); deleteNode(node.id); }} className="p-1 text-gray-500 hover:text-red-400"><Trash2 className="w-3 h-3"/></button>
                             </div>
                         </div>
                         <div className="p-3 relative">
                             <textarea value={node.data.content} onChange={(e) => updateNodeData(node.id, { content: e.target.value })} placeholder={node.type === 'prompt' ? 'Instructions for AI...' : 'Context Data...'} className="w-full bg-black/20 rounded border border-gray-700/50 p-2 text-xs text-gray-300 resize-y min-h-[80px] focus:border-gray-500 outline-none" onMouseDown={(e) => e.stopPropagation()} />
                             {node.data.output && (<div className="mt-2 pt-2 border-t border-gray-700/30"><div className="flex justify-between items-center mb-1"><span className="text-[9px] font-bold text-green-400 uppercase">Generated Output</span><button onClick={(e) => { e.stopPropagation(); onApplyResult(node.data.output!); }} title="Insert to Editor" className="text-gray-500 hover:text-white"><Download className="w-3 h-3"/></button></div><div className="text-[10px] text-gray-400 line-clamp-3 bg-black/40 p-1.5 rounded font-mono">{node.data.output}</div></div>)}
                             <div className="absolute -bottom-3 right-2 flex gap-1">{node.data.status === 'completed' && <CheckCircle2 className="w-5 h-5 text-green-500 bg-black rounded-full"/>}{node.data.status === 'error' && <AlertTriangle className="w-5 h-5 text-red-500 bg-black rounded-full"/>}</div>
                             <div className="absolute -bottom-3 left-2"><button onClick={(e) => { e.stopPropagation(); setInspectedNodeId(node.id); }} className="bg-gray-800 text-gray-400 p-1 rounded-full border border-gray-600 hover:text-white hover:border-white transition-colors" title="Inspect Inputs"><Eye className="w-3 h-3" /></button></div>
                         </div>
                         <div className="absolute left-0 top-1/2 -translate-x-1/2 w-3 h-3 bg-gray-400 rounded-full border border-gray-900 cursor-crosshair hover:bg-white transition-colors" onMouseUp={(e) => handleConnectorMouseUp(e, node.id)}/>
                         <div className="absolute right-0 top-1/2 translate-x-1/2 w-3 h-3 bg-gray-400 rounded-full border border-gray-900 cursor-crosshair hover:bg-white transition-colors" onMouseDown={(e) => handleConnectorMouseDown(e, node.id)}/>
                    </div>
                ))}
            </div>
        </div>
      </div>
      
      {/* --- MODALS --- */}
      {/* 1. Wand Modal */}
      {wandNodeId && (<div className="absolute inset-0 bg-black/80 flex items-center justify-center z-[60] backdrop-blur-sm animate-in fade-in"><div className="bg-gray-900 border border-purple-500/50 p-6 rounded-xl w-96 shadow-2xl relative"><h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2"><Sparkles className="w-5 h-5 text-purple-400"/> Magic Prompt Writer</h3><p className="text-sm text-gray-400 mb-4">Describe your goal for this step. The AI will read the connected inputs and write a detailed instruction for you.</p><textarea value={wandSeed} onChange={e => setWandSeed(e.target.value)} placeholder="e.g. A tense dialogue where they discuss the artifact..." className="w-full bg-black/30 border border-gray-700 rounded p-3 text-sm text-white h-32 mb-4"/><div className="flex justify-end gap-2"><Button variant="ghost" onClick={() => setWandNodeId(null)}>Cancel</Button><Button onClick={handleWandGenerate} disabled={!wandSeed || isWandGenerating} className="bg-purple-600 hover:bg-purple-500">{isWandGenerating ? <Loader2 className="w-4 h-4 animate-spin mr-2"/> : <Wand2 className="w-4 h-4 mr-2"/>} Generate Instruction</Button></div></div></div>)}

      {/* 2. Auto-Build Modal */}
      {isAutoBuildOpen && (<div className="absolute inset-0 bg-black/80 flex items-center justify-center z-[60] backdrop-blur-sm animate-in fade-in"><div className="bg-gray-900 border border-pink-500/50 p-6 rounded-xl w-[500px] shadow-2xl relative"><h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2"><Sparkles className="w-5 h-5 text-pink-400"/> Auto-Build Workflow</h3><p className="text-sm text-gray-400 mb-4">Describe the flow you want. The AI will generate nodes, connections, and instructions automatically, using your World Bible context.</p><div className="flex gap-2 mb-4 bg-black/30 p-1 rounded-lg"><button onClick={() => setAutoBuildMode('sequence')} className={`flex-1 py-2 text-xs rounded-md transition-colors ${autoBuildMode === 'sequence' ? 'bg-pink-600 text-white' : 'text-gray-400 hover:text-white'}`}>Sequence (Scene A → Scene B)</button><button onClick={() => setAutoBuildMode('final-only')} className={`flex-1 py-2 text-xs rounded-md transition-colors ${autoBuildMode === 'final-only' ? 'bg-pink-600 text-white' : 'text-gray-400 hover:text-white'}`}>Refinement (Draft → Polish)</button></div><textarea value={autoBuildPrompt} onChange={e => setAutoBuildPrompt(e.target.value)} placeholder="e.g. A scene where Vex investigates the derelict ship and gets ambushed..." className="w-full bg-black/30 border border-gray-700 rounded p-3 text-sm text-white h-32 mb-4"/><div className="flex justify-end gap-2"><Button variant="ghost" onClick={() => setIsAutoBuildOpen(false)}>Cancel</Button><Button onClick={handleAutoBuildGraph} disabled={!autoBuildPrompt || isBuildingGraph} className="bg-pink-600 hover:bg-pink-500">{isBuildingGraph ? <Loader2 className="w-4 h-4 animate-spin mr-2"/> : <Zap className="w-4 h-4 mr-2"/>} Build Graph</Button></div></div></div>)}

      {/* 3. Refiner Modal */}
      {isRefinerOpen && (<div className="absolute inset-0 bg-black/80 flex items-center justify-center z-[60] backdrop-blur-sm animate-in fade-in"><div className="bg-gray-900 border border-purple-500/50 p-6 rounded-xl w-[500px] shadow-2xl relative"><h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2"><Wand2 className="w-5 h-5 text-purple-400"/> Refine Selection</h3><p className="text-sm text-gray-400 mb-4">How should the AI modify the {selectedNodeIds.length} selected nodes? It can split them, merge them, or add logic checks.</p><textarea value={refinerPrompt} onChange={e => setRefinerPrompt(e.target.value)} placeholder="e.g. Break this interaction into 3 beats and add a tension check in the middle..." className="w-full bg-black/30 border border-gray-700 rounded p-3 text-sm text-white h-32 mb-4"/><div className="flex justify-end gap-2"><Button variant="ghost" onClick={() => setIsRefinerOpen(false)}>Cancel</Button><Button onClick={handleRefineGraph} disabled={!refinerPrompt || isRefiningGraph} className="bg-purple-600 hover:bg-purple-500">{isRefiningGraph ? <Loader2 className="w-4 h-4 animate-spin mr-2"/> : <Sparkles className="w-4 h-4 mr-2"/>} Enhance Flow</Button></div></div></div>)}

      {/* 4. Inspector Modal */}
      {inspectionData && (<div className="absolute inset-0 bg-black/80 flex items-center justify-center z-[70] backdrop-blur-sm animate-in zoom-in-95" onClick={() => setInspectedNodeId(null)}><div className="bg-[#1a1b26] border border-gray-700 p-6 rounded-xl w-[800px] max-h-[80vh] shadow-2xl relative overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}><div className="flex justify-between items-center mb-4 border-b border-gray-800 pb-2"><h3 className="text-xl font-bold text-white flex items-center gap-2"><Eye className="w-5 h-5 text-blue-400"/> Node Inspector: <span className="text-blue-200">{inspectionData.nodeLabel}</span></h3><button onClick={() => setInspectedNodeId(null)} className="text-gray-500 hover:text-white"><X className="w-5 h-5"/></button></div><div className="flex-1 overflow-y-auto space-y-4 pr-2"><div className="grid grid-cols-2 gap-4"><div className="space-y-2"><label className="text-xs font-bold text-gray-500 uppercase">Compiled Inputs (What AI Sees)</label><div className="bg-black/30 p-3 rounded border border-gray-700 text-xs text-gray-300 font-mono h-64 overflow-y-auto whitespace-pre-wrap">{inspectionData.inputsText || "No inputs connected."}</div></div><div className="space-y-2"><label className="text-xs font-bold text-gray-500 uppercase">Global Story Context (Last 500 chars)</label><div className="bg-black/30 p-3 rounded border border-gray-700 text-xs text-gray-300 font-serif h-64 overflow-y-auto italic">"{inspectionData.storyPreview}"</div></div></div><div className="space-y-2"><label className="text-xs font-bold text-gray-500 uppercase">Node Instruction</label><div className="bg-blue-900/10 p-3 rounded border border-blue-500/20 text-sm text-blue-100">{inspectionData.nodeInstruction}</div></div></div></div></div>)}
    </div>
  );
};

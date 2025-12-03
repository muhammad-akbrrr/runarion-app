
import React, { useState, useMemo } from 'react';
import { BibleItem, BibleRelationship } from '../types';
import { X, Users, Network, Grid as GridIcon, Filter, ZoomIn, ZoomOut, Activity, Globe } from 'lucide-react';
import { Button } from './Button';

interface RelationshipMatrixProps {
  isOpen: boolean;
  onClose: () => void;
  bibleItems: BibleItem[];
}

export const RelationshipMatrix: React.FC<RelationshipMatrixProps> = ({
  isOpen,
  onClose,
  bibleItems,
}) => {
  const [viewMode, setViewMode] = useState<'graph' | 'grid' | 'global'>('global');
  const [selectedCharId, setSelectedCharId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);

  // Get only items that are typically actors (Characters/Factions)
  const actors = useMemo(() => 
    bibleItems.filter(i => i.schemaId === 'character' || i.schemaId === 'faction' || i.relationships?.length),
  [bibleItems]);

  // Build a complete edge list for the graph
  const relationships = useMemo(() => {
    const rels: { source: string, targetName: string, type: string, desc: string, affinity: number }[] = [];
    actors.forEach(actor => {
        if (actor.relationships) {
            actor.relationships.forEach(r => {
                rels.push({
                    source: actor.id,
                    targetName: r.targetName,
                    type: r.type,
                    desc: r.description,
                    affinity: r.affinityScore || 0
                });
            });
        }
    });
    return rels;
  }, [actors]);

  const selectedActor = actors.find(a => a.id === selectedCharId) || actors[0];

  if (!isOpen) return null;

  // Helper to render Affinity Bar
  const renderAffinityBar = (score: number) => {
      // score -100 to 100
      // normalize to 0-100%
      const percent = ((score + 100) / 200) * 100;
      let colorClass = 'bg-gray-500';
      if (score < -30) colorClass = 'bg-red-500';
      else if (score > 30) colorClass = 'bg-green-500';
      else colorClass = 'bg-yellow-500';

      return (
          <div className="w-full h-2 bg-gray-800 rounded-full mt-2 relative overflow-hidden group">
              <div className={`h-full ${colorClass} transition-all duration-500`} style={{ width: `${percent}%` }} />
              <div className="absolute inset-0 flex items-center justify-center text-[8px] font-bold text-white drop-shadow opacity-0 group-hover:opacity-100 transition-opacity">
                  {score}
              </div>
          </div>
      );
  };

  return (
    <div className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-md flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-800 bg-[#1a1b26]">
        <div className="flex items-center gap-4">
            <h2 className="text-xl font-serif text-white flex items-center gap-2">
                <Users className="w-6 h-6 text-pink-400"/> Relationship Matrix
            </h2>
            <div className="flex bg-gray-900 rounded-lg p-1 border border-gray-700">
                 <button 
                    onClick={() => { setViewMode('global'); setSelectedCharId(null); }}
                    className={`px-3 py-1 text-xs rounded-md flex items-center gap-2 transition-colors ${viewMode === 'global' ? 'bg-pink-600 text-white' : 'text-gray-400 hover:text-white'}`}
                >
                    <Globe className="w-3 h-3"/> Constellation
                </button>
                <button 
                    onClick={() => setViewMode('graph')}
                    className={`px-3 py-1 text-xs rounded-md flex items-center gap-2 transition-colors ${viewMode === 'graph' ? 'bg-pink-600 text-white' : 'text-gray-400 hover:text-white'}`}
                >
                    <Network className="w-3 h-3"/> Focused
                </button>
                <button 
                    onClick={() => setViewMode('grid')}
                    className={`px-3 py-1 text-xs rounded-md flex items-center gap-2 transition-colors ${viewMode === 'grid' ? 'bg-pink-600 text-white' : 'text-gray-400 hover:text-white'}`}
                >
                    <GridIcon className="w-3 h-3"/> Grid
                </button>
            </div>
        </div>
        <button onClick={onClose} className="p-2 hover:bg-gray-800 rounded-full text-gray-400 hover:text-white transition-colors">
            <X className="w-6 h-6"/>
        </button>
      </div>

      <div className="flex-1 flex overflow-hidden">
         {/* Sidebar List (Hidden in Global unless we want details) */}
         <div className="w-64 bg-gray-900 border-r border-gray-800 p-4 overflow-y-auto">
             <h3 className="text-xs font-bold text-gray-500 uppercase mb-3">Entities ({actors.length})</h3>
             
             {/* New explicit button to return to global view */}
             <button
                onClick={() => { setSelectedCharId(null); setViewMode('global'); }}
                className={`w-full text-left px-3 py-2 rounded text-sm mb-2 transition-colors font-bold ${viewMode === 'global' ? 'bg-pink-900/60 text-pink-100' : 'bg-gray-800/50 text-gray-400 hover:text-white'}`}
             >
                <Globe className="w-3 h-3 inline mr-2"/> Show All / Global
             </button>

             <div className="space-y-1">
                 {actors.map(actor => (
                     <button
                        key={actor.id}
                        onClick={() => { setSelectedCharId(actor.id); if(viewMode === 'global') setViewMode('graph'); }}
                        className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${selectedCharId === actor.id ? 'bg-pink-900/40 text-pink-200 border border-pink-500/30' : 'text-gray-400 hover:bg-gray-800 hover:text-white'}`}
                     >
                         {actor.name}
                     </button>
                 ))}
             </div>
         </div>

         {/* Main View */}
         <div className="flex-1 bg-[#0f1014] relative overflow-hidden flex items-center justify-center">
             
             {viewMode === 'global' && (
                  <div className="w-full h-full relative" style={{ transform: `scale(${zoom})`, transformOrigin: 'center' }}>
                      <svg className="absolute inset-0 w-full h-full pointer-events-none">
                         {/* Draw ALL connections */}
                         {relationships.map((rel, idx) => {
                             const sourceIdx = actors.findIndex(a => a.id === rel.source);
                             const targetIdx = actors.findIndex(a => a.name === rel.targetName);
                             if (sourceIdx === -1 || targetIdx === -1) return null;

                             // Simple circular layout logic
                             const radius = 350;
                             const cx = window.innerWidth / 2 - 128;
                             const cy = window.innerHeight / 2 - 32;
                             
                             const angle1 = (sourceIdx / actors.length) * 2 * Math.PI;
                             const x1 = cx + Math.cos(angle1) * radius;
                             const y1 = cy + Math.sin(angle1) * radius;

                             const angle2 = (targetIdx / actors.length) * 2 * Math.PI;
                             const x2 = cx + Math.cos(angle2) * radius;
                             const y2 = cy + Math.sin(angle2) * radius;

                             let strokeColor = '#6b7280'; // gray
                             if (rel.affinity > 20) strokeColor = '#22c55e'; // green
                             if (rel.affinity < -20) strokeColor = '#ef4444'; // red

                             return (
                                 <line 
                                    key={idx}
                                    x1={x1} y1={y1} 
                                    x2={x2} y2={y2} 
                                    stroke={strokeColor} 
                                    strokeWidth={Math.abs(rel.affinity)/20 + 0.5} 
                                    strokeOpacity="0.4"
                                 />
                             )
                         })}
                      </svg>
                      {/* Render Nodes in Circle */}
                      {actors.map((actor, idx) => {
                           const radius = 350;
                           const cx = (window.innerWidth - 256) / 2;
                           const cy = (window.innerHeight - 64) / 2;
                           const angle = (idx / actors.length) * 2 * Math.PI;
                           const x = cx + Math.cos(angle) * radius;
                           const y = cy + Math.sin(angle) * radius;

                           return (
                               <div 
                                    key={actor.id} 
                                    className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group"
                                    style={{ left: x, top: y }}
                                    onClick={() => { setSelectedCharId(actor.id); setViewMode('graph'); }}
                               >
                                   <div className="w-3 h-3 bg-pink-500 rounded-full shadow-[0_0_10px_rgba(236,72,153,0.8)] group-hover:scale-150 transition-transform"/>
                                   <div className="absolute top-4 left-1/2 -translate-x-1/2 text-[10px] text-gray-400 font-bold whitespace-nowrap bg-black/50 px-1 rounded">{actor.name}</div>
                               </div>
                           )
                      })}
                  </div>
             )}

             {viewMode === 'graph' && selectedActor ? (
                 <div className="w-full h-full relative" style={{ transform: `scale(${zoom})`, transformOrigin: 'center' }}>
                     {/* Hub and Spoke Visualizer */}
                     <svg className="absolute inset-0 w-full h-full pointer-events-none">
                         <defs>
                            <marker id="rel-arrow" markerWidth="10" markerHeight="7" refX="28" refY="3.5" orient="auto">
                                <polygon points="0 0, 10 3.5, 0 7" fill="#ec4899" />
                            </marker>
                         </defs>
                         
                         {/* Draw Lines */}
                         {(selectedActor.relationships || []).map((rel, idx) => {
                             const angle = (idx / (selectedActor.relationships?.length || 1)) * 2 * Math.PI;
                             const radius = 300;
                             const centerX = window.innerWidth / 2 - 128; // adjusting for sidebar
                             const centerY = window.innerHeight / 2 - 32;
                             
                             const tx = centerX + Math.cos(angle) * radius;
                             const ty = centerY + Math.sin(angle) * radius;

                             return (
                                 <g key={idx}>
                                     <line 
                                        x1={centerX} y1={centerY} 
                                        x2={tx} y2={ty} 
                                        stroke="#ec4899" 
                                        strokeWidth="1" 
                                        strokeOpacity="0.5"
                                        markerEnd="url(#rel-arrow)"
                                     />
                                     {/* Label on line */}
                                     <text x={(centerX + tx)/2} y={(centerY + ty)/2} fill="#ec4899" fontSize="10" textAnchor="middle" dy="-5" className="bg-black">
                                         {rel.type} ({rel.affinityScore || 0})
                                     </text>
                                 </g>
                             )
                         })}
                     </svg>

                     {/* Center Node (Selected) */}
                     <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 rounded-full bg-pink-900/20 border-2 border-pink-500 flex items-center justify-center text-center p-2 shadow-[0_0_30px_rgba(236,72,153,0.3)] z-10">
                         <div>
                            <div className="text-lg font-bold text-white">{selectedActor.name}</div>
                            <div className="text-[10px] text-pink-300 uppercase">{selectedActor.schemaId}</div>
                         </div>
                     </div>

                     {/* Surrounding Nodes */}
                     {(selectedActor.relationships || []).map((rel, idx) => {
                             const angle = (idx / (selectedActor.relationships?.length || 1)) * 2 * Math.PI;
                             const radius = 300;
                             // Hardcoded center approximation for demo
                             const centerX = (window.innerWidth - 256) / 2; 
                             const centerY = (window.innerHeight - 64) / 2;
                             
                             const tx = centerX + Math.cos(angle) * radius;
                             const ty = centerY + Math.sin(angle) * radius;

                             return (
                                 <div 
                                    key={idx}
                                    style={{ left: tx, top: ty }}
                                    className="absolute -translate-x-1/2 -translate-y-1/2 w-56 bg-gray-800/80 border border-gray-600 p-3 rounded-lg backdrop-blur text-sm shadow-xl z-20 group"
                                 >
                                     <div className="flex justify-between items-start mb-1">
                                         <div className="font-bold text-white">{rel.targetName}</div>
                                         <div className="text-[10px] uppercase font-bold text-pink-400">{rel.type}</div>
                                     </div>
                                     
                                     {renderAffinityBar(rel.affinityScore || 0)}
                                     
                                     <p className="text-xs text-gray-300 line-clamp-2 italic mt-2">"{rel.description}"</p>
                                     
                                     {/* Hover History Popover */}
                                     {rel.modifiers && rel.modifiers.length > 0 && (
                                         <div className="hidden group-hover:block absolute top-full left-0 w-full bg-black border border-gray-700 p-2 rounded mt-1 z-30">
                                             <div className="text-[9px] font-bold text-gray-400 uppercase mb-1">Affinity History</div>
                                             {rel.modifiers.map((mod, i) => (
                                                 <div key={i} className="flex justify-between text-[9px] text-gray-300 border-b border-gray-800 pb-1 mb-1 last:border-0">
                                                     <span>{mod.reason}</span>
                                                     <span className={mod.value > 0 ? 'text-green-400' : 'text-red-400'}>{mod.value > 0 ? '+' : ''}{mod.value}</span>
                                                 </div>
                                             ))}
                                         </div>
                                     )}
                                 </div>
                             )
                     })}
                 </div>
             ) : viewMode === 'graph' && !selectedActor ? (
                 <div className="text-gray-500">Select an entity to view their network</div>
             ) : (
                 // GRID VIEW
                 <div className="w-full h-full overflow-auto p-8">
                     <table className="w-full text-left border-collapse">
                         <thead>
                             <tr>
                                 <th className="p-3 border-b border-gray-700 text-gray-400 text-xs uppercase">Entity</th>
                                 <th className="p-3 border-b border-gray-700 text-gray-400 text-xs uppercase">Target</th>
                                 <th className="p-3 border-b border-gray-700 text-gray-400 text-xs uppercase">Type</th>
                                 <th className="p-3 border-b border-gray-700 text-gray-400 text-xs uppercase">Affinity</th>
                                 <th className="p-3 border-b border-gray-700 text-gray-400 text-xs uppercase">Details</th>
                             </tr>
                         </thead>
                         <tbody>
                             {relationships.map((rel, idx) => {
                                 const sourceName = actors.find(a => a.id === rel.source)?.name || 'Unknown';
                                 // Simple filtering
                                 if (selectedCharId && rel.source !== selectedCharId && rel.targetName !== actors.find(a=>a.id === selectedCharId)?.name) return null;

                                 return (
                                     <tr key={idx} className="hover:bg-gray-800/30 border-b border-gray-800/50">
                                         <td className="p-3 text-sm text-white font-medium">{sourceName}</td>
                                         <td className="p-3 text-sm text-gray-300">{rel.targetName}</td>
                                         <td className="p-3">
                                             <span className="px-2 py-0.5 rounded-full bg-pink-900/30 text-pink-300 text-xs border border-pink-500/20">
                                                 {rel.type}
                                             </span>
                                         </td>
                                         <td className="p-3 w-32">
                                             {renderAffinityBar(rel.affinity)}
                                         </td>
                                         <td className="p-3 text-sm text-gray-400 italic">{rel.desc}</td>
                                     </tr>
                                 )
                             })}
                         </tbody>
                     </table>
                 </div>
             )}

             {/* Zoom Controls for Graph */}
             {viewMode !== 'grid' && (
                 <div className="absolute bottom-8 right-8 flex gap-2">
                     <button onClick={() => setZoom(Math.max(0.5, zoom - 0.1))} className="p-2 bg-gray-800 rounded-full hover:bg-gray-700 text-white"><ZoomOut className="w-4 h-4"/></button>
                     <button onClick={() => setZoom(1)} className="px-3 bg-gray-800 rounded-full hover:bg-gray-700 text-xs text-white">Reset</button>
                     <button onClick={() => setZoom(Math.min(2, zoom + 0.1))} className="p-2 bg-gray-800 rounded-full hover:bg-gray-700 text-white"><ZoomIn className="w-4 h-4"/></button>
                 </div>
             )}
         </div>
      </div>
    </div>
  );
};

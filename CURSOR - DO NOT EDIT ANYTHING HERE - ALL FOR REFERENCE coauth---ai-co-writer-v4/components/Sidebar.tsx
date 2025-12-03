

import React, { useState, useMemo, useEffect } from 'react';
import { Sparkles, PenTool, X, Settings2, Network, Book, Palette, Plus, Trash2, ChevronRight, Loader2, ListPlus, Edit2, Wand2, Save, Ban, Search, Check, AlertCircle, History, Users2, ShieldAlert, ArrowRight, Upload, Download, ScanSearch, CheckCheck, RotateCcw, StopCircle, MessageSquareText, FileText, AlignLeft, Type, Quote, PenLine, HelpCircle, Printer, BrainCircuit } from 'lucide-react';
import { Button } from './Button';
import { ModelType, BibleItem, StyleProfile, BibleSchema, BibleField, LoreSuggestion, EditorIssue, ScanFocus, AdvisorMessage, EditorScanMode } from '../types';
import { extractStyleDNA, generateBibleAttributes, refineStyleInstruction, suggestNegativeConstraints, scanForNewLore, runEditorScan, assessNaturalness } from '../services/geminiService';
import { AdvisorChat } from './AdvisorChat';
import { findBestMatch } from '../utils';

interface SidebarProps {
  instruction: string;
  setInstruction: (val: string) => void;
  negativeInstruction?: string;
  setNegativeInstruction?: (val: string) => void;

  onGenerate: () => void;
  isGenerating: boolean;
  wordCount: number;
  isOpen: boolean;
  onToggle: () => void;
  selectedModel: ModelType;
  onSelectModel: (model: ModelType) => void;
  onOpenChainBuilder: () => void;
  onOpenRelationshipMatrix: () => void;
  onOpenBookPreview: () => void;
  
  // LIVE Content Prop
  storyContent: string;
  onUpdateContent?: (text: string) => void;

  // Bible Props
  bibleItems: BibleItem[];
  bibleSchemas: BibleSchema[];
  onAddBibleItem: (item: BibleItem) => void;
  onUpdateBibleItem: (item: BibleItem) => void;
  onDeleteBibleItem: (id: string) => void;
  onAddSchema: (schema: BibleSchema) => void;
  
  prefillItem?: { name: string, description: string } | null;
  onClearPrefill?: () => void;

  // Style Props
  styles: StyleProfile[];
  activeStyleId: string | null;
  onAddStyle: (style: StyleProfile) => void;
  onUpdateStyle: (style: StyleProfile) => void;
  onDeleteStyle: (id: string) => void;
  onSelectStyle: (id: string | null) => void;

  // Project Management
  onResetProject: () => void;
  
  // Advisor Props
  advisorHistory: AdvisorMessage[];
  setAdvisorHistory: React.Dispatch<React.SetStateAction<AdvisorMessage[]>>;

  // Audit Props
  auditResults: EditorIssue[];
  setAuditResults: React.Dispatch<React.SetStateAction<EditorIssue[]>>;
}

type Tab = 'write' | 'bible' | 'styles' | 'advisor' | 'publish';
type AuditScope = 'full' | 'chapter' | 'chunked';

export const Sidebar: React.FC<SidebarProps> = ({
  instruction,
  setInstruction,
  negativeInstruction = '',
  setNegativeInstruction,
  onGenerate,
  isGenerating,
  wordCount,
  isOpen,
  onToggle,
  selectedModel,
  onSelectModel,
  onOpenChainBuilder,
  onOpenRelationshipMatrix,
  onOpenBookPreview,
  storyContent,
  onUpdateContent,
  bibleItems,
  bibleSchemas,
  onAddBibleItem,
  onUpdateBibleItem,
  onDeleteBibleItem,
  onAddSchema,
  prefillItem,
  onClearPrefill,
  styles,
  activeStyleId,
  onAddStyle,
  onUpdateStyle,
  onDeleteStyle,
  onSelectStyle,
  onResetProject,
  advisorHistory,
  setAdvisorHistory,
  auditResults,
  setAuditResults
}) => {
  const [activeTab, setActiveTab] = useState<Tab>('write');
  
  // --- Bible Form State ---
  const [isAddingBible, setIsAddingBible] = useState(false);
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [selectedSchemaId, setSelectedSchemaId] = useState<string>('character');
  const [newItemName, setNewItemName] = useState('');
  const [newItemData, setNewItemData] = useState<Record<string, string>>({});
  
  // Entity Evolution State
  const [bibleViewMode, setBibleViewMode] = useState<'data' | 'events' | 'relations'>('data');
  const [newItemEvents, setNewItemEvents] = useState<any[]>([]);
  const [newItemRelations, setNewItemRelations] = useState<any[]>([]);

  // Bible Search State
  const [searchQuery, setSearchQuery] = useState('');

  // --- Auto Gen State ---
  const [autoGenSeed, setAutoGenSeed] = useState('');
  const [isAutoGenerating, setIsAutoGenerating] = useState(false);
  const [showAutoFill, setShowAutoFill] = useState(false);

  // --- Custom Schema Builder State ---
  const [isBuildingSchema, setIsBuildingSchema] = useState(false);
  const [schemaToEditId, setSchemaToEditId] = useState<string>('new');
  const [newSchemaName, setNewSchemaName] = useState('');
  const [newSchemaFields, setNewSchemaFields] = useState<BibleField[]>([]);
  const [tempField, setTempField] = useState<Partial<BibleField>>({ label: '', type: 'text', required: false });

  // --- Lore Harvester State ---
  const [showScanConfig, setShowScanConfig] = useState(false);
  const [scanFocus, setScanFocus] = useState<ScanFocus[]>(['entities', 'events', 'relationships']);
  const [isScanningLore, setIsScanningLore] = useState(false);
  const [loreSuggestions, setLoreSuggestions] = useState<LoreSuggestion[]>([]);
  
  // --- Editor Scan (Audit) State ---
  const [showAuditConfig, setShowAuditConfig] = useState(false);
  const [auditModes, setAuditModes] = useState<EditorScanMode[]>(['logic', 'prose', 'formatting']);
  const [customAuditInstruction, setCustomAuditInstruction] = useState('');
  const [isAuditing, setIsAuditing] = useState(false);
  // auditResults state removed (lifted to props)
  const [isAuditStale, setIsAuditStale] = useState(false);
  const [naturalnessResult, setNaturalnessResult] = useState<{score: number, summary: string} | null>(null);
  
  // Audit Scope State
  const [auditScope, setAuditScope] = useState<AuditScope>('full');
  const [chapterRange, setChapterRange] = useState({ start: 0, end: 0 });
  
  // Deep Scan State (Shared logic for Lore and Audit chunks)
  const [isDeepScan, setIsDeepScan] = useState(false); // For Lore
  const [scanChunkSize, setScanChunkSize] = useState(20000); // characters (~4000 words)
  const [scanProgress, setScanProgress] = useState({ current: 0, total: 0 });
  const [abortController, setAbortController] = useState<AbortController | null>(null);

  // Handle Prefill (Context Promotion)
  useEffect(() => {
      if (prefillItem) {
          setActiveTab('bible');
          setIsAddingBible(true);
          setNewItemName(prefillItem.name);
          // Try to put description in the first textarea field of the active schema
          const schema = bibleSchemas.find(s => s.id === selectedSchemaId) || bibleSchemas[0];
          const firstTextField = schema.fields.find(f => f.type === 'textarea') || schema.fields[0];
          if (firstTextField) {
              setNewItemData({ [firstTextField.key]: prefillItem.description });
          }
          if (onClearPrefill) onClearPrefill();
      }
  }, [prefillItem, bibleSchemas, selectedSchemaId, onClearPrefill]);

  // Use schemas from props (which are now initialized with defaults in App.tsx)
  const activeSchema = bibleSchemas.find(s => s.id === selectedSchemaId) || bibleSchemas[0];

  // Detect Chapters for Selector
  const detectedChapters = useMemo(() => {
      if (!storyContent) return [];
      // Regex to find headers like "Chapter 1", "### The Beginning", etc.
      const matches = [...storyContent.matchAll(/^(#{1,3}\s.*|^Chapter\s+\d+.*)/gm)];
      if (matches.length === 0) return [];
      return matches.map((m, idx) => ({
          index: idx,
          label: m[0].trim(),
          startIndex: m.index!,
          endIndex: matches[idx + 1] ? matches[idx + 1].index! : storyContent.length
      }));
  }, [storyContent]);

  // Reset range if chapters change
  useEffect(() => {
      if (detectedChapters.length > 0) {
          setChapterRange(prev => ({ 
              start: Math.min(prev.start, detectedChapters.length - 1), 
              end: Math.min(Math.max(prev.end, prev.start), detectedChapters.length - 1) 
          }));
      }
  }, [detectedChapters.length]);

  // Filter Bible Items
  const filteredBibleItems = useMemo(() => {
      if (!searchQuery) return bibleItems;
      const lowerQ = searchQuery.toLowerCase();
      return bibleItems.filter(item => 
          item.name.toLowerCase().includes(lowerQ) || 
          item.schemaId.toLowerCase().includes(lowerQ) ||
          Object.values(item.data).some(v => (v as string).toLowerCase().includes(lowerQ))
      );
  }, [bibleItems, searchQuery]);

  // --- Handlers ---
  
  const handleEditItem = (item: BibleItem) => {
      setEditingItemId(item.id);
      setSelectedSchemaId(item.schemaId);
      setNewItemName(item.name);
      setNewItemData(item.data);
      setNewItemEvents(item.events || []);
      setNewItemRelations(item.relationships || []);
      
      setIsAddingBible(true);
      setShowAutoFill(false);
      setBibleViewMode('data');
      setLoreSuggestions([]); // Clear suggestions to focus on edit
      setAuditResults([]);
  };

  const handleSaveBibleItem = () => {
    if (!newItemName) {
        alert("Name is required");
        return;
    }
    
    const missingRequired = activeSchema.fields
        .filter(f => f.required && !newItemData[f.key])
        .map(f => f.label);

    if (missingRequired.length > 0) {
        if(!confirm(`Missing required fields: ${missingRequired.join(', ')}. Save anyway?`)) {
            return;
        }
    }

    const itemPayload: BibleItem = {
      id: editingItemId || Date.now().toString(),
      schemaId: selectedSchemaId,
      name: newItemName,
      data: newItemData,
      events: newItemEvents,
      relationships: newItemRelations
    };

    if (editingItemId) {
        onUpdateBibleItem(itemPayload);
    } else {
        onAddBibleItem(itemPayload);
    }
    
    // Reset
    setEditingItemId(null);
    setNewItemName('');
    setNewItemData({});
    setNewItemEvents([]);
    setNewItemRelations([]);
    setIsAddingBible(false);
    setShowAutoFill(false);
  };

  const handleAutoGenerate = async () => {
      setIsAutoGenerating(true);
      try {
          const attributes = await generateBibleAttributes(activeSchema, autoGenSeed, selectedModel);
          setNewItemData(prev => ({ ...prev, ...attributes }));
          if (attributes.name && !newItemName) setNewItemName(attributes.name);
          setShowAutoFill(false);
      } catch (e) {
          alert("Failed to auto-generate.");
      } finally {
          setIsAutoGenerating(false);
      }
  };

  const handleScanLore = async () => {
      if (!storyContent) { alert("No story content to scan."); return; }
      setIsScanningLore(true);
      setShowScanConfig(false);
      setScanProgress({ current: 0, total: 0 });
      setLoreSuggestions([]);
      const controller = new AbortController();
      setAbortController(controller);

      try {
          if (isDeepScan) {
              const totalLength = storyContent.length;
              const totalChunks = Math.ceil(totalLength / scanChunkSize);
              setScanProgress({ current: 0, total: totalChunks });
              let collectedSuggestions: LoreSuggestion[] = [];
              for (let i = 0; i < totalChunks; i++) {
                  if (controller.signal.aborted) break;
                  const start = i * scanChunkSize;
                  const end = Math.min(start + scanChunkSize, totalLength);
                  const chunk = storyContent.slice(start, end);
                  setScanProgress(prev => ({ ...prev, current: i + 1 }));
                  const chunkSuggestions = await scanForNewLore(chunk, bibleItems, bibleSchemas, selectedModel, scanFocus);
                  const newUnique = chunkSuggestions.filter(s => {
                      const isDupe = collectedSuggestions.some(existing => existing.type === s.type && existing.name === s.name && (s.relTargetName ? existing.relTargetName === s.relTargetName : true));
                      return !isDupe;
                  });
                  collectedSuggestions = [...collectedSuggestions, ...newUnique];
                  setLoreSuggestions(prev => [...prev, ...newUnique]);
              }
              if (collectedSuggestions.length === 0 && !controller.signal.aborted) alert("Deep scan complete. No new lore found.");
          } else {
              const suggestions = await scanForNewLore(storyContent, bibleItems, bibleSchemas, selectedModel, scanFocus);
              setLoreSuggestions(suggestions);
              if (suggestions.length === 0) alert("No new lore found with current filters.");
          }
      } catch (e: any) {
          if (!controller.signal.aborted) {
              const msg = e.message || '';
              if (msg.includes('429') || msg.includes('quota')) alert("Scan failed: API Rate Limit exceeded. Please try again in a few moments.");
              else alert("Scan failed. See console for details.");
          }
      } finally {
          setIsScanningLore(false);
          setAbortController(null);
      }
  };
  
  const handleStopScan = () => {
      if (abortController) { abortController.abort(); setIsScanningLore(false); setIsAuditing(false); setAbortController(null); }
  };

  const toggleScanFocus = (focus: ScanFocus) => { setScanFocus(prev => prev.includes(focus) ? prev.filter(f => f !== focus) : [...prev, focus]); };
  const toggleAuditMode = (mode: EditorScanMode) => { setAuditModes(prev => prev.includes(mode) ? prev.filter(m => m !== mode) : [...prev, mode]); };

  const handleAuditStory = async () => {
      if (!storyContent) { alert("Need story content to audit."); return; }
      setIsAuditing(true); setShowAuditConfig(false); setIsAuditStale(false); setAuditResults([]); setNaturalnessResult(null);
      const controller = new AbortController();
      setAbortController(controller);
      
      try {
          let textToScan = storyContent;
          if (auditScope === 'chapter') {
              const startCh = detectedChapters[chapterRange.start];
              const endCh = detectedChapters[chapterRange.end];
              if (startCh && endCh) textToScan = storyContent.slice(startCh.startIndex, endCh.endIndex);
          }

          // If Humanization is enabled, run specific assessment
          if (auditModes.includes('humanization')) {
              // Analyze chunk for score (if 'chunked', just analyze the last chunk or a sample for speed, or separate loop?)
              // For simplicity, assess the current scope text
              assessNaturalness(textToScan, selectedModel).then(res => setNaturalnessResult(res));
          }

          if (auditScope === 'chunked') {
              const totalLength = storyContent.length;
              const totalChunks = Math.ceil(totalLength / scanChunkSize);
              setScanProgress({ current: 0, total: totalChunks });
              for (let i = 0; i < totalChunks; i++) {
                  if (controller.signal.aborted) break;
                  const start = i * scanChunkSize;
                  const end = Math.min(start + scanChunkSize, totalLength);
                  const chunk = storyContent.slice(start, end);
                  setScanProgress(prev => ({ ...prev, current: i + 1 }));
                  const results = await runEditorScan(chunk, bibleItems, auditModes, customAuditInstruction, selectedModel);
                  setAuditResults(prev => [...prev, ...results]);
              }
          } else {
              const results = await runEditorScan(textToScan, bibleItems, auditModes, customAuditInstruction, selectedModel);
              setAuditResults(results);
              if (results.length === 0) alert("Clean scan! No issues found.");
          }
      } catch (e: any) {
          if (!controller.signal.aborted) {
              const msg = e.message || '';
              if (msg.includes('429') || msg.includes('quota')) alert("Audit failed: Rate Limit exceeded. Try 'Chunked' scope or wait a moment.");
              else alert("Audit failed.");
          }
      } finally { setIsAuditing(false); setAbortController(null); }
  };

  const handleFixStory = (result: EditorIssue) => {
      if (!result.fixSuggestion) return;
      const match = findBestMatch(storyContent, result.snippet);
      if (!match) { alert("Could not find exact text match to replace. The text may have changed since the scan. Please copy the fix manually."); return; }
      const newContent = storyContent.substring(0, match.start) + result.fixSuggestion + storyContent.substring(match.end);
      if (onUpdateContent) onUpdateContent(newContent);
      setIsAuditStale(true);
      setAuditResults(prev => prev.filter(r => r !== result));
  };

  const handleFixBible = (result: EditorIssue) => {
      if (!result.bibleUpdate) return;
      const targetName = result.bibleUpdate.targetName;
      const targetItem = bibleItems.find(i => i.name.toLowerCase() === targetName.toLowerCase());
      if (targetItem) {
          const updatedItem = { ...targetItem, data: { ...targetItem.data, ...(result.bibleUpdate.updates.data || {}) } };
          onUpdateBibleItem(updatedItem);
          setIsAuditStale(true);
          setAuditResults(prev => prev.filter(r => r !== result));
      } else { alert("Could not find matching Bible item to update."); }
  };

  const applySuggestionToMap = (suggestion: LoreSuggestion, itemsMap: Map<string, BibleItem>, addedIds: Map<string, string>) => {
      if (suggestion.type === 'new_entity') {
          let schemaId = suggestion.schemaId || 'character';
          const newId = Date.now().toString() + Math.random().toString(36).substr(2, 5);
          const newItem: BibleItem = { id: newId, schemaId: schemaId, name: suggestion.name, data: suggestion.data || {}, events: [], relationships: [] };
          itemsMap.set(newId, newItem);
          addedIds.set(suggestion.name.toLowerCase(), newId);
      } else {
          let targetId = suggestion.targetId;
          if (!targetId || !itemsMap.has(targetId)) {
               if (suggestion.name && addedIds.has(suggestion.name.toLowerCase())) targetId = addedIds.get(suggestion.name.toLowerCase());
               else if (suggestion.name) { for (const [id, item] of itemsMap.entries()) { if (item.name.toLowerCase() === suggestion.name.toLowerCase()) { targetId = id; break; } } }
          }
          const existing = targetId ? itemsMap.get(targetId) : undefined;
          if (existing) {
              const updatedItem = { ...existing };
              if (suggestion.type === 'update_entity') updatedItem.data = { ...updatedItem.data, ...(suggestion.data || {}) };
              else if (suggestion.type === 'new_event') {
                  const newEvent = { id: Date.now().toString() + Math.random().toString(36).substr(2, 5), description: suggestion.eventDescription || '', contextSnippet: suggestion.eventContext, timestamp: 'Recent Story Update' };
                  updatedItem.events = [...(updatedItem.events || []), newEvent];
              } else if (suggestion.type === 'update_relationship') {
                  const newRel = { targetId: 'unknown', targetName: suggestion.relTargetName || 'Unknown', type: suggestion.relType || 'Neutral', description: suggestion.relDescription || '' };
                  const existingRels = updatedItem.relationships || [];
                  const existsIdx = existingRels.findIndex(r => r.targetName.toLowerCase() === newRel.targetName.toLowerCase());
                  let updatedRels = [...existingRels];
                  if (existsIdx >= 0) { 
                      const currentRel = updatedRels[existsIdx];
                      const newScore = Math.max(-100, Math.min(100, (currentRel.affinityScore || 0) + (suggestion.relAffinityChange || 0)));
                      const history = currentRel.modifiers || [];
                      if (suggestion.relChangeReason && suggestion.relAffinityChange !== undefined && suggestion.relAffinityChange !== 0) {
                          history.push({ id: Date.now().toString(), reason: suggestion.relChangeReason, value: suggestion.relAffinityChange, timestamp: new Date().toLocaleDateString() });
                      }
                      updatedRels[existsIdx] = { ...currentRel, ...newRel, affinityScore: newScore, modifiers: history }; 
                  } else { 
                      updatedRels.push({ ...newRel, affinityScore: suggestion.relAffinityChange || 0, modifiers: suggestion.relChangeReason ? [{ id: Date.now().toString(), reason: suggestion.relChangeReason, value: suggestion.relAffinityChange || 0, timestamp: new Date().toLocaleDateString() }] : [] }); 
                  }
                  updatedItem.relationships = updatedRels;
              }
              itemsMap.set(existing.id, updatedItem);
          }
      }
  };

  const handleAcceptLore = (suggestion: LoreSuggestion) => {
      const itemsMap = new Map<string, BibleItem>();
      bibleItems.forEach(item => itemsMap.set(item.id, item));
      const addedIds = new Map<string, string>();
      applySuggestionToMap(suggestion, itemsMap, addedIds);
      itemsMap.forEach((item, id) => { if (bibleItems.find(i => i.id === id)) onUpdateBibleItem(item); else onAddBibleItem(item); });
      setLoreSuggestions(prev => prev.filter(s => s !== suggestion));
  };

  const handleAcceptAllLore = () => {
      const itemsMap = new Map<string, BibleItem>();
      bibleItems.forEach(item => itemsMap.set(item.id, item));
      const addedIds = new Map<string, string>();
      loreSuggestions.forEach(suggestion => applySuggestionToMap(suggestion, itemsMap, addedIds));
      const originalIds = new Set(bibleItems.map(i => i.id));
      itemsMap.forEach((item, id) => { if (originalIds.has(id)) onUpdateBibleItem(item); else onAddBibleItem(item); });
      setLoreSuggestions([]);
  };

  useEffect(() => {
     if (isBuildingSchema) {
         if (schemaToEditId === 'new') { setNewSchemaName(''); setNewSchemaFields([]); } 
         else { const existing = bibleSchemas.find(s => s.id === schemaToEditId); if (existing) { setNewSchemaName(existing.name); setNewSchemaFields([...existing.fields]); } }
     }
  }, [isBuildingSchema, schemaToEditId, bibleSchemas]);

  const handleAddTempField = () => {
      if (!tempField.label) return;
      const key = tempField.label.toLowerCase().replace(/\s+/g, '_');
      setNewSchemaFields([...newSchemaFields, { key, label: tempField.label, type: tempField.type as 'text' | 'textarea', required: tempField.required || false, placeholder: 'Enter value...' }]);
      setTempField({ label: '', type: 'text', required: false });
  };

  const handleSaveSchema = () => {
      if (!newSchemaName || newSchemaFields.length === 0) return;
      const id = schemaToEditId === 'new' ? 'custom_' + Date.now() : schemaToEditId;
      onAddSchema({ id, name: newSchemaName, fields: newSchemaFields, isCustom: true });
      setIsBuildingSchema(false); setSelectedSchemaId(id); setNewSchemaName(''); setNewSchemaFields([]);
  };

  // --- Style Handlers ---
  const [isCreatingStyle, setIsCreatingStyle] = useState(false);
  const [styleSample, setStyleSample] = useState('');
  const [styleName, setStyleName] = useState('');
  const [isExtractingStyle, setIsExtractingStyle] = useState(false);
  const [editingStyleId, setEditingStyleId] = useState<string | null>(null);
  const [editedDNA, setEditedDNA] = useState('');
  const [editedConstraints, setEditedConstraints] = useState('');
  const [showStyleRefine, setShowStyleRefine] = useState(false);
  const [styleRefineInput, setStyleRefineInput] = useState('');
  const [isRefining, setIsRefining] = useState(false);
  const [isSuggestingConstraints, setIsSuggestingConstraints] = useState(false);

  const handleCreateStyle = async () => {
    if (!styleSample || !styleName) return;
    setIsExtractingStyle(true);
    try {
      const dna = await extractStyleDNA(styleSample, selectedModel);
      onAddStyle({ id: Date.now().toString(), name: styleName, dna: dna, negativeConstraints: '' });
      setStyleName(''); setStyleSample(''); setIsCreatingStyle(false);
    } catch (e) { alert("Failed to extract style."); } finally { setIsExtractingStyle(false); }
  };

  const handleStartEditStyle = (style: StyleProfile, e: React.MouseEvent) => {
      e.stopPropagation(); setEditingStyleId(style.id); setEditedDNA(style.dna); setEditedConstraints(style.negativeConstraints || ''); setIsCreatingStyle(false); setShowStyleRefine(false);
  };

  const handleSaveStyleEdit = (originalStyle: StyleProfile) => {
      onUpdateStyle({ ...originalStyle, dna: editedDNA, negativeConstraints: editedConstraints }); setEditingStyleId(null);
  };

  const handleRefineStyle = async () => {
      if (!styleRefineInput) return;
      setIsRefining(true);
      try { const newDna = await refineStyleInstruction(editedDNA, styleRefineInput, selectedModel); setEditedDNA(newDna); setStyleRefineInput(''); setShowStyleRefine(false); } catch (e) { alert("Failed to refine style."); } finally { setIsRefining(false); }
  };

  const handleSuggestConstraints = async () => {
      setIsSuggestingConstraints(true);
      try { const suggestions = await suggestNegativeConstraints(editedDNA, selectedModel); setEditedConstraints(suggestions); } catch (e) { alert("Failed to suggest constraints."); } finally { setIsSuggestingConstraints(false); }
  };

  const handleExport = () => {
      const data = { bibleItems, bibleSchemas, styles, content: localStorage.getItem('coauth_content'), graph: localStorage.getItem('coauth_graph') };
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = `coauth-project-${Date.now()}.json`; a.click();
  };

  const handleImportClick = () => { document.getElementById('import-file')?.click(); };

  const handleImportFile = (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]; if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
          try {
              const data = JSON.parse(ev.target?.result as string);
              if (!data.bibleItems) throw new Error("Invalid project file");
              if(confirm("Importing will overwrite current project. Continue?")) {
                  if(data.content) localStorage.setItem('coauth_content', data.content);
                  if(data.bibleItems) localStorage.setItem('coauth_bible', JSON.stringify(data.bibleItems));
                  if(data.bibleSchemas) localStorage.setItem('coauth_schemas', JSON.stringify(data.bibleSchemas));
                  if(data.styles) localStorage.setItem('coauth_styles', JSON.stringify(data.styles));
                  if(data.graph) localStorage.setItem('coauth_graph', data.graph);
                  window.location.reload();
              }
          } catch(err) { alert("Import failed: Invalid file."); }
      };
      reader.readAsText(file);
  };
  
  const handleClearProject = () => {
      if (confirm("ARE YOU SURE? This will delete all Story Content, Bible Data, Styles, and Graphs. This cannot be undone.")) {
          onResetProject();
      }
  };

  const activeStyleProfile = styles.find(s => s.id === activeStyleId) || null;

  return (
    <div className={`fixed inset-y-0 right-0 z-50 w-80 bg-gray-900 border-l border-gray-800 shadow-2xl transform transition-transform duration-300 ease-in-out flex flex-col ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}>
      {/* Header with Tabs */}
      <div className="flex-none p-4 border-b border-gray-800 bg-gray-950/50">
        <div className="flex items-center justify-between mb-0">
          <div className="flex bg-gray-800/50 p-1 rounded-lg">
            <button onClick={() => setActiveTab('write')} className={`p-2 rounded-md transition-all ${activeTab === 'write' ? 'bg-gray-700 text-white shadow-sm' : 'text-gray-400 hover:text-gray-200'}`} title="Writer Controls"><PenTool className="w-4 h-4" /></button>
            <button onClick={() => setActiveTab('bible')} className={`p-2 rounded-md transition-all ${activeTab === 'bible' ? 'bg-gray-700 text-white shadow-sm' : 'text-gray-400 hover:text-gray-200'}`} title="World Bible"><Book className="w-4 h-4" /></button>
            <button onClick={() => setActiveTab('advisor')} className={`p-2 rounded-md transition-all ${activeTab === 'advisor' ? 'bg-gray-700 text-white shadow-sm' : 'text-gray-400 hover:text-gray-200'}`} title="Advisor Chat"><MessageSquareText className="w-4 h-4" /></button>
            <button onClick={() => setActiveTab('styles')} className={`p-2 rounded-md transition-all ${activeTab === 'styles' ? 'bg-gray-700 text-white shadow-sm' : 'text-gray-400 hover:text-gray-200'}`} title="Style Vault"><Palette className="w-4 h-4" /></button>
            <button onClick={() => setActiveTab('publish')} className={`p-2 rounded-md transition-all ${activeTab === 'publish' ? 'bg-gray-700 text-white shadow-sm' : 'text-gray-400 hover:text-gray-200'}`} title="Typesetter / Publish"><Printer className="w-4 h-4" /></button>
          </div>
          <button onClick={onToggle} className="p-1 text-gray-400 hover:text-white rounded-md hover:bg-gray-800 transition-colors"><X className="w-5 h-5" /></button>
        </div>
      </div>

      {/* Main Content Area - Split based on Tab */}
      
        {/* --- WRITE TAB --- */}
        {activeTab === 'write' && (
          <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
            <div className="flex flex-col gap-4 animate-in fade-in slide-in-from-right-4 duration-200">
            <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-700/50">
              <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">Word Count</div>
              <div className="text-2xl font-mono text-white">{wordCount}</div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300 flex items-center gap-2"><Settings2 className="w-3 h-3" /> Model</label>
              <div className="relative">
                <select value={selectedModel} onChange={(e) => onSelectModel(e.target.value as ModelType)} className="w-full bg-gray-950 border border-gray-700 rounded-lg p-2.5 text-sm text-gray-200 focus:ring-2 focus:ring-accent focus:border-transparent appearance-none cursor-pointer hover:bg-gray-900 transition-colors">
                  <option value={ModelType.GEMINI_3_PRO}>Gemini 3.0 Pro</option>
                  <option value={ModelType.GEMINI_2_5_PRO}>Gemini 2.5 Pro</option>
                  <option value={ModelType.GEMINI_2_5_FLASH}>Gemini 2.5 Flash</option>
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-400"><ChevronRight className="w-4 h-4 rotate-90" /></div>
              </div>
            </div>

            {activeStyleId && (
              <div className="p-2 bg-purple-500/10 border border-purple-500/20 rounded-lg flex items-center justify-between">
                <div className="flex items-center gap-2"><Palette className="w-3 h-3 text-purple-400" /><span className="text-xs text-purple-200 truncate max-w-[150px]">Using: <span className="font-semibold">{styles.find(s => s.id === activeStyleId)?.name}</span></span></div>
                <button onClick={() => onSelectStyle(null)} className="text-purple-400 hover:text-white"><X className="w-3 h-3" /></button>
              </div>
            )}

            <div className="space-y-2 pt-2 border-t border-gray-800 mt-2">
               <label className="text-sm font-medium text-gray-300 flex items-center gap-2"><Network className="w-3 h-3 text-purple-400" /> Visual Graph</label>
              <Button onClick={onOpenChainBuilder} variant="secondary" className="w-full justify-between group"><span>Open Logic Graph</span><span className="text-gray-500 group-hover:text-white transition-colors">→</span></Button>
            </div>

            <div className="space-y-2 pt-2 border-t border-gray-800 mt-2">
              <label className="text-sm font-medium text-gray-300">Direct Instruction</label>
              <textarea value={instruction} onChange={(e) => setInstruction(e.target.value)} placeholder="e.g., Introduce a plot twist..." className="w-full h-32 bg-gray-950 border border-gray-700 rounded-lg p-3 text-sm text-gray-200 focus:ring-2 focus:ring-accent focus:border-transparent resize-none placeholder-gray-600 transition-all"/>
            </div>

            {setNegativeInstruction && (
              <div className="space-y-2">
                 <label className="text-xs font-medium text-red-400 flex items-center gap-1"><Ban className="w-3 h-3"/> Negative Constraints</label>
                 <textarea 
                    value={negativeInstruction} 
                    onChange={(e) => setNegativeInstruction(e.target.value)} 
                    placeholder="e.g. Do not use passive voice..." 
                    className="w-full h-16 bg-gray-950 border border-red-900/30 rounded-lg p-2 text-xs text-red-100 focus:ring-1 focus:ring-red-500 focus:border-transparent resize-none placeholder-red-900/50 transition-all"
                 />
              </div>
            )}

            <Button onClick={onGenerate} isLoading={isGenerating} icon={<Sparkles className="w-4 h-4" />} className="w-full mt-2">{isGenerating ? 'Writing...' : 'Continue Story'}</Button>
            
            <div className="mt-auto pt-4 border-t border-gray-800 flex flex-col gap-2">
                 <div className="flex gap-2">
                     <button onClick={handleExport} className="flex-1 p-2 bg-gray-800 hover:bg-gray-700 rounded text-xs flex items-center justify-center gap-1 text-gray-300"><Download className="w-3 h-3"/> Export</button>
                     <button onClick={handleImportClick} className="flex-1 p-2 bg-gray-800 hover:bg-gray-700 rounded text-xs flex items-center justify-center gap-1 text-gray-300"><Upload className="w-3 h-3"/> Import</button>
                     <input type="file" id="import-file" className="hidden" accept=".json" onChange={handleImportFile} />
                 </div>
                 <button type="button" onClick={handleClearProject} className="w-full p-2 bg-red-900/30 hover:bg-red-800/50 text-red-300 rounded text-xs flex items-center justify-center gap-1 border border-red-900/50"><RotateCcw className="w-3 h-3"/> Clear / Start Fresh</button>
            </div>
          </div>
          </div>
        )}

        {/* --- ADVISOR TAB --- */}
        {activeTab === 'advisor' && (
            <div className="flex-1 overflow-hidden animate-in fade-in slide-in-from-right-4 duration-200">
                <AdvisorChat 
                    storyContext={storyContent} 
                    bibleItems={bibleItems}
                    activeStyle={activeStyleProfile}
                    onUpdateContent={onUpdateContent || (() => {})}
                    history={advisorHistory}
                    setHistory={setAdvisorHistory}
                />
            </div>
        )}

        {/* --- PUBLISH TAB --- */}
        {activeTab === 'publish' && (
            <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
                <div className="flex flex-col gap-4 animate-in fade-in slide-in-from-right-4 duration-200">
                    <div className="p-4 bg-green-900/10 border border-green-500/20 rounded-lg">
                        <h3 className="text-sm font-bold text-green-300 mb-2 flex items-center gap-2"><Printer className="w-4 h-4"/> Book Typesetter</h3>
                        <p className="text-xs text-gray-400 mb-4">
                            Format your manuscript for print (PDF). Customize trim size, fonts, and margins, then export a print-ready file.
                        </p>
                        <Button onClick={onOpenBookPreview} className="w-full bg-green-600 hover:bg-green-500 text-white border-none shadow-lg">
                            Open Visual Typesetter
                        </Button>
                    </div>
                    
                    <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                        <h4 className="text-xs font-bold text-gray-400 uppercase mb-2">Export Formats</h4>
                        <div className="space-y-2">
                            <button onClick={() => { /* Placeholder */ alert("PDF Export happens inside the Visual Typesetter."); }} className="w-full p-2 bg-gray-900 hover:bg-gray-800 rounded border border-gray-700 text-xs text-left flex items-center justify-between group">
                                <span>PDF (Print Ready)</span>
                                <ArrowRight className="w-3 h-3 text-gray-500 group-hover:text-white"/>
                            </button>
                            <button onClick={() => { /* Placeholder */ alert("EPUB export coming soon."); }} className="w-full p-2 bg-gray-900 hover:bg-gray-800 rounded border border-gray-700 text-xs text-left flex items-center justify-between group opacity-50 cursor-not-allowed">
                                <span>EPUB (E-Book)</span>
                                <span className="text-[9px] bg-gray-800 px-1 rounded text-gray-500">Soon</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        )}

        {/* --- BIBLE TAB (Split Layout) --- */}
        {activeTab === 'bible' && (
          <div className="flex flex-col h-full animate-in fade-in slide-in-from-right-4 duration-200">
             {/* Fixed Toolbar */}
             <div className="flex-none p-4 border-b border-gray-800 bg-gray-900 z-30 relative">
                 <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-white">World Bible</h3>
                  <div className="flex gap-2 relative">
                      {/* Editor Scan Popover Trigger */}
                      <div className="relative">
                          <button onClick={() => setShowAuditConfig(!showAuditConfig)} className={`p-1 rounded hover:bg-red-400/10 ${isAuditing ? 'text-red-400' : 'text-gray-400'}`} title="Run Editor Scan">
                            {isAuditing ? <Loader2 className="w-4 h-4 animate-spin"/> : <ShieldAlert className="w-4 h-4" />}
                          </button>
                          {showAuditConfig && (
                              <div className="absolute top-full mt-2 right-0 bg-gray-900 border border-gray-600 p-4 rounded-xl w-72 shadow-2xl z-[100] animate-in slide-in-from-top-2 backdrop-blur-md">
                                  <h4 className="text-xs font-bold text-gray-300 mb-2 uppercase flex items-center gap-2"><ShieldAlert className="w-3 h-3"/> Editor Scan</h4>
                                  
                                  {/* Scope Selection */}
                                  <div className="mb-3 bg-black/20 p-2 rounded">
                                      <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">Scan Scope</label>
                                      <div className="flex gap-1 mb-2">
                                          <button onClick={() => setAuditScope('full')} className={`flex-1 py-1 text-[10px] rounded border transition-colors ${auditScope === 'full' ? 'bg-red-900/40 border-red-500/50 text-red-200' : 'bg-gray-800 border-transparent text-gray-400 hover:text-white'}`} title="Checks entire book for logic/continuity.">Full</button>
                                          <button onClick={() => setAuditScope('chapter')} className={`flex-1 py-1 text-[10px] rounded border transition-colors ${auditScope === 'chapter' ? 'bg-blue-900/40 border-blue-500/50 text-blue-200' : 'bg-gray-800 border-transparent text-gray-400 hover:text-white'}`} title="Checks specific chapters.">Range</button>
                                          <button onClick={() => setAuditScope('chunked')} className={`flex-1 py-1 text-[10px] rounded border transition-colors ${auditScope === 'chunked' ? 'bg-yellow-900/40 border-yellow-500/50 text-yellow-200' : 'bg-gray-800 border-transparent text-gray-400 hover:text-white'}`} title="Iterates in chunks. Best for Prose/Grammar.">Chunked</button>
                                      </div>
                                      
                                      {/* Chapter Range Selector */}
                                      {auditScope === 'chapter' && (
                                          <div className="space-y-1">
                                              {detectedChapters.length === 0 ? (
                                                  <div className="text-[10px] text-gray-500 italic">No chapters detected. Scanning full text.</div>
                                              ) : (
                                                  <div className="flex items-center gap-2">
                                                      <select 
                                                          value={chapterRange.start} 
                                                          onChange={(e) => setChapterRange(prev => ({ ...prev, start: Math.min(parseInt(e.target.value), prev.end) }))} 
                                                          className="flex-1 bg-gray-950 border border-gray-700 rounded p-1 text-[10px] text-gray-300 w-full"
                                                      >
                                                          {detectedChapters.map((ch, idx) => (
                                                              <option key={idx} value={idx}>{ch.label}</option>
                                                          ))}
                                                      </select>
                                                      <span className="text-[10px] text-gray-500">to</span>
                                                      <select 
                                                          value={chapterRange.end} 
                                                          onChange={(e) => setChapterRange(prev => ({ ...prev, end: Math.max(parseInt(e.target.value), prev.start) }))} 
                                                          className="flex-1 bg-gray-950 border border-gray-700 rounded p-1 text-[10px] text-gray-300 w-full"
                                                      >
                                                          {detectedChapters.map((ch, idx) => (
                                                              <option key={idx} value={idx}>{ch.label}</option>
                                                          ))}
                                                      </select>
                                                  </div>
                                              )}
                                          </div>
                                      )}
                                      
                                      {/* Help Text */}
                                      <div className="text-[9px] text-gray-500 italic mt-1 flex items-start gap-1">
                                          <HelpCircle className="w-3 h-3 flex-shrink-0"/>
                                          <span>
                                              {auditScope === 'full' && "Best for Plot Holes & Continuity across the whole book."}
                                              {auditScope === 'chapter' && "Focuses audit on a specific range of chapters."}
                                              {auditScope === 'chunked' && "Best for Prose, Typos & Grammar. Deep scan."}
                                          </span>
                                      </div>
                                  </div>

                                  <div className="space-y-2 mb-3">
                                      <label className="flex items-center gap-2 text-xs text-gray-400"><input type="checkbox" checked={auditModes.includes('logic')} onChange={() => toggleAuditMode('logic')} /> Logic & Continuity</label>
                                      <label className="flex items-center gap-2 text-xs text-gray-400"><input type="checkbox" checked={auditModes.includes('prose')} onChange={() => toggleAuditMode('prose')} /> Prose & Style</label>
                                      <label className="flex items-center gap-2 text-xs text-gray-400"><input type="checkbox" checked={auditModes.includes('formatting')} onChange={() => toggleAuditMode('formatting')} /> Formatting & Spelling</label>
                                      <label className="flex items-center gap-2 text-xs text-gray-300 font-bold"><input type="checkbox" checked={auditModes.includes('humanization')} onChange={() => toggleAuditMode('humanization')} /> <BrainCircuit className="w-3 h-3 text-purple-400"/> AI Detection (Humanizer)</label>
                                      <label className="flex items-center gap-2 text-xs text-gray-400"><input type="checkbox" checked={auditModes.includes('custom')} onChange={() => toggleAuditMode('custom')} /> Custom</label>
                                  </div>
                                  
                                  {auditModes.includes('custom') && (
                                      <textarea 
                                        placeholder="Specific instructions..." 
                                        value={customAuditInstruction}
                                        onChange={(e) => setCustomAuditInstruction(e.target.value)}
                                        className="w-full bg-black/30 border border-gray-700 rounded p-2 text-[10px] text-white h-16 resize-none mb-2"
                                      />
                                  )}
                                  
                                  {isAuditing ? (
                                      <div className="w-full text-center">
                                          {auditScope === 'chunked' && <div className="text-[10px] text-yellow-400 mb-1">Scanning Chunk {scanProgress.current}/{scanProgress.total}</div>}
                                          <Button size="sm" onClick={handleStopScan} className="w-full text-xs bg-red-600 hover:bg-red-500"><StopCircle className="w-3 h-3 mr-1"/> Stop</Button>
                                      </div>
                                  ) : (
                                      <Button size="sm" onClick={handleAuditStory} className="w-full text-xs bg-red-600 hover:bg-red-500">Run Editor Scan</Button>
                                  )}
                              </div>
                          )}
                      </div>
                      
                      {/* Scan Popover Trigger */}
                      <div className="relative">
                          <button onClick={() => setShowScanConfig(!showScanConfig)} className={`p-1 rounded hover:bg-yellow-400/10 ${isScanningLore ? 'text-yellow-400' : 'text-gray-400'}`} title="Scan Text for New Lore">
                            {isScanningLore ? <Loader2 className="w-4 h-4 animate-spin"/> : <ScanSearch className="w-4 h-4" />}
                          </button>
                          {showScanConfig && (
                              <div className="absolute top-full mt-2 right-0 bg-gray-900 border border-gray-600 p-4 rounded-xl w-72 shadow-2xl z-[100] animate-in slide-in-from-top-2 backdrop-blur-md">
                                  <h4 className="text-xs font-bold text-gray-300 mb-2 uppercase">Scan Focus</h4>
                                  <div className="space-y-2 mb-3">
                                      <label className="flex items-center gap-2 text-xs text-gray-400"><input type="checkbox" checked={scanFocus.includes('entities')} onChange={() => toggleScanFocus('entities')} /> Entities</label>
                                      <label className="flex items-center gap-2 text-xs text-gray-400"><input type="checkbox" checked={scanFocus.includes('events')} onChange={() => toggleScanFocus('events')} /> Plot Timeline</label>
                                      <label className="flex items-center gap-2 text-xs text-gray-400"><input type="checkbox" checked={scanFocus.includes('relationships')} onChange={() => toggleScanFocus('relationships')} /> Relationships</label>
                                  </div>
                                  
                                  <div className="border-t border-gray-700 my-2 pt-2">
                                      <label className="flex items-center gap-2 text-xs text-gray-300 font-bold mb-1"><input type="checkbox" checked={isDeepScan} onChange={(e) => setIsDeepScan(e.target.checked)} /> Deep Scan (Chunked)</label>
                                      {isDeepScan && (
                                          <div className="pl-5 space-y-1">
                                              <div className="flex justify-between text-[9px] text-gray-400"><span>Chunk Size</span><span>{Math.round(scanChunkSize / 1000)}k chars</span></div>
                                              <input type="range" min="10000" max="100000" step="5000" value={scanChunkSize} onChange={(e) => setScanChunkSize(parseInt(e.target.value))} className="w-full accent-yellow-500 h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer"/>
                                      </div>
                                  )}
                              </div>
                              
                              {isScanningLore ? (
                                  <Button size="sm" onClick={handleStopScan} className="w-full text-xs bg-red-600 hover:bg-red-500"><StopCircle className="w-3 h-3 mr-1"/> Stop Scan</Button>
                              ) : (
                                  <Button size="sm" onClick={handleScanLore} className="w-full text-xs">Run Scan</Button>
                              )}
                          </div>
                      )}
                  </div>

                  <button onClick={onOpenRelationshipMatrix} className={`p-1 rounded hover:bg-pink-400/10 text-gray-400 hover:text-pink-400`} title="Relationship Matrix"><Users2 className="w-4 h-4" /></button>
                  <button onClick={() => { setIsBuildingSchema(!isBuildingSchema); setIsAddingBible(false); }} className={`p-1 rounded hover:bg-blue-400/10 ${isBuildingSchema ? 'text-blue-400' : 'text-gray-400'}`} title="Manage Categories"><ListPlus className="w-4 h-4" /></button>
                  <button onClick={() => { setIsAddingBible(!isAddingBible); setEditingItemId(null); setNewItemName(''); setNewItemData({}); setNewItemEvents([]); setNewItemRelations([]); setIsBuildingSchema(false); setLoreSuggestions([]); setAuditResults([]); setIsAuditStale(false); setNaturalnessResult(null); }} className={`p-1 rounded hover:bg-green-400/10 ${isAddingBible ? 'text-green-400' : 'text-gray-400'}`} title="Add Entry"><Plus className="w-4 h-4" /></button>
              </div>
            </div>

            {/* SEARCH BAR */}
            {!isAddingBible && !isBuildingSchema && (
                <div className="relative mb-0">
                    <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Search Bible..." className="w-full bg-black/20 border border-gray-700 rounded-lg py-2 pl-9 pr-2 text-xs text-gray-300 focus:outline-none focus:border-gray-500"/>
                    <Search className="w-3 h-3 text-gray-500 absolute left-3 top-2.5" />
                    {searchQuery && (<button onClick={() => setSearchQuery('')} className="absolute right-2 top-2.5 text-gray-500 hover:text-white"><X className="w-3 h-3" /></button>)}
                </div>
            )}
             </div>

             {/* Scrollable List Area */}
             <div className="flex-1 overflow-y-auto p-4 scrollbar-thin z-0">
            
            {/* Deep Scan Progress */}
            {(isScanningLore && isDeepScan) && (
                <div className="bg-yellow-900/20 border border-yellow-500/20 rounded-lg p-3 mb-4">
                    <div className="flex justify-between text-xs text-yellow-200 mb-1">
                        <span>Deep Scanning...</span>
                        <span>{scanProgress.current} / {scanProgress.total}</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-1.5 overflow-hidden">
                        <div className="bg-yellow-500 h-full transition-all duration-300" style={{ width: `${(scanProgress.current / (scanProgress.total || 1)) * 100}%` }}></div>
                    </div>
                </div>
            )}

            {/* NATURALNESS SCORE (HUMANIZER) */}
            {naturalnessResult && (
                <div className={`border rounded-lg p-3 space-y-2 mb-4 animate-in slide-in-from-top-2 ${naturalnessResult.score > 70 ? 'bg-green-900/10 border-green-500/30' : naturalnessResult.score > 40 ? 'bg-yellow-900/10 border-yellow-500/30' : 'bg-red-900/10 border-red-500/30'}`}>
                    <div className="flex justify-between items-center">
                        <h4 className="text-xs font-bold text-gray-300 uppercase flex items-center gap-1">
                            <BrainCircuit className="w-3 h-3"/> Human Score
                        </h4>
                        <span className={`text-lg font-bold ${naturalnessResult.score > 70 ? 'text-green-400' : naturalnessResult.score > 40 ? 'text-yellow-400' : 'text-red-400'}`}>{naturalnessResult.score}%</span>
                    </div>
                    
                    <div className="w-full bg-black/40 rounded-full h-2 overflow-hidden">
                        <div 
                            className={`h-full transition-all duration-500 ${naturalnessResult.score > 70 ? 'bg-green-500' : naturalnessResult.score > 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                            style={{ width: `${naturalnessResult.score}%` }}
                        />
                    </div>
                    <p className="text-[10px] text-gray-400 italic">"{naturalnessResult.summary}"</p>
                    <button onClick={() => setNaturalnessResult(null)} className="w-full text-center text-[9px] text-gray-500 hover:text-white pt-1">Dismiss</button>
                </div>
            )}

            {/* AUDIT RESULTS (Interactive) */}
            {auditResults.length > 0 && (
                <div className={`border rounded-lg p-3 space-y-3 mb-4 ${isAuditStale ? 'bg-orange-900/10 border-orange-500/30' : 'bg-red-900/10 border-red-500/20'}`}>
                     <div className="flex justify-between items-center">
                         <h4 className={`text-xs font-bold flex items-center gap-1 ${isAuditStale ? 'text-orange-400' : 'text-red-400'}`}>
                             {isAuditStale ? <AlertCircle className="w-3 h-3"/> : <ShieldAlert className="w-3 h-3"/>} 
                             {isAuditStale ? 'Results Stale' : 'Scan Results'}
                         </h4>
                         <button onClick={() => { setAuditResults([]); setIsAuditStale(false); }} className="text-gray-500 hover:text-white"><X className="w-3 h-3"/></button>
                     </div>
                     <div className="text-[10px] text-gray-400 italic mb-1">
                        Hover over highlighted text in the editor to apply fixes.
                     </div>
                    {auditResults.map((result, idx) => (
                        <div key={idx} className="bg-black/20 p-2 rounded border border-gray-700 text-[10px] space-y-2">
                            <div className="flex items-center gap-2 mb-1">
                                <span className={`px-1.5 py-0.5 rounded text-[9px] uppercase font-bold ${
                                    result.type === 'logic' ? 'bg-red-500/20 text-red-300' : 
                                    result.type === 'prose' ? 'bg-blue-500/20 text-blue-300' : 
                                    result.type === 'humanization' ? 'bg-purple-500/20 text-purple-300' :
                                    result.type === 'formatting' ? 'bg-yellow-500/20 text-yellow-300' : 
                                    'bg-gray-500/20 text-gray-300'
                                }`}>{result.category || result.type}</span>
                            </div>
                            <p className="text-gray-200 font-medium">{result.description}</p>
                            <div className="pl-1 border-l-2 border-red-500/30 text-gray-400 italic">"{result.snippet.substring(0, 60)}..."</div>
                            {result.fixSuggestion && (
                                <div className="pl-1 border-l-2 border-green-500/30 text-green-400 italic font-medium">"{result.fixSuggestion.substring(0, 60)}..."</div>
                            )}
                            <div className="flex gap-2 pt-1">
                                {result.fixSuggestion && (<button onClick={() => handleFixStory(result)} className="flex-1 p-1 bg-green-800/40 hover:bg-green-700 rounded text-green-100 border border-green-500/30 flex items-center justify-center gap-1"><Wand2 className="w-3 h-3"/> Auto-Fix</button>)}
                                {result.bibleUpdate && (<button onClick={() => handleFixBible(result)} className="flex-1 p-1 bg-blue-800/40 hover:bg-blue-700 rounded text-blue-100 border border-blue-500/30 flex items-center justify-center gap-1"><Save className="w-3 h-3"/> Update Bible</button>)}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* LORE HARVESTER SUGGESTIONS */}
            {loreSuggestions.length > 0 && (
                <div className="bg-yellow-900/10 border border-yellow-500/20 rounded-lg p-3 space-y-3 mb-4">
                    <div className="flex justify-between items-center">
                        <h4 className="text-xs font-bold text-yellow-400 flex items-center gap-1"><Sparkles className="w-3 h-3"/> Lore Suggestions</h4>
                        <div className="flex gap-1">
                             <button onClick={handleAcceptAllLore} className="text-green-400 hover:text-white p-1" title="Accept All"><CheckCheck className="w-3 h-3"/></button>
                             <button onClick={() => setLoreSuggestions([])} className="text-gray-500 hover:text-white p-1" title="Clear All"><X className="w-3 h-3"/></button>
                        </div>
                    </div>
                    {loreSuggestions.map((suggestion, idx) => (
                        <div key={idx} className="bg-black/20 p-2 rounded border border-gray-700 flex flex-col gap-2">
                            <div className="flex justify-between items-start">
                                <div>
                                    <div className="flex items-center gap-2">
                                        <span className={`text-[9px] px-1 rounded font-bold uppercase ${suggestion.type === 'new_entity' ? 'bg-green-500/20 text-green-300' : suggestion.type === 'update_entity' ? 'bg-blue-500/20 text-blue-300' : suggestion.type === 'new_event' ? 'bg-orange-500/20 text-orange-300' : 'bg-pink-500/20 text-pink-300'}`}>
                                            {suggestion.type === 'new_entity' ? 'New Entity' : suggestion.type === 'update_entity' ? 'Update' : suggestion.type === 'new_event' ? 'Timeline' : 'Relationship'}
                                        </span>
                                        <span className="text-xs font-bold text-gray-200">{suggestion.name}</span>
                                    </div>
                                    <p className="text-[10px] text-gray-400 mt-1 italic">"{suggestion.reason}"</p>
                                    {suggestion.eventDescription && <p className="text-[10px] text-orange-200 mt-1">Event: {suggestion.eventDescription}</p>}
                                    {suggestion.relDescription && <p className="text-[10px] text-pink-200 mt-1">Rel: {suggestion.relDescription} with {suggestion.relTargetName}</p>}
                                    {suggestion.relAffinityChange !== undefined && suggestion.relAffinityChange !== 0 && (
                                        <p className={`text-[10px] font-bold mt-1 ${suggestion.relAffinityChange > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                            Affinity: {suggestion.relAffinityChange > 0 ? '+' : ''}{suggestion.relAffinityChange} ({suggestion.relChangeReason})
                                        </p>
                                    )}
                                </div>
                                <div className="flex gap-1">
                                    <button onClick={() => handleAcceptLore(suggestion)} className="p-1 bg-green-900/30 hover:bg-green-600 text-green-200 rounded"><Check className="w-3 h-3"/></button>
                                    <button onClick={() => setLoreSuggestions(prev => prev.filter((_, i) => i !== idx))} className="p-1 bg-red-900/30 hover:bg-red-600 text-red-200 rounded"><X className="w-3 h-3"/></button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* SCHEMA EDITOR */}
             {isBuildingSchema && (
                <div className="bg-gray-800/50 p-3 rounded-lg border border-blue-500/30 space-y-3 mb-4">
                    <div className="flex justify-between items-center"><h4 className="text-xs font-bold text-blue-300 uppercase">Category Editor</h4><select value={schemaToEditId} onChange={(e) => setSchemaToEditId(e.target.value)} className="bg-gray-950 border border-gray-700 rounded p-1 text-xs text-gray-300"><option value="new">+ New Category</option>{bibleSchemas.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></div>
                    <input placeholder="Category Name" value={newSchemaName} onChange={e => setNewSchemaName(e.target.value)} className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-sm text-white focus:border-blue-500"/>
                    <div className="space-y-2">
                        {newSchemaFields.map((field, idx) => (
                            <div key={idx} className="flex items-center justify-between text-xs bg-gray-900 p-2 rounded border border-gray-700">
                                <div className="flex flex-col"><span>{field.label} <span className="text-gray-500">({field.type})</span></span><button onClick={() => { const updated = [...newSchemaFields]; updated[idx].required = !updated[idx].required; setNewSchemaFields(updated); }} className={`text-[9px] text-left mt-0.5 ${field.required ? 'text-red-400' : 'text-gray-500'}`}>{field.required ? 'Required' : 'Optional'}</button></div>
                                <button onClick={() => setNewSchemaFields(prev => prev.filter((_, i) => i !== idx))} className="text-red-400 hover:text-white"><X className="w-3 h-3"/></button>
                            </div>
                        ))}
                    </div>
                    <div className="flex gap-2 items-end bg-gray-900/50 p-2 rounded border border-gray-700 border-dashed">
                        <div className="flex-1 space-y-1">
                            <input placeholder="Field Label (e.g. Mana Cost)" value={tempField.label} onChange={e => setTempField({...tempField, label: e.target.value})} className="w-full bg-gray-950 border border-gray-700 rounded p-1.5 text-xs text-white"/>
                            <div className="flex gap-2"><select value={tempField.type} onChange={e => setTempField({...tempField, type: e.target.value as any})} className="bg-gray-950 border border-gray-700 rounded p-1.5 text-xs text-gray-300"><option value="text">Short Text</option><option value="textarea">Long Text</option></select></div>
                        </div>
                        <Button size="sm" variant="secondary" onClick={handleAddTempField}><Plus className="w-3 h-3"/></Button>
                    </div>
                    <Button size="sm" onClick={handleSaveSchema} className="w-full">{schemaToEditId === 'new' ? 'Create Category' : 'Update Category'}</Button>
                </div>
            )}
            
            {/* BIBLE ITEM EDITOR */}
            {isAddingBible && !isBuildingSchema && (
              <div className="bg-gray-800/50 p-3 rounded-lg border border-gray-700 space-y-3 mb-4">
                <div className="flex justify-between items-center"><h4 className="text-xs font-bold text-gray-400 uppercase">{editingItemId ? 'Edit Entry' : 'New Entry'}</h4><button onClick={() => setIsAddingBible(false)} className="text-gray-500 hover:text-white"><X className="w-3 h-3"/></button></div>

                <div className="flex gap-2 bg-black/20 p-1 rounded">
                    <button onClick={() => setBibleViewMode('data')} className={`flex-1 text-[10px] py-1 rounded ${bibleViewMode === 'data' ? 'bg-gray-700 text-white' : 'text-gray-400'}`}>Data</button>
                    <button onClick={() => setBibleViewMode('events')} className={`flex-1 text-[10px] py-1 rounded ${bibleViewMode === 'events' ? 'bg-gray-700 text-white' : 'text-gray-400'}`}>Timeline</button>
                    <button onClick={() => setBibleViewMode('relations')} className={`flex-1 text-[10px] py-1 rounded ${bibleViewMode === 'relations' ? 'bg-gray-700 text-white' : 'text-gray-400'}`}>Relations</button>
                </div>

                {bibleViewMode === 'data' && (
                    <>
                        <div className="flex gap-2">
                            <select value={selectedSchemaId} onChange={e => setSelectedSchemaId(e.target.value)} disabled={!!editingItemId} className="flex-1 bg-gray-950 border border-gray-700 rounded p-2 text-sm text-gray-300">{bibleSchemas.map(s => (<option key={s.id} value={s.id}>{s.name}</option>))}</select>
                            <button onClick={() => setShowAutoFill(!showAutoFill)} className={`p-2 rounded border border-purple-500/30 ${showAutoFill ? 'bg-purple-500 text-white' : 'bg-gray-900 text-purple-400 hover:bg-purple-900/20'}`} title="AI Auto-Fill"><Wand2 className="w-4 h-4" /></button>
                        </div>
                        {showAutoFill && (
                            <div className="bg-purple-900/10 p-2 rounded border border-purple-500/20 space-y-2 animate-in slide-in-from-top-2">
                                <textarea placeholder={`Describe the ${activeSchema.name.toLowerCase()} briefly... (or leave empty for random)`} value={autoGenSeed} onChange={e => setAutoGenSeed(e.target.value)} className="w-full bg-gray-950 border border-purple-500/30 rounded p-2 text-xs text-white h-16"/>
                                <Button size="sm" onClick={handleAutoGenerate} disabled={isAutoGenerating} className="w-full text-xs bg-purple-600 hover:bg-purple-500">{isAutoGenerating ? <Loader2 className="w-3 h-3 animate-spin mr-2"/> : <Sparkles className="w-3 h-3 mr-2" />} Auto-Fill Fields</Button>
                            </div>
                        )}
                        <input placeholder="Entry Name" value={newItemName} onChange={e => setNewItemName(e.target.value)} className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-sm text-white font-semibold"/>
                        <div className="space-y-3 max-h-60 overflow-y-auto pr-1">
                            {activeSchema.fields.map(field => (
                                <div key={field.key} className="space-y-1">
                                    <label className="text-xs text-gray-400 flex justify-between">{field.label}{field.required && <span className="text-red-400/50 text-[9px] uppercase tracking-wider ml-1">Req</span>}</label>
                                    {field.type === 'textarea' ? (<textarea value={newItemData[field.key] || ''} onChange={e => setNewItemData({...newItemData, [field.key]: e.target.value})} placeholder={field.placeholder} className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-xs text-white h-20 resize-y focus:border-gray-500 transition-colors"/>) : (<input value={newItemData[field.key] || ''} onChange={e => setNewItemData({...newItemData, [field.key]: e.target.value})} placeholder={field.placeholder} className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-xs text-white focus:border-gray-500 transition-colors"/>)}
                                </div>
                            ))}
                        </div>
                    </>
                )}

                {bibleViewMode === 'events' && (
                    <div className="space-y-3">
                        <div className="flex justify-between items-center"><span className="text-xs text-orange-300 font-bold uppercase">Plot Timeline</span><button onClick={() => setNewItemEvents([...newItemEvents, {id: Date.now().toString(), description: 'New Event', timestamp: 'Now'}])} className="text-orange-400 hover:text-white"><Plus className="w-4 h-4"/></button></div>
                        <div className="space-y-2 max-h-60 overflow-y-auto">
                            {newItemEvents.map((evt, idx) => (
                                <div key={idx} className="bg-orange-900/10 p-2 rounded border border-orange-500/20 text-xs">
                                    <div className="flex justify-between"><input value={evt.timestamp || ''} onChange={(e) => { const updated = [...newItemEvents]; updated[idx].timestamp = e.target.value; setNewItemEvents(updated); }} className="bg-transparent text-orange-300/70 text-[10px] w-20" placeholder="Time"/><button onClick={() => setNewItemEvents(prev => prev.filter((_, i) => i !== idx))} className="text-red-500"><X className="w-3 h-3"/></button></div>
                                    <textarea value={evt.description} onChange={(e) => { const updated = [...newItemEvents]; updated[idx].description = e.target.value; setNewItemEvents(updated); }} className="w-full bg-transparent text-gray-300 mt-1 resize-none" rows={2}/>
                                    {evt.contextSnippet && (<div className="text-[9px] text-gray-500 italic mt-1 border-l-2 border-orange-500/30 pl-1 truncate">Src: "{evt.contextSnippet}"</div>)}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {bibleViewMode === 'relations' && (
                    <div className="space-y-3">
                        <div className="flex justify-between items-center"><span className="text-xs text-pink-300 font-bold uppercase">Relationships</span><button onClick={() => setNewItemRelations([...newItemRelations, {targetName: 'Target', type: 'Neutral', description: ''}])} className="text-pink-400 hover:text-white"><Plus className="w-4 h-4"/></button></div>
                         <div className="space-y-2 max-h-60 overflow-y-auto">
                            {newItemRelations.map((rel, idx) => (
                                <div key={idx} className="bg-pink-900/10 p-2 rounded border border-pink-500/20 text-xs">
                                    <div className="flex gap-1 mb-1">
                                        <input value={rel.targetName} onChange={(e) => { const updated = [...newItemRelations]; updated[idx].targetName = e.target.value; setNewItemRelations(updated); }} className="bg-black/20 text-pink-200 w-1/2 p-1 rounded" placeholder="Target"/>
                                        <input value={rel.type} onChange={(e) => { const updated = [...newItemRelations]; updated[idx].type = e.target.value; setNewItemRelations(updated); }} className="bg-black/20 text-pink-200 w-1/2 p-1 rounded" placeholder="Type"/>
                                         <button onClick={() => setNewItemRelations(prev => prev.filter((_, i) => i !== idx))} className="text-red-500"><X className="w-3 h-3"/></button>
                                    </div>
                                    <textarea value={rel.description} onChange={(e) => { const updated = [...newItemRelations]; updated[idx].description = e.target.value; setNewItemRelations(updated); }} placeholder="Description" className="w-full bg-transparent text-gray-300 mt-1 resize-none" rows={2}/>
                                    {/* Manual Affinity Edit */}
                                    <div className="flex items-center gap-2 mt-1">
                                        <label className="text-[9px] text-gray-500">Affinity:</label>
                                        <input type="number" value={rel.affinityScore || 0} onChange={(e) => { const updated = [...newItemRelations]; updated[idx].affinityScore = parseInt(e.target.value); setNewItemRelations(updated); }} className="bg-black/20 text-gray-300 w-12 p-0.5 text-[9px] rounded"/>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
                <Button size="sm" onClick={handleSaveBibleItem} className="w-full">{editingItemId ? <><Save className="w-3 h-3 mr-2"/> Update Entry</> : <><Plus className="w-3 h-3 mr-2"/> Add to Bible</>}</Button>
              </div>
            )}
            
            {/* BIBLE LIST */}
            <div className="space-y-3 pb-4">
              {filteredBibleItems.length === 0 && !isAddingBible && !isBuildingSchema && (<div className="text-center py-8 text-gray-500 text-xs">{searchQuery ? "No matching entries found." : "No entries yet. Add structured data to reference in your story."}</div>)}
              {filteredBibleItems.map(item => {
                  const schema = bibleSchemas.find(s => s.id === item.schemaId);
                  return (
                    <div key={item.id} className="group bg-gray-800/30 border border-gray-700/50 rounded-lg p-3 hover:border-gray-600 transition-all">
                    <div className="flex items-start justify-between">
                        <div><span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${item.schemaId === 'character' ? 'bg-blue-500/20 text-blue-300' : item.schemaId === 'location' ? 'bg-green-500/20 text-green-300' : item.schemaId === 'item' ? 'bg-yellow-500/20 text-yellow-300' : 'bg-purple-500/20 text-purple-300'}`}>{schema?.name || 'Unknown'}</span><h4 className="font-medium text-gray-200 mt-1">{item.name}</h4></div>
                        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button onClick={() => handleEditItem(item)} className="text-gray-500 hover:text-blue-400 p-1"><Edit2 className="w-3 h-3" /></button>
                            <button onClick={() => onDeleteBibleItem(item.id)} className="text-gray-500 hover:text-red-400 p-1"><Trash2 className="w-3 h-3" /></button>
                        </div>
                    </div>
                    <p className="text-xs text-gray-400 mt-2 line-clamp-2">{Object.values(item.data)[0] || "No data"}</p>
                    <div className="flex gap-2 mt-2">
                        {item.events && item.events.length > 0 && (<span className="flex items-center text-[9px] text-orange-400/70"><History className="w-2 h-2 mr-1"/> {item.events.length} Events</span>)}
                        {item.relationships && item.relationships.length > 0 && (<span className="flex items-center text-[9px] text-pink-400/70"><Users2 className="w-2 h-2 mr-1"/> {item.relationships.length} Rels</span>)}
                    </div>
                    </div>
                  );
              })}
            </div>
            </div>
          </div>
        )}

        {/* --- STYLES TAB --- */}
        {activeTab === 'styles' && (
          <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
          <div className="flex flex-col gap-4 animate-in fade-in slide-in-from-right-4 duration-200">
            <div className="flex items-center justify-between"><h3 className="text-sm font-semibold text-white">Style Vault</h3><button onClick={() => { setIsCreatingStyle(!isCreatingStyle); setEditingStyleId(null); setStyleName(''); setStyleSample(''); }} className="p-1 text-purple-400 hover:bg-purple-400/10 rounded"><Plus className="w-4 h-4" /></button></div>
            {isCreatingStyle && !editingStyleId && (
              <div className="bg-gray-800/50 p-3 rounded-lg border border-gray-700 space-y-3">
                <input placeholder="Style Name (e.g., Noir Detective)" value={styleName} onChange={e => setStyleName(e.target.value)} className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-sm text-white"/>
                <div className="space-y-1"><label className="text-xs text-gray-400">Sample Text (Paste ~500 words)</label><textarea placeholder="Paste text here for AI analysis..." value={styleSample} onChange={e => setStyleSample(e.target.value)} className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-xs text-white h-32"/></div>
                <Button size="sm" onClick={handleCreateStyle} className="w-full" disabled={isExtractingStyle}>{isExtractingStyle ? <><Loader2 className="w-3 h-3 animate-spin mr-2"/> Analyzing DNA...</> : 'Extract Style DNA'}</Button>
              </div>
            )}
            {editingStyleId && (
                <div className="bg-gray-800/50 p-3 rounded-lg border border-purple-500/50 space-y-3 shadow-lg">
                    <div className="flex justify-between"><h4 className="text-xs font-bold text-purple-300">Editing DNA</h4><button onClick={() => setEditingStyleId(null)} className="text-gray-500"><X className="w-3 h-3"/></button></div>
                    <div className="space-y-1 relative">
                        <div className="flex justify-between items-center"><label className="text-[10px] text-gray-400 uppercase tracking-wider">Instructions (DNA)</label><button onClick={() => setShowStyleRefine(!showStyleRefine)} className="text-purple-400 hover:text-purple-300 text-[10px] flex items-center gap-1"><Wand2 className="w-3 h-3"/> Refine</button></div>
                        {showStyleRefine && (<div className="mb-2 p-2 bg-purple-900/20 rounded border border-purple-500/30 flex gap-2 animate-in slide-in-from-top-1"><input value={styleRefineInput} onChange={e => setStyleRefineInput(e.target.value)} placeholder="How to tweak? (e.g. 'Make it funnier')" className="flex-1 bg-black/30 border border-purple-500/30 rounded px-2 py-1 text-xs text-white"/><button onClick={handleRefineStyle} disabled={isRefining} className="text-purple-400 hover:text-white">{isRefining ? <Loader2 className="w-3 h-3 animate-spin"/> : <Sparkles className="w-3 h-3"/>}</button></div>)}
                        <textarea value={editedDNA} onChange={e => setEditedDNA(e.target.value)} className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-xs text-gray-300 h-32 font-mono"/>
                    </div>
                    <div className="space-y-1">
                        <div className="flex justify-between items-center"><label className="text-[10px] text-red-400 uppercase tracking-wider flex items-center gap-1"><Ban className="w-3 h-3"/> Negative Constraints</label><button onClick={handleSuggestConstraints} disabled={isSuggestingConstraints} className="text-red-400 hover:text-red-300 text-[10px] flex items-center gap-1" title="Auto-Suggest Constraints">{isSuggestingConstraints ? <Loader2 className="w-3 h-3 animate-spin"/> : <Wand2 className="w-3 h-3"/>} Auto</button></div>
                        <textarea value={editedConstraints} onChange={e => setEditedConstraints(e.target.value)} placeholder="What should the AI AVOID? (e.g., 'Do not use passive voice', 'Avoid slang')" className="w-full bg-gray-950 border border-red-900/30 rounded p-2 text-xs text-red-100 h-16 placeholder-red-900/50"/>
                    </div>
                    <Button size="sm" onClick={() => { const original = styles.find(s => s.id === editingStyleId); if (original) handleSaveStyleEdit(original); }} className="w-full bg-purple-600 hover:bg-purple-500">Save Style Changes</Button>
                </div>
            )}
            <div className="space-y-3 pb-10">
              {styles.length === 0 && !isCreatingStyle && (<div className="text-center py-8 text-gray-500 text-xs">No custom styles. Create one to analyze your writing voice.</div>)}
              {styles.map(style => (
                <div key={style.id} className={`group relative bg-gray-800/30 border rounded-lg p-3 transition-all cursor-pointer ${activeStyleId === style.id ? 'border-purple-500 ring-1 ring-purple-500/50' : 'border-gray-700/50 hover:border-gray-500'} ${editingStyleId === style.id ? 'opacity-50 pointer-events-none' : ''}`} onClick={() => onSelectStyle(style.id === activeStyleId ? null : style.id)}>
                  <div className="flex items-start justify-between"><div><h4 className="font-medium text-gray-200">{style.name}</h4><span className="text-[10px] text-gray-500">DNA Extracted</span></div>{activeStyleId === style.id && (<span className="flex items-center gap-1 text-[10px] font-bold text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded-full">ACTIVE</span>)}</div>
                  <div className="mt-2 text-[10px] text-gray-400 line-clamp-2">{style.dna}</div>
                  {style.negativeConstraints && (<div className="mt-1 text-[9px] text-red-400/70 flex items-center gap-1"><Ban className="w-2 h-2"/> {style.negativeConstraints.substring(0, 30)}...</div>)}
                  <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity bg-gray-900/80 rounded p-0.5">
                    <button onClick={(e) => handleStartEditStyle(style, e)} className="p-1 text-gray-400 hover:text-blue-400 rounded" title="Edit DNA"><Edit2 className="w-3 h-3" /></button>
                    <button onClick={(e) => { e.stopPropagation(); onDeleteStyle(style.id); }} className="p-1 text-gray-400 hover:text-red-400 rounded"><Trash2 className="w-3 h-3" /></button>
                  </div>
                </div>
              ))}
            </div>
          </div>
          </div>
        )}
      

      {/* Footer info */}
      <div className="mt-auto p-4 border-t border-gray-800 bg-gray-950 flex-none">
        <div className="flex items-center justify-between text-xs text-gray-500"><span>CoAuth Beta</span><span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500/50"></span>Online</span></div>
      </div>
    </div>
  );
};
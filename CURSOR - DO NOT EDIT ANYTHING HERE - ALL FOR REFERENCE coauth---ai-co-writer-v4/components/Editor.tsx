

import React, { useRef, useEffect, useState } from 'react';
import MonacoEditor, { OnMount, BeforeMount } from '@monaco-editor/react';
import { Button } from './Button';
import { Sparkles, Wand2, Minimize2, Maximize2, PenTool, Bold, Italic, Heading1, Heading2, BrainCircuit } from 'lucide-react';
import { ModelType, StyleProfile, EditorIssue } from '../types';
import { processInlineSelection, humanizeSelection } from '../services/geminiService';

interface EditorProps {
  content: string;
  onChange: (newContent: string) => void;
  isGenerating: boolean;
  selectedModel: ModelType;
  activeStyleProfile: StyleProfile | null;
  auditResults?: EditorIssue[]; // Visual markers for issues
}

export const Editor: React.FC<EditorProps> = ({ content, onChange, isGenerating, selectedModel, activeStyleProfile, auditResults = [] }) => {
  const editorRef = useRef<any>(null);
  const monacoRef = useRef<any>(null);
  
  // Toolbar State
  const [showToolbar, setShowToolbar] = useState(false);
  const [toolbarPosition, setToolbarPosition] = useState({ top: 0, left: 0 });
  const [selectionRange, setSelectionRange] = useState<any>(null);
  const [selectedText, setSelectedText] = useState('');
  const [isProcessingSelection, setIsProcessingSelection] = useState(false);
  const [customPrompt, setCustomPrompt] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);

  const applyFormatting = (format: 'bold' | 'italic' | 'h1' | 'h2') => {
    if (!editorRef.current) return;
    const editor = editorRef.current;
    const model = editor.getModel();
    const selections = editor.getSelections();
    if (!model || !selections) return;

    const edits: any[] = [];
    
    selections.forEach((selection: any) => {
        // Line-based formatting (Headers)
        if (format === 'h1' || format === 'h2') {
             const startLineNumber = selection.startLineNumber;
             const endLineNumber = selection.endLineNumber;
             
             for (let i = startLineNumber; i <= endLineNumber; i++) {
                 const lineContent = model.getLineContent(i);
                 let newLineContent = lineContent;
                 
                 // Remove existing headers if any to toggle or switch
                 if (lineContent.startsWith('# ')) newLineContent = lineContent.substring(2);
                 else if (lineContent.startsWith('## ')) newLineContent = lineContent.substring(3);
                 else if (lineContent.startsWith('### ')) newLineContent = lineContent.substring(4);
                 
                 // Check if we are "toggling off" (i.e. if it was H1 and we clicked H1, it becomes text)
                 const wasH1 = lineContent.startsWith('# ');
                 const wasH2 = lineContent.startsWith('## ');
                 
                 if (format === 'h1' && !wasH1) {
                     newLineContent = '# ' + newLineContent;
                 } else if (format === 'h2' && !wasH2) {
                     newLineContent = '## ' + newLineContent;
                 }
                 
                 // Replace the full line
                 edits.push({
                     range: new monacoRef.current.Range(i, 1, i, lineContent.length + 1),
                     text: newLineContent,
                     forceMoveMarkers: true
                 });
             }
        } 
        // Inline formatting (Bold/Italic)
        else {
            const text = model.getValueInRange(selection);
            const symbol = format === 'bold' ? '**' : '*';
            let newText = "";
            
            // Simple toggle logic
            if (text.startsWith(symbol) && text.endsWith(symbol) && text.length >= symbol.length * 2) {
                 newText = text.substring(symbol.length, text.length - symbol.length);
            } else {
                 newText = `${symbol}${text}${symbol}`;
            }
            
            edits.push({
                range: selection,
                text: newText,
                forceMoveMarkers: true
            });
        }
    });
    
    editor.executeEdits('formatting', edits);
    editor.focus();
  };

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;

    // Register Keyboard Shortcuts
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyB, () => {
        applyFormatting('bold');
    });

    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyI, () => {
        applyFormatting('italic');
    });
    
    // Header Shortcuts (Ctrl+1 / Ctrl+2)
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Digit1, () => {
        applyFormatting('h1');
    });
    
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Digit2, () => {
        applyFormatting('h2');
    });

    // Listen to selection changes
    editor.onDidChangeCursorSelection((e) => {
        const selection = editor.getSelection();
        if (selection && !selection.isEmpty()) {
            const model = editor.getModel();
            const text = model?.getValueInRange(selection);
            if (text) {
                const rect = editor.getScrolledVisiblePosition(selection.getStartPosition());
                if (rect) {
                    // Offset for toolbar positioning
                    const domNode = editor.getDomNode();
                    const containerRect = domNode?.getBoundingClientRect();
                    
                    if (containerRect) {
                        setToolbarPosition({
                            top: rect.top + 20, // Move a bit down from top of selection
                            left: rect.left + 50
                        });
                        setSelectionRange(selection);
                        setSelectedText(text);
                        setShowToolbar(true);
                        // Hide custom input when selection changes
                        setShowCustomInput(false);
                    }
                }
            }
        } else {
            setShowToolbar(false);
            setSelectionRange(null);
        }
    });

    // Register Code Action Provider for Quick Fixes (Grammarly style)
    monaco.languages.registerCodeActionProvider('markdown', {
        provideCodeActions: (model, range, context, token) => {
            const actions: any[] = [];
            
            // Context.markers contains the markers that overlap with the current cursor/hover range
            context.markers.forEach(marker => {
                // We use the marker's source/message to find the corresponding EditorIssue
                // Since we don't have direct access to 'auditResults' inside this closure easily if it's stale,
                // we rely on the marker data we injected.
                // NOTE: We embedded the 'fixSuggestion' into the marker 'code' property as a hack,
                // or we can try to find it in the external auditResults if available.
                
                // Let's use a convention: marker.code contains the fix suggestion string if available.
                // Or if it's an object { value: string, target: uri }, we extract value.
                
                // However, marker.code is usually for error codes (string or {value, link}).
                // Let's rely on finding the issue in the prop.
                // We'll access the LATEST auditResults via a ref if needed, but for now let's try to match by message.
                
                // SIMPLE HACK: We put the fix directly in the marker structure when creating it? No, can't add custom props to IMarkerData easily.
                // ALTERNATIVE: Use the message to look up.
                
                // Actually, let's just create a generic "Fix this" action if we can't look it up, 
                // but we really want the specific fix.
                
                // Let's assume marker.source is "AI Editor"
                if (marker.source === "AI Editor") {
                     // We can't access `auditResults` reliably here due to closure staleness unless we use a ref.
                     // But we can cheat: put the fix in the `code` field as a string.
                     if (marker.code && typeof marker.code === 'string') {
                         actions.push({
                             title: `Quick Fix: ${marker.code}`,
                             kind: 'quickfix',
                             isPreferred: true,
                             edit: {
                                 edits: [{
                                     resource: model.uri,
                                     textEdit: {
                                         range: marker,
                                         text: marker.code
                                     }
                                 }]
                             }
                         });
                     }
                }
            });
            
            return {
                actions: actions,
                dispose: () => {}
            };
        }
    });
  };

  const handleBeforeMount: BeforeMount = (monaco) => {
    // Define a custom theme that matches the app's aesthetic
    monaco.editor.defineTheme('coauth-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [
        { token: '', foreground: 'c0caf5' }, // text-ink color
        { token: 'strong', fontStyle: 'bold', foreground: '7aa2f7' }, // bold
        { token: 'emphasis', fontStyle: 'italic', foreground: 'bb9af7' }, // italic
        { token: 'keyword.heading', fontStyle: 'bold', foreground: '7dcfff' }, // headings
      ],
      colors: {
        'editor.background': '#1a1b26', // bg-paper
        'editor.foreground': '#c0caf5',
        'editor.lineHighlightBackground': '#1a1b26', // hide line highlight
        'editor.selectionBackground': '#7aa2f74d', // accent with opacity
        'scrollbarSlider.background': '#414868',
        'scrollbarSlider.hoverBackground': '#565f89',
        'scrollbarSlider.activeBackground': '#565f89',
      }
    });
  };

  // --- VISUAL MARKERS (Squiggles) ---
  useEffect(() => {
      if (editorRef.current && monacoRef.current) {
          const editor = editorRef.current;
          const monaco = monacoRef.current;
          const model = editor.getModel();
          
          if (!model) return;

          const markers: any[] = [];
          
          auditResults.forEach(issue => {
              // Find matches in the text
              const matches = model.findMatches(issue.snippet);
              
              matches.forEach((match: any) => {
                  let severity = monaco.MarkerSeverity.Info;
                  if (issue.type === 'logic') severity = monaco.MarkerSeverity.Error;
                  if (issue.type === 'formatting' || issue.category?.toLowerCase().includes('spell')) severity = monaco.MarkerSeverity.Warning;
                  if (issue.type === 'humanization') severity = monaco.MarkerSeverity.Hint;

                  markers.push({
                      severity: severity,
                      message: `${issue.category || issue.type}: ${issue.description}`,
                      startLineNumber: match.range.startLineNumber,
                      startColumn: match.range.startColumn,
                      endLineNumber: match.range.endLineNumber,
                      endColumn: match.range.endColumn,
                      source: 'AI Editor',
                      // HACK: Store the fix suggestion in the 'code' field so the CodeActionProvider can read it
                      code: issue.fixSuggestion || "" 
                  });
              });
          });

          monaco.editor.setModelMarkers(model, 'owner', markers);
      }
  }, [auditResults, content]); // Re-run when audit results update or content changes (though markers clear on edit usually)

  // Scroll to bottom during generation
  useEffect(() => {
    if (isGenerating && editorRef.current) {
      const model = editorRef.current.getModel();
      if (model) {
        // Reveal the last line to keep up with streaming text
        const lineCount = model.getLineCount();
        editorRef.current.revealLine(lineCount);
      }
    }
  }, [content, isGenerating]);

  const executeInlineEdit = async (instruction: string) => {
      if (!editorRef.current || !selectionRange || !selectedText) return;
      
      setIsProcessingSelection(true);
      try {
          const newText = await processInlineSelection(
              selectedText, 
              instruction, 
              content, 
              selectedModel, 
              activeStyleProfile
          );
          
          if (newText) {
              const selection = selectionRange;
              editorRef.current.executeEdits("ai-inline", [{
                  range: selection,
                  text: newText,
                  forceMoveMarkers: true
              }]);
          }
      } catch (e) {
          alert("Inline edit failed");
      } finally {
          setIsProcessingSelection(false);
          setShowToolbar(false);
          setShowCustomInput(false);
          editorRef.current.focus();
      }
  };

  const executeHumanize = async () => {
      if (!editorRef.current || !selectionRange || !selectedText) return;
      setIsProcessingSelection(true);
      try {
          const newText = await humanizeSelection(selectedText, selectedModel);
          if (newText) {
               editorRef.current.executeEdits("ai-humanize", [{
                  range: selectionRange,
                  text: newText,
                  forceMoveMarkers: true
              }]);
          }
      } catch (e) {
          alert("Humanization failed");
      } finally {
          setIsProcessingSelection(false);
          setShowToolbar(false);
          editorRef.current.focus();
      }
  };

  return (
    <div className="flex-1 h-full w-full relative group">
      <MonacoEditor
        height="100%"
        defaultLanguage="markdown"
        value={content}
        onChange={(value) => onChange(value || '')}
        theme="coauth-dark"
        beforeMount={handleBeforeMount}
        onMount={handleEditorDidMount}
        loading={
          <div className="flex items-center justify-center h-full text-gray-500">
            Initializing Editor...
          </div>
        }
        options={{
          fontFamily: "'Merriweather', 'Georgia', serif",
          fontSize: 18,
          lineHeight: 32,
          wordWrap: 'on',
          minimap: { enabled: false },
          lineNumbers: 'off',
          glyphMargin: false,
          folding: false,
          scrollBeyondLastLine: false,
          renderLineHighlight: 'none',
          contextmenu: true,
          smoothScrolling: true,
          cursorBlinking: 'smooth',
          cursorWidth: 2,
          padding: { top: 32, bottom: 32 },
          overviewRulerBorder: false,
          hideCursorInOverviewRuler: true,
          renderWhitespace: 'none',
          scrollbar: {
            vertical: 'visible',
            horizontal: 'hidden',
            useShadows: false,
            verticalScrollbarSize: 10,
          },
          // Enable quick suggestions for code actions
          lightbulb: {
            enabled: true
          }
        }}
      />
      
      {/* Floating Inline Toolbar */}
      {showToolbar && (
          <div 
             className="absolute z-50 bg-[#1a1b26] border border-gray-700 rounded-lg shadow-2xl p-1 flex flex-col gap-2 animate-in fade-in zoom-in-95"
             style={{ top: Math.max(10, toolbarPosition.top - 50), left: Math.max(10, toolbarPosition.left) }}
          >
              {!showCustomInput ? (
                <div className="flex gap-1 items-center">
                  <Button size="sm" variant="ghost" onClick={() => applyFormatting('bold')} title="Bold (Ctrl+B)" disabled={isProcessingSelection} className="w-8 px-0"><Bold className="w-3 h-3"/></Button>
                  <Button size="sm" variant="ghost" onClick={() => applyFormatting('italic')} title="Italic (Ctrl+I)" disabled={isProcessingSelection} className="w-8 px-0"><Italic className="w-3 h-3"/></Button>
                  <div className="w-px bg-gray-700 h-4 mx-1"/>
                  <Button size="sm" variant="ghost" onClick={() => applyFormatting('h1')} title="Chapter Title (H1 / Ctrl+1)" disabled={isProcessingSelection} className="w-8 px-0"><Heading1 className="w-3 h-3"/></Button>
                  <Button size="sm" variant="ghost" onClick={() => applyFormatting('h2')} title="Subheading (H2 / Ctrl+2)" disabled={isProcessingSelection} className="w-8 px-0"><Heading2 className="w-3 h-3"/></Button>
                  <div className="w-px bg-gray-700 h-6 mx-1 self-center"/>
                  <Button size="sm" variant="ghost" onClick={() => executeInlineEdit("Rewrite to improve quality and style")} title="Rewrite" disabled={isProcessingSelection}><PenTool className="w-3 h-3 mr-1"/> Rewrite</Button>
                  <Button size="sm" variant="ghost" onClick={executeHumanize} title="De-AI: Rewrite to be grittier and more natural" disabled={isProcessingSelection} className="border border-purple-500/30 text-purple-200 hover:bg-purple-900/30"><BrainCircuit className="w-3 h-3 mr-1 text-purple-400"/> Humanize</Button>
                  <Button size="sm" variant="ghost" onClick={() => executeInlineEdit("Expand this section with more detail")} title="Expand" disabled={isProcessingSelection}><Maximize2 className="w-3 h-3 mr-1"/> Expand</Button>
                  <Button size="sm" variant="ghost" onClick={() => executeInlineEdit("Shorten and simplify this section")} title="Shorten" disabled={isProcessingSelection}><Minimize2 className="w-3 h-3 mr-1"/> Shorten</Button>
                  <Button size="sm" variant="ghost" onClick={() => setShowCustomInput(true)} title="Custom Instruction" disabled={isProcessingSelection}><Wand2 className="w-3 h-3 mr-1"/> Custom</Button>
                </div>
              ) : (
                  <div className="flex gap-1 p-1">
                      <input 
                         value={customPrompt} 
                         onChange={(e) => setCustomPrompt(e.target.value)} 
                         placeholder="Instruction..." 
                         className="bg-black/30 border border-gray-700 rounded px-2 text-xs text-white w-48"
                         autoFocus
                         onKeyDown={(e) => {
                             if(e.key === 'Enter') executeInlineEdit(customPrompt);
                             if(e.key === 'Escape') setShowCustomInput(false);
                         }}
                      />
                      <Button size="sm" onClick={() => executeInlineEdit(customPrompt)} disabled={isProcessingSelection || !customPrompt}><Sparkles className="w-3 h-3"/></Button>
                  </div>
              )}
          </div>
      )}

      {/* Subtle indicator when typing/generating */}
      <div className={`absolute bottom-4 right-8 text-xs text-accent transition-opacity duration-500 pointer-events-none z-10 ${isGenerating ? 'opacity-100' : 'opacity-0'}`}>
        AI Writing...
      </div>
    </div>
  );
};
import { useEffect, useState, useCallback, useRef } from 'react';
import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import {
    $getSelection,
    $isRangeSelection,
    $getRoot,
    $createTextNode,
    COMMAND_PRIORITY_LOW,
    SELECTION_CHANGE_COMMAND,
    TextNode,
} from 'lexical';
import { $createParagraphNode } from 'lexical';
import { createPortal } from 'react-dom';
import { Button } from '@/Components/ui/button';
import { Input } from '@/Components/ui/input';
import {
    Sparkles,
    PenLine,
    Heart,
    Loader2,
    X,
    ChevronRight,
} from 'lucide-react';

interface SelectionToolbarPluginProps {
    workspaceId: string;
    projectId: string;
    chapterOrder: number;
    aiModel?: string;
    onRewriteComplete?: (oldText: string, newText: string) => void;
}

interface ToolbarPosition {
    top: number;
    left: number;
}

export function SelectionToolbarPlugin({
    workspaceId,
    projectId,
    chapterOrder,
    aiModel = 'gemini-2.5-flash',
    onRewriteComplete,
}: SelectionToolbarPluginProps) {
    const [editor] = useLexicalComposerContext();
    const [isVisible, setIsVisible] = useState(false);
    const [position, setPosition] = useState<ToolbarPosition>({ top: 0, left: 0 });
    const [selectedText, setSelectedText] = useState('');
    const [contextBefore, setContextBefore] = useState('');
    const [contextAfter, setContextAfter] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [showCustomPrompt, setShowCustomPrompt] = useState(false);
    const [customPrompt, setCustomPrompt] = useState('');
    const toolbarRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);
    const isInteractingRef = useRef(false);
    const lastSelectionRef = useRef<string>('');

    // Get context around selection (before and after text)
    const getSelectionContext = useCallback(() => {
        let before = '';
        let after = '';
        let selected = '';

        editor.getEditorState().read(() => {
            const selection = $getSelection();
            if (!$isRangeSelection(selection)) return;

            selected = selection.getTextContent();
            
            // Get the full text content of the editor
            const root = editor.getEditorState()._nodeMap.get('root');
            if (!root) return;

            const fullText = root.getTextContent();
            const selectedText = selection.getTextContent();
            
            // Find where the selected text appears
            const selectedIndex = fullText.indexOf(selectedText);
            if (selectedIndex === -1) return;

            // Get context (up to 500 characters before and after for better context)
            const contextLength = 500;
            before = fullText.substring(Math.max(0, selectedIndex - contextLength), selectedIndex);
            after = fullText.substring(selectedIndex + selectedText.length, selectedIndex + selectedText.length + contextLength);
        });

        return { before, after, selected };
    }, [editor]);

    // Update toolbar position based on selection
    const updateToolbar = useCallback(() => {
        // Don't update if we're interacting with the toolbar
        if (isInteractingRef.current) {
            return;
        }

        const nativeSelection = window.getSelection();
        
        if (!nativeSelection || nativeSelection.rangeCount === 0 || nativeSelection.isCollapsed) {
            setIsVisible(false);
            setShowCustomPrompt(false);
            return;
        }

        const selectedTextContent = nativeSelection.toString().trim();
        
        // Require at least 3 characters to show toolbar
        if (selectedTextContent.length < 3) {
            setIsVisible(false);
            setShowCustomPrompt(false);
            return;
        }

        // Check if selection is within the editor
        const editorElement = editor.getRootElement();
        if (!editorElement) {
            setIsVisible(false);
            return;
        }

        // Check if selection is inside the editor element
        const range = nativeSelection.getRangeAt(0);
        if (!editorElement.contains(range.commonAncestorContainer)) {
            setIsVisible(false);
            return;
        }

        const rect = range.getBoundingClientRect();
        
        // Store the selected text
        setSelectedText(selectedTextContent);
        lastSelectionRef.current = selectedTextContent;
        
        // Get context
        const context = getSelectionContext();
        setContextBefore(context.before);
        setContextAfter(context.after);

        // Calculate position (above the selection)
        const toolbarWidth = 300;
        const selectionMidX = rect.left + rect.width / 2;
        let left = selectionMidX - toolbarWidth / 2;
        
        // Keep toolbar within viewport
        left = Math.max(10, Math.min(left, window.innerWidth - toolbarWidth - 10));
        
        // Position above selection with some padding
        let top = rect.top + window.scrollY - 55;
        
        // If too close to top, show below selection
        if (top < 10) {
            top = rect.bottom + window.scrollY + 10;
        }
        
        setPosition({ top, left });
        setIsVisible(true);
    }, [editor, getSelectionContext]);

    // Listen for selection changes with debounce
    useEffect(() => {
        let timeoutId: NodeJS.Timeout | null = null;
        
        const handleSelectionChange = () => {
            // Don't update if interacting with toolbar
            if (isInteractingRef.current) return;
            
            // Debounce the update
            if (timeoutId) clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                updateToolbar();
            }, 150);
        };

        const removeListener = editor.registerCommand(
            SELECTION_CHANGE_COMMAND,
            () => {
                handleSelectionChange();
                return false;
            },
            COMMAND_PRIORITY_LOW
        );

        // Listen for mouseup to catch selection end
        const handleMouseUp = (e: MouseEvent) => {
            // Don't trigger if clicking on toolbar
            if (toolbarRef.current?.contains(e.target as Node)) {
                return;
            }
            
            // Delay to let selection settle
            setTimeout(() => {
                if (!isInteractingRef.current) {
                    updateToolbar();
                }
            }, 50);
        };

        document.addEventListener('mouseup', handleMouseUp);

        return () => {
            removeListener();
            document.removeEventListener('mouseup', handleMouseUp);
            if (timeoutId) clearTimeout(timeoutId);
        };
    }, [editor, updateToolbar]);

    // Handle toolbar interaction state
    const handleToolbarMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        isInteractingRef.current = true;
    }, []);

    const handleToolbarMouseUp = useCallback((e: React.MouseEvent) => {
        e.stopPropagation();
    }, []);

    // Focus input when custom prompt is shown
    useEffect(() => {
        if (showCustomPrompt && inputRef.current) {
            // Small delay to ensure DOM is ready
            setTimeout(() => {
                inputRef.current?.focus();
            }, 50);
        }
    }, [showCustomPrompt]);

    // Hide toolbar when clicking outside (but not when clicking toolbar itself)
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            // If clicking on toolbar, don't hide
            if (toolbarRef.current?.contains(e.target as Node)) {
                return;
            }
            
            // Reset interaction state
            isInteractingRef.current = false;
            
            // If clicking in editor, let selection change handler manage visibility
            const editorElement = editor.getRootElement();
            if (editorElement?.contains(e.target as Node)) {
                return;
            }
            
            // Clicking outside editor - hide toolbar
            setIsVisible(false);
            setShowCustomPrompt(false);
            setCustomPrompt('');
        };

        // Use mousedown for earlier detection
        document.addEventListener('mousedown', handleClickOutside);
        
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [editor]);

    // Handle escape key
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isVisible) {
                setIsVisible(false);
                setShowCustomPrompt(false);
                setCustomPrompt('');
                isInteractingRef.current = false;
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
        };
    }, [isVisible]);

    // Handle rewrite action
    const handleRewrite = async (action: 'rewrite' | 'humanize' | 'custom', customInstruction?: string) => {
        const textToRewrite = selectedText || lastSelectionRef.current;
        if (!textToRewrite || isLoading) return;

        setIsLoading(true);
        isInteractingRef.current = true;

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
            
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/rewrite-selection`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'X-CSRF-TOKEN': csrfToken,
                    },
                    body: JSON.stringify({
                        selected_text: textToRewrite,
                        context_before: contextBefore,
                        context_after: contextAfter,
                        action: action,
                        custom_instruction: customInstruction || customPrompt,
                        chapter_order: chapterOrder,
                        model: aiModel,
                    }),
                }
            );

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to rewrite text');
            }

            const data = await response.json();
            
            if (data.success && data.new_text) {
                // Replace the text in the editor using find-and-replace
                // since the original selection is gone after the API call
                editor.update(() => {
                    const root = $getRoot();
                    
                    // Collect all text nodes and their positions
                    const textNodes: Array<{ node: TextNode; start: number; end: number }> = [];
                    let currentIndex = 0;
                    
                    const collectTextNodes = (node: any) => {
                        if (node instanceof TextNode) {
                            const nodeText = node.getTextContent();
                            textNodes.push({
                                node,
                                start: currentIndex,
                                end: currentIndex + nodeText.length
                            });
                            currentIndex += nodeText.length;
                        } else if (node.getChildren) {
                            const children = node.getChildren();
                            for (let i = 0; i < children.length; i++) {
                                collectTextNodes(children[i]);
                                // Add newline character for paragraph breaks (except last child)
                                if (node.getType?.() === 'root' && i < children.length - 1) {
                                    currentIndex += 1; // Account for newline between paragraphs
                                }
                            }
                        }
                    };
                    
                    collectTextNodes(root);
                    
                    const textContent = root.getTextContent();
                    const startIndex = textContent.indexOf(textToRewrite);
                    
                    if (startIndex === -1) {
                        console.warn('Original text not found in editor');
                        return;
                    }
                    
                    const endIndex = startIndex + textToRewrite.length;
                    
                    // Find which nodes contain the start and end of our selection
                    let startNode: TextNode | null = null;
                    let startOffset = 0;
                    let endNode: TextNode | null = null;
                    let endOffset = 0;
                    
                    // Recalculate positions accounting for newlines properly
                    let charPos = 0;
                    const allParagraphs = root.getChildren();
                    
                    for (let pIdx = 0; pIdx < allParagraphs.length; pIdx++) {
                        const para = allParagraphs[pIdx];
                        if (!para.getChildren) continue;
                        
                        const children = para.getChildren();
                        for (const child of children) {
                            if (child instanceof TextNode) {
                                const nodeText = child.getTextContent();
                                const nodeStart = charPos;
                                const nodeEnd = charPos + nodeText.length;
                                
                                // Check if this node contains start
                                if (!startNode && startIndex >= nodeStart && startIndex < nodeEnd) {
                                    startNode = child;
                                    startOffset = startIndex - nodeStart;
                                }
                                
                                // Check if this node contains end
                                if (!endNode && endIndex > nodeStart && endIndex <= nodeEnd) {
                                    endNode = child;
                                    endOffset = endIndex - nodeStart;
                                }
                                
                                charPos += nodeText.length;
                            }
                        }
                        
                        // Add newline for paragraph break (matches getTextContent behavior)
                        if (pIdx < allParagraphs.length - 1) {
                            charPos += 1;
                        }
                    }
                    
                    if (!startNode || !endNode) {
                        console.warn('Could not find start/end nodes for replacement');
                        return;
                    }
                    
                    // Case 1: Start and end are in the same node
                    if (startNode === endNode) {
                        const nodeText = startNode.getTextContent();
                        const newText = nodeText.substring(0, startOffset) + 
                                       data.new_text + 
                                       nodeText.substring(endOffset);
                        startNode.setTextContent(newText);
                    } else {
                        // Case 2: Text spans multiple nodes
                        // Strategy: Put all new text in start node, clear middle nodes, trim end node
                        
                        // Track nodes to process
                        let inRange = false;
                        const nodesToRemove: TextNode[] = [];
                        let foundEnd = false;
                        
                        for (let pIdx = 0; pIdx < allParagraphs.length && !foundEnd; pIdx++) {
                            const para = allParagraphs[pIdx];
                            if (!para.getChildren) continue;
                            
                            const children = para.getChildren();
                            for (const child of children) {
                                if (child instanceof TextNode) {
                                    if (child === startNode) {
                                        // Keep text before selection, add new text
                                        const nodeText = child.getTextContent();
                                        child.setTextContent(nodeText.substring(0, startOffset) + data.new_text);
                                        inRange = true;
                                    } else if (child === endNode) {
                                        // Keep text after selection
                                        const nodeText = child.getTextContent();
                                        const remainingText = nodeText.substring(endOffset);
                                        if (remainingText) {
                                            child.setTextContent(remainingText);
                                        } else {
                                            nodesToRemove.push(child);
                                        }
                                        foundEnd = true;
                                        break;
                                    } else if (inRange) {
                                        // Middle node - mark for removal
                                        nodesToRemove.push(child);
                                    }
                                }
                            }
                        }
                        
                        // Remove middle nodes
                        for (const node of nodesToRemove) {
                            const parent = node.getParent();
                            node.remove();
                            // If parent paragraph is now empty, remove it too
                            if (parent && parent.getChildrenSize?.() === 0) {
                                parent.remove();
                            }
                        }
                    }
                });

                // Notify parent component
                if (onRewriteComplete) {
                    onRewriteComplete(textToRewrite, data.new_text);
                }

                // Hide toolbar after successful rewrite
                setIsVisible(false);
                setShowCustomPrompt(false);
                setCustomPrompt('');
            }
        } catch (error) {
            console.error('Rewrite error:', error);
            alert(error instanceof Error ? error.message : 'Failed to rewrite text');
        } finally {
            setIsLoading(false);
            isInteractingRef.current = false;
        }
    };

    // Handle custom button click
    const handleCustomClick = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        isInteractingRef.current = true;
        setShowCustomPrompt(true);
    }, []);

    // Handle back button click
    const handleBackClick = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setShowCustomPrompt(false);
        setCustomPrompt('');
    }, []);

    // Handle action button clicks
    const handleActionClick = useCallback((action: 'rewrite' | 'humanize') => (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        isInteractingRef.current = true;
        handleRewrite(action);
    }, [handleRewrite]);

    // Handle submit button click
    const handleSubmitClick = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (customPrompt.trim()) {
            handleRewrite('custom', customPrompt);
        }
    }, [customPrompt, handleRewrite]);

    // Handle input changes
    const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        setCustomPrompt(e.target.value);
    }, []);

    // Handle input keydown
    const handleInputKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
        e.stopPropagation();
        if (e.key === 'Enter' && customPrompt.trim()) {
            e.preventDefault();
            handleRewrite('custom', customPrompt);
        } else if (e.key === 'Escape') {
            e.preventDefault();
            setShowCustomPrompt(false);
            setCustomPrompt('');
        }
    }, [customPrompt, handleRewrite]);

    // Handle input focus
    const handleInputFocus = useCallback(() => {
        isInteractingRef.current = true;
    }, []);

    // Toolbar component
    const toolbar = isVisible ? (
        <div
            ref={toolbarRef}
            className="fixed z-[9999] animate-in fade-in-0 zoom-in-95 duration-100"
            style={{
                top: `${position.top}px`,
                left: `${position.left}px`,
            }}
            onMouseDown={handleToolbarMouseDown}
            onMouseUp={handleToolbarMouseUp}
            onClick={(e) => e.stopPropagation()}
        >
            <div className="bg-zinc-900 text-white rounded-lg shadow-2xl border border-zinc-700 overflow-hidden">
                {!showCustomPrompt ? (
                    <div className="flex items-center gap-1 p-1.5">
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 px-3 text-white hover:bg-zinc-800 hover:text-white gap-2"
                            onClick={handleActionClick('rewrite')}
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <PenLine className="h-4 w-4" />
                            )}
                            <span className="text-sm">Rewrite</span>
                        </Button>
                        
                        <div className="w-px h-5 bg-zinc-700" />
                        
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 px-3 text-white hover:bg-zinc-800 hover:text-white gap-2"
                            onClick={handleActionClick('humanize')}
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <Heart className="h-4 w-4" />
                            )}
                            <span className="text-sm">Humanize</span>
                        </Button>
                        
                        <div className="w-px h-5 bg-zinc-700" />
                        
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 px-3 text-white hover:bg-zinc-800 hover:text-white gap-2"
                            onClick={handleCustomClick}
                            disabled={isLoading}
                        >
                            <Sparkles className="h-4 w-4" />
                            <span className="text-sm">Custom</span>
                            <ChevronRight className="h-3 w-3" />
                        </Button>
                    </div>
                ) : (
                    <div className="p-2 w-80">
                        <div className="flex items-center gap-2 mb-2">
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6 text-zinc-400 hover:text-white hover:bg-zinc-800"
                                onClick={handleBackClick}
                            >
                                <X className="h-4 w-4" />
                            </Button>
                            <span className="text-sm text-zinc-400">Custom instruction</span>
                        </div>
                        <div className="flex gap-2">
                            <Input
                                ref={inputRef}
                                placeholder="e.g., Make it more dramatic..."
                                value={customPrompt}
                                onChange={handleInputChange}
                                onKeyDown={handleInputKeyDown}
                                onFocus={handleInputFocus}
                                className="h-8 bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500 text-sm focus:ring-violet-500 focus:border-violet-500"
                                autoFocus
                            />
                            <Button
                                size="sm"
                                className="h-8 px-3 bg-violet-600 hover:bg-violet-700 shrink-0"
                                onClick={handleSubmitClick}
                                disabled={isLoading || !customPrompt.trim()}
                            >
                                {isLoading ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    <Sparkles className="h-4 w-4" />
                                )}
                            </Button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    ) : null;

    // Render toolbar via portal to body
    return createPortal(toolbar, document.body);
}

export default SelectionToolbarPlugin;

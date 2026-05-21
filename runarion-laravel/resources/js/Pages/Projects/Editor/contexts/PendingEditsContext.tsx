import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

export interface PendingEdit {
    id: string;
    chapter: string;
    oldText: string;
    newText: string;
    reason?: string;
    status: 'pending' | 'accepted' | 'rejected' | 'stale';
    // Position info for inline rendering
    matchedStart?: number;
    matchedEnd?: number;
    matchConfidence?: number;
}

export type AdvisorMode = 'chat' | 'agent';

// Normalize text for comparison
function normalizeForComparison(text: string): string {
    return text
        .replace(/[\u2018\u2019\u201A\u201B\u2032\u2035']/g, "'")
        .replace(/[\u201C\u201D\u201E\u201F\u2033\u2036"]/g, '"')
        .replace(/[\u2014\u2015\u2012\u2013—–-]/g, '-')
        .replace(/\s+/g, ' ')
        .trim()
        .toLowerCase();
}

// Check if two edit targets overlap (same or similar oldText)
function editsOverlap(edit1: PendingEdit, edit2: PendingEdit): boolean {
    const norm1 = normalizeForComparison(edit1.oldText);
    const norm2 = normalizeForComparison(edit2.oldText);
    
    // Exact match
    if (norm1 === norm2) return true;
    
    // One contains the other (partial overlap)
    if (norm1.includes(norm2) || norm2.includes(norm1)) return true;
    
    // Significant word overlap (>60% of words match)
    const words1 = new Set(norm1.split(' ').filter(w => w.length > 3));
    const words2 = new Set(norm2.split(' ').filter(w => w.length > 3));
    
    if (words1.size === 0 || words2.size === 0) return false;
    
    let overlap = 0;
    for (const word of words1) {
        if (words2.has(word)) overlap++;
    }
    
    const overlapRatio = overlap / Math.min(words1.size, words2.size);
    return overlapRatio > 0.6;
}

interface PendingEditsContextType {
    // Mode
    advisorMode: AdvisorMode;
    setAdvisorMode: (mode: AdvisorMode) => void;
    
    // Pending edits
    pendingEdits: PendingEdit[];
    addPendingEdit: (edit: Omit<PendingEdit, 'id' | 'status'>) => string;
    addPendingEdits: (edits: Omit<PendingEdit, 'id' | 'status'>[]) => string[];
    removePendingEdit: (id: string) => void;
    acceptEdit: (id: string) => PendingEdit | undefined;
    rejectEdit: (id: string) => void;
    clearAllEdits: () => void;
    invalidateOverlappingEdits: (acceptedEdit: PendingEdit) => void;
    markEditAsStale: (id: string) => void;
    
    // Active edit (being shown in editor)
    activeEditId: string | null;
    setActiveEditId: (id: string | null) => void;
    
    // Get edit by id
    getEditById: (id: string) => PendingEdit | undefined;
}

const PendingEditsContext = createContext<PendingEditsContextType | null>(null);

export function PendingEditsProvider({ children }: { children: ReactNode }) {
    const [advisorMode, setAdvisorMode] = useState<AdvisorMode>('chat');
    const [pendingEdits, setPendingEdits] = useState<PendingEdit[]>([]);
    const [activeEditId, setActiveEditId] = useState<string | null>(null);

    const generateId = () => `edit-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    const addPendingEdit = useCallback((edit: Omit<PendingEdit, 'id' | 'status'>) => {
        const id = generateId();
        const newEdit: PendingEdit = {
            ...edit,
            id,
            status: 'pending',
        };
        setPendingEdits(prev => [...prev, newEdit]);
        return id;
    }, []);

    const addPendingEdits = useCallback((edits: Omit<PendingEdit, 'id' | 'status'>[]) => {
        const newEdits: PendingEdit[] = edits.map(edit => ({
            ...edit,
            id: generateId(),
            status: 'pending',
        }));
        setPendingEdits(prev => [...prev, ...newEdits]);
        return newEdits.map(e => e.id);
    }, []);

    const removePendingEdit = useCallback((id: string) => {
        setPendingEdits(prev => prev.filter(e => e.id !== id));
        if (activeEditId === id) {
            setActiveEditId(null);
        }
    }, [activeEditId]);

    // Invalidate edits that overlap with an accepted edit
    const invalidateOverlappingEdits = useCallback((acceptedEdit: PendingEdit) => {
        setPendingEdits(prev => {
            return prev.map(edit => {
                if (edit.id === acceptedEdit.id) return edit;
                if (edit.status !== 'pending') return edit;
                
                // Check if this edit overlaps with the accepted one
                if (editsOverlap(edit, acceptedEdit)) {
                    console.log('[PendingEdits] Marking edit as stale (overlaps with accepted):', edit.oldText.substring(0, 50));
                    return { ...edit, status: 'stale' as const };
                }
                return edit;
            });
        });
    }, []);

    const acceptEdit = useCallback((id: string) => {
        let acceptedEdit: PendingEdit | undefined;
        setPendingEdits(prev => {
            const edit = prev.find(e => e.id === id);
            if (edit) {
                acceptedEdit = { ...edit, status: 'accepted' };
            }
            return prev.filter(e => e.id !== id);
        });
        
        // Invalidate overlapping edits
        if (acceptedEdit) {
            // Use setTimeout to avoid state update conflicts
            setTimeout(() => {
                invalidateOverlappingEdits(acceptedEdit!);
            }, 0);
        }
        
        if (activeEditId === id) {
            setActiveEditId(null);
        }
        return acceptedEdit;
    }, [activeEditId, invalidateOverlappingEdits]);

    const rejectEdit = useCallback((id: string) => {
        setPendingEdits(prev => prev.filter(e => e.id !== id));
        if (activeEditId === id) {
            setActiveEditId(null);
        }
    }, [activeEditId]);

    const markEditAsStale = useCallback((id: string) => {
        setPendingEdits(prev => prev.map(e => 
            e.id === id ? { ...e, status: 'stale' as const } : e
        ));
        // If this was the active edit, clear it
        if (activeEditId === id) {
            setActiveEditId(null);
        }
    }, [activeEditId]);

    const clearAllEdits = useCallback(() => {
        setPendingEdits([]);
        setActiveEditId(null);
    }, []);

    const getEditById = useCallback((id: string) => {
        return pendingEdits.find(e => e.id === id);
    }, [pendingEdits]);

    return (
        <PendingEditsContext.Provider
            value={{
                advisorMode,
                setAdvisorMode,
                pendingEdits,
                addPendingEdit,
                addPendingEdits,
                removePendingEdit,
                acceptEdit,
                rejectEdit,
                clearAllEdits,
                invalidateOverlappingEdits,
                markEditAsStale,
                activeEditId,
                setActiveEditId,
                getEditById,
            }}
        >
            {children}
        </PendingEditsContext.Provider>
    );
}

export function usePendingEdits() {
    const context = useContext(PendingEditsContext);
    if (!context) {
        throw new Error('usePendingEdits must be used within a PendingEditsProvider');
    }
    return context;
}


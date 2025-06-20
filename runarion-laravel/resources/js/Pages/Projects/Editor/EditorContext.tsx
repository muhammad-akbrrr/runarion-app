import React, { createContext, useContext, useState, ReactNode } from 'react';

// Define the shape of our editor state
interface EditorState {
    // Basic parameters (outside of advanced)
    preset: string;
    authorProfile: string;
    aiModel: string;
    memory: string;
    storyGenre: string;
    storyTone: string;
    storyPOV: string;
    
    // Advanced parameters
    temperature: number;
    repetitionPenalty: number;
    outputLength: number;
    topP: number; // Nucleus sampling
    tailFree: number;
    topA: number;
    topK: number;
    minOutputToken: number;
}

// Define the shape of our context
interface EditorContextType {
    editorState: EditorState;
    updateEditorState: <K extends keyof EditorState>(key: K, value: EditorState[K]) => void;
}

// Create the context with a default value
const EditorContext = createContext<EditorContextType | undefined>(undefined);

// Create a provider component
export function EditorProvider({ children }: { children: ReactNode }) {
    const [editorState, setEditorState] = useState<EditorState>({
        preset: 'story-telling',
        authorProfile: 'tolkien',
        aiModel: 'chatgpt-4o',
        memory: '',
        storyGenre: '',
        storyTone: '',
        storyPOV: '',
        
        // Default values for advanced parameters
        temperature: 1.35,
        repetitionPenalty: 2.8,
        outputLength: 300,
        topP: 0.85,
        tailFree: 0.85,
        topA: 0.85,
        topK: 0.85,
        minOutputToken: 50,
    });

    const updateEditorState = <K extends keyof EditorState>(key: K, value: EditorState[K]) => {
        setEditorState(prevState => ({
            ...prevState,
            [key]: value
        }));
    };

    return (
        <EditorContext.Provider value={{ editorState, updateEditorState }}>
            {children}
        </EditorContext.Provider>
    );
}

// Create a hook for using the context
export function useEditor() {
    const context = useContext(EditorContext);
    if (context === undefined) {
        throw new Error('useEditor must be used within an EditorProvider');
    }
    return context;
}

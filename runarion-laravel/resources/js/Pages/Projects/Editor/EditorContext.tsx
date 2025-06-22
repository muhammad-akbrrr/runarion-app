import React, { createContext, useContext, useState, ReactNode, useEffect } from 'react';

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
    
    // Additional parameters for JSON structure
    phraseBias: Array<{[key: string]: number}>;
    bannedTokens: string[];
    stopSequences: string[];
    
    // Caller information
    userId: string;
    workspaceId: string;
    projectId: string;
    apiKeys: {
        openai: string;
        gemini: string;
        deepseek: string;
    };
}

// Define the shape of our context
interface EditorContextType {
    editorState: EditorState;
    updateEditorState: <K extends keyof EditorState>(key: K, value: EditorState[K]) => void;
}

// Create the context with a default value
const EditorContext = createContext<EditorContextType | undefined>(undefined);

// Default editor state
const defaultEditorState: EditorState = {
    preset: 'story-telling',
    authorProfile: '',
    aiModel: 'gemini-2.0-flash',
    memory: '',
    storyGenre: '',
    storyTone: '',
    storyPOV: '',
    
    // Default values for advanced parameters
    temperature: 1,
    repetitionPenalty: 0,
    outputLength: 300,
    topP: 0.85,
    tailFree: 0.85,
    topA: 0.85,
    topK: 0.85,
    minOutputToken: 1,
    
    // Additional parameters for JSON structure
    phraseBias: [],
    bannedTokens: [],
    stopSequences: [],
    
    // Caller information
    userId: "1",
    workspaceId: "",
    projectId: "",
    apiKeys: {
        openai: "",
        gemini: "",
        deepseek: ""
    }
};

// Create a provider component
export function EditorProvider({ 
    children, 
    workspaceId, 
    projectId,
    userId,
    initialEditorState
}: { 
    children: ReactNode, 
    workspaceId?: string, 
    projectId?: string,
    userId?: string,
    initialEditorState?: any
}) {
    // Initialize with default state
    const [editorState, setEditorState] = useState<EditorState>({
        ...defaultEditorState,
        userId: userId || defaultEditorState.userId,
        workspaceId: workspaceId || defaultEditorState.workspaceId,
        projectId: projectId || defaultEditorState.projectId,
    });

    // Update editor state with saved values if available
    useEffect(() => {
        if (initialEditorState) {
            console.log("Loading saved editor state:", initialEditorState);
            
            // Create a new state object by merging the default state with the saved state
            const mergedState = {
                ...editorState,
                ...initialEditorState,
                // Ensure these values are always set correctly
                userId: userId || editorState.userId,
                workspaceId: workspaceId || editorState.workspaceId,
                projectId: projectId || editorState.projectId,
            };
            
            setEditorState(mergedState);
        }
    }, [initialEditorState]);

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

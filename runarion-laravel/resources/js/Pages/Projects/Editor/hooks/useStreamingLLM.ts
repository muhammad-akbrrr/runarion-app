import { useState, useEffect, useRef, useCallback } from 'react';
import Echo from '@/echo';

interface StreamingLLMState {
    isStreaming: boolean;
    streamingText: string;
    error: string | null;
    sessionId: string | null;
}

interface UseStreamingLLMProps {
    workspaceId: string;
    projectId: string;
    chapterOrder: number;
    onStreamComplete: (fullText: string) => void;
    onStreamError: (error: string) => void;
}

export function useStreamingLLM({
    workspaceId,
    projectId,
    chapterOrder,
    onStreamComplete,
    onStreamError,
}: UseStreamingLLMProps) {
    const [state, setState] = useState<StreamingLLMState>({
        isStreaming: false,
        streamingText: '',
        error: null,
        sessionId: null,
    });

    const channelRef = useRef<any>(null);
    const streamingTextRef = useRef<string>('');
    const currentSessionRef = useRef<string | null>(null);

    // Setup WebSocket listeners
    useEffect(() => {
        const channelName = `project.${workspaceId}.${projectId}`;
        
        console.log('Setting up WebSocket channel:', channelName);
        
        // Join private channel
        channelRef.current = Echo.private(channelName);

        // Listen for stream started event
        channelRef.current.listen('.llm.stream.started', (data: any) => {
            console.log('Stream started:', data);
            
            if (data.chapter_order === chapterOrder) {
                currentSessionRef.current = data.session_id;
                streamingTextRef.current = '';
                
                setState(prev => ({
                    ...prev,
                    isStreaming: true,
                    streamingText: '',
                    error: null,
                    sessionId: data.session_id,
                }));
            }
        });

        // Listen for stream chunks
        channelRef.current.listen('.llm.stream.chunk', (data: any) => {
            console.log('Stream chunk received:', data);
            
            if (data.chapter_order === chapterOrder && 
                data.session_id === currentSessionRef.current) {
                
                streamingTextRef.current += data.chunk;
                
                setState(prev => ({
                    ...prev,
                    streamingText: streamingTextRef.current,
                }));
            }
        });

        // Listen for stream completion
        channelRef.current.listen('.llm.stream.completed', (data: any) => {
            console.log('Stream completed:', data);
            
            if (data.chapter_order === chapterOrder && 
                data.session_id === currentSessionRef.current) {
                
                setState(prev => ({
                    ...prev,
                    isStreaming: false,
                    sessionId: null,
                }));

                if (data.success) {
                    onStreamComplete(data.full_text);
                } else {
                    onStreamError(data.error || 'Stream failed');
                }

                // Reset refs
                streamingTextRef.current = '';
                currentSessionRef.current = null;
            }
        });

        // Listen for content updates (from other sources)
        channelRef.current.listen('.project.content.updated', (data: any) => {
            console.log('Content updated:', data);
            
            // Handle content updates from other sources if needed
            if (data.chapter_order === chapterOrder && 
                data.trigger !== 'llm_generation' &&
                !state.isStreaming) {
                // Handle manual content updates from other users
                // This could trigger a callback to update the editor
            }
        });

        return () => {
            if (channelRef.current) {
                console.log('Leaving WebSocket channel');
                channelRef.current.stopListening('.llm.stream.started');
                channelRef.current.stopListening('.llm.stream.chunk');
                channelRef.current.stopListening('.llm.stream.completed');
                channelRef.current.stopListening('.project.content.updated');
                Echo.leave(channelName);
                channelRef.current = null;
            }
        };
    }, [workspaceId, projectId, chapterOrder, onStreamComplete, onStreamError]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (channelRef.current) {
                const channelName = `project.${workspaceId}.${projectId}`;
                Echo.leave(channelName);
            }
        };
    }, []);

    const cancelStream = useCallback(() => {
        if (state.isStreaming && currentSessionRef.current) {
            // Reset state
            setState(prev => ({
                ...prev,
                isStreaming: false,
                streamingText: '',
                sessionId: null,
            }));
            
            streamingTextRef.current = '';
            currentSessionRef.current = null;
            
            console.log('Stream cancelled by user');
        }
    }, [state.isStreaming]);

    return {
        isStreaming: state.isStreaming,
        streamingText: state.streamingText,
        error: state.error,
        sessionId: state.sessionId,
        cancelStream,
    };
}

import { useState, useEffect, useRef, useCallback } from 'react';
import Echo from '@/echo';
import axios from 'axios';

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
        
        try {
            // Leave any existing channel first to prevent duplicate listeners
            if (channelRef.current) {
                channelRef.current.stopListening('.llm.stream.started');
                channelRef.current.stopListening('.llm.stream.chunk');
                channelRef.current.stopListening('.llm.stream.completed');
                channelRef.current.stopListening('.project.content.updated');
                Echo.leave(channelName);
            }
            
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
                        error: data.success ? null : (data.error || 'Stream failed'),
                    }));

                    if (data.success) {
                        onStreamComplete(data.full_text || streamingTextRef.current);
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
                    data.trigger === 'llm_generation' &&
                    !state.isStreaming) {
                    // This is a completed generation update
                    // We might want to refresh the content
                }
            });
            
            console.log('WebSocket listeners set up successfully');
        } catch (error) {
            console.error('Error setting up WebSocket listeners:', error);
            setState(prev => ({
                ...prev,
                error: 'Failed to connect to WebSocket server',
            }));
        }

        return () => {
            if (channelRef.current) {
                console.log('Leaving WebSocket channel');
                try {
                    channelRef.current.stopListening('.llm.stream.started');
                    channelRef.current.stopListening('.llm.stream.chunk');
                    channelRef.current.stopListening('.llm.stream.completed');
                    channelRef.current.stopListening('.project.content.updated');
                    Echo.leave(channelName);
                } catch (error) {
                    console.error('Error leaving WebSocket channel:', error);
                }
                channelRef.current = null;
            }
        };
    }, [workspaceId, projectId, chapterOrder]);

    const cancelStream = useCallback(() => {
        if (state.isStreaming && currentSessionRef.current) {
            // Make a request to cancel the stream
            axios.post(
                route("editor.project.cancel-generation", {
                    workspace_id: workspaceId,
                    project_id: projectId,
                }),
                {
                    session_id: currentSessionRef.current,
                    chapter_order: chapterOrder,
                }
            ).catch(error => {
                console.error('Error cancelling stream:', error);
            });
            
            // Reset state immediately for better UX
            setState(prev => ({
                ...prev,
                isStreaming: false,
                error: 'Generation cancelled by user',
            }));
            
            console.log('Stream cancelled by user');
        }
    }, [state.isStreaming, workspaceId, projectId, chapterOrder]);

    return {
        isStreaming: state.isStreaming,
        streamingText: state.streamingText,
        error: state.error,
        sessionId: state.sessionId,
        cancelStream,
    };
}

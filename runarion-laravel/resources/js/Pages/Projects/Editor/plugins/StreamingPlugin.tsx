import { useEffect, useRef } from 'react';
import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import { $getRoot, $createTextNode, $createParagraphNode } from 'lexical';
import { 
    $convertFromMarkdownString,
    $convertToMarkdownString,
    HEADING,
    UNORDERED_LIST,
    ORDERED_LIST,
    QUOTE,
    BOLD_STAR,
    BOLD_UNDERSCORE,
    ITALIC_STAR,
    ITALIC_UNDERSCORE,
    STRIKETHROUGH,
    INLINE_CODE,
} from '@lexical/markdown';

// Define supported transformers using the correct exports
const SUPPORTED_TRANSFORMERS = [
    HEADING,
    UNORDERED_LIST,
    ORDERED_LIST,
    QUOTE,
    BOLD_STAR,
    BOLD_UNDERSCORE,
    ITALIC_STAR,
    ITALIC_UNDERSCORE,
    STRIKETHROUGH,
    INLINE_CODE,
];

interface StreamingPluginProps {
    isStreaming: boolean;
    streamingText: string;
    baseContent: string;
    isRegenerating?: boolean;
    onStreamingUpdate?: (fullContent: string) => void;
}

/**
 * Plugin to handle real-time streaming text updates from LLM
 * Combines base content with streaming text and renders in real-time
 */
export function StreamingPlugin({ 
    isStreaming, 
    streamingText, 
    baseContent, 
    isRegenerating = false,
    onStreamingUpdate 
}: StreamingPluginProps) {
    const [editor] = useLexicalComposerContext();
    const lastStreamingTextRef = useRef<string>('');
    const isStreamingRef = useRef<boolean>(false);
    const hasInitializedRef = useRef<boolean>(false);
    const baseContentAtStartRef = useRef<string>('');

    useEffect(() => {
        // Track streaming state changes
        if (isStreaming !== isStreamingRef.current) {
            isStreamingRef.current = isStreaming;
            if (!isStreaming) {
                // Streaming ended, reset refs
                lastStreamingTextRef.current = '';
                hasInitializedRef.current = false;
                baseContentAtStartRef.current = '';
                console.log('StreamingPlugin: Streaming ended');
            } else {
                // Streaming started - capture baseContent at this moment
                baseContentAtStartRef.current = baseContent || '';
                hasInitializedRef.current = false;
                console.log('StreamingPlugin: Streaming started with baseContent:', {
                    baseContentLength: baseContent?.length || 0,
                    baseContentPreview: baseContent?.substring(0, 50) || ''
                });
            }
        }

        if (isStreaming && streamingText && streamingText !== lastStreamingTextRef.current) {
            lastStreamingTextRef.current = streamingText;
            
            // Use the baseContent captured at stream start to avoid race conditions
            const effectiveBaseContent = baseContentAtStartRef.current || baseContent || '';
            
            // Combine base content with streaming text
            let separator = '';
            if (effectiveBaseContent) {
                // Add space if base content doesn't end with newline or space
                if (!effectiveBaseContent.endsWith('\n') && !effectiveBaseContent.endsWith(' ') && 
                    !streamingText.startsWith('\n') && !streamingText.startsWith(' ')) {
                    separator = ' ';
                }
            }
            
            const fullContent = effectiveBaseContent + separator + streamingText;

            // Notify parent component of the streaming update
            if (onStreamingUpdate) {
                onStreamingUpdate(fullContent);
            }

            editor.update(() => {
                const root = $getRoot();
                
                // Clear and re-render the full content
                // This is necessary because Lexical doesn't have a good way to append markdown
                root.clear();

                // Render the full content (user text + AI text)
                try {
                    $convertFromMarkdownString(fullContent, SUPPORTED_TRANSFORMERS);
                } catch (error) {
                    console.error('StreamingPlugin: Error parsing streaming markdown:', error);
                    // Fallback: add as plain text in a paragraph
                    const paragraph = $createParagraphNode();
                    const textNode = $createTextNode(fullContent);
                    paragraph.append(textNode);
                    root.append(paragraph);
                }
            }, { discrete: true }); // Use discrete update to batch changes
        }
    }, [isStreaming, streamingText, baseContent, isRegenerating, editor, onStreamingUpdate]);

    return null;
}

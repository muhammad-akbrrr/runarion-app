import { useEffect, useRef } from 'react';
import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import { $getRoot, $createTextNode, $createParagraphNode } from 'lexical';
import { 
    $convertFromMarkdownString,
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

    useEffect(() => {
        // Track streaming state changes
        if (isStreaming !== isStreamingRef.current) {
            isStreamingRef.current = isStreaming;
            if (!isStreaming) {
                // Streaming ended, reset the ref
                lastStreamingTextRef.current = '';
                console.log('StreamingPlugin: Streaming ended');
            } else {
                console.log('StreamingPlugin: Streaming started');
            }
        }

        if (isStreaming && streamingText && streamingText !== lastStreamingTextRef.current) {
            lastStreamingTextRef.current = streamingText;
            
            console.log('StreamingPlugin: Updating with streaming text', {
                baseContentLength: baseContent?.length || 0,
                streamingTextLength: streamingText?.length || 0,
                streamingTextPreview: streamingText?.substring(0, 50) + '...',
                isRegenerating
            });

            // Combine base content with streaming text
            let separator = '';
            if (baseContent) {
                // Add space if base content doesn't end with newline or space
                if (!baseContent.endsWith('\n') && !baseContent.endsWith(' ') && 
                    !streamingText.startsWith('\n') && !streamingText.startsWith(' ')) {
                    separator = ' ';
                }
            }
            
            const fullContent = baseContent + separator + streamingText;

            // Notify parent component of the streaming update
            if (onStreamingUpdate) {
                onStreamingUpdate(fullContent);
            }

            editor.update(() => {
                const root = $getRoot();
                root.clear();

                try {
                    // Convert the combined markdown to Lexical nodes
                    $convertFromMarkdownString(fullContent, SUPPORTED_TRANSFORMERS);
                    console.log('StreamingPlugin: Successfully converted markdown to Lexical nodes', {
                        isRegenerating,
                        fullContentLength: fullContent.length
                    });
                } catch (error) {
                    console.error('StreamingPlugin: Error parsing streaming markdown:', error);
                    // Fallback: add as plain text in a paragraph
                    const paragraph = $createParagraphNode();
                    const textNode = $createTextNode(fullContent);
                    paragraph.append(textNode);
                    root.append(paragraph);
                }

                // Move cursor to end - use a more reliable method
                setTimeout(() => {
                    editor.update(() => {
                        const root = $getRoot();
                        if (root.getChildrenSize() > 0) {
                            const lastChild = root.getLastChild();
                            if (lastChild) {
                                lastChild.selectEnd();
                            }
                        }
                    });
                }, 10); // Slightly longer timeout to ensure DOM is updated
            });
        }
    }, [isStreaming, streamingText, baseContent, isRegenerating, editor, onStreamingUpdate]);

    return null;
}

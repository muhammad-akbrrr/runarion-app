import { useEffect } from 'react';
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
}

/**
 * Plugin to handle real-time streaming text updates from LLM
 * Combines base content with streaming text and renders in real-time
 */
export function StreamingPlugin({ isStreaming, streamingText, baseContent }: StreamingPluginProps) {
    const [editor] = useLexicalComposerContext();

    useEffect(() => {
        if (isStreaming && streamingText) {
            console.log('StreamingPlugin: Updating with streaming text', {
                baseContentLength: baseContent?.length || 0,
                streamingTextLength: streamingText?.length || 0,
                streamingTextPreview: streamingText?.substring(0, 50) + '...'
            });

            editor.update(() => {
                const root = $getRoot();
                root.clear();

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

                try {
                    // Convert the combined markdown to Lexical nodes
                    $convertFromMarkdownString(fullContent, SUPPORTED_TRANSFORMERS);
                    console.log('StreamingPlugin: Successfully converted markdown to Lexical nodes');
                } catch (error) {
                    console.error('StreamingPlugin: Error parsing streaming markdown:', error);
                    // Fallback: add as plain text in a paragraph
                    const paragraph = $createParagraphNode();
                    const textNode = $createTextNode(fullContent);
                    paragraph.append(textNode);
                    root.append(paragraph);
                }

                // Move cursor to end
                setTimeout(() => {
                    editor.update(() => {
                        if (root.getChildrenSize() > 0) {
                            const lastChild = root.getLastChild();
                            if (lastChild) {
                                lastChild.selectEnd();
                            }
                        }
                    });
                }, 0);
            });
        }
    }, [isStreaming, streamingText, baseContent, editor]);

    return null;
}

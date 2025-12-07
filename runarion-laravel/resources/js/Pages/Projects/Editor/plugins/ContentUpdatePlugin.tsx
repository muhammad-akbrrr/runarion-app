import { useEffect, useRef } from 'react';
import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import {
    $getRoot,
    $createParagraphNode,
    $createTextNode,
} from 'lexical';
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
export const SUPPORTED_TRANSFORMERS = [
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

interface ContentUpdatePluginProps {
    content: string;
    isStreaming: boolean;
}

/**
 * Custom plugin to update editor content when chapter changes
 * Handles markdown conversion and cursor positioning
 */
export function ContentUpdatePlugin({ content, isStreaming }: ContentUpdatePluginProps) {
    const [editor] = useLexicalComposerContext();
    const wasStreamingRef = useRef(false);
    const skipNextUpdateRef = useRef(false);
    const lastContentLengthRef = useRef(0);

    useEffect(() => {
        // Track when streaming ends - skip the next update to prevent flicker
        if (wasStreamingRef.current && !isStreaming) {
            console.log('ContentUpdatePlugin: Streaming just ended, will skip next update');
            skipNextUpdateRef.current = true;
        }
        wasStreamingRef.current = isStreaming;
        
        // Don't update content during streaming to avoid conflicts
        if (isStreaming) {
            console.log('ContentUpdatePlugin: Skipping update during streaming');
            return;
        }
        
        // Skip the update right after streaming ends (StreamingPlugin already rendered the content)
        if (skipNextUpdateRef.current) {
            console.log('ContentUpdatePlugin: Skipping post-streaming update to prevent flicker');
            skipNextUpdateRef.current = false;
            return;
        }

        console.log('ContentUpdatePlugin: Checking if content update needed', {
            contentLength: content?.length || 0,
            contentPreview: content?.substring(0, 50) + '...'
        });

        // Save scroll position before update
        const editorElement = editor.getRootElement();
        const scrollContainer = editorElement?.closest('.overflow-y-auto') || editorElement?.parentElement;
        const savedScrollTop = scrollContainer?.scrollTop || 0;

        editor.update(() => {
            const root = $getRoot();
            
            // Get current markdown content to compare
            const currentMarkdown = $convertToMarkdownString(SUPPORTED_TRANSFORMERS);
            
            if (currentMarkdown === content) {
                console.log('ContentUpdatePlugin: Content unchanged, skipping update');
                return; // No need to update
            }
            
            // Determine if this is a major change (chapter switch) or minor edit
            const previousLength = lastContentLengthRef.current;
            const newLength = content?.length || 0;
            const lengthDiff = Math.abs(newLength - previousLength);
            const isMajorChange = previousLength === 0 || lengthDiff > previousLength * 0.5;
            
            console.log('ContentUpdatePlugin: Updating editor content', {
                currentLength: currentMarkdown.length,
                newLength: newLength,
                isMajorChange
            });
            
            lastContentLengthRef.current = newLength;
            
            // Clear the editor
            root.clear();

            if (content && content.trim()) {
                try {
                    // Convert markdown to Lexical nodes
                    $convertFromMarkdownString(content, SUPPORTED_TRANSFORMERS);
                    console.log('ContentUpdatePlugin: Successfully converted markdown to Lexical nodes');
                } catch (error) {
                    console.error('ContentUpdatePlugin: Error parsing markdown content:', error);
                    // Fallback to plain text
                    const paragraph = $createParagraphNode();
                    const textNode = $createTextNode(content);
                    paragraph.append(textNode);
                    root.append(paragraph);
                }
            } else {
                // Add empty paragraph if no content
                const paragraph = $createParagraphNode();
                root.append(paragraph);
            }

            // Only set cursor to end on major changes (chapter switches)
            // For minor edits, preserve scroll position
            if (isMajorChange) {
                setTimeout(() => {
                    editor.update(() => {
                        if (root.getChildrenSize() > 0) {
                            const lastChild = root.getLastChild();
                            if (lastChild) {
                                lastChild.selectEnd();
                            }
                        }
                    });
                }, 10);
            } else {
                // Restore scroll position for minor edits
                setTimeout(() => {
                    if (scrollContainer) {
                        scrollContainer.scrollTop = savedScrollTop;
                    }
                }, 20);
            }
        });
    }, [content, editor, isStreaming]);

    return null;
}

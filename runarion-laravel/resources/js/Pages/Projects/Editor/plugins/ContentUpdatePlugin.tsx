import { useEffect } from 'react';
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

    useEffect(() => {
        // Don't update content during streaming to avoid conflicts
        if (isStreaming) {
            console.log('ContentUpdatePlugin: Skipping update during streaming');
            return;
        }

        console.log('ContentUpdatePlugin: Checking if content update needed', {
            contentLength: content?.length || 0,
            contentPreview: content?.substring(0, 50) + '...'
        });

        editor.update(() => {
            const root = $getRoot();
            
            // Get current markdown content to compare
            const currentMarkdown = $convertToMarkdownString(SUPPORTED_TRANSFORMERS);
            
            if (currentMarkdown === content) {
                console.log('ContentUpdatePlugin: Content unchanged, skipping update');
                return; // No need to update
            }
            
            console.log('ContentUpdatePlugin: Updating editor content', {
                currentLength: currentMarkdown.length,
                newLength: content?.length || 0
            });
            
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

            // Set cursor to end after content is loaded - use setTimeout to avoid race conditions
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
        });
    }, [content, editor, isStreaming]);

    return null;
}

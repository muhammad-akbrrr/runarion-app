import { useEffect } from 'react';
import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import { LexicalEditor } from 'lexical';

interface EditorRefPluginProps {
    editorRef: React.MutableRefObject<LexicalEditor | null>;
}

/**
 * Plugin to store editor reference for external access
 * Used for context menu operations and other editor manipulations
 */
export function EditorRefPlugin({ editorRef }: EditorRefPluginProps) {
    const [editor] = useLexicalComposerContext();
    
    useEffect(() => {
        editorRef.current = editor;
    }, [editor, editorRef]);
    
    return null;
}

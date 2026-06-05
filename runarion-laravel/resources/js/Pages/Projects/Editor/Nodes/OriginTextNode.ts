import {
    TextNode,
    SerializedTextNode,
    NodeKey,
    LexicalNode,
    $applyNodeReplacement,
    LexicalEditor,
    DOMExportOutput,
    EditorConfig,
} from "lexical";

export type OriginType = "user" | "ai";

export interface SerializedOriginTextNode extends SerializedTextNode {
    origin: OriginType;
    type: "origin-text";
}

/**
 * Custom TextNode that tracks whether content was authored by the user or AI.
 * This metadata is persisted in Lexical JSON and survives undo/redo, page refresh, etc.
 */
export class OriginTextNode extends TextNode {
    __origin: OriginType;

    constructor(text: string, origin: OriginType = "user", key?: NodeKey) {
        super(text, key);
        this.__origin = origin;
    }

    static getType(): string {
        return "origin-text";
    }

    static clone(node: OriginTextNode): OriginTextNode {
        return new OriginTextNode(node.__text, node.__origin, node.__key);
    }

    // Serialization for persistence in Lexical JSON
    exportJSON(): SerializedOriginTextNode {
        return {
            ...super.exportJSON(),
            origin: this.__origin,
            type: "origin-text",
        };
    }

    // Deserialization from stored Lexical JSON
    static importJSON(
        serializedNode: SerializedOriginTextNode
    ): OriginTextNode {
        const node = $createOriginTextNode(
            serializedNode.text,
            serializedNode.origin
        );
        node.setFormat(serializedNode.format);
        node.setDetail(serializedNode.detail);
        node.setMode(serializedNode.mode);
        node.setStyle(serializedNode.style);
        return node;
    }

    // DOM export - used when copying content
    exportDOM(editor: LexicalEditor): DOMExportOutput {
        const element = super.exportDOM(editor).element as HTMLElement;
        if (element) {
            element.setAttribute("data-origin", this.__origin);
        }
        return { element };
    }

    // Note: importDOM is not overridden - pasted content will go through TextNode
    // and get converted by OriginTrackingPlugin to OriginTextNode with 'user' origin

    getOrigin(): OriginType {
        // Always get the latest version of the node
        return this.getLatest().__origin;
    }

    setOrigin(origin: OriginType): this {
        const self = this.getWritable();
        self.__origin = origin;
        return self;
    }

    // Override splitText to preserve origin on all resulting nodes
    splitText(...splitOffsets: number[]): OriginTextNode[] {
        const nodes = super.splitText(...splitOffsets) as OriginTextNode[];
        const origin = this.__origin;

        // Ensure all split nodes inherit the origin
        nodes.forEach((node) => {
            if (node !== this && node instanceof OriginTextNode) {
                const writable = node.getWritable() as OriginTextNode;
                writable.__origin = origin;
            }
        });

        return nodes;
    }

    // Create a copy with the same origin
    createDOM(config: EditorConfig): HTMLElement {
        const element = super.createDOM(config);
        element.setAttribute("data-origin", this.__origin);
        return element;
    }

    updateDOM(
        prevNode: OriginTextNode,
        dom: HTMLElement,
        config: EditorConfig
    ): boolean {
        // Cast to 'unknown' then 'this' to satisfy the parent's polymorphic 'this' requirement
        const isUpdated = super.updateDOM(
            prevNode as unknown as this,
            dom,
            config
        );

        // Update data-origin attribute if origin changed
        if (prevNode.__origin !== this.__origin) {
            dom.setAttribute("data-origin", this.__origin);
        }

        return isUpdated;
    }
}

// Factory function to create OriginTextNode with proper Lexical registration
export function $createOriginTextNode(
    text: string,
    origin: OriginType = "user"
): OriginTextNode {
    return $applyNodeReplacement(new OriginTextNode(text, origin));
}

// Type guard to check if a node is an OriginTextNode
export function $isOriginTextNode(
    node: LexicalNode | null | undefined
): node is OriginTextNode {
    return node instanceof OriginTextNode;
}

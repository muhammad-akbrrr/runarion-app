/**
 * Utilities for extracting plain text from Lexical JSON content
 */

/**
 * Check if content is valid Lexical JSON format
 */
export function isLexicalJSON(content: string | null | undefined): boolean {
    if (!content?.trim().startsWith("{")) return false;
    try {
        const parsed = JSON.parse(content);
        return parsed.root?.type === "root";
    } catch {
        return false;
    }
}

/**
 * Extract plain text from a Lexical JSON node recursively
 */
export function extractTextFromNode(node: any): string {
    if (!node) return "";

    // Text node - return its text content
    if (node.type === "text" || node.type === "origin-text") {
        return node.text || "";
    }

    // For container nodes, process children
    if (node.children && Array.isArray(node.children)) {
        return node.children
            .map((child: any, index: number) => {
                const text = extractTextFromNode(child);
                // Add paragraph breaks between paragraphs
                if (
                    child.type === "paragraph" &&
                    index < node.children.length - 1
                ) {
                    return text + "\n\n";
                }
                return text;
            })
            .join("");
    }

    return "";
}

/**
 * Extract plain text from Lexical JSON content string
 * Returns the original string if not valid Lexical JSON
 */
export function extractTextFromLexical(content: string | null | undefined): string {
    if (!content) return "";

    if (!isLexicalJSON(content)) {
        return content;
    }

    try {
        const parsed = JSON.parse(content);
        return extractTextFromNode(parsed.root);
    } catch {
        return content;
    }
}

import {
    $getRoot,
    LexicalEditor,
    LexicalNode,
    ElementNode,
    TextNode,
} from "lexical";
import {
    $isOriginTextNode,
    $createOriginTextNode,
    OriginTextNode,
} from "../Nodes/OriginTextNode";

/**
 * Calculate AI coverage for a given text range
 */
function calculateAiCoverage(
    aiRanges: number[][],
    nodeStart: number,
    nodeEnd: number,
): number {
    let aiCoverage = 0;
    for (const [start, end] of aiRanges) {
        const overlapStart = Math.max(nodeStart, start);
        const overlapEnd = Math.min(nodeEnd, end);
        if (overlapEnd > overlapStart) {
            aiCoverage += overlapEnd - overlapStart;
        }
    }
    return aiCoverage;
}

/**
 * Migrate legacy aiRanges (position-based) to OriginTextNode metadata.
 *
 * Called once when a chapter loads if it has legacy ai_ranges data.
 * After migration, the aiRanges should be cleared and subsequent saves
 * will persist the origin metadata in the Lexical JSON instead.
 *
 * This function handles both plain TextNodes and OriginTextNodes:
 * - OriginTextNodes: Just update the origin property
 * - TextNodes: Convert to OriginTextNode with the correct origin
 *
 * @param editor - The Lexical editor instance
 * @param aiRanges - Array of [start, end] positions marking AI-generated text
 * @returns boolean - true if migration was performed, false if skipped
 */
export function migrateAiRangesToMetadata(
    editor: LexicalEditor,
    aiRanges: number[][],
): boolean {
    if (!aiRanges || aiRanges.length === 0) {
        console.log("Migration: No aiRanges to migrate");
        return false;
    }

    console.log(
        `Migration: Migrating ${aiRanges.length} aiRanges to OriginTextNode metadata`,
    );

    editor.update(
        () => {
            const root = $getRoot();
            let plainTextOffset = 0;
            let migratedNodes = 0;
            let convertedNodes = 0;

            const processNode = (node: LexicalNode) => {
                // Handle both TextNode and OriginTextNode
                if (node instanceof TextNode) {
                    const text = node.getTextContent();
                    const nodeStart = plainTextOffset;
                    const nodeEnd = plainTextOffset + text.length;

                    // Calculate how much of this node is covered by AI ranges
                    const aiCoverage = calculateAiCoverage(
                        aiRanges,
                        nodeStart,
                        nodeEnd,
                    );
                    const textLength = text.length;

                    // If more than 50% is AI, mark as AI; otherwise user
                    const isAi =
                        textLength > 0 && aiCoverage / textLength > 0.5;
                    const newOrigin = isAi ? "ai" : "user";

                    // If it's already an OriginTextNode, just update origin
                    if ($isOriginTextNode(node)) {
                        const currentOrigin = (
                            node as OriginTextNode
                        ).getOrigin();
                        if (currentOrigin !== newOrigin) {
                            (node as OriginTextNode).setOrigin(newOrigin);
                            migratedNodes++;
                        }
                    } else {
                        // Convert plain TextNode to OriginTextNode with correct origin
                        const originNode = $createOriginTextNode(
                            text,
                            newOrigin,
                        );
                        originNode.setFormat(node.getFormat());
                        originNode.setDetail(node.getDetail());
                        originNode.setMode(node.getMode());
                        originNode.setStyle(node.getStyle());
                        node.replace(originNode);
                        convertedNodes++;
                    }

                    plainTextOffset = nodeEnd;
                } else if (
                    "getChildren" in node &&
                    typeof (node as ElementNode).getChildren === "function"
                ) {
                    const children = (node as ElementNode).getChildren();
                    children.forEach(processNode);
                }
            };

            root.getChildren().forEach(processNode);
            console.log(
                `Migration: Updated ${migratedNodes} nodes, converted ${convertedNodes} TextNodes to OriginTextNodes`,
            );
        },
        { discrete: true, tag: "migration" },
    );

    return true;
}

/**
 * Check if content needs migration (has legacy aiRanges but no OriginTextNode metadata).
 *
 * This is a simple heuristic - if we have aiRanges data and the content exists,
 * we assume migration is needed.
 *
 * @param aiRanges - Legacy AI ranges array
 * @returns boolean - true if migration should be performed
 */
export function needsMigration(
    aiRanges: number[][] | undefined | null,
): boolean {
    return Array.isArray(aiRanges) && aiRanges.length > 0;
}

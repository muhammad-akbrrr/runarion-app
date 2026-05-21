// Interaction type with sentiment modifiers (CK3-style)
export interface Interaction {
    vertex_id: string;
    source_character: string;
    target_character: string;
    interaction_type: string;
    emotional_tone: string;
    context?: string;
    text_evidence?: string;
    chapter_number?: number;
    sentiment_modifier?: number;
    sentiment_reasoning?: string; // AI's explanation for the score
    ai_scored?: boolean; // Whether AI directly scored this
}

// Sentiment breakdown item for CK3-style display
export interface SentimentBreakdownItem {
    label: string;
    value: number;
    description?: string;
    chapter?: number;
    reasoning?: string; // AI reasoning for the score
}

export interface Entity {
    vertex_id: string; // String to avoid JS precision loss with large Apache AGE IDs
    name: string;
    type: string;
    properties: Record<string, any>;
}

// V2 Chapter Analysis structure
export interface KeyEvidence {
    quote: string;
    context?: string;
}

export interface EmotionalTone {
    id: number;
    name: string;
    is_base: boolean; // Base tones can't be deleted
    created_at?: string;
}

export interface ChapterAnalysis {
    chapter_number: number;
    chapter_name: string;
    sentiment_score: number;
    relationship_type: string;
    emotional_tone: string;
    summary: string;
    key_moment?: string; // Legacy field
    key_evidence?: KeyEvidence[]; // New detailed evidence
}

export interface Relationship {
    edge_id: string; // String to avoid JS precision loss with large Apache AGE IDs
    source: string;
    target: string;
    relationship_type: string;
    properties?: Record<string, any> & {
        // V2 fields
        sentiment_score?: number;
        emotional_tone?: string;
        context?: string;
        relationship_progression?: string;
        chapter_analyses?: string; // JSON string of ChapterAnalysis[]
        analysis_version?: string; // 'v2' for chapter-based
    };
}

export interface RelationshipsTabProps {
    entity: Entity;
    entityRelationships: Relationship[];
    allRelationships: Relationship[];
    allEntities?: Entity[];
    workspaceId: string;
    projectId: string;
    onRelationshipCreated: () => void;
    onRelationshipDeleted: () => void;
    onRelationshipUpdated: () => void;
    onSavingChange?: (isSaving: boolean) => void;
}

export type ViewMode = "all" | "one-to-one";
export type SortBy = "name" | "type" | "recent";
export type FilterBy = "all" | string;
export type InteractionsViewMode = "all" | "by-chapter";

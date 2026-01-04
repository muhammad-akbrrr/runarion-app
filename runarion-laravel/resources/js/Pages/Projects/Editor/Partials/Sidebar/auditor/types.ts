// Types for AuditorToolsTab and its sub-components

export interface AuditorToolsTabProps {
    workspaceId: string;
    projectId: string;
    selectedModel: string;
    onApplyStoryFix?: (oldText: string, newText: string) => boolean;
}

export interface ChapterScanInfo {
    chapter_order: number;
    chapter_name: string;
    current_content_hash: string;
    stored_content_hash: string;
    has_changes: boolean;
    content_length: number;

    // Detailed extraction status
    extraction: {
        done: boolean;
        last_at: string | null;
        categories_extracted: string[];
        entity_count: number;
        warning: string | null;
    };

    // Record keeper summarization status
    record_keeper: {
        done: boolean;
        last_at: string | null;
        warning: string | null;
    };

    // Data integrity warning
    has_warning: boolean;

    // Category-specific summarization status
    category_summaries: {
        done: boolean;
        last_at: string | null;
        categories_summarized: string[];
    };

    // What needs to be done
    needs_extraction: boolean;
    needs_summarization: boolean;

    // Legacy fields
    last_extraction_at: string | null;
    last_summarization_at: string | null;
    entities_extracted: string[];
    not_scanned: boolean;
}

export interface ScanStatus {
    chapters: Record<number, ChapterScanInfo>;
    total_chapters: number;
    extraction_pending: number;
    summarization_pending: number;
    data_warnings: number;
    // Legacy
    chapters_with_changes: number;
    chapters_not_scanned: number;
}

export interface ConsistencyIssue {
    entity_name?: string;
    entity_type?: string;
    issue_type: string;
    title?: string;
    field?: string;
    current_db_value?: string;
    story_evidence?: string;
    description?: string;
    location?: string;
    evidence?: string;
    severity: string;
    suggestion: string;
}

export interface DuplicateGroup {
    entities: Array<{ vertex_id: string; name: string }>;
    entity_type: string;
    confidence: number;
    reason: string;
    suggested_canonical: string;
}

export interface PropertyChange {
    field: string;
    old_value: any;
    new_value: any;
    reason: string;
    chapter_reference?: number;
}

export interface RefreshResults {
    entities_processed: number;
    entities_updated: number;
    entities_unchanged: number;
    changes_by_entity: Record<string, PropertyChange[]>;
    errors: string[];
}

// Shared props passed from main orchestrator to section components
export interface SharedSectionProps {
    workspaceId: string;
    projectId: string;
    selectedModel: string;
    availableCategories: string[];
    availableEntities: Record<string, Array<{ vertex_id: string; name: string }>>;
    loadingCategories: boolean;
    loadingEntities: boolean;
    loadEntitiesForCategory: (category: string) => Promise<void>;
}

// Preview data for record fix dialog
export interface RecordFixPreviewData {
    issue: ConsistencyIssue;
    index: number;
    field: string;
    oldValue: string;
    newValue: string;
    explanation: string;
}

// Preview data for story text fix dialog
export interface StoryTextPreviewData {
    issue: ConsistencyIssue;
    index: number;
    oldText: string;
    newText: string;
    explanation: string;
    chapterName: string;
    chapterOrder: number;
}

export type ProjectCategory =
    | "horror"
    | "sci-fi"
    | "fantasy"
    | "romance"
    | "thriller"
    | "mystery"
    | "adventure"
    | "comedy"
    | "dystopian"
    | "crime"
    | "fiction"
    | "biography"
    | "historical";

export type ProjectRole = "editor" | "manager" | "admin";

export interface ProjectAccess {
    user: {
        id: string;
        name: string;
        email: string;
        avatar_url: string | null;
    };
    role: ProjectRole;
}

export interface GenerationVersion {
    index: number;
    content: string;
    timestamp: number;
}

export interface GenerationStep {
    id: string;
    parentId: string | null;
    content: string;
    timestamp: number;
    settings: any;
    isUserGenerated: boolean;
    versions: GenerationVersion[];
}

export interface GenerationHistory {
    steps: GenerationStep[];
    currentStepId: string | null;
    lastSelectedVersions: Record<string, number>;
}

export interface NavigationInfo {
    currentVersionIndex: number;
    totalVersions: number;
    canUndo: boolean;
    canRedo: boolean;
    canRegenerate: boolean;
    versionDisplayText: string;
    currentNodeId?: string; // ID of the current node in the version tree
}

export interface ProjectChapter {
    order: number;
    chapter_name: string;
    content: string;
    summary: string;
    plot_points: Array<string>;
    generation_history?: GenerationHistory;
    navigation_info?: NavigationInfo;
    ai_ranges?: number[][]; // Legacy: position-based AI text markers (migrated to OriginTextNode metadata)
}

export interface ProjectContent {
    id: string;
    project_id: string;
    content: ProjectChapter[];
    metadata: Record<string, any> | null;
    generation_history: Record<number, GenerationHistory> | null;
    current_step_id: string | null;
    last_selected_versions: Record<string, number> | null;
    last_edited_at: string | null;
    last_edited_by: number | null;
    created_at: string;
    updated_at: string;
    deleted_at: string | null;
    last_editor?: {
        id: number;
        name: string;
    } | null;
}

export interface Project {
    id: string;
    workspace_id: string;
    folder_id: string | null;
    original_author: number | null;
    name: string;
    slug: string;
    settings: Record<string, any> | null;
    category: ProjectCategory | null;
    saved_in: string;
    description: string | null;
    access: ProjectAccess[] | null;
    current_user_access: ProjectAccess | null;
    is_active: boolean;
    backup_frequency: "daily" | "weekly" | "manual";
    completed_onboarding: boolean;
    last_backup_at: string | null;
    next_backup_at: string | null;
    created_at: string;
    updated_at: string;
    deleted_at: string | null;
    author?: {
        id: number;
        name: string;
    } | null;
    content?: ProjectContent | null;
}

export interface ProjectSettings {
    // Main Settings
    currentPreset: string;
    authorProfile: string;
    aiModel: string;
    selectionToolbarMode: 'formatting' | 'ai-rewrite';  // DEPRECATED - unified toolbar now shows both formatting and AI features
    memory: string;
    storyGenre: string;
    storyTone: string;
    storyPov: string;
    
    // Advanced Settings
    temperature: number;
    repetitionPenalty: number;
    outputLength: number;
    minOutputToken: number;
    thinkingBudget: number;  // Token budget for AI reasoning (thinking models only)
    
    // Sampling
    topP: number;
    tailFree: number;
    topA: number;
    topK: number;
    
    // Complex Settings
    phraseBias: Array<{ [key: string]: number }>;
    bannedPhrases: string[];
    stopSequences: string[];
}

// Type for story fix confirmation request (when confidence is 50-90%)
export interface StoryFixConfirmationRequest {
    needsConfirmation: true;
    matchedText: string;
    confidence: number;
    start: number;
    end: number;
    newText: string;
}

// Return type for story fix callbacks
export type StoryFixResult = boolean | StoryFixConfirmationRequest;

export interface SidebarSettingsProps {
    settings: Partial<ProjectSettings>;
    onSettingChange: (key: keyof ProjectSettings, value: any) => void;
    workspaceId?: string;
    projectId?: string;
    authorStyles?: Array<{ id: string; name: string; status?: string }>;  // Available author styles from workspace
    onApplyStoryFix?: (oldText: string, newText: string) => boolean;  // Callback to apply story fixes, returns success/failure
}

// Models that support thinking (internal reasoning before responding)
export const THINKING_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-flash", 
    "gemini-3-pro-preview"
];

// Default thinking budgets per model
export const DEFAULT_THINKING_BUDGETS: Record<string, number> = {
    "gemini-2.5-pro": 4096,
    "gemini-2.5-flash": 2048,
    "gemini-3-pro-preview": 4096,
};

export const DEFAULT_SETTINGS: ProjectSettings = {
    currentPreset: "story-telling",
    authorProfile: "",  // Empty - user must select from available workspace author styles
    aiModel: "gemini-2.0-flash",
    selectionToolbarMode: "formatting",  // DEPRECATED - no longer used, kept for backward compatibility
    memory: "",
    storyGenre: "",
    storyTone: "",
    storyPov: "",
    temperature: 1,
    repetitionPenalty: 0,
    outputLength: 300,
    minOutputToken: 50,
    thinkingBudget: 4096,  // Default thinking budget (only used for thinking models)
    topP: 0.85,
    tailFree: 0.85,
    topA: 0.85,
    topK: 0.85,
    phraseBias: [],
    bannedPhrases: [],
    stopSequences: [],
};

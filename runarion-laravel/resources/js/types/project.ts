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

export interface ProjectChapter {
    order: number;
    chapter_name: string;
    content: string;
    summary: string;
    plot_points: Array<string>;
    generation_history?: GenerationHistory;
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
    memory: string;
    storyGenre: string;
    storyTone: string;
    storyPov: string;
    
    // Advanced Settings
    temperature: number;
    repetitionPenalty: number;
    outputLength: number;
    minOutputToken: number;
    
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

export interface SidebarSettingsProps {
    settings: Partial<ProjectSettings>;
    onSettingChange: (key: keyof ProjectSettings, value: any) => void;
    workspaceId?: string;
    projectId?: string;
}

export const DEFAULT_SETTINGS: ProjectSettings = {
    currentPreset: "story-telling",
    authorProfile: "tolkien",
    aiModel: "gemini-2.0-flash",
    memory: "",
    storyGenre: "",
    storyTone: "",
    storyPov: "",
    temperature: 1,
    repetitionPenalty: 0,
    outputLength: 300,
    minOutputToken: 50,
    topP: 0.85,
    tailFree: 0.85,
    topA: 0.85,
    topK: 0.85,
    phraseBias: [],
    bannedPhrases: [],
    stopSequences: [],
};

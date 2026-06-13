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

export interface PipelineLock {
    isLocked: boolean;
    runId?: string;
    operationId?: string;
    operationType?: string;
    draftId?: string | null;
    authorStyleId?: string | null;
    status: string;
    phase: string;
    message?: string | null;
    errorMessage?: string | null;
    startedAt?: string | null;
    completedAt?: string | null;
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
    pipelineLock?: PipelineLock | null;
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
    selectionToolbarMode: "formatting" | "ai-rewrite"; // DEPRECATED - unified toolbar now shows both formatting and AI features
    memory: string;
    storyGenre: string;
    storyTone: string;
    storyPov: string;

    // Advanced Settings
    temperature: number;
    repetitionPenalty: number;
    outputLength: number;
    minOutputToken: number;
    thinkingBudget: number; // Token budget for AI reasoning (thinking models only)

    // Sampling
    topP: number;
    tailFree: number;
    topA: number;
    topK: number;

    // Complex Settings
    phraseBias: Array<{ [key: string]: number }>;
    bannedPhrases: string[];
    stopSequences: string[];

    // Auditor Tab Settings
    auditorAnalysisModel: string;

    // Advisor Tab Settings (default values for new chats)
    advisorModel: string;
    advisorSystemInstructions: string;
    advisorThinkingBudget: number;
    advisorOutputLength: number;
    advisorTemperature: number;
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
    authorStyles?: Array<{ id: string; name: string; status?: string; schemaVersion?: number }>;
    projectPipelineLock?: PipelineLock | null;
    onApplyStoryFix?: (oldText: string, newText: string) => Promise<boolean>; // Callback to apply story fixes, returns success/failure
    onSavingChange?: (isSaving: boolean) => void; // Callback to signal saving state changes (for save indicator)
}

// Parameter range configuration for model-specific slider settings
export interface ParameterRange {
    min: number;
    max: number;
    step: number;
    default: number;
}

// Per-model configuration defining supported parameters and their ranges
export interface ModelConfig {
    id: string;
    label: string;
    provider: string;
    supportsThinking: boolean;
    params: {
        temperature?: ParameterRange;
        topP?: ParameterRange;
        topK?: ParameterRange;
        outputLength?: ParameterRange;
        thinkingBudget?: ParameterRange;
        repetitionPenalty?: ParameterRange;
        tailFree?: ParameterRange;
        topA?: ParameterRange;
        phraseBias?: ParameterRange;
        minOutputToken?: ParameterRange;
    };
}

export const MODEL_CONFIGS: Record<string, ModelConfig> = {
    "gemini-2.5-flash": {
        id: "gemini-2.5-flash",
        label: "Gemini 2.5 Flash (Fast + Thinking)",
        provider: "gemini",
        supportsThinking: true,
        params: {
            temperature: { min: 0, max: 2, step: 0.01, default: 1 },
            topP: { min: 0, max: 1, step: 0.01, default: 0.95 },
            outputLength: { min: 50, max: 8192, step: 10, default: 1000 },
            thinkingBudget: { min: 0, max: 24576, step: 256, default: 2048 },
            // repetitionPenalty: not supported — "Penalty is not enabled for models/gemini-2.5-flash"
        },
    },
    "gemini-2.5-pro": {
        id: "gemini-2.5-pro",
        label: "Gemini 2.5 Pro (Quality + Thinking)",
        provider: "gemini",
        supportsThinking: true,
        params: {
            temperature: { min: 0, max: 2, step: 0.01, default: 1 },
            topP: { min: 0, max: 1, step: 0.01, default: 0.95 },
            outputLength: { min: 50, max: 8192, step: 10, default: 1000 },
            thinkingBudget: { min: 0, max: 24576, step: 256, default: 4096 },
            // repetitionPenalty: not supported — "Penalty is not enabled for models/gemini-2.5-*"
        },
    },
    "gemini-3-pro-preview": {
        id: "gemini-3-pro-preview",
        label: "Gemini 3.0 Pro (Paid API Key)",
        provider: "gemini",
        supportsThinking: true,
        params: {
            temperature: { min: 0, max: 2, step: 0.01, default: 1 },
            topP: { min: 0, max: 1, step: 0.01, default: 0.95 },
            topK: { min: 1, max: 100, step: 1, default: 64 },
            outputLength: { min: 50, max: 8192, step: 10, default: 1000 },
            thinkingBudget: { min: 0, max: 24576, step: 256, default: 4096 },
            repetitionPenalty: { min: -2, max: 2, step: 0.1, default: 0 },
        },
    },
};

// Models that support thinking — derived from MODEL_CONFIGS
export const THINKING_MODELS = Object.values(MODEL_CONFIGS)
    .filter((m) => m.supportsThinking)
    .map((m) => m.id);

// Default thinking budgets per model — derived from MODEL_CONFIGS
export const DEFAULT_THINKING_BUDGETS: Record<string, number> =
    Object.fromEntries(
        Object.values(MODEL_CONFIGS)
            .filter((m) => m.params.thinkingBudget)
            .map((m) => [m.id, m.params.thinkingBudget!.default]),
    );

export const DEFAULT_SETTINGS: ProjectSettings = {
    currentPreset: "story-telling",
    authorProfile: "", // Empty - user must select from available workspace author styles
    aiModel: "gemini-2.5-flash",
    selectionToolbarMode: "formatting", // DEPRECATED - no longer used, kept for backward compatibility
    memory: "",
    storyGenre: "",
    storyTone: "",
    storyPov: "",
    temperature: 1,
    repetitionPenalty: 0,
    outputLength: 1000,
    minOutputToken: 50,
    thinkingBudget: 4096, // Default thinking budget (only used for thinking models)
    topP: 0.85,
    tailFree: 0.85,
    topA: 0.85,
    topK: 64,
    phraseBias: [],
    bannedPhrases: [],
    stopSequences: [],
    // Auditor Tab Settings
    auditorAnalysisModel: "gemini-2.5-flash",
    // Advisor Tab Settings
    advisorModel: "gemini-2.5-flash",
    advisorSystemInstructions: "",
    advisorThinkingBudget: 4096,
    advisorOutputLength: 4000,
    advisorTemperature: 0.8,
};

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
    aiModel: "chatgpt-4o",
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

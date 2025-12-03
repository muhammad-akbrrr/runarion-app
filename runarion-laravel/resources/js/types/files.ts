// Define the storage provider type
export interface StorageProvider {
  id: string;
  name: string;
  icon: string;
  color: string;
  used: number;
  total: number;
  percentage: number;
  enabled: boolean;
}

// Define the author style type
export interface AuthorStyle {
  id: string;
  name: string;
  fileCount: number;
  avatar: string;
  color: string;
  status: 'init_completed' | 'sampling_completed' | 'sampling_failed' | 'profiling_completed' | 'profiling_failed';
  projectIds: string[];
  techniques?: {
    dialogue?: {
      conversation_style?: string;
      dialogue_balance?: string;
      character_voices?: string;
    };
    action?: {
      action_sequences?: string;
      fight_scenes?: string;
      tension?: string;
    };
    literary?: {
      devices?: string;
      metaphors?: string;
      pacing?: string;
      transitions?: string;
      word_patterns?: string;
      scene_structure?: string;
    };
    descriptions?: {
      atmosphere?: string;
      scene_painting?: string;
      character_descriptions?: string;
    };
    worldbuilding?: {
      world_reveals?: string;
      exposition?: string;
      history_magic?: string;
    };
  };
  examples?: {
    dialogue?: string[];
    action?: string[];
    literary?: string[];
    descriptions?: string[];
    worldbuilding?: string[];
  };
}

// Define the project type
export interface Project {
  id: string;
  name: string;
  size: string;
  createdAt: string;
  sharedWith: string[];
  savedIn: string;
}

// Define the props type for the main component
export type FileManagerProps = {
  workspaceId: string;
  workspaceName: string;
  storageProviders: StorageProvider[];
  authorStyles: AuthorStyle[];
  projects: Project[];
};

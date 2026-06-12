import type { PipelineLock } from "./project";

// Define the author style type
export interface AuthorStyle {
  id: string;
  name: string;
  author_name?: string;
  fileCount: number;
  avatar: string;
  color: string;
  status: 'init_completed' | 'init_failed' | 'sampling_completed' | 'sampling_failed' | 'profiling_completed' | 'profiling_failed';
  schemaVersion: number;
  projectIds: string[];
  techniques?: {
    voice?: {
      diction?: string;
      syntax?: string;
      rhythm?: string;
      register?: string;
      figurative_language?: string;
    };
    dialogue?: {
      conversation_style?: string;
      speaker_differentiation?: string;
      dialogue_narration_balance?: string;
    };
    description?: {
      description_density?: string;
      sensory_focus?: string;
      atmosphere_strategy?: string;
    };
    exposition?: {
      exposition_strategy?: string;
      context_integration?: string;
      terminology_handling?: string;
    };
    pacing?: {
      scene_tempo?: string;
      transition_style?: string;
      tension_pattern?: string;
    };
    narrative?: {
      pov_tendency?: string;
      narrative_distance?: string;
      redundancy_avoidance?: string;
    };
  };
  examples?: {
    voice?: string[];
    dialogue?: string[];
    description?: string[];
    exposition?: string[];
    pacing?: string[];
  };
  adaptation?: {
    portable_traits?: string[];
    non_portable_markers?: string[];
    transfer_risks?: string[];
    suppression_guidance?: string[];
  };
}

// Define the project type
export interface Project {
  id: string;
  name: string;
  size: string;
  createdAt: string;
  sharedWith: string[];
  pipelineLock?: PipelineLock | null;
}

// Define the props type for the main component
export type FileManagerProps = {
  workspaceId: string;
  workspaceName: string;
  authorStyles: AuthorStyle[];
  projects: Project[];
};

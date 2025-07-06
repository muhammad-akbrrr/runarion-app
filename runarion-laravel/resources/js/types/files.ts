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

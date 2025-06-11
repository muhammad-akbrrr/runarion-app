export interface HighlightedProject {
    created_at: string;
    project_id: string;
    workspace_id: string;
}

export interface User {
    id: string;
    name: string;
    avatar_url: string | null;
    email: string;
    email_verified_at: string | null;
    last_workspace_id: string;
    settings: Record<string, any> | null;
    notifications: Record<string, boolean> | null;
    highlighted_projects: HighlightedProject[] | null;
}

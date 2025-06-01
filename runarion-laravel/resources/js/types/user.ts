export interface User {
    id: string;
    name: string;
    avatar_url: string | null;
    email: string;
    email_verified_at: string | null;
    last_workspace_id: string;
    settings: Record<string, any> | null;
    notifications: Record<string, boolean> | null;
}

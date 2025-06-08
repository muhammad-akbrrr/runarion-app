export interface Project {
    id: string;
    workspace_id: string;
    folder_id: string | null;
    name: string;
    slug: string;
    settings: Record<string, any> | null;
    is_active: boolean;
    created_at: string;
    updated_at: string;
    deleted_at: string | null;
}

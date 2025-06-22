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

export interface ProjectChapter {
    order: number;
    chapter_name: string;
    content: string;
}

export interface ProjectContent {
    id: string;
    project_id: string;
    content: ProjectChapter[];
    metadata: Record<string, any> | null;
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

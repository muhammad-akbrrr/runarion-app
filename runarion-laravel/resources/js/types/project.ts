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

export interface Project {
    id: string;
    workspace_id: string;
    folder_id: string | null;
    name: string;
    slug: string;
    settings: Record<string, any> | null;
    category: ProjectCategory | null;
    saved_in: string;
    description: string | null;
    access: ProjectAccess[] | null;
    is_active: boolean;
    created_at: string;
    updated_at: string;
    deleted_at: string | null;
}

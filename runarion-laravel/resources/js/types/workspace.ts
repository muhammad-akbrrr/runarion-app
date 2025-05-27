export interface SimpleWorkspace {
    id: number;
    name: string;
    slug: string;
}

export interface SimpleWorkspaceWithRole {
    id: number;
    name: string;
    slug: string;
    cover_image_url: string | null;
    role: string;
}

export interface Workspace {
    id: number;
    name: string;
    slug: string;
    cover_image_url: string | null;
    is_active: boolean;
    timezone: string | null;
    permissions: Record<string, string[]>;
}

export interface WorkspaceMember {
    id: number | null;
    name: string | null;
    email: string;
    avatar_url: string | null;
    role: "member" | "owner" | "admin";
    is_verified: boolean | null;
}

export interface SimpleWorkspace {
    id: string;
    name: string;
    slug: string;
}

export interface SimpleWorkspaceWithRole {
    id: string;
    name: string;
    slug: string;
    cover_image_url: string | null;
    role: string;
}

export interface Workspace {
    id: string;
    name: string;
    slug: string;
    cover_image_url: string | null;
    timezone: string | null;
    settings: Record<string, any> | null;
    permissions: Record<string, string[]> | null;
    cloud_storage: Record<string, any> | null;
    llm: Record<string, any> | null;
    billing_email: string | null;
    billing_name: string | null;
    billing_address: string | null;
    billing_city: string | null;
    billing_state: string | null;
    billing_postal_code: string | null;
    billing_country: string | null;
    billing_phone: string | null;
    billing_tax_id: string | null;
    stripe_customer_id: string | null;
    stripe_subscription_id: string | null;
    trial_ends_at: string | null;
    subscription_ends_at: string | null;
    is_active: boolean;
    created_at: string;
    updated_at: string;
    deleted_at: string | null;
}

export interface WorkspaceMember {
    id: number | null;
    name: string | null;
    email: string;
    avatar_url: string | null;
    role: "member" | "owner" | "admin";
    is_verified: boolean | null;
}

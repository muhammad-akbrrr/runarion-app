export interface WorkspaceSetting {
    theme?: string;
    notifications?: Record<string, boolean>;
}

export interface Workspace {
    id: number;
    name: string;
    slug: string;
    description: string | null;
    cover_image_url: string | null;
    settings: WorkspaceSetting;
    billing_email?: string | null;
    billing_name?: string | null;
    billing_address?: string | null;
    billing_city?: string | null;
    billing_state?: string | null;
    billing_postal_code?: string | null;
    billing_country?: string | null;
    billing_phone?: string | null;
    billing_tax_id?: string | null;
    stripe_customer_id?: string | null;
    stripe_subscription_id?: string | null;
    trial_ends_at: string | null;
    subscription_ends_at: string | null;
    is_active: boolean;
}

export interface WorkspaceField {
    name: keyof Workspace;
    label: string;
    type: "text" | "email" | "checkbox" | "tel";
}

export interface WorkspaceMember {
    id: number | null;
    name: string | null;
    email: string;
    avatar_url: string | null;
    role: string;
    is_verified: boolean | null;
}

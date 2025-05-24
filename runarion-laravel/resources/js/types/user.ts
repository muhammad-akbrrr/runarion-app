export interface User {
    id: number;
    name: string;
    avatar_url: string | null;
    email: string;
    email_verified_at: string | null;
    settings: {
        notifications: Record<string, boolean>;
    };
}

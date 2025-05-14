export interface User {
    id: number;
    name: string;
    email: string;
    settings: Record<string, string | number | boolean>;
    email_verified_at?: string;
}

import type { User } from "@/types/user";

export * from "@/types/user";
export * from "@/types/workspace";
export * from "./project";

export type PageProps<
    T extends Record<string, unknown> = Record<string, unknown>
> = T & {
    auth: {
        user: User;
        csrf_token: string;
    };
    workspaces: SimpleWorkspace[];
    flash?: {
        success?: string | null;
        error?: string | null;
        info?: string | null;
        warning?: string | null;
    };
};

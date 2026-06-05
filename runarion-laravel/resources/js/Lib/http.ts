import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

const CSRF_META_SELECTOR = 'meta[name="csrf-token"]';

axios.defaults.headers.common["X-Requested-With"] = "XMLHttpRequest";
axios.defaults.headers.common["Accept"] = "application/json";

export function syncCsrfToken(token?: string | null): void {
    if (!token) {
        delete axios.defaults.headers.common["X-CSRF-TOKEN"];
        return;
    }

    axios.defaults.headers.common["X-CSRF-TOKEN"] = token;

    const metaTag = document.querySelector(CSRF_META_SELECTOR);
    if (metaTag instanceof HTMLMetaElement) {
        metaTag.content = token;
    }
}

export interface NormalizedHttpError<T = unknown> {
    status?: number;
    message: string;
    data: T | null;
    canceled: boolean;
}

export function normalizeHttpError<T = unknown>(
    error: unknown,
): NormalizedHttpError<T> {
    if (axios.isCancel(error)) {
        return {
            message: "Request cancelled",
            status: undefined,
            data: null,
            canceled: true,
        };
    }

    if (axios.isAxiosError(error)) {
        return {
            message:
                error.response?.data && typeof error.response.data === "object"
                    ? String(
                          (error.response.data as Record<string, unknown>)
                              .message ??
                              (error.response.data as Record<string, unknown>)
                                  .error ??
                              error.message,
                      )
                    : error.message,
            status: error.response?.status,
            data: (error as AxiosError<T>).response?.data ?? null,
            canceled: false,
        };
    }

    return {
        message: error instanceof Error ? error.message : "Unknown error",
        status: undefined,
        data: null,
        canceled: false,
    };
}

axios.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    config.headers.set("X-Requested-With", "XMLHttpRequest");
    config.headers.set("Accept", config.headers.get("Accept") ?? "application/json");

    return config;
});

export const http = axios;

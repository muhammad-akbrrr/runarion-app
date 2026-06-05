import { defineConfig } from "vite";
import laravel from "laravel-vite-plugin";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
    plugins: [
        laravel({
            input: "resources/js/app.tsx",
            refresh: true,
        }),
        react(),
        tailwindcss(),
    ],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./resources/js"),
        },
    },
    server: {
        host: "0.0.0.0",
        port: 5173,
        strictPort: true,
        hmr: {
            host: "localhost",
            protocol: "http",
            clientPort: 5173,
        },
        cors: true,
        headers: {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
        watch: {
            usePolling: true,
            interval: 1000,
            ignored: [
                "**/node_modules/**",
                "**/vendor/**",
                "**/storage/**",
                "**/public/build/**",
            ],
        },
    },
    optimizeDeps: {
        include: [
            "react",
            "react-dom",
            "@inertiajs/react",
            "axios",
            "@radix-ui/react-accordion",
            "@radix-ui/react-alert-dialog",
            "@radix-ui/react-avatar",
            "@radix-ui/react-checkbox",
            "@radix-ui/react-collapsible",
            "@radix-ui/react-context-menu",
            "@radix-ui/react-dialog",
            "@radix-ui/react-dropdown-menu",
            "@radix-ui/react-label",
            "@radix-ui/react-popover",
            "@radix-ui/react-progress",
            "@radix-ui/react-scroll-area",
            "@radix-ui/react-select",
            "@radix-ui/react-separator",
            "@radix-ui/react-slider",
            "@radix-ui/react-slot",
            "@radix-ui/react-switch",
            "@radix-ui/react-tabs",
            "@radix-ui/react-toggle",
            "@radix-ui/react-tooltip",
            "lucide-react",
        ],
        exclude: ["fsevents"],
        esbuildOptions: {
            target: "esnext",
        },
    },
    cacheDir: "node_modules/.vite",
    build: {
        outDir: "public/build",
        rollupOptions: {
            output: {
                manualChunks: {
                    "vendor-react": ["react", "react-dom"],
                    "vendor-inertia": ["@inertiajs/react"],
                    "vendor-radix": [
                        "@radix-ui/react-dialog",
                        "@radix-ui/react-dropdown-menu",
                        "@radix-ui/react-popover",
                        "@radix-ui/react-select",
                    ],
                },
            },
        },
    },
});

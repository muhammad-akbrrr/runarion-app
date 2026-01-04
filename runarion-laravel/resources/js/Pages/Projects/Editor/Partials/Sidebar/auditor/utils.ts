// Utility functions for AuditorToolsTab components

export function getSeverityColor(severity: string): string {
    switch (severity?.toLowerCase()) {
        case "critical":
        case "high":
            return "bg-red-100 text-red-800 border-red-200";
        case "major":
        case "medium":
            return "bg-yellow-100 text-yellow-800 border-yellow-200";
        default:
            return "bg-blue-100 text-blue-800 border-blue-200";
    }
}

export function getIssueTypeColor(type: string): string {
    switch (type?.toLowerCase()) {
        case "contradiction":
            return "bg-red-500";
        case "outdated":
            return "bg-orange-500";
        case "missing_update":
            return "bg-blue-500";
        case "plot_holes":
            return "bg-purple-500";
        case "timeline":
            return "bg-yellow-500";
        case "character":
            return "bg-green-500";
        case "continuity":
            return "bg-pink-500";
        default:
            return "bg-gray-500";
    }
}

// Helper to get CSRF token for fetch requests
export function getCsrfToken(): string {
    return (
        document
            .querySelector('meta[name="csrf-token"]')
            ?.getAttribute("content") || ""
    );
}

// Common fetch options for POST requests
export function getPostOptions(body: object): RequestInit {
    return {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "X-CSRF-TOKEN": getCsrfToken(),
        },
        body: JSON.stringify(body),
    };
}

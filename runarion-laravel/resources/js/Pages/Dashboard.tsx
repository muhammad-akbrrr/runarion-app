import { Card, CardContent, CardHeader, CardTitle } from "@/Components/ui/card";
import AuthenticatedLayout, { BreadcrumbItem } from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";
import { Head } from "@inertiajs/react";

export default function Dashboard({
    workspaceId,
    generationLogs,
    quotaManager
}: PageProps<{
    workspaceId: string;
    generationLogs: {
        request_id: string;
        provider: string;
        model_used: string;
        total_tokens: number;
        processing_time_ms: number;
        success: boolean;
        created_at: string;
        user: { name: string };
        project: { name: string };
    }[];
    quotaManager: {
        remaining: number;
        limit: number;
        usage: number;
    };
}>) {
    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Dashboard", path: "workspace.dashboard" },
        { label: "Home", path: "workspace.dashboard" },
    ].map((item) => ({
        ...item,
        param: { workspace_id: workspaceId },
    }));

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Dashboard" />

            <div className="space-y-6">
                <Card>
                    <CardHeader>
                        <CardTitle>Welcome to your Dashboard</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-foreground">You're logged in!</p>
                    </CardContent>
                </Card>
            </div>
        </AuthenticatedLayout>
    );
}
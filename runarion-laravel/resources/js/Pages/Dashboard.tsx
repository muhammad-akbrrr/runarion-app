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

                <Card>
                    <CardHeader>
                        <CardTitle>Recent Generation Logs</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm text-left border-collapse">
                                <thead className="border-b font-medium">
                                    <tr>
                                        <th>User</th>
                                        <th>Project</th>
                                        <th>Provider</th>
                                        <th>Model</th>
                                        <th>Total Tokens</th>
                                        <th>Processing Time</th>
                                        <th>Status</th>
                                        <th>Created At</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {generationLogs.length === 0 && (
                                        <tr>
                                            <td colSpan={8} className="text-center py-4">
                                                No generation logs found.
                                            </td>
                                        </tr>
                                    )}
                                    {generationLogs.map((log) => (
                                        <tr key={log.request_id} className="border-b">
                                            <td>{log.user.name}</td>
                                            <td>{log.project?.name ?? "N/A"}</td>
                                            <td>{log.provider}</td>
                                            <td>{log.model_used}</td>
                                            <td>{log.total_tokens} tokens</td>
                                            <td>{log.processing_time_ms} ms</td>
                                            <td className={log.success ? "text-green-600" : "text-red-600"}>
                                                {log.success ? "Success" : "Failed"}
                                            </td>
                                            <td>{new Date(log.created_at).toLocaleString()}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader>
                        <CardTitle>Quota Usage</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p>
                        Usage Percentage: <strong>{((quotaManager.usage / quotaManager.limit) * 100).toFixed(1)}</strong> %
                        </p>
                        <p>
                        Used: <strong>{quotaManager.usage}</strong> / {quotaManager.limit} Generations
                        </p>
                        <p>
                        Remaining: <strong>{quotaManager.remaining}</strong>
                        </p>
                    </CardContent>
                </Card>
            </div>
        </AuthenticatedLayout>
    );
}

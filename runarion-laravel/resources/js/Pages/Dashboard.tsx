import { Card, CardContent, CardHeader, CardTitle } from "@/Components/ui/card";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";
import { Head } from "@inertiajs/react";

export default function Dashboard({
    workspaceId,
}: PageProps<{
    workspaceId: string;
}>) {
    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Dashboard", path: "workspace.dashboard" },
        { label: "Home", path: "workspace.dashboard" },
    ].map((item) => ({
        ...item,
        param: workspaceId,
    }));

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Dashboard" />

            <div>
                <div className="w-full">
                    <Card>
                        <CardHeader>
                            <CardTitle>Welcome to your Dashboard</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <p className="text-foreground">You're logged in!</p>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </AuthenticatedLayout>
    );
}

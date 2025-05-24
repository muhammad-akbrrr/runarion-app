import { Card, CardContent, CardHeader, CardTitle } from "@/Components/ui/card";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps, SimpleWorkspaceWithRole } from "@/types";
import { Head } from "@inertiajs/react";
import WorkspaceCard from "./Partials/WorkspaceCard";

export default function List({
    workspaces,
}: PageProps<{
    workspaces: SimpleWorkspaceWithRole[];
}>) {
    const breadcrumbs: BreadcrumbItem[] = [
        { label: "My Settings", path: "profile.edit" },
        { label: "Workspaces", path: "workspace.list" },
    ];

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="My Workspaces" />

            <Card className="w-full h-full ">
                <CardHeader>
                    <CardTitle className="text-2xl">My Workspaces</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-row flex-wrap gap-4">
                    {workspaces.map((workspace) => (
                        <WorkspaceCard
                            key={workspace.id}
                            workspace={workspace}
                        />
                    ))}
                    <WorkspaceCard workspace={null} />
                </CardContent>
            </Card>
        </AuthenticatedLayout>
    );
}

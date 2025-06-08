import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";
import { Head } from "@inertiajs/react";

export default function ProjectSettings({
    workspaceId,
    projectId,
}: PageProps<{
    workspaceId: string;
    projectId: string;
}>) {
    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Project Settings", path: "workspace.projects.edit" },
        { label: "General", path: "workspace.projects.edit" },
    ].map((item) => ({
        ...item,
        param: {} as any,
    }));

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Project Settings" />

            <div></div>
        </AuthenticatedLayout>
    );
}

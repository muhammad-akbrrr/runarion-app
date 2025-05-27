import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/Components/ui/card";
import { Separator } from "@/Components/ui/separator";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";
import { Head } from "@inertiajs/react";
import ConnectionCard from "./Partials/ConnectionCard";

interface CloudStorageDataItem {
    enabled: boolean;
}

export default function CloudStorage({
    workspaceId,
    data,
    isUserAdmin,
    isUserOwner,
}: PageProps<{
    workspaceId: number;
    data: Record<string, CloudStorageDataItem>;
    isUserAdmin: boolean;
    isUserOwner: boolean;
}>) {
    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Workspace Settings", path: "workspace.edit" },
        { label: "Cloud Storage", path: "workspace.edit.cloud-storage" },
    ].map((item) => ({
        ...item,
        param: workspaceId,
    }));

    const connections = [
        {
            key: "google_drive",
            logo_url: "/images/google_drive.png",
            name: "Google Drive",
            description:
                "Attach, preview, share and create Google Drive items inside of Runarion.",
        },
        {
            key: "dropbox",
            logo_url: "/images/dropbox.png",
            name: "Dropbox",
            description:
                "Attach, preview, share and create Dropbox items inside of Runarion.",
        },
        {
            key: "onedrive",
            logo_url: "/images/onedrive.png",
            name: "OneDrive",
            description:
                "Attach, preview, share and create OneDrive items inside of Runarion.",
        },
    ];

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Cloud Storage" />

            <Card className="w-full h-full ">
                <CardHeader>
                    <CardTitle className="text-2xl">Cloud Storage</CardTitle>
                    <CardDescription className="text-sm">
                        Enable or disable cloud storage integrations with your
                        workspace
                    </CardDescription>
                </CardHeader>
                <Separator className="mx-6" style={{ width: "auto" }} />
                <CardContent className="flex flex-col gap-4">
                    {connections.map((connection) => (
                        <ConnectionCard
                            key={connection.key}
                            logo_url={connection.logo_url}
                            name={connection.name}
                            description={connection.description}
                            connected={data[connection.key]?.enabled ?? false}
                            onConnect={() => {}}
                            disabled={!isUserAdmin && !isUserOwner}
                        />
                    ))}
                </CardContent>
            </Card>
        </AuthenticatedLayout>
    );
}

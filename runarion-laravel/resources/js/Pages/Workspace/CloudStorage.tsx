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
import { Head, router } from "@inertiajs/react";
import ConnectionCard from "./Partials/ConnectionCard";

interface CloudStorageDataItem {
    enabled: boolean;
}

export default function CloudStorage({
    workspaceId,
    data,
    isUserAdmin,
    isUserOwner,
    flash,
}: PageProps<{
    workspaceId: string;
    data: Record<string, CloudStorageDataItem>;
    isUserAdmin: boolean;
    isUserOwner: boolean;
    flash?: { success?: string; error?: string; info?: string };
}>) {
    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Workspace Settings", path: "workspace.edit" },
        { label: "Cloud Storage", path: "workspace.edit.cloud-storage" },
    ].map((item) => ({
        ...item,
        param: { workspace_id: workspaceId },
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

    const handleConnect = (key: string) => {
        if (key === "google_drive") {
            window.location.href = route('cloudstorage.google.redirect', { workspace_id: workspaceId });
        }
    };

    const handleDisconnect = (key: string) => {
        if (key === "google_drive") {
            router.delete(route('cloudstorage.google.disconnect', { workspace_id: workspaceId }));
        }
    };

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
                            onConnect={() => handleConnect(connection.key)}
                            onDisconnect={() => handleDisconnect(connection.key)}
                            disabled={!isUserAdmin && !isUserOwner}
                        />
                    ))}
                </CardContent>
            </Card>
        </AuthenticatedLayout>
    );
}

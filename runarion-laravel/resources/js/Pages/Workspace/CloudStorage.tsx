import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/Components/ui/card";
import { Separator } from "@/Components/ui/separator";
import AuthenticatedLayout, { BreadcrumbItem } from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";
import { Head, router } from "@inertiajs/react";
import { useState } from "react";
import ConnectionCard from "./Partials/ConnectionCard";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";
import { Button } from "@/Components/ui/button";

interface CloudStorageDataItem {
    enabled: boolean;
}

export default function CloudStorage({
    workspaceId,
    data,
    isUserAdmin,
    isUserOwner,
}: PageProps<{
    workspaceId: string;
    data: Record<string, CloudStorageDataItem>;
    isUserAdmin: boolean;
    isUserOwner: boolean;
}>) {
    const [selectedKey, setSelectedKey] = useState<string | null>(null);
    const [dialogOpen, setDialogOpen] = useState(false);

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
            description: "Attach, preview, share and create Google Drive items inside of Runarion.",
        },
        {
            key: "dropbox",
            logo_url: "/images/dropbox.png",
            name: "Dropbox",
            description: "Attach, preview, share and create Dropbox items inside of Runarion.",
        },
        {
            key: "onedrive",
            logo_url: "/images/onedrive.png",
            name: "OneDrive",
            description: "Attach, preview, share and create OneDrive items inside of Runarion.",
        },
    ];

    const handleAction = (key: string) => {
        const isConnected = data[key]?.enabled;
        const routeParams = { workspace_id: workspaceId, provider: key };

        if (isConnected) {
            router.delete(route("cloudstorage.disconnect", routeParams));
        } else {
            window.location.href = route("cloudstorage.redirect", routeParams);
        }
    };

    const openConfirmation = (key: string) => {
        setSelectedKey(key);
        setDialogOpen(true);
    };

    const selected = selectedKey ? connections.find(c => c.key === selectedKey) : null;
    const isConnected = selectedKey ? data[selectedKey]?.enabled : false;

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Cloud Storage" />

            <Card className="w-full">
                <CardHeader>
                    <CardTitle className="text-2xl">Cloud Storage</CardTitle>
                    <CardDescription className="text-sm">
                        Enable or disable cloud storage integrations with your workspace.
                    </CardDescription>
                </CardHeader>
                <Separator className="w-full" />
                <CardContent className="flex flex-col gap-4 overflow-x-hidden">
                    {connections.map((connection) => (
                        <ConnectionCard
                            key={connection.key}
                            logo_url={connection.logo_url}
                            name={connection.name}
                            description={connection.description}
                            connected={data[connection.key]?.enabled ?? false}
                            onConnect={() => openConfirmation(connection.key)}
                            disabled={!isUserAdmin && !isUserOwner}
                        />
                    ))}
                </CardContent>
            </Card>

            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>
                            {isConnected ? "Disconnect Storage" : "Connect Storage"}
                        </DialogTitle>
                        <DialogDescription>
                            {isConnected
                                ? `Are you sure you want to disconnect ${selected?.name}?`
                                : `You're about to connect ${selected?.name} to your workspace.`}
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            variant={isConnected ? "destructive" : "default"}
                            onClick={() => {
                                if (selectedKey) handleAction(selectedKey);
                                setDialogOpen(false);
                            }}
                        >
                            {isConnected ? "Disconnect" : "Connect"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </AuthenticatedLayout>
    );
}

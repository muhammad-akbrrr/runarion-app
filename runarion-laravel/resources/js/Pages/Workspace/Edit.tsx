import { AvatarUpload } from "@/Components/ui/avatar-upload";
import { Button } from "@/Components/ui/button";
import {
    Card,
    CardContent,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/Components/ui/card";
import { Input } from "@/Components/ui/input";
import { Label } from "@/Components/ui/label";
import { Separator } from "@/Components/ui/separator";
import { Switch } from "@/Components/ui/switch";
import { Textarea } from "@/Components/ui/textarea";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps, Workspace } from "@/types";
import { Transition } from "@headlessui/react";
import { Head, useForm } from "@inertiajs/react";
import { LayoutGrid } from "lucide-react";
import { FormEventHandler, useState } from "react";
import DeleteWorkspaceDialog from "./Partials/DeleteWorkspaceDialog";
import LeaveWorkspaceDialog from "./Partials/LeaveWorkspaceDialog";

export default function Edit({
    workspace,
    isUserAdmin,
    isUserOwner,
}: PageProps<{
    workspace: Workspace;
    isUserAdmin: boolean;
    isUserOwner: boolean;
}>) {
    const isUserOwnerOrAdmin = isUserOwner || isUserAdmin;

    const [openDialog, setOpenDialog] = useState(false);

    const { data, setData, post, errors, processing, recentlySuccessful } =
        useForm({
            name: workspace.name,
            description: workspace.description,
            settings: workspace.settings,
            photo: null as File | null,
        });

    const submit: FormEventHandler = (e) => {
        e.preventDefault();
        post(route("workspace.update", workspace.id), {
            forceFormData: true,
        });
    };

    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Workspace Settings", path: "workspace.edit" },
        { label: "General", path: "workspace.edit" },
    ].map((item) => ({
        ...item,
        param: workspace.id,
    }));

    const permissions = [
        {
            key: "invite_members",
            title: "Invite Members",
            description:
                "Gives the user permission to invite members to the Workspace.",
        },
        {
            key: "invite_guests",
            title: "Invite Guests",
            description:
                "Gives the user permission to invite guests to the Workspace.",
        },
        {
            key: "manage_guests",
            title: "Manage Users",
            description:
                "Grants the user permission to view and manage all members and guests in a Workspace. This includes adding and removing users, changing roles, and managing invites.",
        },
        {
            key: "create_projects",
            title: "Create Projects",
            description:
                "Gives the user the permission to create and edit projects. When toggled off, users are able to still access the project, just not create them.",
        },
        {
            key: "delete_projects",
            title: "Delete Projects",
            description: "Gives the user the permission to delete projects.",
        },
    ];

    const roles = ["guest", "member", "admin"];

    const handleCheckPermission = (
        permission: string,
        role: string,
        checked: boolean
    ) => {
        const currentPermissions = data.settings.permissions[permission] || [];
        const newPermissions = checked
            ? [...currentPermissions, role]
            : currentPermissions.filter((r) => r !== role);
        setData("settings", {
            ...data.settings,
            permissions: {
                ...data.settings.permissions,
                [permission]: newPermissions,
            },
        });
    };

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="General Settings" />

            <Card className="w-full h-full ">
                <form onSubmit={submit}>
                    <CardHeader>
                        <CardTitle className="text-2xl">
                            General Settings
                        </CardTitle>
                    </CardHeader>
                    <Separator
                        className="mt-2 mb-4 mx-6"
                        style={{ width: "auto" }}
                    />
                    <CardContent className="flex flex-col gap-2 mt-2">
                        <AvatarUpload
                            label="Workspace Photo"
                            src={workspace.cover_image_url}
                            onChange={(file) => setData("photo", file)}
                            fallback={LayoutGrid}
                            error={errors.photo}
                            className="mb-2"
                        />
                        <div className="space-y-1">
                            <Label htmlFor="name">Name</Label>
                            <Input
                                id="name"
                                value={data.name}
                                onChange={(e) =>
                                    setData("name", e.target.value)
                                }
                                required
                                autoComplete="name"
                                disabled={!isUserOwnerOrAdmin}
                            />
                            <div className="text-sm text-destructive -mt-1.5">
                                {errors.name || "\u00A0"}
                            </div>
                        </div>
                        <div className="space-y-1">
                            <Label htmlFor="description">Description</Label>
                            <Textarea
                                id="description"
                                value={data.description ?? ""}
                                onChange={(e) =>
                                    setData("description", e.target.value)
                                }
                                rows={3}
                                placeholder="A short description of your workspace."
                                disabled={!isUserOwnerOrAdmin}
                            />
                            <div className="text-sm text-destructive -mt-1.5">
                                {errors.description || "\u00A0"}
                            </div>
                        </div>
                        <div className="space-y-1">
                            <Label htmlFor="timezone">Timezone</Label>
                            <Input
                                id="timezone"
                                value={data.settings.timezone ?? ""}
                                onChange={(e) =>
                                    setData("settings", {
                                        ...data.settings,
                                        timezone: e.target.value,
                                    })
                                }
                                required
                                disabled={!isUserOwnerOrAdmin}
                            />
                            <div className="text-sm text-destructive -mt-1.5">
                                {
                                    // @ts-ignore
                                    errors["settings.timezone"] || "\u00A0"
                                }
                            </div>
                        </div>
                    </CardContent>
                    <CardHeader>
                        <CardTitle className="mt-4 text-2xl">
                            Role Permission
                        </CardTitle>
                    </CardHeader>
                    <Separator
                        className="mt-2 mb-4 mx-6"
                        style={{ width: "auto" }}
                    />
                    <CardContent className="mt-2">
                        <div className="border rounded-md text-sm">
                            <div className="flex font-medium border-b">
                                <div className="flex-1 px-4 py-3 border-r">
                                    Actions
                                </div>
                                {roles.map((role) => (
                                    <div
                                        key={role}
                                        className="w-24 px-4 py-3 text-center capitalize border-r last:border-r-0"
                                    >
                                        {role}
                                    </div>
                                ))}
                            </div>
                            {permissions.map((item, idx) => (
                                <div
                                    key={idx}
                                    className="flex items-stretch border-b last:border-b-0"
                                >
                                    <div className="flex-1 px-4 py-3 border-r">
                                        <div className="font-medium">
                                            {item.title}
                                        </div>
                                        <div className="text-muted-foreground text-xs">
                                            {item.description}
                                        </div>
                                    </div>
                                    {roles.map((role, rIdx) => (
                                        <div
                                            key={rIdx}
                                            className="w-24 flex items-center justify-center px-4 py-3 border-r last:border-r-0"
                                        >
                                            <Switch
                                                checked={data.settings.permissions[
                                                    item.key
                                                ]?.includes(role)}
                                                onCheckedChange={(checked) =>
                                                    handleCheckPermission(
                                                        item.key,
                                                        role,
                                                        checked
                                                    )
                                                }
                                                disabled={!isUserOwner}
                                            />
                                        </div>
                                    ))}
                                </div>
                            ))}
                        </div>
                    </CardContent>
                    <CardFooter className="flex justify-between mt-6">
                        <>
                            <Button
                                type="button"
                                disabled={processing}
                                variant="destructive"
                                onClick={() => setOpenDialog(true)}
                            >
                                {isUserOwner
                                    ? "Delete Workspace"
                                    : "Leave Workspace"}
                            </Button>
                            {isUserOwner ? (
                                <DeleteWorkspaceDialog
                                    workspaceId={workspace.id}
                                    open={openDialog}
                                    onOpenChange={setOpenDialog}
                                />
                            ) : (
                                <LeaveWorkspaceDialog
                                    workspaceId={workspace.id}
                                    open={openDialog}
                                    onOpenChange={setOpenDialog}
                                />
                            )}
                        </>
                        {isUserOwnerOrAdmin && (
                            <div className="flex items-center gap-4">
                                <Transition
                                    show={recentlySuccessful}
                                    enter="transition ease-in-out"
                                    enterFrom="opacity-0"
                                    leave="transition ease-in-out"
                                    leaveTo="opacity-0"
                                >
                                    <p className="text-sm text-muted-foreground">
                                        Saved
                                    </p>
                                </Transition>
                                <Button type="submit" disabled={processing}>
                                    Save Changes
                                </Button>
                            </div>
                        )}
                    </CardFooter>
                </form>
            </Card>
        </AuthenticatedLayout>
    );
}

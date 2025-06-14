import { AvatarUpload } from "@/Components/avatar-upload";
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
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/Components/ui/select";
import { Separator } from "@/Components/ui/separator";
import { Switch } from "@/Components/ui/switch";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/Components/ui/table";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps, Workspace } from "@/types";
import { Transition } from "@headlessui/react";
import { Head, useForm } from "@inertiajs/react";
import { FormEventHandler, useState } from "react";
import { allTimezones, useTimezoneSelect } from "react-timezone-select";
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

    const { options: timezoneOptions } = useTimezoneSelect(allTimezones);

    const { data, setData, post, errors, processing, recentlySuccessful } =
        useForm({
            name: workspace.name,
            timezone: workspace.timezone ?? null,
            permissions: workspace.permissions ?? {},
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
        param: { workspace_id: workspace.id },
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
        const currentPermissions = data.permissions[permission] || [];
        const newPermissions = checked
            ? [...currentPermissions, role]
            : currentPermissions.filter((r) => r !== role);
        setData("permissions", {
            ...data.permissions,
            [permission]: newPermissions,
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
                            alt={workspace.name}
                            error={errors.photo}
                            className="mb-2"
                        />
                        <div className="space-y-1 flex flex-col gap-1">
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
                        <div className="space-y-1 flex flex-col gap-1">
                            <Label htmlFor="timezone">Timezone</Label>
                            <Select
                                value={data.timezone ?? undefined}
                                onValueChange={(value) =>
                                    setData("timezone", value)
                                }
                                disabled={!isUserOwnerOrAdmin}
                            >
                                <SelectTrigger
                                    id="timezone"
                                    size="default"
                                    className="w-full hover:cursor-pointer"
                                >
                                    <SelectValue placeholder="Select a timezone" />
                                </SelectTrigger>
                                <SelectContent position="popper">
                                    {timezoneOptions.map((option) => (
                                        <SelectItem
                                            key={option.value}
                                            value={option.value}
                                        >
                                            {option.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <div className="text-sm text-destructive -mt-1.5">
                                {errors.timezone || "\u00A0"}
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
                        <div className="border rounded-md">
                            <Table className="rounded-md  overflow-hidden">
                                <TableHeader>
                                    <TableRow className="border-b">
                                        <TableHead className="border-r rounded-tl-md">
                                            Actions
                                        </TableHead>
                                        {roles.map((role, index) => (
                                            <TableHead
                                                key={role}
                                                className={`text-center capitalize border-r ${
                                                    index === roles.length - 1
                                                        ? "last:border-r-0 rounded-tr-md"
                                                        : ""
                                                }`}
                                            >
                                                {role}
                                            </TableHead>
                                        ))}
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {permissions.map((item, index) => (
                                        <TableRow
                                            key={item.key}
                                            className="border-b last:border-b-0"
                                        >
                                            <TableCell
                                                className={`border-r ${
                                                    index ===
                                                    permissions.length - 1
                                                        ? "rounded-bl-md"
                                                        : ""
                                                }`}
                                            >
                                                <div className="font-medium">
                                                    {item.title}
                                                </div>
                                                <div className="text-muted-foreground text-xs">
                                                    {item.description}
                                                </div>
                                            </TableCell>
                                            {roles.map((role, rIndex) => (
                                                <TableCell
                                                    key={role}
                                                    className={`text-center border-r ${
                                                        rIndex ===
                                                        roles.length - 1
                                                            ? "last:border-r-0"
                                                            : ""
                                                    } ${
                                                        index ===
                                                            permissions.length -
                                                                1 &&
                                                        rIndex ===
                                                            roles.length - 1
                                                            ? "rounded-br-md"
                                                            : ""
                                                    }`}
                                                >
                                                    <Switch
                                                        checked={data.permissions[
                                                            item.key
                                                        ]?.includes(role)}
                                                        onCheckedChange={(
                                                            checked
                                                        ) =>
                                                            handleCheckPermission(
                                                                item.key,
                                                                role,
                                                                checked
                                                            )
                                                        }
                                                        disabled={!isUserOwner}
                                                    />
                                                </TableCell>
                                            ))}
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
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

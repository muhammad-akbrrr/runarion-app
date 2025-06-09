import { Button } from "@/Components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/Components/ui/card";
import { Separator } from "@/Components/ui/separator";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/Components/ui/select";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps, Project, ProjectRole } from "@/types";
import { Head, router, useForm } from "@inertiajs/react";
import { CirclePlus } from "lucide-react";
import { useState } from "react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";

interface Props
    extends PageProps<{
        workspaceId: string;
        projectId: string;
        project: Project;
    }> {}

const PROJECT_ROLES: ProjectRole[] = ["editor", "manager", "admin"];

export default function ProjectAccess({
    workspaceId,
    projectId,
    project,
}: Props) {
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [memberToDelete, setMemberToDelete] = useState<{
        id: string;
        name: string;
    } | null>(null);
    const [isRemoving, setIsRemoving] = useState(false);

    const roleForm = useForm({
        user_id: "",
        role: "" as ProjectRole,
    });

    const deleteForm = useForm({
        user_id: "",
    });

    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Project Settings", path: "workspace.projects.edit" },
        { label: "Access", path: "workspace.projects.edit.access" },
    ].map((item) => ({
        ...item,
        param: { project_id: projectId, workspace_id: workspaceId },
    }));

    // Helper functions for role-based access control
    const isAdmin = project.current_user_access?.role === "admin";
    const isManager = project.current_user_access?.role === "manager";
    const isOriginalAuthor =
        Number(project.current_user_access?.user.id) ===
        project.original_author;
    const isCurrentUser = (userId: string) =>
        userId === project.current_user_access?.user.id;

    const canRemoveMember = (
        member: NonNullable<Project["access"]>[number]
    ) => {
        // If user is not admin or manager, they can't remove anyone
        if (!isAdmin && !isManager) return false;

        // If trying to remove self
        if (isCurrentUser(member.user.id)) {
            // Original author can't remove themselves
            if (isOriginalAuthor) return false;
            // Others can remove themselves
            return true;
        }

        // Manager logic
        if (isManager) {
            // Managers can remove editors and other managers
            return member.role === "editor" || member.role === "manager";
        }

        // Admin logic
        if (isAdmin) {
            // Original author admin can remove other admins
            if (isOriginalAuthor) {
                return true;
            }
            // Other admins can't remove other admins
            if (member.role === "admin") {
                return false;
            }
            // Can remove managers and editors
            return true;
        }

        return false;
    };

    const handleRoleChange = (userId: string, newRole: ProjectRole) => {
        router.patch(
            route("workspace.projects.update.member.role", {
                workspace_id: workspaceId,
                project_id: projectId,
            }),
            {
                user_id: userId,
                role: newRole,
            },
            {
                preserveScroll: true,
            }
        );
    };

    const handleRemoveMember = () => {
        if (!memberToDelete || isRemoving) return;

        setIsRemoving(true);
        router.delete(
            route("workspace.projects.remove.member", {
                workspace_id: workspaceId,
                project_id: projectId,
            }),
            {
                data: {
                    user_id: memberToDelete.id,
                },
                preserveScroll: true,
                onSuccess: () => {
                    setDeleteDialogOpen(false);
                    setMemberToDelete(null);
                    setIsRemoving(false);
                },
                onError: () => {
                    setIsRemoving(false);
                },
            }
        );
    };

    const handleRemoveClick = (
        member: NonNullable<Project["access"]>[number]
    ) => {
        setMemberToDelete({
            id: member.user.id,
            name: member.user.name,
        });
        setDeleteDialogOpen(true);
    };

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Project Access" />

            <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Remove Project Member</DialogTitle>
                        <DialogDescription>
                            Are you sure you want to remove{" "}
                            {memberToDelete?.name} from this project?
                        </DialogDescription>
                    </DialogHeader>

                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => {
                                setDeleteDialogOpen(false);
                                setMemberToDelete(null);
                            }}
                            disabled={isRemoving}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={handleRemoveMember}
                            disabled={isRemoving}
                        >
                            {isRemoving ? "Removing..." : "Confirm"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Card className="w-full h-full gap-0">
                <CardHeader>
                    <CardTitle className="text-2xl">
                        Manage Project Access
                    </CardTitle>
                </CardHeader>
                <Separator
                    className="mt-2 mb-4 mx-6"
                    style={{ width: "auto" }}
                />
                <CardContent>
                    <div className="flex flex-col gap-4">
                        <div className="flex items-center justify-between">
                            <h2 className="font-semibold">Project Members</h2>
                            <Button>
                                <CirclePlus />
                                Add Members
                            </Button>
                        </div>
                        <div className="flex flex-col">
                            {project.access?.map((member) => (
                                <div
                                    key={member.user.id}
                                    className="flex items-center justify-between border-b py-2"
                                >
                                    <div>
                                        <p className="font-medium text-sm">
                                            {member.user.name}
                                        </p>
                                        <p className="text-sm text-gray-500">
                                            {member.user.email}
                                        </p>
                                    </div>
                                    <div className="flex items-center space-x-4">
                                        <Select
                                            defaultValue={member.role}
                                            disabled={(() => {
                                                const isSelf = isCurrentUser(
                                                    member.user.id
                                                );
                                                const isMemberOriginalAuthor =
                                                    Number(member.user.id) ===
                                                    project.original_author;

                                                // Original author can't change their own role
                                                if (
                                                    isOriginalAuthor &&
                                                    isSelf
                                                ) {
                                                    return true;
                                                }

                                                // Other admins can't demote the original author
                                                if (
                                                    isAdmin &&
                                                    !isOriginalAuthor &&
                                                    isMemberOriginalAuthor
                                                ) {
                                                    return true;
                                                }

                                                // Editors can't change anyone's role
                                                if (!isAdmin && !isManager) {
                                                    return true;
                                                }

                                                // Managers can only change editors and other managers
                                                if (isManager && !isAdmin) {
                                                    if (
                                                        member.role === "admin"
                                                    ) {
                                                        return true;
                                                    }
                                                    return false;
                                                }

                                                // Admins can change anyone's role except original author
                                                if (isAdmin) {
                                                    if (
                                                        isMemberOriginalAuthor
                                                    ) {
                                                        return true;
                                                    }
                                                    return false;
                                                }

                                                return false;
                                            })()}
                                            onValueChange={(
                                                value: ProjectRole
                                            ) => {
                                                handleRoleChange(
                                                    member.user.id,
                                                    value
                                                );
                                            }}
                                        >
                                            <SelectTrigger
                                                size="default"
                                                className="w-32 hover:cursor-pointer"
                                            >
                                                <SelectValue placeholder="Select a role">
                                                    {member.role
                                                        .charAt(0)
                                                        .toUpperCase() +
                                                        member.role.slice(1)}
                                                </SelectValue>
                                            </SelectTrigger>
                                            <SelectContent position="popper">
                                                {PROJECT_ROLES.map((role) => (
                                                    <SelectItem
                                                        key={role}
                                                        value={role}
                                                    >
                                                        {role
                                                            .charAt(0)
                                                            .toUpperCase() +
                                                            role.slice(1)}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        {(isAdmin || isManager) && (
                                            <Button
                                                variant="destructive"
                                                size="sm"
                                                disabled={
                                                    !canRemoveMember(member) ||
                                                    isRemoving
                                                }
                                                onClick={() =>
                                                    handleRemoveClick(member)
                                                }
                                            >
                                                Remove
                                            </Button>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                        {project.access && project.access.length > 0 && (
                            <div className="flex items-center justify-between mt-2">
                                <div className="text-sm text-muted-foreground">
                                    Showing 1 to {project.access.length} of{" "}
                                    {project.access.length} members
                                </div>
                                <div className="flex items-center gap-2">
                                    <Button variant="outline" disabled>
                                        Previous
                                    </Button>
                                    <Button disabled>Next</Button>
                                </div>
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>
        </AuthenticatedLayout>
    );
}

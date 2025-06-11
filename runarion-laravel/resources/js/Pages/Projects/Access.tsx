import { Button } from "@/Components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/Components/ui/card";
import { Separator } from "@/Components/ui/separator";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps, Project, ProjectRole, User } from "@/types";
import { Head, router } from "@inertiajs/react";
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
import ProjectMemberItem from "./Partials/ProjectMemberItem";
import AddProjectMemberDialog from "./Partials/AddProjectMemberDialog";

interface Props
    extends PageProps<{
        workspaceId: string;
        projectId: string;
        project: Project;
        workspaceMembers: User[];
    }> {}

const PROJECT_ROLES: ProjectRole[] = ["editor", "manager", "admin"];

export default function ProjectAccess({
    workspaceId,
    projectId,
    project,
    workspaceMembers,
}: Props) {
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [addMemberDialogOpen, setAddMemberDialogOpen] = useState(false);
    const [memberToDelete, setMemberToDelete] = useState<{
        id: string;
        name: string;
    } | null>(null);
    const [isRemoving, setIsRemoving] = useState(false);

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
        if (!isAdmin && !isManager) return false;

        // If trying to remove self
        if (isCurrentUser(member.user.id)) {
            if (isOriginalAuthor) return false;
            return true;
        }

        // Manager logic
        if (isManager) {
            return member.role === "editor" || member.role === "manager";
        }

        // Admin logic
        if (isAdmin) {
            if (Number(member.user.id) === project.original_author) {
                return false;
            }
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

            <AddProjectMemberDialog
                isOpen={addMemberDialogOpen}
                onClose={() => setAddMemberDialogOpen(false)}
                workspaceMembers={workspaceMembers}
                project={project}
                workspaceId={workspaceId}
                projectId={projectId}
            />

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
                            <Button
                                onClick={() => setAddMemberDialogOpen(true)}
                                disabled={!isAdmin && !isManager}
                            >
                                <CirclePlus />
                                Add Members
                            </Button>
                        </div>
                        <div className="flex flex-col">
                            {project.access?.map((member) => (
                                <ProjectMemberItem
                                    key={member.user.id}
                                    member={member}
                                    project={project}
                                    isAdmin={isAdmin}
                                    isManager={isManager}
                                    isOriginalAuthor={isOriginalAuthor}
                                    isCurrentUser={isCurrentUser}
                                    canRemoveMember={canRemoveMember}
                                    isRemoving={isRemoving}
                                    onRoleChange={handleRoleChange}
                                    onRemoveClick={handleRemoveClick}
                                    projectRoles={PROJECT_ROLES}
                                />
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

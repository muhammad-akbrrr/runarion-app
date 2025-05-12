import { Card, CardContent } from "@/Components/ui/card";
import AuthenticatedLayout from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";
import { Workspace, WorkspaceMember } from "@/types/workspace";
import { Head, usePage } from "@inertiajs/react";
import DeleteWorkspaceForm from "./Partials/DeleteWorkspaceForm";
import ManageWorkspaceMemberForm from "./Partials/ManageWorkspaceMemberForm";
import UpdateWorkspaceBillingForm from "./Partials/UpdateWorkspaceBillingForm";
import UpdateWorkspaceInformationForm from "./Partials/UpdateWorkspaceInformationForm";
import UpdateWorkspaceSettingForm from "./Partials/UpdateWorkspaceSettingForm";

export default function Edit({
    workspace,
    workspaceMembers,
    isUserAdmin,
    isUserOwner,
}: PageProps<{
    workspace: Workspace;
    workspaceMembers: WorkspaceMember[];
    isUserAdmin: boolean;
    isUserOwner: boolean;
}>) {
    const { auth } = usePage().props;
    const isUserOwnerOrAdmin = isUserOwner || isUserAdmin;

    return (
        <AuthenticatedLayout
            user={auth.user}
            header={
                <h2 className="text-xl font-semibold leading-tight text-foreground">
                    Workspace
                </h2>
            }
        >
            <Head title="Workspace" />

            <div className="py-12">
                <div className="mx-auto max-w-7xl space-y-6 sm:px-6 lg:px-8">
                    <Card>
                        <CardContent>
                            <UpdateWorkspaceInformationForm
                                workspace={workspace}
                                isUserOwnerOrAdmin={isUserOwnerOrAdmin}
                                className="max-w-xl"
                            />
                        </CardContent>
                    </Card>

                    <Card>
                        <CardContent>
                            <UpdateWorkspaceSettingForm
                                workspace={workspace}
                                isUserOwnerOrAdmin={isUserOwnerOrAdmin}
                                className="max-w-xl"
                            />
                        </CardContent>
                    </Card>

                    <Card>
                        <CardContent>
                            <ManageWorkspaceMemberForm
                                userId={auth.user.id}
                                workspaceId={workspace.id}
                                workspaceMembers={workspaceMembers}
                                isUserOwner={isUserOwner}
                                isUserAdmin={isUserAdmin}
                                className="max-w-xl"
                            />
                        </CardContent>
                    </Card>

                    {isUserOwnerOrAdmin && (
                        <Card>
                            <CardContent>
                                <UpdateWorkspaceBillingForm
                                    workspace={workspace}
                                    isUserOwnerOrAdmin={isUserOwnerOrAdmin}
                                    className="max-w-xl"
                                />
                            </CardContent>
                        </Card>
                    )}

                    {isUserOwner && (
                        <Card>
                            <CardContent>
                                <DeleteWorkspaceForm
                                    workspace={workspace}
                                    className="max-w-xl"
                                />
                            </CardContent>
                        </Card>
                    )}
                </div>
            </div>
        </AuthenticatedLayout>
    );
}

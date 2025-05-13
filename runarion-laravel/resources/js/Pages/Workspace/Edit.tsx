import { Card, CardContent } from "@/Components/ui/card";
import AuthenticatedLayout from "@/Layouts/AuthenticatedLayout";
import { PageProps, Workspace, WorkspaceMember } from "@/types";
import { Head, usePage } from "@inertiajs/react";
import DeleteWorkspaceSection from "./Partials/DeleteWorkspaceSection";
import LeaveWorkspaceSection from "./Partials/LeaveWorkspaceSection";
import ManageWorkspaceMemberSection from "./Partials/ManageWorkspaceMemberSection";
import UpdateWorkspaceBillingSection from "./Partials/UpdateWorkspaceBillingSection";
import UpdateWorkspaceInformationSection from "./Partials/UpdateWorkspaceInformationSection";
import UpdateWorkspaceSettingSection from "./Partials/UpdateWorkspaceSettingSection";

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
                            <UpdateWorkspaceInformationSection
                                workspace={workspace}
                                isUserOwnerOrAdmin={isUserOwnerOrAdmin}
                                className="max-w-xl"
                            />
                        </CardContent>
                    </Card>

                    <Card>
                        <CardContent>
                            <UpdateWorkspaceSettingSection
                                workspace={workspace}
                                isUserOwnerOrAdmin={isUserOwnerOrAdmin}
                                className="max-w-xl"
                            />
                        </CardContent>
                    </Card>

                    <Card>
                        <CardContent>
                            <ManageWorkspaceMemberSection
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
                                <UpdateWorkspaceBillingSection
                                    workspace={workspace}
                                    isUserOwnerOrAdmin={isUserOwnerOrAdmin}
                                    className="max-w-xl"
                                />
                            </CardContent>
                        </Card>
                    )}

                    {!isUserOwner && (
                        <Card>
                            <CardContent>
                                <LeaveWorkspaceSection
                                    workspaceId={workspace.id}
                                    className="max-w-xl"
                                />
                            </CardContent>
                        </Card>
                    )}

                    {isUserOwner && (
                        <Card>
                            <CardContent>
                                <DeleteWorkspaceSection
                                    workspaceId={workspace.id}
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

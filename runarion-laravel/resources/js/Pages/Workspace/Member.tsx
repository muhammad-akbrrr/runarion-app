import { Button } from "@/Components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/Components/ui/card";
import { Separator } from "@/Components/ui/separator";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps, WorkspaceMember } from "@/types";
import { Head, router } from "@inertiajs/react";
import { CirclePlus } from "lucide-react";
import { useState } from "react";
import AddWorkspaceMemberDialog from "./Partials/AddWorkspaceMemberDialog";
import WorkspaceMemberCard from "./Partials/WorkspaceMemberCard";

export default function Member({
    workspaceId,
    limit,
    totalMembers,
    members,
    isUserAdmin,
    isUserOwner,
}: PageProps<{
    workspaceId: string;
    limit: number;
    totalMembers: number;
    members: WorkspaceMember[];
    isUserAdmin: boolean;
    isUserOwner: boolean;
}>) {
    const offsetFromQuery = route().queryParams.offset;
    const parsedOffset =
        typeof offsetFromQuery === "string" ? parseInt(offsetFromQuery) : 0;
    const [offset, setOffset] = useState(parsedOffset);

    const [openAdd, setOpenAdd] = useState(false);
    const [processing, setProcessing] = useState(false);

    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Workspace Settings", path: "workspace.edit" },
        { label: "Members", path: "workspace.edit.member" },
    ].map((item) => ({
        ...item,
        param: workspaceId,
    }));

    const getStatus = (member: WorkspaceMember) => {
        if (member.id === null) {
            return "invited";
        }
        if (!member.is_verified) {
            return "unverified";
        }
        return "active";
    };

    const movePage = (ref: 1 | -1) => {
        const newOffset = offset + ref * limit;
        setOffset(newOffset);
        router.get(
            route("workspace.edit.member", {
                workspace_id: workspaceId,
                offset: newOffset,
            })
        );
    };

    const handleRoleChange = (member: WorkspaceMember, role: string) => {
        router.patch(
            route("workspace.update.member", workspaceId),
            {
                role: role,
                user_id: member.id,
                user_email: member.email,
            },
            {
                preserveScroll: true,
                onStart: () => setProcessing(true),
                onFinish: () => setProcessing(false),
            }
        );
    };

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Members" />

            <Card className="w-full h-full ">
                <CardHeader>
                    <CardTitle className="text-2xl">Manage Members</CardTitle>
                </CardHeader>
                <Separator className="mx-6" style={{ width: "auto" }} />
                <CardContent>
                    <div className="flex flex-col gap-4">
                        <div className="flex items-center justify-between">
                            <h2 className="font-semibold">Team Members</h2>
                            {(isUserAdmin || isUserOwner) && (
                                <Button onClick={() => setOpenAdd(true)}>
                                    <CirclePlus />
                                    Invite Members
                                </Button>
                            )}
                        </div>
                        <div className="flex flex-col gap-1">
                            {members.map((member) => (
                                <WorkspaceMemberCard
                                    key={member.id}
                                    workspaceId={workspaceId}
                                    userId={member.id}
                                    name={member.name}
                                    email={member.email}
                                    status={getStatus(member)}
                                    role={member.role}
                                    onRoleChange={(role) =>
                                        handleRoleChange(member, role)
                                    }
                                    disabled={
                                        processing ||
                                        !isUserOwner ||
                                        member.role === "owner"
                                    }
                                />
                            ))}
                        </div>
                        <div className="flex items-center justify-between mt-2">
                            <div className="text-sm text-muted-foreground">
                                {`Showing ${offset + 1} to ${
                                    offset + members.length
                                } of ${totalMembers} members`}
                            </div>
                            <div className="flex items-center gap-2">
                                <Button
                                    variant="outline"
                                    onClick={() => movePage(-1)}
                                    disabled={offset === 0}
                                >
                                    Previous
                                </Button>
                                <Button
                                    onClick={() => movePage(1)}
                                    disabled={
                                        offset + members.length >= totalMembers
                                    }
                                >
                                    Next
                                </Button>
                            </div>
                        </div>
                    </div>
                    <AddWorkspaceMemberDialog
                        open={openAdd}
                        onOpenChange={setOpenAdd}
                        workspaceId={workspaceId}
                        isUserOwner={isUserOwner}
                    />
                </CardContent>
            </Card>
        </AuthenticatedLayout>
    );
}

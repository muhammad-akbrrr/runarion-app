import { Label } from "@/Components/ui/label";
import { WorkspaceMember } from "@/types/workspace";
import { useState } from "react";
import RemoveWorkspaceMemberButton from "./RemoveWorkspaceMemberButton";
import UpdateWorkspaceMemberButton from "./UpdateWorkspaceMemberButton";
import WorkspaceMemberCard from "./WorkspaceMemberCard";

export default function ManageWorkspaceMemberSection({
    userId,
    workspaceId,
    workspaceMembers,
    isUserOwner,
    isUserAdmin,
    className = "",
}: {
    userId: number;
    workspaceId: number;
    workspaceMembers: WorkspaceMember[];
    isUserOwner: boolean;
    isUserAdmin: boolean;
    className?: string;
}) {
    const [selectedAdmins, setSelectedAdmins] = useState<(number | string)[]>(
        []
    );
    const [selectedMembers, setSelectedMembers] = useState<(number | string)[]>(
        []
    );

    const handleSelect = (
        checked: boolean,
        item: WorkspaceMember,
        setter: React.Dispatch<React.SetStateAction<(number | string)[]>>
    ) => {
        if (checked) {
            setter((prev) => [
                ...prev,
                item.id === null ? item.email : item.id,
            ]);
        } else {
            setter((prev) =>
                prev.filter((e) => e !== item.id && e !== item.email)
            );
        }
    };

    const sortByName = (a: WorkspaceMember, b: WorkspaceMember) => {
        if (a.name === null) {
            return 1;
        }
        if (b.name === null) {
            return -1;
        }
        if (a.name > b.name) {
            return 1;
        }
        return -1;
    };

    const owner = workspaceMembers.find((member) => member.role === "owner");
    const admins = workspaceMembers
        .filter((member) => member.role === "admin")
        .sort(sortByName);
    const members = workspaceMembers
        .filter((member) => member.role === "member")
        .sort(sortByName);

    return (
        <section className={className}>
            <header>
                <h2 className="text-lg font-medium text-foreground">
                    Workspace Members
                </h2>
            </header>

            <form className="mt-6 space-y-6">
                <div className="space-y-2">
                    <Label>Owner</Label>
                    {owner && (
                        <WorkspaceMemberCard
                            member={owner}
                            isSelf={owner.id === userId}
                            isUserOwner={isUserOwner}
                            isUserAdmin={isUserAdmin}
                        />
                    )}
                </div>
                <div className="space-y-2">
                    <Label>Admin Members</Label>
                    <div className="flex flex-wrap gap-2 w-[60rem]">
                        {admins.map((admin) => (
                            <WorkspaceMemberCard
                                key={admin.email}
                                member={admin}
                                isSelf={admin.id === userId}
                                isUserOwner={isUserOwner}
                                isUserAdmin={isUserAdmin}
                                checked={selectedAdmins.includes(
                                    admin.id === null ? admin.email : admin.id
                                )}
                                onCheckedChange={(checked) =>
                                    handleSelect(
                                        checked,
                                        admin,
                                        setSelectedAdmins
                                    )
                                }
                            />
                        ))}
                    </div>
                    {isUserOwner && (
                        <div className="flex gap-2">
                            <RemoveWorkspaceMemberButton
                                workspaceId={workspaceId}
                                role="admin"
                                selected={selectedAdmins}
                                onSuccess={() => setSelectedAdmins([])}
                            />
                            <UpdateWorkspaceMemberButton
                                workspaceId={workspaceId}
                                action="demote"
                                selected={selectedAdmins}
                                onSuccess={() => setSelectedAdmins([])}
                            />
                        </div>
                    )}
                </div>
                <div className="space-y-2">
                    <Label>Regular Members</Label>
                    <div className="flex flex-wrap gap-2 w-[60rem]">
                        {members.map((member) => (
                            <WorkspaceMemberCard
                                key={member.email}
                                member={member}
                                isSelf={member.id === userId}
                                isUserOwner={isUserOwner}
                                isUserAdmin={isUserAdmin}
                                checked={selectedMembers.includes(
                                    member.id === null
                                        ? member.email
                                        : member.id
                                )}
                                onCheckedChange={(checked) =>
                                    handleSelect(
                                        checked,
                                        member,
                                        setSelectedMembers
                                    )
                                }
                            />
                        ))}
                    </div>
                    {(isUserAdmin || isUserOwner) && (
                        <div className="flex gap-2">
                            <RemoveWorkspaceMemberButton
                                workspaceId={workspaceId}
                                role="member"
                                selected={selectedMembers}
                                onSuccess={() => setSelectedMembers([])}
                            />
                            <UpdateWorkspaceMemberButton
                                workspaceId={workspaceId}
                                action="promote"
                                selected={selectedMembers}
                                onSuccess={() => setSelectedMembers([])}
                            />
                        </div>
                    )}
                </div>
            </form>
        </section>
    );
}

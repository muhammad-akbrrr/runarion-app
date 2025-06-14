import { Button } from "@/Components/ui/button";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/Components/ui/select";
import { Project, ProjectRole } from "@/types";

interface ProjectMemberItemProps {
    member: NonNullable<Project["access"]>[number];
    project: Project;
    isAdmin: boolean;
    isManager: boolean;
    isOriginalAuthor: boolean;
    isCurrentUser: (userId: string) => boolean;
    canRemoveMember: (
        member: NonNullable<Project["access"]>[number]
    ) => boolean;
    isRemoving: boolean;
    onRoleChange: (userId: string, newRole: ProjectRole) => void;
    onRemoveClick: (member: NonNullable<Project["access"]>[number]) => void;
    projectRoles: ProjectRole[];
}

export default function ProjectMemberItem({
    member,
    project,
    isAdmin,
    isManager,
    isOriginalAuthor,
    isCurrentUser,
    canRemoveMember,
    isRemoving,
    onRoleChange,
    onRemoveClick,
    projectRoles,
}: ProjectMemberItemProps) {
    return (
        <div className="flex items-center justify-between border-b py-2">
            <div>
                <p className="font-medium text-sm">{member.user.name}</p>
                <p className="text-sm text-gray-500">{member.user.email}</p>
            </div>
            <div className="flex items-center space-x-4">
                <Select
                    defaultValue={member.role}
                    disabled={(() => {
                        const isSelf = isCurrentUser(member.user.id);
                        const isMemberOriginalAuthor =
                            Number(member.user.id) === project.original_author;

                        // Original author can't change their own role
                        if (isOriginalAuthor && isSelf) {
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
                            if (member.role === "admin") {
                                return true;
                            }
                            return false;
                        }

                        // Admins can change anyone's role except original author
                        if (isAdmin) {
                            if (isMemberOriginalAuthor) {
                                return true;
                            }
                            return false;
                        }

                        return false;
                    })()}
                    onValueChange={(value: ProjectRole) => {
                        onRoleChange(member.user.id, value);
                    }}
                >
                    <SelectTrigger
                        size="default"
                        className="w-32 hover:cursor-pointer"
                    >
                        <SelectValue placeholder="Select a role">
                            {member.role.charAt(0).toUpperCase() +
                                member.role.slice(1)}
                        </SelectValue>
                    </SelectTrigger>
                    <SelectContent position="popper">
                        {projectRoles
                            .filter((role) => {
                                // If current user is manager, only show editor and manager roles
                                if (isManager && !isAdmin) {
                                    return (
                                        role === "editor" || role === "manager"
                                    );
                                }
                                // If current user is admin, show all roles
                                if (isAdmin) {
                                    return true;
                                }
                                // For editors, no roles should be shown (handled by disabled state)
                                return false;
                            })
                            .map((role) => (
                                <SelectItem key={role} value={role}>
                                    {role.charAt(0).toUpperCase() +
                                        role.slice(1)}
                                </SelectItem>
                            ))}
                    </SelectContent>
                </Select>
                {(isAdmin || isManager) && (
                    <Button
                        variant="destructive"
                        size="sm"
                        disabled={!canRemoveMember(member) || isRemoving}
                        onClick={() => onRemoveClick(member)}
                    >
                        Remove
                    </Button>
                )}
            </div>
        </div>
    );
}

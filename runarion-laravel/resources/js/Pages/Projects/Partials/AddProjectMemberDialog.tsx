import { Button } from "@/Components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";
import { ScrollArea } from "@/Components/ui/scroll-area";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/Components/ui/select";
import { Project, ProjectRole, User } from "@/types";
import { useState } from "react";
import { router } from "@inertiajs/react";

interface AddProjectMemberDialogProps {
    isOpen: boolean;
    onClose: () => void;
    workspaceMembers: User[];
    project: Project;
    workspaceId: string;
    projectId: string;
}

const PROJECT_ROLES: ProjectRole[] = ["editor", "manager", "admin"];

export default function AddProjectMemberDialog({
    isOpen,
    onClose,
    workspaceMembers,
    project,
    workspaceId,
    projectId,
}: AddProjectMemberDialogProps) {
    const [selectedRoles, setSelectedRoles] = useState<
        Record<string, ProjectRole>
    >({});
    const [isProcessing, setIsProcessing] = useState(false);

    const availableMembers = workspaceMembers.filter((member) => {
        return !project.access?.some(
            (access) => String(access.user.id) === String(member.id)
        );
    });

    const handleRoleChange = (memberId: string, role: ProjectRole) => {
        setSelectedRoles((prev) => ({
            ...prev,
            [memberId]: role,
        }));
    };

    const handleConfirm = () => {
        setIsProcessing(true);

        // Convert selectedRoles to array of {user_id, role} objects
        const membersToAdd = Object.entries(selectedRoles).map(
            ([userId, role]) => ({
                user_id: userId,
                role,
            })
        );

        router.post(
            route("workspace.projects.add.members", {
                workspace_id: workspaceId,
                project_id: projectId,
            }),
            {
                members: membersToAdd,
            },
            {
                onSuccess: () => {
                    setIsProcessing(false);
                    onClose();
                },
                onError: () => {
                    setIsProcessing(false);
                },
            }
        );
    };

    const handleClose = () => {
        setSelectedRoles({});
        onClose();
    };

    const selectedCount = Object.keys(selectedRoles).length;

    return (
        <Dialog open={isOpen} onOpenChange={handleClose}>
            <DialogContent className="lg:min-w-xl">
                <DialogHeader>
                    <DialogTitle>Add Project Members</DialogTitle>
                    <DialogDescription>
                        Select members from your workspace to add to this
                        project.
                    </DialogDescription>
                </DialogHeader>

                <ScrollArea className="h-[350px]">
                    <div className="flex flex-col gap-2">
                        {availableMembers.map((member) => (
                            <div
                                key={member.id}
                                className="flex items-center justify-between p-2 border rounded-lg"
                            >
                                <div>
                                    <p className="font-medium text-sm">
                                        {member.name}
                                    </p>
                                    <p className="text-sm text-gray-500">
                                        {member.email}
                                    </p>
                                </div>
                                <Select
                                    value={selectedRoles[member.id]}
                                    onValueChange={(value: ProjectRole) =>
                                        handleRoleChange(member.id, value)
                                    }
                                >
                                    <SelectTrigger className="w-32">
                                        <SelectValue placeholder="Select one..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {PROJECT_ROLES.map((role) => (
                                            <SelectItem key={role} value={role}>
                                                {role.charAt(0).toUpperCase() +
                                                    role.slice(1)}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        ))}
                    </div>
                </ScrollArea>

                <DialogFooter className="flex flex-row items-center !justify-between">
                    <p className="text-sm text-muted-foreground">
                        {selectedCount} of {availableMembers.length} Selected
                    </p>
                    <div className="flex items-center gap-2">
                        <Button variant="outline" onClick={handleClose}>
                            Cancel
                        </Button>
                        <Button
                            onClick={handleConfirm}
                            disabled={selectedCount === 0 || isProcessing}
                        >
                            {isProcessing ? "Adding..." : "Confirm"}
                        </Button>
                    </div>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

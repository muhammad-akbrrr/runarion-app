import { Button } from "@/Components/ui/button";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/Components/ui/select";
import { useState } from "react";
import RemoveWorkspaceMemberDialog from "./RemoveWorkspaceMemberDialog";

export default function WorkspaceMemberCard({
    workspaceId,
    userId,
    name,
    email,
    status,
    role,
    onRoleChange,
    disabled = false,
}: {
    workspaceId: string;
    userId: number | null;
    name: string | null;
    email: string;
    status: "active" | "invited" | "unverified" | "suspended";
    role: "owner" | "admin" | "member";
    onRoleChange: (newRole: "owner" | "admin" | "member") => void;
    disabled?: boolean;
}) {
    const [openDialog, setOpenDialog] = useState(false);

    const statusTexts = {
        active: "Active",
        invited: "Invite Sent",
        unverified: "Unverified Email",
        suspended: "Suspended",
    };

    const statusStyles = {
        active: "bg-green-100 text-green-600",
        invited: "bg-blue-100 text-blue-600",
        unverified: "bg-yellow-100 text-yellow-600",
        suspended: "bg-red-100 text-red-600",
    };

    return (
        <div className="flex items-center justify-between border-b py-2">
            <div>
                <p
                    className="font-medium text-sm"
                    style={name === null ? { fontStyle: "italic" } : {}}
                >
                    {name ?? "Unknown"}
                </p>
                <p className="text-sm text-gray-500">{email}</p>
            </div>
            <div className="flex items-center space-x-4">
                <span
                    className={`text-sm font-medium px-2 py-1 rounded ${statusStyles[status]}`}
                >
                    {statusTexts[status]}
                </span>
                <Select
                    value={role}
                    onValueChange={onRoleChange}
                    disabled={disabled}
                >
                    <SelectTrigger
                        size="default"
                        className="w-32 hover:cursor-pointer"
                    >
                        <SelectValue placeholder="Select a role" />
                    </SelectTrigger>
                    <SelectContent position="popper">
                        {role === "owner" ? (
                            <SelectItem value="owner">Owner</SelectItem>
                        ) : (
                            <>
                                <SelectItem value="admin">Admin</SelectItem>
                                <SelectItem value="member">Member</SelectItem>
                            </>
                        )}
                    </SelectContent>
                </Select>
                <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => setOpenDialog(true)}
                    disabled={disabled}
                >
                    Remove
                </Button>
                {/* <DropdownMenu>
                    <DropdownMenuTrigger className="hover:bg-gray-200 rounded-full p-0.5 cursor-pointer">
                        <Ellipsis />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                        <DropdownMenuItem>Remove</DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu> */}
            </div>
            <RemoveWorkspaceMemberDialog
                open={openDialog}
                onOpenChange={setOpenDialog}
                workspaceId={workspaceId}
                selected={userId ?? email}
            />
        </div>
    );
}

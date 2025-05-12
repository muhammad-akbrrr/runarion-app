import { Button } from "@/Components/ui/button";
import { router } from "@inertiajs/react";
import { useState } from "react";

export default function UpdateWorkspaceMemberButton({
    workspaceId,
    action,
    selected,
    onSuccess,
}: {
    workspaceId: number;
    action: "promote" | "demote";
    selected: (string | number)[];
    onSuccess: () => void;
}) {
    const [processing, setProcessing] = useState(false);

    const ids = selected.filter((item) => typeof item === "number");
    const disabled =
        selected.length === 0 ||
        processing ||
        selected.filter((item) => typeof item === "string").length > 0;

    const handleRemove = () =>
        router.patch(
            route("workspace-members.update", workspaceId),
            {
                workspace_id: workspaceId,
                role: action === "promote" ? "admin" : "member",
                user_ids: ids,
            },
            {
                preserveScroll: true,
                onSuccess: onSuccess,
                onStart: () => setProcessing(true),
                onFinish: () => setProcessing(false),
            }
        );

    return (
        <Button
            onClick={handleRemove}
            disabled={disabled}
            size="sm"
            type="button"
        >
            {action === "promote" ? "Promote to Admin" : "Demote to Member"}
        </Button>
    );
}

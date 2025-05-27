import { Button } from "@/Components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";
import { router } from "@inertiajs/react";
import { useState } from "react";

export default function RemoveWorkspaceMemberDialog({
    open,
    onOpenChange,
    workspaceId,
    selected,
}: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    workspaceId: number;
    selected: string | number;
}) {
    const [processing, setProcessing] = useState(false);

    const handleRemove = () =>
        router.delete(route("workspace-member.remove"), {
            data: {
                workspace_id: workspaceId,
                user_id: typeof selected === "number" ? selected : null,
                user_email: typeof selected === "string" ? selected : null,
            },
            preserveScroll: true,
            onSuccess: () => onOpenChange(false),
            onStart: () => setProcessing(true),
            onFinish: () => setProcessing(false),
        });

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Remove Workspace Members</DialogTitle>
                    <DialogDescription>
                        Are you sure you want to remove this member from this
                        workspace?
                    </DialogDescription>
                </DialogHeader>

                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                    >
                        Cancel
                    </Button>
                    <Button
                        variant="destructive"
                        disabled={processing}
                        onClick={handleRemove}
                    >
                        Yes
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

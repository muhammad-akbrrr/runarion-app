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

export default function LeaveWorkspaceDialog({
    workspaceId,
    open,
    onOpenChange,
}: {
    workspaceId: number;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}) {
    const [processing, setProcessing] = useState(false);

    const handleLeave = () =>
        router.delete(route("workspace-member.leave", workspaceId), {
            preserveScroll: true,
            onSuccess: () => onOpenChange(false),
            onStart: () => setProcessing(true),
            onFinish: () => setProcessing(false),
        });

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Leave Workspace</DialogTitle>
                    <DialogDescription>
                        Are you sure you want to leave this workspace?
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
                        onClick={handleLeave}
                    >
                        Yes
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

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

export default function DeleteWorkspaceDialog({
    workspaceId,
    open,
    onOpenChange,
}: {
    workspaceId: string;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}) {
    const [processing, setProcessing] = useState(false);

    const handleDelete = () =>
        router.delete(route("workspace.destroy", workspaceId), {
            preserveScroll: true,
            onSuccess: () => onOpenChange(false),
            onStart: () => setProcessing(true),
            onFinish: () => setProcessing(false),
        });

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Delete Workspace</DialogTitle>
                    <DialogDescription>
                        Are you sure you want to delete this workspace?
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
                        onClick={handleDelete}
                    >
                        Yes
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

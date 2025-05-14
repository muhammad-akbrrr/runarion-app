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

export default function LeaveWorkspaceSection({
    workspaceId,
    className = "",
}: {
    workspaceId: number;
    className?: string;
}) {
    const [openDialog, setOpenDialog] = useState(false);
    const [processing, setProcessing] = useState(false);

    const handleLeave = () =>
        router.delete(route("workspace-members.leave", workspaceId), {
            preserveScroll: true,
            onSuccess: () => setOpenDialog(false),
            onStart: () => setProcessing(true),
            onFinish: () => setProcessing(false),
        });

    return (
        <section className={`space-y-6 ${className}`}>
            <header>
                <h2 className="text-lg font-medium text-foreground">
                    Leave Workspace
                </h2>
            </header>

            <Button variant="destructive" onClick={() => setOpenDialog(true)}>
                Leave Workspace
            </Button>

            <Dialog open={openDialog} onOpenChange={setOpenDialog}>
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
                            onClick={() => setOpenDialog(false)}
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
        </section>
    );
}

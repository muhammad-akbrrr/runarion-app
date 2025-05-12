import { Button } from "@/Components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";
import { Workspace } from "@/types/workspace";
import { router } from "@inertiajs/react";
import { useState } from "react";

export default function DeleteWorkspaceSection({
    workspace,
    className = "",
}: {
    workspace: Workspace;
    className?: string;
}) {
    const [openDialog, setOpenDialog] = useState(false);
    const [processing, setProcessing] = useState(false);

    const handleDelete = () =>
        router.delete(route("workspaces.destroy", workspace.id), {
            preserveScroll: true,
            onSuccess: () => setOpenDialog(false),
            onStart: () => setProcessing(true),
            onFinish: () => setProcessing(false),
        });

    return (
        <section className={`space-y-6 ${className}`}>
            <header>
                <h2 className="text-lg font-medium text-foreground">
                    Delete Workspace
                </h2>
            </header>

            <Button variant="destructive" onClick={() => setOpenDialog(true)}>
                Delete Workspace
            </Button>

            <Dialog open={openDialog} onOpenChange={setOpenDialog}>
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
                            onClick={() => setOpenDialog(false)}
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
        </section>
    );
}

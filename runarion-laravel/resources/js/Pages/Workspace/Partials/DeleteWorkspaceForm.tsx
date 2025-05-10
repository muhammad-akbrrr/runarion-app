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
import { useForm } from "@inertiajs/react";
import { FormEventHandler, useState } from "react";

export default function DeleteWorkspaceForm({
    workspace,
    className = "",
}: {
    workspace: Workspace;
    className?: string;
}) {
    const [openDialog, setOpenDialog] = useState(false);

    const { delete: destroy, processing } = useForm();

    const handleDelete: FormEventHandler = (e) => {
        e.preventDefault();

        destroy(route("workspaces.destroy", workspace.id), {
            preserveScroll: true,
            onSuccess: () => setOpenDialog(false),
        });
    };

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

                    <form onSubmit={handleDelete} className="space-y-4">
                        <DialogFooter>
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => setOpenDialog(false)}
                            >
                                Cancel
                            </Button>
                            <Button
                                type="submit"
                                variant="destructive"
                                disabled={processing}
                            >
                                Yes
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </section>
    );
}

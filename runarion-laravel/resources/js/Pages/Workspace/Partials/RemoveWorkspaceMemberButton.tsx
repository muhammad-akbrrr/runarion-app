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

export default function RemoveWorkspaceMemberButton({
    workspaceId,
    role,
    selected,
    onSuccess,
}: {
    workspaceId: number;
    role: string;
    selected: (string | number)[];
    onSuccess: () => void;
}) {
    const [open, setOpen] = useState(false);
    const [processing, setProcessing] = useState(false);

    const ids = selected.filter((item) => typeof item === "number");
    const emails = selected.filter((item) => typeof item === "string");

    const handleRemove = () =>
        router.delete(route("workspace-members.remove"), {
            data: {
                workspace_id: workspaceId,
                role: role,
                user_ids: ids,
                user_emails: emails,
            },
            preserveScroll: true,
            onSuccess: () => {
                setOpen(false);
                onSuccess();
            },
            onStart: () => setProcessing(true),
            onFinish: () => setProcessing(false),
        });

    return (
        <>
            <Button
                type="button"
                variant="destructive"
                onClick={() => setOpen(true)}
                size="sm"
                disabled={selected.length === 0}
            >
                Remove
            </Button>

            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Remove Workspace Members</DialogTitle>
                        <DialogDescription>
                            Are you sure you want to remove these members from
                            this workspace?
                        </DialogDescription>
                    </DialogHeader>

                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setOpen(false)}
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
        </>
    );
}

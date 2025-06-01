import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/Components/ui/dialog";
import { Input } from "@/Components/ui/input";
import { Button } from "@/Components/ui/button";
import React from "react";

interface DeleteProjectDialogProps {
    open: boolean;
    setOpen: (open: boolean) => void;
    projectName: string;
    confirmationInput: string;
    setConfirmationInput: (value: string) => void;
    loading: boolean;
    handleDelete: () => void;
}

const DeleteProjectDialog: React.FC<DeleteProjectDialogProps> = ({
    open,
    setOpen,
    projectName,
    confirmationInput,
    setConfirmationInput,
    loading,
    handleDelete,
}) => (
    <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
            <DialogHeader>
                <DialogTitle>Delete Project</DialogTitle>
                <DialogDescription>
                    This action cannot be undone. Please type{" "}
                    <b>{projectName}</b> to confirm deletion.
                </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-4">
                <Input
                    type="text"
                    placeholder="Type project name to confirm"
                    value={confirmationInput}
                    onChange={(e) => setConfirmationInput(e.target.value)}
                    autoFocus
                />
                <DialogFooter className="flex flex-row gap-2 justify-end">
                    <Button
                        variant="secondary"
                        type="button"
                        onClick={() => setOpen(false)}
                        disabled={loading}
                    >
                        Cancel
                    </Button>
                    <Button
                        variant="destructive"
                        type="button"
                        disabled={confirmationInput !== projectName || loading}
                        onClick={handleDelete}
                    >
                        Delete
                    </Button>
                </DialogFooter>
            </div>
        </DialogContent>
    </Dialog>
);

export default DeleteProjectDialog;

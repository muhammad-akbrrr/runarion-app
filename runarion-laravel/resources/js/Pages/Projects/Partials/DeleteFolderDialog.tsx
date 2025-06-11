import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/Components/ui/dialog";
import { Button } from "@/Components/ui/button";
import React from "react";

interface DeleteFolderDialogProps {
    open: boolean;
    setOpen: (open: boolean) => void;
    loading: boolean;
    handleDelete: () => void;
}

const DeleteFolderDialog: React.FC<DeleteFolderDialogProps> = ({
    open,
    setOpen,
    loading,
    handleDelete,
}) => (
    <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
            <DialogHeader>
                <DialogTitle>Delete Folder</DialogTitle>
                <DialogDescription>
                    Deleting this folder will move all projects inside it to the
                    root of the workspace. Are you sure you want to continue?
                </DialogDescription>
            </DialogHeader>
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
                    disabled={loading}
                    onClick={handleDelete}
                >
                    Delete
                </Button>
            </DialogFooter>
        </DialogContent>
    </Dialog>
);

export default DeleteFolderDialog;

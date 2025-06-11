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

interface AddFolderDialogProps {
    open: boolean;
    setOpen: (open: boolean) => void;
    folderName: string;
    setFolderName: (name: string) => void;
    loading: boolean;
    handleAddFolder: () => void;
}

const AddFolderDialog: React.FC<AddFolderDialogProps> = ({
    open,
    setOpen,
    folderName,
    setFolderName,
    loading,
    handleAddFolder,
}) => (
    <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
            <DialogHeader>
                <DialogTitle>Add Folder</DialogTitle>
                <DialogDescription>
                    Enter a name for your new folder.
                </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-4">
                <Input
                    type="text"
                    placeholder="Folder name"
                    value={folderName}
                    onChange={(e) => setFolderName(e.target.value)}
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
                        variant="default"
                        type="button"
                        disabled={!folderName.trim() || loading}
                        onClick={handleAddFolder}
                    >
                        Add
                    </Button>
                </DialogFooter>
            </div>
        </DialogContent>
    </Dialog>
);

export default AddFolderDialog;

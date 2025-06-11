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

interface AddProjectDialogProps {
    open: boolean;
    setOpen: (open: boolean) => void;
    projectName: string;
    setProjectName: (name: string) => void;
    loading: boolean;
    handleAddProject: () => void;
}

const AddProjectDialog: React.FC<AddProjectDialogProps> = ({
    open,
    setOpen,
    projectName,
    setProjectName,
    loading,
    handleAddProject,
}) => (
    <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
            <DialogHeader>
                <DialogTitle>New Project</DialogTitle>
                <DialogDescription>
                    Enter a name for your new project.
                </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-4">
                <Input
                    type="text"
                    placeholder="Project name"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
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
                        disabled={!projectName.trim() || loading}
                        onClick={handleAddProject}
                    >
                        Create
                    </Button>
                </DialogFooter>
            </div>
        </DialogContent>
    </Dialog>
);

export default AddProjectDialog;

import React from "react";
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

interface DeleteProjectDialogProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  projectName: string;
  isMultiple: boolean;
  confirmationInput: string;
  setConfirmationInput: (value: string) => void;
  loading: boolean;
  handleDelete: () => void;
  selectedCount?: number;
}

const DeleteProjectDialog: React.FC<DeleteProjectDialogProps> = ({
  open,
  setOpen,
  projectName,
  isMultiple,
  confirmationInput,
  setConfirmationInput,
  loading,
  handleDelete,
  selectedCount = 0,
}) => {
  const confirmationText = isMultiple ? "I WANNA DELETE THE SELECTED PROJECTS" : projectName;
  
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete {isMultiple ? "Projects" : "Project"}</DialogTitle>
          <DialogDescription>
            {isMultiple 
              ? <>This action cannot be undone. Please type <b>I WANNA DELETE THE SELECTED PROJECTS</b> to confirm deletion of {selectedCount} projects.</>
              : <>This action cannot be undone. Please type <b>{projectName}</b> to confirm deletion.</>
            }
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <Input
            type="text"
            placeholder={isMultiple 
              ? "Type I WANNA DELETE THE SELECTED PROJECTS to confirm" 
              : `Type ${projectName} to confirm`}
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
              disabled={confirmationInput !== confirmationText || loading}
              onClick={handleDelete}
            >
              Delete
            </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default DeleteProjectDialog;

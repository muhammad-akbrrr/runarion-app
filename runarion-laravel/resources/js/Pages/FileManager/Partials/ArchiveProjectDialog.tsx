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

interface ArchiveProjectDialogProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  projectName?: string;
  isMultiple: boolean;
  confirmationInput: string;
  setConfirmationInput: (value: string) => void;
  loading: boolean;
  handleArchive: () => void;
  selectedCount?: number;
}

const ArchiveProjectDialog: React.FC<ArchiveProjectDialogProps> = ({
  open,
  setOpen,
  projectName,
  isMultiple,
  confirmationInput,
  setConfirmationInput,
  loading,
  handleArchive,
  selectedCount = 0,
}) => (
  <Dialog open={open} onOpenChange={setOpen}>
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Archive {isMultiple ? "Projects" : "Project"}</DialogTitle>
        <DialogDescription>
          {isMultiple 
            ? `You are about to archive ${selectedCount} projects. This action can be undone later.`
            : `You are about to archive "${projectName}". This action can be undone later.`}
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
            disabled={
              (isMultiple && confirmationInput !== "I WANNA DELETE THE SELECTED PROJECTS") || 
              (!isMultiple && confirmationInput !== projectName) || 
              loading
            }
            onClick={handleArchive}
          >
            Archive
          </Button>
        </DialogFooter>
      </div>
    </DialogContent>
  </Dialog>
);

export default ArchiveProjectDialog;

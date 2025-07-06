import React from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/Components/ui/dialog";
import { Input } from "@/Components/ui/input";
import { Button } from "@/Components/ui/button";

interface AddAuthorStyleDialogProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  onSubmit: () => void;
}

export default function AddAuthorStyleDialog({ 
  open, 
  setOpen, 
  onSubmit 
}: AddAuthorStyleDialogProps) {
  const [authorName, setAuthorName] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  const handleSubmit = () => {
    if (!authorName.trim()) return;
    setLoading(true);
    
    // Here you would typically make an API call to create the author style
    // For now, we'll just simulate it with a timeout
    setTimeout(() => {
      onSubmit();
      setLoading(false);
      setAuthorName("");
      setOpen(false);
    }, 500);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Author Style</DialogTitle>
          <DialogDescription>
            Create a new author style for your projects.
          </DialogDescription>
        </DialogHeader>
        <div className="py-4">
          <Input
            placeholder="Author name"
            value={authorName}
            onChange={(e) => setAuthorName(e.target.value)}
            className="mb-4"
            autoFocus
          />
        </div>
        <DialogFooter>
          <Button 
            variant="outline" 
            onClick={() => setOpen(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button 
            onClick={handleSubmit}
            disabled={!authorName.trim() || loading}
          >
            {loading ? "Creating..." : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

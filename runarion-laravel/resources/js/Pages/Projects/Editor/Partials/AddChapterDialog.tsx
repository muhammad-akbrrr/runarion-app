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

interface AddChapterDialogProps {
    open: boolean;
    setOpen: (open: boolean) => void;
    chapterName: string;
    setChapterName: (name: string) => void;
    loading: boolean;
    handleAddChapter: () => void;
}

const AddChapterDialog: React.FC<AddChapterDialogProps> = ({
    open,
    setOpen,
    chapterName,
    setChapterName,
    loading,
    handleAddChapter,
}) => (
    <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
            <DialogHeader>
                <DialogTitle>Add Chapter</DialogTitle>
                <DialogDescription>
                    Enter a name for your new chapter.
                </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-4">
                <Input
                    type="text"
                    placeholder="Chapter name"
                    value={chapterName}
                    onChange={(e) => setChapterName(e.target.value)}
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
                        disabled={!chapterName.trim() || loading}
                        onClick={handleAddChapter}
                    >
                        Add
                    </Button>
                </DialogFooter>
            </div>
        </DialogContent>
    </Dialog>
);

export default AddChapterDialog;

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
import { AlertCircle } from "lucide-react";
import React from "react";
import { MagicWandButton } from "@/Components/MagicWandButton";

interface AddChapterDialogProps {
    open: boolean;
    setOpen: (open: boolean) => void;
    chapterName: string;
    setChapterName: (name: string) => void;
    loading: boolean;
    handleAddChapter: () => void;
    existingChapterNames?: string[];
    error?: string;
    workspaceId?: string;
    projectId?: string;
}

const AddChapterDialog: React.FC<AddChapterDialogProps> = ({
    open,
    setOpen,
    chapterName,
    setChapterName,
    loading,
    handleAddChapter,
    existingChapterNames = [],
    error,
    workspaceId,
    projectId,
}) => {
    // Check for duplicate name (case-insensitive, trimmed)
    const normalizedInput = chapterName.trim().toLowerCase();
    const isDuplicate = existingChapterNames.some(
        name => name.trim().toLowerCase() === normalizedInput
    );
    const showDuplicateError = isDuplicate && chapterName.trim().length > 0;

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>Add Chapter</DialogTitle>
                    <DialogDescription>
                        Enter a name for your new chapter.
                    </DialogDescription>
                </DialogHeader>
                <div className="flex flex-col gap-4">
                    <div className="flex flex-col gap-2">
                        <div className="flex gap-2">
                            <Input
                                type="text"
                                placeholder="Chapter name"
                                value={chapterName}
                                onChange={(e) => setChapterName(e.target.value)}
                                autoFocus
                                className={`flex-1 ${showDuplicateError || error ? "border-red-500" : ""}`}
                            />
                            {workspaceId && projectId && (
                                <MagicWandButton
                                    text={chapterName}
                                    onEnhanced={(enhanced) => setChapterName(enhanced)}
                                    enhancementMode="chapter_name"
                                    workspaceId={workspaceId}
                                    projectId={projectId}
                                    disabled={loading}
                                    size="icon"
                                    variant="outline"
                                />
                            )}
                        </div>
                        {showDuplicateError && (
                            <div className="flex items-start gap-2 text-sm text-red-600">
                                <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                                <span>
                                    A chapter named "{existingChapterNames.find(
                                        name => name.trim().toLowerCase() === normalizedInput
                                    )}" already exists.
                                </span>
                            </div>
                        )}
                        {error && !showDuplicateError && (
                            <div className="flex items-start gap-2 text-sm text-red-600">
                                <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                                <span>{error}</span>
                            </div>
                        )}
                    </div>

                    {existingChapterNames.length > 0 && (
                        <div className="flex flex-col gap-2">
                            <p className="text-sm font-medium text-gray-700">
                                Existing chapters:
                            </p>
                            <div className="max-h-32 overflow-y-auto rounded-md border border-gray-200 bg-gray-50 p-2">
                                <ul className="space-y-1">
                                    {existingChapterNames.map((name, index) => (
                                        <li
                                            key={index}
                                            className="text-sm text-gray-600 px-2 py-1"
                                        >
                                            {name}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    )}

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
                            disabled={!chapterName.trim() || loading || showDuplicateError}
                            onClick={handleAddChapter}
                        >
                            Add
                        </Button>
                    </DialogFooter>
                </div>
            </DialogContent>
        </Dialog>
    );
};

export default AddChapterDialog;

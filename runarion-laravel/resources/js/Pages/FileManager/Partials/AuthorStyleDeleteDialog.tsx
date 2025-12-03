import * as React from "react";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/Components/ui/alert-dialog";
import { router } from "@inertiajs/react";
import { AuthorStyle } from "@/types/files";

interface AuthorStyleDeleteDialogProps {
    open: boolean;
    onClose: () => void;
    authorStyle: AuthorStyle | null;
    workspaceId: string;
}

export default function AuthorStyleDeleteDialog({
    open,
    onClose,
    authorStyle,
    workspaceId,
}: AuthorStyleDeleteDialogProps) {
    const [isDeleting, setIsDeleting] = React.useState(false);

    const handleDelete = () => {
        if (!authorStyle) return;
        
        setIsDeleting(true);

        router.delete(
            route("workspace.files.author-styles.delete", { 
                workspace_id: workspaceId, 
                author_style_id: authorStyle.id 
            }),
            {
                preserveScroll: true,
                onSuccess: () => {
                    setIsDeleting(false);
                    onClose();
                },
                onError: () => {
                    setIsDeleting(false);
                },
            }
        );
    };

    if (!authorStyle) return null;

    return (
        <AlertDialog open={open} onOpenChange={onClose}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>Delete Author Style</AlertDialogTitle>
                    <AlertDialogDescription>
                        Are you sure you want to delete the author style "{authorStyle.name}"? 
                        This action cannot be undone and will remove all associated data including 
                        techniques and examples.
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
                    <AlertDialogAction 
                        onClick={handleDelete}
                        disabled={isDeleting}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                        {isDeleting ? "Deleting..." : "Delete"}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}


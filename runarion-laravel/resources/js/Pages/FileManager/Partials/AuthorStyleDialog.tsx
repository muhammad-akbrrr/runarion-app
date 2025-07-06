import * as React from "react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";
import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { router } from "@inertiajs/react";
import { CloudUpload, X } from "lucide-react";
import { AuthorStyle } from "@/types/files";

interface AuthorStyleDialogProps {
    open: boolean;
    onClose: () => void;
    authorStyles: AuthorStyle[];
}

export default function AuthorStyleDialog({
    open,
    onClose,
    authorStyles,
}: AuthorStyleDialogProps) {
    const [isProcessing, setIsProcessing] = React.useState(false);
    const [authorName, setAuthorName] = React.useState("");
    const [authorFiles, setAuthorFiles] = React.useState<File[]>([]);
    const [authorNameTouched, setAuthorNameTouched] = React.useState(false);
    const [authorStyleError, setAuthorStyleError] = React.useState<string | null>(null);

    // Reset state on open/close
    React.useEffect(() => {
        if (!open) {
            setAuthorName("");
            setAuthorFiles([]);
            setIsProcessing(false);
            setAuthorNameTouched(false);
            setAuthorStyleError(null);
        }
    }, [open]);

    // File input handlers
    const handleAuthorFilesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            const files = Array.from(e.target.files).slice(0, 5);
            setAuthorFiles(files);
        }
    };

    // Form submission handler
    const handleSubmit = () => {
        if (authorFiles.length === 0) {
            setAuthorStyleError("Please upload at least one file.");
            return;
        }
        
        if (!authorName) {
            setAuthorStyleError("Please enter an author name.");
            return;
        }
        
        // Check for duplicate name
        const existingNames = authorStyles.map(style => style.name.toLowerCase());
        if (existingNames.includes(authorName.toLowerCase())) {
            setAuthorStyleError("An author with this name already exists.");
            return;
        }

        setIsProcessing(true);

        // Prepare form data for submission
        const formData = new FormData();
        formData.append("author_name", authorName);
        authorFiles.forEach((file, index) => {
            formData.append(`author_files[${index}]`, file);
        });

        // Here you would typically make an API call to create the author style
        setTimeout(() => {
            console.log("Creating author style:", {
                authorName,
                authorFiles,
            });
            
            // In a real implementation, you would use router.post to submit the form
            // router.post(route("workspace.files.author-styles.store"), formData, {
            //     forceFormData: true,
            //     onSuccess: () => {
            //         setIsProcessing(false);
            //         onClose();
            //     },
            //     onError: (errors) => {
            //         setIsProcessing(false);
            //         setAuthorStyleError(errors.message || "Failed to create author style.");
            //     },
            // });
            
            setIsProcessing(false);
            onClose();
        }, 1000);
    };

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-xl">
                <DialogHeader className="flex flex-row justify-center mb-2">
                    <DialogTitle>Create Author Style</DialogTitle>
                </DialogHeader>

                <div className="flex flex-col gap-4 mb-2 w-full">
                    <div className="flex flex-col justify-stretch items-start gap-2">
                        <div className="flex flex-col justify-start items-start gap-0.5">
                            <label className="text-sm">Upload Author Documents</label>
                            <p className="text-xs text-muted-foreground">
                                Upload documents that represent the author's writing style
                            </p>
                        </div>
                        
                        <div className="border-dashed border-2 rounded-lg p-6 flex flex-col items-center justify-center gap-1 text-center relative mb-2 w-full">
                            <Input
                                className="absolute left-0 top-0 w-full h-full opacity-0 cursor-pointer"
                                type="file"
                                accept=".pdf,.doc,.docx,.txt"
                                multiple
                                onChange={handleAuthorFilesChange}
                            />
                            <CloudUpload className="w-5 h-5 text-muted-foreground mb-2" />
                            <p className="font-semibold">
                                Click or drag to upload
                            </p>
                            <div className="w-4 h-0.5 bg-muted-foreground rounded-[1px]"></div>
                            <p className="text-muted-foreground text-xs">
                                Max file size: 100 MiB
                            </p>
                        </div>

                        <div className="flex flex-col justify-stretch items-start gap-2 w-full">
                            {authorFiles.map((file, idx) => (
                                <div
                                    key={idx}
                                    className="flex items-center justify-between bg-muted p-2 rounded-md w-full"
                                >
                                    <p className="text-xs">
                                        {file.name}
                                    </p>
                                    <Button
                                        className="!p-0 w-auto h-auto"
                                        variant="ghost"
                                        onClick={() =>
                                            setAuthorFiles(
                                                authorFiles.filter((_, i) => i !== idx)
                                            )
                                        }
                                    >
                                        <X className="h-3 w-3" />
                                    </Button>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="w-full h-[1px] bg-gray-200 rounded-[1px]"></div>

                    <div className="flex flex-col justify-stretch items-start gap-2">
                        <div className="flex flex-col justify-start items-start gap-0.5">
                            <label className="text-sm">Author Name</label>
                            <p className="text-xs text-muted-foreground">
                                Give your author style a unique name
                            </p>
                        </div>
                        <Input
                            className="w-full"
                            placeholder="Author name"
                            value={authorName}
                            onChange={(e) => {
                                setAuthorName(e.target.value);
                                setAuthorNameTouched(true);
                                setAuthorStyleError(null);
                            }}
                            onBlur={() => setAuthorNameTouched(true)}
                        />
                        {authorNameTouched && !authorName && (
                            <p className="text-xs text-destructive mt-1">
                                Author name is required.
                            </p>
                        )}
                    </div>
                </div>

                {authorStyleError && (
                    <p className="text-xs text-destructive mt-1">
                        {authorStyleError}
                    </p>
                )}

                <div className="flex flex-row items-center justify-between">
                    <Button variant="outline" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button
                        onClick={handleSubmit}
                        disabled={
                            isProcessing ||
                            authorFiles.length === 0 ||
                            !authorName
                        }
                    >
                        {isProcessing ? "Creating..." : "Create Author Style"}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}

import * as React from "react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";
import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { Checkbox } from "@/Components/ui/checkbox";
import { Label } from "@/Components/ui/label";
import { router, usePage } from "@inertiajs/react";
import { CloudUpload, X, Check } from "lucide-react";
import { AuthorStyle } from "@/types/files";
import { PageProps } from "@/types";

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
    const { projects, workspaceId } = usePage<PageProps<{ 
        projects: { id: string; name: string }[],
        workspaceId: string
    }>>().props;
    
    const [isProcessing, setIsProcessing] = React.useState(false);
    const [authorName, setAuthorName] = React.useState("");
    const [authorFiles, setAuthorFiles] = React.useState<File[]>([]);
    const [selectedProjectIds, setSelectedProjectIds] = React.useState<string[]>([]);
    const [applyToAll, setApplyToAll] = React.useState(false);
    const [authorNameTouched, setAuthorNameTouched] = React.useState(false);
    const [projectTouched, setProjectTouched] = React.useState(false);
    const [authorStyleError, setAuthorStyleError] = React.useState<string | null>(null);

    // Reset state on open/close
    React.useEffect(() => {
        if (!open) {
            setAuthorName("");
            setAuthorFiles([]);
            setSelectedProjectIds([]);
            setApplyToAll(false);
            setIsProcessing(false);
            setAuthorNameTouched(false);
            setProjectTouched(false);
            setAuthorStyleError(null);
        }
    }, [open]);

    // Handle apply to all toggle
    const handleApplyToAllChange = (checked: boolean) => {
        setApplyToAll(checked);
        if (checked && projects) {
            setSelectedProjectIds(projects.map(p => p.id));
        } else {
            setSelectedProjectIds([]);
        }
        setProjectTouched(true);
    };

    // Handle individual project toggle
    const handleProjectToggle = (projectId: string) => {
        setSelectedProjectIds(prev => {
            if (prev.includes(projectId)) {
                const newIds = prev.filter(id => id !== projectId);
                setApplyToAll(false);
                return newIds;
            } else {
                const newIds = [...prev, projectId];
                if (projects && newIds.length === projects.length) {
                    setApplyToAll(true);
                }
                return newIds;
            }
        });
        setProjectTouched(true);
    };

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
        
        if (selectedProjectIds.length === 0) {
            setAuthorStyleError("Please select at least one project.");
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
        // For now, send the first project ID (backend stores single project_id)
        // TODO: Update backend to support multiple projects via pivot table
        formData.append("project_id", selectedProjectIds[0]);
        authorFiles.forEach((file, index) => {
            formData.append(`author_files[${index}]`, file);
        });
        
        console.log("Creating author style:", {
            authorName,
            projectIds: selectedProjectIds,
            authorFiles,
        });
        
        // Submit the form to the backend
        router.post(route("workspace.files.author-styles.store", { workspace_id: workspaceId }), formData, {
            forceFormData: true,
            onSuccess: () => {
                setIsProcessing(false);
                onClose();
            },
            onError: (errors) => {
                setIsProcessing(false);
                if (errors.author_name) {
                    setAuthorStyleError(errors.author_name);
                } else if (errors.project_id) {
                    setAuthorStyleError(errors.project_id);
                } else if (errors.author_files) {
                    setAuthorStyleError(errors.author_files);
                } else {
                    setAuthorStyleError("An error occurred while creating the author style.");
                }
            },
        });
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

                    <div className="w-full h-[1px] bg-gray-200 rounded-[1px]"></div>

                    <div className="flex flex-col justify-stretch items-start gap-2">
                        <div className="flex flex-col justify-start items-start gap-0.5">
                            <label className="text-sm">Associated Projects</label>
                            <p className="text-xs text-muted-foreground">
                                Select projects where this author style can be used
                            </p>
                        </div>
                        
                        {/* Apply to All Checkbox */}
                        <div className="flex items-center space-x-2 py-2 px-3 bg-muted rounded-md w-full">
                            <Checkbox 
                                id="apply-to-all"
                                checked={applyToAll}
                                onCheckedChange={handleApplyToAllChange}
                            />
                            <Label 
                                htmlFor="apply-to-all" 
                                className="text-sm font-medium cursor-pointer"
                            >
                                Apply to all projects
                            </Label>
                        </div>
                        
                        {/* Project List */}
                        <div className="w-full border rounded-md max-h-[150px] overflow-y-auto">
                            {projects && projects.length > 0 ? (
                                projects.map((project) => (
                                    <div 
                                        key={project.id}
                                        className="flex items-center space-x-2 px-3 py-2 hover:bg-muted/50 cursor-pointer border-b last:border-b-0"
                                        onClick={() => handleProjectToggle(project.id)}
                                    >
                                        <Checkbox 
                                            checked={selectedProjectIds.includes(project.id)}
                                            onCheckedChange={() => handleProjectToggle(project.id)}
                                        />
                                        <span className="text-sm">{project.name}</span>
                                    </div>
                                ))
                            ) : (
                                <div className="px-3 py-2 text-sm text-muted-foreground">
                                    No projects available
                                </div>
                            )}
                        </div>
                        
                        {selectedProjectIds.length > 0 && (
                            <p className="text-xs text-muted-foreground">
                                {selectedProjectIds.length} project{selectedProjectIds.length !== 1 ? 's' : ''} selected
                            </p>
                        )}
                        
                        {projectTouched && selectedProjectIds.length === 0 && (
                            <p className="text-xs text-destructive mt-1">
                                At least one project must be selected.
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
                            !authorName ||
                            selectedProjectIds.length === 0
                        }
                    >
                        {isProcessing ? "Creating..." : "Create Author Style"}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}

import { Button } from "@/Components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuTrigger,
} from "@/Components/ui/dropdown-menu";
import { DropdownMenuItem } from "@/Components/ui/dropdown-menu";
import { ChevronDown, Ellipsis } from "lucide-react";
import { Input } from "@/Components/ui/input";
import { FolderPlus } from "lucide-react";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";
import { Head, router } from "@inertiajs/react";
import { Badge } from "@/Components/ui/badge";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/Components/ui/dialog";
import { useState } from "react";

export default function ProjectList({
    workspaceId,
    folders = [],
    projects = [],
}: PageProps<{
    workspaceId: string;
    folders: { id: string; name: string }[];
    projects: { id: string; name: string }[];
}>) {
    const [open, setOpen] = useState(false);
    const [folderName, setFolderName] = useState("");
    const [loading, setLoading] = useState(false);

    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Dashboard", path: "workspace.dashboard" },
        { label: "Projects", path: "workspace.projects" },
    ].map((item) => ({
        ...item,
        param: workspaceId,
    }));

    const handleAddFolder = async () => {
        if (!folderName.trim()) return;
        setLoading(true);
        router.post(
            route("workspace.folders.store", workspaceId),
            { name: folderName },
            {
                onSuccess: () => {
                    setOpen(false);
                    setFolderName("");
                },
                onFinish: () => setLoading(false),
                only: ["folders"],
                preserveScroll: true,
            }
        );
    };

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Project Overview" />
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

            <div>
                <div className="w-full flex flex-col gap-6 items-stretch justify-start">
                    <div className="w-full flex flex-row gap-4 items-center justify-between">
                        <form className="flex flex-row gap-2 items-stretch justify-start">
                            <DropdownMenu>
                                <DropdownMenuTrigger>
                                    <Button
                                        variant="secondary"
                                        className="bg-white flex flex-row gap-2 items-center justify-start"
                                    >
                                        Sort by
                                        <ChevronDown className="h-4 w-4" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="start">
                                    <DropdownMenuItem></DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                            <Input
                                type="text"
                                placeholder="Search for projects"
                                className="lg:min-w-3xs bg-white"
                            />
                        </form>
                        <div className="flex flex-row gap-2 items-stretch justify-start">
                            <Button
                                variant="default"
                                onClick={() => setOpen(true)}
                            >
                                <FolderPlus className="h-4 w-4" />
                            </Button>

                            <Button variant="default">New Project</Button>
                        </div>
                    </div>
                    {/* Folders Section: Only show if folders exist */}
                    {folders.length > 0 && (
                        <div className="flex flex-col items-stretch justify-start gap-4">
                            <p className="text-xl">Folders</p>
                            <div className="grid lg:grid-cols-4 md:grid-cols-2 gap-4">
                                {folders.map((folder) => (
                                    <div
                                        key={folder.id}
                                        className="p-4 rounded-md flex flex-col items-stretch justify-between gap-8 bg-white border border-gray-300"
                                    >
                                        <div className="flex flex-row gap-2 justify-between items-start">
                                            <div className="flex flex-col justify-start items-start gap-1">
                                                <p className="text-base">
                                                    {folder.name}
                                                </p>
                                                <p className="text-xs text-gray-500">
                                                    Created by Author
                                                </p>
                                            </div>
                                            <DropdownMenu>
                                                <DropdownMenuTrigger>
                                                    <div className="cursor-pointer">
                                                        <Ellipsis className="h-4 w-4" />
                                                    </div>
                                                </DropdownMenuTrigger>
                                                <DropdownMenuContent align="end">
                                                    <DropdownMenuItem></DropdownMenuItem>
                                                </DropdownMenuContent>
                                            </DropdownMenu>
                                        </div>
                                        <div className="flex flex-row gap-2 justify-between items-center">
                                            <p className="text-sm">21d ago</p>
                                            <Badge variant="secondary">
                                                0 Projects
                                            </Badge>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                    {/* Projects Section: Always show, but show empty state if no projects */}
                    <div className="flex flex-col items-stretch justify-start gap-4">
                        <p className="text-xl">Projects</p>
                        <div className="grid lg:grid-cols-4 md:grid-cols-2 gap-4">
                            {projects.length === 0 ? (
                                <div className="col-span-full flex flex-col items-center justify-center py-12">
                                    <p className="text-gray-500">
                                        You don't have any projects
                                    </p>
                                </div>
                            ) : (
                                projects.map((project) => (
                                    <div
                                        key={project.id}
                                        className="p-4 rounded-md flex flex-col items-stretch justify-between gap-8 bg-white border border-gray-300"
                                    >
                                        <div className="flex flex-row gap-2 justify-between items-start">
                                            <div className="flex flex-col justify-start items-start gap-1">
                                                <p className="text-base">
                                                    {project.name}
                                                </p>
                                                <p className="text-xs text-gray-500">
                                                    Created by Author
                                                </p>
                                            </div>
                                            <DropdownMenu>
                                                <DropdownMenuTrigger>
                                                    <div className="cursor-pointer">
                                                        <Ellipsis className="h-4 w-4" />
                                                    </div>
                                                </DropdownMenuTrigger>
                                                <DropdownMenuContent align="end">
                                                    <DropdownMenuItem></DropdownMenuItem>
                                                </DropdownMenuContent>
                                            </DropdownMenu>
                                        </div>
                                        <div className="flex flex-row gap-2 justify-between items-center">
                                            <p className="text-sm">21d ago</p>
                                            <Badge variant="secondary">
                                                Category Name
                                            </Badge>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </AuthenticatedLayout>
    );
}

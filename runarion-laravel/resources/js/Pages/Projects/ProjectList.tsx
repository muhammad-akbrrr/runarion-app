import { Button } from "@/Components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuTrigger,
} from "@/Components/ui/dropdown-menu";
import { DropdownMenuItem } from "@/Components/ui/dropdown-menu";
import { ChevronDown, Ellipsis, ChevronLeft } from "lucide-react";
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
import { Link } from "@inertiajs/react";

export default function ProjectList({
    workspaceId,
    folders = [],
    projects = [],
    folder = null,
}: PageProps<{
    workspaceId: string;
    folders: { id: string; name: string }[];
    projects: { id: string; name: string }[];
    folder?: { id: string; name: string } | null;
}>) {
    const [open, setOpen] = useState(false);
    const [folderName, setFolderName] = useState("");
    const [loading, setLoading] = useState(false);

    // New project modal state
    const [projectModalOpen, setProjectModalOpen] = useState(false);
    const [projectName, setProjectName] = useState("");
    const [projectLoading, setProjectLoading] = useState(false);

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

    // Handle create new project
    const handleCreateProject = async () => {
        if (!projectName.trim()) return;
        setProjectLoading(true);
        router.post(
            route("workspace.projects.store", workspaceId),
            { name: projectName, folder_id: folder ? folder.id : undefined },
            {
                onSuccess: (page) => {
                    setProjectModalOpen(false);
                    setProjectName("");
                    // The backend redirects to the editor, so no need to do anything else
                },
                onFinish: () => setProjectLoading(false),
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

            {/* New Project Modal */}
            <Dialog open={projectModalOpen} onOpenChange={setProjectModalOpen}>
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
                                onClick={() => setProjectModalOpen(false)}
                                disabled={projectLoading}
                            >
                                Cancel
                            </Button>
                            <Button
                                variant="default"
                                type="button"
                                disabled={!projectName.trim() || projectLoading}
                                onClick={handleCreateProject}
                            >
                                Create
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
                            {/** Hide Add Folder button if inside a folder */}
                            {!folder && (
                                <Button
                                    variant="default"
                                    onClick={() => setOpen(true)}
                                >
                                    <FolderPlus className="h-4 w-4" />
                                </Button>
                            )}
                            <Button
                                variant="default"
                                onClick={() => setProjectModalOpen(true)}
                            >
                                New Project
                            </Button>
                        </div>
                    </div>
                    {/* Folders Section: Only show if folders exist and no folder is selected */}
                    {folders.length > 0 && !folder && (
                        <div className="flex flex-col items-stretch justify-start gap-4">
                            <p className="text-xl">Folders</p>
                            <div className="grid lg:grid-cols-4 md:grid-cols-2 gap-4">
                                {folders.map((folderItem) => (
                                    <Link
                                        key={folderItem.id}
                                        href={route("workspace.folders.open", {
                                            workspace_id: workspaceId,
                                            folder_id: folderItem.id,
                                        })}
                                        className="p-4 rounded-md flex flex-col items-stretch justify-between gap-8 bg-white border border-gray-300 hover:bg-gray-50 transition cursor-pointer"
                                    >
                                        <div className="flex flex-row gap-2 justify-between items-start">
                                            <div className="flex flex-col justify-start items-start gap-1">
                                                <p className="text-base">
                                                    {folderItem.name}
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
                                                    <DropdownMenuItem>
                                                        <span>
                                                            Delete folder
                                                        </span>
                                                    </DropdownMenuItem>
                                                </DropdownMenuContent>
                                            </DropdownMenu>
                                        </div>
                                        <div className="flex flex-row gap-2 justify-between items-center">
                                            <p className="text-sm">21d ago</p>
                                            <Badge variant="secondary">
                                                0 Projects
                                            </Badge>
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        </div>
                    )}
                    {/* Folder View: If a folder is selected, show back button and projects in folder */}
                    {folder && (
                        <div className="flex flex-col items-stretch justify-start gap-4">
                            <Link
                                href={route("workspace.projects", workspaceId)}
                                className="flex items-center gap-2 w-fit text-gray-700 hover:text-gray-900 mb-2"
                            >
                                <ChevronLeft className="h-4 w-4" />
                                <span>Back</span>
                            </Link>
                            <div className="grid lg:grid-cols-4 md:grid-cols-2 gap-4">
                                {projects.length === 0 ? (
                                    <div className="col-span-full flex flex-col items-center justify-center py-12">
                                        <p className="text-gray-500">
                                            No projects in this folder
                                        </p>
                                    </div>
                                ) : (
                                    projects.map((project) => (
                                        <Link
                                            key={project.id}
                                            href={route(
                                                "workspace.projects.editor",
                                                {
                                                    workspace_id: workspaceId,
                                                    project_id: project.id,
                                                }
                                            )}
                                            className="p-4 rounded-md flex flex-col items-stretch justify-between gap-8 bg-white border border-gray-300 hover:bg-gray-50 transition cursor-pointer"
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
                                                        <DropdownMenuItem>
                                                            <span>
                                                                Delete project
                                                            </span>
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem>
                                                            <span>
                                                                Project settings
                                                            </span>
                                                        </DropdownMenuItem>
                                                    </DropdownMenuContent>
                                                </DropdownMenu>
                                            </div>
                                            <div className="flex flex-row gap-2 justify-between items-center">
                                                <p className="text-sm">
                                                    21d ago
                                                </p>
                                                <Badge variant="secondary">
                                                    Category Name
                                                </Badge>
                                            </div>
                                        </Link>
                                    ))
                                )}
                            </div>
                        </div>
                    )}
                    {/* Projects Section: Only show if no folder is selected */}
                    {!folder && (
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
                                        <Link
                                            key={project.id}
                                            href={route(
                                                "workspace.projects.editor",
                                                {
                                                    workspace_id: workspaceId,
                                                    project_id: project.id,
                                                }
                                            )}
                                            className="p-4 rounded-md flex flex-col items-stretch justify-between gap-8 bg-white border border-gray-300 hover:bg-gray-50 transition cursor-pointer"
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
                                                        <DropdownMenuItem>
                                                            <span>
                                                                Delete project
                                                            </span>
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem>
                                                            <span>
                                                                Project settings
                                                            </span>
                                                        </DropdownMenuItem>
                                                    </DropdownMenuContent>
                                                </DropdownMenu>
                                            </div>
                                            <div className="flex flex-row gap-2 justify-between items-center">
                                                <p className="text-sm">
                                                    21d ago
                                                </p>
                                                <Badge variant="secondary">
                                                    Category Name
                                                </Badge>
                                            </div>
                                        </Link>
                                    ))
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </AuthenticatedLayout>
    );
}

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
import { useState } from "react";
import { Link } from "@inertiajs/react";
import AddFolderDialog from "./Partials/AddFolderDialog";
import DeleteFolderDialog from "./Partials/DeleteFolderDialog";
import AddProjectDialog from "./Partials/AddProjectDialog";
import DeleteProjectDialog from "./Partials/DeleteProjectDialog";
import { Project } from "@/types/project";

const formatTimeAgo = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) {
        return `${diffInSeconds}s ago`;
    }

    const diffInMinutes = Math.floor(diffInSeconds / 60);
    if (diffInMinutes < 60) {
        return `${diffInMinutes}m ago`;
    }

    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) {
        return `${diffInHours}h ago`;
    }

    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 30) {
        return `${diffInDays}d ago`;
    }

    const diffInMonths = Math.floor(diffInDays / 30);
    if (diffInMonths < 12) {
        return `${diffInMonths}mo ago`;
    }

    const diffInYears = Math.floor(diffInMonths / 12);
    return `${diffInYears}y ago`;
};

export default function ProjectList({
    workspaceId,
    folders = [],
    projects = [],
    folder = null,
}: PageProps<{
    workspaceId: string;
    folders: { id: string; name: string; created_at: string }[];
    projects: Project[];
    folder?: { id: string; name: string; created_at: string } | null;
}>) {
    const [open, setOpen] = useState(false);
    const [folderName, setFolderName] = useState("");
    const [loading, setLoading] = useState(false);

    // New project modal state
    const [projectModalOpen, setProjectModalOpen] = useState(false);
    const [projectName, setProjectName] = useState("");
    const [projectLoading, setProjectLoading] = useState(false);

    // Delete project modal state
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [deleteProjectId, setDeleteProjectId] = useState<string | null>(null);
    const [deleteProjectName, setDeleteProjectName] = useState("");
    const [deleteProjectInput, setDeleteProjectInput] = useState("");
    const [deleteLoading, setDeleteLoading] = useState(false);

    // Delete folder modal state
    const [deleteFolderDialogOpen, setDeleteFolderDialogOpen] = useState(false);
    const [deleteFolderId, setDeleteFolderId] = useState<string | null>(null);
    const [deleteFolderLoading, setDeleteFolderLoading] = useState(false);

    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Dashboard", path: "workspace.dashboard" },
        { label: "Projects", path: "workspace.projects" },
    ].map((item) => ({
        ...item,
        param: { workspace_id: workspaceId },
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

    // Handle delete project
    const openDeleteDialog = (projectId: string, projectName: string) => {
        setDeleteProjectId(projectId);
        setDeleteProjectName(projectName);
        setDeleteProjectInput("");
        setDeleteDialogOpen(true);
    };

    const handleDeleteProject = async () => {
        if (!deleteProjectId) return;
        setDeleteLoading(true);
        router.delete(
            route("workspace.projects.destroy", {
                workspace_id: workspaceId,
                project_id: deleteProjectId,
            }),
            {
                preserveScroll: true,
                onFinish: () => {
                    setDeleteLoading(false);
                    setDeleteDialogOpen(false);
                    setDeleteProjectId(null);
                    setDeleteProjectName("");
                    setDeleteProjectInput("");
                },
            }
        );
    };

    const openDeleteFolderDialog = (folderId: string) => {
        setDeleteFolderId(folderId);
        setDeleteFolderDialogOpen(true);
    };

    const handleDeleteFolder = async () => {
        if (!deleteFolderId) return;
        setDeleteFolderLoading(true);
        router.delete(
            route("workspace.folders.destroy", {
                workspace_id: workspaceId,
                folder_id: deleteFolderId,
            }),
            {
                preserveScroll: true,
                onFinish: () => {
                    setDeleteFolderLoading(false);
                    setDeleteFolderDialogOpen(false);
                    setDeleteFolderId(null);
                },
            }
        );
    };

    const openProjectSettings = (projectId: string) => {
        router.get(
            route("workspace.projects.edit", {
                workspace_id: workspaceId,
                project_id: projectId,
            })
        );
    };

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Project Overview" />
            <AddFolderDialog
                open={open}
                setOpen={setOpen}
                folderName={folderName}
                setFolderName={setFolderName}
                loading={loading}
                handleAddFolder={handleAddFolder}
            />

            <AddProjectDialog
                open={projectModalOpen}
                setOpen={setProjectModalOpen}
                projectName={projectName}
                setProjectName={setProjectName}
                loading={projectLoading}
                handleAddProject={handleCreateProject}
            />

            <DeleteProjectDialog
                open={deleteDialogOpen}
                setOpen={setDeleteDialogOpen}
                projectName={deleteProjectName}
                confirmationInput={deleteProjectInput}
                setConfirmationInput={setDeleteProjectInput}
                loading={deleteLoading}
                handleDelete={handleDeleteProject}
            />

            <DeleteFolderDialog
                open={deleteFolderDialogOpen}
                setOpen={setDeleteFolderDialogOpen}
                loading={deleteFolderLoading}
                handleDelete={handleDeleteFolder}
            />

            <div>
                <div className="w-full flex flex-col gap-6 items-stretch justify-start">
                    <div className="w-full flex flex-row gap-4 items-center justify-between">
                        <form className="flex flex-row gap-2 items-stretch justify-start">
                            <DropdownMenu>
                                <DropdownMenuTrigger>
                                    <Button
                                        variant="outline"
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
                                {folders.map((folderItem) => {
                                    const projectCount = projects.filter(
                                        (p) => p.folder_id === folderItem.id
                                    ).length;
                                    return (
                                        <div
                                            key={folderItem.id}
                                            className="p-4 rounded-md flex flex-col items-stretch justify-between gap-8 bg-white border border-gray-300 hover:bg-gray-50 transition cursor-pointer relative"
                                        >
                                            <Link
                                                href={route(
                                                    "workspace.folders.open",
                                                    {
                                                        workspace_id:
                                                            workspaceId,
                                                        folder_id:
                                                            folderItem.id,
                                                    }
                                                )}
                                                className="absolute inset-0 z-0 w-full h-full"
                                            />
                                            <div className="flex flex-row gap-2 justify-between items-start">
                                                <div className="flex flex-col justify-start items-start gap-1">
                                                    <Link
                                                        href={route(
                                                            "workspace.folders.open",
                                                            {
                                                                workspace_id:
                                                                    workspaceId,
                                                                folder_id:
                                                                    folderItem.id,
                                                            }
                                                        )}
                                                        className="text-base"
                                                    >
                                                        {folderItem.name}
                                                    </Link>
                                                    <p className="text-xs text-gray-500">
                                                        Created by Author
                                                    </p>
                                                </div>
                                                <DropdownMenu>
                                                    <DropdownMenuTrigger>
                                                        <div className="cursor-pointer relative z-20 p-2 m-[-8px]">
                                                            <Ellipsis className="h-4 w-4" />
                                                        </div>
                                                    </DropdownMenuTrigger>
                                                    <DropdownMenuContent align="end">
                                                        <DropdownMenuItem
                                                            onClick={() =>
                                                                openDeleteFolderDialog(
                                                                    folderItem.id
                                                                )
                                                            }
                                                        >
                                                            <span>
                                                                Delete folder
                                                            </span>
                                                        </DropdownMenuItem>
                                                    </DropdownMenuContent>
                                                </DropdownMenu>
                                            </div>
                                            <div className="flex flex-row gap-2 justify-between items-center">
                                                <p className="text-sm">
                                                    {formatTimeAgo(
                                                        folderItem.created_at
                                                    )}
                                                </p>
                                                <Badge variant="secondary">
                                                    {projectCount} Project
                                                    {projectCount === 1
                                                        ? ""
                                                        : "s"}
                                                </Badge>
                                            </div>
                                        </div>
                                    );
                                })}
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
                                        <div
                                            key={project.id}
                                            className="p-4 rounded-md flex flex-col items-stretch justify-between gap-8 bg-white border border-gray-300 hover:bg-gray-50 transition cursor-pointer relative"
                                        >
                                            <Link
                                                href={route(
                                                    "workspace.projects.editor",
                                                    {
                                                        workspace_id:
                                                            workspaceId,
                                                        project_id: project.id,
                                                    }
                                                )}
                                                className="absolute inset-0 z-0 w-full h-full"
                                            />
                                            <div className="flex flex-row gap-2 justify-between items-start">
                                                <div className="flex flex-col justify-start items-start gap-1">
                                                    <Link
                                                        href={route(
                                                            "workspace.projects.editor",
                                                            {
                                                                workspace_id:
                                                                    workspaceId,
                                                                project_id:
                                                                    project.id,
                                                            }
                                                        )}
                                                        className="text-base"
                                                    >
                                                        {project.name}
                                                    </Link>
                                                    <p className="text-xs text-gray-500">
                                                        Created by{" "}
                                                        {project.author?.name ||
                                                            "Unknown"}
                                                    </p>
                                                </div>
                                                <DropdownMenu>
                                                    <DropdownMenuTrigger>
                                                        <div className="cursor-pointer relative z-20 p-2 m-[-8px]">
                                                            <Ellipsis className="h-4 w-4" />
                                                        </div>
                                                    </DropdownMenuTrigger>
                                                    <DropdownMenuContent align="end">
                                                        <DropdownMenuItem
                                                            onClick={() =>
                                                                openDeleteDialog(
                                                                    project.id,
                                                                    project.name
                                                                )
                                                            }
                                                        >
                                                            <span>
                                                                Delete project
                                                            </span>
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem
                                                            onClick={() =>
                                                                openProjectSettings(
                                                                    project.id
                                                                )
                                                            }
                                                        >
                                                            <span>
                                                                Project settings
                                                            </span>
                                                        </DropdownMenuItem>
                                                    </DropdownMenuContent>
                                                </DropdownMenu>
                                            </div>
                                            <div className="flex flex-row gap-2 justify-between items-center">
                                                <p className="text-sm">
                                                    {formatTimeAgo(
                                                        project.updated_at
                                                    )}
                                                </p>
                                                {project.category && (
                                                    <Badge
                                                        variant="secondary"
                                                        className="capitalize"
                                                    >
                                                        {project.category}
                                                    </Badge>
                                                )}
                                            </div>
                                        </div>
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
                                        <div
                                            key={project.id}
                                            className="p-4 rounded-md flex flex-col items-stretch justify-between gap-8 bg-white border border-gray-300 hover:bg-gray-50 transition cursor-pointer relative"
                                        >
                                            <Link
                                                href={route(
                                                    "workspace.projects.editor",
                                                    {
                                                        workspace_id:
                                                            workspaceId,
                                                        project_id: project.id,
                                                    }
                                                )}
                                                className="absolute inset-0 z-0 w-full h-full"
                                            />
                                            <div className="flex flex-row gap-2 justify-between items-start">
                                                <div className="flex flex-col justify-start items-start gap-1">
                                                    <Link
                                                        href={route(
                                                            "workspace.projects.editor",
                                                            {
                                                                workspace_id:
                                                                    workspaceId,
                                                                project_id:
                                                                    project.id,
                                                            }
                                                        )}
                                                        className="text-base"
                                                    >
                                                        {project.name}
                                                    </Link>
                                                    <p className="text-xs text-gray-500">
                                                        Created by{" "}
                                                        {project.author?.name ||
                                                            "Unknown"}
                                                    </p>
                                                </div>
                                                <DropdownMenu>
                                                    <DropdownMenuTrigger>
                                                        <div className="cursor-pointer relative z-20 p-2 m-[-8px]">
                                                            <Ellipsis className="h-4 w-4" />
                                                        </div>
                                                    </DropdownMenuTrigger>
                                                    <DropdownMenuContent align="end">
                                                        <DropdownMenuItem
                                                            onClick={() =>
                                                                openDeleteDialog(
                                                                    project.id,
                                                                    project.name
                                                                )
                                                            }
                                                        >
                                                            <span>
                                                                Delete project
                                                            </span>
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem
                                                            onClick={() =>
                                                                openProjectSettings(
                                                                    project.id
                                                                )
                                                            }
                                                        >
                                                            <span>
                                                                Project settings
                                                            </span>
                                                        </DropdownMenuItem>
                                                    </DropdownMenuContent>
                                                </DropdownMenu>
                                            </div>
                                            <div className="flex flex-row gap-2 justify-between items-center">
                                                <p className="text-sm">
                                                    {formatTimeAgo(
                                                        project.updated_at
                                                    )}
                                                </p>
                                                {project.category && (
                                                    <Badge
                                                        variant="secondary"
                                                        className="capitalize"
                                                    >
                                                        {project.category}
                                                    </Badge>
                                                )}
                                            </div>
                                        </div>
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

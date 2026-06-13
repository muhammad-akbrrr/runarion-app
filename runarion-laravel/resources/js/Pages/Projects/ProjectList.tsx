import { Button } from "@/Components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuTrigger,
    DropdownMenuCheckboxItem,
} from "@/Components/ui/dropdown-menu";
import { ChevronDown, ChevronLeft } from "lucide-react";
import { Input } from "@/Components/ui/input";
import { FolderPlus } from "lucide-react";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";
import { Head, router, usePage } from "@inertiajs/react";
import { useState, useMemo, useEffect } from "react";
import { Link } from "@inertiajs/react";
import AddFolderDialog from "./Partials/AddFolderDialog";
import DeleteFolderDialog from "./Partials/DeleteFolderDialog";
import AddProjectDialog from "./Partials/AddProjectDialog";
import DeleteProjectDialog from "./Partials/DeleteProjectDialog";
import { Project } from "@/types/project";
import ItemCard from "./Partials/ItemCard";
import { toast } from "sonner";
import { useWorkspacePipelineEvents } from "@/Hooks/useWorkspacePipelineEvents";

export default function ProjectList({
    workspaceId,
    folders = [],
    projects = [],
    folder = null,
}: PageProps<{
    workspaceId: string;
    folders: {
        id: string;
        name: string;
        created_at: string;
        author?: { id: number; name: string };
    }[];
    projects: Project[];
    folder?: {
        id: string;
        name: string;
        created_at: string;
        author?: { id: number; name: string };
    } | null;
}>) {
    const { flash, auth } = usePage<PageProps>().props;
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

    // Sorting state
    const [sortCategory, setSortCategory] = useState(false);
    const [sortLastModified, setSortLastModified] = useState(false);
    const [sortAlphaAsc, setSortAlphaAsc] = useState(false);
    const [sortAlphaDesc, setSortAlphaDesc] = useState(false);

    // Fuzzy search state
    const [searchValue, setSearchValue] = useState("");

    // Compute visible projects (filtered by folder if inside a folder)
    const visibleProjects = folder
        ? projects.filter((p) => p.folder_id === folder.id)
        : projects;

    // Compute sorted projects based on selected sort
    let sortedProjects = [...visibleProjects];
    if (sortCategory) {
        sortedProjects.sort((a, b) => {
            const catA = a.category || "";
            const catB = b.category || "";
            return catA.localeCompare(catB);
        });
    } else if (sortLastModified) {
        sortedProjects.sort(
            (a, b) =>
                new Date(b.updated_at).getTime() -
                new Date(a.updated_at).getTime(),
        );
    } else if (sortAlphaAsc) {
        sortedProjects.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortAlphaDesc) {
        sortedProjects.sort((a, b) => b.name.localeCompare(a.name));
    }

    // Fuzzy search filter (case-insensitive substring match)
    const filteredProjects = useMemo(() => {
        if (!searchValue.trim()) return sortedProjects;
        const search = searchValue.trim().toLowerCase();
        return sortedProjects.filter((project) =>
            project.name.toLowerCase().includes(search),
        );
    }, [searchValue, sortedProjects]);

    // Check if any sort or search is active
    const isSortActive =
        sortCategory || sortLastModified || sortAlphaAsc || sortAlphaDesc;
    const isSearchActive = !!searchValue.trim();
    const isResultsActive = isSortActive || isSearchActive;

    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Dashboard", path: "workspace.dashboard" },
        { label: "Projects", path: "workspace.projects" },
    ].map((item) => ({
        ...item,
        param: { workspace_id: workspaceId },
    }));

    const favoriteProjectIds = useMemo(
        () =>
            new Set(
                (auth.user.highlighted_projects ?? [])
                    .filter(
                        (project) => project.workspace_id === workspaceId,
                    )
                    .map((project) => project.project_id),
            ),
        [auth.user.highlighted_projects, workspaceId],
    );

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
            },
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
                onSuccess: (_page) => {
                    setProjectModalOpen(false);
                    setProjectName("");
                    // Backend redirects to editor - Inertia will follow the redirect automatically
                },
                onError: (errors) => {
                    console.error("Error creating project:", errors);
                    setProjectLoading(false);
                },
                onFinish: () => {
                    // Only set loading to false if we're still on this page
                    // (redirect should have happened if successful)
                    setTimeout(() => setProjectLoading(false), 100);
                },
                preserveScroll: false, // Allow scroll reset on redirect
            },
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
            },
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
            },
        );
    };

    const openProjectSettings = (projectId: string) => {
        router.get(
            route("workspace.projects.edit", {
                workspace_id: workspaceId,
                project_id: projectId,
            }),
        );
    };

    const handleToggleFavorite = (
        projectId: string,
        isFavorite: boolean,
    ) => {
        const routeParams = {
            workspace_id: workspaceId,
            project_id: projectId,
        };

        if (isFavorite) {
            router.delete(route("workspace.projects.unfavorite", routeParams), {
                preserveScroll: true,
                preserveState: true,
            });

            return;
        }

        router.post(
            route("workspace.projects.favorite", routeParams),
            {},
            {
                preserveScroll: true,
                preserveState: true,
            },
        );
    };

    useEffect(() => {
        if (flash?.success) toast.success(flash.success);
        if (flash?.error) toast.error(flash.error);
        if (flash?.info) toast.info(flash.info);
        if (flash?.warning) toast.warning(flash.warning);
    }, [flash?.success, flash?.error, flash?.info, flash?.warning]);

    useWorkspacePipelineEvents({
        workspaceId,
        reloadOnly: ["projects"],
    });

    return isResultsActive ? (
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
                        <div className="flex flex-row gap-2 items-stretch justify-start">
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
                                    <DropdownMenuCheckboxItem
                                        checked={sortCategory}
                                        onCheckedChange={setSortCategory}
                                    >
                                        Category
                                    </DropdownMenuCheckboxItem>
                                    <DropdownMenuCheckboxItem
                                        checked={sortLastModified}
                                        onCheckedChange={setSortLastModified}
                                    >
                                        Last Modified
                                    </DropdownMenuCheckboxItem>
                                    <DropdownMenuCheckboxItem
                                        checked={sortAlphaAsc}
                                        onCheckedChange={setSortAlphaAsc}
                                    >
                                        Alphabetically (A-Z)
                                    </DropdownMenuCheckboxItem>
                                    <DropdownMenuCheckboxItem
                                        checked={sortAlphaDesc}
                                        onCheckedChange={setSortAlphaDesc}
                                    >
                                        Alphabetically (Z-A)
                                    </DropdownMenuCheckboxItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                            <Input
                                type="text"
                                placeholder="Search for projects"
                                className="lg:min-w-3xs bg-white"
                                value={searchValue}
                                onChange={(e) => setSearchValue(e.target.value)}
                            />
                        </div>
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
                    {/* Results Section: Show for both folder and non-folder views when sort or search is active */}
                    <div className="flex flex-col items-stretch justify-start gap-4">
                        {folder ? (
                            <Link
                                href={route("workspace.projects", workspaceId)}
                                className="flex items-center gap-2 w-fit text-gray-700 hover:text-gray-900 mb-2"
                            >
                                <ChevronLeft className="h-4 w-4" />
                                <span>Back</span>
                            </Link>
                        ) : (
                            <p className="text-xl">Results</p>
                        )}
                        <div className="grid lg:grid-cols-4 md:grid-cols-2 gap-4">
                            {filteredProjects.length === 0 ? (
                                <div className="col-span-full flex flex-col items-center justify-center py-12">
                                    <p className="text-gray-500">
                                        {folder
                                            ? "No projects in this folder"
                                            : "You don't have any projects"}
                                    </p>
                                </div>
                            ) : (
                                filteredProjects.map((project) => (
                                    <ItemCard
                                        key={project.id}
                                        variant="project"
                                        item={project}
                                        onDelete={openDeleteDialog}
                                        onSettings={openProjectSettings}
                                        onToggleFavorite={
                                            handleToggleFavorite
                                        }
                                        isFavorite={favoriteProjectIds.has(
                                            project.id,
                                        )}
                                        workspaceId={workspaceId}
                                    />
                                ))
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </AuthenticatedLayout>
    ) : (
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
                        <div className="flex flex-row gap-2 items-stretch justify-start">
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
                                    <DropdownMenuCheckboxItem
                                        checked={sortCategory}
                                        onCheckedChange={setSortCategory}
                                    >
                                        Category
                                    </DropdownMenuCheckboxItem>
                                    <DropdownMenuCheckboxItem
                                        checked={sortLastModified}
                                        onCheckedChange={setSortLastModified}
                                    >
                                        Last Modified
                                    </DropdownMenuCheckboxItem>
                                    <DropdownMenuCheckboxItem
                                        checked={sortAlphaAsc}
                                        onCheckedChange={setSortAlphaAsc}
                                    >
                                        Alphabetically (A-Z)
                                    </DropdownMenuCheckboxItem>
                                    <DropdownMenuCheckboxItem
                                        checked={sortAlphaDesc}
                                        onCheckedChange={setSortAlphaDesc}
                                    >
                                        Alphabetically (Z-A)
                                    </DropdownMenuCheckboxItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                            <Input
                                type="text"
                                placeholder="Search for projects"
                                className="lg:min-w-3xs bg-white"
                                value={searchValue}
                                onChange={(e) => setSearchValue(e.target.value)}
                            />
                        </div>
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
                                        (p) => p.folder_id === folderItem.id,
                                    ).length;
                                    return (
                                        <ItemCard
                                            key={folderItem.id}
                                            variant="folder"
                                            item={folderItem}
                                            projectCount={projectCount}
                                            onDelete={openDeleteFolderDialog}
                                            workspaceId={workspaceId}
                                        />
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
                                        <ItemCard
                                            key={project.id}
                                            variant="project"
                                            item={project}
                                            onDelete={openDeleteDialog}
                                            onSettings={openProjectSettings}
                                            onToggleFavorite={
                                                handleToggleFavorite
                                            }
                                            isFavorite={favoriteProjectIds.has(
                                                project.id,
                                            )}
                                            workspaceId={workspaceId}
                                        />
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
                                        <ItemCard
                                            key={project.id}
                                            variant="project"
                                            item={project}
                                            onDelete={openDeleteDialog}
                                            onSettings={openProjectSettings}
                                            onToggleFavorite={
                                                handleToggleFavorite
                                            }
                                            isFavorite={favoriteProjectIds.has(
                                                project.id,
                                            )}
                                            workspaceId={workspaceId}
                                        />
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

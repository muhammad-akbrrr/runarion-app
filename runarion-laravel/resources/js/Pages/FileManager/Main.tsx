import React, { useState } from "react";
import { Head, usePage } from "@inertiajs/react";
import { Card, CardContent } from "@/Components/ui/card";
import { Button } from "@/Components/ui/button";
import { Badge } from "@/Components/ui/badge";
import { Checkbox } from "@/Components/ui/checkbox";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/Components/ui/table";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/Components/ui/dialog";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/Components/ui/dropdown-menu";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";
import {
    Cloud,
    Folder,
    HardDrive,
    MoreVertical,
    CirclePlus,
    ArrowUpDown,
    User,
    Users,
} from "lucide-react";

// Define the storage provider type
interface StorageProvider {
    id: string;
    name: string;
    icon: string;
    color: string;
    used: number;
    total: number;
    percentage: number;
    enabled: boolean;
}

// Define the author style type
interface AuthorStyle {
    id: string;
    name: string;
    fileCount: number;
    avatar: string;
    color: string;
}

// Define the project type
interface Project {
    id: string;
    name: string;
    size: string;
    createdAt: string;
    sharedWith: string[];
    savedIn: string;
}

// Define the props type
type Props = {
    workspaceId: string;
    workspaceName: string;
    storageProviders: StorageProvider[];
    authorStyles: AuthorStyle[];
    projects: Project[];
};

export default function FileManager() {
    const {
        workspaceId,
        workspaceName,
        storageProviders,
        authorStyles,
        projects,
    } = usePage<PageProps<Props>>().props;
    const [isAuthorStyleModalOpen, setIsAuthorStyleModalOpen] = useState(false);
    const [sortColumn, setSortColumn] = useState<string | null>(null);
    const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
    const [selectedProjects, setSelectedProjects] = useState<string[]>([]);
    const [selectAll, setSelectAll] = useState(false);

    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Dashboard", path: "workspace.dashboard" },
        { label: "File Manager", path: "workspace.files" },
    ].map((item) => ({
        ...item,
        param: { workspace_id: workspaceId },
    }));

    // Sort storage providers: enabled first (with Local Storage at the beginning), then disabled
    const sortedStorageProviders = [...storageProviders].sort((a, b) => {
        // Local Storage is always first
        if (a.name === "Local Storage") return -1;
        if (b.name === "Local Storage") return 1;

        // Then sort by enabled status
        if (a.enabled && !b.enabled) return -1;
        if (!a.enabled && b.enabled) return 1;

        // If both have the same enabled status, keep original order
        return 0;
    });

    // Sort projects based on the selected column and direction
    const sortedProjects = [...projects].sort((a, b) => {
        if (!sortColumn) return 0;

        let comparison = 0;

        switch (sortColumn) {
            case "name":
                comparison = a.name.localeCompare(b.name);
                break;
            case "size":
                // Extract numeric value from size string (e.g., "2.4 MB" -> 2.4)
                const sizeA = parseFloat(a.size);
                const sizeB = parseFloat(b.size);
                comparison = sizeA - sizeB;
                break;
            case "createdAt":
                comparison =
                    new Date(a.createdAt).getTime() -
                    new Date(b.createdAt).getTime();
                break;
            default:
                return 0;
        }

        return sortDirection === "asc" ? comparison : -comparison;
    });

    const handleSort = (column: string) => {
        if (sortColumn === column) {
            setSortDirection(sortDirection === "asc" ? "desc" : "asc");
        } else {
            setSortColumn(column);
            setSortDirection("asc");
        }
    };

    const handleSelectAll = () => {
        if (selectAll) {
            setSelectedProjects([]);
        } else {
            setSelectedProjects(projects.map((project) => project.id));
        }
        setSelectAll(!selectAll);
    };

    const handleSelectProject = (projectId: string) => {
        if (selectedProjects.includes(projectId)) {
            setSelectedProjects(
                selectedProjects.filter((id) => id !== projectId)
            );
        } else {
            setSelectedProjects([...selectedProjects, projectId]);
        }
    };

    // Function to get the appropriate icon component based on the icon name
    const getIconComponent = (iconName: string) => {
        switch (iconName) {
            case "Cloud":
                return Cloud;
            case "Dropbox":
                return Cloud;
            case "HardDrive":
                return HardDrive;
            default:
                return Folder;
        }
    };

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="File Manager" />

            <div className="space-y-6">
                {/* File Manager Section */}
                <div className="space-y-4">
                    <div className="flex justify-between items-center">
                        <h2 className="text-xl">File Manager</h2>
                    </div>

                    {/* Storage Cards - 4 column grid on md+, 2 column on sm, 1 column on xs */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                        {sortedStorageProviders.map((provider) => {
                            const IconComponent = getIconComponent(
                                provider.icon
                            );
                            return (
                                <div
                                    key={provider.id}
                                    className={`bg-white rounded-md border ${
                                        !provider.enabled ? "opacity-60" : ""
                                    }`}
                                >
                                    <div className="p-4">
                                        <div className="flex items-center gap-3">
                                            <div
                                                className={`${provider.color} p-2 rounded-full bg-gray-100`}
                                            >
                                                <IconComponent className="h-4 w-4" />
                                            </div>
                                            <div className="flex-1">
                                                <h3 className="font-medium">
                                                    {provider.name}
                                                </h3>
                                            </div>
                                        </div>

                                        {provider.enabled && (
                                            <div className="mt-3 space-y-2">
                                                <div className="h-1 w-full bg-gray-200 rounded">
                                                    <div
                                                        className="h-1 rounded bg-gray-700"
                                                        style={{
                                                            width: `${provider.percentage}%`,
                                                        }}
                                                    />
                                                </div>
                                                <div className="text-sm text-muted-foreground">
                                                    {provider.used}GB /{" "}
                                                    {provider.total}GB
                                                </div>
                                            </div>
                                        )}

                                        {!provider.enabled && (
                                            <div className="mt-3 space-y-2">
                                                <div className="h-1 w-full bg-gray-200 rounded"></div>
                                                <div className="text-sm text-muted-foreground">
                                                    ∞ / ∞
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Author Styles */}
                <div className="space-y-4">
                    <div className="flex justify-between items-center">
                        <h2 className="text-xl">Author Styles</h2>
                        <Button>
                            <CirclePlus className="h-4 w-4" />
                            Add Style
                        </Button>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                        {authorStyles.length > 0 ? (
                            authorStyles.map((style) => (
                                <div
                                    key={style.id}
                                    className="w-full bg-white rounded-md border"
                                >
                                    <div className="p-4 relative flex flex-col items-stretch justofy-between gap-3">
                                        <div className="flex flex-row items-center justify-between gap-3">
                                            <div
                                                className={`${style.color} p-2 rounded-full flex items-center justify-center font-medium`}
                                            >
                                                <div className="w-4 h-4">
                                                    {style.avatar}
                                                </div>
                                            </div>
                                            <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">
                                                {style.fileCount} Files
                                            </span>
                                        </div>
                                        <div className="truncate">
                                            <p className="font-medium text-sm">
                                                {style.name}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="w-full col-span-4 text-center py-8 text-muted-foreground">
                                You don't have any author styles yet.
                            </div>
                        )}
                    </div>
                </div>

                {/* Projects Table */}
                <div className="space-y-4">
                    <div className="flex justify-between items-center">
                        <h2 className="text-xl">Project Files</h2>
                        <Button variant="outline">View All</Button>
                    </div>

                    <Card className="rounded-md py-2">
                        <CardContent className="px-2">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className="w-[40px]">
                                            <Checkbox
                                                checked={selectAll}
                                                onCheckedChange={
                                                    handleSelectAll
                                                }
                                            />
                                        </TableHead>
                                        <TableHead
                                            className="cursor-pointer"
                                            onClick={() => handleSort("name")}
                                        >
                                            <div className="flex items-center">
                                                Name
                                                <ArrowUpDown className="ml-2 h-4 w-4" />
                                            </div>
                                        </TableHead>
                                        <TableHead
                                            className="cursor-pointer"
                                            onClick={() => handleSort("size")}
                                        >
                                            <div className="flex items-center">
                                                Size
                                                <ArrowUpDown className="ml-2 h-4 w-4" />
                                            </div>
                                        </TableHead>
                                        <TableHead
                                            className="cursor-pointer"
                                            onClick={() =>
                                                handleSort("createdAt")
                                            }
                                        >
                                            <div className="flex items-center">
                                                Created At
                                                <ArrowUpDown className="ml-2 h-4 w-4" />
                                            </div>
                                        </TableHead>
                                        <TableHead>Shared With</TableHead>
                                        <TableHead>Saved In</TableHead>
                                        <TableHead className="w-[60px]">
                                            Actions
                                        </TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {sortedProjects.length > 0 ? (
                                        sortedProjects.map((project) => (
                                            <TableRow key={project.id}>
                                                <TableCell>
                                                    <Checkbox
                                                        checked={selectedProjects.includes(
                                                            project.id
                                                        )}
                                                        onCheckedChange={() =>
                                                            handleSelectProject(
                                                                project.id
                                                            )
                                                        }
                                                    />
                                                </TableCell>
                                                <TableCell className="font-medium">
                                                    <div className="flex items-center gap-2">
                                                        <Folder className="h-4 w-4" />
                                                        {project.name}
                                                    </div>
                                                </TableCell>
                                                <TableCell>
                                                    {project.size}
                                                </TableCell>
                                                <TableCell>
                                                    {project.createdAt}
                                                </TableCell>
                                                <TableCell>
                                                    {project.sharedWith.length >
                                                    0 ? (
                                                        <div className="flex items-center">
                                                            {project.sharedWith
                                                                .length ===
                                                            1 ? (
                                                                <>
                                                                    <User className="h-4 w-4 mr-1" />
                                                                    <span>
                                                                        {
                                                                            project
                                                                                .sharedWith[0]
                                                                        }
                                                                    </span>
                                                                </>
                                                            ) : (
                                                                <>
                                                                    <Users className="h-4 w-4 mr-1" />
                                                                    <span>
                                                                        {
                                                                            project
                                                                                .sharedWith
                                                                                .length
                                                                        }{" "}
                                                                        users
                                                                    </span>
                                                                </>
                                                            )}
                                                        </div>
                                                    ) : (
                                                        <span className="text-muted-foreground">
                                                            Not shared
                                                        </span>
                                                    )}
                                                </TableCell>
                                                <TableCell>
                                                    <Badge variant="outline">
                                                        {project.savedIn}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell>
                                                    <DropdownMenu>
                                                        <DropdownMenuTrigger
                                                            asChild
                                                        >
                                                            <Button
                                                                variant="ghost"
                                                                size="icon"
                                                                className="h-8 w-8"
                                                            >
                                                                <MoreVertical className="h-4 w-4" />
                                                                <span className="sr-only">
                                                                    Open menu
                                                                </span>
                                                            </Button>
                                                        </DropdownMenuTrigger>
                                                        <DropdownMenuContent align="end">
                                                            <DropdownMenuItem>
                                                                Open
                                                            </DropdownMenuItem>
                                                            <DropdownMenuItem>
                                                                Share
                                                            </DropdownMenuItem>
                                                            <DropdownMenuItem>
                                                                Rename
                                                            </DropdownMenuItem>
                                                            <DropdownMenuItem className="text-red-600">
                                                                Delete
                                                            </DropdownMenuItem>
                                                        </DropdownMenuContent>
                                                    </DropdownMenu>
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    ) : (
                                        <TableRow>
                                            <TableCell
                                                colSpan={7}
                                                className="!text-base text-center py-8 text-gray-500 !h-[42svh]"
                                            >
                                                No projects found.
                                            </TableCell>
                                        </TableRow>
                                    )}
                                </TableBody>
                            </Table>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </AuthenticatedLayout>
    );
}

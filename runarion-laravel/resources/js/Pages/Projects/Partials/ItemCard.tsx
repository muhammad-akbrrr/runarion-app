import { Link } from "@inertiajs/react";
import { Ellipsis } from "lucide-react";
import { Badge } from "@/Components/ui/badge";
import {
    DropdownMenu,
    DropdownMenuTrigger,
    DropdownMenuContent,
    DropdownMenuItem,
} from "@/Components/ui/dropdown-menu";

interface FolderItem {
    id: string;
    name: string;
    created_at: string;
    author?: { id: number; name: string } | null;
}

interface ProjectItem {
    id: string;
    name: string;
    updated_at: string;
    author?: { id: number; name: string } | null;
    category?: string | null;
}

type ItemCardProps =
    | {
          variant: "folder";
          item: FolderItem;
          projectCount: number;
          onDelete: (id: string) => void;
          workspaceId: string;
      }
    | {
          variant: "project";
          item: ProjectItem;
          onDelete: (id: string, name: string) => void;
          onSettings: (id: string) => void;
          workspaceId: string;
      };

const formatTimeAgo = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    if (diffInSeconds < 60) return `${diffInSeconds}s ago`;
    const diffInMinutes = Math.floor(diffInSeconds / 60);
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours}h ago`;
    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 30) return `${diffInDays}d ago`;
    const diffInMonths = Math.floor(diffInDays / 30);
    if (diffInMonths < 12) return `${diffInMonths}mo ago`;
    const diffInYears = Math.floor(diffInMonths / 12);
    return `${diffInYears}y ago`;
};

export default function ItemCard(props: ItemCardProps) {
    if (props.variant === "folder") {
        const { item, projectCount, onDelete, workspaceId } = props;
        return (
            <div
                className="p-4 rounded-md flex flex-col items-stretch justify-between gap-8 bg-white border border-gray-300 hover:bg-gray-50 transition cursor-pointer relative"
            >
                <Link
                    href={route("workspace.folders.open", {
                        workspace_id: workspaceId,
                        folder_id: item.id,
                    })}
                    className="absolute inset-0 z-0 w-full h-full"
                />
                <div className="flex flex-row gap-2 justify-between items-start">
                    <div className="flex flex-col justify-start items-start gap-1">
                        <Link
                            href={route("workspace.folders.open", {
                                workspace_id: workspaceId,
                                folder_id: item.id,
                            })}
                            className="text-base"
                        >
                            {item.name}
                        </Link>
                        <p className="text-xs text-gray-500">
                            Created by {item.author?.name ?? "Unknown"}
                        </p>
                    </div>
                    <DropdownMenu>
                        <DropdownMenuTrigger>
                            <div className="cursor-pointer relative z-20 p-2 m-[-8px]">
                                <Ellipsis className="h-4 w-4" />
                            </div>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => onDelete(item.id)}>
                                <span>Delete folder</span>
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
                <div className="flex flex-row gap-2 justify-between items-center">
                    <p className="text-sm">{formatTimeAgo(item.created_at)}</p>
                    <Badge variant="secondary">
                        {projectCount} Project{projectCount === 1 ? "" : "s"}
                    </Badge>
                </div>
            </div>
        );
    } else {
        const { item, onDelete, onSettings, workspaceId } = props;
        return (
            <div
                className="p-4 rounded-md flex flex-col items-stretch justify-between gap-8 bg-white border border-gray-300 hover:bg-gray-50 transition cursor-pointer relative"
            >
                <Link
                    href={route("workspace.projects.editor", {
                        workspace_id: workspaceId,
                        project_id: item.id,
                    })}
                    className="absolute inset-0 z-0 w-full h-full"
                />
                <div className="flex flex-row gap-2 justify-between items-start">
                    <div className="flex flex-col justify-start items-start gap-1">
                        <Link
                            href={route("workspace.projects.editor", {
                                workspace_id: workspaceId,
                                project_id: item.id,
                            })}
                            className="text-base"
                        >
                            {item.name}
                        </Link>
                        <p className="text-xs text-gray-500">
                            Created by {item.author?.name ?? "Unknown"}
                        </p>
                    </div>
                    <DropdownMenu>
                        <DropdownMenuTrigger>
                            <div className="cursor-pointer relative z-20 p-2 m-[-8px]">
                                <Ellipsis className="h-4 w-4" />
                            </div>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => onDelete(item.id, item.name)}>
                                <span>Delete project</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => onSettings(item.id)}>
                                <span>Project settings</span>
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
                <div className="flex flex-row gap-2 justify-between items-center">
                    <p className="text-sm">{formatTimeAgo(item.updated_at)}</p>
                    {item.category && (
                        <Badge variant="secondary" className="capitalize">
                            {item.category}
                        </Badge>
                    )}
                </div>
            </div>
        );
    }
} 
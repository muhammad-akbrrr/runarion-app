import { Avatar, AvatarFallback, AvatarImage } from "@/Components/ui/avatar";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/Components/ui/dropdown-menu";
import { SimpleWorkspaceWithRole } from "@/types";
import { router } from "@inertiajs/react";
import { Ellipsis, PlusSquare } from "lucide-react";
import { useState } from "react";
import AddWorkspaceDialog from "./AddWorkspaceDialog";
import DeleteWorkspaceDialog from "./DeleteWorkspaceDialog";

export default function WorkspaceCard({
    workspace,
}: {
    workspace: SimpleWorkspaceWithRole | null;
}) {
    const [openAdd, setOpenAdd] = useState(false);
    const [openDelete, setOpenDelete] = useState(false);

    const workspaceInitials = workspace
        ? workspace.name
              .split(" ")
              .map((n: string) => n[0])
              .join("")
              .substring(0, 4)
              .toUpperCase()
        : "";

    const getSetWorkspaceId = () => {
        if (!workspace) {
            return;
        }
        localStorage.setItem("selectedWorkspace", workspace.id.toString());
        return workspace.id;
    };

    const handleClickOpen = () => {
        localStorage.setItem("openSidebarSettings", "0");
        getSetWorkspaceId();
        router.get(route("dashboard"));
    };

    const handleClickSettings = () => {
        const workspaceId = getSetWorkspaceId();
        router.get(route("workspace.edit", workspaceId));
    };

    return (
        <div className="relative w-64 flex flex-col justify-between bg-slate-50 border border-slate-400 rounded-lg p-4 text-center hover:shadow-md">
            {workspace ? (
                <>
                    <div className="absolute top-2 right-2">
                        <DropdownMenu>
                            <DropdownMenuTrigger className="hover:bg-gray-200 rounded-full p-0.5 cursor-pointer">
                                <Ellipsis />
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={handleClickOpen}>
                                    Open
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={handleClickSettings}>
                                    Settings
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                    onClick={() => setOpenDelete(true)}
                                >
                                    Delete
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>
                    <div>
                        <Avatar className="w-28 h-28 mx-auto rounded-full object-cover border border-slate-400">
                            <AvatarImage
                                src={workspace.cover_image_url || undefined}
                                alt={workspace.name}
                                className="object-cover object-center"
                            />
                            <AvatarFallback>{workspaceInitials}</AvatarFallback>
                        </Avatar>
                        <h2 className="text-lg font-semibold mt-2">
                            {workspace.name}
                        </h2>
                    </div>
                    <div
                        className="text-sm mt-1 mx-auto inline-block underline hover:cursor-pointer"
                        onClick={handleClickOpen}
                    >
                        Open Workspace
                    </div>
                    <DeleteWorkspaceDialog
                        workspaceId={workspace.id}
                        open={openDelete}
                        onOpenChange={setOpenDelete}
                    />
                </>
            ) : (
                <>
                    <div
                        className="flex flex-col justify-center items-center gap-2 m-auto hover:cursor-pointer"
                        onClick={() => setOpenAdd(true)}
                    >
                        <PlusSquare className="w-24 h-24 text-slate-400" />
                        <h2 className="text-lg font-semibold text-slate-400">
                            Add New
                        </h2>
                    </div>
                    <AddWorkspaceDialog
                        open={openAdd}
                        onOpenChange={setOpenAdd}
                    />
                </>
            )}
        </div>
    );
}

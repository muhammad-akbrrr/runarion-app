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
import { Head } from "@inertiajs/react";
import { Badge } from "@/Components/ui/badge";

export default function ProjectList({
    workspaceId,
}: PageProps<{
    workspaceId: string;
}>) {
    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Dashboard", path: "workspace.dashboard" },
        { label: "Projects", path: "workspace.projects" },
    ].map((item) => ({
        ...item,
        param: workspaceId,
    }));

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Project Overview" />

            <div>
                <div className="w-full flex flex-col gap-6 items-stretch justify-start">
                    <form className="w-full flex flex-row gap-4 items-center justify-between">
                        <div className="flex flex-row gap-2 items-stretch justify-start">
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
                                className="min-w-3xs bg-white"
                            />
                        </div>
                        <div className="flex flex-row gap-2 items-stretch justify-start">
                            <Button variant="default">
                                <FolderPlus className="h-4 w-4" />
                            </Button>

                            <Button variant="default">New Project</Button>
                        </div>
                    </form>
                    <div className="flex flex-col items-stretch justify-start gap-4">
                        <p className="text-xl">Folders</p>
                        <div className="grid grid-cols-4">
                            <div className="p-4 rounded-md flex flex-col items-stretch justify-between gap-8 bg-white border border-gray-300">
                                <div className="flex flex-row gap-2 justify-between items-start">
                                    <div className="flex flex-col justify-start items-start gap-1">
                                        <p className="text-base">
                                            Draft Project
                                        </p>
                                        <p className="text-xs text-gray-500">
                                            Created by Yousuf
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
                        </div>
                    </div>
                    <div className="flex flex-col items-stretch justify-start gap-4">
                        <p className="text-xl">Projects</p>
                        <div className="grid grid-cols-4">
                            <div className="p-4 rounded-md flex flex-col items-stretch justify-between gap-8 bg-white border border-gray-300">
                                <div className="flex flex-row gap-2 justify-between items-start">
                                    <div className="flex flex-col justify-start items-start gap-1">
                                        <p className="text-base">
                                            Draft Project
                                        </p>
                                        <p className="text-xs text-gray-500">
                                            Created by Yousuf
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
                        </div>
                    </div>
                </div>
            </div>
        </AuthenticatedLayout>
    );
}

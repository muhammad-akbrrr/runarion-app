import { Button } from "@/Components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/Components/ui/card";
import { Separator } from "@/Components/ui/separator";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/Components/ui/select";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps, Project } from "@/types";
import { Head } from "@inertiajs/react";
import { CirclePlus } from "lucide-react";

interface Props
    extends PageProps<{
        workspaceId: string;
        projectId: string;
        project: Project;
    }> {}

export default function ProjectAccess({
    workspaceId,
    projectId,
    project,
}: Props) {
    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Project Settings", path: "workspace.projects.edit" },
        { label: "Access", path: "workspace.projects.edit.access" },
    ].map((item) => ({
        ...item,
        param: { project_id: projectId, workspace_id: workspaceId },
    }));

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Project Access" />

            <Card className="w-full h-full gap-0">
                <CardHeader>
                    <CardTitle className="text-2xl">
                        Manage Project Access
                    </CardTitle>
                </CardHeader>
                <Separator
                    className="mt-2 mb-4 mx-6"
                    style={{ width: "auto" }}
                />
                <CardContent>
                    <div className="flex flex-col gap-4">
                        <div className="flex items-center justify-between">
                            <h2 className="font-semibold">Project Members</h2>
                            <Button>
                                <CirclePlus />
                                Add Members
                            </Button>
                        </div>
                        <div className="flex flex-col">
                            {/* First member */}
                            <div className="flex items-center justify-between border-b py-2">
                                <div>
                                    <p className="font-medium text-sm">
                                        John Doe
                                    </p>
                                    <p className="text-sm text-gray-500">
                                        john@example.com
                                    </p>
                                </div>
                                <div className="flex items-center space-x-4">
                                    <Select defaultValue="owner">
                                        <SelectTrigger
                                            size="default"
                                            className="w-32 hover:cursor-pointer"
                                        >
                                            <SelectValue placeholder="Select a role" />
                                        </SelectTrigger>
                                        <SelectContent position="popper">
                                            <SelectItem value="owner">
                                                Owner
                                            </SelectItem>
                                        </SelectContent>
                                    </Select>
                                    <Button
                                        variant="destructive"
                                        size="sm"
                                        disabled
                                    >
                                        Remove
                                    </Button>
                                </div>
                            </div>

                            {/* Second member */}
                            <div className="flex items-center justify-between border-b py-2">
                                <div>
                                    <p className="font-medium text-sm">
                                        Jane Smith
                                    </p>
                                    <p className="text-sm text-gray-500">
                                        jane@example.com
                                    </p>
                                </div>
                                <div className="flex items-center space-x-4">
                                    <Select defaultValue="member">
                                        <SelectTrigger
                                            size="default"
                                            className="w-32 hover:cursor-pointer"
                                        >
                                            <SelectValue placeholder="Select a role" />
                                        </SelectTrigger>
                                        <SelectContent position="popper">
                                            <SelectItem value="admin">
                                                Admin
                                            </SelectItem>
                                            <SelectItem value="member">
                                                Member
                                            </SelectItem>
                                        </SelectContent>
                                    </Select>
                                    <Button variant="destructive" size="sm">
                                        Remove
                                    </Button>
                                </div>
                            </div>
                        </div>
                        <div className="flex items-center justify-between mt-2">
                            <div className="text-sm text-muted-foreground">
                                Showing 1 to 2 of 10 members
                            </div>
                            <div className="flex items-center gap-2">
                                <Button variant="outline" disabled>
                                    Previous
                                </Button>
                                <Button>Next</Button>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </AuthenticatedLayout>
    );
}

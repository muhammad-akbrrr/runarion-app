import { Button } from "@/Components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/Components/ui/card";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/Components/ui/select";
import { Label } from "@/Components/ui/label";
import { Separator } from "@/Components/ui/separator";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps, Project } from "@/types";
import { Head } from "@inertiajs/react";

interface Props
    extends PageProps<{
        workspaceId: string;
        projectId: string;
        project: Project;
    }> {}

export default function ProjectBackups({
    workspaceId,
    projectId,
    project,
}: Props) {
    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Project Settings", path: "workspace.projects.edit" },
        { label: "Backups", path: "workspace.projects.edit.backups" },
    ].map((item) => ({
        ...item,
        param: { project_id: projectId, workspace_id: workspaceId },
    }));

    // Static backup items for now
    const backups = [
        {
            label: "Automatic Backup",
            date: "June 8th 2025, 2:11:56 am",
        },
        {
            label: "Manual Backup",
            date: "June 7th 2025, 11:00:00 pm",
        },
    ];

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Project Backups" />

            <Card className="w-full h-full gap-0">
                <CardHeader>
                    <CardTitle className="text-2xl">Backup History</CardTitle>
                </CardHeader>
                <Separator
                    className="mt-2 mb-6 mx-6"
                    style={{ width: "auto" }}
                />
                <CardContent className="flex flex-col gap-4">
                    {/* Backup Frequency Select */}
                    <div className="space-y-1 flex flex-col gap-1">
                        <Label htmlFor="backup-frequency">
                            Backup Frequency
                        </Label>
                        <div className="flex flex-row items-stretch justify-center gap-2">
                            <Select defaultValue="daily">
                                <SelectTrigger
                                    id="backup-frequency"
                                    className="w-full"
                                >
                                    <SelectValue placeholder="Select frequency" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="manual">
                                        Manual
                                    </SelectItem>
                                    <SelectItem value="daily">Daily</SelectItem>
                                    <SelectItem value="weekly">
                                        Weekly
                                    </SelectItem>
                                </SelectContent>
                            </Select>
                            <Button variant="default">Save</Button>
                        </div>
                    </div>

                    {/* Backup Items List */}
                    <div className="flex flex-col mt-2">
                        {backups.map((backup, idx) => (
                            <div
                                key={idx}
                                className="flex items-center justify-between border-b py-3"
                            >
                                <div>
                                    <div className="font-medium text-base mb-1">
                                        {backup.label}
                                    </div>
                                    <div className="text-sm text-muted-foreground">
                                        {backup.date}
                                    </div>
                                </div>
                                <div className="flex gap-2">
                                    <Button variant="outline" size="sm">
                                        Preview
                                    </Button>
                                    <Button variant="secondary" size="sm">
                                        Restore
                                    </Button>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Pagination */}
                    <div className="flex items-center justify-between mt-2">
                        <div className="text-sm text-muted-foreground">
                            Showing 1 to 2 of 10 backups
                        </div>
                        <div className="flex items-center gap-2">
                            <Button variant="outline" disabled>
                                Previous
                            </Button>
                            <Button>Next</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </AuthenticatedLayout>
    );
}

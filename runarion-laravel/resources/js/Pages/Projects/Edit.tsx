import { Button } from "@/Components/ui/button";
import {
    Card,
    CardContent,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/Components/ui/card";
import { Textarea } from "@/Components/ui/textarea";
import { Input } from "@/Components/ui/input";
import { Label } from "@/Components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/Components/ui/select";
import { Separator } from "@/Components/ui/separator";
import { Transition } from "@headlessui/react";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps, Project, ProjectCategory } from "@/types";
import { Head, useForm, router } from "@inertiajs/react";
import { FormEventHandler, useState } from "react";
import DeleteProjectDialog from "./Partials/DeleteProjectDialog";

interface Props
    extends PageProps<{
        workspaceId: string;
        projectId: string;
        project: Project;
    }> {}

interface FormData extends Record<string, string> {
    name: string;
    category: string;
    description: string;
    storageLocation: string;
}

const STORAGE_LOCATIONS = {
    "01": "Server",
    "02": "Google Drive",
    "03": "Dropbox",
    "04": "OneDrive",
} as const;

const CATEGORIES: ProjectCategory[] = [
    "horror",
    "sci-fi",
    "fantasy",
    "romance",
    "thriller",
    "mystery",
    "adventure",
    "comedy",
    "dystopian",
    "crime",
    "fiction",
    "biography",
    "historical",
];

const formatCategory = (category: string): string => {
    return category
        .split("-")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
};

export default function ProjectSettings({
    workspaceId,
    projectId,
    project,
}: Props) {
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [deleteProjectInput, setDeleteProjectInput] = useState("");
    const [deleteLoading, setDeleteLoading] = useState(false);

    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Project Settings", path: "workspace.projects.edit" },
        { label: "General", path: "workspace.projects.edit" },
    ].map((item) => ({
        ...item,
        param: { project_id: projectId, workspace_id: workspaceId },
    }));

    const { data, setData, patch, errors, processing, recentlySuccessful } =
        useForm<FormData>({
            name: project.name || "",
            category: project.category || "none",
            description: project.description || "",
            storageLocation: project.saved_in || "01",
        });

    const submit: FormEventHandler = (e) => {
        e.preventDefault();
        patch(
            route("workspace.projects.update", {
                workspace_id: workspaceId,
                project_id: projectId,
            })
        );
    };

    const handleDeleteProject = async () => {
        setDeleteLoading(true);
        router.delete(
            route("workspace.projects.destroy", {
                workspace_id: workspaceId,
                project_id: projectId,
            }),
            {
                onFinish: () => {
                    setDeleteLoading(false);
                    setDeleteDialogOpen(false);
                    setDeleteProjectInput("");
                },
            }
        );
    };

    // Check if current user is admin using the current_user_access information
    const isAdmin = project.current_user_access?.role === "admin";

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Project Settings" />

            <DeleteProjectDialog
                open={deleteDialogOpen}
                setOpen={setDeleteDialogOpen}
                projectName={project.name}
                confirmationInput={deleteProjectInput}
                setConfirmationInput={setDeleteProjectInput}
                loading={deleteLoading}
                handleDelete={handleDeleteProject}
            />

            <Card className="w-full h-full ">
                <form onSubmit={submit}>
                    <CardHeader>
                        <CardTitle className="text-2xl">
                            General Settings
                        </CardTitle>
                    </CardHeader>
                    <Separator
                        className="mt-2 mb-6 mx-6"
                        style={{ width: "auto" }}
                    />
                    <CardContent className="flex flex-col gap-2 mt-2">
                        <div className="space-y-1 flex flex-col gap-1">
                            <Label htmlFor="name">Project Title</Label>
                            <Input
                                id="name"
                                value={data.name}
                                onChange={(e) =>
                                    setData("name", e.target.value)
                                }
                                required
                                autoComplete="name"
                            />
                            <div className="text-sm text-destructive -mt-1.5">
                                {errors.name || "\u00A0"}
                            </div>
                        </div>

                        <div className="space-y-1 flex flex-col gap-1">
                            <Label htmlFor="category">Project Category</Label>
                            <Select
                                value={data.category}
                                onValueChange={(value) =>
                                    setData("category", value)
                                }
                            >
                                <SelectTrigger
                                    id="category"
                                    size="default"
                                    className="w-full hover:cursor-pointer"
                                >
                                    <SelectValue placeholder="Select a category" />
                                </SelectTrigger>
                                <SelectContent position="popper">
                                    <SelectItem value="none">
                                        Select a category
                                    </SelectItem>
                                    {CATEGORIES.map((category) => (
                                        <SelectItem
                                            key={category}
                                            value={category}
                                        >
                                            {formatCategory(category)}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <div className="text-sm text-destructive -mt-1.5">
                                {errors.category || "\u00A0"}
                            </div>
                        </div>

                        <div className="space-y-1 flex flex-col gap-1">
                            <Label htmlFor="storageLocation">
                                Save Project In
                            </Label>
                            <Select
                                value={data.storageLocation}
                                onValueChange={(value) =>
                                    setData("storageLocation", value)
                                }
                            >
                                <SelectTrigger
                                    id="storageLocation"
                                    size="default"
                                    className="w-full hover:cursor-pointer"
                                >
                                    <SelectValue placeholder="Select storage location" />
                                </SelectTrigger>
                                <SelectContent position="popper">
                                    {Object.entries(STORAGE_LOCATIONS).map(
                                        ([code, label]) => (
                                            <SelectItem key={code} value={code}>
                                                {label}
                                            </SelectItem>
                                        )
                                    )}
                                </SelectContent>
                            </Select>
                            <div className="text-sm text-destructive -mt-1.5">
                                {errors.storageLocation || "\u00A0"}
                            </div>
                        </div>

                        <div className="space-y-1 flex flex-col gap-1">
                            <Label htmlFor="description">Description</Label>
                            <Textarea
                                id="description"
                                value={data.description}
                                onChange={(e) =>
                                    setData("description", e.target.value)
                                }
                                className="min-h-24"
                            />
                            <div className="text-sm text-destructive -mt-1.5">
                                {errors.description || "\u00A0"}
                            </div>
                        </div>
                    </CardContent>
                    <CardFooter className="flex justify-between mt-2">
                        {isAdmin && (
                            <Button
                                type="button"
                                disabled={processing}
                                variant="destructive"
                                onClick={() => setDeleteDialogOpen(true)}
                            >
                                Delete Project
                            </Button>
                        )}
                        <div className="flex items-center gap-4">
                            <Transition
                                show={recentlySuccessful}
                                enter="transition ease-in-out"
                                enterFrom="opacity-0"
                                leave="transition ease-in-out"
                                leaveTo="opacity-0"
                            >
                                <p className="text-sm text-muted-foreground">
                                    Saved
                                </p>
                            </Transition>
                            <Button type="submit" disabled={processing}>
                                Save Changes
                            </Button>
                        </div>
                    </CardFooter>
                </form>
            </Card>
        </AuthenticatedLayout>
    );
}

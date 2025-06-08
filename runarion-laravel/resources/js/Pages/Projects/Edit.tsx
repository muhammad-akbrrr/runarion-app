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
import { PageProps, Project } from "@/types";
import { Head, useForm } from "@inertiajs/react";
import { FormEventHandler } from "react";

interface Props
    extends PageProps<{
        workspaceId: string;
        projectId: string;
        project: Project;
    }> {}

export default function ProjectSettings({
    workspaceId,
    projectId,
    project,
}: Props) {
    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Project Settings", path: "workspace.projects.edit" },
        { label: "General", path: "workspace.projects.edit" },
    ].map((item) => ({
        ...item,
        param: { project_id: projectId, workspace_id: workspaceId },
    }));

    const { data, setData, post, errors, processing, recentlySuccessful } =
        useForm({
            name: project.name,
            description: "",
            genre: "",
            storageLocation: "",
        });

    const submit: FormEventHandler = (e) => {
        e.preventDefault();
        post(route("placehoder.route.fornow", project.id), {
            forceFormData: true,
        });
    };

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Project Settings" />

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
                            <Label htmlFor="genre">Project Genre</Label>
                            <Select
                                value={data.genre}
                                onValueChange={(value) =>
                                    setData("genre", value)
                                }
                            >
                                <SelectTrigger
                                    id="genre"
                                    size="default"
                                    className="w-full hover:cursor-pointer"
                                >
                                    <SelectValue placeholder="Select a genre" />
                                </SelectTrigger>
                                <SelectContent position="popper">
                                    <SelectItem value="action">
                                        Action
                                    </SelectItem>
                                    <SelectItem value="comedy">
                                        Comedy
                                    </SelectItem>
                                    <SelectItem value="drama">Drama</SelectItem>
                                </SelectContent>
                            </Select>
                            <div className="text-sm text-destructive -mt-1.5">
                                {errors.genre || "\u00A0"}
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
                                    <SelectItem value="server">
                                        Server
                                    </SelectItem>
                                    <SelectItem value="google-drive">
                                        Google Drive
                                    </SelectItem>
                                    <SelectItem value="dropbox">
                                        Dropbox
                                    </SelectItem>
                                    <SelectItem value="onedrive">
                                        OneDrive
                                    </SelectItem>
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

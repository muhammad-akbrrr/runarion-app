import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { Label } from "@/Components/ui/label";
import { Textarea } from "@/Components/ui/textarea";
import { Workspace } from "@/types/workspace";
import { Transition } from "@headlessui/react";
import { useForm } from "@inertiajs/react";
import { FormEventHandler } from "react";

export default function UpdateWorkspaceInformationSection({
    workspace,
    isUserOwnerOrAdmin,
    className = "",
}: {
    workspace: Workspace;
    isUserOwnerOrAdmin: boolean;
    className?: string;
}) {
    const { data, setData, patch, errors, processing, recentlySuccessful } =
        useForm({
            name: workspace.name,
            description: workspace.description,
        });

    const submit: FormEventHandler = (e) => {
        e.preventDefault();
        patch(route("workspaces.update", workspace.id));
    };

    return (
        <section className={className}>
            <header>
                <h2 className="text-lg font-medium text-foreground">
                    Workspace Information
                </h2>
            </header>

            <form onSubmit={submit} className="mt-6 space-y-6">
                <div className="space-y-2">
                    <Label htmlFor="name">Name</Label>
                    <Input
                        id="name"
                        value={data.name}
                        onChange={(e) => setData("name", e.target.value)}
                        required
                        autoComplete="name"
                        disabled={!isUserOwnerOrAdmin}
                    />
                    {errors.name && (
                        <p className="text-sm text-destructive">
                            {errors.name}
                        </p>
                    )}
                </div>

                <div className="space-y-2">
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                        id="description"
                        value={data.description ?? ""}
                        onChange={(e) => setData("description", e.target.value)}
                        rows={3}
                        placeholder="A short description of your workspace."
                        disabled={!isUserOwnerOrAdmin}
                    />
                    {errors.description && (
                        <p className="text-sm text-destructive">
                            {errors.description}
                        </p>
                    )}
                </div>

                {isUserOwnerOrAdmin && (
                    <div className="flex items-center gap-4">
                        <Button type="submit" disabled={processing}>
                            Save
                        </Button>

                        <Transition
                            show={recentlySuccessful}
                            enter="transition ease-in-out"
                            enterFrom="opacity-0"
                            leave="transition ease-in-out"
                            leaveTo="opacity-0"
                        >
                            <p className="text-sm text-muted-foreground">
                                Saved.
                            </p>
                        </Transition>
                    </div>
                )}
            </form>
        </section>
    );
}

import { Button } from "@/Components/ui/button";
import { Checkbox } from "@/Components/ui/checkbox";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/Components/ui/dropdown-menu";
import { Label } from "@/Components/ui/label";
import { Workspace } from "@/types/workspace";
import { Transition } from "@headlessui/react";
import { useForm } from "@inertiajs/react";
import { FormEventHandler } from "react";

export default function UpdateWorkspaceSetting({
    workspace,
    isUserAdmin,
    className = "",
}: {
    workspace: Workspace;
    isUserAdmin: boolean;
    className?: string;
}) {
    const { data, setData, patch, errors, processing, recentlySuccessful } =
        useForm({
            ...workspace.settings,
        });

    const submit: FormEventHandler = (e) => {
        e.preventDefault();
        patch(route("workspaces.update.settings", workspace.id));
    };

    const themeOptions = [
        ["light", "Light"],
        ["dark", "Dark"],
        ["system", "System"],
    ];

    return (
        <section className={className}>
            <header>
                <h2 className="text-lg font-medium text-foreground">
                    Workspace Settings
                </h2>
            </header>

            <form onSubmit={submit} className="mt-6 space-y-6">
                <div className="space-y-2">
                    <DropdownMenu>
                        <Label htmlFor="theme">Theme</Label>
                        <DropdownMenuTrigger
                            id="theme"
                            className="px-2 py-1 bg-gray-200 rounded"
                            disabled={!isUserAdmin}
                        >
                            {data.theme || "..."}
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-48">
                            {themeOptions.map(([value, label]) => (
                                <DropdownMenuItem
                                    key={value}
                                    onClick={() => setData("theme", "system")}
                                >
                                    {label}
                                </DropdownMenuItem>
                            ))}
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>

                <div className="space-y-2">
                    <Label>Notifications</Label>
                    {data.notifications &&
                        Object.entries(data.notifications).map(
                            ([key, value]) => (
                                <div
                                    key={key}
                                    className="flex items-center space-x-2"
                                >
                                    <Checkbox
                                        id={key}
                                        checked={value}
                                        onCheckedChange={(checked) =>
                                            setData("notifications", {
                                                ...data.notifications,
                                                [key]: !!checked,
                                            })
                                        }
                                        disabled={!isUserAdmin}
                                    />
                                    <Label htmlFor={key}>{key}</Label>
                                </div>
                            )
                        )}
                </div>

                {isUserAdmin && (
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

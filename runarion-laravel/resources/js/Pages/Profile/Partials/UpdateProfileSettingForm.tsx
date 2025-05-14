import { Button } from "@/Components/ui/button";
import { Checkbox } from "@/Components/ui/checkbox";
import { Input } from "@/Components/ui/input";
import { Label } from "@/Components/ui/label";
import { Transition } from "@headlessui/react";
import { useForm, usePage } from "@inertiajs/react";
import { FormEventHandler } from "react";

const userSettingFields = [
    {
        name: "setting1",
        label: "Setting 1",
        type: "text",
    },
    {
        name: "setting2",
        label: "Setting 2",
        type: "number",
    },
    {
        name: "setting3",
        label: "Setting 3",
        type: "checkbox",
    },
];

export default function UpdateProfileSettingForm({
    className = "",
}: {
    className?: string;
}) {
    const settings = usePage().props.auth.user.settings;

    const { data, setData, patch, errors, processing, recentlySuccessful } =
        useForm(settings);

    const submit: FormEventHandler = (e) => {
        e.preventDefault();
        patch(route("profile.update.settings"), {
            preserveScroll: true,
        });
    };

    return (
        <section className={className}>
            <header>
                <h2 className="text-lg font-medium text-foreground">
                    Profile Settings
                </h2>

                <p className="mt-1 text-sm text-muted-foreground">
                    Update your account's profile settings.
                </p>
            </header>

            <form onSubmit={submit} className="mt-6 space-y-6">
                {userSettingFields.map((field) =>
                    field.type === "checkbox" ? (
                        <div
                            key={field.name}
                            className="flex items-center space-x-2"
                        >
                            <Checkbox
                                id={field.name}
                                checked={!!data[field.name]}
                                onCheckedChange={(checked) =>
                                    setData(field.name, checked)
                                }
                            />
                            <Label htmlFor={field.name}>{field.label}</Label>
                        </div>
                    ) : (
                        <div key={field.name} className="space-y-2">
                            <Label htmlFor={field.name}>{field.label}</Label>
                            <Input
                                id={field.name}
                                type={field.type}
                                value={
                                    data[field.name]
                                        ? data[field.name].toString()
                                        : ""
                                }
                                onChange={(e) =>
                                    setData(field.name, e.target.value)
                                }
                            />
                            {errors[field.name] && (
                                <p className="text-sm text-destructive">
                                    {errors[field.name]}
                                </p>
                            )}
                        </div>
                    )
                )}

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
                        <p className="text-sm text-muted-foreground">Saved.</p>
                    </Transition>
                </div>
            </form>
        </section>
    );
}

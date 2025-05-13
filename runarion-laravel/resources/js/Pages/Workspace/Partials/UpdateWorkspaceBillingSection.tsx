import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { Label } from "@/Components/ui/label";
import { Workspace, WorkspaceField } from "@/types";
import { Transition } from "@headlessui/react";
import { useForm } from "@inertiajs/react";
import { FormEventHandler } from "react";

export default function UpdateWorkspaceBillingSection({
    workspace,
    isUserOwnerOrAdmin,
    className = "",
}: {
    workspace: Workspace;
    isUserOwnerOrAdmin: boolean;
    className?: string;
}) {
    if (!isUserOwnerOrAdmin) {
        return null;
    }

    const billingFields: WorkspaceField[] = [
        {
            name: "billing_email",
            label: "Email",
            type: "email",
        },
        {
            name: "billing_name",
            label: "Name",
            type: "text",
        },
        {
            name: "billing_address",
            label: "Address",
            type: "text",
        },
        {
            name: "billing_city",
            label: "City",
            type: "text",
        },
        {
            name: "billing_state",
            label: "State",
            type: "text",
        },
        {
            name: "billing_postal_code",
            label: "Postal Code",
            type: "text",
        },
        {
            name: "billing_country",
            label: "Country",
            type: "text",
        },
        {
            name: "billing_phone",
            label: "Phone Number",
            type: "tel",
        },
        {
            name: "billing_tax_id",
            label: "Tax ID",
            type: "text",
        },
    ];

    const initialData = billingFields.reduce((acc, field) => {
        const value = workspace[field.name] ?? null;
        if (typeof value === "string" || value === null) {
            acc[field.name] = value;
        }
        return acc;
    }, {} as Record<string, string | null>);

    const { data, setData, patch, errors, processing, recentlySuccessful } =
        useForm(initialData);

    const submit: FormEventHandler = (e) => {
        e.preventDefault();
        patch(route("workspaces.update.billing", workspace.id), {
            preserveScroll: true,
        });
    };

    return (
        <section className={className}>
            <header>
                <h2 className="text-lg font-medium text-foreground">
                    Workspace Billing
                </h2>
            </header>

            <form onSubmit={submit} className="mt-6 space-y-6">
                {billingFields.map((field) => (
                    <div key={field.name} className="space-y-2">
                        <Label htmlFor={field.name}>{field.label}</Label>
                        <Input
                            id={field.name}
                            type={field.type}
                            value={data[field.name] ?? ""}
                            onChange={(e) =>
                                setData(field.name, e.target.value)
                            }
                            required
                            autoComplete={field.name}
                        />
                        {errors[field.name] && (
                            <p className="text-sm text-destructive">
                                {errors[field.name]}
                            </p>
                        )}
                    </div>
                ))}

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

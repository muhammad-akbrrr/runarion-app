import { Button } from "@/Components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/Components/ui/card";
import { Checkbox } from "@/Components/ui/checkbox";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";
import { Input } from "@/Components/ui/input";
import { Label } from "@/Components/ui/label";
import { Separator } from "@/Components/ui/separator";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";
import { Head, useForm } from "@inertiajs/react";
import { FormEventHandler } from "react";
import ConnectionCard from "./Partials/ConnectionCard";

interface LLMDataItem {
    enabled: boolean;
    api_key_exists: boolean;
}

export default function LLM({
    workspaceId,
    data,
    isUserAdmin,
    isUserOwner,
}: PageProps<{
    workspaceId: number;
    data: Record<string, LLMDataItem>;
    isUserAdmin: boolean;
    isUserOwner: boolean;
}>) {
    const {
        data: formData,
        setData: setFormData,
        patch,
        processing,
        reset,
        errors,
        clearErrors,
    } = useForm({
        llm_key: "",
        enabled: false as boolean,
        api_key: "",
        delete_api_key: false as boolean,
    });

    const llm = data[formData.llm_key];

    const closeModal = () => {
        clearErrors();
        reset();
    };

    const handleSubmit: FormEventHandler = (e) => {
        e.preventDefault();

        patch(route("workspace.update.llm", workspaceId), {
            preserveScroll: true,
            onSuccess: () => closeModal(),
            onFinish: () => reset(),
        });
    };

    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Workspace Settings", path: "workspace.edit" },
        { label: "LLM Integration", path: "workspace.edit.llm" },
    ].map((item) => ({
        ...item,
        param: workspaceId,
    }));

    const connections = [
        {
            key: "openai",
            logo_url: "/images/openai.png",
            name: "OpenAI",
            description:
                "Use your own OpenAI API keys to gain full control over the LLM model.",
        },
        {
            key: "gemini",
            logo_url: "/images/gemini.png",
            name: "Gemini",
            description:
                "Use your own Gemini API keys to gain full control over the LLM model.",
        },
        {
            key: "deepseek",
            logo_url: "/images/deepseek.png",
            name: "DeepSeek",
            description:
                "Use your own DeepSeek API keys to gain full control over the LLM model.",
        },
    ];

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="LLM Integration" />

            <Card className="w-full h-full ">
                <CardHeader>
                    <CardTitle className="text-2xl">LLM Integration</CardTitle>
                    <CardDescription className="text-sm">
                        Enable or disable LLM API integrations for this
                        workspace.
                    </CardDescription>
                </CardHeader>
                <Separator className="mx-6" style={{ width: "auto" }} />
                <CardContent className="flex flex-col gap-4">
                    {connections.map((connection) => (
                        <ConnectionCard
                            key={connection.key}
                            logo_url={connection.logo_url}
                            name={connection.name}
                            description={connection.description}
                            connected={data[connection.key]?.enabled}
                            onConnect={() => {
                                setFormData("llm_key", connection.key);
                                setFormData(
                                    "enabled",
                                    !data[connection.key]?.enabled
                                );
                            }}
                            disabled={!isUserAdmin && !isUserOwner}
                        />
                    ))}
                </CardContent>
                <Dialog
                    open={formData.llm_key !== ""}
                    onOpenChange={closeModal}
                >
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>
                                {llm?.enabled
                                    ? "Disconnect LLM"
                                    : "Connect LLM"}
                            </DialogTitle>
                            <DialogDescription>
                                {llm?.enabled
                                    ? "Are you sure you want to disconnect this LLM?"
                                    : llm?.api_key_exists
                                    ? "Since you already have an API key for this LLM, you can fill a new one to replace it or leave it empty to keep the current one."
                                    : "Since you don't have an API key for this LLM, you have to fill the field below to connect."}
                            </DialogDescription>
                        </DialogHeader>

                        <form onSubmit={handleSubmit} className="space-y-4">
                            {llm?.enabled ? (
                                <div className="flex items-center space-x-1">
                                    <Checkbox
                                        id="delete_api_key"
                                        checked={formData.delete_api_key}
                                        onCheckedChange={(checked) =>
                                            setFormData(
                                                "delete_api_key",
                                                checked === true
                                            )
                                        }
                                    />
                                    <Label
                                        htmlFor="delete_api_key"
                                        className="ml-2"
                                    >
                                        Delete API Key
                                    </Label>
                                </div>
                            ) : (
                                <div className="space-y-1">
                                    <Label
                                        htmlFor="api_key"
                                        className="sr-only"
                                    >
                                        API Key
                                    </Label>
                                    <Input
                                        id="api_key"
                                        type="password"
                                        required={!llm?.api_key_exists}
                                        value={formData.api_key}
                                        onChange={(e) =>
                                            setFormData(
                                                "api_key",
                                                e.target.value
                                            )
                                        }
                                    />
                                    <div className="text-sm text-destructive -mt-1.5">
                                        {errors.api_key || "\u00A0"}
                                    </div>
                                </div>
                            )}

                            <DialogFooter>
                                <Button
                                    type="button"
                                    variant="outline"
                                    onClick={closeModal}
                                >
                                    Cancel
                                </Button>
                                <Button
                                    type="submit"
                                    variant={
                                        llm?.enabled ? "destructive" : "default"
                                    }
                                    disabled={processing}
                                >
                                    {llm?.enabled ? "Yes" : "Connect"}
                                </Button>
                            </DialogFooter>
                        </form>
                    </DialogContent>
                </Dialog>
            </Card>
        </AuthenticatedLayout>
    );
}

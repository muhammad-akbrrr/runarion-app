import { Alert, AlertDescription } from "@/Components/ui/alert";
import { AvatarUpload } from "@/Components/ui/avatar-upload";
import { Button } from "@/Components/ui/button";
import {
    Card,
    CardContent,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/Components/ui/card";
import { Input } from "@/Components/ui/input";
import { Label } from "@/Components/ui/label";
import { Separator } from "@/Components/ui/separator";
import { Switch } from "@/Components/ui/switch";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";
import { Transition } from "@headlessui/react";
import { Head, Link, useForm, usePage } from "@inertiajs/react";
import { UserIcon } from "lucide-react";
import { FormEventHandler, useState } from "react";
import DeleteUserDialog from "./Partials/DeleteUserDialog";

export default function Edit({
    mustVerifyEmail,
    status,
}: PageProps<{ mustVerifyEmail: boolean; status?: string }>) {
    const user = usePage().props.auth.user;

    const [openDelete, setOpenDelete] = useState(false);
    const [browserNotification, setBrowserNotification] = useState(
        Notification.permission === "granted"
    );

    const { data, setData, post, errors, processing, recentlySuccessful } =
        useForm({
            name: user.name,
            email: user.email,
            settings: user.settings,
            current_password: "",
            password: "",
            photo: null as File | null,
        });

    const submit: FormEventHandler = (e) => {
        e.preventDefault();
        post(route("profile.update"), {
            forceFormData: true,
            onSuccess: () => {
                setData("current_password", "");
                setData("password", "");
            },
        });
    };

    const breadcrumbs: BreadcrumbItem[] = [
        { label: "My Settings", path: "profile.edit" },
        { label: "Profile", path: "profile.edit" },
    ];

    const handleCheckNotification = (checked: boolean, key: string) => {
        setData((prev) => ({
            ...prev,
            settings: {
                ...prev.settings,
                notifications: {
                    ...prev.settings.notifications,
                    [key]: checked,
                },
            },
        }));
    };

    const activateBrowserNotification = () => {
        Notification.requestPermission().then((permission) => {
            if (permission === "granted") {
                setBrowserNotification(true);
            }
        });
    };

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Profile" />

            <Card className="w-full h-full ">
                <form onSubmit={submit}>
                    <CardHeader>
                        <CardTitle className="text-2xl">
                            General Settings
                        </CardTitle>
                    </CardHeader>
                    <Separator
                        className="mt-2 mb-4 mx-6"
                        style={{ width: "auto" }}
                    />
                    <CardContent className="flex flex-col gap-2 mt-2">
                        <AvatarUpload
                            label="Profile Photo"
                            src={user.avatar_url}
                            onChange={(file) => setData("photo", file)}
                            fallback={UserIcon}
                            error={errors.photo}
                            className="mb-2"
                        />
                        <div className="space-y-1">
                            <Label htmlFor="name">Name</Label>
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
                        <div className="space-y-1">
                            <Label htmlFor="name">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                value={data.email}
                                onChange={(e) =>
                                    setData("email", e.target.value)
                                }
                                required
                                autoComplete="username"
                            />
                            <div className="text-sm text-destructive -mt-1.5">
                                {errors.email || "\u00A0"}
                            </div>
                            {mustVerifyEmail &&
                                user.email_verified_at === null && (
                                    <Alert className="-mt-1">
                                        <AlertDescription>
                                            Your email address is unverified.
                                            <Link
                                                href={route(
                                                    "verification.send"
                                                )}
                                                method="post"
                                                as="button"
                                                className="ml-1 text-sm text-primary underline hover:text-primary/80"
                                            >
                                                Click here to re-send the
                                                verification email.
                                            </Link>
                                        </AlertDescription>
                                    </Alert>
                                )}
                            {status === "verification-link-sent" && (
                                <Alert className="-mt-1" variant="success">
                                    <AlertDescription>
                                        A new verification link has been sent to
                                        your email address.
                                    </AlertDescription>
                                </Alert>
                            )}
                        </div>
                        <div className="space-y-1">
                            <Label htmlFor="current_password">
                                Current Password
                            </Label>
                            <Input
                                id="current_password"
                                type="password"
                                value={data.current_password}
                                onChange={(e) =>
                                    setData("current_password", e.target.value)
                                }
                                autoComplete="current-password"
                            />
                            <div className="text-sm text-destructive -mt-1.5">
                                {errors.current_password || "\u00A0"}
                            </div>
                        </div>
                        <div className="space-y-1">
                            <Label htmlFor="password">New Password</Label>
                            <Input
                                id="password"
                                type="password"
                                value={data.password}
                                onChange={(e) =>
                                    setData("password", e.target.value)
                                }
                                autoComplete="new-password"
                            />
                            <div className="text-sm text-destructive -mt-1.5">
                                {errors.password || "\u00A0"}
                            </div>
                        </div>
                    </CardContent>
                    <CardHeader>
                        <CardTitle className="text-2xl">
                            Notifications
                        </CardTitle>
                    </CardHeader>
                    <Separator
                        className="mt-2 mb-4 mx-6"
                        style={{ width: "auto" }}
                    />
                    <CardContent className="flex flex-col gap-2 mt-2 max-w-lg">
                        <div>Choose where you get notified</div>
                        <div className="flex justify-between gap-10 mt-2">
                            <Label htmlFor="email_notification">
                                Email notification
                            </Label>
                            <Switch
                                id="email_notification"
                                checked={
                                    data.settings.notifications["email"] ??
                                    false
                                }
                                onCheckedChange={(checked) =>
                                    handleCheckNotification(checked, "email")
                                }
                            />
                        </div>
                        <div className="flex justify-between gap-10 mt-2">
                            <Label htmlFor="desktop_notification">
                                Desktop notification
                            </Label>
                            <Switch
                                id="desktop_notification"
                                checked={
                                    data.settings.notifications["desktop"] ??
                                    false
                                }
                                onCheckedChange={(checked) =>
                                    handleCheckNotification(checked, "desktop")
                                }
                            />
                        </div>
                        {"Notification" in window && (
                            <div className="flex justify-between gap-10 mt-2">
                                <Label htmlFor="browser_notification">
                                    Browser notification
                                </Label>
                                <Switch
                                    id="browser_notification"
                                    checked={browserNotification}
                                    onCheckedChange={
                                        activateBrowserNotification
                                    }
                                    disabled={browserNotification}
                                />
                            </div>
                        )}
                    </CardContent>
                    <CardFooter className="flex justify-between mt-10">
                        <>
                            <Button
                                type="button"
                                disabled={processing}
                                variant="destructive"
                                onClick={() => setOpenDelete(true)}
                            >
                                Delete Account
                            </Button>
                            <DeleteUserDialog
                                open={openDelete}
                                onOpenChange={setOpenDelete}
                            />
                        </>
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

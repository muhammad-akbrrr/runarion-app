import { AvatarUpload } from "@/Components/avatar-upload";
import { Button } from "@/Components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";
import { Input } from "@/Components/ui/input";
import { Label } from "@/Components/ui/label";
import { useForm } from "@inertiajs/react";
import { FormEventHandler } from "react";

export default function AddWorkspaceDialog({
    open,
    onOpenChange,
}: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}) {
    const { data, setData, post, processing, reset, errors, clearErrors } =
        useForm({
            name: "",
            slug: "",
            photo: null as File | null,
        });

    const closeModal = () => {
        onOpenChange(false);
        clearErrors();
        reset();
    };

    const store: FormEventHandler = (e) => {
        e.preventDefault();

        post(route("workspace.store"), {
            preserveScroll: true,
            onSuccess: () => closeModal(),
            forceFormData: true,
        });
    };

    const getSlug = (value: string) =>
        value
            .toLowerCase()
            .replace(/\s+/g, "-")
            .replace(/[^\w-]+/g, "");

    return (
        <Dialog open={open} onOpenChange={closeModal}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Add New Workspace</DialogTitle>
                </DialogHeader>
                <form onSubmit={store} className="space-y-1">
                    <AvatarUpload
                        label="Workspace Photo"
                        src={null}
                        onChange={(file) => setData("photo", file)}
                        error={errors.photo}
                        className="mb-2"
                    />
                    <div className="space-y-1">
                        <Label htmlFor="name">Name</Label>
                        <Input
                            id="name"
                            value={data.name}
                            onChange={(e) => {
                                setData("name", e.target.value);
                                setData("slug", getSlug(e.target.value));
                            }}
                            required
                            autoComplete="name"
                        />
                        <div className="text-sm text-destructive -mt-1.5">
                            {errors.name || "\u00A0"}
                        </div>
                    </div>
                    <div className="space-y-1">
                        <Label htmlFor="slug">Slug</Label>
                        <Input
                            id="slug"
                            value={data.slug}
                            onChange={(e) =>
                                setData("slug", getSlug(e.target.value))
                            }
                            required
                            autoComplete="slug"
                        />
                        <div className="text-sm text-destructive -mt-1.5">
                            {errors.slug || "\u00A0"}
                        </div>
                    </div>
                    <DialogFooter>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={closeModal}
                        >
                            Cancel
                        </Button>
                        <Button type="submit" disabled={processing}>
                            Add
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}

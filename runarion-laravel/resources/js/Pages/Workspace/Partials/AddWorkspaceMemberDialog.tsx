import { Button } from "@/Components/ui/button";
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
import { router } from "@inertiajs/react";
import { useEffect, useState } from "react";

const isValidEmail = (email: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
};

export default function AddWorkspaceMemberDialog({
    open,
    onOpenChange,
    workspaceId,
    isUserOwner,
}: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    workspaceId: string;
    isUserOwner: boolean;
}) {
    const [role, setRole] = useState("member");
    const [query, setQuery] = useState("");
    const [emails, setEmails] = useState<string[]>([]);
    const [selectedEmails, setSelectedEmails] = useState<
        { email: string; exist: boolean }[]
    >([]);
    const [processing, setProcessing] = useState(false);
    const [showError, setShowError] = useState(false);

    useEffect(() => {
        if (!open || query.length == 0) {
            setEmails([]);
            return;
        }

        const path = route("workspace-member.unassigned", workspaceId);
        const queryParams = new URLSearchParams({
            search: query,
            limit: "10",
        }).toString();
        const controller = new AbortController();
        let timeoutId: NodeJS.Timeout;

        const fetchOptions = async () => {
            try {
                const res = await fetch(`${path}?${queryParams}`, {
                    signal: controller.signal,
                });

                const data: { id: number; name: string; email: string }[] =
                    await res.json();
                setEmails(data.map((item) => item.email));
            } catch (error) {
                console.error(error);
            }
        };

        timeoutId = setTimeout(fetchOptions, 200);

        return () => {
            clearTimeout(timeoutId);
            controller.abort();
        };
    }, [open, query]);

    const disabled = selectedEmails.length === 0 || processing;

    const handleOpenChange = (open: boolean) => {
        onOpenChange(open);
        if (!open) {
            setQuery("");
            setEmails([]);
            setSelectedEmails([]);
            setShowError(false);
        }
    };

    const handleSelect = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key !== " ") return;

        if (!query) return;

        if (!isValidEmail(query)) {
            setShowError(true);
            return;
        }
        setShowError(false);

        if (!selectedEmails.some((item) => item.email === query)) {
            const exist = emails.includes(query);
            setSelectedEmails((prev) => [...prev, { email: query, exist }]);
        }

        setQuery("");
    };

    const removeItem = (item: string) => {
        setSelectedEmails((prev) => prev.filter((e) => e.email !== item));
    };

    const handleAdd = () =>
        router.post(
            route("workspace-member.assign"),
            {
                workspace_id: workspaceId,
                role: role,
                user_emails: selectedEmails.map((item) => item.email),
            },
            {
                preserveScroll: true,
                onSuccess: () => handleOpenChange(false),
                onStart: () => setProcessing(true),
                onFinish: () => setProcessing(false),
            }
        );

    return (
        <Dialog open={open} onOpenChange={handleOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Invite Workspace Members</DialogTitle>
                    <DialogDescription>
                        Type/search email addresses of the members you want to
                        invite to this workspace. You can invite multiple
                        members at once by clicking SPACE after each email
                        address.
                    </DialogDescription>
                </DialogHeader>

                {selectedEmails.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                        {selectedEmails.map((item) => (
                            <div
                                key={item.email}
                                className="bg-gray-200 text-sm px-3 rounded-full flex items-center"
                                style={
                                    item.exist
                                        ? {}
                                        : {
                                              color: "gray",
                                          }
                                }
                            >
                                <span>
                                    {item.email +
                                        (item.exist ? "" : " (unregistered)")}
                                </span>
                                <button
                                    type="button"
                                    onClick={() => removeItem(item.email)}
                                    className="ml-2 text-lg text-gray-600 hover:text-red-500"
                                >
                                    &times;
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                {showError && (
                    <p className="text-red-500 text-sm">
                        Please enter a valid email address.
                    </p>
                )}

                <Input
                    type="email"
                    placeholder="Start typing email address ..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={handleSelect}
                    list="suggestions"
                />
                <datalist id="suggestions">
                    {emails
                        .filter(
                            (email) =>
                                !selectedEmails
                                    .map((item) => item.email)
                                    .includes(email)
                        )
                        .map((email, idx) => (
                            <option key={idx} value={email} />
                        ))}
                </datalist>

                {isUserOwner && (
                    <div className="flex items-center gap-2">
                        <Checkbox
                            id="role"
                            checked={role === "admin"}
                            onCheckedChange={(checked) =>
                                setRole(checked ? "admin" : "member")
                            }
                        />
                        <Label htmlFor="role">Invite as Admin</Label>
                    </div>
                )}

                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={() => handleOpenChange(false)}
                    >
                        Cancel
                    </Button>
                    <Button disabled={disabled} onClick={handleAdd}>
                        Add
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

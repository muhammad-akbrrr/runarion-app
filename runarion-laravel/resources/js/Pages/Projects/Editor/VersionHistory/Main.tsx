import { useEffect, useRef, useState } from "react";
import ProjectEditorLayout from "@/Layouts/ProjectEditorLayout";
import { PageProps, Project } from "@/types";
import { Head, router } from "@inertiajs/react";
import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { Textarea } from "@/Components/ui/textarea";
import { Label } from "@/Components/ui/label";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/Components/ui/card";
import { Clock, History, Loader2, Save, User } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";
import { http } from "@/Lib/http";

interface SnapshotSummary {
    chapter_count: number;
    chat_count: number;
    message_count: number;
    entity_count: number;
    relationship_count: number;
    has_multiprompt_state: boolean;
}

interface Snapshot {
    id: string;
    name: string | null;
    description: string | null;
    snapshot_kind: string;
    is_immutable: boolean;
    created_at: string;
    created_by: {
        id: number;
        name: string;
    } | null;
    summary: SnapshotSummary;
}

export default function VersionHistoryPage({
    workspaceId,
    projectId,
    project,
    snapshots = [],
    summary,
}: PageProps<{
    workspaceId: string;
    projectId: string;
    project: Project;
    snapshots?: Snapshot[];
    summary: SnapshotSummary & { snapshot_count: number };
}>) {
    const [localSnapshots, setLocalSnapshots] = useState<Snapshot[]>(snapshots);
    const [isSaveDialogOpen, setIsSaveDialogOpen] = useState(false);
    const [snapshotName, setSnapshotName] = useState("");
    const [snapshotDescription, setSnapshotDescription] = useState("");
    const [isSaving, setIsSaving] = useState(false);
    const [isRestoring, setIsRestoring] = useState(false);
    const [isSavingIndicator, setIsSavingIndicator] = useState(false);
    const savingDebounceRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        if (isSaving || isRestoring) {
            setIsSavingIndicator(true);
            if (savingDebounceRef.current) {
                clearTimeout(savingDebounceRef.current);
                savingDebounceRef.current = null;
            }
        } else {
            savingDebounceRef.current = setTimeout(() => {
                setIsSavingIndicator(false);
            }, 1500);
        }

        return () => {
            if (savingDebounceRef.current) {
                clearTimeout(savingDebounceRef.current);
            }
        };
    }, [isSaving, isRestoring]);

    const handleSaveSnapshot = async () => {
        setIsSaving(true);

        try {
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/version-history/snapshots`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                    },
                    data: {
                        name: snapshotName || null,
                        description: snapshotDescription || null,
                    },
                },
            );

            const data = response.data;
            if (response.status >= 200 && response.status < 300 && data.success) {
                setLocalSnapshots((prev) => [data.snapshot, ...prev]);
                setSnapshotName("");
                setSnapshotDescription("");
                setIsSaveDialogOpen(false);
                toast.success("Manual snapshot created.");
                return;
            }

            toast.error(data.error || data.message || "Failed to create snapshot.");
        } catch (error) {
            toast.error(
                `Failed to create snapshot: ${
                    error instanceof Error ? error.message : "Unknown error"
                }`,
            );
        } finally {
            setIsSaving(false);
        }
    };

    const handleRestoreSnapshot = async (snapshotId: string) => {
        if (
            !confirm(
                "Restore this project snapshot? A pre-restore safety snapshot will be created automatically.",
            )
        ) {
            return;
        }

        setIsRestoring(true);

        try {
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/version-history/snapshots/${snapshotId}/restore`,
                {
                    method: "POST",
                    headers: {
                        Accept: "application/json",
                    },
                },
            );

            const data = response.data;
            if (response.status === 202 && data.success) {
                toast.success("Snapshot restore started. Redirecting out of the editor...");
                setTimeout(() => {
                    router.visit(
                        data.redirect_to ||
                            route("workspace.projects", {
                                workspace_id: workspaceId,
                            }),
                    );
                }, 1200);
                return;
            }

            toast.error(data.error || data.message || "Failed to restore snapshot.");
        } catch (error) {
            toast.error(
                `Failed to restore snapshot: ${
                    error instanceof Error ? error.message : "Unknown error"
                }`,
            );
        } finally {
            setIsRestoring(false);
        }
    };

    const kindLabel = (kind: string) => {
        switch (kind) {
            case "anchor":
                return "Original";
            case "manual":
                return "Manual";
            case "autosave":
                return "Auto";
            case "pre_restore":
                return "Pre-Restore";
            case "pipeline_import":
                return "Pipeline";
            default:
                return kind;
        }
    };

    return (
        <ProjectEditorLayout
            project={project}
            projectId={projectId}
            workspaceId={workspaceId}
            isSaving={isSavingIndicator}
        >
            <Head title="Version History" />

            <div className="w-full h-full bg-gray-50 p-4 md:p-6">
                <div className="mx-auto flex max-w-6xl flex-col gap-4">
                    <Card className="border-gray-200">
                        <CardHeader className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                            <div className="space-y-1">
                                <CardTitle className="flex items-center gap-2 text-xl">
                                    <History className="h-5 w-5" />
                                    Project Snapshots
                                </CardTitle>
                                <CardDescription>
                                    Snapshots capture the full project state, not
                                    just chapter text.
                                </CardDescription>
                            </div>
                            <Button
                                onClick={() => setIsSaveDialogOpen(true)}
                                className="gap-2"
                            >
                                <Save className="h-4 w-4" />
                                Create Manual Snapshot
                            </Button>
                        </CardHeader>
                        <CardContent className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
                            <Metric label="Snapshots" value={summary.snapshot_count} />
                            <Metric label="Chapters" value={summary.chapter_count} />
                            <Metric label="Chats" value={summary.chat_count} />
                            <Metric label="Messages" value={summary.message_count} />
                            <Metric label="Entities" value={summary.entity_count} />
                            <Metric
                                label="Multiprompt"
                                value={summary.has_multiprompt_state ? "Saved" : "Empty"}
                            />
                        </CardContent>
                    </Card>

                    <div className="grid gap-4">
                        {localSnapshots.length === 0 ? (
                            <Card className="border-dashed border-gray-300 bg-white">
                                <CardContent className="py-12 text-center text-gray-500">
                                    <History className="mx-auto mb-3 h-10 w-10 text-gray-300" />
                                    No snapshots available.
                                </CardContent>
                            </Card>
                        ) : (
                            localSnapshots.map((snapshot) => (
                                <Card key={snapshot.id} className="border-gray-200 bg-white">
                                    <CardHeader className="gap-3 md:flex-row md:items-start md:justify-between">
                                        <div className="space-y-2">
                                            <div className="flex flex-wrap items-center gap-2">
                                                <CardTitle className="text-base">
                                                    {snapshot.name || "Untitled Snapshot"}
                                                </CardTitle>
                                                <span className="rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-gray-700">
                                                    {kindLabel(snapshot.snapshot_kind)}
                                                </span>
                                                {snapshot.is_immutable && (
                                                    <span className="rounded-full bg-amber-100 px-2 py-1 text-xs font-medium text-amber-800">
                                                        Immutable
                                                    </span>
                                                )}
                                            </div>
                                            {snapshot.description && (
                                                <CardDescription className="max-w-3xl text-sm">
                                                    {snapshot.description}
                                                </CardDescription>
                                            )}
                                            <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500">
                                                <span className="flex items-center gap-1">
                                                    <Clock className="h-3 w-3" />
                                                    {formatDistanceToNow(
                                                        new Date(snapshot.created_at),
                                                        { addSuffix: true },
                                                    )}
                                                </span>
                                                <span className="text-gray-400">
                                                    {new Date(snapshot.created_at).toLocaleString()}
                                                </span>
                                                {snapshot.created_by && (
                                                    <span className="flex items-center gap-1">
                                                        <User className="h-3 w-3" />
                                                        {snapshot.created_by.name}
                                                    </span>
                                                )}
                                            </div>
                                        </div>

                                        <Button
                                            onClick={() => handleRestoreSnapshot(snapshot.id)}
                                            variant="outline"
                                            disabled={isRestoring}
                                        >
                                            {isRestoring ? (
                                                <Loader2 className="h-4 w-4 animate-spin" />
                                            ) : (
                                                "Restore Snapshot"
                                            )}
                                        </Button>
                                    </CardHeader>
                                    <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
                                        <Metric label="Chapters" value={snapshot.summary.chapter_count} />
                                        <Metric label="Chats" value={snapshot.summary.chat_count} />
                                        <Metric label="Messages" value={snapshot.summary.message_count} />
                                        <Metric label="Entities" value={snapshot.summary.entity_count} />
                                        <Metric label="Relations" value={snapshot.summary.relationship_count} />
                                        <Metric
                                            label="Multiprompt"
                                            value={
                                                snapshot.summary.has_multiprompt_state
                                                    ? "Saved"
                                                    : "Empty"
                                            }
                                        />
                                    </CardContent>
                                </Card>
                            ))
                        )}
                    </div>
                </div>
            </div>

            <Dialog open={isSaveDialogOpen} onOpenChange={setIsSaveDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Create Manual Snapshot</DialogTitle>
                        <DialogDescription>
                            This captures the current project-wide state,
                            including content, settings, chats, records, and
                            multiprompt state.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        <div className="space-y-2">
                            <Label htmlFor="snapshot-name">Name</Label>
                            <Input
                                id="snapshot-name"
                                value={snapshotName}
                                onChange={(e) => setSnapshotName(e.target.value)}
                                placeholder="Before arc rewrite"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="snapshot-description">Description</Label>
                            <Textarea
                                id="snapshot-description"
                                value={snapshotDescription}
                                onChange={(e) => setSnapshotDescription(e.target.value)}
                                placeholder="Optional note about why this snapshot matters."
                                rows={4}
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setIsSaveDialogOpen(false)}
                            disabled={isSaving}
                        >
                            Cancel
                        </Button>
                        <Button onClick={handleSaveSnapshot} disabled={isSaving}>
                            {isSaving ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                "Create Snapshot"
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </ProjectEditorLayout>
    );
}

function Metric({
    label,
    value,
}: {
    label: string;
    value: number | string;
}) {
    return (
        <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-3">
            <div className="text-xs uppercase tracking-wide text-gray-500">
                {label}
            </div>
            <div className="mt-1 text-lg font-semibold text-gray-900">
                {value}
            </div>
        </div>
    );
}

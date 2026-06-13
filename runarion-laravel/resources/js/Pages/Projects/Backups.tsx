import { useMemo, useState } from "react";
import { Button } from "@/Components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/Components/ui/card";
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
import { Textarea } from "@/Components/ui/textarea";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { http } from "@/Lib/http";
import { PageProps, Project } from "@/types";
import { Head, router } from "@inertiajs/react";
import { formatDistanceToNow } from "date-fns";
import {
    BookOpenText,
    Clock3,
    GitBranch,
    Loader2,
    MessageSquare,
    Plus,
    RotateCcw,
    Save,
    User,
} from "lucide-react";
import { toast } from "sonner";

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

interface Props extends PageProps<{
    workspaceId: string;
    projectId: string;
    project: Project;
    snapshots: Snapshot[];
    summary: SnapshotSummary & { snapshot_count: number };
}> {}

export default function ProjectBackups({
    workspaceId,
    projectId,
    snapshots,
    summary,
}: Props) {
    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Project Settings", path: "workspace.projects.edit" },
        { label: "Backups", path: "workspace.projects.edit.backups" },
    ].map((item) => ({
        ...item,
        param: { project_id: projectId, workspace_id: workspaceId },
    }));

    const [localSnapshots, setLocalSnapshots] = useState<Snapshot[]>(snapshots);
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [snapshotName, setSnapshotName] = useState("");
    const [snapshotDescription, setSnapshotDescription] = useState("");
    const [isSaving, setIsSaving] = useState(false);
    const [restoringSnapshotId, setRestoringSnapshotId] = useState<
        string | null
    >(null);

    const renderedSummary = useMemo(
        () => ({
            snapshot_count: localSnapshots.length,
            chapter_count: summary.chapter_count,
            chat_count: summary.chat_count,
            entity_count: summary.entity_count,
            has_multiprompt_state: summary.has_multiprompt_state,
        }),
        [localSnapshots.length, summary],
    );

    const handleCreateSnapshot = async () => {
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
            if (
                response.status >= 200 &&
                response.status < 300 &&
                data.success
            ) {
                setLocalSnapshots((prev) => [data.snapshot, ...prev]);
                setSnapshotName("");
                setSnapshotDescription("");
                setIsCreateOpen(false);
                toast.success("Snapshot created.");
                return;
            }

            toast.error(
                data.error || data.message || "Failed to create snapshot.",
            );
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
                "Restore this project backup? A pre-restore snapshot will be created automatically before the restore starts.",
            )
        ) {
            return;
        }

        setRestoringSnapshotId(snapshotId);

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
                toast.success(
                    "Restore started. Redirecting out of the project...",
                );
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

            toast.error(
                data.error || data.message || "Failed to restore snapshot.",
            );
        } catch (error) {
            toast.error(
                `Failed to restore snapshot: ${
                    error instanceof Error ? error.message : "Unknown error"
                }`,
            );
        } finally {
            setRestoringSnapshotId(null);
        }
    };

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Project Backups" />

            <Card className="h-full w-full gap-0">
                <CardHeader className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                    <div className="space-y-1">
                        <CardTitle className="text-2xl">
                            Backup History
                        </CardTitle>
                        <p className="text-sm text-muted-foreground">
                            Backups capture the full project state: chapters,
                            project settings, chats, entities, and multiprompt
                            state.
                        </p>
                    </div>
                    <Button
                        onClick={() => setIsCreateOpen(true)}
                        className="gap-2"
                    >
                        <Plus className="h-4 w-4" />
                        Create Snapshot
                    </Button>
                </CardHeader>
                <Separator
                    className="mx-6 mb-6 mt-2"
                    style={{ width: "auto" }}
                />
                <CardContent className="flex flex-col gap-6">
                    <div className="grid gap-3 md:grid-cols-4">
                        <SummaryMetric
                            label="Backups"
                            value={renderedSummary.snapshot_count}
                        />
                        <SummaryMetric
                            label="Chapters"
                            value={renderedSummary.chapter_count}
                        />
                        <SummaryMetric
                            label="Entities"
                            value={renderedSummary.entity_count}
                        />
                        <SummaryMetric
                            label="Chats"
                            value={renderedSummary.chat_count}
                        />
                    </div>

                    <div className="rounded-xl border bg-background">
                        {localSnapshots.length === 0 ? (
                            <div className="px-6 py-16 text-center text-sm text-muted-foreground">
                                No backups yet.
                            </div>
                        ) : (
                            localSnapshots.map((snapshot, index) => (
                                <SnapshotRow
                                    key={snapshot.id}
                                    snapshot={snapshot}
                                    isLast={index === localSnapshots.length - 1}
                                    isRestoring={
                                        restoringSnapshotId === snapshot.id
                                    }
                                    onRestore={() =>
                                        handleRestoreSnapshot(snapshot.id)
                                    }
                                />
                            ))
                        )}
                    </div>
                </CardContent>
            </Card>

            <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Create Snapshot</DialogTitle>
                        <DialogDescription>
                            Save a project-wide backup that can be restored
                            later.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="snapshot-name">Name</Label>
                            <Input
                                id="snapshot-name"
                                value={snapshotName}
                                onChange={(event) =>
                                    setSnapshotName(event.target.value)
                                }
                                placeholder="Optional snapshot name"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="snapshot-description">
                                Description
                            </Label>
                            <Textarea
                                id="snapshot-description"
                                value={snapshotDescription}
                                onChange={(event) =>
                                    setSnapshotDescription(event.target.value)
                                }
                                placeholder="What is important about this snapshot?"
                                rows={4}
                            />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setIsCreateOpen(false)}
                            disabled={isSaving}
                        >
                            Cancel
                        </Button>
                        <Button
                            onClick={handleCreateSnapshot}
                            disabled={isSaving}
                            className="gap-2"
                        >
                            {isSaving ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <Save className="h-4 w-4" />
                            )}
                            Save Snapshot
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </AuthenticatedLayout>
    );
}

function SnapshotRow({
    snapshot,
    isLast,
    isRestoring,
    onRestore,
}: {
    snapshot: Snapshot;
    isLast: boolean;
    isRestoring: boolean;
    onRestore: () => void;
}) {
    return (
        <div
            className={`flex flex-col gap-4 p-4 md:flex-row md:items-center md:justify-between ${
                isLast ? "" : "border-b"
            }`}
        >
            <div className="min-w-0 md:w-xs space-y-2">
                <div className="text-sm font-semibold text-foreground capitalize">
                    {formatDistanceToNow(new Date(snapshot.created_at), {
                        addSuffix: true,
                    })}
                </div>
                <div className="text-sm text-muted-foreground">
                    {new Date(snapshot.created_at).toLocaleString()}
                </div>
            </div>

            <div className="min-w-0 flex-1 space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                    <div className="truncate text-sm font-medium text-foreground">
                        {snapshot.name || kindLabel(snapshot.snapshot_kind)}
                    </div>
                    <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                        {kindLabel(snapshot.snapshot_kind)}
                    </span>
                </div>

                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
                    <SnapshotMeta
                        icon={BookOpenText}
                        label={`${snapshot.summary.chapter_count} chapters`}
                    />
                    <SnapshotMeta
                        icon={GitBranch}
                        label={`${snapshot.summary.entity_count} entities`}
                    />
                    <SnapshotMeta
                        icon={MessageSquare}
                        label={`${snapshot.summary.chat_count} chats`}
                    />
                    <SnapshotMeta
                        icon={Clock3}
                        label={
                            snapshot.summary.has_multiprompt_state
                                ? "Multiprompt saved"
                                : "No multiprompt state"
                        }
                    />
                    {snapshot.created_by && (
                        <SnapshotMeta
                            icon={User}
                            label={snapshot.created_by.name}
                        />
                    )}
                </div>
            </div>

            <div className="flex shrink-0 items-center gap-2">
                <Button
                    onClick={onRestore}
                    disabled={isRestoring}
                    className="gap-2"
                >
                    {isRestoring ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                        <RotateCcw className="h-4 w-4" />
                    )}
                    Restore
                </Button>
            </div>
        </div>
    );
}

function SnapshotMeta({
    icon: Icon,
    label,
}: {
    icon: typeof Clock3;
    label: string;
}) {
    return (
        <span className="flex items-center gap-1.5">
            <Icon className="h-3.5 w-3.5" />
            {label}
        </span>
    );
}

function SummaryMetric({
    label,
    value,
}: {
    label: string;
    value: string | number;
}) {
    return (
        <div className="rounded-xl border bg-background px-4 py-3">
            <div className="text-xs uppercase tracking-wide text-muted-foreground">
                {label}
            </div>
            <div className="mt-1 text-lg font-semibold text-foreground">
                {value}
            </div>
        </div>
    );
}

function kindLabel(kind: string) {
    switch (kind) {
        case "anchor":
            return "Original version";
        case "manual":
            return "Manual snapshot";
        case "autosave":
            return "Automatic backup";
        case "pre_restore":
            return "Pre-restore snapshot";
        case "pipeline_import":
            return "Pipeline backup";
        default:
            return kind;
    }
}

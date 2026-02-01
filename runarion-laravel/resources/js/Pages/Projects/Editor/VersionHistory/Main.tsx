import { useState, useEffect, useRef } from "react";
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
import {
    History,
    Save,
    Trash2,
    Edit,
    ChevronRight,
    ChevronDown,
    Clock,
    User,
    Loader2,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";

interface Snapshot {
    id: string;
    name: string | null;
    description: string | null;
    created_at: string;
    created_by: {
        id: number;
        name: string;
    } | null;
}

interface ChapterVersionInfo {
    order: number;
    chapter_name: string;
    current_node_id: string | null;
    current_version_index: number;
    navigation_info: {
        canUndo: boolean;
        canRedo: boolean;
        canRegenerate: boolean;
        currentVersionIndex: number;
        totalVersions: number;
        versionDisplayText: string;
    };
    version_tree: VersionTreeNode[];
}

interface VersionTreeNode {
    node_id: string;
    parent_node_id: string | null;
    parent_version_index: number | null;
    is_user_generated: boolean;
    generation_settings: any;
    created_at: string | null;
    is_current: boolean;
    versions: VersionInfo[];
}

interface VersionInfo {
    version_index: number;
    content_preview: string;
    content_length: number;
    created_at: string | null;
    is_current: boolean;
}

export default function VersionHistoryPage({
    workspaceId,
    projectId,
    project,
    snapshots = [],
    chapters = [],
}: PageProps<{
    workspaceId: string;
    projectId: string;
    project: Project;
    snapshots?: Snapshot[];
    chapters?: ChapterVersionInfo[];
}>) {
    const [localSnapshots, setLocalSnapshots] = useState<Snapshot[]>(snapshots);
    const [localChapters, setLocalChapters] =
        useState<ChapterVersionInfo[]>(chapters);
    const [isSaveDialogOpen, setIsSaveDialogOpen] = useState(false);
    const [snapshotName, setSnapshotName] = useState("");
    const [snapshotDescription, setSnapshotDescription] = useState("");
    const [isSaving, setIsSaving] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [expandedChapters, setExpandedChapters] = useState<Set<number>>(
        new Set(),
    );
    const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());

    // Debounced saving indicator (stays visible 1.5s after operation completes)
    const [isSavingIndicator, setIsSavingIndicator] = useState(false);
    const savingDebounceRef = useRef<NodeJS.Timeout | null>(null);

    // Combined raw saving state
    const isOperationInProgress = isSaving || isDeleting || isLoading;

    // Debounce the saving indicator
    useEffect(() => {
        if (isOperationInProgress) {
            // Show indicator immediately when operation starts
            setIsSavingIndicator(true);
            // Clear any pending "done" timer
            if (savingDebounceRef.current) {
                clearTimeout(savingDebounceRef.current);
                savingDebounceRef.current = null;
            }
        } else {
            // Debounce hiding the indicator - wait 1.5s after operation ends
            savingDebounceRef.current = setTimeout(() => {
                setIsSavingIndicator(false);
            }, 1500);
        }

        return () => {
            if (savingDebounceRef.current) {
                clearTimeout(savingDebounceRef.current);
            }
        };
    }, [isOperationInProgress]);

    const handleSaveSnapshot = async () => {
        setIsSaving(true);

        try {
            const csrfToken =
                document
                    .querySelector('meta[name="csrf-token"]')
                    ?.getAttribute("content") || "";
            const url = `/${workspaceId}/projects/${projectId}/editor/version-history/snapshots`;

            console.log("Saving snapshot:", {
                url,
                name: snapshotName,
                description: snapshotDescription,
            });

            const response = await fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                    "X-CSRF-TOKEN": csrfToken,
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: JSON.stringify({
                    name: snapshotName || null,
                    description: snapshotDescription || null,
                }),
            });

            console.log("Response status:", response.status);

            let data;
            try {
                data = await response.json();
                console.log("Response data:", data);
            } catch (jsonError) {
                const text = await response.text();
                console.error("Failed to parse JSON response:", text);
                toast.error(
                    `Server error: ${response.status} ${response.statusText}`,
                );
                setIsSaving(false);
                return;
            }

            if (response.ok && data.success) {
                setLocalSnapshots([data.snapshot, ...localSnapshots]);
                setSnapshotName("");
                setSnapshotDescription("");
                setIsSaveDialogOpen(false);
                toast.success("Snapshot saved successfully!");
            } else {
                console.error("Save failed:", data);
                toast.error(
                    data.error || data.message || "Failed to save snapshot",
                );
            }
        } catch (error) {
            console.error("Save snapshot error:", error);
            toast.error(
                `Failed to save snapshot: ${
                    error instanceof Error ? error.message : "Unknown error"
                }`,
            );
        } finally {
            setIsSaving(false);
        }
    };

    const handleLoadSnapshot = async (snapshotId: string) => {
        if (
            !confirm(
                "Are you sure you want to load this snapshot? This will restore all chapters to their saved state. You will need to refresh the editor to see the changes.",
            )
        ) {
            return;
        }

        setIsLoading(true);

        try {
            const csrfToken =
                document
                    .querySelector('meta[name="csrf-token"]')
                    ?.getAttribute("content") || "";
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/version-history/snapshots/${snapshotId}/load`,
                {
                    method: "POST",
                    headers: {
                        Accept: "application/json",
                        "X-CSRF-TOKEN": csrfToken,
                        "X-Requested-With": "XMLHttpRequest",
                    },
                },
            );

            const data = await response.json();

            if (response.ok && data.success) {
                setLocalChapters(data.chapters);
                toast.success(
                    "Snapshot loaded successfully! Redirecting to editor...",
                );
                // Redirect to main editor so user can see the restored content
                setTimeout(() => {
                    router.visit(
                        route("workspace.projects.editor", {
                            workspace_id: workspaceId,
                            project_id: projectId,
                        }),
                    );
                }, 1500);
            } else {
                console.error("Load snapshot failed:", data);
                toast.error(
                    data.error || data.message || "Failed to load snapshot",
                );
            }
        } catch (error) {
            console.error("Load snapshot error:", error);
            toast.error(
                `Failed to load snapshot: ${
                    error instanceof Error ? error.message : "Unknown error"
                }`,
            );
        } finally {
            setIsLoading(false);
        }
    };

    const handleDeleteSnapshot = async (snapshotId: string) => {
        if (
            !confirm(
                "Are you sure you want to delete this snapshot? This action cannot be undone.",
            )
        ) {
            return;
        }

        setIsDeleting(true);

        try {
            const csrfToken =
                document
                    .querySelector('meta[name="csrf-token"]')
                    ?.getAttribute("content") || "";
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/version-history/snapshots/${snapshotId}`,
                {
                    method: "DELETE",
                    headers: {
                        Accept: "application/json",
                        "X-CSRF-TOKEN": csrfToken,
                        "X-Requested-With": "XMLHttpRequest",
                    },
                },
            );

            const data = await response.json();

            if (response.ok && data.success) {
                setLocalSnapshots(
                    localSnapshots.filter((s) => s.id !== snapshotId),
                );
                toast.success("Snapshot deleted successfully!");
            } else {
                toast.error(data.error || "Failed to delete snapshot");
            }
        } catch (error) {
            toast.error("Failed to delete snapshot");
        } finally {
            setIsDeleting(false);
        }
    };

    const toggleChapter = (chapterOrder: number) => {
        const newExpanded = new Set(expandedChapters);
        if (newExpanded.has(chapterOrder)) {
            newExpanded.delete(chapterOrder);
        } else {
            newExpanded.add(chapterOrder);
        }
        setExpandedChapters(newExpanded);
    };

    const toggleNode = (nodeId: string) => {
        const newExpanded = new Set(expandedNodes);
        if (newExpanded.has(nodeId)) {
            newExpanded.delete(nodeId);
        } else {
            newExpanded.add(nodeId);
        }
        setExpandedNodes(newExpanded);
    };

    const renderVersionTree = (chapter: ChapterVersionInfo) => {
        if (!expandedChapters.has(chapter.order)) {
            return null;
        }

        return (
            <div className="ml-2 space-y-2">
                {chapter.version_tree.map((node, nodeIndex) => (
                    <div
                        key={node.node_id}
                        className="border-l-2 border-gray-200 pl-4"
                    >
                        <div className="flex items-center gap-2 py-2">
                            <button
                                onClick={() => toggleNode(node.node_id)}
                                className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
                            >
                                {expandedNodes.has(node.node_id) ? (
                                    <ChevronDown className="h-4 w-4" />
                                ) : (
                                    <ChevronRight className="h-4 w-4" />
                                )}
                                <span className="font-medium">
                                    Node {nodeIndex + 1}
                                    {node.is_current && (
                                        <span className="ml-2 text-xs text-blue-600 font-normal">
                                            (Current)
                                        </span>
                                    )}
                                </span>
                                {node.is_user_generated && (
                                    <span className="text-xs text-gray-500">
                                        (User)
                                    </span>
                                )}
                            </button>
                            <span className="text-xs text-gray-400">
                                {node.created_at &&
                                    formatDistanceToNow(
                                        new Date(node.created_at),
                                        { addSuffix: true },
                                    )}
                            </span>
                        </div>
                        {expandedNodes.has(node.node_id) && (
                            <div className="ml-6 space-y-1">
                                {node.versions.map((version) => (
                                    <div
                                        key={version.version_index}
                                        className={`p-2 rounded text-sm ${
                                            version.is_current
                                                ? "bg-blue-50 border border-blue-200"
                                                : "bg-gray-50 border border-gray-200"
                                        }`}
                                    >
                                        <div className="flex items-center justify-between mb-1">
                                            <span className="font-medium">
                                                Version {version.version_index}
                                                {version.is_current && (
                                                    <span className="ml-2 text-xs text-blue-600">
                                                        (Current)
                                                    </span>
                                                )}
                                            </span>
                                            <span className="text-xs text-gray-500">
                                                {version.created_at &&
                                                    formatDistanceToNow(
                                                        new Date(
                                                            version.created_at,
                                                        ),
                                                        { addSuffix: true },
                                                    )}
                                            </span>
                                        </div>
                                        <div className="text-xs text-gray-600 mt-1">
                                            {version.content_preview}
                                        </div>
                                        <div className="text-xs text-gray-400 mt-1">
                                            {version.content_length.toLocaleString()}{" "}
                                            characters
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        );
    };

    return (
        <ProjectEditorLayout
            project={project}
            projectId={projectId}
            workspaceId={workspaceId}
            isSaving={isSavingIndicator}
        >
            <Head title="Version History" />

            <div className="w-full h-full flex flex-col bg-gray-50">
                <div className="flex-1 flex gap-4 p-4 overflow-hidden min-h-0">
                    {/* Left Sidebar - Snapshots */}
                    <div className="w-80 flex flex-col bg-white rounded-lg shadow-sm border border-gray-200 min-h-0">
                        <div className="p-4 border-b border-gray-200 shrink-0">
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-lg font-semibold">
                                    Snapshots
                                </h2>
                                <Button
                                    onClick={() => setIsSaveDialogOpen(true)}
                                    size="sm"
                                    className="gap-2"
                                >
                                    <Save className="h-4 w-4" />
                                    Save Current
                                </Button>
                            </div>
                        </div>
                        <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
                            {localSnapshots.length === 0 ? (
                                <div className="text-center text-gray-500 py-8">
                                    <History className="h-12 w-12 mx-auto mb-2 text-gray-300" />
                                    <p>No snapshots yet</p>
                                    <p className="text-sm mt-1">
                                        Save your current state to create one
                                    </p>
                                </div>
                            ) : (
                                localSnapshots.map((snapshot) => (
                                    <Card
                                        key={snapshot.id}
                                        className="hover:shadow-md transition-shadow py-4 gap-4"
                                    >
                                        <CardHeader className="px-4">
                                            <div className="flex items-center justify-between gap-4">
                                                <div className="flex-1 flex-col gap-1">
                                                    <CardTitle className="text-sm font-medium">
                                                        {snapshot.name ||
                                                            "Unnamed Snapshot"}
                                                    </CardTitle>
                                                    {snapshot.description && (
                                                        <CardDescription className="text-xs">
                                                            {
                                                                snapshot.description
                                                            }
                                                        </CardDescription>
                                                    )}
                                                </div>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() =>
                                                        handleDeleteSnapshot(
                                                            snapshot.id,
                                                        )
                                                    }
                                                    className="h-6 w-6 p-0"
                                                >
                                                    <Trash2 className="h-3 w-3" />
                                                </Button>
                                            </div>
                                        </CardHeader>
                                        <CardContent className="px-4 flex flex-col gap-2">
                                            <div className="flex items-center justify-between gap-4 text-xs text-gray-500">
                                                <div className="flex items-center gap-1">
                                                    <Clock className="h-3 w-3" />
                                                    {formatDistanceToNow(
                                                        new Date(
                                                            snapshot.created_at,
                                                        ),
                                                        { addSuffix: true },
                                                    )}
                                                </div>
                                                {snapshot.created_by && (
                                                    <div className="flex items-center gap-1">
                                                        <User className="h-3 w-3" />
                                                        {
                                                            snapshot.created_by
                                                                .name
                                                        }
                                                    </div>
                                                )}
                                            </div>
                                            <Button
                                                onClick={() =>
                                                    handleLoadSnapshot(
                                                        snapshot.id,
                                                    )
                                                }
                                                size="sm"
                                                variant="outline"
                                                className="w-full"
                                                disabled={isLoading}
                                            >
                                                {isLoading ? (
                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                ) : (
                                                    "Load Snapshot"
                                                )}
                                            </Button>
                                        </CardContent>
                                    </Card>
                                ))
                            )}
                        </div>
                    </div>

                    {/* Right Side - Chapter Version Trees */}
                    <div className="flex-1 flex flex-col bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden min-h-0">
                        <div className="p-4 border-b border-gray-200 shrink-0">
                            <h2 className="text-lg font-semibold">
                                Chapter Versions
                            </h2>
                            <p className="text-sm text-gray-500 mt-1">
                                View and navigate through version history for
                                each chapter
                            </p>
                        </div>
                        <div className="flex-1 overflow-y-auto p-4 min-h-0">
                            {localChapters.length === 0 ? (
                                <div className="text-center text-gray-500 py-12">
                                    <History className="h-12 w-12 mx-auto mb-2 text-gray-300" />
                                    <p>No chapters with version history</p>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    {localChapters.map((chapter) => (
                                        <Card
                                            key={chapter.order}
                                            className="hover:shadow-md transition-shadow py-4! gap-4!"
                                        >
                                            <CardHeader className="px-4! gap-4! grid-rows-1!">
                                                <button
                                                    onClick={() =>
                                                        toggleChapter(
                                                            chapter.order,
                                                        )
                                                    }
                                                    className="flex items-center justify-between w-full text-left"
                                                >
                                                    <div className="flex items-center gap-2">
                                                        {expandedChapters.has(
                                                            chapter.order,
                                                        ) ? (
                                                            <ChevronDown className="h-4 w-4 text-gray-400" />
                                                        ) : (
                                                            <ChevronRight className="h-4 w-4 text-gray-400" />
                                                        )}
                                                        <CardTitle className="text-base font-medium">
                                                            {
                                                                chapter.chapter_name
                                                            }
                                                        </CardTitle>
                                                    </div>
                                                    <div className="text-xs text-gray-500">
                                                        {
                                                            chapter
                                                                .navigation_info
                                                                .totalVersions
                                                        }{" "}
                                                        version
                                                        {chapter.navigation_info
                                                            .totalVersions !== 1
                                                            ? "s"
                                                            : ""}
                                                        {" • "}
                                                        Current: v
                                                        {
                                                            chapter
                                                                .navigation_info
                                                                .currentVersionIndex
                                                        }
                                                    </div>
                                                </button>
                                            </CardHeader>
                                            {expandedChapters.has(
                                                chapter.order,
                                            ) && (
                                                <CardContent className="px-4!">
                                                    {chapter.version_tree
                                                        .length === 0 ? (
                                                        <p className="text-sm text-gray-500">
                                                            No version history
                                                        </p>
                                                    ) : (
                                                        renderVersionTree(
                                                            chapter,
                                                        )
                                                    )}
                                                </CardContent>
                                            )}
                                        </Card>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Save Snapshot Dialog */}
            <Dialog open={isSaveDialogOpen} onOpenChange={setIsSaveDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Save Current State</DialogTitle>
                        <DialogDescription>
                            Create a snapshot of all chapters at their current
                            versions. You can restore this state later.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="snapshot-name">
                                Name (optional)
                            </Label>
                            <Input
                                id="snapshot-name"
                                placeholder="e.g., Before major rewrite"
                                value={snapshotName}
                                onChange={(e) =>
                                    setSnapshotName(e.target.value)
                                }
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="snapshot-description">
                                Description (optional)
                            </Label>
                            <Textarea
                                id="snapshot-description"
                                placeholder="Add a note about this snapshot..."
                                value={snapshotDescription}
                                onChange={(e) =>
                                    setSnapshotDescription(e.target.value)
                                }
                                rows={3}
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => {
                                setIsSaveDialogOpen(false);
                                setSnapshotName("");
                                setSnapshotDescription("");
                            }}
                        >
                            Cancel
                        </Button>
                        <Button
                            onClick={handleSaveSnapshot}
                            disabled={isSaving}
                        >
                            {isSaving ? (
                                <>
                                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                    Saving...
                                </>
                            ) : (
                                <>
                                    <Save className="h-4 w-4 mr-2" />
                                    Save Snapshot
                                </>
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </ProjectEditorLayout>
    );
}

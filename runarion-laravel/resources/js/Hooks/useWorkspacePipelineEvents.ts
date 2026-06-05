import { router } from "@inertiajs/react";
import { useEffect, useRef } from "react";
import { toast } from "sonner";
import "@/echo";

export interface WorkspacePipelineEvent {
    workspace_id: string;
    project_id: string;
    run_id: string;
    status: string;
    phase: string;
    is_locked: boolean;
    message?: string;
    should_toast?: boolean;
    timestamp?: string;
}

interface UseWorkspacePipelineEventsOptions {
    workspaceId: string;
    reloadOnly: string[];
    projectId?: string;
    onEvent?: (event: WorkspacePipelineEvent) => void;
}

export function useWorkspacePipelineEvents({
    workspaceId,
    reloadOnly,
    projectId,
    onEvent,
}: UseWorkspacePipelineEventsOptions): void {
    const seenToastKeys = useRef<Set<string>>(new Set());
    const reloadSignature = reloadOnly.join("|");

    useEffect(() => {
        const channel = window.Echo?.private(`workspace.${workspaceId}`);
        channel?.listen(
            ".project.pipeline.lifecycle.updated",
            (event: WorkspacePipelineEvent) => {
                if (projectId && event?.project_id !== projectId) {
                    return;
                }

                if (event?.message && event.should_toast !== false) {
                    const toastKey = [
                        event.run_id,
                        event.status,
                        event.phase,
                        event.is_locked ? "locked" : "unlocked",
                    ].join(":");

                    if (!seenToastKeys.current.has(toastKey)) {
                        seenToastKeys.current.add(toastKey);

                        const notify =
                            event.status === "failed"
                                ? toast.error
                                : event.is_locked
                                  ? toast.info
                                  : toast.success;

                        notify(event.message);
                    }
                }

                onEvent?.(event);

                router.reload({
                    only: reloadOnly,
                });
            },
        );

        return () => {
            window.Echo?.leave(`private-workspace.${workspaceId}`);
        };
    }, [workspaceId, projectId, onEvent, reloadSignature]);
}

import { useState, useRef, useCallback, useEffect } from "react";
import ProjectEditorLayout from "@/Layouts/ProjectEditorLayout";
import { PageProps, Project } from "@/types";
import { Head } from "@inertiajs/react";
import RecordsPanel from "./RecordsPanel";

export default function ProjectEditorPage({
    workspaceId,
    projectId,
    project,
}: PageProps<{
    workspaceId: string;
    projectId: string;
    project: Project;
}>) {
    const [isSaving, setIsSaving] = useState(false);
    const [isIndicatorVisible, setIsIndicatorVisible] = useState(false);
    const indicatorDebounceRef = useRef<NodeJS.Timeout | null>(null);

    // Debounced handler for save state changes - keeps indicator visible for 1.5s after save completes
    const handleSavingChange = useCallback((saving: boolean) => {
        setIsSaving(saving);

        if (saving) {
            // Show indicator immediately when saving starts
            setIsIndicatorVisible(true);
            // Clear any pending "done" timer
            if (indicatorDebounceRef.current) {
                clearTimeout(indicatorDebounceRef.current);
                indicatorDebounceRef.current = null;
            }
        } else {
            // Debounce hiding the indicator - wait 1.5s after saving ends
            indicatorDebounceRef.current = setTimeout(() => {
                setIsIndicatorVisible(false);
            }, 1500);
        }
    }, []);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (indicatorDebounceRef.current) {
                clearTimeout(indicatorDebounceRef.current);
            }
        };
    }, []);

    return (
        <ProjectEditorLayout
            project={project}
            projectId={projectId}
            workspaceId={workspaceId}
            isSaving={isIndicatorVisible}
        >
            <Head title="Project Database" />
            <RecordsPanel
                workspaceId={workspaceId}
                projectId={projectId}
                onSavingChange={handleSavingChange}
            />
        </ProjectEditorLayout>
    );
}

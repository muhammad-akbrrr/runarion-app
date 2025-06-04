import ProjectEditorLayout from "@/Layouts/ProjectEditorLayout";
import { PageProps } from "@/types";
import { Head } from "@inertiajs/react";
import { useEffect, useState } from "react";
import LoadingOverlay from "@/Components/LoadingOverlay";

export default function ProjectEditorPage({
    workspaceId,
    projectId,
    projectName,
    projectData, // Assume projectData contains all initial data from backend
}: PageProps<{
    workspaceId: string;
    projectId: string;
    projectName?: string;
    projectData?: any;
}>) {
    const TOTAL_STEPS = 3;
    const [completedSteps, setCompletedSteps] = useState(0);
    const [loading, setLoading] = useState(true);

    // Simulate async data loading steps
    useEffect(() => {
        if (!loading || projectData) {
            setLoading(false);
            setCompletedSteps(TOTAL_STEPS);
            return;
        }

        let cancelled = false;

        async function fetchAllData() {
            // --- Start of data fetching logic ---

            // Simulate step 1: Fetch project metadata
            await new Promise((resolve) => setTimeout(resolve, 1300));
            setCompletedSteps(1);

            // Simulate step 2: Fetch project files
            await new Promise((resolve) => setTimeout(resolve, 1700));
            setCompletedSteps(2);

            // Simulate step 3: Fetch user permissions
            await new Promise((resolve) => setTimeout(resolve, 1500));
            setCompletedSteps(3);

            // --- End of data fetching logic ---

            setLoading(false);
        }

        setCompletedSteps(0);
        setLoading(true);
        fetchAllData();

        return () => {
            cancelled = true;
        };
    }, [workspaceId, projectId, projectName, projectData]);

    const progress = (completedSteps / TOTAL_STEPS) * 100;

    return (
        <>
            <LoadingOverlay
                visible={loading}
                progress={progress}
                message={`Loading project data (${Math.round(progress)}%)`}
            />
            <div
                style={{
                    visibility: loading ? "hidden" : "visible",
                    opacity: loading ? 0 : 1,
                    transition: "opacity 0.3s",
                }}
            >
                <ProjectEditorLayout
                    projectName={projectName || "Untitled Project"}
                    projectId={projectId}
                    workspaceId={workspaceId}
                >
                    <Head title="Dashboard" />
                    {/* Main content goes here */}
                </ProjectEditorLayout>
            </div>
        </>
    );
}

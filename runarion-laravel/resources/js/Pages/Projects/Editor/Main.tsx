import ProjectEditorLayout from "@/Layouts/ProjectEditorLayout";
import { PageProps } from "@/types";
import { Head } from "@inertiajs/react";

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
    return (
        <ProjectEditorLayout
            projectName={projectName || "Untitled Project"}
            projectId={projectId}
            workspaceId={workspaceId}
        >
            <Head title="Project Editor" />
            {/* Main content goes here */}
        </ProjectEditorLayout>
    );
}

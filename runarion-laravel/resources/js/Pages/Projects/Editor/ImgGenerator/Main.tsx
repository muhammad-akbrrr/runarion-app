import ProjectEditorLayout from "@/Layouts/ProjectEditorLayout";
import { PageProps, Project } from "@/types";
import { Head } from "@inertiajs/react";

export default function ProjectEditorPage({
    workspaceId,
    projectId,
    project,
}: PageProps<{
    workspaceId: string;
    projectId: string;
    project: Project;
}>) {
    return (
        <ProjectEditorLayout
            project={project}
            projectId={projectId}
            workspaceId={workspaceId}
        >
            <Head title="Image Editor" />
            {/* Main content goes here */}
        </ProjectEditorLayout>
    );
}

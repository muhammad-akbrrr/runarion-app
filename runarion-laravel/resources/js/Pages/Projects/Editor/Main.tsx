import ProjectEditorLayout from "@/Layouts/ProjectEditorLayout";
import { PageProps } from "@/types";
import { Head } from "@inertiajs/react";

export default function Dashboard({
    workspaceId,
    projectName,
}: PageProps<{
    workspaceId: string;
    projectName?: string;
}>) {
    return (
        <ProjectEditorLayout>
            <Head title="Dashboard" />

            <div>
                <div className="w-full p-5">
                    {projectName && (
                        <div className="text-lg font-semibold">
                            Project: {projectName}
                        </div>
                    )}
                </div>
            </div>
        </ProjectEditorLayout>
    );
}

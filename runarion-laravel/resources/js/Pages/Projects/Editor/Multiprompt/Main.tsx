import ProjectEditorLayout from "@/Layouts/ProjectEditorLayout";
import { PageProps, Project, ProjectChapter } from "@/types";
import { Head, router } from "@inertiajs/react";
import { ChainBuilder } from "../ChainBuilder/ChainBuilder";
import { useState, useEffect } from "react";

export default function ProjectEditorPage({
    workspaceId,
    projectId,
    project,
}: PageProps<{
    workspaceId: string;
    projectId: string;
    project: Project;
}>) {
    const [chapters, setChapters] = useState<ProjectChapter[]>([]);
    const [projectSettings, setProjectSettings] = useState(project.settings || {});

    useEffect(() => {
        // Load chapters
        fetch(`/${workspaceId}/projects/${projectId}/editor/chapters`)
            .then((res) => res.json())
            .then((data) => {
                if (data.chapters) {
                    setChapters(data.chapters);
                }
            })
            .catch(console.error);
    }, [workspaceId, projectId]);

    // Update local settings when project prop changes (from server)
    useEffect(() => {
        if (project.settings) {
            setProjectSettings(project.settings);
        }
    }, [project.settings]);

    // Get AI model from settings - log for debugging
    const aiModel = projectSettings?.aiModel || project.settings?.aiModel || 'gemini-2.0-flash';
    const authorProfile = projectSettings?.authorProfile || project.settings?.authorProfile;
    
    // Debug logging
    useEffect(() => {
        console.log('Multi-Node: AI Model selection', {
            projectSettings_aiModel: projectSettings?.aiModel,
            project_settings_aiModel: project.settings?.aiModel,
            final_aiModel: aiModel,
            all_project_settings: project.settings,
        });
    }, [projectSettings, project.settings, aiModel]);

    // Callback to apply result to editor - stores in localStorage and navigates
    const handleApplyResult = (text: string) => {
        if (text && text.trim()) {
            // Store result in localStorage for editor to pick up
            localStorage.setItem(`chainbuilder_result_${projectId}`, text);
            localStorage.setItem(`chainbuilder_result_timestamp_${projectId}`, Date.now().toString());
            
            // Navigate to editor
            router.visit(`/${workspaceId}/projects/${projectId}/editor`, {
                preserveScroll: false,
            });
        }
    };

    return (
        <ProjectEditorLayout
            project={project}
            projectId={projectId}
            workspaceId={workspaceId}
        >
            <Head title="Multi-Node Prompt Builder" />
            <div className="w-full h-full" style={{ minHeight: 'calc(100vh - 4rem)' }}>
                <ChainBuilder
                    workspaceId={workspaceId}
                    projectId={projectId}
                    project={project}
                    chapters={chapters}
                    aiModel={aiModel}
                    authorProfile={authorProfile}
                    settings={projectSettings || project.settings || {}}
                    onApplyResult={handleApplyResult}
                />
            </div>
        </ProjectEditorLayout>
    );
}

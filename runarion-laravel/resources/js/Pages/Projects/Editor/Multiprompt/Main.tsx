import ProjectEditorLayout from "@/Layouts/ProjectEditorLayout";
import { PageProps, Project, ProjectChapter } from "@/types";
import { Head, router } from "@inertiajs/react";
import { ChainBuilder } from "./ChainBuilder/ChainBuilder";
import type { GraphTemplate } from "./ChainBuilder/types";
import { useState, useEffect } from "react";
import { http } from "@/Lib/http";
import { toast } from "sonner";

export default function ProjectEditorPage({
    workspaceId,
    projectId,
    project,
    multipromptState,
}: PageProps<{
    workspaceId: string;
    projectId: string;
    project: Project;
    multipromptState?: {
        graph_state?: Record<string, unknown> | null;
        templates?: GraphTemplate[] | null;
    } | null;
}>) {
    const [chapters, setChapters] = useState<ProjectChapter[]>([]);
    const [projectSettings, setProjectSettings] = useState(
        project.settings || {},
    );
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        // Load chapters
        http.get<{ chapters?: ProjectChapter[] }>(
            `/${workspaceId}/projects/${projectId}/editor/chapters`,
        )
            .then(({ data }) => {
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
    const aiModel =
        projectSettings?.aiModel ||
        project.settings?.aiModel ||
        "gemini-2.5-flash";
    const authorProfile =
        projectSettings?.authorProfile || project.settings?.authorProfile;

    // Debug logging
    useEffect(() => {
        console.log("Multi-Node: AI Model selection", {
            projectSettings_aiModel: projectSettings?.aiModel,
            project_settings_aiModel: project.settings?.aiModel,
            final_aiModel: aiModel,
            all_project_settings: project.settings,
        });
    }, [projectSettings, project.settings, aiModel]);

    // Callback to apply result to editor - saves server-side then navigates
    const handleApplyResult = async (text: string) => {
        if (text && text.trim()) {
            try {
                // Save content server-side first (avoids storage size limits)
                const response = await http(
                    `/${workspaceId}/projects/${projectId}/editor/chain-builder/apply-to-story`,
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            Accept: "application/json",
                        },
                        data: {
                            result_text: text,
                            // chapter_order: optional, defaults to last chapter
                        },
                    },
                );

                if (response.status >= 200 && response.status < 300) {
                    // Content saved successfully, navigate to editor
                    router.visit(
                        `/${workspaceId}/projects/${projectId}/editor`,
                        {
                            preserveScroll: false,
                        },
                    );
                } else {
                    const error = response.data.catch(() => ({
                        error: "Unknown error",
                    }));
                    console.error("Failed to apply result:", error);
                    toast.error(
                        `Failed to save content: ${error.error || "Please try again."}`,
                    );
                }
            } catch (error) {
                console.error("Error applying result:", error);
                toast.error("Failed to save content. Please try again.");
            }
        }
    };

    return (
        <ProjectEditorLayout
            project={project}
            projectId={projectId}
            workspaceId={workspaceId}
            isSaving={isLoading}
        >
            <Head title="Multi-Node Prompt Builder" />
            <div
                className="w-full h-full"
                style={{ minHeight: "calc(100vh - 4rem)" }}
            >
                <ChainBuilder
                    workspaceId={workspaceId}
                    projectId={projectId}
                    project={project}
                    chapters={chapters}
                    persistedGraphState={multipromptState?.graph_state || null}
                    persistedTemplates={multipromptState?.templates || []}
                    aiModel={aiModel}
                    authorProfile={authorProfile}
                    settings={projectSettings || project.settings || {}}
                    onApplyResult={handleApplyResult}
                    onLoadingChange={setIsLoading}
                />
            </div>
        </ProjectEditorLayout>
    );
}

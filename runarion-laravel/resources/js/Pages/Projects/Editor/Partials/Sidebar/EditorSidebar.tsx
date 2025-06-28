import type React from "react";
import {
    Sidebar,
    SidebarContent,
    SidebarProvider,
} from "@/Components/ui/sidebar";
import { SidebarTabs } from "./SidebarTabs";

interface EditorSidebarProps {
    children: React.ReactNode;
    currentPreset: string;
    authorProfile: string;
    aiModel: string;
    memory: string;
    storyGenre: string;
    storyTone: string;
    storyPov: string;
    temperature: number;
    repetitionPenalty: number;
    outputLength: number;
    minOutputToken: number;
    topP: number;
    tailFree: number;
    topA: number;
    topK: number;
    phraseBias: Array<{ [key: string]: number }>;
    bannedPhrases: string[];
    stopSequences: string[];
    onSettingChange: (key: string, value: any) => void;
    workspaceId?: string;
    projectId?: string;
}

export function EditorSidebar({ 
    children,
    currentPreset,
    authorProfile,
    aiModel,
    memory,
    storyGenre,
    storyTone,
    storyPov,
    temperature,
    repetitionPenalty,
    outputLength,
    minOutputToken,
    topP,
    tailFree,
    topA,
    topK,
    phraseBias,
    bannedPhrases,
    stopSequences,
    onSettingChange,
    workspaceId, 
    projectId 
}: EditorSidebarProps) {
    return (
        <SidebarProvider
            defaultOpen={true}
            style={{ "--sidebar-width": "22rem" } as React.CSSProperties}
            className="flex flex-col flex-grow h-full min-h-0"
        >
            <div
                className="
                    flex flex-row w-full flex-grow min-h-0 relative
                "
            >
                {/* Main content area - takes remaining space */}
                <div
                    className="
                        flex-1 flex flex-col flex-grow
                        min-w-0 min-h-0
                        p-4 gap-4
                    "
                >
                    {children}
                </div>

                {/* Right sidebar - takes its natural width */}
                <Sidebar
                    side="right"
                    collapsible="icon"
                    className="absolute flex flex-col h-auto"
                >
                    <SidebarContent className="overflow-y-auto overflow-x-hidden group-data-[collapsible=icon]:overflow-hidden">
                        <SidebarTabs 
                            currentPreset={currentPreset}
                            authorProfile={authorProfile}
                            aiModel={aiModel}
                            memory={memory}
                            storyGenre={storyGenre}
                            storyTone={storyTone}
                            storyPov={storyPov}
                            temperature={temperature}
                            repetitionPenalty={repetitionPenalty}
                            outputLength={outputLength}
                            minOutputToken={minOutputToken}
                            topP={topP}
                            tailFree={tailFree}
                            topA={topA}
                            topK={topK}
                            phraseBias={phraseBias}
                            bannedPhrases={bannedPhrases}
                            stopSequences={stopSequences}
                            onSettingChange={onSettingChange}
                            workspaceId={workspaceId}
                            projectId={projectId}
                        />
                    </SidebarContent>
                </Sidebar>
            </div>
        </SidebarProvider>
    );
}

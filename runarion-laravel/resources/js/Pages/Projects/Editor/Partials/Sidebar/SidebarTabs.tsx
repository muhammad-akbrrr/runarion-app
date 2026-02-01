import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/Components/ui/tabs";
import { SidebarTrigger, useSidebar } from "@/Components/ui/sidebar";
import { Grid3X3 } from "lucide-react";
import { SidebarContent } from "./SidebarMainContent";
import { SidebarSettingsProps } from "@/types/project";
import AuditorTab from "@/Pages/Projects/Editor/Partials/Sidebar/AuditorTab";
import AdvisorTab from "@/Pages/Projects/Editor/Partials/Sidebar/AdvisorTab";

export function SidebarTabs({
    settings,
    onSettingChange,
    workspaceId,
    projectId,
    authorStyles,
    onApplyStoryFix,
    onSavingChange,
}: SidebarSettingsProps) {
    const { state } = useSidebar();
    const isCollapsed = state === "collapsed";

    return (
        <div className="w-full flex flex-col flex-grow">
            {/* Wrap everything in a single Tabs component */}
            <Tabs
                defaultValue="settings"
                className="w-full flex flex-col flex-grow"
            >
                {/* Sticky header with trigger and tabs */}
                <div className="sticky top-0 z-10 bg-white border-b">
                    <div className="flex items-center p-3">
                        <SidebarTrigger className="h-6 w-6 p-0 mr-4 z-50 flex-shrink-0">
                            <Grid3X3 className="h-4 w-4" />
                        </SidebarTrigger>

                        {/* Tabs aligned to center vertically with opacity animation */}
                        <TabsList
                            className={`grid w-full grid-cols-3 flex-1 !h-auto !p-1 transition-opacity duration-200 ease-in-out ${
                                isCollapsed
                                    ? "opacity-0 pointer-events-none"
                                    : "opacity-100 pointer-events-auto"
                            }`}
                        >
                            <TabsTrigger
                                value="settings"
                                className="text-sm px-2 py-1 !shadow-none"
                            >
                                Settings
                            </TabsTrigger>
                            <TabsTrigger
                                value="advisor"
                                className="text-sm px-2 py-1 !shadow-none"
                            >
                                Advisor
                            </TabsTrigger>
                            <TabsTrigger
                                value="auditor"
                                className="text-sm px-2 py-1 !shadow-none"
                            >
                                Auditor
                            </TabsTrigger>
                        </TabsList>
                    </div>
                </div>

                {/* Scrollable content area with opacity animation and conditional overflow */}
                <div
                    className={`flex-grow transition-opacity duration-200 ease-in-out ${
                        isCollapsed
                            ? "opacity-0 pointer-events-none"
                            : "opacity-100 pointer-events-auto"
                    }`}
                >
                    {/* Settings tab content - shows the AI configuration */}
                    <TabsContent value="settings" className="mt-0">
                        <SidebarContent 
                            settings={settings}
                            onSettingChange={onSettingChange}
                            workspaceId={workspaceId}
                            projectId={projectId}
                            authorStyles={authorStyles}
                        />
                    </TabsContent>

                    {/* Advisor tab content */}
                    <TabsContent value="advisor" className="mt-0 h-[calc(100vh-120px)]">
                        {workspaceId && projectId && (
                            <AdvisorTab
                                workspaceId={workspaceId}
                                projectId={projectId}
                                onApplyEdit={onApplyStoryFix}
                                settings={settings}
                                onSettingChange={onSettingChange}
                                onSavingChange={onSavingChange}
                            />
                        )}
                    </TabsContent>

                    {/* Auditor tab content */}
                    <TabsContent value="auditor" className="mt-0">
                        {workspaceId && projectId && (
                            <AuditorTab
                                workspaceId={workspaceId}
                                projectId={projectId}
                                onApplyStoryFix={onApplyStoryFix}
                                settings={settings}
                                onSettingChange={onSettingChange}
                            />
                        )}
                    </TabsContent>
                </div>
            </Tabs>
        </div>
    );
}

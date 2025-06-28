import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/Components/ui/tabs";
import { SidebarTrigger, useSidebar } from "@/Components/ui/sidebar";
import { Grid3X3 } from "lucide-react";
import { SidebarContent } from "./SidebarMainContent";

interface SidebarTabsProps {
    projectSettings?: any;
    workspaceId?: string;
    projectId?: string;
}

export function SidebarTabs({ 
    projectSettings = {}, 
    workspaceId, 
    projectId 
}: SidebarTabsProps) {
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
                                value="summarize"
                                className="text-sm px-2 py-1 !shadow-none"
                            >
                                Summarize
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
                            projectSettings={projectSettings}
                            workspaceId={workspaceId}
                            projectId={projectId}
                        />
                    </TabsContent>

                    {/* Advisor tab content */}
                    <TabsContent value="advisor" className="mt-0">
                        <div className="p-3">
                            <p className="text-sm text-gray-500">
                                Advisor content will go here
                            </p>
                        </div>
                    </TabsContent>

                    {/* Summarize tab content */}
                    <TabsContent value="summarize" className="mt-0">
                        <div className="p-3">
                            <p className="text-sm text-gray-500">
                                Summarize content will go here
                            </p>
                        </div>
                    </TabsContent>
                </div>
            </Tabs>
        </div>
    );
}

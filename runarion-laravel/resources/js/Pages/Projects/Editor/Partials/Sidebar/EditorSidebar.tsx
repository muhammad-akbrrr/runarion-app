import type React from "react";
import {
    Sidebar,
    SidebarContent,
    SidebarProvider,
} from "@/Components/ui/sidebar";
import { SidebarTabs } from "./SidebarTabs";

interface EditorSidebarProps {
    children: React.ReactNode;
}

export function EditorSidebar({ children }: EditorSidebarProps) {
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
                        <SidebarTabs />
                    </SidebarContent>
                </Sidebar>
            </div>
        </SidebarProvider>
    );
}

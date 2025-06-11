import { Link } from "@inertiajs/react";
import {
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarMenu,
    SidebarMenuItem,
    SidebarMenuButton,
} from "@/Components/ui/sidebar";
import {
    Bot,
    Cloud,
    DollarSign,
    LayoutGrid,
    Settings,
    User as SingleUser,
    Users,
    LucideProps,
} from "lucide-react";
import { RouteParams } from "../../../../vendor/tightenco/ziggy/src/js";

interface SidebarItem {
    label: string;
    icon: React.ForwardRefExoticComponent<
        Omit<LucideProps, "ref"> & React.RefAttributes<SVGSVGElement>
    >;
    path: string;
    param?: RouteParams<string>;
}

interface SettingsSidebarProps {
    workspaceId: string;
}

export default function SettingsSidebar({ workspaceId }: SettingsSidebarProps) {
    const workspaceSettingsItems: SidebarItem[] = [
        { label: "General", icon: Settings, path: "workspace.edit" },
        { label: "Members", icon: Users, path: "workspace.edit.member" },
        {
            label: "Cloud Storage",
            icon: Cloud,
            path: "workspace.edit.cloud-storage",
        },
        { label: "LLM Integration", icon: Bot, path: "workspace.edit.llm" },
        {
            label: "Plans & Billing",
            icon: DollarSign,
            path: "workspace.edit.billing",
        },
    ].map((item) => ({
        ...item,
        param: { workspace_id: workspaceId },
    }));

    const mySettingsItems: SidebarItem[] = [
        { label: "Profile", icon: SingleUser, path: "profile.edit" },
        { label: "Workspaces", icon: LayoutGrid, path: "workspace.index" },
    ];

    const renderSidebarGroup = (name: string, items: SidebarItem[]) => (
        <SidebarGroup>
            <SidebarGroupLabel>{name}</SidebarGroupLabel>
            <SidebarGroupContent>
                <SidebarMenu>
                    {items.map((item) => (
                        <SidebarMenuItem key={item.label}>
                            <SidebarMenuButton
                                asChild
                                isActive={
                                    item.path
                                        ? route().current(item.path)
                                        : false
                                }
                            >
                                <Link
                                    href={
                                        item.path
                                            ? route(item.path, item.param)
                                            : "#"
                                    }
                                    onClick={(e) => {
                                        if (!item.path) {
                                            e.preventDefault();
                                        }
                                    }}
                                >
                                    <item.icon className="h-4 w-4" />
                                    <span>{item.label}</span>
                                </Link>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                    ))}
                </SidebarMenu>
            </SidebarGroupContent>
        </SidebarGroup>
    );

    return (
        <>
            {renderSidebarGroup("Workspace Settings", workspaceSettingsItems)}
            {renderSidebarGroup("My Settings", mySettingsItems)}
        </>
    );
}

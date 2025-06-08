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
    Settings,
    Shield,
    Database,
    Activity,
    LucideProps,
} from "lucide-react";

interface SidebarItem {
    label: string;
    icon: React.ForwardRefExoticComponent<
        Omit<LucideProps, "ref"> & React.RefAttributes<SVGSVGElement>
    >;
    path: string;
    param?: {
        id?: string;
        project_id?: string;
        workspace_id?: string;
        [key: string]: string | undefined;
    };
}

interface ProjectSettingsSidebarProps {
    workspaceId: string;
    projectId: string;
}

export default function ProjectSettingsSidebar({
    workspaceId,
    projectId,
}: ProjectSettingsSidebarProps) {
    const projectSettingsItems: SidebarItem[] = [
        { label: "General", icon: Settings, path: "workspace.projects.edit" },
        {
            label: "Access",
            icon: Shield,
            path: "workspace.projects.edit.access",
        },
        {
            label: "Backups",
            icon: Database,
            path: "workspace.projects.edit.backups",
        },
        {
            label: "Activity",
            icon: Activity,
            path: "workspace.projects.edit.activity",
        },
    ].map((item) => ({
        ...item,
        param: { project_id: projectId, workspace_id: workspaceId },
    }));

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

    return <>{renderSidebarGroup("Project Settings", projectSettingsItems)}</>;
}

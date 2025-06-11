import { Avatar, AvatarFallback, AvatarImage } from "@/Components/ui/avatar";
import {
    Breadcrumb,
    BreadcrumbItem,
    BreadcrumbLink,
    BreadcrumbList,
    BreadcrumbPage,
    BreadcrumbSeparator,
} from "@/Components/ui/breadcrumb";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/Components/ui/dropdown-menu";
import {
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarHeader,
    SidebarInset,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarProvider,
    SidebarRail,
} from "@/Components/ui/sidebar";
import { Link, router, usePage } from "@inertiajs/react";
import {
    ChevronDown,
    ChevronLeft,
    FileText,
    Folder,
    Home,
    Library,
    LucideProps,
    Settings,
    Star,
} from "lucide-react";
import React, { PropsWithChildren } from "react";
import { RouteParams } from "../../../vendor/tightenco/ziggy/src/js";
import LoadingOverlay from "@/Components/LoadingOverlay";
import SettingsSidebar from "./Partials/SettingsSidebar";
import ProjectSettingsSidebar from "./Partials/ProjectSettingsSidebar";

export interface BreadcrumbItem {
    label: string;
    path: string;
    param?: RouteParams<string>;
}

interface SidebarItem {
    label: string;
    icon: React.ForwardRefExoticComponent<
        Omit<LucideProps, "ref"> & React.RefAttributes<SVGSVGElement>
    >;
    path: string;
    param?: RouteParams<string>;
}

export default function AuthenticatedLayout({
    breadcrumbs,
    children,
}: PropsWithChildren<{
    breadcrumbs: BreadcrumbItem[];
}>) {
    const { auth, workspaces, workspace_switching } = usePage().props;
    const user = auth.user;
    const workspaceId = user.last_workspace_id;
    const projectId = route().params.project_id as string | undefined;

    const workspaceName = workspaces.find(
        (workspace) => workspace.id === workspaceId
    )?.name;

    const [loading, setLoading] = React.useState(false);
    const [completedSteps, setCompletedSteps] = React.useState(0);
    const TOTAL_STEPS = 3;
    const progress = (completedSteps / TOTAL_STEPS) * 100;

    // Effect to handle workspace switching animation
    React.useEffect(() => {
        if (workspace_switching) {
            const simulateLoading = async () => {
                setLoading(true);
                setCompletedSteps(0);

                // Simulate step 1
                await new Promise((resolve) => setTimeout(resolve, 800));
                setCompletedSteps(1);

                // Simulate step 2
                await new Promise((resolve) => setTimeout(resolve, 700));
                setCompletedSteps(2);

                // Simulate step 3
                await new Promise((resolve) => setTimeout(resolve, 600));
                setCompletedSteps(3);

                setLoading(false);
            };

            simulateLoading();
        }
    }, [workspace_switching]);

    const handleWorkspaceSelect = (id: string) => {
        if (id === workspaceId) return;
        const path = window.location.pathname;
        const newPath = path.replace(workspaceId, id);
        router.get(newPath);
    };

    const userInitials = user.name
        .split(" ")
        .map((n: string) => n[0])
        .join("")
        .substring(0, 2)
        .toUpperCase();

    const dashboardItems: SidebarItem[] = [
        {
            label: "Home",
            icon: Home,
            path: "workspace.dashboard",
            param: { id: workspaceId },
        },
        {
            label: "Projects",
            icon: Library,
            path: "workspace.projects",
            param: { id: workspaceId },
        },
        { label: "File Manager", icon: Folder, path: "" },
    ];

    const dummyFavoriteItems: SidebarItem[] = [
        { label: "The Three Musketeers" },
        { label: "The Count of Monte Cristo" },
    ].map((item) => ({
        ...item,
        icon: Star,
        path: "",
    }));

    const openSettings =
        route().current("workspace.edit*") ||
        route().current("profile.edit") ||
        route().current("workspace.index");

    const openProjectSettings = route().current("workspace.projects.edit*");

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
        <SidebarProvider>
            <LoadingOverlay
                visible={loading}
                progress={progress}
                message={`Switching workspace... (${Math.round(progress)}%)`}
            />
            <Sidebar className="flex" collapsible="offcanvas">
                <SidebarHeader>
                    {openSettings || openProjectSettings ? (
                        <div
                            className="w-full h-12 flex items-center gap-2 rounded hover:bg-gray-100 cursor-pointer"
                            onClick={() =>
                                router.get(
                                    openProjectSettings
                                        ? route("workspace.projects", {
                                              workspace_id: workspaceId,
                                          })
                                        : route("workspace.dashboard", {
                                              workspace_id: workspaceId,
                                          })
                                )
                            }
                        >
                            <ChevronLeft className="h-4 w-4 ml-1" />
                            <div>
                                {openProjectSettings
                                    ? "All Projects"
                                    : "Back to Dashboard"}
                            </div>
                        </div>
                    ) : (
                        <DropdownMenu>
                            <DropdownMenuTrigger className="w-full h-12 rounded hover:bg-gray-100 cursor-pointer">
                                <div className="flex items-center gap-2 px-2">
                                    <Avatar>
                                        <AvatarImage
                                            src={user.avatar_url || undefined}
                                            alt={user.name}
                                            className="object-cover object-center"
                                        />
                                        <AvatarFallback>
                                            {userInitials}
                                        </AvatarFallback>
                                    </Avatar>
                                    <div className="flex-1 overflow-hidden text-left">
                                        <p className="text-sm font-medium leading-none truncate">
                                            {user.name}
                                        </p>
                                        <p className="text-sm text-muted-foreground truncate">
                                            {workspaceName}
                                        </p>
                                    </div>
                                    <ChevronDown className="h-4 w-4" />
                                </div>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent
                                align="start"
                                className="w-[240px]"
                            >
                                {workspaces.map((workspace) => (
                                    <DropdownMenuItem
                                        key={workspace.id}
                                        onClick={() =>
                                            handleWorkspaceSelect(workspace.id)
                                        }
                                    >
                                        {workspace.name}
                                    </DropdownMenuItem>
                                ))}
                            </DropdownMenuContent>
                        </DropdownMenu>
                    )}
                </SidebarHeader>

                <SidebarContent>
                    {!openSettings && !openProjectSettings && (
                        <>
                            {renderSidebarGroup("Dashboard", dashboardItems)}
                            {renderSidebarGroup(
                                "Favorites",
                                dummyFavoriteItems
                            )}
                        </>
                    )}

                    {openSettings && (
                        <SettingsSidebar workspaceId={workspaceId} />
                    )}

                    {openProjectSettings && projectId && (
                        <ProjectSettingsSidebar
                            workspaceId={workspaceId}
                            projectId={projectId}
                        />
                    )}
                </SidebarContent>

                {!openSettings && (
                    <SidebarFooter className="border-t border-border p-4">
                        <SidebarMenu>
                            <SidebarMenuItem>
                                <SidebarMenuButton asChild>
                                    <Link
                                        href={route("workspace.edit", {
                                            workspace_id: workspaceId,
                                        })}
                                    >
                                        <Settings className="h-4 w-4" />
                                        <span>Settings</span>
                                    </Link>
                                </SidebarMenuButton>
                                <SidebarMenuButton asChild>
                                    <Link href="#">
                                        <FileText className="h-4 w-4" />
                                        <span>Documentation</span>
                                    </Link>
                                </SidebarMenuButton>
                            </SidebarMenuItem>
                        </SidebarMenu>
                    </SidebarFooter>
                )}
            </Sidebar>
            <SidebarRail />
            <SidebarInset className="flex flex-col w-full">
                <div className="flex justify-between items-center px-2.5 py-2.5">
                    {breadcrumbs.length > 0 && (
                        <Breadcrumb className="mx-2">
                            <BreadcrumbList>
                                {breadcrumbs.map((item, index) => (
                                    <React.Fragment key={index}>
                                        <BreadcrumbItem className="text-base">
                                            {index ===
                                            breadcrumbs.length - 1 ? (
                                                <BreadcrumbPage>
                                                    {item.label}
                                                </BreadcrumbPage>
                                            ) : (
                                                <BreadcrumbLink
                                                    href={
                                                        item.path
                                                            ? route(
                                                                  item.path,
                                                                  item.param
                                                              )
                                                            : "#"
                                                    }
                                                    onClick={(e) => {
                                                        if (!item.path) {
                                                            e.preventDefault();
                                                        }
                                                    }}
                                                >
                                                    {item.label}
                                                </BreadcrumbLink>
                                            )}
                                        </BreadcrumbItem>
                                        {index < breadcrumbs.length - 1 && (
                                            <BreadcrumbSeparator />
                                        )}
                                    </React.Fragment>
                                ))}
                            </BreadcrumbList>
                        </Breadcrumb>
                    )}
                    <DropdownMenu>
                        <DropdownMenuTrigger className="p-1 rounded hover:bg-gray-100 cursor-pointer">
                            <div className="flex items-center gap-2">
                                <Avatar>
                                    <AvatarImage
                                        src={user.avatar_url || undefined}
                                        alt={user.name}
                                        className="object-cover object-center"
                                    />
                                    <AvatarFallback>
                                        {userInitials}
                                    </AvatarFallback>
                                </Avatar>
                                <div className="flex-1 overflow-hidden text-left">
                                    <p className="text-sm font-medium leading-none truncate">
                                        {user.name}
                                    </p>
                                </div>
                                <ChevronDown className="h-4 w-4 mr-1" />
                            </div>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-56">
                            <DropdownMenuItem
                                onClick={() =>
                                    router.get(route("profile.edit"))
                                }
                            >
                                Profile
                            </DropdownMenuItem>
                            <DropdownMenuItem
                                onClick={() => router.post(route("logout"))}
                            >
                                Log Out
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>

                <main className="flex-1 w-full p-5 bg-gray-100">
                    {children}
                </main>
            </SidebarInset>
        </SidebarProvider>
    );
}

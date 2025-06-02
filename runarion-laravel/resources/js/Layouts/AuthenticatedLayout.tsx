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
    Bot,
    ChevronDown,
    ChevronLeft,
    Cloud,
    DollarSign,
    FileText,
    Folder,
    Home,
    LayoutGrid,
    Library,
    LucideProps,
    Settings,
    Star,
    User as UserIcon,
    Users,
} from "lucide-react";
import React, { PropsWithChildren } from "react";
import { ParameterValue } from "../../../vendor/tightenco/ziggy/src/js";

export interface BreadcrumbItem {
    label: string;
    path: string;
    param?: ParameterValue;
}

interface SidebarItem {
    label: string;
    icon: React.ForwardRefExoticComponent<
        Omit<LucideProps, "ref"> & React.RefAttributes<SVGSVGElement>
    >;
    path: string;
    param?: ParameterValue;
}

export default function AuthenticatedLayout({
    breadcrumbs,
    children,
}: PropsWithChildren<{
    breadcrumbs: BreadcrumbItem[];
}>) {
    const { auth, workspaces } = usePage().props;
    const user = auth.user;
    const workspaceId = user.last_workspace_id;

    const workspaceName = workspaces.find(
        (workspace) => workspace.id === workspaceId
    )?.name;

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
            param: workspaceId,
        },
        {
            label: "Projects",
            icon: Library,
            path: "workspace.projects",
            param: workspaceId,
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
        param: workspaceId,
    }));

    const mySettingsItems: SidebarItem[] = [
        { label: "Profile", icon: UserIcon, path: "profile.edit" },
        { label: "Workspaces", icon: LayoutGrid, path: "workspace.index" },
    ];

    const openSettings = [...workspaceSettingsItems, ...mySettingsItems].some(
        (item) => route().current(item.path, item.param)
    );

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
            <Sidebar className="flex" collapsible="offcanvas">
                <SidebarHeader>
                    {openSettings ? (
                        <div
                            className="w-full h-12 flex items-center gap-2 rounded hover:bg-gray-100 cursor-pointer"
                            onClick={() =>
                                router.get(
                                    route("workspace.dashboard", workspaceId)
                                )
                            }
                        >
                            <ChevronLeft className="h-4 w-4 ml-1" />
                            <div>Back to Dashboard</div>
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
                    {!openSettings &&
                        renderSidebarGroup("Dashboard", dashboardItems)}

                    {!openSettings &&
                        renderSidebarGroup("Favorites", dummyFavoriteItems)}

                    {openSettings &&
                        renderSidebarGroup(
                            "Workspace Settings",
                            workspaceSettingsItems
                        )}

                    {openSettings &&
                        renderSidebarGroup("My Settings", mySettingsItems)}
                </SidebarContent>

                {!openSettings && (
                    <SidebarFooter className="border-t border-border p-4">
                        <SidebarMenu>
                            <SidebarMenuItem>
                                <SidebarMenuButton asChild>
                                    <Link
                                        href={route(
                                            "workspace.edit",
                                            workspaceId
                                        )}
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

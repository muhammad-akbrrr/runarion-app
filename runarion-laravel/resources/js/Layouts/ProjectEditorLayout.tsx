import * as React from "react";
import {
    Menu,
    SquareStack,
    Database,
    Network,
    Puzzle,
    Layers,
    Settings,
    FileText,
    Search,
    MessageCircle,
    Share,
    Check,
    Loader2,
    FolderPlus,
    Upload,
    UserPlus,
    Folder,
    User,
    LayoutDashboard,
    HelpCircle,
    Keyboard,
    X,
} from "lucide-react";
import { Link, router } from "@inertiajs/react";
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
    SidebarHeader,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarInset,
    SidebarProvider,
} from "@/Components/ui/sidebar";
import { Dialog, DialogContent } from "@/Components/ui/dialog";
import { Input } from "@/Components/ui/input";
import { Button } from "@/Components/ui/button";
import LoadingOverlay from "@/Components/LoadingOverlay";
import { Project } from "@/types";

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

interface NavigationItem {
    icon: React.ComponentType<{ className?: string }>;
    label: string;
    isActive: boolean;
}

interface EditableTextProps {
    initialValue: string;
    onSave?: (
        value: string,
        setIsSaving: (b: boolean) => void,
        setIsSaved: (b: boolean) => void
    ) => Promise<void>;
}

interface CommandDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

interface ActionItem {
    icon: React.ComponentType<{ className?: string }>;
    label: string;
}

// ============================================================================
// NAVIGATION DATA
// ============================================================================

const navigationItems: NavigationItem[] = [
    { icon: SquareStack, label: "Pages", isActive: true },
    { icon: Database, label: "Database", isActive: false },
    { icon: Network, label: "API", isActive: false },
    { icon: Puzzle, label: "Components", isActive: false },
    { icon: Layers, label: "Layers", isActive: false },
];

const footerItems: ActionItem[] = [
    { icon: Settings, label: "Settings" },
    { icon: FileText, label: "Documentation" },
];

const commandActions: ActionItem[] = [
    { icon: FolderPlus, label: "Create a new folder" },
    { icon: Upload, label: "Upload new document" },
    { icon: UserPlus, label: "Invite to project" },
];

const quickLinks: ActionItem[] = [
    { icon: Folder, label: "File Manager" },
    { icon: User, label: "Profile" },
    { icon: LayoutDashboard, label: "Dashboard" },
    { icon: HelpCircle, label: "Support" },
    { icon: Keyboard, label: "Keyboard Shortcuts" },
];

// ============================================================================
// EDITABLE TEXT COMPONENT
// ============================================================================

function EditableText({ initialValue, onSave }: EditableTextProps) {
    const [value, setValue] = React.useState(initialValue);
    const [isEditing, setIsEditing] = React.useState(false);
    const [isSaving, setIsSaving] = React.useState(false);
    const [isSaved, setIsSaved] = React.useState(true);

    const handleSave = async () => {
        if (value === initialValue) {
            setIsEditing(false);
            return;
        }

        setIsSaving(true);
        setIsSaved(false);

        try {
            await onSave?.(value, setIsSaving, setIsSaved);
            setIsSaved(true);
            setTimeout(() => setIsSaved(true), 2000); // Show saved state for 2 seconds
        } catch (error) {
            console.error("Failed to save:", error);
        } finally {
            setIsSaving(false);
            setIsEditing(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter") {
            handleSave();
        } else if (e.key === "Escape") {
            setValue(initialValue);
            setIsEditing(false);
        }
    };

    React.useEffect(() => {
        if (value !== initialValue) {
            setIsSaved(false);
        }
    }, [value, initialValue]);

    if (isEditing) {
        return (
            <Input
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onBlur={handleSave}
                onKeyDown={handleKeyDown}
                className="h-8 w-auto min-w-60 shadow-none outline-none border-none bg-transparent px-2 text-base font-medium focus-visible:ring-0"
                autoFocus
            />
        );
    }

    return (
        <div className="flex items-center gap-2">
            <button
                onClick={() => setIsEditing(true)}
                className="text-base font-medium hover:bg-accent hover:text-accent-foreground rounded px-1 py-0.5 transition-colors"
            >
                {value}
            </button>
            {isSaving ? (
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            ) : isSaved ? (
                <Check className="h-4 w-4 text-green-600" />
            ) : (
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            )}
        </div>
    );
}

// ============================================================================
// COMMAND DIALOG COMPONENT
// ============================================================================

function CommandDialog({ open, onOpenChange }: CommandDialogProps) {
    const [search, setSearch] = React.useState("");

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl p-0 [&>button]:hidden">
                <div className="p-4 pb-2">
                    <div className="relative">
                        <Input
                            placeholder="Search"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="pr-8"
                            autoFocus
                        />
                        <Button
                            variant="ghost"
                            size="sm"
                            className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6 p-0"
                            onClick={() => onOpenChange(false)}
                        >
                            <X className="h-4 w-4" />
                        </Button>
                    </div>
                </div>

                <div className="px-4 pb-4">
                    <div className="space-y-4">
                        <div>
                            <h3 className="mb-2 text-sm font-medium text-muted-foreground">
                                Actions
                            </h3>
                            <div className="space-y-1 mx-[-0.5rem]">
                                {commandActions.map((action) => (
                                    <Button
                                        key={action.label}
                                        variant="ghost"
                                        className="w-full justify-start h-8 px-2"
                                    >
                                        <action.icon className="mr-2 h-4 w-4" />
                                        {action.label}
                                    </Button>
                                ))}
                            </div>
                        </div>

                        <div>
                            <h3 className="mb-2 text-sm font-medium text-muted-foreground">
                                Quick Links
                            </h3>
                            <div className="space-y-1 mx-[-0.5rem]">
                                {quickLinks.map((link) => (
                                    <Button
                                        key={link.label}
                                        variant="ghost"
                                        className="w-full justify-start h-8 px-2"
                                    >
                                        <link.icon className="mr-2 h-4 w-4" />
                                        {link.label}
                                    </Button>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}

// ============================================================================
// MAIN PROJECT LAYOUT COMPONENT
// ============================================================================

interface ProjectEditorLayoutProps {
    children?: React.ReactNode;
    project: Project;
    projectId: string;
    workspaceId: string;
}

export default function ProjectEditorLayout({
    children,
    project,
    projectId,
    workspaceId,
}: ProjectEditorLayoutProps) {
    // Loader logic (similar to AuthenticatedLayout)
    const TOTAL_STEPS = 3;
    const [loading, setLoading] = React.useState(true);
    const [completedSteps, setCompletedSteps] = React.useState(0);
    const prevProjectId = React.useRef<string | null>(null);
    const progress = (completedSteps / TOTAL_STEPS) * 100;

    React.useEffect(() => {
        // Only play loader if projectId changes (from null or from one value to another)
        if (prevProjectId.current === projectId) {
            setLoading(false);
            setCompletedSteps(TOTAL_STEPS);
            return;
        }
        prevProjectId.current = projectId;
        let cancelled = false;
        async function simulateProjectLoading() {
            setLoading(true);
            setCompletedSteps(0);
            // Simulate step 1
            await new Promise((resolve) => setTimeout(resolve, 800));
            if (cancelled) return;
            setCompletedSteps(1);
            // Simulate step 2
            await new Promise((resolve) => setTimeout(resolve, 700));
            if (cancelled) return;
            setCompletedSteps(2);
            // Simulate step 3
            await new Promise((resolve) => setTimeout(resolve, 600));
            if (cancelled) return;
            setCompletedSteps(3);
            setLoading(false);
        }
        simulateProjectLoading();
        return () => {
            cancelled = true;
        };
    }, [projectId]);

    // Command palette state
    const [commandOpen, setCommandOpen] = React.useState(false);

    // Keyboard shortcut for command dialog
    React.useEffect(() => {
        const down = (e: KeyboardEvent) => {
            if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                setCommandOpen((open) => !open);
            }
        };
        document.addEventListener("keydown", down);
        return () => document.removeEventListener("keydown", down);
    }, []);

    // Save handler for EditableText
    const handleSave = async (
        value: string,
        setIsSaving: (b: boolean) => void,
        setIsSaved: (b: boolean) => void
    ) => {
        setIsSaving(true);
        router.patch(
            route("editor.project.updateName", {
                workspace_id: workspaceId,
                project_id: projectId,
            }),
            {
                name: value,
            },
            {
                preserveScroll: true,
                onSuccess: () => {
                    setIsSaving(false);
                    setIsSaved(true);
                },
                onError: () => {
                    setIsSaving(false);
                },
            }
        );
    };

    return (
        <>
            <LoadingOverlay
                visible={loading}
                progress={progress}
                message={`Loading project... (${Math.round(progress)}%)`}
            />
            <div
                style={{
                    visibility: loading ? "hidden" : "visible",
                    opacity: loading ? 0 : 1,
                    transition: "opacity 0.3s",
                }}
            >
                <SidebarProvider defaultOpen={false}>
                    <Sidebar collapsible="icon" className="border-r bg-white">
                        {/* Sidebar Header: Menu Dropdown */}
                        <SidebarHeader className="border-b flex items-center justify-center">
                            <SidebarMenu>
                                <SidebarMenuItem>
                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <div className="m-0.5 w-8 h-8 flex items-center justify-center p-2 rounded-md cursor-pointer hover:bg-sidebar-accent hover:text-sidebar-accent-foreground">
                                                <Menu className="size-5" />
                                            </div>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent
                                            align="start"
                                            className="w-48"
                                        >
                                            <DropdownMenuItem>
                                                <Link
                                                    href={route(
                                                        "workspace.projects",
                                                        {
                                                            workspace_id:
                                                                workspaceId,
                                                        }
                                                    )}
                                                >
                                                    <span>
                                                        Back to dashboard
                                                    </span>
                                                </Link>
                                            </DropdownMenuItem>
                                            <DropdownMenuItem>
                                                <Link
                                                    href={route(
                                                        "workspace.projects.edit",
                                                        {
                                                            workspace_id:
                                                                workspaceId,
                                                            project_id:
                                                                projectId,
                                                        }
                                                    )}
                                                >
                                                    <span>
                                                        Project settings
                                                    </span>
                                                </Link>
                                            </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </SidebarMenuItem>
                            </SidebarMenu>
                        </SidebarHeader>

                        {/* Sidebar Navigation (unchanged) */}
                        <SidebarContent className="py-4 flex flex-col items-center">
                            <SidebarMenu className="flex flex-col items-center">
                                {navigationItems.map((item) => (
                                    <SidebarMenuItem key={item.label}>
                                        <SidebarMenuButton
                                            isActive={item.isActive}
                                            tooltip={item.label}
                                            className="w-8 h-8 flex items-center justify-center p-0"
                                        >
                                            <item.icon className="size-5" />
                                        </SidebarMenuButton>
                                    </SidebarMenuItem>
                                ))}
                            </SidebarMenu>
                        </SidebarContent>

                        {/* Sidebar Footer (unchanged) */}
                        <SidebarFooter className="border-t py-4 flex flex-col items-center">
                            <SidebarMenu className="flex flex-col items-center">
                                {footerItems.map((item) => (
                                    <SidebarMenuItem key={item.label}>
                                        <SidebarMenuButton
                                            tooltip={item.label}
                                            className="w-8 h-8 flex items-center justify-center p-0"
                                        >
                                            <item.icon className="size-5" />
                                        </SidebarMenuButton>
                                    </SidebarMenuItem>
                                ))}
                            </SidebarMenu>
                        </SidebarFooter>
                    </Sidebar>
                    <SidebarInset className="flex flex-col w-full">
                        {/* Header area: TopBar features */}
                        <div className="grid grid-cols-3 items-center px-4 py-2 border-b bg-white">
                            {/* Left: Project title */}
                            <div className="flex items-center">
                                <EditableText
                                    initialValue={project.name}
                                    onSave={handleSave}
                                />
                            </div>
                            {/* Center: Search/Command palette */}
                            <div className="flex justify-center">
                                <Button
                                    variant="outline"
                                    className="w-96 justify-between items-center text-muted-foreground h-9 px-2"
                                    onClick={() => setCommandOpen(true)}
                                >
                                    <div className="flex items-center gap-2">
                                        <Search className="h-4 w-4" />
                                        Search
                                    </div>
                                    <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1 font-mono text-sm font-medium text-muted-foreground opacity-100">
                                        <span className="text-xs">⌘</span>K
                                    </kbd>
                                </Button>
                            </div>
                            {/* Right: Actions */}
                            <div className="flex justify-end gap-2">
                                <Button variant="outline">
                                    <MessageCircle className="h-4 w-4" />
                                    Comment
                                </Button>
                                <Button>
                                    <Share className="h-4 w-4" />
                                    Share
                                </Button>
                            </div>
                        </div>
                        {/* Command Palette Dialog */}
                        <CommandDialog
                            open={commandOpen}
                            onOpenChange={setCommandOpen}
                        />
                        {/* Main content area */}
                        <main className="flex-1 w-full bg-gray-100">
                            {children}
                        </main>
                    </SidebarInset>
                </SidebarProvider>
            </div>
        </>
    );
}

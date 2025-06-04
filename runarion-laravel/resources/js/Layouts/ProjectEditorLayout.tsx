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
    onSave?: (value: string) => Promise<void>;
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

/**
 * @param initialValue - The initial text value
 * @param onSave - Async function called when saving (optional)
 */
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
            await onSave?.(value);
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
                className="h-8 w-auto min-w-32 border-none bg-transparent p-0 text-base font-medium focus-visible:ring-0"
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
}

export default function ProjectEditorLayout({
    children,
}: ProjectEditorLayoutProps) {
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
    const handleSave = async (value: string) => {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        console.log("Saved:", value);
    };

    return (
        <SidebarProvider defaultOpen={false}>
            <Sidebar collapsible="icon" className="border-r bg-white">
                {/* Sidebar Header: Menu Dropdown (unchanged) */}
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
                                        <span>Back to dashboard</span>
                                    </DropdownMenuItem>
                                    <DropdownMenuItem>
                                        <span>Project settings</span>
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </SidebarMenuItem>
                    </SidebarMenu>
                </SidebarHeader>

                {/* Sidebar Navigation (unchanged) */}
                <SidebarContent className="py-4 flex flex-col items-center">
                    <SidebarMenu className="gap-4 flex flex-col items-center">
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
                    <SidebarMenu className="gap-4 flex flex-col items-center">
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
                {/* Header area: TopBar features (unchanged) */}
                <div className="flex justify-between items-center px-4 py-2 border-b bg-white">
                    {/* Left: Project title */}
                    <div className="flex items-center">
                        <EditableText
                            initialValue="Draft Project #1"
                            onSave={handleSave}
                        />
                    </div>
                    {/* Center: Search/Command palette */}
                    <div className="flex justify-center">
                        <Button
                            variant="outline"
                            className="w-64 justify-between items-center text-muted-foreground h-9 px-2"
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
                            <MessageCircle className="mr-2 h-4 w-4" />
                            Comment
                        </Button>
                        <Button>
                            <Share className="mr-2 h-4 w-4" />
                            Share
                        </Button>
                    </div>
                </div>
                {/* Command Palette Dialog (unchanged) */}
                <CommandDialog
                    open={commandOpen}
                    onOpenChange={setCommandOpen}
                />
                {/* Main content area */}
                <main className="flex-1 w-full bg-gray-100">{children}</main>
            </SidebarInset>
        </SidebarProvider>
    );
}

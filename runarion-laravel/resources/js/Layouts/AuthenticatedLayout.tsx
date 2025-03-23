import { PropsWithChildren } from "react";
import ApplicationLogo from "@/Components/application-logo";
import { Link } from "@inertiajs/react";
import { Button } from "@/Components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/Components/ui/sheet";
import { Menu } from "lucide-react";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/Components/ui/dropdown-menu";

export default function Authenticated({
    user,
    header,
    children,
}: PropsWithChildren<{ user: any; header?: React.ReactNode }>) {
    return (
        <div className="min-h-screen bg-background">
            <nav className="border-b">
                <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                    <div className="flex h-16 justify-between">
                        <div className="flex flex-row items-center justify-start">
                            <div className="flex shrink-0 items-center">
                                <Link href="/">
                                    <ApplicationLogo className="block h-9 w-auto fill-current text-muted-foreground" />
                                </Link>
                            </div>

                            <div className="hidden space-x-8 sm:-my-px sm:ml-10 sm:flex">
                                <Link
                                    href={route("dashboard")}
                                    className="text-sm text-muted-foreground hover:text-foreground"
                                >
                                    Dashboard
                                </Link>
                            </div>
                        </div>

                        <div className="hidden sm:ml-6 sm:flex sm:items-center">
                            <div className="ml-3 relative">
                                <DropdownMenu>
                                    <DropdownMenuTrigger>
                                        <Button
                                            variant="ghost"
                                            className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-muted-foreground hover:text-foreground focus:outline-none transition ease-in-out duration-150"
                                        >
                                            {user.name}
                                            <svg
                                                className="ml-2 -mr-0.5 h-4 w-4"
                                                xmlns="http://www.w3.org/2000/svg"
                                                viewBox="0 0 20 20"
                                                fill="currentColor"
                                            >
                                                <path
                                                    fillRule="evenodd"
                                                    d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                                                    clipRule="evenodd"
                                                />
                                            </svg>
                                        </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent
                                        align="end"
                                        className="w-56"
                                    >
                                        <DropdownMenuItem>
                                            <Link
                                                href={route("profile.edit")}
                                                className="w-full text-left"
                                            >
                                                Profile
                                            </Link>
                                        </DropdownMenuItem>
                                        <DropdownMenuItem>
                                            <Link
                                                href={route("logout")}
                                                method="post"
                                                as="button"
                                                className="w-full text-left"
                                            >
                                                Log Out
                                            </Link>
                                        </DropdownMenuItem>
                                    </DropdownMenuContent>
                                </DropdownMenu>
                            </div>
                        </div>

                        <div className="-mr-2 flex items-center sm:hidden">
                            <Sheet>
                                <SheetTrigger asChild>
                                    <Button variant="ghost" size="icon">
                                        <Menu className="h-6 w-6" />
                                    </Button>
                                </SheetTrigger>
                                <SheetContent className="flex flex-col gap-2 p-4 pt-12">
                                    <Link
                                        href={route("dashboard")}
                                        className="w-full text-left text-sm text-muted-foreground hover:text-foreground"
                                    >
                                        Dashboard
                                    </Link>
                                    <Link
                                        href={route("profile.edit")}
                                        className="w-full text-left text-sm text-muted-foreground hover:text-foreground"
                                    >
                                        Profile
                                    </Link>
                                    <Link
                                        href={route("logout")}
                                        method="post"
                                        as="button"
                                        className="w-full text-left text-sm text-muted-foreground hover:text-foreground"
                                    >
                                        Log Out
                                    </Link>
                                </SheetContent>
                            </Sheet>
                        </div>
                    </div>
                </div>
            </nav>

            {header && (
                <header className="bg-background shadow">
                    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
                        {header}
                    </div>
                </header>
            )}

            <main>{children}</main>
        </div>
    );
}

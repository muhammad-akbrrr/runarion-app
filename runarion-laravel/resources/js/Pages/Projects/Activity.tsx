import { Button } from "@/Components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/Components/ui/card";
import { Input } from "@/Components/ui/input";
import { Separator } from "@/Components/ui/separator";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps, Project } from "@/types";
import { Head } from "@inertiajs/react";
import {
    DropdownMenu,
    DropdownMenuTrigger,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuCheckboxItem,
} from "@/Components/ui/dropdown-menu";
import { ChevronDown, ArrowUpDown } from "lucide-react";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/Components/ui/table";
import {
    ColumnDef,
    flexRender,
    getCoreRowModel,
    getPaginationRowModel,
    getSortedRowModel,
    SortingState,
    useReactTable,
} from "@tanstack/react-table";
import { useState } from "react";

interface Props
    extends PageProps<{
        workspaceId: string;
        projectId: string;
        project: Project;
    }> {}

type Activity = {
    id: string;
    date: string;
    time: string;
    user: string;
    email: string;
    role: string;
    severity: string;
    event: string;
};

const data: Activity[] = [
    {
        id: "1",
        date: "October 5th, 2025",
        time: "3:00:00 PM",
        user: "John Doe",
        email: "john@example.com",
        role: "Admin",
        severity: "Info",
        event: "Updated project settings",
    },
    {
        id: "2",
        date: "October 4th, 2025",
        time: "1:15:22 PM",
        user: "Jane Smith",
        email: "jane@example.com",
        role: "Member",
        severity: "Warning",
        event: "Created a new backup",
    },
];

const columns: ColumnDef<Activity>[] = [
    {
        accessorKey: "date",
        header: ({ column }) => {
            return (
                <Button
                    variant="ghost"
                    onClick={() =>
                        column.toggleSorting(column.getIsSorted() === "asc")
                    }
                >
                    Date
                    <ArrowUpDown className="ml-2 h-4 w-4" />
                </Button>
            );
        },
        cell: ({ row }) => (
            <div>
                <div>{row.getValue("date")}</div>
                <div className="text-xs text-muted-foreground">
                    {row.original.time}
                </div>
            </div>
        ),
    },
    {
        accessorKey: "user",
        header: "User",
        cell: ({ row }) => (
            <div>
                <div>{row.getValue("user")}</div>
                <div className="text-xs text-muted-foreground">
                    {row.original.email}
                </div>
            </div>
        ),
    },
    {
        accessorKey: "role",
        header: "Role",
    },
    {
        accessorKey: "severity",
        header: "Severity",
    },
    {
        accessorKey: "event",
        header: "Activity Event",
    },
];

export default function ProjectActivity({
    workspaceId,
    projectId,
    project,
}: Props) {
    // Sorting state
    const [sorting, setSorting] = useState<SortingState>([]);
    const [sortRole, setSortRole] = useState(false);
    const [sortSeverity, setSortSeverity] = useState(false);
    const [sortEvent, setSortEvent] = useState(false);

    const table = useReactTable({
        data,
        columns,
        getCoreRowModel: getCoreRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        getSortedRowModel: getSortedRowModel(),
        onSortingChange: setSorting,
        state: {
            sorting,
        },
    });

    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Project Settings", path: "workspace.projects.edit" },
        { label: "Activity", path: "workspace.projects.edit.activity" },
    ].map((item) => ({
        ...item,
        param: { project_id: projectId, workspace_id: workspaceId },
    }));

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Project Activity" />

            <Card className="w-full h-full gap-0">
                <CardHeader>
                    <CardTitle className="text-2xl">Audit Logs</CardTitle>
                </CardHeader>
                <Separator
                    className="mt-2 mb-6 mx-6"
                    style={{ width: "auto" }}
                />
                <CardContent className="flex flex-col gap-4">
                    {/* Sort and Search Form */}
                    <form className="flex flex-row gap-2 items-stretch justify-between">
                        <DropdownMenu>
                            <DropdownMenuTrigger>
                                <Button
                                    variant="outline"
                                    className="bg-white flex flex-row gap-2 items-center justify-start"
                                >
                                    Sort by
                                    <ChevronDown className="h-4 w-4" />
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="start">
                            <DropdownMenuCheckboxItem
                                checked={sortRole}
                                onCheckedChange={setSortRole}
                            >
                                Role
                            </DropdownMenuCheckboxItem>
                            <DropdownMenuCheckboxItem
                                checked={sortSeverity}
                                onCheckedChange={setSortSeverity}
                            >
                                Severity
                            </DropdownMenuCheckboxItem>
                            <DropdownMenuCheckboxItem
                                checked={sortEvent}
                                onCheckedChange={setSortEvent}
                            >
                                Activity
                            </DropdownMenuCheckboxItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                        <Input
                            type="text"
                            placeholder="Search for activity"
                            className="lg:w-3xs md:w-56 sm:w-48 bg-white"
                        />
                    </form>

                    {/* Activity Table */}
                    <div className="rounded-md border w-full">
                        <Table>
                            <TableHeader>
                                {table.getHeaderGroups().map((headerGroup) => (
                                    <TableRow key={headerGroup.id}>
                                        {headerGroup.headers.map((header) => (
                                            <TableHead key={header.id}>
                                                {header.isPlaceholder
                                                    ? null
                                                    : flexRender(
                                                          header.column
                                                              .columnDef.header,
                                                          header.getContext()
                                                      )}
                                            </TableHead>
                                        ))}
                                    </TableRow>
                                ))}
                            </TableHeader>
                            <TableBody>
                                {table.getRowModel().rows?.length ? (
                                    table.getRowModel().rows.map((row) => (
                                        <TableRow key={row.id}>
                                            {row
                                                .getVisibleCells()
                                                .map((cell) => (
                                                    <TableCell key={cell.id}>
                                                        {flexRender(
                                                            cell.column
                                                                .columnDef.cell,
                                                            cell.getContext()
                                                        )}
                                                    </TableCell>
                                                ))}
                                        </TableRow>
                                    ))
                                ) : (
                                    <TableRow>
                                        <TableCell
                                            colSpan={columns.length}
                                            className="h-24 text-center"
                                        >
                                            No results.
                                        </TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </Table>
                    </div>

                    {/* Pagination */}
                    <div className="flex items-center justify-between mt-2">
                        <div className="text-sm text-muted-foreground">
                            Showing{" "}
                            {table.getState().pagination.pageIndex *
                                table.getState().pagination.pageSize +
                                1}{" "}
                            to{" "}
                            {Math.min(
                                (table.getState().pagination.pageIndex + 1) *
                                    table.getState().pagination.pageSize,
                                table.getFilteredRowModel().rows.length
                            )}{" "}
                            of {table.getFilteredRowModel().rows.length}{" "}
                            activities
                        </div>
                        <div className="flex items-center gap-2">
                            <Button
                                variant="outline"
                                onClick={() => table.previousPage()}
                                disabled={!table.getCanPreviousPage()}
                            >
                                Previous
                            </Button>
                            <Button
                                onClick={() => table.nextPage()}
                                disabled={!table.getCanNextPage()}
                            >
                                Next
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </AuthenticatedLayout>
    );
}

import { Card, CardContent, CardHeader, CardTitle } from "@/Components/ui/card";
import { Progress } from "@/Components/ui/progress";
import { Separator } from "@/Components/ui/separator";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";
import { Head } from "@inertiajs/react";

interface UsageBreakdownItem {
    label: string;
    percentage: number;
}

interface UsagePayload {
    usedPercentage: number;
    remainingPercentage: number;
    daysLeft: number | null;
    featureBreakdown: UsageBreakdownItem[];
    projectBreakdown: UsageBreakdownItem[];
    periodStartAt: string | null;
    periodEndAt: string | null;
}

export default function Usage({
    workspaceId,
    workspaceName,
    usage,
}: PageProps<{
    workspaceId: string;
    workspaceName: string;
    isUserAdmin: boolean;
    isUserOwner: boolean;
    usage: UsagePayload;
}>) {
    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Workspace Settings", path: "workspace.edit" },
        { label: "Usage", path: "workspace.edit.usage" },
    ].map((item) => ({
        ...item,
        param: { workspace_id: workspaceId },
    }));

    const featureBreakdown = usage.featureBreakdown.slice(0, 5);
    const projectBreakdown = usage.projectBreakdown.slice(0, 5);

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Workspace Usage" />

            <div className="space-y-6">
                <Card className="w-full h-full gap-0">
                    <CardHeader>
                        <CardTitle className="text-2xl">
                            Workspace Usage
                        </CardTitle>
                    </CardHeader>
                    <Separator
                        className="mt-2 mb-4 mx-6"
                        style={{ width: "auto" }}
                    />
                    <CardContent className="space-y-4">
                        <div className="rounded-md bg-slate-50 border border-slate-400 p-4">
                            <div className="flex items-start justify-between gap-4">
                                <div>
                                    <p className="text-sm text-muted-foreground">
                                        Current monthly usage
                                    </p>
                                    <p className="text-4xl font-semibold tracking-tight">
                                        {usage.usedPercentage.toFixed(1)}%
                                    </p>
                                    <p className="mt-1 text-sm text-muted-foreground">
                                        {workspaceName} has{" "}
                                        {usage.remainingPercentage.toFixed(1)}%{" "}
                                        remaining this cycle.
                                    </p>
                                </div>
                                <div className="text-right text-sm text-muted-foreground">
                                    <p>
                                        {usage.daysLeft === null
                                            ? "Billing window pending"
                                            : `${usage.daysLeft} day${usage.daysLeft === 1 ? "" : "s"} left`}
                                    </p>
                                    {usage.periodEndAt && (
                                        <p>
                                            Resets by{" "}
                                            {new Date(
                                                usage.periodEndAt,
                                            ).toLocaleDateString()}
                                        </p>
                                    )}
                                </div>
                            </div>
                            <Progress
                                value={usage.usedPercentage}
                                className="mt-4 h-2"
                            />
                        </div>

                        <div className="grid gap-4 md:grid-cols-3">
                            <Card className="rounded-md bg-slate-50 border border-slate-400 shadow-none py-4 gap-4">
                                <CardHeader className="px-4">
                                    <CardTitle className="text-base">
                                        Used
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="px-4">
                                    <p className="text-3xl font-semibold">
                                        {usage.usedPercentage.toFixed(1)}%
                                    </p>
                                </CardContent>
                            </Card>
                            <Card className="rounded-md bg-slate-50 border border-slate-400 shadow-none py-4 gap-4">
                                <CardHeader className="px-4">
                                    <CardTitle className="text-base">
                                        Remaining
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="px-4">
                                    <p className="text-3xl font-semibold">
                                        {usage.remainingPercentage.toFixed(1)}%
                                    </p>
                                </CardContent>
                            </Card>
                            <Card className="rounded-md bg-slate-50 border border-slate-400 shadow-none py-4 gap-4">
                                <CardHeader className="px-4">
                                    <CardTitle className="text-base">
                                        Window
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="px-4">
                                    <p className="text-3xl font-semibold">
                                        {usage.daysLeft === null
                                            ? "Pending"
                                            : `${usage.daysLeft}d`}
                                    </p>
                                </CardContent>
                            </Card>
                        </div>
                    </CardContent>
                </Card>

                <div className="grid gap-6 lg:grid-cols-2 items-start">
                    <Card className="gap-4">
                        <CardHeader>
                            <CardTitle className="text-lg">
                                Usage by feature
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {featureBreakdown.length > 0 ? (
                                featureBreakdown.map((item) => (
                                    <div key={item.label} className="space-y-2">
                                        <div className="flex items-center justify-between text-sm">
                                            <span className="font-medium capitalize">
                                                {item.label.replaceAll(
                                                    "_",
                                                    " ",
                                                )}
                                            </span>
                                            <span className="text-muted-foreground">
                                                {item.percentage.toFixed(1)}%
                                            </span>
                                        </div>
                                        <Progress
                                            value={item.percentage}
                                            className="h-2"
                                        />
                                    </div>
                                ))
                            ) : (
                                <p className="text-sm text-muted-foreground">
                                    No billable usage has been recorded for this
                                    period yet.
                                </p>
                            )}
                        </CardContent>
                    </Card>

                    <Card className="gap-4">
                        <CardHeader>
                            <CardTitle className="text-lg">
                                Usage per project
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {projectBreakdown.length > 0 ? (
                                projectBreakdown.map((item) => (
                                    <div key={item.label} className="space-y-2">
                                        <div className="flex items-center justify-between text-sm">
                                            <span className="font-medium">
                                                {item.label}
                                            </span>
                                            <span className="text-muted-foreground">
                                                {item.percentage.toFixed(1)}%
                                            </span>
                                        </div>
                                        <Progress
                                            value={item.percentage}
                                            className="h-2"
                                        />
                                    </div>
                                ))
                            ) : (
                                <p className="text-sm text-muted-foreground">
                                    Project-level usage will appear after
                                    billable workspace activity is recorded.
                                </p>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </AuthenticatedLayout>
    );
}

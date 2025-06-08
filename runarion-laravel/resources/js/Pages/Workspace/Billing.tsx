import { Button } from "@/Components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/Components/ui/card";
import { Separator } from "@/Components/ui/separator";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";
import { Head } from "@inertiajs/react";
import { CircleCheck, Info } from "lucide-react";

export default function Billing({
    workspaceId,
    isUserAdmin,
    isUserOwner,
}: PageProps<{
    workspaceId: string;
    isUserAdmin: boolean;
    isUserOwner: boolean;
}>) {
    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Workspace Settings", path: "workspace.edit" },
        { label: "Plans & Billing", path: "workspace.edit.billing" },
    ].map((item) => ({
        ...item,
        param: { workspace_id: workspaceId },
    }));

    const planDetails = {
        name: "Starter Plan (Yearly)",
        description: "$32 per member-month. Billed yearly.",
        features: [
            "Feature 1 ...",
            "Feature 2 ...",
            "Feature 3 ...",
            "Feature 4 ...",
        ],
    };

    const billingData: Record<string, string> = {
        nextPayment: "05 October, 2026",
        billingCycle: "Yearly Payment",
        totalSeats: "50 Seats",
        totalPayment: "$19,200",
    };

    const billingLabels = [
        { label: "Next Payment", value: "nextPayment" },
        { label: "Billing Cycle", value: "billingCycle" },
        { label: "Total Seats", value: "totalSeats" },
        { label: "Total Payment", value: "totalPayment" },
    ];

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Plans & Billing" />

            <Card className="w-full h-full gap-0">
                <CardHeader>
                    <CardTitle className="text-2xl">
                        Manage Plans & Billing
                    </CardTitle>
                </CardHeader>
                <Separator
                    className="mt-2 mb-4 mx-6"
                    style={{ width: "auto" }}
                />
                <CardContent>
                    <div className="flex justify-between items-center bg-slate-50 border border-slate-400 p-4 rounded-md mb-4 text-slate-700">
                        <div className="flex gap-2 items-center">
                            <Info className="h-5 w-5" />
                            <p>
                                {`Your plan will be charged again on ${billingData.nextPayment}`}
                            </p>
                        </div>
                        <Button variant="default">Reactivate</Button>
                    </div>

                    <div className="flex justify-between bg-slate-50 border border-slate-400 rounded-md p-4 mb-6">
                        <div className="w-full flex flex-col gap-1">
                            <p>{planDetails.name}</p>
                            <p>{planDetails.description}</p>
                        </div>
                        <div className="w-full flex flex-col gap-1">
                            <div>Included in the plan:</div>
                            {planDetails.features.map((feature, index) => (
                                <div
                                    key={index}
                                    className="flex gap-1 items-center"
                                >
                                    <CircleCheck className="h-4 w-4" />
                                    <p>{feature}</p>
                                </div>
                            ))}
                        </div>
                    </div>

                    <Separator className="mb-6" />

                    <div className="mb-4">Billing</div>
                    <div className="grid grid-cols-4 gap-4 mb-6">
                        {billingLabels.map((item) => (
                            <div key={item.label}>
                                <p className="text-slate-500">{item.label}</p>
                                <p className="text-slate-700">
                                    {billingData[item.value] || ""}
                                </p>
                            </div>
                        ))}
                    </div>

                    <Separator className="mb-6" />

                    <div className="mb-4">
                        Manage your billing email address, payment method, and
                        view invoices with your account email.
                    </div>
                    <Button variant="secondary">Manage Billing</Button>
                </CardContent>
            </Card>
        </AuthenticatedLayout>
    );
}

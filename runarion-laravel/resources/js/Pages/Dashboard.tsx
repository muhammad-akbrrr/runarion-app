import { Card, CardContent, CardHeader, CardTitle } from "@/Components/ui/card";
import AuthenticatedLayout, {
    BreadcrumbItem,
} from "@/Layouts/AuthenticatedLayout";
import { Head } from "@inertiajs/react";

export default function Dashboard() {
    const breadcrumbs: BreadcrumbItem[] = [
        { label: "Dashboard", path: "dashboard" },
        { label: "Home", path: "dashboard" },
    ];

    return (
        <AuthenticatedLayout breadcrumbs={breadcrumbs}>
            <Head title="Dashboard" />

            <div>
                <div className="w-full">
                    <Card>
                        <CardHeader>
                            <CardTitle>Welcome to your Dashboard</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <p className="text-foreground">You're logged in!</p>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </AuthenticatedLayout>
    );
}

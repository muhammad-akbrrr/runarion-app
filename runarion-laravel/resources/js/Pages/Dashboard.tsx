// resources/js/Pages/Dashboard.tsx

import React from "react";
import { Head, usePage } from "@inertiajs/react";
import { Card, CardContent, CardHeader, CardTitle } from "@/Components/ui/card";
import AuthenticatedLayout, { BreadcrumbItem } from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";

type Props = {
  workspaceId: string;
  storages: string[];
  filesByProvider: Record<string, string[]>;
};

export default function Dashboard() {
  const { workspaceId } = usePage<PageProps<Props>>().props;

  const breadcrumbs: BreadcrumbItem[] = [
    { label: "Dashboard", path: "workspace.dashboard" },
    { label: "Home", path: "workspace.dashboard" },
  ].map((item) => ({
    ...item,
    param: { workspace_id: workspaceId },
  }));

  return (
    <AuthenticatedLayout breadcrumbs={breadcrumbs}>
      <Head title="Dashboard" />

      <div className="space-y-6">
        {/* Welcome card */}
        <Card>
          <CardHeader>
            <CardTitle>Welcome to your Dashboard</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-foreground">You're logged in!</p>
          </CardContent>
        </Card>
      </div>
    </AuthenticatedLayout>
  );
}

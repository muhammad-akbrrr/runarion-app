// resources/js/Pages/FileManager/Index.tsx

import React from "react";
import { Head, usePage } from "@inertiajs/react";
import { Card, CardContent, CardHeader, CardTitle } from "@/Components/ui/card";
import AuthenticatedLayout, { BreadcrumbItem } from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";
import { Folder } from "lucide-react";

type Props = {
  workspaceId: string;
  workspaceName: string;
};

export default function FileManager() {
  const { workspaceId, workspaceName } = usePage<PageProps<Props>>().props;

  const breadcrumbs: BreadcrumbItem[] = [
    { label: "Dashboard", path: "workspace.dashboard" },
    { label: "File Manager", path: "workspace.files" },
  ].map((item) => ({
    ...item,
    param: { workspace_id: workspaceId },
  }));

  return (
    <AuthenticatedLayout breadcrumbs={breadcrumbs}>
      <Head title="File Manager" />

      <div className="space-y-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-2xl font-bold">File Manager</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center space-x-4 rounded-md border p-4">
              <Folder className="h-8 w-8 text-blue-500" />
              <div>
                <p className="text-sm font-medium leading-none">Current Workspace</p>
                <p className="text-sm text-muted-foreground">{workspaceName}</p>
              </div>
            </div>
            
            <div className="mt-6">
              <p className="text-muted-foreground">
                This is the file manager page for workspace: <strong>{workspaceName}</strong>
              </p>
              <p className="text-muted-foreground mt-2">
                Workspace ID: <code>{workspaceId}</code>
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Placeholder for future file manager components */}
        <Card>
          <CardHeader>
            <CardTitle>Files</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">
              The file manager functionality will be implemented here.
            </p>
          </CardContent>
        </Card>
      </div>
    </AuthenticatedLayout>
  );
}

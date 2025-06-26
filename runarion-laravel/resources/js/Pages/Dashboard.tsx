// resources/js/Pages/Dashboard.tsx

import React, { useEffect, useRef } from "react";
import { Head, Link, usePage, router } from "@inertiajs/react";
import { Card, CardContent, CardHeader, CardTitle } from "@/Components/ui/card";
import AuthenticatedLayout, { BreadcrumbItem } from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";

type Props = {
  workspaceId: string;
  storages: string[];
  filesByProvider: Record<string, string[]>;
};

export default function Dashboard() {
  const { workspaceId, storages, filesByProvider } =
    usePage<PageProps<Props>>().props;

  const prevFilesRef = useRef(filesByProvider);

  function loadFiles(provider: string) {
    router.get(
      route("workspace.dashboard.files", {
        workspace_id: workspaceId,
        provider,
      }),
      {},
      {
        only: ["filesByProvider"],
        preserveState: true,
        preserveScroll: true,
      }
    );
  }

  useEffect(() => {
    if (prevFilesRef.current !== filesByProvider) {
      console.log("Files updated:", filesByProvider);
      prevFilesRef.current = filesByProvider;
    }
  }, [filesByProvider]);

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

        {storages.map((provider) => {
          const list = filesByProvider[provider];

          return (
            <Card key={provider}>
              <CardHeader>
                <CardTitle className="capitalize">
                  {provider.replace("_", " ")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {/* show Load Files button until we have data */}
                {list === undefined && (
                  <button
                    onClick={() => loadFiles(provider)}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Load Files
                  </button>
                )}

                {/* once loaded, display list or empty message */}
                {Array.isArray(list) && (
                  list.length > 0 ? (
                    <ul className="list-disc list-inside mt-4">
                      {list.map((path) => (
                        <li key={path}>
                          <Link
                            href={`/${workspaceId}/settings/cloud-storage/${provider}/files/download/${encodeURIComponent(path)}`}
                            className="text-blue-600 hover:underline"
                          >
                            {path}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-4 text-gray-500">
                      No files in {provider.replace("_", " ")}.
                    </p>
                  )
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </AuthenticatedLayout>
  );
}

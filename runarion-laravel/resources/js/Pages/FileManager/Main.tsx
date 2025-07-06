import React, { useState } from "react";
import { Head, usePage } from "@inertiajs/react";
import AuthenticatedLayout, { BreadcrumbItem } from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";
import { FileManagerProps } from "@/types/files";

// Import partials
import StorageCards from "./Partials/StorageCards";
import AuthorStyleCard from "./Partials/AuthorStyleCard";
import ProjectsTable from "./Partials/ProjectsTable";
import AuthorStyleDialog from "./Partials/AuthorStyleDialog";

export default function FileManager() {
  const { workspaceId, workspaceName, storageProviders, authorStyles, projects } = usePage<PageProps<FileManagerProps>>().props;
  const [isAuthorStyleDialogOpen, setIsAuthorStyleDialogOpen] = useState(false);

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
        {/* Storage Cards Section */}
        <StorageCards storageProviders={storageProviders} />

        {/* Author Styles Section */}
        <AuthorStyleCard 
          authorStyles={authorStyles} 
          onAddClick={() => setIsAuthorStyleDialogOpen(true)} 
        />

        {/* Projects Table Section */}
        <ProjectsTable 
          projects={projects} 
          workspaceId={workspaceId} 
        />
      </div>

      {/* Author Style Dialog */}
      <AuthorStyleDialog 
        open={isAuthorStyleDialogOpen} 
        onClose={() => setIsAuthorStyleDialogOpen(false)} 
        authorStyles={authorStyles}
      />
    </AuthenticatedLayout>
  );
}

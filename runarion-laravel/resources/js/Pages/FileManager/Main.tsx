import React, { useState, useEffect } from "react";
import { Head, usePage, router } from "@inertiajs/react";
import AuthenticatedLayout, { BreadcrumbItem } from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";
import { FileManagerProps, AuthorStyle } from "@/types/files";

// Import partials
import StorageCards from "./Partials/StorageCards";
import AuthorStyleCard from "./Partials/AuthorStyleCard";
import ProjectsTable from "./Partials/ProjectsTable";
import AuthorStyleDialog from "./Partials/AuthorStyleDialog";
import AuthorStyleEditDialog from "./Partials/AuthorStyleEditDialog";
import AuthorStyleDeleteDialog from "./Partials/AuthorStyleDeleteDialog";

export default function FileManager() {
  const { workspaceId, workspaceName, storageProviders, authorStyles, projects } = usePage<PageProps<FileManagerProps>>().props;
  const [isAuthorStyleDialogOpen, setIsAuthorStyleDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedStyle, setSelectedStyle] = useState<AuthorStyle | null>(null);

  // Auto-refresh to check for completed author styles
  useEffect(() => {
    // Check if any styles are still processing
    const hasProcessingStyles = authorStyles.some(
      style => style.status === 'init_completed' || style.status === 'sampling_completed'
    );

    if (hasProcessingStyles) {
      // Poll every 10 seconds while styles are processing
      const interval = setInterval(() => {
        router.reload({ only: ['authorStyles'] });
      }, 10000);

      return () => clearInterval(interval);
    }
  }, [authorStyles]);

  const handleEditClick = (style: AuthorStyle) => {
    setSelectedStyle(style);
    setIsEditDialogOpen(true);
  };

  const handleDeleteClick = (style: AuthorStyle) => {
    setSelectedStyle(style);
    setIsDeleteDialogOpen(true);
  };

  const handleEditClose = () => {
    setIsEditDialogOpen(false);
    setSelectedStyle(null);
  };

  const handleDeleteClose = () => {
    setIsDeleteDialogOpen(false);
    setSelectedStyle(null);
  };

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
          onEditClick={handleEditClick}
          onDeleteClick={handleDeleteClick}
        />

        {/* Projects Table Section */}
        <ProjectsTable 
          projects={projects} 
          workspaceId={workspaceId} 
        />
      </div>

      {/* Author Style Create Dialog */}
      <AuthorStyleDialog 
        open={isAuthorStyleDialogOpen} 
        onClose={() => setIsAuthorStyleDialogOpen(false)} 
        authorStyles={authorStyles}
      />

      {/* Author Style Edit Dialog */}
      <AuthorStyleEditDialog
        open={isEditDialogOpen}
        onClose={handleEditClose}
        authorStyle={selectedStyle}
        workspaceId={workspaceId}
      />

      {/* Author Style Delete Dialog */}
      <AuthorStyleDeleteDialog
        open={isDeleteDialogOpen}
        onClose={handleDeleteClose}
        authorStyle={selectedStyle}
        workspaceId={workspaceId}
      />
    </AuthenticatedLayout>
  );
}

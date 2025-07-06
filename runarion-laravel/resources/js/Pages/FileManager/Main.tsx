import React, { useState, useMemo } from "react";
import { Head, usePage, Link } from "@inertiajs/react";
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle,
  CardFooter,
} from "@/Components/ui/card";
import { Button } from "@/Components/ui/button";
import { Badge } from "@/Components/ui/badge";
import { Checkbox } from "@/Components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/Components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/Components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/Components/ui/dropdown-menu";
import AuthenticatedLayout, { BreadcrumbItem } from "@/Layouts/AuthenticatedLayout";
import { PageProps } from "@/types";
import { 
  Cloud, 
  Folder, 
  HardDrive, 
  MoreVertical, 
  CirclePlus, 
  ArrowUpDown,
  User,
  Users,
  ChevronLeft,
  ChevronRight,
  Ellipsis,
} from "lucide-react";

// Define the storage provider type
interface StorageProvider {
  id: string;
  name: string;
  icon: string;
  color: string;
  used: number;
  total: number;
  percentage: number;
  enabled: boolean;
}

// Define the author style type
interface AuthorStyle {
  id: string;
  name: string;
  fileCount: number;
  avatar: string;
  color: string;
}

// Define the project type
interface Project {
  id: string;
  name: string;
  size: string;
  createdAt: string;
  sharedWith: string[];
  savedIn: string;
}

// Define the props type
type Props = {
  workspaceId: string;
  workspaceName: string;
  storageProviders: StorageProvider[];
  authorStyles: AuthorStyle[];
  projects: Project[];
};

export default function FileManager() {
  const { workspaceId, workspaceName, storageProviders, authorStyles, projects } = usePage<PageProps<Props>>().props;
  const [isAuthorStyleModalOpen, setIsAuthorStyleModalOpen] = useState(false);
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [selectedProjects, setSelectedProjects] = useState<string[]>([]);
  const [selectAll, setSelectAll] = useState(false);
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 15;

  const breadcrumbs: BreadcrumbItem[] = [
    { label: "Dashboard", path: "workspace.dashboard" },
    { label: "File Manager", path: "workspace.files" },
  ].map((item) => ({
    ...item,
    param: { workspace_id: workspaceId },
  }));

  // Sort storage providers: enabled first (with Local Storage at the beginning), then disabled
  const sortedStorageProviders = [...storageProviders].sort((a, b) => {
    // Local Storage is always first
    if (a.name === "Local Storage") return -1;
    if (b.name === "Local Storage") return 1;
    
    // Then sort by enabled status
    if (a.enabled && !b.enabled) return -1;
    if (!a.enabled && b.enabled) return 1;
    
    // If both have the same enabled status, keep original order
    return 0;
  });

  // Sort projects based on the selected column and direction
  const sortedProjects = useMemo(() => {
    return [...projects].sort((a, b) => {
      if (!sortColumn) return 0;
      
      let comparison = 0;
      
      switch (sortColumn) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'size':
          // Extract numeric value from size string (e.g., "2.4 MB" -> 2.4)
          const sizeA = parseFloat(a.size);
          const sizeB = parseFloat(b.size);
          comparison = sizeA - sizeB;
          break;
        case 'createdAt':
          comparison = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
          break;
        default:
          return 0;
      }
      
      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [projects, sortColumn, sortDirection]);

  // Calculate pagination
  const totalPages = Math.ceil(sortedProjects.length / itemsPerPage);
  const paginatedProjects = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return sortedProjects.slice(startIndex, startIndex + itemsPerPage);
  }, [sortedProjects, currentPage, itemsPerPage]);

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const handleSelectAll = () => {
    if (selectAll) {
      setSelectedProjects([]);
    } else {
      setSelectedProjects(paginatedProjects.map(project => project.id));
    }
    setSelectAll(!selectAll);
  };

  const handleSelectProject = (projectId: string) => {
    if (selectedProjects.includes(projectId)) {
      setSelectedProjects(selectedProjects.filter(id => id !== projectId));
      if (selectAll) setSelectAll(false);
    } else {
      setSelectedProjects([...selectedProjects, projectId]);
      if (selectedProjects.length + 1 === paginatedProjects.length) {
        setSelectAll(true);
      }
    }
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    setSelectedProjects([]);
    setSelectAll(false);
  };

  // Function to get the appropriate icon component based on the icon name
  const getIconComponent = (iconName: string) => {
    switch (iconName) {
      case 'Cloud':
        return Cloud;
      case 'Dropbox':
        return Cloud;
      case 'HardDrive':
        return HardDrive;
      default:
        return Folder;
    }
  };

  return (
    <AuthenticatedLayout breadcrumbs={breadcrumbs}>
      <Head title="File Manager" />

      <div className="space-y-6">
        {/* File Manager Section */}
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl">File Manager</h2>
          </div>
          
          {/* Storage Cards - 4 column grid on md+, 2 column on sm, 1 column on xs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            {sortedStorageProviders.map((provider) => {
              const IconComponent = getIconComponent(provider.icon);
              return (
                <div key={provider.id} className={`bg-white rounded-lg border ${!provider.enabled ? 'opacity-60' : ''}`}>
                  <div className="p-6">
                    <div className="flex items-center gap-4">
                      <div className={`${provider.color} p-2 rounded-full bg-gray-100`}>
                        <IconComponent className="h-6 w-6" />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-medium">{provider.name}</h3>
                        {!provider.enabled && (
                          <span className="text-xs text-muted-foreground">Disabled</span>
                        )}
                      </div>
                    </div>
                    
                    {provider.enabled && (
                      <div className="mt-4 space-y-2">
                        <div className="h-2 w-full bg-gray-200 rounded">
                          <div 
                            className="h-2 rounded bg-blue-500" 
                            style={{ width: `${provider.percentage}%` }}
                          />
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {provider.used}GB / {provider.total}GB
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Author Styles */}
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl">Author Styles</h2>
            <Button 
              variant="default"
              onClick={() => setIsAuthorStyleModalOpen(true)}
            >
              <CirclePlus />
              Add Style
            </Button>
          </div>
          <div className="flex space-x-4 overflow-auto pb-2">
            {authorStyles.length > 0 ? (
              authorStyles.map((style) => (
                <div key={style.id} className="min-w-[250px] max-w-[300px] bg-white rounded-lg border">
                  <div className="p-4 relative">
                    <span className="absolute top-2 right-2 text-xs bg-gray-100 px-2 py-0.5 rounded">
                      {style.fileCount} Files
                    </span>
                    <div className="flex items-center gap-3 mt-4">
                      <div className={`${style.color} w-10 h-10 rounded-full flex items-center justify-center font-medium`}>
                        {style.avatar}
                      </div>
                      <div className="truncate">
                        <h3 className="font-medium text-sm">{style.name}</h3>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="w-full text-center py-8 text-muted-foreground">
                No author styles found. Create one by clicking the "Add Style" button.
              </div>
            )}
          </div>
        </div>

        {/* Projects Table */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle>Projects</CardTitle>
            <Button variant="outline" size="sm">View All</Button>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[40px]">
                    <Checkbox 
                      checked={selectAll} 
                      onCheckedChange={handleSelectAll}
                    />
                  </TableHead>
                  <TableHead className="cursor-pointer" onClick={() => handleSort('name')}>
                    <div className="flex items-center">
                      Name
                      <ArrowUpDown className="ml-2 h-4 w-4" />
                    </div>
                  </TableHead>
                  <TableHead className="cursor-pointer" onClick={() => handleSort('size')}>
                    <div className="flex items-center">
                      Size
                      <ArrowUpDown className="ml-2 h-4 w-4" />
                    </div>
                  </TableHead>
                  <TableHead className="cursor-pointer" onClick={() => handleSort('createdAt')}>
                    <div className="flex items-center">
                      Created At
                      <ArrowUpDown className="ml-2 h-4 w-4" />
                    </div>
                  </TableHead>
                  <TableHead>Shared With</TableHead>
                  <TableHead>Saved In</TableHead>
                  <TableHead className="w-[60px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedProjects.length > 0 ? (
                  paginatedProjects.map((project) => (
                    <TableRow key={project.id}>
                      <TableCell>
                        <Checkbox 
                          checked={selectedProjects.includes(project.id)}
                          onCheckedChange={() => handleSelectProject(project.id)}
                        />
                      </TableCell>
                      <TableCell className="font-medium">
                        <div className="flex items-center">
                          <Folder className="h-4 w-4 mr-2 text-blue-500" />
                          {project.name}
                        </div>
                      </TableCell>
                      <TableCell>{project.size}</TableCell>
                      <TableCell>{project.createdAt}</TableCell>
                      <TableCell>
                        {project.sharedWith.length > 0 ? (
                          <div className="flex items-center">
                            {project.sharedWith.length === 1 ? (
                              <>
                                <User className="h-4 w-4 mr-1" />
                                <span>{project.sharedWith[0]}</span>
                              </>
                            ) : (
                              <>
                                <Users className="h-4 w-4 mr-1" />
                                <span>{project.sharedWith.length} users</span>
                              </>
                            )}
                          </div>
                        ) : (
                          <span className="text-muted-foreground">Not shared</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{project.savedIn}</Badge>
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger>
                            <div className="cursor-pointer relative z-20 p-2 m-[-8px]">
                              <Ellipsis className="h-4 w-4" />
                            </div>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => {}}>
                              <span>Project Settings</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => {}}>
                              <span>Move to Folder</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => {}}>
                              <span>Open Project</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => {}}>
                              <span>Duplicate Project</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => {}}>
                              <span>Share Project</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => {}}>
                              <span>Archive Project</span>
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                      No projects found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
          {totalPages > 1 && (
            <CardFooter className="flex justify-between items-center border-t px-6 py-4">
              <div className="text-sm text-muted-foreground">
                Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, projects.length)} of {projects.length} projects
              </div>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <div className="flex items-center space-x-1">
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                    <Button
                      key={page}
                      variant={page === currentPage ? "default" : "outline"}
                      size="sm"
                      className="w-8 h-8 p-0"
                      onClick={() => handlePageChange(page)}
                    >
                      {page}
                    </Button>
                  ))}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </CardFooter>
          )}
        </Card>
      </div>

      {/* Author Style Modal (placeholder) */}
      <Dialog open={isAuthorStyleModalOpen} onOpenChange={setIsAuthorStyleModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Author Style</DialogTitle>
            <DialogDescription>
              Create a new author style for your projects.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            {/* Form content would go here */}
            <p className="text-sm text-muted-foreground">Author style creation form placeholder.</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAuthorStyleModalOpen(false)}>Cancel</Button>
            <Button onClick={() => setIsAuthorStyleModalOpen(false)}>Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AuthenticatedLayout>
  );
}

import React, { useState, useMemo } from "react";
import { Project } from "@/types/files";
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/Components/ui/dropdown-menu";
import { 
  Folder, 
  Ellipsis, 
  ArrowUpDown,
  User,
  Users,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

interface ProjectsTableProps {
  projects: Project[];
}

export default function ProjectsTable({ projects }: ProjectsTableProps) {
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [selectedProjects, setSelectedProjects] = useState<string[]>([]);
  const [selectAll, setSelectAll] = useState(false);
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 15;

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

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle>Projects</CardTitle>
        <Button variant="default" size="sm">View All</Button>
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
  );
}

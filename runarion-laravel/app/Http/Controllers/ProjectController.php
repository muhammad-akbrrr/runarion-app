<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;
use Illuminate\Http\RedirectResponse;
use App\Models\Folder;
use App\Models\Projects;
use Illuminate\Support\Str;

class ProjectController extends Controller
{
    public function show(Request $request, string $workspace_id): RedirectResponse|Response
    {
        $folders = Folder::where('workspace_id', $workspace_id)->get(['id', 'name']);
        $projects = Projects::where('workspace_id', $workspace_id)->get(['id', 'name', 'folder_id']);

        return Inertia::render('Projects/ProjectList', [
            'workspaceId' => $workspace_id,
            'folders' => $folders,
            'projects' => $projects,
        ]);
    }

    /**
     * Show the project editor page for a specific project.
     */
    public function editor(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (!$project) {
            return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id]);
        }

        return Inertia::render('Projects/Editor/Main', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'projectName' => $project->name,
        ]);
    }

    /**
     * Opens up a specific folder.
     */
    public function openFolder(Request $request, string $workspace_id, string $folder_id)
    {
        $folders = Folder::where('workspace_id', $workspace_id)->get(['id', 'name']);
        $selectedFolder = Folder::where('id', $folder_id)
            ->where('workspace_id', $workspace_id)
            ->first();
        if (!$selectedFolder) {
            return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id]);
        }
        $projects = Projects::where('workspace_id', $workspace_id)
            ->where('folder_id', $folder_id)
            ->get(['id', 'name', 'folder_id']);

        return Inertia::render('Projects/ProjectList', [
            'workspaceId' => $workspace_id,
            'folders' => $folders,
            'projects' => $projects,
            'folder' => $selectedFolder,
        ]);
    }

    /**
     * Store a new folder in the workspace.
     */
    public function storeFolder(Request $request, string $workspace_id)
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
        ]);
        $folder = new Folder();
        $folder->workspace_id = $workspace_id;
        $folder->name = $validated['name'];
        $folder->slug = Str::slug($validated['name']);
        $folder->save();

        $folders = Folder::where('workspace_id', $workspace_id)->get(['id', 'name']);
        $projects = Projects::where('workspace_id', $workspace_id)->get(['id', 'name', 'folder_id']);

        return Inertia::render('Projects/ProjectList', [
            'workspaceId' => $workspace_id,
            'folders' => $folders,
            'projects' => $projects,
        ]);
    }

    /**
     * Store a new project in the workspace.
     */
    public function storeProject(Request $request, string $workspace_id)
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'folder_id' => 'nullable|string',
        ]);
        $project = new Projects();
        $project->workspace_id = $workspace_id;
        $project->name = $validated['name'];
        $project->slug = Str::slug($validated['name']);
        if (!empty($validated['folder_id'])) {
            $project->folder_id = $validated['folder_id'];
        }
        $project->save();

        // Redirect to the editor page for the new project
        return redirect()->route('workspace.projects.editor', [
            'workspace_id' => $workspace_id,
            'project_id' => $project->id,
        ]);
    }

    /**
     * Delete a project from the workspace.
     */
    public function destroyProject(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('workspace_id', $workspace_id)->where('id', $project_id)->firstOrFail();
        $project->delete();
        return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id]);
    }

    /**
     * Delete a folder and move its projects to the root of the workspace.
     */
    public function destroyFolder(Request $request, string $workspace_id, string $folder_id)
    {
        // Move all projects in this folder to the root (folder_id = null)
        Projects::where('workspace_id', $workspace_id)
            ->where('folder_id', $folder_id)
            ->update(['folder_id' => null]);

        // Delete the folder
        $folder = Folder::where('workspace_id', $workspace_id)->where('id', $folder_id)->firstOrFail();
        $folder->delete();

        return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id]);
    }
}

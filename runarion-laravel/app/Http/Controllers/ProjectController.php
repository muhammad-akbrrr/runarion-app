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
        $projects = Projects::where('workspace_id', $workspace_id)->get(['id', 'name']);

        return Inertia::render('Projects/ProjectList', [
            'workspaceId' => $workspace_id,
            'folders' => $folders,
            'projects' => $projects,
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
        $projects = Projects::where('workspace_id', $workspace_id)->get(['id', 'name']);

        return Inertia::render('Projects/ProjectList', [
            'workspaceId' => $workspace_id,
            'folders' => $folders,
            'projects' => $projects,
        ]);
    }

    /**
     * Opens up a specific folder.
     */
    public function openFolder(Request $request, string $workspace_id, string $folder_id)
    {

    }
}

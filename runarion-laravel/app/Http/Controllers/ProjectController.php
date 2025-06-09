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
        $folders = Folder::where('workspace_id', $workspace_id)->get(['id', 'name', 'created_at']);
        $projects = Projects::where('workspace_id', $workspace_id)
            ->with(['author:id,name'])
            ->get();

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
        $folders = Folder::where('workspace_id', $workspace_id)->get(['id', 'name', 'created_at']);
        $selectedFolder = Folder::where('id', $folder_id)
            ->where('workspace_id', $workspace_id)
            ->first();
        if (!$selectedFolder) {
            return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id]);
        }
        $projects = Projects::where('workspace_id', $workspace_id)
            ->where('folder_id', $folder_id)
            ->with(['author:id,name'])
            ->get();

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

        $folders = Folder::where('workspace_id', $workspace_id)->get(['id', 'name', 'created_at']);
        $projects = Projects::where('workspace_id', $workspace_id)->get();

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
        $project->original_author = $request->user()->id;
        if (!empty($validated['folder_id'])) {
            $project->folder_id = $validated['folder_id'];
        }

        // Add initial access entry for the creator
        $project->access = [
            [
                'user' => [
                    'id' => (string) $request->user()->id,
                    'name' => $request->user()->name,
                    'email' => $request->user()->email,
                    'avatar_url' => $request->user()->profile_photo_url ?? null,
                ],
                'role' => 'admin'
            ]
        ];

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
        $project->is_active = false;
        $project->save();
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
        $folder->is_active = false;
        $folder->save();
        $folder->delete();

        return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id]);
    }

    /**
     * Show the settings page for a specific project.
     */
    public function settings(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (!$project) {
            return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id]);
        }

        // Get current user's access information
        $currentUserAccess = null;
        if ($project->access) {
            $currentUserId = (string) $request->user()->id;
            $currentUserAccess = collect($project->access)->first(function ($access) use ($currentUserId) {
                return (string) $access['user']['id'] === $currentUserId;
            });
        }

        // Add current user's access to the project data
        $project->current_user_access = $currentUserAccess;

        return Inertia::render('Projects/Edit', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => $project,
        ]);
    }

    /**
     * Update project information.
     */
    public function update(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('workspace_id', $workspace_id)
            ->where('id', $project_id)
            ->firstOrFail();

        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'category' => 'nullable|string',
            'description' => 'nullable|string',
            'storageLocation' => 'required|string|in:01,02,03,04',
        ]);

        $project->name = $validated['name'];
        $project->slug = Str::slug($validated['name']);
        $project->category = $validated['category'] === 'none' ? null : $validated['category'];
        $project->description = $validated['description'];
        $project->saved_in = $validated['storageLocation'];
        $project->save();

        return back();
    }

    /**
     * Show the access settings page for a specific project.
     */
    public function access(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (!$project) {
            return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id]);
        }

        // Get current user's access information
        $currentUserAccess = null;
        if ($project->access) {
            $currentUserId = (string) $request->user()->id;
            $currentUserAccess = collect($project->access)->first(function ($access) use ($currentUserId) {
                return (string) $access['user']['id'] === $currentUserId;
            });
        }

        // Add current user's access to the project data
        $project->current_user_access = $currentUserAccess;

        return Inertia::render('Projects/Access', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => $project,
        ]);
    }

    /**
     * Update a member's role in the project.
     */
    public function updateMemberRole(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->firstOrFail();

        $validated = $request->validate([
            'user_id' => 'required|integer|exists:users,id',
            'role' => 'required|string|in:editor,manager,admin',
        ]);

        // Update the role in the access array
        $access = $project->access;
        foreach ($access as &$member) {
            if ((string) $member['user']['id'] === (string) $validated['user_id']) {
                $member['role'] = $validated['role'];
                break;
            }
        }
        $project->access = $access;
        $project->save();

        // Get current user's access information
        $currentUserAccess = null;
        if ($project->access) {
            $currentUserId = (string) $request->user()->id;
            $currentUserAccess = collect($project->access)->first(function ($access) use ($currentUserId) {
                return (string) $access['user']['id'] === $currentUserId;
            });
        }

        // Add current user's access to the project data
        $project->current_user_access = $currentUserAccess;

        return Inertia::render('Projects/Access', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => $project,
        ]);
    }

    /**
     * Remove a member from the project.
     */
    public function removeMember(Request $request, string $workspace_id, string $project_id)
    {
        \Log::info('Remove Member Request', [
            'request_data' => $request->all(),
            'user_id' => $request->input('user_id'),
            'type' => gettype($request->input('user_id'))
        ]);

        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->firstOrFail();

        \Log::info('Project Found', [
            'project_id' => $project_id,
            'access' => $project->access
        ]);

        $validated = $request->validate([
            'user_id' => 'required|integer|exists:users,id',
        ]);

        \Log::info('Validation Passed', [
            'validated_data' => $validated
        ]);

        // Remove the member from the access array
        $access = $project->access;
        \Log::info('Before Filter', [
            'access' => $access,
            'user_id_to_remove' => $validated['user_id']
        ]);

        $access = array_filter($access, function ($member) use ($validated) {
            $result = (string) $member['user']['id'] !== (string) $validated['user_id'];
            \Log::info('Filter Comparison', [
                'member_id' => $member['user']['id'],
                'member_id_type' => gettype($member['user']['id']),
                'validated_id' => $validated['user_id'],
                'validated_id_type' => gettype($validated['user_id']),
                'result' => $result
            ]);
            return $result;
        });

        \Log::info('After Filter', [
            'filtered_access' => $access
        ]);

        $project->access = array_values($access); // Reindex array
        $project->save();

        \Log::info('Project Saved', [
            'new_access' => $project->access
        ]);

        // Get current user's access information
        $currentUserAccess = null;
        if ($project->access) {
            $currentUserId = (string) $request->user()->id;
            $currentUserAccess = collect($project->access)->first(function ($access) use ($currentUserId) {
                return (string) $access['user']['id'] === $currentUserId;
            });
        }

        // Add current user's access to the project data
        $project->current_user_access = $currentUserAccess;

        return Inertia::render('Projects/Access', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => $project,
        ]);
    }

    /**
     * Show the backups settings page for a specific project.
     */
    public function backups(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (!$project) {
            return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id]);
        }

        return Inertia::render('Projects/Backups', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => $project,
        ]);
    }

    /**
     * Show the activity settings page for a specific project.
     */
    public function activity(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (!$project) {
            return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id]);
        }

        return Inertia::render('Projects/Activity', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => $project,
        ]);
    }
}

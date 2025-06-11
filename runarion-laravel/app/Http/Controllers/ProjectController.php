<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;
use Illuminate\Http\RedirectResponse;
use App\Models\Folder;
use App\Models\Projects;
use App\Models\Workspace;
use Illuminate\Support\Str;
use App\Models\WorkspaceMember;
use Illuminate\Validation\Rule;

class ProjectController extends Controller
{
    public function show(Request $request, string $workspace_id): RedirectResponse|Response
    {
        $folders = Folder::where('workspace_id', $workspace_id)
            ->where('is_active', true)
            ->with(['author:id,name'])
            ->get();

        $projects = Projects::where('workspace_id', $workspace_id)
            ->with(['author:id,name'])
            ->get()
            ->map(function ($project) {
                if ($project->folder_id) {
                    $project->folder = Folder::where('id', $project->folder_id)
                        ->where('is_active', true)
                        ->first(['id', 'name']);
                }
                return $project;
            });

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
        $folders = Folder::where('workspace_id', $workspace_id)
            ->where('is_active', true)
            ->with(['author:id,name'])
            ->get();
        $selectedFolder = Folder::where('id', $folder_id)
            ->where('workspace_id', $workspace_id)
            ->where('is_active', true)
            ->with(['author:id,name'])
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

        // Check if user is a member of the workspace
        $isMember = WorkspaceMember::where('workspace_id', $workspace_id)
            ->where('user_id', $request->user()->id)
            ->exists();

        if (!$isMember) {
            return back()->withErrors(['name' => 'You must be a member of this workspace to create folders.']);
        }

        $folder = new Folder();
        $folder->workspace_id = $workspace_id;
        $folder->name = $validated['name'];
        $folder->slug = Str::slug($validated['name']);
        $folder->original_author = $request->user()->id;

        // Validate using model rules
        $rules = Folder::rules();
        $rules['workspace_id'] = ['required', 'ulid', 'exists:workspaces,id'];
        $validator = \Validator::make($folder->toArray(), $rules);
        if ($validator->fails()) {
            return back()->withErrors($validator->errors());
        }

        $folder->save();

        return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id]);
    }

    /**
     * Store a new project in the workspace.
     */
    public function storeProject(Request $request, string $workspace_id)
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'folder_id' => 'nullable|string|exists:folders,id',
        ]);

        // Check if user is a member of the workspace
        $isMember = WorkspaceMember::where('workspace_id', $workspace_id)
            ->where('user_id', $request->user()->id)
            ->exists();

        if (!$isMember) {
            return back()->withErrors(['name' => 'You must be a member of this workspace to create projects.']);
        }

        // If folder_id is provided and not 'none', verify it exists and belongs to the workspace
        if (!empty($validated['folder_id']) && $validated['folder_id'] !== null) {
            $folder = Folder::where('id', $validated['folder_id'])
                ->where('workspace_id', $workspace_id)
                ->where('is_active', true)
                ->first();

            if (!$folder) {
                return back()->withErrors(['folder_id' => 'Invalid folder selected.']);
            }
        }

        $project = new Projects();
        $project->workspace_id = $workspace_id;
        $project->name = $validated['name'];
        $project->slug = Str::slug($validated['name']);
        $project->original_author = $request->user()->id;
        $project->folder_id = empty($validated['folder_id']) || $validated['folder_id'] === null ? null : $validated['folder_id'];
        $project->saved_in = '01'; // Default to server storage

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

        // Validate using model rules
        $rules = Projects::rules();
        $rules['workspace_id'] = ['required', 'ulid', 'exists:workspaces,id'];
        $validator = \Validator::make($project->toArray(), $rules);
        if ($validator->fails()) {
            return back()->withErrors($validator->errors());
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
        $project = Projects::where('workspace_id', $workspace_id)
            ->where('id', $project_id)
            ->firstOrFail();

        // Check if user is the original author or has admin access
        $isOriginalAuthor = (string) $project->original_author === (string) $request->user()->id;
        $hasAdminAccess = false;

        if ($project->access) {
            $currentUserAccess = collect($project->access)->first(function ($access) use ($request) {
                return (string) $access['user']['id'] === (string) $request->user()->id;
            });
            $hasAdminAccess = $currentUserAccess && $currentUserAccess['role'] === 'admin';
        }

        if (!$isOriginalAuthor && !$hasAdminAccess) {
            return back()->withErrors(['project' => 'You do not have permission to delete this project.']);
        }

        // Update the slug to make it unique when soft deleted
        $project->slug = $project->slug . '-' . Str::random(6);
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
        $folder = Folder::where('workspace_id', $workspace_id)
            ->where('id', $folder_id)
            ->firstOrFail();

        // Check if user is the original author
        $isOriginalAuthor = (string) $folder->original_author === (string) $request->user()->id;

        // Check if user is workspace owner
        $isWorkspaceOwner = WorkspaceMember::where('workspace_id', $workspace_id)
            ->where('user_id', $request->user()->id)
            ->where('role', 'owner')
            ->exists();

        if (!$isOriginalAuthor && !$isWorkspaceOwner) {
            return back()->withErrors(['folder' => 'You do not have permission to delete this folder.']);
        }

        // Move all projects in this folder to the root (folder_id = null)
        Projects::where('workspace_id', $workspace_id)
            ->where('folder_id', $folder_id)
            ->update(['folder_id' => null]);

        // Update the slug to make it unique when soft deleted
        $folder->slug = $folder->slug . '-' . Str::random(6);
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

        // Get workspace folders
        $folders = Folder::where('workspace_id', $workspace_id)
            ->where('is_active', true)
            ->get();

        return Inertia::render('Projects/Edit', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => $project,
            'folders' => $folders,
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

        // Check if user is the original author or has admin access
        $isOriginalAuthor = (string) $project->original_author === (string) $request->user()->id;
        $hasAdminAccess = false;

        if ($project->access) {
            $currentUserAccess = collect($project->access)->first(function ($access) use ($request) {
                return (string) $access['user']['id'] === (string) $request->user()->id;
            });
            $hasAdminAccess = $currentUserAccess && $currentUserAccess['role'] === 'admin';
        }

        if (!$isOriginalAuthor && !$hasAdminAccess) {
            return back()->withErrors(['project' => 'You do not have permission to update this project.']);
        }

        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'category' => 'nullable|string',
            'description' => 'nullable|string',
            'storageLocation' => 'required|string|in:01,02,03,04',
            'folder_id' => 'nullable|string|exists:folders,id',
        ]);

        // If folder_id is provided, verify it exists and belongs to the workspace
        if ($validated['folder_id'] !== 'none') {
            $folder = Folder::where('id', $validated['folder_id'])
                ->where('workspace_id', $workspace_id)
                ->where('is_active', true)
                ->first();

            if (!$folder) {
                return back()->withErrors(['folder_id' => 'Invalid folder selected.']);
            }
        }

        $project->name = $validated['name'];
        $project->slug = Str::slug($validated['name']);
        $project->category = $validated['category'] === 'none' ? null : $validated['category'];
        $project->description = $validated['description'];
        $project->saved_in = $validated['storageLocation'];
        $project->folder_id = $validated['folder_id'] === 'none' ? null : $validated['folder_id'];

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

        // Get workspace members
        $workspace = Workspace::find($workspace_id);
        $workspaceMembers = $workspace->users()->get();

        return Inertia::render('Projects/Access', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => $project,
            'workspaceMembers' => $workspaceMembers,
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

        // Prevent changing original author's role
        if ((string) $validated['user_id'] === (string) $project->original_author) {
            return back()->withErrors(['user_id' => 'Cannot change the role of the original author.']);
        }

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

        // Get workspace members
        $workspace = Workspace::find($workspace_id);
        $workspaceMembers = $workspace->users()->get();

        return Inertia::render('Projects/Access', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => $project,
            'workspaceMembers' => $workspaceMembers,
        ]);
    }

    /**
     * Remove a member from the project.
     */
    public function removeMember(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->firstOrFail();

        $validated = $request->validate([
            'user_id' => 'required|integer|exists:users,id',
        ]);

        // Prevent removing original author
        if ((string) $validated['user_id'] === (string) $project->original_author) {
            return back()->withErrors(['user_id' => 'Cannot remove the original author from the project.']);
        }

        // Check if user is removing themselves
        $isSelfRemoval = (string) $request->user()->id === (string) $validated['user_id'];
        $access = $project->access;

        $access = array_filter($access, function ($member) use ($validated) {
            $result = (string) $member['user']['id'] !== (string) $validated['user_id'];
            return $result;
        });

        $project->access = array_values($access); // Reindex array
        $project->save();

        // If user removed themselves, redirect to projects list
        if ($isSelfRemoval) {
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

        // Get workspace members
        $workspace = Workspace::find($workspace_id);
        $workspaceMembers = $workspace->users()->get();

        return Inertia::render('Projects/Access', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => $project,
            'workspaceMembers' => $workspaceMembers,
        ]);
    }

    public function addMember(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->firstOrFail();

        $validated = $request->validate([
            'members' => 'required|array',
            'members.*.user_id' => 'required|string',
            'members.*.role' => 'required|string|in:editor,manager,admin',
        ]);

        // Get workspace members
        $workspace = Workspace::find($workspace_id);
        $workspaceMembers = $workspace->users()->get();

        // Get current access array
        $currentAccess = $project->access ?? [];

        // Add new members to the access array
        foreach ($validated['members'] as $memberData) {
            // Find the workspace member
            $member = $workspaceMembers->first(function ($m) use ($memberData) {
                return (string) $m->id === $memberData['user_id'];
            });

            if (!$member) {
                continue; // Skip if member not found
            }

            // Check if member already exists in access array
            $exists = false;
            foreach ($currentAccess as $existingMember) {
                if ((string) $existingMember['user']['id'] === (string) $member->id) {
                    $exists = true;
                    break;
                }
            }

            // Only add if member doesn't already exist
            if (!$exists) {
                $currentAccess[] = [
                    'user' => [
                        'id' => (string) $member->id,
                        'name' => $member->name,
                        'email' => $member->email,
                        'avatar_url' => $member->profile_photo_url ?? null,
                    ],
                    'role' => $memberData['role'],
                ];
            }
        }

        // Update project access
        $project->access = $currentAccess;
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
            'workspaceMembers' => $workspaceMembers,
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

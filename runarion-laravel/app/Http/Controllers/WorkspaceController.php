<?php

namespace App\Http\Controllers;

use App\Models\Workspace;
use App\Models\WorkspaceMember;
use App\Models\WorkspaceInvitation;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Redirect;
use Inertia\Inertia;
use Inertia\Response;

class WorkspaceController extends Controller
{
    private function getWorkspace(int $workspaceId): Workspace
    {
        /** @var \App\Models\Workspace $workspace */
        $workspace = Workspace::find($workspaceId);

        if (!$workspace) {
            abort(401, 'Workspace not found.');
        }

        return $workspace;
    }

    private function getViewableWorkspace(int $workspaceId, int $userId): Workspace
    {
        $workspace = $this->getWorkspace($workspaceId);
        $isUserMember = $workspace->hasMany(WorkspaceMember::class)
            ->where('user_id', $userId)
            ->exists();
        if ($isUserMember) {
            abort(403, 'You are not authorized to view this workspace.');
        }
        return $workspace;
    }

    private function getUpdatableWorkspace(int $workspaceId, int $userId): Workspace
    {
        $workspace = $this->getWorkspace($workspaceId);
        $isUserOwnerOrAdmin = $workspace->hasMany(WorkspaceMember::class)
            ->where('user_id', $userId)
            ->whereIn('role', ['owner', 'admin'])
            ->exists();
        if (!$isUserOwnerOrAdmin) {
            abort(403, 'You are not authorized to update this workspace.');
        }
        return $workspace;
    }

    private function getDestroyableWorkspace(int $workspaceId, int $userId): Workspace
    {
        $workspace = $this->getWorkspace($workspaceId);
        $isUserOwner = $workspace->hasMany(WorkspaceMember::class)
            ->where('user_id', $userId)
            ->where('role', 'owner')
            ->exists();
        if (!$isUserOwner) {
            abort(403, 'You are not authorized to delete this workspace.');
        }
        return $workspace;
    }

    /**
     * Display the workspace's form.
     */
    public function edit(Request $request, int $workspace_id): Response
    {
        $workspace = $this->getViewableWorkspace($workspace_id, $request->user()->id);

        $workspaceMembers = $workspace->hasMany(WorkspaceMember::class)
            ->with('user')
            ->get()
            ->map(fn  ($member) => [
                'id' => $member->user->id,
                'name' => $member->user->name,
                'email' => $member->user->email,
                'avatar_url' => $member->user->avatar_url,
                'role' => $member->role,
                'is_verified' => $member->user->isVerified(),
            ])
            ->toArray();

        $workspaceInvitedMembers = WorkspaceInvitation::where('workspace_id', $workspace->id)
            ->get()    
            ->map(fn ($invitation) => [
                'id' => null,
                'name' => null,
                'email' => $invitation->user_email,
                'avatar_url' => null,
                'role' => $invitation->role,
                'is_verified' => null,
            ])
            ->toArray();

        $isUserAdmin = $workspace->hasMany(WorkspaceMember::class)
            ->where('user_id', $request->user()->id)
            ->where('role', 'admin')
            ->exists();
        $isUserOwner = $workspace->hasMany(WorkspaceMember::class)
            ->where('user_id', $request->user()->id)
            ->where('role', 'owner')
            ->exists();
        if (!$isUserAdmin && !$isUserOwner) {
            $workspace = $workspace->only([
                'id',
                'name', 
                'slug',
                'description',
                'cover_image_url',
                'settings',
                'trial_ends_at',
                'subscription_ends_at',
                'is_active',
            ]);
        }

        return Inertia::render('Workspace/Edit', [
            'workspace' => $workspace,
            'workspaceMembers' => array_merge($workspaceMembers, $workspaceInvitedMembers),
            'isUserAdmin' => $isUserAdmin,
            'isUserOwner' => $isUserOwner,
        ]);
    }

    /**
     * Update the workspace's information.
     */
    public function update(Request $request, $workspace_id): RedirectResponse
    {
        $workspace = $this->getUpdatableWorkspace($workspace_id, $request->user()->id);

        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'description' => 'string',
        ]);

        $workspace->update($validated);

        $workspace->save();

        return Redirect::route('workspaces.edit', ['workspace_id' => $workspace_id]);
    }

    /**
     * Update the workspace's settings.
     */
    public function updateSettings(Request $request, $workspace_id): RedirectResponse
    {
        $workspace = $this->getUpdatableWorkspace($workspace_id, $request->user()->id);

        $validated = $request->validate([
            'theme' => 'string|max:255',
            'notifications' => 'array', 
            'notifications.*' => 'boolean', 
        ]);

        $workspace->settings = array_merge($workspace->settings ?? [], $validated);
        $workspace->save();

        return Redirect::route('workspaces.edit', ['workspace_id' => $workspace_id]);
    }

    /**
     * Update the workspace's billing information.
     */
    public function updateBilling(Request $request, $workspace_id): RedirectResponse
    {
        $workspace = $this->getUpdatableWorkspace($workspace_id, $request->user()->id);

        $request->validate([
            'billing_*' => 'string|max:255',
            'billing_email' => 'email',
        ]);

        $data = $request->only(
            array_filter(
                array_keys($request->all()),
                fn($key) => str_starts_with($key, 'billing_')
            )
        );
        $workspace->update($data);

        $workspace->save();

        return Redirect::route('workspaces.edit', ['workspace_id' => $workspace_id]);
    }

    /**
     * Delete the workspace.
     */
    public function destroy(Request $request, $workspace_id): RedirectResponse
    {
        $workspace = $this->getDestroyableWorkspace($workspace_id, $request->user()->id);

        $workspace->delete();

        return Redirect::to('/');
    }
}

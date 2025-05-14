<?php

namespace App\Http\Controllers;

use App\Models\Workspace;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Redirect;
use Inertia\Inertia;
use Inertia\Response;

class WorkspaceController extends Controller
{
    private function getUserRole(int $workspaceId, int $userId): ?string
    {
        return DB::table('workspace_members')
            ->where('workspace_id', $workspaceId)
            ->where('user_id', $userId)
            ->value('role');
    }

    private function canView(int $workspaceId, int $userId): void
    {
        $userRole = $this->getUserRole($workspaceId, $userId);
        if ($userRole === null) {
            abort(403, 'You are not authorized to view this workspace.');
        }
    }

    private function canUpdate(int $workspaceId, int $userId): void
    {
        $userRole = $this->getUserRole($workspaceId, $userId);
        if ($userRole === 'member') {
            abort(403, 'You are not authorized to update this workspace.');
        }
    }

    private function canDestroy(int $workspaceId, int $userId): void
    {
        $userRole = $this->getUserRole($workspaceId, $userId);
        if ($userRole !== 'owner') {
            abort(403, 'You are not authorized to delete this workspace.');
        }
    }

    /**
     * Display the workspace's form.
     */
    public function edit(Request $request, int $workspace_id): Response
    {
        $this->canView($workspace_id, $request->user()->id);

        $workspace = Workspace::where('id', $workspace_id)->first();
        if (!$workspace) {
            abort(401, 'Workspace not found.');
        }

        $userRole = $this->getUserRole($workspace_id, $request->user()->id);
        $isUserOwner = $userRole == 'owner';
        $isUserAdmin = $userRole == 'admin';
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

        $workspaceMembers = DB::table('workspace_members')
            ->where('workspace_id', $workspace_id)
            ->join('users', 'workspace_members.user_id', '=', 'users.id')
            ->get()
            ->map(fn ($member) => [
                'id' => $member->user_id,
                'name' => $member->name,
                'email' => $member->email,
                'avatar_url' => $member->avatar_url,
                'role' => $member->role,
                'is_verified' => $member->is_verified,
            ])
            ->toArray();

        $workspaceInvitedMembers = DB::table('workspace_invitations')
            ->where('workspace_id', $workspace_id)
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
        $this->canUpdate($workspace_id, $request->user()->id);

        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'description' => 'string',
        ]);

        DB::table('workspaces')
            ->where('id', $workspace_id)
            ->update($validated);

        return Redirect::route('workspaces.edit', ['workspace_id' => $workspace_id]);
    }

    /**
     * Update the workspace's settings.
     */
    public function updateSettings(Request $request, $workspace_id): RedirectResponse
    {
        $this->canUpdate($workspace_id, $request->user()->id);

        $validated = $request->validate([
            'theme' => 'string|max:255',
            'notifications' => 'array', 
            'notifications.*' => 'boolean', 
        ]);

        $updates = [];
        foreach ($validated as $key => $value) {
            $updates["settings->{$key}"] = $value;
        }

        DB::table('workspaces')
            ->where('id', $workspace_id)
            ->update($updates);

        return Redirect::route('workspaces.edit', ['workspace_id' => $workspace_id]);
    }

    /**
     * Update the workspace's billing information.
     */
    public function updateBilling(Request $request, $workspace_id): RedirectResponse
    {
        $this->canUpdate($workspace_id, $request->user()->id);

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
        
        DB::table('workspaces')
            ->where('id', $workspace_id)
            ->update($data);

        return Redirect::route('workspaces.edit', ['workspace_id' => $workspace_id]);
    }

    /**
     * Delete the workspace.
     */
    public function destroy(Request $request, $workspace_id): RedirectResponse
    {
        $this->canDestroy($workspace_id, $request->user()->id);

        DB::table('workspaces')
            ->where('id', $workspace_id)
            ->delete();

        return Redirect::to('/');
    }
}

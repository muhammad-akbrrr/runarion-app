<?php

namespace App\Http\Controllers;

use App\Models\Workspace;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Redirect;
use Inertia\Inertia;
use Inertia\Response;

class WorkspaceController extends Controller
{
    private function getWorkspace(int $workspace_id): Workspace
    {
        /** @var \App\Models\Workspace $workspace */
        $workspace = Workspace::find($workspace_id);

        if (!$workspace) {
            abort(401, 'Workspace not found.');
        }

        return $workspace;
    }

    private function getViewableWorkspace(int $workspace_id, int $user_id): Workspace
    {
        $workspace = $this->getWorkspace($workspace_id);
        if (!$workspace->isMember($user_id)) {
            abort(403, 'You are not authorized to view this workspace.');
        }
        return $workspace;
    }

    private function getModifiableWorkspace(int $workspace_id, int $user_id): Workspace
    {
        $workspace = $this->getWorkspace($workspace_id);
        if (!$workspace->isOwnerOrAdmin($user_id)) {
            abort(403, 'You are not authorized to modify this workspace.');
        }
        return $workspace;
    }

    /**
     * Display the workspace's form.
     */
    public function edit(Request $request, int $workspace_id): Response
    {
        $workspace = $this->getViewableWorkspace($workspace_id, $request->user()->id);

        $isUserAdmin = $workspace->isOwnerOrAdmin($request->user()->id);
        if (!$isUserAdmin) {
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
            'isUserAdmin' => $isUserAdmin,
        ]);
    }

    /**
     * Update the workspace's information.
     */
    public function update(Request $request, $workspace_id): RedirectResponse
    {
        $workspace = $this->getModifiableWorkspace($workspace_id, $request->user()->id);

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
        $workspace = $this->getModifiableWorkspace($workspace_id, $request->user()->id);

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
        $workspace = $this->getModifiableWorkspace($workspace_id, $request->user()->id);

        $validated = $request->validate([
            'billing_email' => 'email',
            'billing_*' => 'string|max:255',
        ]);

        $workspace->update($validated);

        $workspace->save();

        return Redirect::route('workspaces.edit', ['workspace_id' => $workspace_id]);
    }

    /**
     * Delete the workspace.
     */
    public function destroy(Request $request, $workspace_id): RedirectResponse
    {
        $workspace = $this->getModifiableWorkspace($workspace_id, $request->user()->id);

        $workspace->delete();

        return Redirect::to('/');
    }
}

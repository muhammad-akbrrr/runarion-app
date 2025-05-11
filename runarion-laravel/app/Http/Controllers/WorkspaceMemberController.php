<?php

namespace App\Http\Controllers;

use App\Models\User;
use App\Models\Workspace;
use App\Models\WorkspaceInvitation;
use App\Models\WorkspaceMember;
use App\Notifications\WorkspaceInvitation as WorkspaceInvitationNotification;
use Carbon\Carbon;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Notification;
use Illuminate\Support\Facades\Redirect;
use Illuminate\Support\Str;
use Inertia\Inertia;
use Inertia\Response;

class WorkspaceMemberController extends Controller
{
    private function getModifiableWorkspace(int $workspaceId, int $userId, string $role, string $type): Workspace
    {
        /** @var \App\Models\Workspace $workspace */
        $workspace = Workspace::find($workspaceId);
        if (!$workspace) {
            abort(401, 'Workspace not found.');
        }

        if ($type == "assign") {
            $message = "assign {$role} to this workspace";
        } elseif ($type == "update") {
            $message = "update role to {$role} in this workspace";
        } elseif ($type == "remove") {
            $message = "remove {$role} from this workspace";
        } else {
            $message = '';
        }

        $isAuthorized = $role == 'admin' ? 
            $workspace->isOwner($userId) :
            $workspace->isOwnerOrAdmin($userId);
        if (!$isAuthorized) {
            abort(403, "You are not authorized to {$message}.");
        }
        return $workspace;
    }

    /**
     * Get the existence and membership status of users based on their emails within a workspace.
     *
     * @param array $emails An array of email addresses to check.
     * @param int $workspaceId The id of the workspace to check membership against.
     *
     * @return array{is_exists: bool, is_member: bool}[] 
     * An array with the same length as the $emails array. Each element has keys:
     *               - 'is_exists' (bool):  true if a user with the corresponding email exists
     *               - 'is_member' (bool):  true if the user is a member of the workspace
     */
    private function getExistAndMembershipStatus(array $emails, int $workspaceId): array
    {
        $users = User::whereIn('email', $emails)
            ->pluck('id', 'email');

        $userIds = array_map(fn ($email) => $users[$email] ?? null, $emails);

        $workspaceUserIds = WorkspaceMember::where('workspace_id', $workspaceId)
            ->whereIn('user_id', array_filter($userIds))
            ->pluck('user_id')
            ->all();

        $result = [];

        foreach ($userIds as $userId) {
            $userExists = $userId !== null;
            $result[] = [
                'is_exists' => $userExists,
                'is_member' => $userExists && in_array($userId, $workspaceUserIds),
            ];
        }

        return $result;
    }

    /**
     * Sends an email invitation to a user to join a workspace
     */
    private function sendInvitation(Workspace $workspace, string $userEmail, bool $userExists, string $role): void
    {
        $token = Str::random(64);
        $expiredAt = Carbon::now()->addHours(24);
        WorkspaceInvitation::updateOrCreate(
            [
                'workspace_id' => $workspace->id,
                'user_email' => $userEmail,
            ],
            [
                'role' => $role,
                'token' => $token,
                'expired_at' => $expiredAt,
            ]
        );

        $acceptUrl = route('workspace.invitation.accept', ['token' => $token]);
        Notification::route('mail', $userEmail)
            ->notify(new WorkspaceInvitationNotification($workspace, $acceptUrl, $role, $userExists));
    }


    /**
     * Assign users to a workspace via email invitation
     */
    public function assign(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'workspace_id' => 'required|numeric',
            'role' => 'required|in:admin,member',
            'user_emails' => 'required|array',
            'user_emails.*' => 'email',
        ]);
        
        $workspace = $this->getModifiableWorkspace(
            $validated['workspace_id'],
            $request->user()->id,
            $validated['role'],
            'assign'
        );

        $userStatus = $this->getExistAndMembershipStatus($validated['user_emails'], $workspace->id);

        foreach ($userStatus as $index => $status) {
            if ($status['is_member']) {
                continue;
            }
            $this->sendInvitation(
                $workspace,
                $validated['user_emails'][$index], 
                $status['is_exists'], 
                $validated['role']
            );
        }
        
        return Redirect::route('workspaces.edit', ['workspace_id' => $workspace->id]);
    }

    /**
     * Update user roles in a workspace
     */
    public function update(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'workspace_id' => 'required|numeric',
            'role' => 'required|in:admin,member',
            'user_ids' => 'required|array',
            'user_ids.*' => 'numeric',
        ]);

        $workspace = $this->getModifiableWorkspace(
            $validated['workspace_id'],
            $request->user()->id,
            $validated['role'],
            'update'
        );

        WorkspaceMember::where('workspace_id', $workspace->id)
            ->whereIn('user_id', $validated['user_ids'])
            ->update(['role' => $validated['role']]);
        
        return Redirect::route('workspaces.edit', ['workspace_id' => $workspace->id]);
    }

    /**
     * Remove users from a workspace
     */
    public function remove(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'workspace_id' => 'required|numeric',
            'role' => 'required|in:admin,member',
            'user_ids' => 'required|array',
            'user_ids.*' => 'numeric',
            'user_emails' => 'required|array',
            'user_emails.*' => 'email',
        ]);

        $workspace = $this->getModifiableWorkspace(
            $validated['workspace_id'],
            $request->user()->id,
            $validated['role'],
            'remove'
        );

        WorkspaceMember::where('workspace_id', $workspace->id)
            ->whereIn('user_id', $validated['user_ids'])
            ->delete();

        WorkspaceInvitation::where('workspace_id', $workspace->id)
            ->whereIn('user_email', $validated['user_emails'])
            ->delete();
        
        return Redirect::route('workspaces.edit', ['workspace_id' => $workspace->id]);
    }

    /**
     * Leave a workspace as a user
     */
    public function leave(Request $request, $workspaceId): RedirectResponse
    {
        /** @var \App\Models\Workspace $workspace */
        $workspace = Workspace::find($workspaceId);
        if (!$workspace) {
            abort(404, 'Workspace not found.');
        }

        $user = $request->user();
        if ($user->isWorkspaceOwner($workspace)) {
            abort(400, 'You cannot leave a workspace you own.');
        }

        WorkspaceMember::where('workspace_id', $workspace->id)
            ->where('user_id', $user->id)
            ->delete();

        return Redirect::to('/');
    }

    
    /**
     * Accept a workspace invitation
     */
    public function accept(Request $request, $token): Response
    {
        // Find invitation by token
        $invitation = WorkspaceInvitation::where('token', $token)
            ->where('expired_at', '>', Carbon::now())
            ->first();
        
        if (!$invitation) {
            return Inertia::render('Workspace/Invitation', [
                'status' => 'invalid'
            ]);
        }

        // Find user by email
        $user = User::where('email', $invitation->user_email)->first();
        if (!$user) {
            return Inertia::render('Workspace/Invitation', [
                'status' => 'unregistered',
            ]);
        }
        
        // Add user to workspace
        WorkspaceMember::create([
            'workspace_id' => $invitation->workspace_id,
            'user_id' => $user->id,
            'role' => $invitation->role,
        ]);
        
        // Delete the invitation
        $invitation->delete();
        
        return Inertia::render('Workspace/Invitation', [
                'status' => 'success',
            ]);
    }
}
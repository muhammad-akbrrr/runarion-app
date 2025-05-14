<?php

namespace App\Http\Controllers;

use App\Models\Workspace;
use App\Notifications\WorkspaceInvitationNotification;
use Carbon\Carbon;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Notification;
use Illuminate\Support\Facades\Redirect;
use Illuminate\Support\Str;
use Inertia\Inertia;
use Inertia\Response;

class WorkspaceMemberController extends Controller
{
    private function getUserRole(int $workspaceId, int $userId): ?string
    {
        return DB::table('workspace_members')
            ->where('workspace_id', $workspaceId)
            ->where('user_id', $userId)
            ->value('role');
    }

    private function getModifiableWorkspace(int $workspaceId, int $userId, string $role, string $type): Workspace
    {
        $workspace = Workspace::where('id', $workspaceId)->first();
        if (!$workspace) {
            abort(401, 'Workspace not found.');
        }

        $message = match ($type) {
            "assign" => "assign {$role} to this workspace",
            "update" => "update role to {$role} in this workspace",
            "remove" => "remove {$role} from this workspace",
            default => '',
        };

        $userRole = $this->getUserRole($workspaceId, $userId);

        $isUserOwner = $userRole == 'owner';
        $isUserOwnerOrAdmin = $userRole == 'admin' || $userRole == 'owner';
        $isAuthorized = $role == 'admin' ? 
            $isUserOwner :
            $isUserOwnerOrAdmin;

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
        $users = DB::table('users')
            ->whereIn('email', $emails)
            ->pluck('id', 'email');

        $userIds = array_map(fn ($email) => $users[$email] ?? null, $emails);

        $workspaceUserIds = DB::table('workspace_members')
            ->where('workspace_id', $workspaceId)
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
    private function sendInvitation(int $workspaceId, string $workspaceName, string $userEmail, bool $userExists, string $role): void
    {
        $token = Str::random(64);
        $expiredAt = Carbon::now()->addHours(24);
        DB::table('workspace_invitations')->updateOrInsert(
            [
                'workspace_id' => $workspaceId,
                'user_email' => $userEmail,
            ],
            [
                'role' => $role,
                'token' => $token,
                'expired_at' => $expiredAt,
            ]
        );

        $acceptUrl = route('workspace-invitation.accept', ['token' => $token]);
        Notification::route('mail', $userEmail)
            ->notify(new WorkspaceInvitationNotification($workspaceName, $acceptUrl, $role, $userExists));
    }

    /**
     * Get list of unassigned users
     */
    public function unassigned(Request $request, int $workspaceId)
    {
        $search = trim($request->query('search', ''));
        $limit = $request->query('limit', 10);

        $userIds = DB::table('workspace_members')
            ->where('workspace_id', $workspaceId)
            ->pluck('user_id')
            ->all();

        $users = DB::table('users')
            ->whereNotIn('id', $userIds)
            ->where('email', 'like', "%{$search}%")
            ->orderBy('email', 'asc')
            ->limit($limit)
            ->get(['id', 'name', 'email']);

        return response()->json($users);
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
                $workspace->id,
                $workspace->name,
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

        DB::table('workspace_members')
            ->where('workspace_id', $workspace->id)
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
            'user_ids' => 'array',
            'user_ids.*' => 'numeric',
            'user_emails' => 'array',
            'user_emails.*' => 'email',
        ]);

        $workspace = $this->getModifiableWorkspace(
            $validated['workspace_id'],
            $request->user()->id,
            $validated['role'],
            'remove'
        );

        if (!empty($validated['user_ids'])) {
            DB::table('workspace_members')
                ->where('workspace_id', $workspace->id)
                ->whereIn('user_id', $validated['user_ids'])
                ->delete();
        }
        if (!empty($validated['user_emails'])) {
            DB::table('workspace_invitations')
                ->where('workspace_id', $workspace->id)
                ->whereIn('user_email', $validated['user_emails'])
                ->delete();
        }

        return Redirect::route('workspaces.edit', ['workspace_id' => $workspace->id]);
    }

    /**
     * Leave a workspace as a user
     */
    public function leave(Request $request, $workspaceId): RedirectResponse
    {
        $userId = $request->user()->id;

        $userRole = $this->getUserRole($workspaceId, $userId);
        if (!$userRole) {
            abort(404, 'You are not a member of this workspace.');
        }

        if ($userRole == 'owner') {
            abort(400, 'You cannot leave a workspace you own.');
        }

        DB::table('workspace_members')
            ->where('workspace_id', $workspaceId)
            ->where('user_id', $userId)
            ->delete();

        return Redirect::to('/');
    }

    
    /**
     * Accept a workspace invitation
     */
    public function accept(Request $request, $token): Response
    {
        // Find invitation by token
        $invitation = DB::table('workspace_invitations')
            ->where('token', $token)
            ->where('expired_at', '>', Carbon::now())
            ->first();
        
        if (!$invitation) {
            return Inertia::render('Workspace/Invitation', [
                'status' => 'invalid'
            ]);
        }

        // Find user id by email
        $userId = DB::table('users')->where('email', $invitation->user_email)->value('id');
        if (!$userId) {
            return Inertia::render('Workspace/Invitation', [
                'status' => 'unregistered',
            ]);
        }
        
        // Add user to workspace
        DB::table('workspace_members')->insert([
            'workspace_id' => $invitation->workspace_id,
            'user_id' => $userId,
            'role' => $invitation->role,
        ]);
        
        // Delete the invitation
        DB::table('workspace_invitations')
            ->where('id', $invitation->id)
            ->delete();
        
        return Inertia::render('Workspace/Invitation', [
                'status' => 'success',
            ]);
    }
}
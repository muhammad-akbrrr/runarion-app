<?php

namespace App\Http\Controllers;

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
    /**
     * Get the existence and membership status of users based on their emails within a workspace.
     *
     * @param array $emails An array of email addresses to check.
     * @param string $workspaceId The id of the workspace to check membership against.
     *
     * @return array{is_exists: bool, is_member: bool}[] 
     * An array with the same length as the $emails array. Each element has keys:
     *               - 'is_exists' (bool):  true if a user with the corresponding email exists
     *               - 'is_member' (bool):  true if the user is a member of the workspace
     */
    private function getExistAndMembershipStatus(array $emails, string $workspaceId): array
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
    private function sendInvitation(string $workspaceId, string $workspaceName, string $userEmail, bool $userExists, string $role): void
    {
        $token = Str::random(64);
        $expiredAt = Carbon::now()->addHours(1);
        DB::table('workspace_invitations')->updateOrInsert(
            [
                'workspace_id' => $workspaceId,
                'user_email' => $userEmail,
            ],
            [
                'id' => Str::ulid()->toString(),
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
     * Display form to update the workspace members
     */
    public function edit(Request $request, string $workspace_id): RedirectResponse|Response
    {
        $userRole = $request->attributes->get('user_role');
        $isUserOwner = $userRole === 'owner';
        $isUserAdmin = $userRole === 'admin';

        $limit = $request->query('limit', 10);
        $offset = $request->query('offset', 0);

        $workspaceMembers = DB::table('workspace_members')
            ->where('workspace_id', $workspace_id)
            ->join('users', 'workspace_members.user_id', '=', 'users.id')
            ->select(
                'users.id',
                'users.name',
                'users.email',
                'users.avatar_url',
                'workspace_members.role',
                'users.email_verified_at'
            );

        $workspaceInvitedMembers = DB::table('workspace_invitations')
            ->where('workspace_id', $workspace_id)
            ->leftJoin('users', 'workspace_invitations.user_email', '=', 'users.email')
            ->select(
                DB::raw('NULL as id'),
                'users.name',
                DB::raw('workspace_invitations.user_email as email'),
                'users.avatar_url',
                'workspace_invitations.role',
                'users.email_verified_at'
            );

        $unionQuery = $workspaceMembers->union($workspaceInvitedMembers);

        $combinedMembers = DB::query()
            ->fromSub($unionQuery, 'combined');

        $totalMembers = $combinedMembers->count();
            
        $members = $combinedMembers
            ->orderByRaw("CASE WHEN role = 'owner' THEN 1 WHEN role = 'admin' THEN 2 ELSE 3 END")
            ->orderByRaw("COALESCE(name, '')")
            ->limit($limit)
            ->offset($offset)
            ->get()
            ->map(fn ($member) => [
                'id' => $member->id,
                'name' => $member->name,
                'email' => $member->email,
                'avatar_url' => $member->avatar_url,
                'role' => $member->role,
                'is_verified' => $member->email_verified_at !== null,
            ])
            ->toArray();
        
        return Inertia::render('Workspace/Member', [
            'workspaceId' => $workspace_id,
            'limit' => $limit,
            'totalMembers' => $totalMembers,
            'members' => $members,
            'isUserAdmin' => $isUserAdmin,
            'isUserOwner' => $isUserOwner,
        ]);
    }

    /**
     * Get list of unassigned users
     */
    public function unassigned(Request $request, string $workspace_id)
    {
        $search = trim($request->query('search', ''));
        $limit = $request->query('limit', 10);

        $userIds = DB::table('workspace_members')
            ->where('workspace_id', $workspace_id)
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
    public function assign(Request $request, string $workspace_id): RedirectResponse
    {
        $validated = $request->validate([
            'role' => 'required|in:admin,member',
            'user_emails' => 'required|array',
            'user_emails.*' => 'email',
        ]);
        $targetUserRole = $validated['role'];
        $targetUserEmails = $validated['user_emails'];
        
        $workspace = DB::table('workspaces')->where('id', $workspace_id)->first();
        if (!$workspace) {
            abort(401, 'Workspace not found.');
        }

        $userRole = $request->attributes->get('user_role');

        $isAuthorized = $targetUserRole === 'admin' ? 
            $userRole === 'owner' : 
            in_array($userRole, ['admin', 'owner']);
        if (!$isAuthorized) {
            abort(403, "You are not authorized to assign {$targetUserRole} to this workspace.");
        }

        $userStatus = $this->getExistAndMembershipStatus($targetUserEmails, $workspace_id);

        foreach ($userStatus as $index => $status) {
            if ($status['is_member']) {
                continue;
            }
            $this->sendInvitation(
                $workspace_id,
                $workspace->name,
                $targetUserEmails[$index], 
                $status['is_exists'], 
                $targetUserRole
            );
        }
        
        return Redirect::route('workspace.edit.member', ['workspace_id' => $workspace_id]);
    }

    /**
     * Update user roles in a workspace
     */
    public function update(Request $request, string $workspace_id): RedirectResponse
    {
        $validated = $request->validate([
            'role' => 'required|in:admin,member',
            'user_id' => 'nullable|numeric',
            'user_email' => 'nullable|string|email',
        ]);
        $targetUserRole = $validated['role'];
        $targetUserId = $validated['user_id'] ?? null;
        $targetUserEmail = $validated['user_email'] ?? null;

        $userRole = $request->attributes->get('user_role');

        if ($userRole !== 'owner') {
            abort(403, 'You are not authorized to update member roles in this workspace.');
        }

        if ($targetUserId !== null) {
            $query = DB::table('workspace_members')
                ->where('workspace_id', $workspace_id)
                ->where('user_id', $targetUserId);
        } else if ($targetUserEmail !== null) {
            $query = DB::table('workspace_invitations')
                ->where('workspace_id', $workspace_id)
                ->where('user_email', $targetUserEmail);
        } else {
            abort(400, 'Either user_id or user_email must be provided.');
        }

        $query->update(['role' => $targetUserRole]);
        
        return Redirect::route('workspace.edit.member', ['workspace_id' => $workspace_id]);
    }

    /**
     * Remove users from a workspace
     */
    public function remove(Request $request, string $workspace_id): RedirectResponse
    {
        $validated = $request->validate([
            'user_id' => 'nullable|numeric',
            'user_email' => 'nullable|string|email',
        ]);
        $targetUserId = $validated['user_id'] ?? null;
        $targetUserEmail = $validated['user_email'] ?? null;

        $userRole = $request->attributes->get('user_role');
        
        if ($userRole !== 'owner' && $userRole !== 'admin') {
            abort(403, 'You are not authorized to remove members from this workspace.');
        }

        if ($targetUserId !== null) {
            $query = DB::table('workspace_members')
                ->where('workspace_id', $workspace_id)
                ->where('user_id', $targetUserId);
        } else if ($targetUserEmail !== null) {
            $query = DB::table('workspace_invitations')
                ->where('workspace_id', $workspace_id)
                ->where('user_email', $targetUserEmail);
        } else {
            abort(400, 'Either user_id or user_email must be provided.');
        }

        $targetUserRole = $query->value('role');

        if ($targetUserRole === null) {
            abort(404, 'User not found in the workspace.');
        }
        if ($targetUserRole == 'owner') {
            abort(400, 'You cannot remove the owner of a workspace.');
        }
        if ($targetUserRole == 'admin' && $userRole !== 'owner') {
            abort(403, 'You are not authorized to remove an admin.');
        }

        $query->delete();

        if ($targetUserId !== null) {
            DB::table('users')
                ->where('id', $targetUserId)
                ->update(['last_workspace_id' => null]);
        }

        return Redirect::route('workspace.edit.member', ['workspace_id' => $workspace_id]);
    }

    /**
     * Leave a workspace as a user
     */
    public function leave(Request $request, string $workspace_id): RedirectResponse
    {
        $user = $request->user();

        $userRole = $request->attributes->get('user_role');

        if ($userRole === 'owner') {
            abort(400, 'You cannot leave a workspace you own.');
        }

        DB::table('workspace_members')
            ->where('workspace_id', $workspace_id)
            ->where('user_id', $user->id)
            ->delete();

        $user->last_workspace_id = null;
        $defaultWorkspaceId = $user->getActiveWorkspaceId();

        return Redirect::route('workspace.dashboard', ['workspace_id' => $defaultWorkspaceId]);
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
            'id' => Str::ulid()->toString(),
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
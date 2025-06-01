<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Inertia\Inertia;
use Symfony\Component\HttpFoundation\Response;

class ResolveWorkspace
{
    /**
     * Handle an incoming request.
     *
     * @param  \Closure(\Illuminate\Http\Request): (\Symfony\Component\HttpFoundation\Response)  $next
     */
    public function handle(Request $request, Closure $next): Response
    {
        $workspaceId = $request->route('workspace_id');
        $user = $request->user();

        if (!$workspaceId && $request->isMethod('get') && $user) {
            $routeName = $request->route()->getName();
            if (str_starts_with($routeName, 'raw.')) {
                $routeName = substr($routeName, 4);
            }
            $defaultWorkspaceId = $request->user()->getActiveWorkspaceId();
            return redirect()->route($routeName, ['workspace_id' => $defaultWorkspaceId]);
        }

        $userWorkspace = DB::table('workspaces')
            ->leftJoin('workspace_members', function ($join) use ($user) {
                $join->on('workspaces.id', '=', 'workspace_members.workspace_id')
                     ->where('workspace_members.user_id', '=', $user->id);
            })
            ->where('workspaces.id', $workspaceId)
            ->select('workspace_members.role')
            ->first();

        if (!$userWorkspace) {
            abort(404, 'Workspace not found');
        }

        if (!$userWorkspace->role) {
            abort(403, 'You are not a member of this workspace');
        }

        $userRole = $userWorkspace->role;

        if ($user->last_workspace_id !== $workspaceId) {
            $user->last_workspace_id = $workspaceId;
            $user->saveQuietly();

            Inertia::share([
                'auth' => [
                    'user' => $user,
                    'csrf_token' => csrf_token(),
                ],
            ]);
        }

        $request->attributes->set('user_role', $userRole);

        return $next($request);
    }
}

<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Inertia\Inertia;
use Symfony\Component\HttpFoundation\Response;

class ResolveProjectEditor
{
    /**
     * Handle an incoming request.
     *
     * @param  \Closure(\Illuminate\Http\Request): (\Symfony\Component\HttpFoundation\Response)  $next
     */
    public function handle(Request $request, Closure $next): Response
    {
        $workspaceId = $request->route('workspace_id');
        $projectId = $request->route('project_id');
        $user = $request->user();

        // Handle raw routes (routes without workspace_id) - redirect to default workspace
        if (!$workspaceId && $request->isMethod('get') && $user) {
            $routeName = $request->route()->getName();
            if (str_starts_with($routeName, 'raw.')) {
                $routeName = substr($routeName, 4);
            }
            $defaultWorkspaceId = $request->user()->getActiveWorkspaceId();
            return redirect()->route($routeName, ['workspace_id' => $defaultWorkspaceId, 'project_id' => $projectId]);
        }

        // Validate workspace access
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

        // Validate project access
        $project = DB::table('projects')
            ->where('id', $projectId)
            ->where('workspace_id', $workspaceId)
            ->where('is_active', true)
            ->first();

        if (!$project) {
            abort(404, 'Project not found');
        }

        // Check if user has access to the project
        $hasProjectAccess = false;
        if ($project->access) {
            $access = json_decode($project->access, true);
            foreach ($access as $accessEntry) {
                if ((string) $accessEntry['user']['id'] === (string) $user->id) {
                    $hasProjectAccess = true;
                    break;
                }
            }
        }

        // Original author always has access
        if ((string) $project->original_author === (string) $user->id) {
            $hasProjectAccess = true;
        }

        if (!$hasProjectAccess) {
            abort(403, 'You do not have access to this project');
        }

        // Check if this is a workspace switch
        $isWorkspaceSwitch = $user->last_workspace_id !== $workspaceId;
        // Check if this is a project switch
        $isProjectSwitch = $user->last_project_id !== $projectId;

        if ($isWorkspaceSwitch || $isProjectSwitch) {
            if ($isWorkspaceSwitch) {
                $user->last_workspace_id = $workspaceId;
            }
            if ($isProjectSwitch) {
                $user->last_project_id = $projectId;
            }
            $user->saveQuietly();
            // Force refresh the user in the session
            auth()->setUser($user);

            // Set session flags ONLY if a real switch happened
            // If both workspace and project are switching, only set project_switching
            if ($isWorkspaceSwitch && $isProjectSwitch) {
                session(['project_switching' => true]);
            } else {
                if ($isWorkspaceSwitch) {
                    session(['workspace_switching' => true]);
                }
                if ($isProjectSwitch) {
                    session(['project_switching' => true]);
                }
            }
        }

        // Detect if coming from a non-editor page (using referer)
        $referer = $request->headers->get('referer');
        $shouldForceLoader = true;
        if ($referer) {
            // Adjust this regex to match all your editor routes
            $isEditorReferer = preg_match('/\/projects\/[^\/]+\/editor/', $referer);
            if ($isEditorReferer) {
                $shouldForceLoader = false;
            }
        }
        if ($shouldForceLoader) {
            session(['force_project_editor_loader' => true]);
        }

        Inertia::share([
            'auth' => [
                'user' => $user,
                'csrf_token' => csrf_token(),
            ],
            'workspace_switching' => session()->pull('workspace_switching', false),
            'project_switching' => session()->pull('project_switching', false),
            'force_project_editor_loader' => session()->pull('force_project_editor_loader', false),
            'project_completed_onboarding' => $project->completed_onboarding ?? false,
        ]);

        $request->attributes->set('user_role', $userRole);
        $request->attributes->set('project', $project);

        return $next($request);
    }
}

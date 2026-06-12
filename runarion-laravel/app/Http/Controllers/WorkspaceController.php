<?php

namespace App\Http\Controllers;

use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Redirect;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Inertia\Inertia;
use Inertia\Response;

class WorkspaceController extends Controller
{
    private function canUpdate(Request $request): void
    {
        $userRole = $request->attributes->get('user_role');
        if ($userRole !== 'owner' && $userRole !== 'admin') {
            abort(403, 'You are not authorized to update this workspace.');
        }
    }

    private function canDestroy(Request $request): void
    {
        $userRole = $request->attributes->get('user_role');
        if ($userRole !== 'owner') {
            abort(403, 'You are not authorized to delete this workspace.');
        }
    }

    /**
     * Display all workspaces for the authenticated user.
     */
    public function index(Request $request): Response
    {
        $workspaces = DB::table('workspaces')
            ->join('workspace_members', 'workspaces.id', '=', 'workspace_members.workspace_id')
            ->where('workspace_members.user_id', $request->user()->id)
            ->select('workspaces.*', 'workspace_members.role')
            ->get()
            ->map(fn ($workspace) => [
                'id' => $workspace->id,
                'name' => $workspace->name,
                'slug' => $workspace->slug,
                'cover_image_url' => $workspace->cover_image_url,
                'role' => $workspace->role,
            ]);

        return Inertia::render('Workspace/List', [
            'workspaces' => $workspaces,
        ]);
    }

    /**
     * Display form to update the workspace.
     */
    public function edit(Request $request, string $workspace_id): RedirectResponse|Response
    {
        $userRole = $request->attributes->get('user_role');
        $isUserOwner = $userRole === 'owner';
        $isUserAdmin = $userRole === 'admin';

        $workspace = DB::table('workspaces')
            ->where('id', $workspace_id)
            ->first(['id', 'name', 'slug', 'cover_image_url', 'timezone', 'permissions', 'is_active']);
        if (! $workspace) {
            abort(401, 'Workspace not found.');
        }

        $workspace->permissions = json_decode($workspace->permissions ?? '{}', true);

        return Inertia::render('Workspace/Edit', [
            'workspace' => $workspace,
            'isUserAdmin' => $isUserAdmin,
            'isUserOwner' => $isUserOwner,
        ]);
    }

    public function usage(Request $request, string $workspace_id): RedirectResponse|Response
    {
        $userRole = $request->attributes->get('user_role');
        $isUserOwner = $userRole === 'owner';
        $isUserAdmin = $userRole === 'admin';

        $workspace = DB::table('workspaces')
            ->where('id', $workspace_id)
            ->first(['id', 'name', 'monthly_token_quota', 'billing_cycle_anchor_at']);

        if (! $workspace) {
            abort(401, 'Workspace not found.');
        }

        $quota = (int) ($workspace->monthly_token_quota ?? 25000000);

        $currentPeriod = null;
        if (Schema::hasTable('workspace_usage_periods')) {
            $currentPeriod = DB::table('workspace_usage_periods')
                ->where('workspace_id', $workspace_id)
                ->orderByDesc('period_start_at')
                ->first();
        }

        $featureBreakdown = [];
        $projectBreakdown = [];

        if (Schema::hasTable('generation_logs')) {
            $logsQuery = DB::table('generation_logs')
                ->where('generation_logs.workspace_id', $workspace_id)
                ->where('generation_logs.success', true);

            if ($currentPeriod) {
                $logsQuery
                    ->where('generation_logs.created_at', '>=', $currentPeriod->period_start_at)
                    ->where('generation_logs.created_at', '<', $currentPeriod->period_end_at);
            }

            $featureBreakdown = (clone $logsQuery)
                ->selectRaw("COALESCE(feature, 'other') as label, COALESCE(SUM(billable_total_tokens), SUM(total_tokens), 0) as total")
                ->groupBy('label')
                ->orderByDesc('total')
                ->get()
                ->map(fn ($row) => [
                    'label' => $row->label,
                    'percentage' => $quota > 0 ? round((((int) $row->total) / $quota) * 100, 2) : 0,
                ])
                ->all();

            $projectBreakdown = (clone $logsQuery)
                ->leftJoin('projects', 'generation_logs.project_id', '=', 'projects.id')
                ->selectRaw("COALESCE(projects.name, 'Workspace-wide') as label, COALESCE(SUM(generation_logs.billable_total_tokens), SUM(generation_logs.total_tokens), 0) as total")
                ->groupBy('label')
                ->orderByDesc('total')
                ->limit(5)
                ->get()
                ->map(fn ($row) => [
                    'label' => $row->label,
                    'percentage' => $quota > 0 ? round((((int) $row->total) / $quota) * 100, 2) : 0,
                ])
                ->all();
        }

        $usedTokens = (int) ($currentPeriod->tokens_consumed ?? 0);
        $reservedTokens = (int) ($currentPeriod->tokens_reserved ?? $usedTokens);
        $effectiveUsed = max($usedTokens, $reservedTokens);
        $usedPercentage = $quota > 0 ? min(100, round(($effectiveUsed / $quota) * 100, 2)) : 0;
        $remainingPercentage = max(0, round(100 - $usedPercentage, 2));

        return Inertia::render('Workspace/Usage', [
            'workspaceId' => $workspace_id,
            'workspaceName' => $workspace->name,
            'isUserAdmin' => $isUserAdmin,
            'isUserOwner' => $isUserOwner,
            'usage' => [
                'usedPercentage' => $usedPercentage,
                'remainingPercentage' => $remainingPercentage,
                'daysLeft' => $currentPeriod && ! empty($currentPeriod->period_end_at)
                    ? max(0, now()->diffInDays(\Illuminate\Support\Carbon::parse($currentPeriod->period_end_at), false))
                    : null,
                'featureBreakdown' => $featureBreakdown,
                'projectBreakdown' => $projectBreakdown,
                'periodStartAt' => $currentPeriod->period_start_at ?? null,
                'periodEndAt' => $currentPeriod->period_end_at ?? null,
            ],
        ]);
    }

    /**
     * Display form to update billing of the workspace.
     */
    public function editBilling(Request $request, string $workspace_id): RedirectResponse|Response
    {
        $userRole = $request->attributes->get('user_role');
        $isUserOwner = $userRole === 'owner';
        $isUserAdmin = $userRole === 'admin';

        return Inertia::render('Workspace/Billing', [
            'workspaceId' => $workspace_id,
            'isUserAdmin' => $isUserAdmin,
            'isUserOwner' => $isUserOwner,
        ]);
    }

    /**
     * Create a new workspace.
     */
    public function store(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'slug' => [
                'required',
                'regex:/^[a-z0-9]+(?:-[a-z0-9]+)*$/',
                'max:255',
                'unique:workspaces,slug',
            ],
            'photo' => 'nullable|image|max:2048',
        ]);

        $workspaceId = Str::ulid()->toString();
        $validated['id'] = $workspaceId;

        $validated['cover_image_url'] = ($request->hasFile('photo')
            ? '/storage/'.Storage::disk('public')
                ->putFile('workspace_photos', $request->file('photo'))
            : 'https://ui-avatars.com/api/?'.http_build_query([
                'name' => $validated['name'],
                'background' => 'random',
            ]));
        unset($validated['photo']);

        DB::table('workspaces')->insert($validated);

        DB::table('workspace_members')->insert([
            'id' => Str::ulid()->toString(),
            'workspace_id' => $workspaceId,
            'user_id' => $request->user()->id,
            'role' => 'owner',
        ]);

        return Redirect::route('workspace.dashboard', ['workspace_id' => $workspaceId]);
    }

    /**
     * Update the workspace.
     */
    public function update(Request $request, string $workspace_id): RedirectResponse
    {
        $this->canUpdate($request);

        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'timezone' => 'nullable|string|max:255',
            'permissions' => 'array',
            'permissions.*' => 'array',
            'permissions.*.*' => 'in:admin,member,guest',
            'photo' => 'nullable|image|max:2048',
        ]);

        if ($request->hasFile('photo')) {
            $prevPhotoUrl = DB::table('workspaces')
                ->where('id', $workspace_id)
                ->value('cover_image_url');
            if ($prevPhotoUrl) {
                $prevPhotoUrl = substr($prevPhotoUrl, strlen('/storage/'));
                Storage::disk('public')->delete($prevPhotoUrl);
            }
            $validated['cover_image_url'] = '/storage/'.Storage::disk('public')
                ->putFile('workspace_photos', $request->file('photo'));
        }
        unset($validated['photo']);

        DB::table('workspaces')
            ->where('id', $workspace_id)
            ->update($validated);

        return Redirect::route('workspace.edit', ['workspace_id' => $workspace_id]);
    }

    /**
     * Delete the workspace.
     */
    public function destroy(Request $request, string $workspace_id): RedirectResponse
    {
        $this->canUpdate($request);

        DB::table('workspaces')
            ->where('id', $workspace_id)
            ->delete();

        return Redirect::route('workspace.index');
    }
}

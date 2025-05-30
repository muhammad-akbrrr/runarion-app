<?php

namespace App\Http\Controllers;

use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Redirect;
use Inertia\Inertia;
use Inertia\Response;

class DashboardController extends Controller
{
    private function getDefaultWorkspaceId(int $userId): ?string
    {
        return DB::table('workspace_members')
            ->where('user_id', $userId)
            ->where('role', 'owner')
            ->value('workspace_id');
    }

    public function show(Request $request, string $workspace_id): RedirectResponse|Response
    {
        $isMember = DB::table('workspace_members')
            ->where('user_id', $request->user()->id)
            ->where('workspace_id', $workspace_id)
            ->exists();
            
        if (!$isMember) {
            $workspaceId = $this->getDefaultWorkspaceId($request->user()->id);
            return Redirect::route('workspace.dashboard', ['workspace_id' => $workspaceId]);
        }

        return Inertia::render('Dashboard', [
            'workspaceId' => $workspace_id,
        ]);
    }

    public function redirect(Request $request): RedirectResponse
    {
        $workspaceId = $this->getDefaultWorkspaceId($request->user()->id);

        return Redirect::route('workspace.dashboard', ['workspace_id' => $workspaceId]);
    }
}

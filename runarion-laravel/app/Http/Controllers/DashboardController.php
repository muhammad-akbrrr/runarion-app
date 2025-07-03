<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;
use App\Models\Workspace;
use App\Services\CloudStorage\CloudStorageProviderFactory;

class DashboardController extends Controller
{
    public function show(Request $request, string $workspace_id): Response
    {
        $workspace = Workspace::findOrFail($workspace_id);
        
        return Inertia::render('Dashboard', [
            'workspaceId'      => $workspace_id,
        ]);
    }
}

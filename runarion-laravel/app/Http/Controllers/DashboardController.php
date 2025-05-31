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
    public function show(Request $request, string $workspace_id): RedirectResponse|Response
    {
        return Inertia::render('Dashboard', [
            'workspaceId' => $workspace_id,
        ]);
    }
}

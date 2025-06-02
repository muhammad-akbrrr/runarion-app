<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;
use Illuminate\Http\RedirectResponse;
class ProjectController extends Controller
{
    public function show(Request $request, string $workspace_id): RedirectResponse|Response
    {
        return Inertia::render('Projects/ProjectList', [
            'workspaceId' => $workspace_id,
        ]);
    }
}

<?php

namespace App\Http\Controllers\ProjectEditor;

use Illuminate\Http\Request;
use App\Models\Projects;
use App\Http\Controllers\Controller;
use Inertia\Inertia;

class MainEditorController extends Controller
{
    public function updateProjectName(Request $request, string $workspace_id, string $project_id)
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
        ]);

        $project = Projects::findOrFail($project_id);
        $project->name = $validated['name'];
        $project->save();

        return Inertia::render('Projects/Editor/Main', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'projectName' => $project->name,
        ]);
    }
}

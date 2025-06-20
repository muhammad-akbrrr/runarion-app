<?php

namespace App\Http\Controllers\ProjectEditor;

use Illuminate\Http\Request;
use App\Http\Controllers\Controller;
use App\Models\Projects;
use Inertia\Inertia;

class ImageGeneratorController extends Controller
{
    /**
     * Show the image editor page inside of the project editor..
     */
    public function imageGenerator(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (!$project) {
            return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id]);
        }

        return Inertia::render('Projects/Editor/ImgGenerator/Main', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => $project,
        ]);
    }
}

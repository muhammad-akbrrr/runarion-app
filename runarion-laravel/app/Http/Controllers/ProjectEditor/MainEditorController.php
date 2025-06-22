<?php

namespace App\Http\Controllers\ProjectEditor;

use Illuminate\Http\Request;
use App\Models\Projects;
use App\Http\Controllers\Controller;
use Inertia\Inertia;
use Illuminate\Support\Str;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class MainEditorController extends Controller
{
    /**
     * Show the project editor page for a specific project.
     */
    public function editor(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (!$project) {
            return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id]);
        }

        return Inertia::render('Projects/Editor/Main', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => $project,
        ]);
    }

    /**
     * Update the current project name.
     */
    public function updateProjectName(Request $request, string $workspace_id, string $project_id)
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
        ]);

        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->firstOrFail();

        $project->name = $validated['name'];
        $project->slug = Str::slug($validated['name']);
        $project->save();

        return Inertia::render('Projects/Editor/Main', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => $project,
        ]);
    }

    /**
     * Generate story content using the Python API.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  string  $workspace_id
     * @param  string  $project_id
     * @return \Illuminate\Http\RedirectResponse
     */
    public function generate(Request $request, string $workspace_id, string $project_id)
    {
        try {
            // Make the API call to the Python service
            $response = Http::post('http://python-app:5000/api/generate', $request);

            // Log the response for debugging
            Log::info('Python API Response', ['response' => $response->json()]);

            // Check if the request was successful
            if ($response->successful()) {
                $responseData = $response->json();

                // Ensure 'success' field exists
                if (!isset($responseData['success'])) {
                    $responseData['success'] = true;
                }

                // Flash the response data to the session
                return redirect()->back()->with('data', $responseData);
            }

            // Flash the failure response
            return redirect()->back()->with('data', [
                'success' => false,
                'error_message' => 'Failed to generate story: ' . $response->body(),
            ]);
        } catch (\Exception $e) {
            Log::error('Story generation error: ' . $e->getMessage());

            // Flash the exception error
            return redirect()->back()->with('data', [
                'success' => false,
                'error_message' => 'An error occurred while generating the story: ' . $e->getMessage(),
            ]);
        }
    }
}

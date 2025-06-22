<?php

namespace App\Http\Controllers\ProjectEditor;

use Illuminate\Http\Request;
use App\Models\Projects;
use App\Models\ProjectContent;
use App\Models\Workspace;
use App\Http\Controllers\Controller;
use Inertia\Inertia;
use Illuminate\Support\Str;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Auth;

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

        // Get the project content for the default chapter
        $projectContent = ProjectContent::where('project_id', $project_id)
            ->where('chapter_id', 'chapter_1')
            ->first();

        // If no content exists, create an empty one
        if (!$projectContent) {
            $projectContent = new ProjectContent([
                'project_id' => $project_id,
                'chapter_id' => 'chapter_1',
                'content' => '',
                'editor_state' => null,
                'word_count' => 0,
                'character_count' => 0,
                'version' => 1,
            ]);
            $projectContent->save();
        }

        return Inertia::render('Projects/Editor/Main', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => $project,
            'projectContent' => $projectContent,
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
     * Save the project content.
     */
    public function saveContent(Request $request, string $workspace_id, string $project_id)
    {
        $validated = $request->validate([
            'content' => 'required|string',
            'chapter_id' => 'required|string',
            'editor_state' => 'nullable|array',
        ]);

        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->firstOrFail();

        // Calculate word and character counts
        $wordCount = ProjectContent::calculateWordCount($validated['content']);
        $characterCount = ProjectContent::calculateCharacterCount($validated['content']);

        // Find or create project content
        $projectContent = ProjectContent::updateOrCreate(
            [
                'project_id' => $project_id,
                'chapter_id' => $validated['chapter_id'],
            ],
            [
                'content' => $validated['content'],
                'editor_state' => $validated['editor_state'],
                'word_count' => $wordCount,
                'character_count' => $characterCount,
                'last_edited_at' => now(),
            ]
        );

        // Increment version if content has changed
        if ($projectContent->wasChanged('content')) {
            $projectContent->version += 1;
            $projectContent->save();
        }

        // Always redirect back with flash data for Inertia
        return redirect()->back()->with([
            'success' => true,
            'message' => 'Content saved successfully',
            'projectContent' => $projectContent,
        ]);
    }

    /**
     * Auto-save the project content.
     */
    public function autoSaveContent(Request $request, string $workspace_id, string $project_id)
    {
        $validated = $request->validate([
            'content' => 'required|string',
            'chapter_id' => 'required|string',
            'editor_state' => 'nullable|array',
        ]);

        // Find or create project content
        $projectContent = ProjectContent::updateOrCreate(
            [
                'project_id' => $project_id,
                'chapter_id' => $validated['chapter_id'],
            ],
            [
                'content' => $validated['content'],
                'editor_state' => $validated['editor_state'],
                'word_count' => ProjectContent::calculateWordCount($validated['content']),
                'character_count' => ProjectContent::calculateCharacterCount($validated['content']),
                'last_autosaved_at' => now(),
            ]
        );

        // Always redirect back with flash data for Inertia
        return redirect()->back()->with([
            'success' => true,
            'message' => 'Content auto-saved successfully',
            'last_autosaved_at' => $projectContent->last_autosaved_at,
        ]);
    }

    /**
     * Load project content for a specific chapter.
     */
    public function loadContent(Request $request, string $workspace_id, string $project_id)
    {
        $validated = $request->validate([
            'chapter_id' => 'required|string',
        ]);

        $projectContent = ProjectContent::where('project_id', $project_id)
            ->where('chapter_id', $validated['chapter_id'])
            ->first();

        if (!$projectContent) {
            // Create a new empty content for this chapter
            $projectContent = new ProjectContent([
                'project_id' => $project_id,
                'chapter_id' => $validated['chapter_id'],
                'content' => '',
                'editor_state' => null,
                'word_count' => 0,
                'character_count' => 0,
                'version' => 1,
                'last_edited_at' => now(),
            ]);
            $projectContent->save();
        }

        // Always return Inertia response
        return Inertia::render('Projects/Editor/Main', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => Projects::findOrFail($project_id),
            'projectContent' => $projectContent,
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

                // If successful, update the project content
                if ($responseData['success'] && isset($responseData['text'])) {
                    $chapterId = $request->input('chapter_id', 'chapter_1');
                    
                    // Get the current project content
                    $projectContent = ProjectContent::where('project_id', $project_id)
                        ->where('chapter_id', $chapterId)
                        ->first();
                    
                    // If no content exists, create a new one
                    if (!$projectContent) {
                        $projectContent = new ProjectContent([
                            'project_id' => $project_id,
                            'chapter_id' => $chapterId,
                            'content' => $responseData['text'] ?? '',
                            'editor_state' => $request->input('generation_config'),
                            'word_count' => ProjectContent::calculateWordCount($responseData['text'] ?? ''),
                            'character_count' => ProjectContent::calculateCharacterCount($responseData['text'] ?? ''),
                            'version' => 1,
                            'last_edited_at' => now(),
                        ]);
                    } else {
                        // Append the generated text to the existing content
                        $newContent = $projectContent->content . ($responseData['text'] ?? '');
                        
                        // Update the project content
                        $projectContent->content = $newContent;
                        $projectContent->word_count = ProjectContent::calculateWordCount($newContent);
                        $projectContent->character_count = ProjectContent::calculateCharacterCount($newContent);
                        $projectContent->version += 1;
                        $projectContent->last_edited_at = now();
                        
                        // Update editor state if provided
                        if ($request->has('generation_config')) {
                            $projectContent->editor_state = $request->input('generation_config');
                        }
                    }
                    
                    // Save the project content
                    $projectContent->save();
                }

                // Always redirect back with flash data for Inertia
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

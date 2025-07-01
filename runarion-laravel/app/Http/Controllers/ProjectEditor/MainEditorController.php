<?php

namespace App\Http\Controllers\ProjectEditor;

use Illuminate\Http\Request;
use App\Models\Projects;
use App\Models\ProjectContent;
use App\Http\Controllers\Controller;
use Inertia\Inertia;
use Illuminate\Support\Str;
use Illuminate\Support\Facades\Auth;
use App\Jobs\ManuscriptDeconstructionJob;
use App\Jobs\StreamLLMJob;
use App\Events\ProjectContentUpdated;
use App\Events\LLMStreamCompleted;
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

        // Query project content
        $projectContent = ProjectContent::where('project_id', $project_id)->first();

        // Extract chapters from JSON content field
        $chapters = [];
        if ($projectContent && $projectContent->content && is_array($projectContent->content)) {
            $chapters = $projectContent->content;
        }

        return Inertia::render('Projects/Editor/Main', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => $project,
            'chapters' => $chapters,
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

        // Extract chapters from JSON content field
        $chapters = [];
        if ($project && $project->content && is_array($project->content)) {
            $chapters = $project->content;
        }

        return redirect()->route('workspace.projects.editor', [
            'workspace_id' => $workspace_id,
            'project_id' => $project_id,
        ]);
    }

    /**
     * Function to handle the project onboarding process.
     */
    public function projectOnboarding(Request $request, string $workspace_id, string $project_id)
    {
        $method = $request->input('method');
        if ($method === 'scratch') {
            $project = Projects::where('id', $project_id)
                ->where('workspace_id', $workspace_id)
                ->firstOrFail();
            $project->completed_onboarding = true;
            $project->save();

            $chapters = [];
            if ($project && $project->content && is_array($project->content)) {
                $chapters = $project->content;
            }

            return Inertia::render('Projects/Editor/Main', [
                'workspaceId' => $workspace_id,
                'projectId' => $project_id,
                'project' => $project,
                'chapters' => $chapters,
            ]);
        }

        if ($method === 'draft') {
            $user = Auth::user();
            $validated = $request->validate([
                'draft_file' => 'required|file|mimes:pdf|max:102400',
                'author_style_type' => 'required|in:existing,new',
                'writing_perspective' => 'required|string',
                'selectedAuthorStyle' => 'required_if:author_style_type,existing',
                'newAuthorFiles' => 'required_if:author_style_type,new|array|sometimes',
                'newAuthorFiles.*' => 'file|mimes:pdf|max:102400|sometimes',
                'newAuthorName' => 'required_if:author_style_type,new|sometimes|string',
            ]);

            // Store draft file
            $draftFile = $request->file('draft_file');
            $draftPath = $draftFile->store('drafts', 'local');
            $draftFullPath = storage_path('app/' . $draftPath);

            // Add file existence check and log
            if (!file_exists($draftFullPath)) {
                throw new \Exception('Draft file missing after store: ' . $draftFullPath);
            }

            $authorStyleType = $validated['author_style_type'];
            $authorStyleId = null;
            $authorSamplePaths = [];
            $newAuthorName = null;

            if ($authorStyleType === 'existing') {
                $authorStyleId = $validated['selectedAuthorStyle'];
            } else if ($authorStyleType === 'new') {
                $newAuthorName = $validated['newAuthorName'];
                $newAuthorFiles = $request->file('newAuthorFiles', []);
                foreach ($newAuthorFiles as $idx => $file) {
                    $path = $file->store('author_samples', 'local');
                    $authorSamplePaths[] = storage_path('app/' . $path);
                }
            }

            $writingPerspective = $validated['writing_perspective'];

            // Dispatch the job
            ManuscriptDeconstructionJob::dispatch(
                $user ? $user->id : null,
                $workspace_id,
                $project_id,
                $draftFullPath,
                $authorStyleType,
                $authorStyleId,
                $authorSamplePaths,
                $newAuthorName,
                $writingPerspective
            );

            return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id]);
        }
        return response()->json(['error' => 'Invalid method'], 400);
    }

    /**
     * Function to handle adding Chapters to a project's Content.
     */
    public function storeProjectChapter(Request $request, string $workspace_id, string $project_id)
    {
        $validated = $request->validate([
            'chapter_name' => 'required|string|max:255',
        ]);

        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->firstOrFail();

        $projectContent = ProjectContent::where('project_id', $project_id)->first();
        if (!$projectContent) {
            // If no content exists, create a new ProjectContent
            $projectContent = ProjectContent::create([
                'project_id' => $project_id,
                'content' => [],
            ]);
        }

        $chapters = $projectContent->content ?? [];
        $newOrder = count($chapters);
        $newChapter = [
            'order' => $newOrder,
            'chapter_name' => $validated['chapter_name'],
            'content' => '',
            'summary' => null,
            'plot_points' => null,
        ];
        $chapters[] = $newChapter;
        $projectContent->content = $chapters;
        $projectContent->save();

        return redirect()->route('workspace.projects.editor', [
            'workspace_id' => $workspace_id,
            'project_id' => $project_id,
        ]);
    }

    /**
     * Function to handle project Saves with broadcasting.
     */
    public function updateProjectData(Request $request, string $workspace_id, string $project_id)
    {
        $validated = $request->validate([
            'order' => 'required|integer',
            'content' => 'nullable|string',
            'trigger' => 'nullable|string|in:manual,auto,llm_generation',
        ]);

        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->firstOrFail();

        $projectContent = ProjectContent::where('project_id', $project_id)->firstOrFail();
        $chapters = $projectContent->content ?? [];

        foreach ($chapters as &$chapter) {
            if (isset($chapter['order']) && $chapter['order'] === $validated['order']) {
                $chapter['content'] = $validated['content'] ?? '';
                break;
            }
        }

        $projectContent->content = $chapters;
        $projectContent->updateLastEdited();
        $projectContent->save();

        // Broadcast content update event
        broadcast(new ProjectContentUpdated(
            $workspace_id,
            $project_id,
            $validated['order'],
            $validated['content'] ?? '',
            $validated['trigger'] ?? 'manual'
        ));

        // Extract chapters from JSON content field
        $chapters = $projectContent->content ?? [];

        return redirect()->route('workspace.projects.editor', [
            'workspace_id' => $workspace_id,
            'project_id' => $project_id,
        ]);
    }

    /**
     * Function to handle project settings updates.
     */
    public function updateProjectSettings(Request $request, string $workspace_id, string $project_id)
    {
        $validated = $request->validate([
            'currentPreset' => 'nullable|string',
            'authorProfile' => 'nullable|string',
            'aiModel' => 'nullable|string',
            'memory' => 'nullable|string',
            'storyGenre' => 'nullable|string',
            'storyTone' => 'nullable|string',
            'storyPov' => 'nullable|string',
            'temperature' => 'nullable|numeric|min:0|max:2',
            'repetitionPenalty' => 'nullable|numeric|min:-2|max:2',
            'outputLength' => 'nullable|integer|min:50|max:1000',
            'minOutputToken' => 'nullable|integer|min:1|max:100',
            'topP' => 'nullable|numeric|min:0|max:1',
            'tailFree' => 'nullable|numeric|min:0|max:1',
            'topA' => 'nullable|numeric|min:0|max:1',
            'topK' => 'nullable|numeric|min:0|max:1',
            'phraseBias' => 'nullable|array',
            'phraseBias.*' => 'nullable|array',
            'bannedPhrases' => 'nullable|array',
            'bannedPhrases.*' => 'nullable|string',
            'stopSequences' => 'nullable|array',
            'stopSequences.*' => 'nullable|string',
        ]);

        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->firstOrFail();

        // Update the settings JSON column
        $project->settings = $validated;
        $project->save();

        return redirect()->route('workspace.projects.editor', [
            'workspace_id' => $workspace_id,
            'project_id' => $project_id,
        ]);
    }

    /**
     * Function to handle LLM text generation with streaming.
     */
    public function generateText(Request $request, string $workspace_id, string $project_id)
    {
        try {
            $validated = $request->validate([
                'prompt' => 'required|string',
                'order' => 'required|integer',
                'settings' => 'nullable|array',
                'settings.aiModel' => 'nullable|string',
                'settings.storyGenre' => 'nullable|string',
                'settings.storyTone' => 'nullable|string',
                'settings.storyPov' => 'nullable|string',
                'settings.temperature' => 'nullable|numeric|min:0|max:2',
                'settings.repetitionPenalty' => 'nullable|numeric|min:-2|max:2',
                'settings.outputLength' => 'nullable|integer|min:50|max:1000',
                'settings.minOutputToken' => 'nullable|integer|min:1|max:100',
                'settings.topP' => 'nullable|numeric|min:0|max:1',
                'settings.tailFree' => 'nullable|numeric|min:0|max:1',
                'settings.topA' => 'nullable|numeric|min:0|max:1',
                'settings.topK' => 'nullable|numeric|min:0|max:1',
                'settings.phraseBias' => 'nullable|array',
                'settings.bannedPhrases' => 'nullable|array',
                'settings.stopSequences' => 'nullable|array',
            ]);

            $project = Projects::where('id', $project_id)
                ->where('workspace_id', $workspace_id)
                ->firstOrFail();

            $user = Auth::user();
            if (!$user) {
                return response()->json(['error' => 'User not authenticated'], 401);
            }

            $settings = $validated['settings'] ?? [];

            // Generate a unique session ID for this generation
            $sessionId = Str::uuid()->toString();

            // Verify the chapter exists
            $projectContent = ProjectContent::where('project_id', $project_id)->first();
            if (!$projectContent) {
                return response()->json(['error' => 'Project content not found'], 404);
            }

            $chapterExists = false;
            $chapters = $projectContent->content ?? [];
            foreach ($chapters as $chapter) {
                if (isset($chapter['order']) && $chapter['order'] === $validated['order']) {
                    $chapterExists = true;
                    break;
                }
            }

            if (!$chapterExists) {
                return response()->json(['error' => 'Chapter not found'], 404);
            }

            // Log the generation request
            Log::info('Text generation request', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'chapter_order' => $validated['order'],
                'session_id' => $sessionId,
                'user_id' => $user->id,
                'model' => $settings['aiModel'] ?? 'default',
            ]);

            // Dispatch streaming job
            StreamLLMJob::dispatch(
                $workspace_id,
                $project_id,
                $validated['order'],
                $validated['prompt'],
                $settings,
                $user->id,
                $sessionId
            );

            return redirect()->route('workspace.projects.editor', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
            ]);
            
        } catch (\Exception $e) {
            Log::error('Error starting text generation', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            return redirect()->route('workspace.projects.editor', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
            ]);
        }
    }
    
    /**
     * Function to handle cancellation of text generation.
     */
    public function cancelGeneration(Request $request, string $workspace_id, string $project_id)
    {
        try {
            $validated = $request->validate([
                'session_id' => 'required|string',
                'chapter_order' => 'required|integer',
            ]);

            $project = Projects::where('id', $project_id)
                ->where('workspace_id', $workspace_id)
                ->firstOrFail();

            $user = Auth::user();
            if (!$user) {
                return response()->json(['error' => 'User not authenticated'], 401);
            }

            Log::info('Cancelling text generation', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'chapter_order' => $validated['chapter_order'],
                'session_id' => $validated['session_id'],
                'user_id' => $user->id,
            ]);

            // Broadcast a completion event with cancelled status
            broadcast(new LLMStreamCompleted(
                $workspace_id,
                $project_id,
                $validated['chapter_order'],
                $validated['session_id'],
                '',
                false,
                'Generation cancelled by user'
            ));

            return response()->json([
                'success' => true,
                'message' => 'Text generation cancelled.',
            ]);
        } catch (\Exception $e) {
            Log::error('Error cancelling text generation', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            return response()->json([
                'success' => false,
                'message' => 'Failed to cancel text generation: ' . $e->getMessage(),
            ], 500);
        }
    }
}

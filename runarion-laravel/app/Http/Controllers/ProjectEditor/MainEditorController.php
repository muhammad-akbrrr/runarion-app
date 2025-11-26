<?php

namespace App\Http\Controllers\ProjectEditor;

use Illuminate\Http\Request;
use App\Models\Projects;
use App\Models\ProjectContent;
use App\Http\Controllers\Controller;
use Inertia\Inertia;
use Illuminate\Support\Str;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;
use App\Jobs\ManuscriptDeconstructionJob;
use App\Jobs\StreamLLMJob;
use App\Events\ProjectContentUpdated;
use App\Events\LLMStreamCompleted;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use App\Services\VersionControlService;
use App\Events\OperationStateChanged;

class MainEditorController extends Controller
{
    protected VersionControlService $versionControl;

    public function __construct(VersionControlService $versionControl)
    {
        $this->versionControl = $versionControl;
    }
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
            
            // Get current content from version control for each chapter
            foreach ($chapters as &$chapter) {
                $currentContent = $this->versionControl->getCurrentContent($project_id, $chapter['order']);
                if ($currentContent !== null) {
                    $chapter['content'] = $currentContent;
                }
                
                // Add navigation info for version control
                $chapter['navigation_info'] = $this->versionControl->getNavigationInfo($project_id, $chapter['order']);
            }
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

        return back()->with('success', 'Project name updated successfully.');
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
            'content' => 'nullable|string|max:1000000',
            'trigger' => 'nullable|string|in:manual,auto,llm_generation',
        ]);

        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->firstOrFail();

        // Use database transaction for consistency
        DB::transaction(function () use ($validated, $project_id, $workspace_id) {
            $projectContent = ProjectContent::where('project_id', $project_id)->firstOrFail();
            $chapters = $projectContent->content ?? [];

            // Update chapter content in JSON
            foreach ($chapters as &$chapter) {
                if (isset($chapter['order']) && $chapter['order'] === $validated['order']) {
                    $chapter['content'] = $validated['content'] ?? '';
                    break;
                }
            }

            $projectContent->content = $chapters;
            $projectContent->updateLastEdited();
            $projectContent->save();

            // Initialize version control if needed and update current content
            $currentContent = $this->versionControl->getCurrentContent($project_id, $validated['order']);
            if ($currentContent === null) {
                $this->versionControl->initializeChapter($project_id, $validated['order'], $validated['content'] ?? '');
            }
        });

        // Broadcast content update event
        broadcast(new ProjectContentUpdated(
            $workspace_id,
            $project_id,
            $validated['order'],
            $validated['content'] ?? '',
            $validated['trigger'] ?? 'manual'
        ));

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
                'prompt' => 'nullable|string',
                'order' => 'required|integer',
                'settings' => 'nullable|array',
                'settings.currentPreset' => 'nullable|string',
                'settings.aiModel' => 'nullable|string',
                'settings.memory' => 'nullable|string',
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

            // Get current content and node info for parent tracking
            $currentContent = $this->versionControl->getCurrentContent($project_id, $validated['order']);
            if ($currentContent === null) {
                // Initialize if not exists
                $currentContent = $validated['prompt'] ?? '';
                $this->versionControl->initializeChapter($project_id, $validated['order'], $currentContent);
            }

            Log::info('Text generation request', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'chapter_order' => $validated['order'],
                'settings' => $settings,
                'session_id' => $sessionId,
                'user_id' => $user->id,
                'model' => $settings['aiModel'] ?? 'default',
            ]);

            // Dispatch streaming job
            StreamLLMJob::dispatch(
                $workspace_id,
                $project_id,
                $validated['order'],
                $currentContent,
                $settings,
                $user->id,
                $sessionId,
                false // isRegenerate flag
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

            if (str_contains($e->getMessage(), 'quota') || str_contains($e->getMessage(), 'limit')) {
                return redirect()->route('workspace.projects.editor', [
                    'workspace_id' => $workspace_id,
                    'project_id' => $project_id,
                ])->withErrors(['generation' => 'Generation quota exceeded. Please try again later.']);
            }

            return redirect()->route('workspace.projects.editor', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
            ])->withErrors(['generation' => 'Failed to start text generation.']);
        }
    }

    /**
     * Function to handle unified project data and settings updates.
     */
    public function updateProjectUnified(Request $request, string $workspace_id, string $project_id)
    {
        Log::info('Incoming request payload', $request->all());
        $validated = $request->validate([
            // Content validation
            'content' => 'nullable|array',
            'content.order' => 'required_with:content|integer',
            'content.content' => 'sometimes|nullable|string|max:1000000',
            'content.trigger' => 'nullable|string|in:manual,auto,llm_generation',
            
            // Settings validation
            'settings' => 'nullable|array',
            'settings.currentPreset' => 'nullable|string',
            'settings.authorProfile' => 'nullable|string',
            'settings.aiModel' => 'nullable|string',
            'settings.memory' => 'nullable|string',
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
            'settings.phraseBias.*' => 'nullable|array',
            'settings.bannedPhrases' => 'nullable|array',
            'settings.bannedPhrases.*' => 'nullable|string',
            'settings.stopSequences' => 'nullable|array',
            'settings.stopSequences.*' => 'nullable|string',
        ]);

        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->firstOrFail();

        $updatedChapters = null;

        // Use database transaction for consistency
        \DB::transaction(function () use ($validated, $project, $project_id, $workspace_id, &$updatedChapters) {
            // Update content if provided
            if (isset($validated['content'])) {
                $contentData = $validated['content'];
                
                $projectContent = ProjectContent::where('project_id', $project_id)->firstOrFail();
                $chapters = $projectContent->content ?? [];

                // Update chapter content
                foreach ($chapters as &$chapter) {
                    if (isset($chapter['order']) && $chapter['order'] === $contentData['order']) {
                        $chapter['content'] = $contentData['content'];
                        break;
                    }
                }

                $projectContent->content = $chapters;
                $projectContent->updateLastEdited();
                
                // Also update the current step version in generation history
                $projectContent->updateCurrentStepVersion($contentData['order'], $contentData['content']);
                
                $projectContent->save();

                $updatedChapters = $chapters;

                // Broadcast content update event
                broadcast(new ProjectContentUpdated(
                    $workspace_id,
                    $project_id,
                    $contentData['order'],
                    $contentData['content'] ?? '',
                    $contentData['trigger'] ?? 'manual'
                ));
            }

            // Update settings if provided
            if (isset($validated['settings'])) {
                $project->settings = $validated['settings'];
                $project->save();
            }
        });

        Log::info('Unified project update completed', [
            'workspace_id' => $workspace_id,
            'project_id' => $project_id,
            'content_updated' => isset($validated['content']),
            'settings_updated' => isset($validated['settings']),
        ]);

        return redirect()->route('workspace.projects.editor', [
            'workspace_id' => $workspace_id,
            'project_id' => $project_id,
        ]);
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

    /**
     * Function to handle text regeneration (create new version of current step).
     */
    public function regenerateText(Request $request, string $workspace_id, string $project_id)
    {
        try {
            $validated = $request->validate([
                'order' => 'required|integer',
                'settings' => 'nullable|array',
                'settings.currentPreset' => 'nullable|string',
                'settings.aiModel' => 'nullable|string',
                'settings.memory' => 'nullable|string',
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

            // Check if regeneration is possible
            $navigationInfo = $this->versionControl->getNavigationInfo($project_id, $validated['order']);
            if (!$navigationInfo['canRegenerate']) {
                return response()->json(['error' => 'Cannot regenerate - no parent content available'], 400);
            }

            $settings = $validated['settings'] ?? [];
            $sessionId = Str::uuid()->toString();

            // Get current state to know which node we're regenerating
            $currentState = $this->versionControl->getCurrentState($project_id, $validated['order']);
            if (!$currentState) {
                return response()->json(['error' => 'Cannot find current state'], 400);
            }

            // Get parent content for prompting (but don't switch to parent node)
            $parentContent = '';
            $currentNode = \App\Models\ContentNode::find($currentState['node_id']);
            if ($currentNode && $currentNode->parent_node_id) {
                $parentNode = \App\Models\ContentNode::find($currentNode->parent_node_id);
                if ($parentNode) {
                    $parentVersionIndex = $currentNode->parent_version_index ?? 0;
                    $parentVersion = $parentNode->versions()
                        ->where('version_index', $parentVersionIndex)
                        ->first();
                    if ($parentVersion) {
                        $parentContent = $parentVersion->content;
                    }
                }
            }

            // Show parent content in canvas for regeneration
            broadcast(new ProjectContentUpdated(
                $workspace_id,
                $project_id,
                $validated['order'],
                $parentContent,
                'regenerate_switch_to_parent'
            ));

            Log::info('Text regeneration request', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'chapter_order' => $validated['order'],
                'current_node_id' => $currentState['node_id'],
                'parent_content_length' => strlen($parentContent),
                'session_id' => $sessionId,
                'user_id' => $user->id,
            ]);

            // Dispatch streaming job for regeneration with current node ID
            StreamLLMJob::dispatch(
                $workspace_id,
                $project_id,
                $validated['order'],
                $parentContent,
                $settings,
                $user->id,
                $sessionId,
                true, // isRegenerate flag
                $currentState['node_id'] // Pass current node ID for regeneration
            );

            return redirect()->route('workspace.projects.editor', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
            ]);

        } catch (\Exception $e) {
            Log::error('Error starting text regeneration', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            if (str_contains($e->getMessage(), 'quota') || str_contains($e->getMessage(), 'limit')) {
                return redirect()->route('workspace.projects.editor', [
                    'workspace_id' => $workspace_id,
                    'project_id' => $project_id,
                ])->withErrors(['generation' => 'Generation quota exceeded. Please try again later.']);
            }

            return redirect()->route('workspace.projects.editor', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
            ])->withErrors(['generation' => 'Failed to start text regeneration.']);
        }
    }

    /**
     * Function to handle version switching within current step.
     */
    public function switchVersion(Request $request, string $workspace_id, string $project_id)
    {
        try {
            $validated = $request->validate([
                'order' => 'required|integer',
                'version_index' => 'required|integer|min:0',
            ]);

            $project = Projects::where('id', $project_id)
                ->where('workspace_id', $workspace_id)
                ->firstOrFail();

            $result = $this->versionControl->switchVersion($project_id, $validated['order'], $validated['version_index']);

            if (!$result) {
                return response()->json(['error' => 'Failed to switch version'], 400);
            }

            // Broadcast content update event
            broadcast(new ProjectContentUpdated(
                $workspace_id,
                $project_id,
                $validated['order'],
                $result['content'],
                'version_switch'
            ));

            return redirect()->route('workspace.projects.editor', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
            ]);

        } catch (\Exception $e) {
            Log::error('Error switching version', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            return response()->json([
                'success' => false,
                'message' => 'Failed to switch version: ' . $e->getMessage(),
            ], 500);
        }
    }

    /**
     * Function to handle undo operation (go to parent step).
     */
    public function undoStep(Request $request, string $workspace_id, string $project_id)
    {
        try {
            $validated = $request->validate([
                'order' => 'required|integer',
            ]);

            $project = Projects::where('id', $project_id)
                ->where('workspace_id', $workspace_id)
                ->firstOrFail();

            // Lock operation
            broadcast(new OperationStateChanged(
                $workspace_id,
                $project_id,
                $validated['order'],
                'undo',
                true
            ));

            $result = $this->versionControl->undoToParent($project_id, $validated['order']);

            if (!$result) {
                broadcast(new OperationStateChanged(
                    $workspace_id,
                    $project_id,
                    $validated['order'],
                    'undo',
                    false
                ));
                return response()->json(['error' => 'Cannot undo - no parent step available'], 400);
            }

            // Get updated navigation info
            $navigationInfo = $this->versionControl->getNavigationInfo($project_id, $validated['order']);

            // Broadcast content update and unlock
            broadcast(new ProjectContentUpdated(
                $workspace_id,
                $project_id,
                $validated['order'],
                $result['content'] ?? '',
                'undo_step'
            ));

            broadcast(new OperationStateChanged(
                $workspace_id,
                $project_id,
                $validated['order'],
                'undo',
                false,
                $navigationInfo
            ));

            return redirect()->route('workspace.projects.editor', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
            ]);

        } catch (\Exception $e) {
            Log::error('Error undoing step', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            broadcast(new OperationStateChanged(
                $workspace_id,
                $project_id,
                $validated['order'] ?? 0,
                'undo',
                false
            ));

            return response()->json([
                'success' => false,
                'message' => 'Failed to undo step: ' . $e->getMessage(),
            ], 500);
        }
    }

    /**
     * Function to handle redo operation (go to last selected child step).
     */
    public function redoStep(Request $request, string $workspace_id, string $project_id)
    {
        try {
            $validated = $request->validate([
                'order' => 'required|integer',
            ]);

            $project = Projects::where('id', $project_id)
                ->where('workspace_id', $workspace_id)
                ->firstOrFail();

            $result = $this->versionControl->redoToChild($project_id, $validated['order']);

            if (!$result) {
                return response()->json(['error' => 'Cannot redo - no child steps available'], 400);
            }

            // Broadcast content update event
            broadcast(new ProjectContentUpdated(
                $workspace_id,
                $project_id,
                $validated['order'],
                $result['content'] ?? '',
                'redo_step'
            ));

            return redirect()->route('workspace.projects.editor', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
            ]);

        } catch (\Exception $e) {
            Log::error('Error redoing step', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            return response()->json([
                'success' => false,
                'message' => 'Failed to redo step: ' . $e->getMessage(),
            ], 500);
        }
    }

    /**
     * Function to initialize generation history for a chapter.
     */
    public function initializeChapterHistory(Request $request, string $workspace_id, string $project_id)
    {
        try {
            $validated = $request->validate([
                'order' => 'required|integer',
                'content' => 'nullable|string',
            ]);

            $project = Projects::where('id', $project_id)
                ->where('workspace_id', $workspace_id)
                ->firstOrFail();

            // Initialize version control for the chapter
            $this->versionControl->initializeChapter($project_id, $validated['order'], $validated['content'] ?? '');

            Log::info('Chapter history initialized', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'chapter_order' => $validated['order'],
            ]);

            return redirect()->route('workspace.projects.editor', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
            ]);

        } catch (\Exception $e) {
            Log::error('Error initializing chapter history', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            return response()->json([
                'success' => false,
                'message' => 'Failed to initialize chapter history: ' . $e->getMessage(),
            ], 500);
        }
    }

    /**
     * Function to get version control info for a chapter.
     */
    public function getVersionControlInfo(Request $request, string $workspace_id, string $project_id)
    {
        try {
            $validated = $request->validate([
                'order' => 'required|integer',
            ]);

            $project = Projects::where('id', $project_id)
                ->where('workspace_id', $workspace_id)
                ->firstOrFail();

            $navigationInfo = $this->versionControl->getNavigationInfo($project_id, $validated['order']);

            return response()->json([
                'success' => true,
                'data' => $navigationInfo,
            ]);

        } catch (\Exception $e) {
            Log::error('Error getting version control info', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            return response()->json([
                'success' => false,
                'message' => 'Failed to get version control info: ' . $e->getMessage(),
            ], 500);
        }
    }
}

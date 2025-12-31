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
use Illuminate\Support\Facades\Cache;
use App\Services\VersionControlService;
use App\Events\OperationStateChanged;
use App\Models\AuthorStyle;

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
        try {
            $project = Projects::where('id', $project_id)
                ->where('workspace_id', $workspace_id)
                ->first();

            if (!$project) {
                return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id])
                    ->withErrors(['project' => 'Project not found']);
            }

            // Query project content
            $projectContent = ProjectContent::where('project_id', $project_id)->first();

            // Extract chapters from JSON content field
            $chapters = [];
            if ($projectContent && $projectContent->content && is_array($projectContent->content)) {
                $chapters = $projectContent->content;

                // Get current content from version control for each chapter
                foreach ($chapters as &$chapter) {
                    try {
                        $currentContent = $this->versionControl->getCurrentContent($project_id, $chapter['order']);
                        if ($currentContent !== null) {
                            $chapter['content'] = $currentContent;
                        }

                        // Add navigation info for version control
                        $chapter['navigation_info'] = $this->versionControl->getNavigationInfo($project_id, $chapter['order']);
                    } catch (\Exception $e) {
                        Log::warning('Error getting version control info for chapter', [
                            'project_id' => $project_id,
                            'chapter_order' => $chapter['order'] ?? null,
                            'error' => $e->getMessage()
                        ]);
                        // Continue with default content
                    }
                }
            }

            // Get author styles for this workspace
            $authorStyles = AuthorStyle::where('workspace_id', $workspace_id)
                ->get()
                ->map(function ($style) {
                    $colors = ['bg-blue-100', 'bg-purple-100', 'bg-green-100', 'bg-pink-100', 'bg-amber-100', 'bg-cyan-100'];
                    $colorIndex = crc32($style->id) % count($colors);
                    return [
                        'id' => $style->id,
                        'name' => $style->author_name,
                        'status' => $style->status ?? 'init_completed',
                        'avatar' => strtoupper(substr($style->author_name, 0, 1)),
                        'color' => $colors[$colorIndex],
                    ];
                });

            return Inertia::render('Projects/Editor/Main', [
                'workspaceId' => $workspace_id,
                'projectId' => $project_id,
                'project' => $project,
                'chapters' => $chapters,
                'authorStyles' => $authorStyles,
            ]);
        } catch (\Exception $e) {
            Log::error('Error loading editor', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id])
                ->withErrors(['editor' => 'Failed to load editor: ' . $e->getMessage()]);
        }
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

            // Get chapters from ProjectContent (where Chapter 1 is stored)
            $projectContent = ProjectContent::where('project_id', $project_id)->first();
            $chapters = [];
            if ($projectContent && $projectContent->content && is_array($projectContent->content)) {
                $chapters = $projectContent->content;
            }

            // Get author styles for this workspace
            $authorStyles = AuthorStyle::where('workspace_id', $workspace_id)
                ->get()
                ->map(function ($style) {
                    $colors = ['bg-blue-100', 'bg-purple-100', 'bg-green-100', 'bg-pink-100', 'bg-amber-100', 'bg-cyan-100'];
                    $colorIndex = crc32($style->id) % count($colors);
                    return [
                        'id' => $style->id,
                        'name' => $style->author_name,
                        'status' => $style->status ?? 'init_completed',
                        'avatar' => strtoupper(substr($style->author_name, 0, 1)),
                        'color' => $colors[$colorIndex],
                    ];
                });

            return Inertia::render('Projects/Editor/Main', [
                'workspaceId' => $workspace_id,
                'projectId' => $project_id,
                'project' => $project,
                'chapters' => $chapters,
                'authorStyles' => $authorStyles,
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

        // Validate for duplicate chapter names (case-insensitive with whitespace trimming)
        $normalizedNewName = strtolower(trim($validated['chapter_name']));

        foreach ($chapters as $chapter) {
            $existingName = strtolower(trim($chapter['chapter_name']));
            if ($existingName === $normalizedNewName) {
                return back()->withErrors([
                    'chapter_name' => "A chapter named '{$chapter['chapter_name']}' already exists."
                ]);
            }
        }

        $newOrder = count($chapters);

        // Defensive cleanup: ensure no leftover version control data exists for this order
        // This can happen if a chapter was deleted but version control wasn't cleaned up properly

        try {
            $this->versionControl->deleteChapterVersionControl($project_id, $newOrder);
        } catch (\Exception $e) {
            // Log but don't fail - this is defensive cleanup
            Log::warning('Error cleaning up version control when creating new chapter', [
                'project_id' => $project_id,
                'chapter_order' => $newOrder,
                'error' => $e->getMessage()
            ]);
        }

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
     * Get all chapters for a project as JSON.
     */
    public function getChapters(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (!$project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $projectContent = ProjectContent::where('project_id', $project_id)->first();
        $chapters = [];

        if ($projectContent && $projectContent->content && is_array($projectContent->content)) {
            $chapters = $projectContent->content;

            // Get current content from version control for each chapter (same as editor method)
            foreach ($chapters as &$chapter) {
                try {
                    $currentContent = $this->versionControl->getCurrentContent($project_id, $chapter['order']);
                    if ($currentContent !== null) {
                        $chapter['content'] = $currentContent;
                    }
                } catch (\Exception $e) {
                    Log::warning('Error getting version control content for chapter in getChapters', [
                        'project_id' => $project_id,
                        'chapter_order' => $chapter['order'] ?? null,
                        'error' => $e->getMessage()
                    ]);
                    // Keep existing content if any
                }
            }
        }

        return response()->json([
            'success' => true,
            'chapters' => $chapters
        ], 200);
    }

    /**
     * Update a chapter's title and/or content.
     */
    public function updateChapter(Request $request, string $workspace_id, string $project_id, int $order)
    {
        $validated = $request->validate([
            'chapter_name' => 'sometimes|string|max:255',
            'content' => 'sometimes|string',
        ]);

        // Ensure at least one field is provided
        if (empty($validated)) {
            return response()->json([
                'error' => 'At least chapter_name or content must be provided'
            ], 422);
        }

        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->firstOrFail();

        $projectContent = ProjectContent::where('project_id', $project_id)->firstOrFail();
        $chapters = $projectContent->content ?? [];

        // Validate for duplicate chapter names (excluding current chapter) if chapter_name is being updated
        if (isset($validated['chapter_name'])) {
            $normalizedNewName = strtolower(trim($validated['chapter_name']));
            foreach ($chapters as $chapter) {
                if ($chapter['order'] !== $order) {
                    $existingName = strtolower(trim($chapter['chapter_name']));
                    if ($existingName === $normalizedNewName) {
                        return response()->json([
                            'error' => "A chapter named '{$chapter['chapter_name']}' already exists."
                        ], 422);
                    }
                }
            }
        }

        // Update chapter fields
        $updated = false;
        foreach ($chapters as &$chapter) {
            if (isset($chapter['order']) && $chapter['order'] === $order) {
                if (isset($validated['chapter_name'])) {
                    $chapter['chapter_name'] = $validated['chapter_name'];
                }
                if (isset($validated['content'])) {
                    $chapter['content'] = $validated['content'];
                }
                $updated = true;
                break;
            }
        }

        if (!$updated) {
            return response()->json([
                'error' => 'Chapter not found'
            ], 404);
        }

        $projectContent->content = $chapters;
        $projectContent->save();

        return response()->json([
            'success' => true,
            'message' => 'Chapter updated successfully',
            'chapters' => $chapters
        ], 200);
    }

    /**
     * Delete a chapter.
     */
    public function deleteChapter(Request $request, string $workspace_id, string $project_id, int $order)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->firstOrFail();

        $projectContent = ProjectContent::where('project_id', $project_id)->firstOrFail();
        $chapters = $projectContent->content ?? [];

        // Remove the chapter (use == for type-coerced comparison to handle int/string mismatch)
        $chapterCountBefore = count($chapters);
        $chapters = array_filter($chapters, function ($chapter) use ($order) {
            // Use != instead of !== to allow type coercion (e.g., "3" == 3)
            return isset($chapter['order']) && (int) $chapter['order'] != (int) $order;
        });
        $chapterCountAfter = count($chapters);

        Log::info('Chapter deletion', [
            'project_id' => $project_id,
            'order_to_delete' => $order,
            'chapters_before' => $chapterCountBefore,
            'chapters_after' => $chapterCountAfter,
            'deleted' => $chapterCountBefore - $chapterCountAfter
        ]);

        // Build mapping of old orders to new orders for version control reordering
        // Before reordering, capture the old orders
        $oldOrders = [];
        foreach (array_values($chapters) as $index => $chapter) {
            $oldOrder = $chapter['order'] ?? $index;
            $oldOrders[$oldOrder] = $index; // Map old order => new order
        }

        // Reorder remaining chapters
        $reorderedChapters = [];
        foreach (array_values($chapters) as $index => $chapter) {
            $chapter['order'] = $index;
            $reorderedChapters[] = $chapter;
        }

        $projectContent->content = $reorderedChapters;
        $projectContent->save();

        // Clean up version control for the deleted chapter
        try {
            $this->versionControl->deleteChapterVersionControl($project_id, $order);
        } catch (\Exception $e) {
            Log::warning('Error cleaning up version control for deleted chapter', [
                'project_id' => $project_id,
                'chapter_order' => $order,
                'error' => $e->getMessage()
            ]);
        }

        // Reorder version control data for remaining chapters
        // Only reorder chapters that actually changed order
        if (!empty($oldOrders)) {
            try {
                $this->versionControl->reorderChapters($project_id, $oldOrders);
            } catch (\Exception $e) {
                Log::warning('Error reordering version control data after chapter deletion', [
                    'project_id' => $project_id,
                    'order_mapping' => $oldOrders,
                    'error' => $e->getMessage()
                ]);
            }
        }

        return response()->json([
            'success' => true,
            'message' => 'Chapter deleted successfully',
            'chapters' => $reorderedChapters
        ], 200);
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
                'chapter_name' => 'nullable|string|max:500',
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

            // Extract chapter_name (prioritize request, fallback to lookup)
            $chapterName = $validated['chapter_name'] ?? null;

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
                    // If chapter_name wasn't provided, look it up from database
                    if (!$chapterName) {
                        $chapterName = $chapter['chapter_name'] ?? 'Untitled';
                    }
                    break;
                }
            }

            if (!$chapterExists) {
                return response()->json(['error' => 'Chapter not found'], 404);
            }

            // Final fallback for chapter name
            $chapterName = $chapterName ?? 'Untitled';

            // CRITICAL: Use the prompt from request (current editor content), not database
            // The frontend sends the current editor content as 'prompt'
            $currentContent = $validated['prompt'] ?? '';

            // Initialize version control if needed
            $existingContent = $this->versionControl->getCurrentContent($project_id, $validated['order']);
            if ($existingContent === null) {
                $this->versionControl->initializeChapter($project_id, $validated['order'], $currentContent);
            }
            // Note: We don't update version control here - the current content is what user typed
            // Version control will create a new node when generation completes

            Log::info('Text generation request', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'chapter_order' => $validated['order'],
                'prompt_length' => strlen($currentContent),
                'settings' => $settings,
                'session_id' => $sessionId,
                'user_id' => $user->id,
                'model' => $settings['aiModel'] ?? 'default',
            ]);

            // Dispatch streaming job with CURRENT editor content
            StreamLLMJob::dispatch(
                $workspace_id,
                $project_id,
                $validated['order'],
                $currentContent, // Use current editor content, not stale database content
                $settings,
                $user->id,
                $sessionId,
                false, // isRegenerate flag
                null, // regenerateNodeId
                $chapterName // chapter name for AI context
            );

            return redirect()->route('workspace.projects.editor', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
            ]);

        } catch (\Illuminate\Validation\ValidationException $e) {
            Log::warning('Validation error in text generation', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'errors' => $e->errors()
            ]);

            return redirect()->route('workspace.projects.editor', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
            ])->withErrors($e->errors());

        } catch (\Illuminate\Database\Eloquent\ModelNotFoundException $e) {
            Log::error('Project or chapter not found for generation', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'error' => $e->getMessage()
            ]);

            return redirect()->route('workspace.projects.editor', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
            ])->withErrors(['generation' => 'Project or chapter not found. Please refresh the page.']);

        } catch (\Exception $e) {
            Log::error('Error starting text generation', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'error' => $e->getMessage(),
                'type' => get_class($e),
                'trace' => $e->getTraceAsString(),
            ]);

            $errorMessage = 'Failed to start text generation. Please try again.';

            // Provide specific error messages
            if (str_contains($e->getMessage(), 'quota') || str_contains($e->getMessage(), 'limit')) {
                $errorMessage = 'Generation quota exceeded. Please try again later.';
            } elseif (str_contains($e->getMessage(), 'authentication') || str_contains($e->getMessage(), 'API key')) {
                $errorMessage = 'AI service authentication failed. Please check your API keys.';
            } elseif (str_contains($e->getMessage(), 'connection') || str_contains($e->getMessage(), 'network')) {
                $errorMessage = 'Failed to connect to AI service. Please check your connection.';
            } elseif (str_contains($e->getMessage(), 'timeout')) {
                $errorMessage = 'Request timed out. Please try again.';
            }

            return redirect()->route('workspace.projects.editor', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
            ])->withErrors(['generation' => $errorMessage]);
        }
    }

    /**
     * Function to handle unified project data and settings updates.
     */
    public function updateProjectUnified(Request $request, string $workspace_id, string $project_id)
    {
        try {
            Log::info('Incoming unified save request', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'has_content' => $request->has('content'),
                'has_settings' => $request->has('settings'),
                'request_id' => Str::uuid()->toString()
            ]);

            $validated = $request->validate([
                // Content validation
                'content' => 'nullable|array',
                'content.order' => 'required_with:content|integer',
                'content.content' => 'sometimes|nullable|string|max:1000000',
                'content.trigger' => 'nullable|string|in:manual,auto,llm_generation',
                'content.ai_ranges' => 'nullable|array',
                'content.ai_ranges.*' => 'nullable|array',
                'content.ai_ranges.*.*' => 'nullable|integer',

                // Settings validation
                'settings' => 'nullable|array',
                'settings.currentPreset' => 'nullable|string',
                'settings.authorProfile' => 'nullable|string',
                'settings.aiModel' => 'nullable|string',
                'settings.selectionToolbarMode' => 'nullable|string|in:formatting,ai-rewrite',
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

            // Use database transaction for consistency with deadlock retry
            $maxAttempts = 3;
            $attempt = 0;
            $lastException = null;

            while ($attempt < $maxAttempts) {
                try {
                    \DB::transaction(function () use ($validated, $project, $project_id, $workspace_id, &$updatedChapters) {
                        // Update content if provided
                        if (isset($validated['content'])) {
                            $contentData = $validated['content'];

                            $projectContent = ProjectContent::where('project_id', $project_id)->firstOrFail();
                            $chapters = $projectContent->content ?? [];

                            // Update chapter content and ai_ranges in JSON
                            foreach ($chapters as &$chapter) {
                                if (isset($chapter['order']) && $chapter['order'] === $contentData['order']) {
                                    $chapter['content'] = $contentData['content'] ?? '';
                                    // Update ai_ranges if provided
                                    if (array_key_exists('ai_ranges', $contentData)) {
                                        $chapter['ai_ranges'] = $contentData['ai_ranges'];
                                    }
                                    break;
                                }
                            }

                            $projectContent->content = $chapters;
                            $projectContent->content_format = 'lexical-json';
                            $projectContent->updateLastEdited();
                            $projectContent->save();

                            // CRITICAL FIX: Also update version control current content
                            // This is the key fix - after generation, manual edits must update the ContentVersion
                            $currentState = $this->versionControl->getCurrentState($project_id, $contentData['order']);

                            if ($currentState) {
                                // Update the current version's content
                                // This ensures that getCurrentContent() returns the manually edited content
                                $updated = $this->versionControl->updateCurrentVersion(
                                    $currentState['node_id'],
                                    $currentState['version_index'],
                                    $contentData['content'] ?? ''
                                );

                                if (!$updated) {
                                    Log::warning('Failed to update version control, but ProjectContent saved', [
                                        'project_id' => $project_id,
                                        'chapter_order' => $contentData['order'],
                                        'node_id' => $currentState['node_id'],
                                        'version_index' => $currentState['version_index']
                                    ]);
                                }
                            } else {
                                // Initialize if doesn't exist (first save before any generation)
                                $this->versionControl->initializeChapter(
                                    $project_id,
                                    $contentData['order'],
                                    $contentData['content'] ?? ''
                                );
                            }

                            // Clear cache to ensure fresh data on next load
                            Cache::forget("content:{$project_id}:{$contentData['order']}");
                            Cache::forget("navigation:{$project_id}:{$contentData['order']}");

                            $updatedChapters = $chapters;

                            Log::info('Unified save completed', [
                                'project_id' => $project_id,
                                'chapter_order' => $contentData['order'],
                                'content_length' => strlen($contentData['content'] ?? ''),
                                'trigger' => $contentData['trigger'] ?? 'manual',
                                'version_control_updated' => isset($currentState)
                            ]);

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
                            // Merge settings to preserve existing values
                            $existingSettings = $project->settings ?? [];
                            $newSettings = $validated['settings'] ?? [];
                            $project->settings = array_merge($existingSettings, $newSettings);
                            $project->save();

                            // Log settings save for debugging
                            Log::info('Settings saved', [
                                'project_id' => $project_id,
                                'aiModel' => $project->settings['aiModel'] ?? 'not set',
                                'all_settings' => $project->settings,
                            ]);

                            Log::info('Settings updated', [
                                'project_id' => $project_id,
                                'settings_keys' => array_keys($validated['settings'])
                            ]);
                        }
                    });

                    // Transaction succeeded, break out of retry loop
                    break;

                } catch (\Illuminate\Database\QueryException $e) {
                    $attempt++;
                    $lastException = $e;

                    // Check if it's a deadlock or lock timeout
                    $isDeadlock = str_contains($e->getMessage(), 'Deadlock') ||
                        str_contains($e->getMessage(), 'Lock wait timeout') ||
                        $e->getCode() === '40001' ||
                        $e->getCode() === '40P01';

                    if ($isDeadlock && $attempt < $maxAttempts) {
                        // Wait with exponential backoff before retrying
                        $delay = min(100 * pow(2, $attempt - 1), 1000); // 100ms, 200ms, 400ms max
                        usleep($delay * 1000);

                        Log::warning('Database deadlock detected, retrying', [
                            'attempt' => $attempt,
                            'max_attempts' => $maxAttempts,
                            'delay_ms' => $delay,
                            'project_id' => $project_id,
                            'error' => $e->getMessage()
                        ]);

                        continue;
                    }

                    // Not a deadlock or max attempts reached
                    throw $e;
                }
            }

            Log::info('Unified project update completed', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'content_updated' => isset($validated['content']),
                'settings_updated' => isset($validated['settings']),
                'attempts' => $attempt + 1
            ]);

            // For XHR/Inertia PATCH requests, return the updated chapters as JSON
            // This prevents page reloads and allows the frontend to update state
            return response()->json([
                'success' => true,
                'chapters' => $updatedChapters,
                'message' => 'Content saved successfully'
            ]);

        } catch (\Illuminate\Validation\ValidationException $e) {
            Log::warning('Validation error in unified save', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'errors' => $e->errors()
            ]);

            return back()->withErrors($e->errors())->withInput();

        } catch (\Illuminate\Database\Eloquent\ModelNotFoundException $e) {
            Log::error('Project not found in unified save', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'error' => $e->getMessage()
            ]);

            return back()->withErrors([
                'save' => 'Project not found. Please refresh the page.'
            ])->setStatusCode(404);

        } catch (\Illuminate\Database\QueryException $e) {
            Log::error('Database error in unified save', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'error' => $e->getMessage(),
                'code' => $e->getCode(),
                'trace' => $e->getTraceAsString()
            ]);

            $errorMessage = 'Failed to save changes due to a database error. Please try again.';

            // Check for specific database errors
            if (str_contains($e->getMessage(), 'Deadlock') || str_contains($e->getMessage(), 'Lock wait timeout')) {
                $errorMessage = 'Save failed due to concurrent updates. Please try again.';
            } elseif (str_contains($e->getMessage(), 'Duplicate entry')) {
                $errorMessage = 'Duplicate data detected. Please check your input.';
            } elseif (str_contains($e->getMessage(), 'Data too long')) {
                $errorMessage = 'Content is too large. Please reduce the size and try again.';
            }

            return back()->withErrors([
                'save' => $errorMessage
            ])->setStatusCode(500);

        } catch (\Exception $e) {
            Log::error('Unexpected error in unified save', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);

            return back()->withErrors([
                'save' => 'An unexpected error occurred. Please try again.'
            ])->setStatusCode(500);
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

    /**
     * Function to handle text regeneration (create new version of current step).
     */
    public function regenerateText(Request $request, string $workspace_id, string $project_id)
    {
        try {
            $validated = $request->validate([
                'order' => 'required|integer',
                'chapter_name' => 'nullable|string|max:500',
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

            // Extract chapter_name (prioritize request, fallback to lookup)
            $chapterName = $validated['chapter_name'] ?? null;
            if (!$chapterName) {
                $projectContent = ProjectContent::where('project_id', $project_id)->first();
                if ($projectContent && $projectContent->content) {
                    foreach ($projectContent->content as $chapter) {
                        if (isset($chapter['order']) && $chapter['order'] === $validated['order']) {
                            $chapterName = $chapter['chapter_name'] ?? 'Untitled';
                            break;
                        }
                    }
                }
            }
            $chapterName = $chapterName ?? 'Untitled';

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
                $currentState['node_id'], // Pass current node ID for regeneration
                $chapterName // chapter name for AI context
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

            // Get updated navigation info
            $navigationInfo = $this->versionControl->getNavigationInfo($project_id, $validated['order']);

            // Broadcast content update event with version info for frontend caching
            broadcast(new ProjectContentUpdated(
                $workspace_id,
                $project_id,
                $validated['order'],
                $result['content'],
                'version_switch',
                $result['version_index'] ?? $validated['version_index'],
                $navigationInfo
            ));

            // Broadcast operation state change with navigation info
            broadcast(new OperationStateChanged(
                $workspace_id,
                $project_id,
                $validated['order'],
                'version_switch',
                false,
                $navigationInfo
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

            // Broadcast content update with version info for frontend caching
            broadcast(new ProjectContentUpdated(
                $workspace_id,
                $project_id,
                $validated['order'],
                $result['content'] ?? '',
                'undo_step',
                $result['version_index'] ?? null,
                $navigationInfo
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

            // Get updated navigation info
            $navigationInfo = $this->versionControl->getNavigationInfo($project_id, $validated['order']);

            // Broadcast content update with version info for frontend caching
            broadcast(new ProjectContentUpdated(
                $workspace_id,
                $project_id,
                $validated['order'],
                $result['content'] ?? '',
                'redo_step',
                $result['version_index'] ?? null,
                $navigationInfo
            ));

            // Broadcast operation state change with navigation info
            broadcast(new OperationStateChanged(
                $workspace_id,
                $project_id,
                $validated['order'],
                'redo',
                false,
                $navigationInfo
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
     * Function to handle selection-based text rewriting.
     * Takes selected text with context and rewrites it using AI.
     */
    public function rewriteSelection(Request $request, string $workspace_id, string $project_id)
    {
        try {
            $validated = $request->validate([
                'selected_text' => 'required|string|min:1|max:10000',
                'context_before' => 'nullable|string|max:2000',
                'context_after' => 'nullable|string|max:2000',
                'action' => 'required|string|in:rewrite,humanize,custom',
                'custom_instruction' => 'nullable|string|max:500',
                'chapter_order' => 'required|integer',
                'model' => 'nullable|string',
            ]);

            $project = Projects::where('id', $project_id)
                ->where('workspace_id', $workspace_id)
                ->firstOrFail();

            $user = Auth::user();
            if (!$user) {
                return response()->json(['error' => 'User not authenticated'], 401);
            }

            // Determine the model to use
            $model = $validated['model'] ?? $project->settings['aiModel'] ?? 'gemini-2.5-flash';

            // Map model names to provider
            $provider = 'gemini';
            if (str_starts_with($model, 'gpt-')) {
                $provider = 'openai';
            } elseif (str_starts_with($model, 'deepseek')) {
                $provider = 'deepseek';
            }

            Log::info('Selection rewrite request', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'chapter_order' => $validated['chapter_order'],
                'action' => $validated['action'],
                'selected_text_length' => strlen($validated['selected_text']),
                'model' => $model,
                'user_id' => $user->id,
            ]);

            // Call Python API for rewrite
            $pythonApiUrl = env('PYTHON_SERVICE_URL', 'http://python-app:5000');

            $response = Http::timeout(60)->post("{$pythonApiUrl}/api/rewrite-selection", [
                'project_id' => $project_id,
                'workspace_id' => $workspace_id,
                'selected_text' => $validated['selected_text'],
                'context_before' => $validated['context_before'] ?? '',
                'context_after' => $validated['context_after'] ?? '',
                'action' => $validated['action'],
                'custom_instruction' => $validated['custom_instruction'] ?? '',
                'model' => $model,
                'provider' => $provider,
            ]);

            if (!$response->successful()) {
                $error = $response->json('error') ?? 'Failed to rewrite text';
                Log::error('Rewrite API error', [
                    'status' => $response->status(),
                    'error' => $error,
                ]);
                return response()->json(['error' => $error], $response->status());
            }

            $result = $response->json();

            return response()->json([
                'success' => true,
                'new_text' => $result['new_text'] ?? '',
                'action' => $validated['action'],
            ]);

        } catch (\Illuminate\Validation\ValidationException $e) {
            Log::warning('Validation error in rewrite selection', [
                'errors' => $e->errors()
            ]);
            return response()->json(['error' => 'Invalid request', 'details' => $e->errors()], 422);

        } catch (\Illuminate\Database\Eloquent\ModelNotFoundException $e) {
            return response()->json(['error' => 'Project not found'], 404);

        } catch (\Exception $e) {
            Log::error('Error in rewrite selection', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);
            return response()->json(['error' => 'Failed to rewrite text: ' . $e->getMessage()], 500);
        }
    }

    /**
     * Function to enhance text using AI with context-aware prompts.
     * Used by the Magic Wand feature to enhance unsent text.
     */
    public function enhanceText(Request $request, string $workspace_id, string $project_id)
    {
        try {
            $validated = $request->validate([
                'text' => 'required|string|min:1|max:10000',
                'enhancement_mode' => 'required|string|in:story_text,chat_message,property,custom_instruction,entity_name,chapter_name,description,summary',
                'model' => 'nullable|string',
                'chapter_content' => 'nullable|string|max:50000', // Optional chapter content for chapter_name mode
            ]);

            $project = Projects::where('id', $project_id)
                ->where('workspace_id', $workspace_id)
                ->firstOrFail();

            $user = Auth::user();
            if (!$user) {
                return response()->json(['error' => 'User not authenticated'], 401);
            }

            // Determine the model to use - check settings properly
            $model = $validated['model']
                ?? ($project->settings && isset($project->settings['aiModel']) ? $project->settings['aiModel'] : null)
                ?? 'gemini-2.0-flash'; // Default to 2.0 flash (most stable)

            // Map model names to provider
            $provider = 'gemini';
            if (str_starts_with($model, 'gpt-')) {
                $provider = 'openai';
            } elseif (str_starts_with($model, 'deepseek')) {
                $provider = 'deepseek';
            }

            Log::info('Text enhancement request', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'enhancement_mode' => $validated['enhancement_mode'],
                'text_length' => strlen($validated['text']),
                'model' => $model,
                'user_id' => $user->id,
            ]);

            // Call Python API for enhancement
            $pythonApiUrl = env('PYTHON_SERVICE_URL', 'http://python-app:5000');

            try {
                $response = Http::timeout(60)->post("{$pythonApiUrl}/api/enhance-text", [
                    'text' => $validated['text'],
                    'enhancement_mode' => $validated['enhancement_mode'],
                    'model' => $model,
                    'provider' => $provider,
                    'project_id' => $project_id,
                    'workspace_id' => $workspace_id,
                    'chapter_content' => $validated['chapter_content'] ?? null,
                ]);

                if (!$response->successful()) {
                    $errorBody = $response->body();
                    $errorData = $response->json();
                    $error = $errorData['error'] ?? $errorData['message'] ?? $errorBody ?? 'Failed to enhance text';

                    Log::error('Enhancement API error', [
                        'status' => $response->status(),
                        'error' => $error,
                        'response_body' => $errorBody,
                    ]);

                    return response()->json([
                        'error' => $error,
                        'status' => $response->status()
                    ], $response->status());
                }

                $result = $response->json();

                if (!isset($result['enhanced_text']) || empty($result['enhanced_text'])) {
                    Log::error('Enhancement API returned empty result', [
                        'result' => $result
                    ]);
                    return response()->json(['error' => 'Enhancement API returned empty result'], 500);
                }

                return response()->json([
                    'success' => true,
                    'enhanced_text' => $result['enhanced_text'],
                ]);

            } catch (\Illuminate\Http\Client\ConnectionException $e) {
                Log::error('Enhancement API connection error', [
                    'error' => $e->getMessage(),
                    'url' => "{$pythonApiUrl}/api/enhance-text",
                ]);
                return response()->json([
                    'error' => 'Could not connect to enhancement service. Please check if the Python service is running.',
                    'details' => $e->getMessage()
                ], 503);
            } catch (\Illuminate\Http\Client\RequestException $e) {
                Log::error('Enhancement API request error', [
                    'error' => $e->getMessage(),
                    'response' => $e->response?->body(),
                ]);
                return response()->json([
                    'error' => 'Enhancement service error: ' . $e->getMessage(),
                ], 500);
            }

        } catch (\Illuminate\Validation\ValidationException $e) {
            Log::warning('Validation error in enhance text', [
                'errors' => $e->errors()
            ]);
            return response()->json(['error' => 'Invalid request', 'details' => $e->errors()], 422);

        } catch (\Illuminate\Database\Eloquent\ModelNotFoundException $e) {
            return response()->json(['error' => 'Project not found'], 404);

        } catch (\Illuminate\Validation\ValidationException $e) {
            // Already handled above, but catch here to prevent duplicate handling
            throw $e;
        } catch (\Illuminate\Database\Eloquent\ModelNotFoundException $e) {
            // Already handled above
            throw $e;
        } catch (\Exception $e) {
            Log::error('Error in enhance text', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
                'trace' => $e->getTraceAsString(),
            ]);
            return response()->json(['error' => 'Failed to enhance text: ' . $e->getMessage()], 500);
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

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
use Illuminate\Support\Facades\Http;

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
     * Function to handle project Saves.
     */
    public function updateProjectData(Request $request, string $workspace_id, string $project_id)
    {
        $validated = $request->validate([
            'order' => 'required|integer',
            'content' => 'nullable|string', // Changed from 'required' to 'nullable' to allow empty content
        ]);

        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->firstOrFail();

        $projectContent = ProjectContent::where('project_id', $project_id)->firstOrFail();
        $chapters = $projectContent->content ?? [];

        foreach ($chapters as &$chapter) {
            if (isset($chapter['order']) && $chapter['order'] === $validated['order']) {
                // Allow empty content - use null coalescing to handle null values
                $chapter['content'] = $validated['content'] ?? '';
                break;
            }
        }

        $projectContent->content = $chapters;
        $projectContent->save();

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
     * Function to handle LLM text generation.
     */
    public function generateText(Request $request, string $workspace_id, string $project_id)
    {
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
        $settings = $validated['settings'] ?? [];
        
        // Get the current chapter content to provide context
        $projectContent = ProjectContent::where('project_id', $project_id)->first();
        $currentChapterContent = '';
        
        if ($projectContent) {
            $chapters = $projectContent->content ?? [];
            foreach ($chapters as $chapter) {
                if (isset($chapter['order']) && $chapter['order'] === $validated['order']) {
                    $currentChapterContent = $chapter['content'] ?? '';
                    break;
                }
            }
        }

        // Prepare the request data for the Python service
        $requestData = [
            'usecase' => 'story',
            'provider' => (
                isset($settings['aiModel']) && stripos($settings['aiModel'], 'gpt') !== false ? 'openai' :
                (isset($settings['aiModel']) && stripos($settings['aiModel'], 'gemini') !== false ? 'gemini' :
                (isset($settings['aiModel']) && stripos($settings['aiModel'], 'deepseek') !== false ? 'deepseek' :
                'openai'))
            ),
            'model' => $settings['aiModel'] ?? 'gpt-4o-mini',
            'prompt' => $validated['prompt'],
            'instruction' => 'Continue the story in a coherent and engaging way, maintaining the same style, tone, and narrative voice.',
            'generation_config' => [
                'temperature' => $settings['temperature'] ?? 1,
                'max_output_tokens' => $settings['outputLength'] ?? 300,
                'top_p' => $settings['topP'] ?? 0.85,
                'top_k' => $settings['topK'] ?? 0.85,
                'repetition_penalty' => $settings['repetitionPenalty'] ?? 0.0,
                'tail_free_sampling' => $settings['tailFree'] ?? 0.85,
                'top_a' => $settings['topA'] ?? 0.85,
                'min_output_tokens' => $settings['minOutputToken'] ?? 50,
                'phrase_bias' => $settings['phraseBias'] ?? [],
                'banned_phrases' => $settings['bannedPhrases'] ?? [],
                'stop_sequences' => $settings['stopSequences'] ?? [],
            ],
            'prompt_config' => [
                'context' => $currentChapterContent,
                'genre' => $settings['storyGenre'] ?? '',
                'tone' => $settings['storyTone'] ?? '',
                'pov' => $settings['storyPov'] ?? '',
            ],
            'caller' => [
                'user_id' => (string)$user->id,
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'api_keys' => [
                    'openai' => '',
                    'gemini' => '',
                    'deepseek' => '',
                ],
            ],
        ];

        try {
            // Make request to Python service using Laravel's HTTP client
            \Log::info('Making request to Python service', [
                'url' => 'http://python-app:5000/api/generate',
                'data' => $requestData
            ]);

            $response = Http::timeout(30)
                ->withHeaders([
                    'Content-Type' => 'application/json',
                ])
                ->post('http://python-app:5000/api/generate', $requestData);

            \Log::info('Python service response', [
                'status' => $response->status(),
                'body' => $response->body()
            ]);

            if ($response->successful()) {
                $responseData = $response->json();

                if ($responseData['success'] && isset($responseData['text'])) {
                    // Update the project content with the generated text
                    $projectContent = ProjectContent::where('project_id', $project_id)->first();
                    if ($projectContent) {
                        $chapters = $projectContent->content ?? [];
                        
                        foreach ($chapters as &$chapter) {
                            if (isset($chapter['order']) && $chapter['order'] === $validated['order']) {
                                // Append the generated text to existing content, add space if needed
                                $existingContent = $chapter['content'] ?? '';
                                $generatedText = $responseData['text'];
                                if ($existingContent !== '' && substr($existingContent, -1) !== ' ' && substr($generatedText, 0, 1) !== ' ') {
                                    $existingContent .= ' ';
                                }
                                $chapter['content'] = $existingContent . $generatedText;
                                break;
                            }
                        }
                        
                        $projectContent->content = $chapters;
                        $projectContent->save();

                        \Log::info('Successfully updated project content with generated text');
                    }

                    return redirect()->route('workspace.projects.editor', [
                        'workspace_id' => $workspace_id,
                        'project_id' => $project_id,
                    ]);
                } else {
                    \Log::error('Generation failed', ['response' => $responseData]);
                    return back()->withErrors([
                        'generation' => $responseData['error_message'] ?? 'Generation failed'
                    ]);
                }
            } else {
                \Log::error('HTTP request failed', [
                    'status' => $response->status(),
                    'body' => $response->body()
                ]);
                return back()->withErrors([
                    'generation' => 'Failed to connect to generation service'
                ]);
            }
        } catch (\Exception $e) {
            \Log::error('LLM Generation Error: ' . $e->getMessage(), [
                'exception' => $e,
                'trace' => $e->getTraceAsString()
            ]);
            return back()->withErrors([
                'generation' => 'Failed to generate text: ' . $e->getMessage()
            ]);
        }
    }
}

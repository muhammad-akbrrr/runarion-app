<?php

namespace App\Http\Controllers\ProjectEditor;

use App\Http\Controllers\Controller;
use App\Models\ProjectContent;
use App\Models\Projects;
use App\Services\VersionControlService;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;
use Inertia\Inertia;

class MultiPromptController extends Controller
{
    protected VersionControlService $versionControl;

    public function __construct(VersionControlService $versionControl)
    {
        $this->versionControl = $versionControl;
    }

    /**
     * Show the multi-prompt editor page inside of the project editor..
     */
    public function multiPrompt(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id]);
        }

        // Get chapters (same as MainEditorController)
        $projectContent = ProjectContent::where('project_id', $project_id)->first();
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
                } catch (\Exception $e) {
                    Log::warning('Error getting version control info for chapter in multi-prompt', [
                        'project_id' => $project_id,
                        'chapter_order' => $chapter['order'] ?? null,
                        'error' => $e->getMessage(),
                    ]);
                }
            }
        }

        return Inertia::render('Projects/Editor/Multiprompt/Main', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => $project,
            'chapters' => $chapters,
        ]);
    }
}

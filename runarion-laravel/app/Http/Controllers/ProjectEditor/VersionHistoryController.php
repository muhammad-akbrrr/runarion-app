<?php

namespace App\Http\Controllers\ProjectEditor;

use Illuminate\Http\Request;
use App\Http\Controllers\Controller;
use App\Models\Projects;
use App\Models\ProjectSnapshot;
use App\Services\VersionControlService;
use Inertia\Inertia;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Log;

class VersionHistoryController extends Controller
{
    protected VersionControlService $versionControl;

    public function __construct(VersionControlService $versionControl)
    {
        $this->versionControl = $versionControl;
    }

    /**
     * Show the version history page
     */
    public function index(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (!$project) {
            return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id]);
        }

        // Get all snapshots
        $snapshots = ProjectSnapshot::where('project_id', $project_id)
            ->orderBy('created_at', 'desc')
            ->with('creator:id,name')
            ->get()
            ->map(function ($snapshot) {
                return [
                    'id' => $snapshot->id,
                    'name' => $snapshot->name,
                    'description' => $snapshot->description,
                    'created_at' => $snapshot->created_at->toISOString(),
                    'created_by' => $snapshot->creator ? [
                        'id' => $snapshot->creator->id,
                        'name' => $snapshot->creator->name,
                    ] : null,
                ];
            });

        // Get all chapters with version info
        $chapters = $this->versionControl->getAllChaptersVersionInfo($project_id);

        return Inertia::render('Projects/Editor/VersionHistory/Main', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => $project,
            'snapshots' => $snapshots,
            'chapters' => $chapters,
        ]);
    }

    /**
     * Create a new snapshot
     */
    public function createSnapshot(Request $request, string $workspace_id, string $project_id)
    {
        $validated = $request->validate([
            'name' => 'nullable|string|max:255',
            'description' => 'nullable|string|max:1000',
        ]);

        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (!$project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $snapshotId = $this->versionControl->createSnapshot(
                $project_id,
                $validated['name'] ?? null,
                $validated['description'] ?? null,
                Auth::id()
            );

            $snapshot = ProjectSnapshot::with('creator:id,name')->find($snapshotId);

            if (!$snapshot) {
                Log::error('Snapshot not found after creation', ['snapshot_id' => $snapshotId]);
                return response()->json(['error' => 'Snapshot created but not found'], 500);
            }

            return response()->json([
                'success' => true,
                'snapshot' => [
                    'id' => $snapshot->id,
                    'name' => $snapshot->name,
                    'description' => $snapshot->description,
                    'created_at' => $snapshot->created_at->toISOString(),
                    'created_by' => $snapshot->creator ? [
                        'id' => $snapshot->creator->id,
                        'name' => $snapshot->creator->name,
                    ] : null,
                ],
            ]);
        } catch (\Exception $e) {
            Log::error('Failed to create snapshot', [
                'project_id' => $project_id,
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            return response()->json([
                'error' => 'Failed to create snapshot',
                'message' => $e->getMessage(),
            ], 500);
        }
    }

    /**
     * Load a snapshot
     */
    public function loadSnapshot(Request $request, string $workspace_id, string $project_id, string $snapshot_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (!$project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $success = $this->versionControl->loadSnapshot($project_id, $snapshot_id);

            if (!$success) {
                return response()->json(['error' => 'Snapshot not found'], 404);
            }

            // Refresh chapters data
            $chapters = $this->versionControl->getAllChaptersVersionInfo($project_id);

            return response()->json([
                'success' => true,
                'chapters' => $chapters,
            ]);
        } catch (\Exception $e) {
            Log::error('Failed to load snapshot', [
                'project_id' => $project_id,
                'snapshot_id' => $snapshot_id,
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            return response()->json([
                'error' => 'Failed to load snapshot',
                'message' => $e->getMessage(),
            ], 500);
        }
    }

    /**
     * Delete a snapshot
     */
    public function deleteSnapshot(Request $request, string $workspace_id, string $project_id, string $snapshot_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (!$project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $snapshot = ProjectSnapshot::where('id', $snapshot_id)
                ->where('project_id', $project_id)
                ->first();

            if (!$snapshot) {
                return response()->json(['error' => 'Snapshot not found'], 404);
            }

            $snapshot->delete();

            return response()->json(['success' => true]);
        } catch (\Exception $e) {
            Log::error('Failed to delete snapshot', [
                'project_id' => $project_id,
                'snapshot_id' => $snapshot_id,
                'error' => $e->getMessage(),
            ]);

            return response()->json(['error' => 'Failed to delete snapshot'], 500);
        }
    }

    /**
     * Update snapshot name/description
     */
    public function updateSnapshot(Request $request, string $workspace_id, string $project_id, string $snapshot_id)
    {
        $validated = $request->validate([
            'name' => 'nullable|string|max:255',
            'description' => 'nullable|string|max:1000',
        ]);

        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (!$project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $snapshot = ProjectSnapshot::where('id', $snapshot_id)
                ->where('project_id', $project_id)
                ->first();

            if (!$snapshot) {
                return response()->json(['error' => 'Snapshot not found'], 404);
            }

            $snapshot->update($validated);

            return response()->json([
                'success' => true,
                'snapshot' => [
                    'id' => $snapshot->id,
                    'name' => $snapshot->name,
                    'description' => $snapshot->description,
                ],
            ]);
        } catch (\Exception $e) {
            Log::error('Failed to update snapshot', [
                'project_id' => $project_id,
                'snapshot_id' => $snapshot_id,
                'error' => $e->getMessage(),
            ]);

            return response()->json(['error' => 'Failed to update snapshot'], 500);
        }
    }

    /**
     * Get version tree for a specific chapter
     */
    public function getChapterVersionTree(Request $request, string $workspace_id, string $project_id, int $chapter_order)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (!$project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $versionTree = $this->versionControl->getChapterVersionTree($project_id, $chapter_order);

            return response()->json([
                'success' => true,
                'version_tree' => $versionTree,
            ]);
        } catch (\Exception $e) {
            Log::error('Failed to get chapter version tree', [
                'project_id' => $project_id,
                'chapter_order' => $chapter_order,
                'error' => $e->getMessage(),
            ]);

            return response()->json(['error' => 'Failed to get version tree'], 500);
        }
    }
}


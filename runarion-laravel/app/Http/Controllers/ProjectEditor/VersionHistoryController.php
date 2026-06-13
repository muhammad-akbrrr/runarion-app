<?php

namespace App\Http\Controllers\ProjectEditor;

use App\Http\Controllers\Controller;
use App\Models\Projects;
use App\Models\ProjectSnapshot;
use App\Services\ProjectSnapshotService;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Log;
use Symfony\Component\HttpFoundation\Response;

class VersionHistoryController extends Controller
{
    protected ProjectSnapshotService $projectSnapshots;

    public function __construct(ProjectSnapshotService $projectSnapshots)
    {
        $this->projectSnapshots = $projectSnapshots;
    }

    /**
     * Show the version history page
     */
    public function index(Request $request, string $workspace_id, string $project_id)
    {
        return redirect()->route('workspace.projects.edit.backups', [
            'workspace_id' => $workspace_id,
            'project_id' => $project_id,
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

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $snapshotId = $this->projectSnapshots->createSnapshot(
                $project_id,
                $validated['name'] ?? null,
                $validated['description'] ?? null,
                Auth::id()
            );

            $snapshot = ProjectSnapshot::with('creator:id,name')->find($snapshotId);

            if (! $snapshot) {
                Log::error('Snapshot not found after creation', ['snapshot_id' => $snapshotId]);

                return response()->json(['error' => 'Snapshot created but not found'], 500);
            }

            return response()->json([
                'success' => true,
                'snapshot' => $this->formatSnapshot($snapshot),
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
    public function restoreSnapshot(Request $request, string $workspace_id, string $project_id, string $snapshot_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $operation = $this->projectSnapshots->queueRestoreSnapshot($workspace_id, $project_id, $snapshot_id, Auth::id());

            return response()->json([
                'success' => true,
                'operation' => [
                    'id' => $operation->id,
                    'type' => $operation->operation_type,
                    'phase' => $operation->phase,
                    'is_locked' => true,
                ],
                'redirect_to' => route('workspace.projects', [
                    'workspace_id' => $workspace_id,
                ]),
            ], Response::HTTP_ACCEPTED);
        } catch (\Exception $e) {
            Log::error('Failed to queue snapshot restore', [
                'project_id' => $project_id,
                'snapshot_id' => $snapshot_id,
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            return response()->json([
                'error' => 'Failed to queue snapshot restore',
                'message' => $e->getMessage(),
            ], 500);
        }
    }

    /**
     * Delete a snapshot
     */
    public function deleteSnapshot(Request $request, string $workspace_id, string $project_id, string $snapshot_id)
    {
        return response()->json([
            'error' => 'Snapshots are immutable and cannot be deleted.',
        ], 405);
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

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $snapshot = ProjectSnapshot::where('id', $snapshot_id)
                ->where('project_id', $project_id)
                ->first();

            if (! $snapshot) {
                return response()->json(['error' => 'Snapshot not found'], 404);
            }

            $snapshot->update($validated);

            return response()->json([
                'success' => true,
                'snapshot' => $this->formatSnapshot($snapshot->fresh(['creator:id,name'])),
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

    private function formatSnapshot(ProjectSnapshot $snapshot): array
    {
        $snapshotData = $snapshot->snapshot_data ?? [];

        return [
            'id' => $snapshot->id,
            'name' => $snapshot->name,
            'description' => $snapshot->description,
            'snapshot_kind' => $snapshot->snapshot_kind,
            'is_immutable' => (bool) $snapshot->is_immutable,
            'created_at' => $snapshot->created_at->toISOString(),
            'created_by' => $snapshot->creator ? [
                'id' => $snapshot->creator->id,
                'name' => $snapshot->creator->name,
            ] : null,
            'summary' => [
                'chapter_count' => count($snapshotData['project_content']['content'] ?? $snapshotData['chapters'] ?? []),
                'chat_count' => count($snapshotData['advisor']['chats'] ?? []),
                'message_count' => count($snapshotData['advisor']['messages'] ?? []),
                'entity_count' => count($snapshotData['records']['entities'] ?? $snapshotData['entities'] ?? []),
                'relationship_count' => count($snapshotData['records']['relationships'] ?? $snapshotData['relationships'] ?? []),
                'has_multiprompt_state' => ! empty($snapshotData['multiprompt']['graph_state'] ?? null),
            ],
        ];
    }
}

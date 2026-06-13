<?php

namespace App\Services;

use App\Events\ProjectOperationLifecycleUpdated;
use App\Models\PipelineRun;
use App\Models\ProjectOperation;
use Illuminate\Database\Eloquent\Collection;

class ProjectOperationStateService
{
    public function __construct(
        private readonly ProjectPipelineStateService $pipelineStateService,
    ) {}

    public function getProjectLock(string $workspaceId, string $projectId): ?array
    {
        return $this->getLocksForProjects($workspaceId, [$projectId])[$projectId] ?? null;
    }

    public function getLocksForProjects(string $workspaceId, array $projectIds): array
    {
        $projectIds = array_values(array_unique(array_filter($projectIds)));
        if ($projectIds === []) {
            return [];
        }

        $locks = $this->pipelineStateService->getLocksForProjects($workspaceId, $projectIds);

        /** @var Collection<int, ProjectOperation> $operations */
        $operations = ProjectOperation::query()
            ->where('workspace_id', $workspaceId)
            ->whereIn('project_id', $projectIds)
            ->whereNull('deleted_at')
            ->orderByDesc('created_at')
            ->get();

        foreach ($operations as $operation) {
            if (! $operation instanceof ProjectOperation || ! $operation->project_id) {
                continue;
            }

            if (! $operation->isLocked()) {
                continue;
            }

            $existing = $locks[$operation->project_id] ?? null;
            if ($existing === null || $this->operationStartedAt($existing) <= ($operation->started_at?->getTimestamp() ?? $operation->created_at?->getTimestamp() ?? 0)) {
                $locks[$operation->project_id] = $this->formatOperationLock($operation);
            }
        }

        return $locks;
    }

    public function createRestoreOperation(string $workspaceId, string $projectId, string $snapshotId, ?int $createdBy = null): ProjectOperation
    {
        $operation = ProjectOperation::query()->create([
            'workspace_id' => $workspaceId,
            'project_id' => $projectId,
            'operation_type' => ProjectOperation::TYPE_SNAPSHOT_RESTORE,
            'status' => ProjectOperation::STATUS_PENDING,
            'phase' => 'queued',
            'message' => 'Project snapshot restore queued. Editing is temporarily locked.',
            'metadata' => [
                'snapshot_id' => $snapshotId,
            ],
            'created_by' => $createdBy,
            'started_at' => now(),
        ]);

        $this->broadcastLifecycle($operation, true);

        return $operation;
    }

    public function markRunning(ProjectOperation $operation, string $phase = 'restoring', ?string $message = null): ProjectOperation
    {
        $operation->status = ProjectOperation::STATUS_RUNNING;
        $operation->phase = $phase;
        $operation->message = $message ?? 'Project snapshot restore is in progress.';
        $operation->started_at ??= now();
        $operation->save();

        $this->broadcastLifecycle($operation, false);

        return $operation;
    }

    public function markCompleted(ProjectOperation $operation, string $phase = 'completed', ?string $message = null): ProjectOperation
    {
        $operation->status = ProjectOperation::STATUS_COMPLETED;
        $operation->phase = $phase;
        $operation->message = $message ?? 'Project snapshot restore completed.';
        $operation->completed_at = now();
        $operation->save();

        $this->broadcastLifecycle($operation, true);

        return $operation;
    }

    public function markFailed(ProjectOperation $operation, ?string $message = null): ProjectOperation
    {
        $operation->status = ProjectOperation::STATUS_FAILED;
        $operation->phase = 'failed';
        $operation->message = $message ?? 'Project snapshot restore failed.';
        $operation->completed_at = now();
        $operation->save();

        $this->broadcastLifecycle($operation, true);

        return $operation;
    }

    public function formatOperationLock(ProjectOperation $operation): array
    {
        return [
            'isLocked' => true,
            'operationId' => $operation->id,
            'operationType' => $operation->operation_type,
            'status' => $operation->status,
            'phase' => $operation->phase ?? 'pending',
            'message' => $operation->message,
            'startedAt' => optional($operation->started_at)->toISOString(),
            'completedAt' => optional($operation->completed_at)->toISOString(),
        ];
    }

    private function broadcastLifecycle(ProjectOperation $operation, bool $shouldToast): void
    {
        broadcast(new ProjectOperationLifecycleUpdated(
            $operation->workspace_id,
            $operation->project_id,
            $operation->id,
            $operation->operation_type,
            $operation->status,
            $operation->phase ?? 'pending',
            $operation->isLocked(),
            $operation->message,
            $shouldToast,
        ));
    }

    private function operationStartedAt(array $lock): int
    {
        if (! empty($lock['startedAt'])) {
            return strtotime((string) $lock['startedAt']) ?: 0;
        }

        return 0;
    }
}

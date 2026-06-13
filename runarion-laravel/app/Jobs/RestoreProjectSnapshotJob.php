<?php

namespace App\Jobs;

use App\Models\ProjectOperation;
use App\Services\ProjectOperationStateService;
use App\Services\ProjectSnapshotService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Log;
use Throwable;

class RestoreProjectSnapshotJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(
        private readonly string $workspaceId,
        private readonly string $projectId,
        private readonly string $snapshotId,
        private readonly string $operationId,
    ) {}

    public function handle(
        ProjectSnapshotService $projectSnapshotService,
        ProjectOperationStateService $operationStateService,
    ): void {
        /** @var ProjectOperation|null $operation */
        $operation = ProjectOperation::query()->find($this->operationId);
        if (! $operation) {
            return;
        }

        $operationStateService->markRunning($operation);

        try {
            $projectSnapshotService->restoreSnapshotNow($this->projectId, $this->snapshotId);
            $operationStateService->markCompleted($operation, 'completed', 'Project snapshot restore completed. You can open the project again.');
        } catch (Throwable $e) {
            Log::error('Project snapshot restore failed', [
                'workspace_id' => $this->workspaceId,
                'project_id' => $this->projectId,
                'snapshot_id' => $this->snapshotId,
                'operation_id' => $this->operationId,
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            $operationStateService->markFailed($operation, 'Project snapshot restore failed. Please try again.');

            throw $e;
        }
    }
}

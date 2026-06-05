<?php

namespace App\Services;

use App\Models\PipelineRun;
use Illuminate\Database\Eloquent\Collection;

class ProjectPipelineStateService
{
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

        /** @var Collection<int, PipelineRun> $runs */
        $runs = PipelineRun::query()
            ->where('workspace_id', $workspaceId)
            ->whereIn('project_id', $projectIds)
            ->whereNull('deleted_at')
            ->orderByDesc('created_at')
            ->get();

        $locks = [];
        foreach ($runs as $run) {
            if (! $run instanceof PipelineRun) {
                continue;
            }

            if (! $run->project_id || array_key_exists($run->project_id, $locks)) {
                continue;
            }

            if ($this->isRunLocked($run)) {
                $locks[$run->project_id] = $this->formatLock($run);
            }
        }

        return $locks;
    }

    public function findActiveRun(string $workspaceId, string $projectId): ?PipelineRun
    {
        return PipelineRun::query()
            ->where('workspace_id', $workspaceId)
            ->where('project_id', $projectId)
            ->whereNull('deleted_at')
            ->orderByDesc('created_at')
            ->get()
            ->first(fn (PipelineRun $run) => $this->isRunLocked($run));
    }

    public function isRunLocked(PipelineRun $run): bool
    {
        if (
            in_array($run->status, [
                PipelineRun::STATUS_PENDING,
                PipelineRun::STATUS_PHASE_1_2_RUNNING,
                PipelineRun::STATUS_PHASE_3_RUNNING,
            ], true)
        ) {
            return true;
        }

        return $run->status === PipelineRun::STATUS_COMPLETED
            && in_array($run->import_status, [
                PipelineRun::IMPORT_STATUS_PENDING,
                PipelineRun::IMPORT_STATUS_RUNNING,
            ], true);
    }

    public function formatLock(PipelineRun $run): array
    {
        return [
            'isLocked' => true,
            'runId' => $run->id,
            'draftId' => $run->draft_id,
            'authorStyleId' => $run->author_style_id,
            'status' => $run->status,
            'phase' => $this->resolvePhaseName($run),
            'errorMessage' => $run->import_error_message ?: $run->error_message,
            'startedAt' => optional($run->started_at)->toISOString(),
            'completedAt' => optional($run->completed_at)->toISOString(),
        ];
    }

    private function resolvePhaseName(PipelineRun $run): string
    {
        if ($run->status === PipelineRun::STATUS_COMPLETED && $run->import_status !== PipelineRun::IMPORT_STATUS_COMPLETED) {
            return 'import';
        }

        return match ((int) $run->current_phase) {
            1 => 'deconstructor',
            2 => 'style_analyzer',
            3 => 'novel_writer',
            default => match ($run->status) {
                PipelineRun::STATUS_PHASE_1_2_RUNNING => 'deconstructor',
                PipelineRun::STATUS_PHASE_3_RUNNING => 'novel_writer',
                default => 'pending',
            },
        };
    }
}

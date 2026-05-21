<?php

namespace App\Jobs;

use App\Events\ProjectPipelineLifecycleUpdated;
use App\Models\PipelineRun;
use App\Services\NovelPipelineImportService;
use App\Services\PythonServiceClient;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use RuntimeException;

class MonitorNovelPipelineRunJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public $timeout = 120;

    public $tries = 30;

    public function __construct(
        private readonly string $pipelineRunId,
    ) {
    }

    public function handle(
        PythonServiceClient $pythonClient,
        NovelPipelineImportService $importService,
    ): void {
        $run = PipelineRun::query()->find($this->pipelineRunId);
        if (!$run || !$run->project_id) {
            return;
        }

        if ($run->status === PipelineRun::STATUS_FAILED || $run->import_status === PipelineRun::IMPORT_STATUS_COMPLETED) {
            return;
        }

        $lock = Cache::lock("pipeline-monitor:{$run->id}", 30);
        if (!$lock->get()) {
            self::dispatch($this->pipelineRunId)->delay(now()->addSeconds(10));
            return;
        }

        try {
            $status = $pythonClient->getNovelPipelineStatus($run->id, $run->user_id);

            DB::transaction(function () use ($run, $status) {
                $freshRun = PipelineRun::query()->lockForUpdate()->findOrFail($run->id);
                $freshRun->status = $status['status'] ?? $freshRun->status;
                $freshRun->current_phase = $status['current_phase'] ?? $freshRun->current_phase;
                $freshRun->phase_1_status = $status['phases']['phase_1']['status'] ?? $freshRun->phase_1_status;
                $freshRun->phase_2_status = $status['phases']['phase_2']['status'] ?? $freshRun->phase_2_status;
                $freshRun->phase_3_status = $status['phases']['phase_3']['status'] ?? $freshRun->phase_3_status;
                $freshRun->author_style_id = $status['author_style_id'] ?? $freshRun->author_style_id;
                $freshRun->error_message = $status['error_message'] ?? null;
                $freshRun->failed_phase = $status['failed_phase'] ?? null;
                $freshRun->metadata = $status['metadata'] ?? $freshRun->metadata;
                $freshRun->completed_at = !empty($status['completed_at']) ? $status['completed_at'] : $freshRun->completed_at;
                $freshRun->save();
            });

            $run->refresh();

            if ($run->status === PipelineRun::STATUS_FAILED) {
                $run->import_status = PipelineRun::IMPORT_STATUS_SKIPPED;
                $run->import_error_message = $run->error_message;
                $run->save();

                broadcast(new ProjectPipelineLifecycleUpdated(
                    $run->workspace_id,
                    $run->project_id,
                    $run->id,
                    $run->status,
                    $this->phaseName($run),
                    false,
                    $run->error_message ?: 'Novel pipeline failed.',
                    true,
                ));
                return;
            }

            if ($run->status === PipelineRun::STATUS_COMPLETED) {
                $this->importCompletedRun($run, $status, $pythonClient, $importService);
                return;
            }

            broadcast(new ProjectPipelineLifecycleUpdated(
                $run->workspace_id,
                $run->project_id,
                $run->id,
                $run->status,
                $this->phaseName($run),
                true,
                'Novel pipeline processing is still running.',
                false,
            ));

            self::dispatch($run->id)->delay(now()->addSeconds(15));
        } finally {
            optional($lock)->release();
        }
    }

    private function importCompletedRun(
        PipelineRun $run,
        array $status,
        PythonServiceClient $pythonClient,
        NovelPipelineImportService $importService,
    ): void {
        try {
            $pythonClient->getNovelPipelineResults($run->id, $run->user_id);
            $importService->importCompletedRun($run);
            $run->refresh();

            broadcast(new ProjectPipelineLifecycleUpdated(
                $run->workspace_id,
                $run->project_id,
                $run->id,
                $run->status,
                'import',
                false,
                'Novel pipeline completed and the rewritten manuscript has been imported.',
                true,
            ));
        } catch (\Throwable $exception) {
            Log::error('Novel pipeline import failed', [
                'pipeline_run_id' => $run->id,
                'project_id' => $run->project_id,
                'error' => $exception->getMessage(),
            ]);

            $freshRun = PipelineRun::query()->find($run->id);
            if (!$freshRun) {
                throw $exception;
            }

            $freshRun->import_status = PipelineRun::IMPORT_STATUS_FAILED;
            $freshRun->import_error_message = $exception->getMessage();
            $freshRun->save();

            broadcast(new ProjectPipelineLifecycleUpdated(
                $freshRun->workspace_id,
                $freshRun->project_id,
                $freshRun->id,
                $freshRun->status,
                'import',
                false,
                $exception->getMessage(),
                true,
            ));
        }
    }

    private function phaseName(PipelineRun $run): string
    {
        return match ((int) $run->current_phase) {
            1 => 'deconstructor',
            2 => 'style_analyzer',
            3 => 'novel_writer',
            default => $run->status === PipelineRun::STATUS_COMPLETED ? 'import' : 'pending',
        };
    }
}

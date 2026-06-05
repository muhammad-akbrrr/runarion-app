<?php

namespace App\Services;

use App\Events\ProjectPipelineLifecycleUpdated;
use App\Jobs\MonitorNovelPipelineRunJob;
use App\Models\AuthorStyle;
use App\Models\PipelineRun;
use App\Models\Projects;
use App\Models\User;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;
use RuntimeException;

class NovelPipelineOrchestratorService
{
    public function __construct(
        private readonly PythonServiceClient $pythonClient,
        private readonly ProjectPipelineStateService $pipelineStateService,
    ) {}

    public function startProjectPipeline(
        Projects $project,
        User $user,
        UploadedFile $manuscriptFile,
        array $options,
    ): PipelineRun {
        if ($project->completed_onboarding) {
            throw ValidationException::withMessages([
                'draft_file' => 'This project has already completed onboarding.',
            ]);
        }

        if ($this->pipelineStateService->findActiveRun($project->workspace_id, $project->id)) {
            throw ValidationException::withMessages([
                'draft_file' => 'This project is already being processed by the novel pipeline.',
            ]);
        }

        [$authorName, $authorStyleMode, $authorFiles] = $this->resolveAuthorStyleInputs(
            $project,
            $options
        );

        $payload = [
            'caller' => [
                'user_id' => (string) $user->id,
                'workspace_id' => $project->workspace_id,
                'project_id' => $project->id,
            ],
            'author_name' => $authorName,
            'author_style_mode' => $authorStyleMode,
            'writing_perspective' => $options['writing_perspective'],
        ];

        $payload = $this->applyTestingProviderOverride($payload);

        $response = $this->pythonClient->startNovelPipeline(
            $payload,
            $manuscriptFile,
            $authorFiles,
        );

        $runId = $response['pipeline_run_id'] ?? null;
        $draftId = $response['draft_id'] ?? null;

        if (! $runId || ! $draftId) {
            throw new RuntimeException('Python pipeline start response did not include a run ID and draft ID.');
        }

        $pipelineRun = DB::transaction(function () use ($runId, $draftId, $project, $user, $authorName) {
            return PipelineRun::query()->updateOrCreate(
                ['id' => $runId],
                [
                    'draft_id' => $draftId,
                    'workspace_id' => $project->workspace_id,
                    'project_id' => $project->id,
                    'user_id' => $user->id,
                    'author_name' => $authorName,
                    'status' => PipelineRun::STATUS_PENDING,
                    'phase_1_status' => 'pending',
                    'phase_2_status' => 'pending',
                    'phase_3_status' => 'pending',
                    'import_status' => PipelineRun::IMPORT_STATUS_PENDING,
                    'import_error_message' => null,
                    'started_at' => now(),
                ]
            );
        });

        MonitorNovelPipelineRunJob::dispatch($pipelineRun->id)->delay(now()->addSeconds(15));

        broadcast(new ProjectPipelineLifecycleUpdated(
            $project->workspace_id,
            $project->id,
            $pipelineRun->id,
            PipelineRun::STATUS_PENDING,
            'pending',
            true,
            'Novel pipeline processing started.',
            true,
        ));

        return $pipelineRun;
    }

    private function resolveAuthorStyleInputs(Projects $project, array $options): array
    {
        if (($options['author_style_type'] ?? null) === 'existing') {
            /** @var AuthorStyle|null $style */
            $style = AuthorStyle::query()
                ->where('workspace_id', $project->workspace_id)
                ->find($options['selected_author_style']);

            if (! $style) {
                throw ValidationException::withMessages([
                    'selectedAuthorStyle' => 'The selected author style could not be found.',
                ]);
            }

            if ($style->status !== 'profiling_completed') {
                throw ValidationException::withMessages([
                    'selectedAuthorStyle' => 'Only fully profiled author styles can be reused during onboarding.',
                ]);
            }

            return [$style->author_name, 'use_existing', []];
        }

        $authorName = trim((string) ($options['new_author_name'] ?? ''));
        if ($authorName === '') {
            throw ValidationException::withMessages([
                'newAuthorName' => 'An author name is required for uploaded author samples.',
            ]);
        }

        $authorFiles = array_values(array_filter(
            $options['new_author_files'] ?? [],
            fn ($file) => $file instanceof UploadedFile
        ));

        if ($authorFiles === []) {
            throw ValidationException::withMessages([
                'newAuthorFiles' => 'At least one author sample is required.',
            ]);
        }

        return [$authorName, 'create_or_update', $authorFiles];
    }

    private function applyTestingProviderOverride(array $payload): array
    {
        if (! app()->environment('testing')) {
            return $payload;
        }

        $provider = trim((string) config('services.python.novel_pipeline_test_provider', ''));
        if ($provider === '') {
            return $payload;
        }

        $model = trim((string) config('services.python.novel_pipeline_test_model', 'mock-replay-v1'));

        $payload['provider'] = Str::lower($provider);
        $payload['model'] = $model;
        $payload['style_analyzer_config'] = array_merge(
            $payload['style_analyzer_config'] ?? [],
            [
                'provider' => Str::lower($provider),
                'model' => $model,
                'phase_start_delay_seconds' => 0,
            ],
        );

        return $payload;
    }
}

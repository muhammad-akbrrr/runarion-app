<?php

use App\Events\ProjectPipelineLifecycleUpdated;
use App\Jobs\MonitorNovelPipelineRunJob;
use App\Models\PipelineRun;
use App\Services\NovelPipelineImportService;
use App\Services\PythonServiceClient;
use Illuminate\Support\Facades\Bus;
use Illuminate\Support\Facades\Event;
use Tests\Support\NovelPipelineTestSupport;

test('monitor job updates active runs and requeues without toast spam', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext();
    $run = NovelPipelineTestSupport::createPipelineRun([
        'workspace_id' => $context['workspace']->id,
        'project_id' => $context['project']->id,
        'user_id' => $context['user']->id,
        'status' => PipelineRun::STATUS_PENDING,
    ]);

    Bus::fake();
    Event::fake([ProjectPipelineLifecycleUpdated::class]);

    $pythonClient = Mockery::mock(PythonServiceClient::class);
    $pythonClient->shouldReceive('getNovelPipelineStatus')
        ->once()
        ->with($run->id, $context['user']->id)
        ->andReturn([
            'status' => PipelineRun::STATUS_PHASE_1_2_RUNNING,
            'current_phase' => 1,
            'phases' => [
                'phase_1' => ['status' => 'running'],
                'phase_2' => ['status' => 'pending'],
                'phase_3' => ['status' => 'pending'],
            ],
            'metadata' => ['heartbeat' => true],
        ]);

    $importService = Mockery::mock(NovelPipelineImportService::class);
    $importService->shouldNotReceive('importCompletedRun');

    (new MonitorNovelPipelineRunJob($run->id))->handle($pythonClient, $importService);

    $run->refresh();

    expect($run->status)->toBe(PipelineRun::STATUS_PHASE_1_2_RUNNING);
    expect($run->current_phase)->toBe(1);
    expect($run->phase_1_status)->toBe('running');
    expect($run->phase_2_status)->toBe('pending');

    Bus::assertDispatched(MonitorNovelPipelineRunJob::class);
    Event::assertDispatched(ProjectPipelineLifecycleUpdated::class, fn (ProjectPipelineLifecycleUpdated $event) => $event->runId === $run->id && $event->shouldToast === false);
});

test('monitor job marks failed runs as skipped and broadcasts a terminal event', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext();
    $run = NovelPipelineTestSupport::createPipelineRun([
        'workspace_id' => $context['workspace']->id,
        'project_id' => $context['project']->id,
        'user_id' => $context['user']->id,
        'status' => PipelineRun::STATUS_PHASE_3_RUNNING,
        'phase_1_status' => 'completed',
        'phase_2_status' => 'completed',
        'phase_3_status' => 'running',
    ]);

    Event::fake([ProjectPipelineLifecycleUpdated::class]);

    $pythonClient = Mockery::mock(PythonServiceClient::class);
    $pythonClient->shouldReceive('getNovelPipelineStatus')
        ->once()
        ->andReturn([
            'status' => PipelineRun::STATUS_FAILED,
            'current_phase' => 3,
            'phases' => [
                'phase_1' => ['status' => 'completed'],
                'phase_2' => ['status' => 'completed'],
                'phase_3' => ['status' => 'failed'],
            ],
            'error_message' => 'Pipeline exploded.',
            'failed_phase' => 3,
        ]);

    $importService = Mockery::mock(NovelPipelineImportService::class);
    $importService->shouldNotReceive('importCompletedRun');

    (new MonitorNovelPipelineRunJob($run->id))->handle($pythonClient, $importService);

    $run->refresh();

    expect($run->status)->toBe(PipelineRun::STATUS_FAILED);
    expect($run->import_status)->toBe(PipelineRun::IMPORT_STATUS_SKIPPED);
    expect($run->import_error_message)->toBe('Pipeline exploded.');

    Event::assertDispatched(ProjectPipelineLifecycleUpdated::class, fn (ProjectPipelineLifecycleUpdated $event) => $event->runId === $run->id && $event->shouldToast === true && $event->isLocked === false);
});

test('monitor job delegates completed runs to the import service', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext();
    $run = NovelPipelineTestSupport::createPipelineRun([
        'workspace_id' => $context['workspace']->id,
        'project_id' => $context['project']->id,
        'user_id' => $context['user']->id,
        'status' => PipelineRun::STATUS_PHASE_3_RUNNING,
        'phase_1_status' => 'completed',
        'phase_2_status' => 'completed',
        'phase_3_status' => 'running',
    ]);

    Event::fake([ProjectPipelineLifecycleUpdated::class]);

    $pythonClient = Mockery::mock(PythonServiceClient::class);
    $pythonClient->shouldReceive('getNovelPipelineStatus')
        ->once()
        ->andReturn([
            'status' => PipelineRun::STATUS_COMPLETED,
            'current_phase' => null,
            'phases' => [
                'phase_1' => ['status' => 'completed'],
                'phase_2' => ['status' => 'completed'],
                'phase_3' => ['status' => 'completed'],
            ],
            'completed_at' => now()->toISOString(),
        ]);
    $pythonClient->shouldReceive('getNovelPipelineResults')
        ->once()
        ->with($run->id, $context['user']->id)
        ->andReturn([
            'pipeline_run_id' => $run->id,
        ]);

    $importService = Mockery::mock(NovelPipelineImportService::class);
    $importService->shouldReceive('importCompletedRun')
        ->once()
        ->with(Mockery::on(fn ($incomingRun) => $incomingRun->id === $run->id));

    (new MonitorNovelPipelineRunJob($run->id))->handle($pythonClient, $importService);

    Event::assertDispatched(ProjectPipelineLifecycleUpdated::class, fn (ProjectPipelineLifecycleUpdated $event) => $event->runId === $run->id && $event->phase === 'import');
});

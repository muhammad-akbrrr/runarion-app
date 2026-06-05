<?php

use App\Jobs\MonitorNovelPipelineRunJob;
use App\Models\PipelineRun;
use App\Models\ProjectContent;
use App\Services\PythonServiceClient;
use Illuminate\Foundation\Http\Middleware\ValidateCsrfToken;
use Illuminate\Foundation\Testing\DatabaseMigrations;
use Illuminate\Support\Facades\Bus;
use Tests\Support\NovelPipelineTestSupport;
use Tests\TestCase;

uses(TestCase::class, DatabaseMigrations::class);

beforeEach(function () {
    /** @var TestCase $this */
    $this->withoutMiddleware(ValidateCsrfToken::class);
});

test('live python onboarding flow imports rewritten manuscript content', function () {
    NovelPipelineTestSupport::skipUnlessLivePythonEnabled();

    config()->set('services.python.novel_pipeline_test_provider', 'mock');
    config()->set('services.python.novel_pipeline_test_model', 'mock-replay-v1');

    $context = NovelPipelineTestSupport::createWorkspaceContext([
        'initial_content' => 'Original manuscript content.',
    ]);

    Bus::fake();

    $response = $this
        ->actingAs($context['user'])
        ->post(route('editor.project.onboarding', [
            'workspace_id' => $context['workspace']->id,
            'project_id' => $context['project']->id,
        ]), [
            'method' => 'draft',
            'draft_file' => NovelPipelineTestSupport::uploadedFixture('short_story.pdf'),
            'author_style_type' => 'new',
            'newAuthorName' => 'Mock Voice Author',
            'newAuthorFiles' => [
                NovelPipelineTestSupport::uploadedFixture('short_sample_1.pdf'),
                NovelPipelineTestSupport::uploadedFixture('short_sample_2.pdf'),
            ],
            'writing_perspective' => '1st-person',
        ]);

    $response->assertRedirect(route('workspace.projects', ['workspace_id' => $context['workspace']->id]));

    /** @var PipelineRun $run */
    $run = PipelineRun::query()
        ->where('project_id', $context['project']->id)
        ->latest('created_at')
        ->firstOrFail();

    Bus::assertDispatched(MonitorNovelPipelineRunJob::class);

    $pythonClient = app(PythonServiceClient::class);
    $deadline = time() + 90;
    $status = null;

    while (time() < $deadline) {
        $status = $pythonClient->getNovelPipelineStatus($run->id, $context['user']->id);

        if (($status['status'] ?? null) === PipelineRun::STATUS_COMPLETED) {
            break;
        }

        if (($status['status'] ?? null) === PipelineRun::STATUS_FAILED) {
            $this->fail('Python pipeline failed during live integration: '.($status['error_message'] ?? 'unknown error'));
        }

        usleep(500000);
    }

    if (($status['status'] ?? null) !== PipelineRun::STATUS_COMPLETED) {
        $this->fail('Python pipeline did not complete within the live integration timeout.');
    }

    app()->call([
        new MonitorNovelPipelineRunJob($run->id),
        'handle',
    ]);

    $run->refresh();
    $context['project']->refresh();
    $projectContent = ProjectContent::query()->where('project_id', $context['project']->id)->firstOrFail();

    expect($run->status)->toBe(PipelineRun::STATUS_COMPLETED);
    expect($run->import_status)->toBe(PipelineRun::IMPORT_STATUS_COMPLETED);
    expect($run->project_snapshot_id)->not->toBeNull();
    expect($context['project']->completed_onboarding)->toBeTrue();
    expect($projectContent->content_format)->toBe('lexical-json');
    expect($projectContent->metadata['last_pipeline_run_id'])->toBe($run->id);
    expect($projectContent->metadata['total_chapters'])->toBeGreaterThan(0);
    expect($projectContent->content[0]['content'])->toContain('"origin":"ai"');
    expect($projectContent->content[0]['content'])->not->toBe('Original manuscript content.');
});

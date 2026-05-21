<?php

use App\Events\ProjectPipelineLifecycleUpdated;
use App\Jobs\MonitorNovelPipelineRunJob;
use App\Models\AuthorStyle;
use App\Services\PythonServiceClient;
use Illuminate\Foundation\Http\Middleware\ValidateCsrfToken;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Bus;
use Illuminate\Support\Facades\Event;
use Illuminate\Support\Str;
use Tests\Support\NovelPipelineTestSupport;

beforeEach(function () {
    $this->withoutMiddleware(ValidateCsrfToken::class);
});

test('draft onboarding starts the novel pipeline with uploaded author samples', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext();
    $runId = (string) Str::ulid();
    $draftId = (string) Str::ulid();

    Bus::fake();
    Event::fake([ProjectPipelineLifecycleUpdated::class]);

    $pythonClient = Mockery::mock(PythonServiceClient::class);
    $pythonClient->shouldReceive('startNovelPipeline')
        ->once()
        ->withArgs(function (array $payload, $manuscriptFile, array $authorFiles) use ($context) {
            expect($payload['caller']['user_id'])->toBe((string) $context['user']->id);
            expect($payload['caller']['workspace_id'])->toBe($context['workspace']->id);
            expect($payload['caller']['project_id'])->toBe($context['project']->id);
            expect($payload['author_name'])->toBe('Octavia Test');
            expect($payload['author_style_mode'])->toBe('create_or_update');
            expect($payload['writing_perspective'])->toBe('1st-person');
            expect($manuscriptFile->getClientOriginalName())->toBe('short_story.pdf');
            expect($authorFiles)->toHaveCount(2);

            return true;
        })
        ->andReturnUsing(function () use ($context, $runId, $draftId) {
            DB::table('drafts')->insert([
                'id' => $draftId,
                'workspace_id' => $context['workspace']->id,
                'user_id' => $context['user']->id,
                'original_filename' => 'short_story.pdf',
                'file_path' => '/tmp/short_story.pdf',
                'file_size' => 1024,
                'word_count' => 400,
                'status' => 'pending',
                'processing_started_at' => now(),
                'processing_completed_at' => null,
                'error_message' => null,
                'metadata' => json_encode([]),
                'created_at' => now(),
                'updated_at' => now(),
                'deleted_at' => null,
            ]);

            return [
                'pipeline_run_id' => $runId,
                'draft_id' => $draftId,
            ];
        });

    app()->instance(PythonServiceClient::class, $pythonClient);

    $response = $this
        ->actingAs($context['user'])
        ->post(route('editor.project.onboarding', [
            'workspace_id' => $context['workspace']->id,
            'project_id' => $context['project']->id,
        ]), [
            'method' => 'draft',
            'draft_file' => NovelPipelineTestSupport::uploadedFixture('short_story.pdf'),
            'author_style_type' => 'new',
            'newAuthorName' => 'Octavia Test',
            'newAuthorFiles' => [
                NovelPipelineTestSupport::uploadedFixture('short_sample_1.pdf'),
                NovelPipelineTestSupport::uploadedFixture('short_sample_2.pdf'),
            ],
            'writing_perspective' => '1st-person',
        ]);

    $response
        ->assertRedirect(route('workspace.projects', ['workspace_id' => $context['workspace']->id]))
        ->assertSessionHas('success');

    $this->assertDatabaseHas('pipeline_runs', [
        'id' => $runId,
        'draft_id' => $draftId,
        'workspace_id' => $context['workspace']->id,
        'project_id' => $context['project']->id,
        'user_id' => $context['user']->id,
        'status' => 'pending',
        'import_status' => 'pending',
    ]);

    Bus::assertDispatched(MonitorNovelPipelineRunJob::class);
    Event::assertDispatched(ProjectPipelineLifecycleUpdated::class, fn (ProjectPipelineLifecycleUpdated $event) => $event->runId === $runId && $event->shouldToast === true);
});

test('draft onboarding reuses a profiling completed author style without schema gating', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext();
    $runId = (string) Str::ulid();
    $draftId = (string) Str::ulid();

    $authorStyle = AuthorStyle::query()->create([
        'workspace_id' => $context['workspace']->id,
        'project_id' => $context['project']->id,
        'user_id' => $context['user']->id,
        'author_name' => 'Existing Author',
        'schema_version' => 1,
        'techniques_json' => [],
        'examples_json' => [],
        'adaptation_json' => [],
        'status' => 'profiling_completed',
        'started_at' => now(),
        'total_time_ms' => 1234,
    ]);

    Bus::fake();

    $pythonClient = Mockery::mock(PythonServiceClient::class);
    $pythonClient->shouldReceive('startNovelPipeline')
        ->once()
        ->withArgs(function (array $payload, $manuscriptFile, array $authorFiles) use ($authorStyle) {
            expect($payload['author_name'])->toBe($authorStyle->author_name);
            expect($payload['author_style_mode'])->toBe('use_existing');
            expect($authorFiles)->toBe([]);
            expect($manuscriptFile->getClientOriginalName())->toBe('short_story.pdf');

            return true;
        })
        ->andReturnUsing(function () use ($context, $runId, $draftId) {
            DB::table('drafts')->insert([
                'id' => $draftId,
                'workspace_id' => $context['workspace']->id,
                'user_id' => $context['user']->id,
                'original_filename' => 'short_story.pdf',
                'file_path' => '/tmp/short_story.pdf',
                'file_size' => 1024,
                'word_count' => 400,
                'status' => 'pending',
                'processing_started_at' => now(),
                'processing_completed_at' => null,
                'error_message' => null,
                'metadata' => json_encode([]),
                'created_at' => now(),
                'updated_at' => now(),
                'deleted_at' => null,
            ]);

            return [
                'pipeline_run_id' => $runId,
                'draft_id' => $draftId,
            ];
        });

    app()->instance(PythonServiceClient::class, $pythonClient);

    $response = $this
        ->actingAs($context['user'])
        ->post(route('editor.project.onboarding', [
            'workspace_id' => $context['workspace']->id,
            'project_id' => $context['project']->id,
        ]), [
            'method' => 'draft',
            'draft_file' => NovelPipelineTestSupport::uploadedFixture('short_story.pdf'),
            'author_style_type' => 'existing',
            'selectedAuthorStyle' => $authorStyle->id,
            'writing_perspective' => '3rd-person-limited',
        ]);

    $response->assertRedirect(route('workspace.projects', ['workspace_id' => $context['workspace']->id]));
    $this->assertDatabaseHas('pipeline_runs', [
        'id' => $runId,
        'author_name' => 'Existing Author',
    ]);
});

test('draft onboarding rejects an already onboarded project before calling python', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext();
    $context['project']->forceFill(['completed_onboarding' => true])->save();

    $pythonClient = Mockery::mock(PythonServiceClient::class);
    $pythonClient->shouldNotReceive('startNovelPipeline');
    app()->instance(PythonServiceClient::class, $pythonClient);

    $response = $this
        ->from('/editor')
        ->actingAs($context['user'])
        ->post(route('editor.project.onboarding', [
            'workspace_id' => $context['workspace']->id,
            'project_id' => $context['project']->id,
        ]), [
            'method' => 'draft',
            'draft_file' => NovelPipelineTestSupport::uploadedFixture('short_story.pdf'),
            'author_style_type' => 'new',
            'newAuthorName' => 'Octavia Test',
            'newAuthorFiles' => [
                NovelPipelineTestSupport::uploadedFixture('short_sample_1.pdf'),
            ],
            'writing_perspective' => '1st-person',
        ]);

    $response
        ->assertRedirect('/editor')
        ->assertSessionHasErrors('draft_file');
});

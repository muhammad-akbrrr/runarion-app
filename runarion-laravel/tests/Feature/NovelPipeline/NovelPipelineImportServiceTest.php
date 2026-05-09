<?php

use App\Models\ChapterState;
use App\Models\ContentNode;
use App\Models\PipelineRun;
use App\Models\ProjectContent;
use App\Models\ProjectSnapshot;
use App\Services\NovelPipelineImportService;
use App\Services\VersionControlService;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Tests\Support\NovelPipelineTestSupport;

function insertPipelineDraftArtifacts(array $context, string $draftId, array $chapters): void
{
    DB::table('drafts')->updateOrInsert(['id' => $draftId], [
        'id' => $draftId,
        'workspace_id' => $context['workspace']->id,
        'user_id' => $context['user']->id,
        'original_filename' => 'short_story.pdf',
        'file_path' => '/tmp/short_story.pdf',
        'file_size' => 1024,
        'word_count' => 400,
        'status' => 'completed',
        'processing_started_at' => now(),
        'processing_completed_at' => now(),
        'error_message' => null,
        'metadata' => json_encode([]),
        'created_at' => now(),
        'updated_at' => now(),
        'deleted_at' => null,
    ]);

    foreach ($chapters as $index => $chapter) {
        DB::table('chapters')->insert([
            'id' => (string) Str::ulid(),
            'draft_id' => $draftId,
            'chapter_number' => $index + 1,
            'title' => $chapter['title'],
            'content' => $chapter['content'],
            'created_at' => now(),
            'updated_at' => now(),
            'deleted_at' => null,
        ]);
    }
}

test('completed pipeline runs import rewritten chapters into project content', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext([
        'initial_content' => 'Original manuscript content.',
    ]);

    app(VersionControlService::class)->initializeChapter(
        $context['project']->id,
        0,
        'Original manuscript content.',
        true
    );

    $draftId = (string) Str::ulid();
    $run = NovelPipelineTestSupport::createPipelineRun([
        'draft_id' => $draftId,
        'workspace_id' => $context['workspace']->id,
        'project_id' => $context['project']->id,
        'user_id' => $context['user']->id,
        'status' => PipelineRun::STATUS_COMPLETED,
        'phase_1_status' => 'completed',
        'phase_2_status' => 'completed',
        'phase_3_status' => 'completed',
        'import_status' => PipelineRun::IMPORT_STATUS_PENDING,
    ]);

    insertPipelineDraftArtifacts($context, $draftId, [
        [
            'title' => 'Arrival',
            'content' => "A new opening line.\nA second paragraph follows.",
        ],
        [
            'title' => 'Departure',
            'content' => "Another rewritten chapter closes the arc.",
        ],
    ]);

    app(NovelPipelineImportService::class)->importCompletedRun($run);

    $run->refresh();
    $context['project']->refresh();
    $projectContent = ProjectContent::query()->where('project_id', $context['project']->id)->firstOrFail();

    expect($run->import_status)->toBe(PipelineRun::IMPORT_STATUS_COMPLETED);
    expect($run->project_snapshot_id)->not->toBeNull();
    expect($context['project']->completed_onboarding)->toBeTrue();
    expect($projectContent->content_format)->toBe('lexical-json');
    expect($projectContent->metadata['last_pipeline_run_id'])->toBe($run->id);
    expect($projectContent->metadata['total_chapters'])->toBe(2);
    expect($projectContent->content)->toHaveCount(2);
    expect($projectContent->content[0]['content'])->toContain('"origin":"ai"');
    expect(ProjectSnapshot::query()->whereKey($run->project_snapshot_id)->exists())->toBeTrue();
    expect(ChapterState::query()->where('project_id', $context['project']->id)->count())->toBe(2);
    expect(ContentNode::query()->where('project_id', $context['project']->id)->count())->toBe(2);
    expect(ContentNode::query()->where('project_id', $context['project']->id)->where('is_user_generated', false)->count())->toBe(2);
});

test('pipeline import preserves original content when no rewritten chapters exist', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext([
        'initial_content' => 'Original manuscript content.',
    ]);

    app(VersionControlService::class)->initializeChapter(
        $context['project']->id,
        0,
        'Original manuscript content.',
        true
    );

    $draftId = (string) Str::ulid();
    $run = NovelPipelineTestSupport::createPipelineRun([
        'draft_id' => $draftId,
        'workspace_id' => $context['workspace']->id,
        'project_id' => $context['project']->id,
        'user_id' => $context['user']->id,
        'status' => PipelineRun::STATUS_COMPLETED,
        'phase_1_status' => 'completed',
        'phase_2_status' => 'completed',
        'phase_3_status' => 'completed',
        'import_status' => PipelineRun::IMPORT_STATUS_PENDING,
    ]);

    DB::table('drafts')->updateOrInsert(['id' => $draftId], [
        'id' => $draftId,
        'workspace_id' => $context['workspace']->id,
        'user_id' => $context['user']->id,
        'original_filename' => 'short_story.pdf',
        'file_path' => '/tmp/short_story.pdf',
        'file_size' => 1024,
        'word_count' => 400,
        'status' => 'completed',
        'processing_started_at' => now(),
        'processing_completed_at' => now(),
        'error_message' => null,
        'metadata' => json_encode([]),
        'created_at' => now(),
        'updated_at' => now(),
        'deleted_at' => null,
    ]);

    expect(fn () => app(NovelPipelineImportService::class)->importCompletedRun($run))
        ->toThrow(RuntimeException::class, 'The pipeline completed without any rewritten chapters to import.');

    $run->refresh();
    $context['project']->refresh();
    $projectContent = ProjectContent::query()->where('project_id', $context['project']->id)->firstOrFail();

    expect($context['project']->completed_onboarding)->toBeFalse();
    expect($projectContent->content[0]['content'])->toBe('Original manuscript content.');
    expect($run->project_snapshot_id)->not->toBeNull();
    expect($run->import_status)->toBe(PipelineRun::IMPORT_STATUS_PENDING);
});

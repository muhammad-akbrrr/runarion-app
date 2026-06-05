<?php

namespace App\Services;

use App\Models\Chapter;
use App\Models\ChapterState;
use App\Models\PipelineRun;
use App\Models\ProjectContent;
use App\Models\Projects;
use Illuminate\Support\Facades\DB;
use RuntimeException;

class NovelPipelineImportService
{
    public function __construct(
        private readonly VersionControlService $versionControl,
        private readonly LexicalContentSerializer $lexicalContentSerializer,
    ) {}

    public function importCompletedRun(PipelineRun $run): void
    {
        $lockedRun = PipelineRun::query()->lockForUpdate()->findOrFail($run->id);

        if ($lockedRun->import_status === PipelineRun::IMPORT_STATUS_COMPLETED) {
            return;
        }

        if (! $lockedRun->project_id) {
            throw new RuntimeException('Pipeline run is missing project linkage.');
        }

        $project = Projects::query()->findOrFail($lockedRun->project_id);

        if (! $lockedRun->project_snapshot_id) {
            $snapshotId = $this->versionControl->createSnapshot(
                $project->id,
                'Pre-pipeline rewrite import',
                'Automatic snapshot created before importing the rewritten manuscript.',
                $lockedRun->user_id
            );

            $lockedRun->project_snapshot_id = $snapshotId;
            $lockedRun->save();
        }

        $chapters = Chapter::query()
            ->where('draft_id', $lockedRun->draft_id)
            ->orderBy('chapter_number')
            ->get();

        if ($chapters->isEmpty()) {
            throw new RuntimeException('The pipeline completed without any rewritten chapters to import.');
        }

        $lockedRun->import_status = PipelineRun::IMPORT_STATUS_RUNNING;
        $lockedRun->import_error_message = null;
        $lockedRun->save();

        DB::transaction(function () use ($lockedRun, $project, $chapters) {
            $projectContent = ProjectContent::query()->firstOrNew([
                'project_id' => $project->id,
            ]);

            $existingOrders = ChapterState::query()
                ->where('project_id', $project->id)
                ->pluck('chapter_order')
                ->unique()
                ->sort()
                ->values();

            foreach ($existingOrders as $chapterOrder) {
                $this->versionControl->deleteChapterVersionControl($project->id, (int) $chapterOrder);
            }

            $rewrittenChapters = [];
            $totalWords = 0;
            foreach ($chapters as $chapter) {
                $content = $this->lexicalContentSerializer->plainTextToOriginLexical($chapter->content ?? '', 'ai');
                $order = max(0, ((int) $chapter->chapter_number) - 1);
                $title = trim((string) $chapter->title) !== '' ? $chapter->title : sprintf('Chapter %d', $chapter->chapter_number);

                $rewrittenChapters[] = [
                    'order' => $order,
                    'chapter_name' => $title,
                    'content' => $content,
                    'summary' => null,
                    'plot_points' => null,
                ];

                $totalWords += str_word_count((string) $chapter->content);
            }

            $chapterCount = count($rewrittenChapters);
            $projectContent->content = $rewrittenChapters;
            $projectContent->content_format = 'lexical-json';
            $projectContent->metadata = [
                'total_words' => $totalWords,
                'total_chapters' => $chapterCount,
                'average_words_per_chapter' => $chapterCount > 0 ? (int) floor($totalWords / $chapterCount) : 0,
                'last_pipeline_run_id' => $lockedRun->id,
                'last_pipeline_imported_at' => now()->toISOString(),
            ];
            $projectContent->last_edited_by = $lockedRun->user_id;
            $projectContent->last_edited_at = now();
            $projectContent->save();

            foreach ($rewrittenChapters as $chapter) {
                $this->versionControl->initializeChapter(
                    $project->id,
                    (int) $chapter['order'],
                    (string) $chapter['content'],
                    false
                );
            }

            $project->completed_onboarding = true;
            $project->save();

            $lockedRun->import_status = PipelineRun::IMPORT_STATUS_COMPLETED;
            $lockedRun->imported_at = now();
            $lockedRun->import_error_message = null;
            $lockedRun->save();
        });
    }
}

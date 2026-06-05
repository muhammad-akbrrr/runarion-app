<?php

namespace App\Console\Commands;

use App\Models\ProjectContent;
use App\Services\VersionControlService;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class MigrateVersionControl extends Command
{
    protected $signature = 'migrate:version-control {--dry-run : Show what would be migrated without making changes}';

    protected $description = 'Migrate existing generation history to optimized version control system';

    public function handle()
    {
        $dryRun = $this->option('dry-run');
        $versionControlService = app(VersionControlService::class);

        if ($dryRun) {
            $this->info('DRY RUN MODE - No changes will be made');
        }

        $projectContents = ProjectContent::whereNotNull('content')->get();
        $this->info("Found {$projectContents->count()} projects to process");

        $bar = $this->output->createProgressBar($projectContents->count());
        $bar->start();

        foreach ($projectContents as $projectContent) {
            try {
                $chapters = $projectContent->content ?? [];

                foreach ($chapters as $chapter) {
                    if (! isset($chapter['order'])) {
                        continue;
                    }

                    $chapterOrder = $chapter['order'];
                    $content = $chapter['content'] ?? '';

                    // Check if already migrated
                    $existingState = DB::table('chapter_states')
                        ->where('project_id', $projectContent->project_id)
                        ->where('chapter_order', $chapterOrder)
                        ->exists();

                    if ($existingState) {
                        continue; // Already migrated
                    }

                    if (! $dryRun) {
                        // Initialize version control for this chapter
                        $versionControlService->initializeChapter(
                            $projectContent->project_id,
                            $chapterOrder,
                            $content
                        );
                    }

                    $this->line("\nMigrated chapter {$chapterOrder} for project {$projectContent->project_id}");
                }

            } catch (\Exception $e) {
                $this->error("\nFailed to migrate project {$projectContent->project_id}: ".$e->getMessage());
            }

            $bar->advance();
        }

        $bar->finish();

        if ($dryRun) {
            $this->info("\nDry run completed. Run without --dry-run to perform actual migration.");
        } else {
            $this->info("\nMigration completed successfully!");
        }
    }
}

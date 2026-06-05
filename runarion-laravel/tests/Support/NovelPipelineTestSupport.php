<?php

namespace Tests\Support;

use App\Models\PipelineRun;
use App\Models\ProjectContent;
use App\Models\ProjectNodeEditor;
use App\Models\Projects;
use App\Models\User;
use App\Models\Workspace;
use App\Models\WorkspaceMember;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use PHPUnit\Framework\SkippedTestError;
use RuntimeException;

class NovelPipelineTestSupport
{
    public static function createWorkspaceContext(array $overrides = []): array
    {
        $user = $overrides['user'] ?? User::factory()->create();
        $workspace = $overrides['workspace'] ?? Workspace::factory()->create();

        WorkspaceMember::query()->create([
            'workspace_id' => $workspace->id,
            'user_id' => $user->id,
            'role' => 'owner',
        ]);

        $user->forceFill([
            'last_workspace_id' => $workspace->id,
        ])->saveQuietly();

        $project = Projects::query()->create([
            'workspace_id' => $workspace->id,
            'folder_id' => null,
            'original_author' => $user->id,
            'name' => $overrides['project_name'] ?? 'Pipeline Test Project',
            'slug' => Str::slug($overrides['project_name'] ?? 'Pipeline Test Project'),
            'settings' => null,
            'category' => null,
            'saved_in' => '01',
            'description' => null,
            'access' => [[
                'user' => [
                    'id' => $user->id,
                    'name' => $user->name,
                    'email' => $user->email,
                    'avatar_url' => $user->avatar_url,
                ],
                'role' => 'admin',
            ]],
            'is_active' => true,
            'backup_frequency' => 'manual',
            'completed_onboarding' => false,
        ]);

        ProjectContent::query()->create([
            'project_id' => $project->id,
            'content' => [[
                'order' => 0,
                'chapter_name' => 'Chapter 1',
                'content' => $overrides['initial_content'] ?? '',
                'summary' => null,
                'plot_points' => null,
            ]],
            'content_format' => 'plain-text',
            'metadata' => [
                'total_words' => str_word_count((string) ($overrides['initial_content'] ?? '')),
                'total_chapters' => 1,
                'average_words_per_chapter' => str_word_count((string) ($overrides['initial_content'] ?? '')),
            ],
            'last_edited_by' => $user->id,
            'last_edited_at' => now(),
        ]);

        ProjectNodeEditor::query()->create([
            'project_id' => $project->id,
        ]);

        return compact('user', 'workspace', 'project');
    }

    public static function uploadedFixture(string $filename): UploadedFile
    {
        $path = self::fixturePath($filename);

        return new UploadedFile(
            $path,
            basename($path),
            mime_content_type($path) ?: 'application/octet-stream',
            null,
            true
        );
    }

    public static function fixturePath(string $filename): string
    {
        $candidates = [
            base_path("../runarion-python/tests/sample/input/{$filename}"),
            '/var/www/python-test-samples/input/'.$filename,
        ];

        foreach ($candidates as $candidate) {
            if (is_file($candidate)) {
                return $candidate;
            }
        }

        throw new RuntimeException("Novel pipeline fixture not found: {$filename}");
    }

    public static function createPipelineRun(array $attributes): PipelineRun
    {
        $draftId = (string) ($attributes['draft_id'] ?? Str::ulid());
        self::ensureDraftExists($draftId, $attributes);

        return PipelineRun::query()->create(array_merge([
            'id' => (string) Str::ulid(),
            'draft_id' => $draftId,
            'workspace_id' => $attributes['workspace_id'],
            'project_id' => $attributes['project_id'],
            'user_id' => $attributes['user_id'],
            'author_name' => $attributes['author_name'] ?? 'Test Author',
            'status' => PipelineRun::STATUS_PENDING,
            'phase_1_status' => 'pending',
            'phase_2_status' => 'pending',
            'phase_3_status' => 'pending',
            'import_status' => PipelineRun::IMPORT_STATUS_PENDING,
            'started_at' => now(),
        ], $attributes));
    }

    private static function ensureDraftExists(string $draftId, array $attributes): void
    {
        if (DB::table('drafts')->where('id', $draftId)->exists()) {
            return;
        }

        DB::table('drafts')->insert([
            'id' => $draftId,
            'workspace_id' => $attributes['workspace_id'],
            'user_id' => $attributes['user_id'],
            'original_filename' => $attributes['draft_original_filename'] ?? 'short_story.pdf',
            'file_path' => $attributes['draft_file_path'] ?? '/tmp/short_story.pdf',
            'file_size' => $attributes['draft_file_size'] ?? 1024,
            'word_count' => $attributes['draft_word_count'] ?? 400,
            'status' => $attributes['draft_status'] ?? 'pending',
            'processing_started_at' => $attributes['draft_processing_started_at'] ?? now(),
            'processing_completed_at' => $attributes['draft_processing_completed_at'] ?? null,
            'error_message' => $attributes['draft_error_message'] ?? null,
            'metadata' => json_encode($attributes['draft_metadata'] ?? []),
            'created_at' => now(),
            'updated_at' => now(),
            'deleted_at' => null,
        ]);
    }

    public static function skipUnlessLivePythonEnabled(): void
    {
        if (! filter_var(env('RUN_LIVE_PYTHON_INTEGRATION', false), FILTER_VALIDATE_BOOL)) {
            throw new SkippedTestError('Live Python integration tests are disabled.');
        }

        $url = rtrim((string) config('services.python.url', ''), '/').'/health';

        try {
            $response = Http::timeout(2)->get($url);
        } catch (\Throwable) {
            throw new SkippedTestError('Python service is not reachable for live integration tests.');
        }

        if (! $response->successful()) {
            throw new SkippedTestError('Python healthcheck failed for live integration tests.');
        }
    }
}

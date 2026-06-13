<?php

use App\Models\ProjectSnapshot;
use Carbon\CarbonImmutable;
use Illuminate\Foundation\Http\Middleware\ValidateCsrfToken;
use Tests\Support\NovelPipelineTestSupport;

beforeEach(function () {
    $this->withoutMiddleware(ValidateCsrfToken::class);
});

test('snapshot compaction preserves current month manual snapshots and trims older month autosaves to three', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext();
    $projectId = $context['project']->id;

    $now = CarbonImmutable::parse('2026-06-13 12:00:00');
    Carbon\Carbon::setTestNow($now);

    foreach (range(0, 18) as $index) {
        $snapshot = ProjectSnapshot::query()->create([
            'project_id' => $projectId,
            'name' => "Recent Autosave {$index}",
            'description' => null,
            'snapshot_kind' => ProjectSnapshot::KIND_AUTOSAVE,
            'is_immutable' => false,
            'schema_version' => 2,
            'state_hash' => "recent-{$index}",
            'snapshot_data' => ['test' => $index],
        ]);

        $snapshot->forceFill([
            'created_at' => $now->subHours($index * 4),
            'updated_at' => $now->subHours($index * 4),
        ])->saveQuietly();
    }

    $manualSnapshot = ProjectSnapshot::query()->create([
        'project_id' => $projectId,
        'name' => 'Exceptional Manual Snapshot',
        'description' => null,
        'snapshot_kind' => ProjectSnapshot::KIND_MANUAL,
        'is_immutable' => false,
        'schema_version' => 2,
        'state_hash' => 'manual-current-month',
        'snapshot_data' => ['manual' => true],
    ]);
    $manualSnapshot->forceFill([
        'created_at' => $now->subDays(5),
        'updated_at' => $now->subDays(5),
    ])->saveQuietly();

    foreach (range(0, 3) as $index) {
        $snapshot = ProjectSnapshot::query()->create([
            'project_id' => $projectId,
            'name' => "May Autosave {$index}",
            'description' => null,
            'snapshot_kind' => ProjectSnapshot::KIND_AUTOSAVE,
            'is_immutable' => false,
            'schema_version' => 2,
            'state_hash' => "older-{$index}",
            'snapshot_data' => ['older' => $index],
        ]);

        $snapshot->forceFill([
            'created_at' => CarbonImmutable::parse("2026-05-".sprintf('%02d', 2 + ($index * 7))." 08:00:00"),
            'updated_at' => CarbonImmutable::parse("2026-05-".sprintf('%02d', 2 + ($index * 7))." 08:00:00"),
        ])->saveQuietly();
    }

    $this->artisan('projects:snapshots:manage', [
        '--project' => $projectId,
        '--skip-capture' => true,
    ])->assertExitCode(0);

    expect(ProjectSnapshot::query()->whereKey($manualSnapshot->id)->whereNull('deleted_at')->exists())->toBeTrue();

    $recentAutosaveCount = ProjectSnapshot::query()
        ->where('project_id', $projectId)
        ->where('snapshot_kind', ProjectSnapshot::KIND_AUTOSAVE)
        ->whereBetween('created_at', [$now->startOfMonth(), $now])
        ->whereNull('deleted_at')
        ->count();

    expect($recentAutosaveCount)->toBe(18);

    $olderMonthAutosaveCount = ProjectSnapshot::query()
        ->where('project_id', $projectId)
        ->where('snapshot_kind', ProjectSnapshot::KIND_AUTOSAVE)
        ->whereBetween('created_at', [
            CarbonImmutable::parse('2026-05-01 00:00:00'),
            CarbonImmutable::parse('2026-05-31 23:59:59'),
        ])
        ->whereNull('deleted_at')
        ->count();

    expect($olderMonthAutosaveCount)->toBe(3);

    Carbon\Carbon::setTestNow();
});

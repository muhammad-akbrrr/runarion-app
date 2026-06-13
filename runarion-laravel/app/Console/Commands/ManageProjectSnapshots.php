<?php

namespace App\Console\Commands;

use App\Models\ProjectSnapshot;
use App\Models\Projects;
use App\Services\ProjectSnapshotService;
use Carbon\CarbonImmutable;
use Illuminate\Console\Command;
use Illuminate\Support\Collection;

class ManageProjectSnapshots extends Command
{
    protected $signature = 'projects:snapshots:manage {--project=} {--skip-capture} {--skip-compaction}';

    protected $description = 'Create periodic project autosnapshots and compact historical project snapshots.';

    public function __construct(
        private readonly ProjectSnapshotService $projectSnapshotService,
    ) {
        parent::__construct();
    }

    public function handle(): int
    {
        $projectIds = Projects::query()
            ->where('is_active', true)
            ->when($this->option('project'), fn ($query, $projectId) => $query->where('id', $projectId))
            ->pluck('id');

        foreach ($projectIds as $projectId) {
            $this->projectSnapshotService->ensureAnchorSnapshot($projectId);

            if (! $this->option('skip-capture')) {
                $this->captureAutosnapshotIfChanged($projectId);
            }

            if (! $this->option('skip-compaction')) {
                $this->compactSnapshots($projectId);
            }
        }

        return self::SUCCESS;
    }

    private function captureAutosnapshotIfChanged(string $projectId): void
    {
        $currentHash = $this->projectSnapshotService->getCurrentProjectStateHash($projectId);
        $latestAutosaveHash = $this->projectSnapshotService->getLatestSnapshotHashByKind(
            $projectId,
            ProjectSnapshot::KIND_AUTOSAVE,
        );

        if ($currentHash === $latestAutosaveHash) {
            return;
        }

        $this->projectSnapshotService->createSnapshot(
            $projectId,
            sprintf('Autosave %s', now()->format('Y-m-d H:i')),
            'Automatic periodic project snapshot.',
            null,
            ProjectSnapshot::KIND_AUTOSAVE,
        );

        Projects::query()->where('id', $projectId)->update([
            'last_backup_at' => now(),
            'next_backup_at' => now()->addHours(4),
        ]);
    }

    private function compactSnapshots(string $projectId): void
    {
        $now = CarbonImmutable::now();
        $currentMonthStart = $now->startOfMonth();
        $recentCutoff = $now->subDays(3);

        /** @var Collection<int, ProjectSnapshot> $snapshots */
        $snapshots = ProjectSnapshot::query()
            ->where('project_id', $projectId)
            ->whereNull('deleted_at')
            ->orderBy('created_at')
            ->get();

        $keepIds = $snapshots
            ->filter(fn (ProjectSnapshot $snapshot) => $snapshot->snapshot_kind === ProjectSnapshot::KIND_ANCHOR)
            ->pluck('id')
            ->all();

        $currentMonthSnapshots = $snapshots->filter(
            fn (ProjectSnapshot $snapshot) => $snapshot->created_at !== null
                && $snapshot->created_at->greaterThanOrEqualTo($currentMonthStart),
        );

        $olderSnapshots = $snapshots->filter(
            fn (ProjectSnapshot $snapshot) => $snapshot->created_at !== null
                && $snapshot->created_at->lessThan($currentMonthStart),
        );

        $keepIds = array_merge(
            $keepIds,
            $this->keepCurrentMonthSnapshots($currentMonthSnapshots, $recentCutoff),
            $this->keepOlderMonthSnapshots($olderSnapshots),
        );

        $keepIds = array_values(array_unique($keepIds));

        ProjectSnapshot::query()
            ->where('project_id', $projectId)
            ->whereNull('deleted_at')
            ->whereNotIn('id', $keepIds)
            ->delete();
    }

    /**
     * Manual snapshots are exceptional only within the current month.
     */
    private function keepCurrentMonthSnapshots(Collection $snapshots, CarbonImmutable $recentCutoff): array
    {
        $keepIds = $snapshots
            ->filter(fn (ProjectSnapshot $snapshot) => in_array($snapshot->snapshot_kind, [
                ProjectSnapshot::KIND_MANUAL,
                ProjectSnapshot::KIND_PRE_RESTORE,
                ProjectSnapshot::KIND_PIPELINE_IMPORT,
            ], true))
            ->pluck('id')
            ->all();

        $autosaves = $snapshots
            ->filter(fn (ProjectSnapshot $snapshot) => $snapshot->snapshot_kind === ProjectSnapshot::KIND_AUTOSAVE)
            ->sortBy('created_at')
            ->values();

        $recentAutosaves = $autosaves
            ->filter(fn (ProjectSnapshot $snapshot) => $snapshot->created_at !== null && $snapshot->created_at->greaterThanOrEqualTo($recentCutoff))
            ->sortByDesc('created_at')
            ->take(18)
            ->pluck('id')
            ->all();

        $olderCurrentMonthAutosaves = $autosaves
            ->filter(fn (ProjectSnapshot $snapshot) => $snapshot->created_at !== null && $snapshot->created_at->lessThan($recentCutoff))
            ->groupBy(fn (ProjectSnapshot $snapshot) => $snapshot->created_at?->format('Y-m-d'))
            ->map(fn (Collection $daySnapshots) => $daySnapshots->sortByDesc('created_at')->first()?->id)
            ->filter()
            ->sort()
            ->take(-27)
            ->values()
            ->all();

        return array_merge($keepIds, $recentAutosaves, $olderCurrentMonthAutosaves);
    }

    private function keepOlderMonthSnapshots(Collection $snapshots): array
    {
        $keepIds = [];

        $groups = $snapshots->groupBy(fn (ProjectSnapshot $snapshot) => $snapshot->created_at?->format('Y-m'));

        foreach ($groups as $monthSnapshots) {
            $ordered = $monthSnapshots->sortBy('created_at')->values();
            if ($ordered->isEmpty()) {
                continue;
            }

            $earliest = $ordered->first();
            $latest = $ordered->last();

            $keepIds[] = $earliest->id;
            $keepIds[] = $latest->id;

            $midpoint = $earliest->created_at->getTimestamp()
                + (int) floor(($latest->created_at->getTimestamp() - $earliest->created_at->getTimestamp()) / 2);

            $midpointSnapshot = $ordered
                ->sortBy(fn (ProjectSnapshot $snapshot) => abs($snapshot->created_at->getTimestamp() - $midpoint))
                ->first();

            if ($midpointSnapshot) {
                $keepIds[] = $midpointSnapshot->id;
            }
        }

        return array_values(array_unique($keepIds));
    }
}

<?php

namespace App\Services;

use App\Jobs\RestoreProjectSnapshotJob;
use App\Models\NovelGraphEdge;
use App\Models\NovelGraphVertex;
use App\Models\ProjectNodeEditor;
use App\Models\ProjectOperation;
use App\Models\Projects;
use App\Models\ProjectContent;
use App\Models\ProjectSnapshot;
use Illuminate\Support\Arr;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

class ProjectSnapshotService
{
    public function __construct(
        private readonly ProjectGraphRestoreService $projectGraphRestoreService,
        private readonly ProjectOperationStateService $projectOperationStateService,
    ) {}

    public function createSnapshot(
        string $projectId,
        ?string $name = null,
        ?string $description = null,
        ?int $createdBy = null,
        string $snapshotKind = ProjectSnapshot::KIND_MANUAL,
        bool $isImmutable = false,
        ?string $sourceSnapshotId = null,
    ): string {
        return DB::transaction(function () use ($projectId, $name, $description, $createdBy, $snapshotKind, $isImmutable, $sourceSnapshotId) {
            $snapshotData = $this->buildProjectSnapshotData($projectId);
            $stateHash = $this->computeSnapshotHash($snapshotData);

            $snapshot = ProjectSnapshot::create([
                'project_id' => $projectId,
                'name' => $name,
                'description' => $description,
                'snapshot_kind' => $snapshotKind,
                'is_immutable' => $isImmutable,
                'source_snapshot_id' => $sourceSnapshotId,
                'schema_version' => 2,
                'state_hash' => $stateHash,
                'snapshot_data' => $snapshotData,
                'created_by' => $createdBy ?? auth()->id(),
            ]);

            Log::info('Snapshot created', [
                'snapshot_id' => $snapshot->id,
                'project_id' => $projectId,
                'snapshot_kind' => $snapshotKind,
                'state_hash' => $stateHash,
            ]);

            return $snapshot->id;
        });
    }

    public function ensureAnchorSnapshot(string $projectId, ?int $createdBy = null): string
    {
        $existingAnchor = ProjectSnapshot::query()
            ->where('project_id', $projectId)
            ->where('snapshot_kind', ProjectSnapshot::KIND_ANCHOR)
            ->orderBy('created_at')
            ->first();

        if ($existingAnchor) {
            return $existingAnchor->id;
        }

        return $this->createSnapshot(
            $projectId,
            'Original Version',
            'Immutable anchor snapshot created when the project was initialized.',
            $createdBy,
            ProjectSnapshot::KIND_ANCHOR,
            true,
        );
    }

    public function getLatestSnapshotHashByKind(string $projectId, string $snapshotKind): ?string
    {
        return ProjectSnapshot::query()
            ->where('project_id', $projectId)
            ->where('snapshot_kind', $snapshotKind)
            ->latest('created_at')
            ->value('state_hash');
    }

    public function getCurrentProjectStateHash(string $projectId): string
    {
        return $this->computeSnapshotHash($this->buildProjectSnapshotData($projectId));
    }

    public function getSnapshotSummary(string $projectId): array
    {
        $snapshotCount = ProjectSnapshot::query()->where('project_id', $projectId)->count();
        $projectContent = ProjectContent::query()->where('project_id', $projectId)->first();

        return [
            'snapshot_count' => $snapshotCount,
            'chapter_count' => count($projectContent?->content ?? []),
            'chat_count' => DB::table('advisor_chats')->where('project_id', $projectId)->count(),
            'message_count' => DB::table('advisor_messages')
                ->whereIn('chat_id', DB::table('advisor_chats')->where('project_id', $projectId)->select('id'))
                ->count(),
            'entity_count' => NovelGraphVertex::query()->where('project_id', $projectId)->whereNull('deleted_at')->count(),
            'relationship_count' => NovelGraphEdge::query()->where('project_id', $projectId)->whereNull('deleted_at')->count(),
            'has_multiprompt_state' => ! empty(ProjectNodeEditor::query()->where('project_id', $projectId)->value('graph_state')),
        ];
    }

    public function queueRestoreSnapshot(string $workspaceId, string $projectId, string $snapshotId, ?int $createdBy = null): ProjectOperation
    {
        return DB::transaction(function () use ($workspaceId, $projectId, $snapshotId, $createdBy) {
            $snapshot = ProjectSnapshot::query()
                ->where('id', $snapshotId)
                ->where('project_id', $projectId)
                ->first();

            if (! $snapshot) {
                throw new \RuntimeException('Snapshot not found.');
            }

            $this->createSnapshot(
                $projectId,
                'Pre-Restore Safety Snapshot',
                'Automatic snapshot created immediately before restoring another snapshot.',
                $createdBy,
                ProjectSnapshot::KIND_PRE_RESTORE,
                true,
                $snapshot->id,
            );

            $operation = $this->projectOperationStateService->createRestoreOperation(
                $workspaceId,
                $projectId,
                $snapshotId,
                $createdBy,
            );

            RestoreProjectSnapshotJob::dispatch($workspaceId, $projectId, $snapshotId, $operation->id);

            return $operation;
        });
    }

    public function restoreSnapshotNow(string $projectId, string $snapshotId): bool
    {
        return DB::transaction(function () use ($projectId, $snapshotId) {
            $snapshot = ProjectSnapshot::query()
                ->where('id', $snapshotId)
                ->where('project_id', $projectId)
                ->first();

            if (! $snapshot) {
                Log::warning('Snapshot not found for restore', [
                    'snapshot_id' => $snapshotId,
                    'project_id' => $projectId,
                ]);

                return false;
            }

            $snapshotData = $snapshot->snapshot_data ?? [];

            if (! isset($snapshotData['project']) && ! isset($snapshotData['project_content'])) {
                return $this->loadLegacySnapshot($projectId, $snapshotData);
            }

            $this->restoreProjectSnapshotData($projectId, $snapshotData);

            Log::info('Snapshot restore completed', [
                'snapshot_id' => $snapshotId,
                'project_id' => $projectId,
                'snapshot_kind' => $snapshot->snapshot_kind,
            ]);

            return true;
        });
    }

    private function buildProjectSnapshotData(string $projectId): array
    {
        $project = Projects::query()->findOrFail($projectId);
        $projectContent = ProjectContent::query()->where('project_id', $projectId)->first();
        $nodeEditor = ProjectNodeEditor::query()->where('project_id', $projectId)->first();
        $chatIds = DB::table('advisor_chats')->where('project_id', $projectId)->pluck('id');

        return [
            'project' => [
                'settings' => $project->settings,
                'completed_onboarding' => $project->completed_onboarding,
                'backup_frequency' => $project->backup_frequency,
                'last_backup_at' => optional($project->last_backup_at)?->toISOString(),
                'next_backup_at' => optional($project->next_backup_at)?->toISOString(),
            ],
            'project_content' => [
                'content' => $projectContent?->content ?? [],
                'content_format' => $projectContent?->content_format,
                'metadata' => $projectContent?->metadata,
                'generation_history' => $projectContent?->generation_history,
                'current_step_id' => $projectContent?->current_step_id,
                'last_selected_versions' => $projectContent?->last_selected_versions,
                'last_edited_at' => optional($projectContent?->last_edited_at)?->toISOString(),
                'last_edited_by' => $projectContent?->last_edited_by,
            ],
            'chapter_version_control' => [
                'content_nodes' => DB::table('content_nodes')
                    ->where('project_id', $projectId)
                    ->orderBy('chapter_order')
                    ->orderBy('created_at')
                    ->get()
                    ->map(fn ($row) => (array) $row)
                    ->all(),
                'content_versions' => DB::table('content_versions')
                    ->whereIn('node_id', DB::table('content_nodes')->where('project_id', $projectId)->select('id'))
                    ->orderBy('node_id')
                    ->orderBy('version_index')
                    ->get()
                    ->map(fn ($row) => (array) $row)
                    ->all(),
                'chapter_states' => DB::table('chapter_states')
                    ->where('project_id', $projectId)
                    ->orderBy('chapter_order')
                    ->get()
                    ->map(fn ($row) => (array) $row)
                    ->all(),
            ],
            'advisor' => [
                'chats' => DB::table('advisor_chats')
                    ->where('project_id', $projectId)
                    ->orderBy('created_at')
                    ->get()
                    ->map(fn ($row) => (array) $row)
                    ->all(),
                'messages' => $chatIds->isEmpty()
                    ? []
                    : DB::table('advisor_messages')
                        ->whereIn('chat_id', $chatIds)
                        ->orderBy('created_at')
                        ->get()
                        ->map(fn ($row) => (array) $row)
                        ->all(),
            ],
            'records' => [
                'entities' => NovelGraphVertex::query()
                    ->withTrashed()
                    ->where('project_id', $projectId)
                    ->orderBy('id')
                    ->get()
                    ->map(fn ($row) => Arr::only($row->toArray(), [
                        'id', 'draft_id', 'project_id', 'entity_type', 'entity_name', 'vertex_id',
                        'vertex_label', 'properties', 'created_at', 'updated_at', 'deleted_at',
                    ]))
                    ->all(),
                'relationships' => NovelGraphEdge::query()
                    ->withTrashed()
                    ->where('project_id', $projectId)
                    ->orderBy('id')
                    ->get()
                    ->map(fn ($row) => Arr::only($row->toArray(), [
                        'id', 'draft_id', 'project_id', 'scene_id', 'source_vertex_id', 'target_vertex_id',
                        'edge_id', 'edge_label', 'properties', 'created_at', 'updated_at', 'deleted_at',
                    ]))
                    ->all(),
                'entity_types' => DB::table('record_entity_types')
                    ->where('project_id', $projectId)
                    ->orderBy('created_at')
                    ->get()
                    ->map(fn ($row) => (array) $row)
                    ->all(),
                'relationship_types' => DB::table('record_relationship_types')
                    ->where('project_id', $projectId)
                    ->orderBy('created_at')
                    ->get()
                    ->map(fn ($row) => (array) $row)
                    ->all(),
            ],
            'multiprompt' => [
                'graph_state' => $nodeEditor?->graph_state,
                'templates' => $nodeEditor?->templates,
            ],
        ];
    }

    private function computeSnapshotHash(array $snapshotData): string
    {
        return hash('sha256', json_encode($snapshotData, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRESERVE_ZERO_FRACTION));
    }

    private function restoreProjectSnapshotData(string $projectId, array $snapshotData): void
    {
        $projectData = $snapshotData['project'] ?? [];
        $projectContentData = $snapshotData['project_content'] ?? [];
        $versionControlData = $snapshotData['chapter_version_control'] ?? [];
        $advisorData = $snapshotData['advisor'] ?? [];
        $recordsData = $snapshotData['records'] ?? [];
        $multipromptData = $snapshotData['multiprompt'] ?? [];

        $project = Projects::query()->findOrFail($projectId);
        $project->settings = $projectData['settings'] ?? [];
        $project->completed_onboarding = $projectData['completed_onboarding'] ?? false;
        $project->backup_frequency = $projectData['backup_frequency'] ?? 'manual';
        $project->last_backup_at = $projectData['last_backup_at'] ?? null;
        $project->next_backup_at = $projectData['next_backup_at'] ?? null;
        $project->save();

        $projectContent = ProjectContent::query()->firstOrNew(['project_id' => $projectId]);
        $projectContent->content = $projectContentData['content'] ?? [];
        $projectContent->content_format = $projectContentData['content_format'] ?? null;
        $projectContent->metadata = $projectContentData['metadata'] ?? null;
        $projectContent->generation_history = $projectContentData['generation_history'] ?? null;
        $projectContent->current_step_id = $projectContentData['current_step_id'] ?? null;
        $projectContent->last_selected_versions = $projectContentData['last_selected_versions'] ?? null;
        $projectContent->last_edited_at = $projectContentData['last_edited_at'] ?? null;
        $projectContent->last_edited_by = $projectContentData['last_edited_by'] ?? null;
        $projectContent->save();

        DB::table('content_versions')->whereIn('node_id', DB::table('content_nodes')->where('project_id', $projectId)->select('id'))->delete();
        DB::table('chapter_states')->where('project_id', $projectId)->delete();
        DB::table('content_nodes')->where('project_id', $projectId)->delete();

        $contentNodes = $versionControlData['content_nodes'] ?? [];
        $contentVersions = $versionControlData['content_versions'] ?? [];
        $chapterStates = $versionControlData['chapter_states'] ?? [];

        if ($contentNodes !== []) {
            DB::table('content_nodes')->insert(array_map(function (array $row) {
                $row['generation_settings'] = array_key_exists('generation_settings', $row)
                    ? $this->normalizeJsonForInsert($row['generation_settings'])
                    : null;

                return $row;
            }, $contentNodes));
        }

        if ($contentVersions !== []) {
            DB::table('content_versions')->insert($contentVersions);
        }

        if ($chapterStates !== []) {
            DB::table('chapter_states')->insert($chapterStates);
        }

        DB::table('advisor_messages')->whereIn('chat_id', DB::table('advisor_chats')->where('project_id', $projectId)->select('id'))->delete();
        DB::table('advisor_chats')->where('project_id', $projectId)->delete();

        if (! empty($advisorData['chats'])) {
            DB::table('advisor_chats')->insert($advisorData['chats']);
        }

        if (! empty($advisorData['messages'])) {
            DB::table('advisor_messages')->insert(array_map(function (array $row) {
                if (array_key_exists('metadata', $row)) {
                    $row['metadata'] = $this->normalizeJsonForInsert($row['metadata']);
                }

                return $row;
            }, $advisorData['messages']));
        }

        $this->projectGraphRestoreService->restore(
            $projectId,
            $recordsData['entities'] ?? [],
            $recordsData['relationships'] ?? [],
        );

        if (! empty($recordsData['entity_types'])) {
            DB::table('record_entity_types')->insert(array_map(function (array $row) {
                if (array_key_exists('field_schema', $row)) {
                    $row['field_schema'] = $this->normalizeJsonForInsert($row['field_schema']);
                }

                return $row;
            }, $recordsData['entity_types']));
        }

        if (! empty($recordsData['relationship_types'])) {
            DB::table('record_relationship_types')->insert($recordsData['relationship_types']);
        }

        $nodeEditor = ProjectNodeEditor::query()->firstOrNew(['project_id' => $projectId]);
        $nodeEditor->graph_state = $multipromptData['graph_state'] ?? null;
        $nodeEditor->templates = $multipromptData['templates'] ?? null;
        $nodeEditor->save();

        foreach ($projectContent->content ?? [] as $chapter) {
            if (isset($chapter['order'])) {
                Cache::forget("content:{$projectId}:{$chapter['order']}");
                Cache::forget("navigation:{$projectId}:{$chapter['order']}");
            }
        }
    }

    private function loadLegacySnapshot(string $projectId, array $snapshotData): bool
    {
        $chapterStatesData = $snapshotData['chapter_states'] ?? $snapshotData;
        $chaptersData = $snapshotData['chapters'] ?? [];
        $entitiesData = $snapshotData['entities'] ?? [];
        $relationshipsData = $snapshotData['relationships'] ?? [];

        $this->restoreProjectSnapshotData($projectId, [
            'project_content' => [
                'content' => $chaptersData,
            ],
            'chapter_version_control' => [
                'content_nodes' => DB::table('content_nodes')->where('project_id', $projectId)->get()->map(fn ($row) => (array) $row)->all(),
                'content_versions' => DB::table('content_versions')->whereIn('node_id', DB::table('content_nodes')->where('project_id', $projectId)->select('id'))->get()->map(fn ($row) => (array) $row)->all(),
                'chapter_states' => collect($chapterStatesData)->map(function (array $state, $chapterOrder) use ($projectId) {
                    return [
                        'id' => (string) \Illuminate\Support\Str::ulid(),
                        'project_id' => $projectId,
                        'chapter_order' => (int) $chapterOrder,
                        'current_node_id' => $state['node_id'],
                        'current_version_index' => $state['version_index'] ?? 0,
                        'updated_at' => now(),
                    ];
                })->values()->all(),
            ],
            'records' => [
                'entities' => $entitiesData,
                'relationships' => $relationshipsData,
                'entity_types' => [],
                'relationship_types' => [],
            ],
        ]);

        return true;
    }

    private function normalizeJsonForInsert(mixed $value): ?string
    {
        if ($value === null) {
            return null;
        }

        if (is_string($value)) {
            return $value;
        }

        return json_encode($value, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    }
}

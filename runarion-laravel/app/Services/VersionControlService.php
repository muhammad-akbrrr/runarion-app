<?php

namespace App\Services;

use App\Models\ChapterState;
use App\Models\ContentNode;
use App\Models\ContentVersion;
use App\Models\NovelGraphEdge;
use App\Models\NovelGraphVertex;
use App\Models\ProjectContent;
use App\Models\ProjectNodeEditor;
use App\Models\ProjectSnapshot;
use App\Models\Projects;
use Illuminate\Support\Arr;
use Illuminate\Support\Str;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

class VersionControlService
{
    /**
     * Initialize version control for a chapter
     */
    public function initializeChapter(string $projectId, int $chapterOrder, string $content, bool $isUserGenerated = true): string
    {
        return DB::transaction(function () use ($projectId, $chapterOrder, $content, $isUserGenerated) {
            // Create initial node
            $node = ContentNode::create([
                'project_id' => $projectId,
                'chapter_order' => $chapterOrder,
                'parent_node_id' => null,
                'parent_version_index' => null,
                'content' => $content,
                'generation_settings' => [],
                'is_user_generated' => $isUserGenerated,
            ]);

            // Create initial version
            ContentVersion::create([
                'node_id' => $node->id,
                'version_index' => 0,
                'content' => $content,
            ]);

            // Set chapter state
            ChapterState::updateOrCreate(
                [
                    'project_id' => $projectId,
                    'chapter_order' => $chapterOrder,
                ],
                [
                    'current_node_id' => $node->id,
                    'current_version_index' => 0,
                ]
            );

            $this->clearCache($projectId, $chapterOrder);

            return $node->id;
        });
    }

    /**
     * Create new node (for generation)
     */
    public function createNode(string $projectId, int $chapterOrder, string $content, array $settings = [], ?string $parentNodeId = null, ?int $parentVersionIndex = null): string
    {
        return DB::transaction(function () use ($projectId, $chapterOrder, $content, $settings, $parentNodeId, $parentVersionIndex) {
            $node = ContentNode::create([
                'project_id' => $projectId,
                'chapter_order' => $chapterOrder,
                'parent_node_id' => $parentNodeId,
                'parent_version_index' => $parentVersionIndex,
                'content' => $content,
                'generation_settings' => $settings,
                'is_user_generated' => false,
            ]);

            ContentVersion::create([
                'node_id' => $node->id,
                'version_index' => 0,
                'content' => $content,
            ]);

            ChapterState::updateOrCreate(
                [
                    'project_id' => $projectId,
                    'chapter_order' => $chapterOrder,
                ],
                [
                    'current_node_id' => $node->id,
                    'current_version_index' => 0,
                ]
            );

            $this->clearCache($projectId, $chapterOrder);

            return $node->id;
        });
    }

    /**
     * Add version to existing node (for regeneration)
     */
    public function addVersion(string $nodeId, string $content): int
    {
        return DB::transaction(function () use ($nodeId, $content) {
            $node = ContentNode::findOrFail($nodeId);

            $nextVersionIndex = $node->versions()->max('version_index') + 1;

            ContentVersion::create([
                'node_id' => $nodeId,
                'version_index' => $nextVersionIndex,
                'content' => $content,
            ]);

            ChapterState::where('project_id', $node->project_id)
                ->where('chapter_order', $node->chapter_order)
                ->update([
                    'current_node_id' => $nodeId,
                    'current_version_index' => $nextVersionIndex,
                ]);

            $this->clearCache($node->project_id, $node->chapter_order);

            return $nextVersionIndex;
        });
    }

    /**
     * Switch to parent node (undo)
     */
    public function undoToParent(string $projectId, int $chapterOrder): ?array
    {
        return DB::transaction(function () use ($projectId, $chapterOrder) {
            $state = ChapterState::where('project_id', $projectId)
                ->where('chapter_order', $chapterOrder)
                ->first();

            if (! $state) {
                return null;
            }

            $currentNode = ContentNode::find($state->current_node_id);
            if (! $currentNode || ! $currentNode->parent_node_id) {
                return null;
            }

            $parentNode = ContentNode::find($currentNode->parent_node_id);
            if (! $parentNode) {
                return null;
            }

            $parentVersionIndex = $currentNode->parent_version_index ?? 0;
            $parentVersion = $parentNode->versions()
                ->where('version_index', $parentVersionIndex)
                ->first();

            if (! $parentVersion) {
                return null;
            }

            $state->update([
                'current_node_id' => $parentNode->id,
                'current_version_index' => $parentVersionIndex,
            ]);

            $this->clearCache($projectId, $chapterOrder);

            return [
                'node_id' => $parentNode->id,
                'version_index' => $parentVersionIndex,
                'content' => $parentVersion->content,
            ];
        });
    }

    /**
     * Switch to child node (redo)
     */
    public function redoToChild(string $projectId, int $chapterOrder): ?array
    {
        return DB::transaction(function () use ($projectId, $chapterOrder) {
            $state = ChapterState::where('project_id', $projectId)
                ->where('chapter_order', $chapterOrder)
                ->first();

            if (! $state) {
                return null;
            }

            $childNode = ContentNode::where('parent_node_id', $state->current_node_id)
                ->where('parent_version_index', $state->current_version_index)
                ->orderBy('created_at', 'desc')
                ->first();

            if (! $childNode) {
                return null;
            }

            $latestVersion = $childNode->versions()
                ->orderBy('version_index', 'desc')
                ->first();

            if (! $latestVersion) {
                return null;
            }

            $state->update([
                'current_node_id' => $childNode->id,
                'current_version_index' => $latestVersion->version_index,
            ]);

            $this->clearCache($projectId, $chapterOrder);

            return [
                'node_id' => $childNode->id,
                'version_index' => $latestVersion->version_index,
                'content' => $latestVersion->content,
            ];
        });
    }

    /**
     * Switch version within current node
     */
    public function switchVersion(string $projectId, int $chapterOrder, int $versionIndex): ?array
    {
        return DB::transaction(function () use ($projectId, $chapterOrder, $versionIndex) {
            $state = ChapterState::where('project_id', $projectId)
                ->where('chapter_order', $chapterOrder)
                ->first();

            if (! $state) {
                return null;
            }

            $version = ContentVersion::where('node_id', $state->current_node_id)
                ->where('version_index', $versionIndex)
                ->first();

            if (! $version) {
                return null;
            }

            $state->update(['current_version_index' => $versionIndex]);

            $this->clearCache($projectId, $chapterOrder);

            return [
                'node_id' => $state->current_node_id,
                'version_index' => $versionIndex,
                'content' => $version->content,
            ];
        });
    }

    /**
     * Get current content for chapter
     */
    public function getCurrentContent(string $projectId, int $chapterOrder): ?string
    {
        $state = ChapterState::where('project_id', $projectId)
            ->where('chapter_order', $chapterOrder)
            ->first();

        if (! $state) {
            return null;
        }

        $version = ContentVersion::where('node_id', $state->current_node_id)
            ->where('version_index', $state->current_version_index)
            ->first();

        return $version?->content;
    }

    /**
     * Get current state info for chapter
     */
    public function getCurrentState(string $projectId, int $chapterOrder): ?array
    {
        $state = ChapterState::where('project_id', $projectId)
            ->where('chapter_order', $chapterOrder)
            ->first();

        if (! $state) {
            return null;
        }

        return [
            'node_id' => $state->current_node_id,
            'version_index' => $state->current_version_index,
        ];
    }

    /**
     * Update the content of a specific version.
     * This is critical for manual edits after generation - it ensures the current
     * ContentVersion stays in sync with ProjectContent JSON.
     *
     * @param  string  $nodeId  The node ID
     * @param  int  $versionIndex  The version index within the node
     * @param  string  $content  The new content
     * @return bool True if updated successfully, false otherwise
     */
    public function updateCurrentVersion(string $nodeId, int $versionIndex, string $content): bool
    {
        try {
            $version = ContentVersion::where('node_id', $nodeId)
                ->where('version_index', $versionIndex)
                ->first();

            if (! $version) {
                Log::warning('Version not found for update', [
                    'node_id' => $nodeId,
                    'version_index' => $versionIndex,
                ]);

                return false;
            }

            // Update the content
            $version->content = $content;
            $version->save();

            // Clear cache to ensure fresh data
            $node = ContentNode::find($nodeId);
            if ($node) {
                $this->clearCache($node->project_id, $node->chapter_order);
            }

            Log::info('Updated current version content', [
                'node_id' => $nodeId,
                'version_index' => $versionIndex,
                'content_length' => strlen($content),
            ]);

            return true;
        } catch (\Exception $e) {
            Log::error('Failed to update current version', [
                'node_id' => $nodeId,
                'version_index' => $versionIndex,
                'error' => $e->getMessage(),
            ]);

            return false;
        }
    }

    /**
     * Get navigation info for toolbar
     */
    public function getNavigationInfo(string $projectId, int $chapterOrder): array
    {
        $state = ChapterState::where('project_id', $projectId)
            ->where('chapter_order', $chapterOrder)
            ->first();

        if (! $state) {
            return [
                'canUndo' => false,
                'canRedo' => false,
                'canRegenerate' => false,
                'currentVersionIndex' => 0,
                'totalVersions' => 0,
                'versionDisplayText' => '0',
            ];
        }

        $currentNode = ContentNode::find($state->current_node_id);
        $canUndo = $currentNode && $currentNode->parent_node_id !== null;

        $canRedo = ContentNode::where('parent_node_id', $state->current_node_id)
            ->where('parent_version_index', $state->current_version_index)
            ->exists();

        $totalVersions = ContentVersion::where('node_id', $state->current_node_id)->count();
        $canRegenerate = $currentNode && $currentNode->parent_node_id !== null;

        return [
            'canUndo' => $canUndo,
            'canRedo' => $canRedo,
            'canRegenerate' => $canRegenerate,
            'currentVersionIndex' => $state->current_version_index,
            'totalVersions' => $totalVersions,
            'versionDisplayText' => (string) $state->current_version_index,
        ];
    }

    private function clearCache(string $projectId, int $chapterOrder): void
    {
        Cache::forget("content:{$projectId}:{$chapterOrder}");
        Cache::forget("navigation:{$projectId}:{$chapterOrder}");
    }

    /**
     * Create a project-wide snapshot.
     */
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

    /**
     * Restore a project-wide snapshot and create a pre-restore snapshot first.
     */
    public function loadSnapshot(string $projectId, string $snapshotId, ?int $createdBy = null): bool
    {
        return DB::transaction(function () use ($projectId, $snapshotId, $createdBy) {
            $snapshot = ProjectSnapshot::query()
                ->where('id', $snapshotId)
                ->where('project_id', $projectId)
                ->first();

            if (! $snapshot) {
                Log::warning('Snapshot not found for load', [
                    'snapshot_id' => $snapshotId,
                    'project_id' => $projectId,
                ]);

                return false;
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

            $snapshotData = $snapshot->snapshot_data ?? [];

            if (! isset($snapshotData['project']) && ! isset($snapshotData['project_content'])) {
                return $this->loadLegacySnapshot($projectId, $snapshotData);
            }

            $this->restoreProjectSnapshotData($projectId, $snapshotData);

            Log::info('Snapshot load completed', [
                'snapshot_id' => $snapshotId,
                'project_id' => $projectId,
                'snapshot_kind' => $snapshot->snapshot_kind,
            ]);

            return true;
        });
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

        NovelGraphEdge::query()->withTrashed()->where('project_id', $projectId)->forceDelete();
        NovelGraphVertex::query()->withTrashed()->where('project_id', $projectId)->forceDelete();
        DB::table('record_relationship_types')->where('project_id', $projectId)->delete();
        DB::table('record_entity_types')->where('project_id', $projectId)->delete();

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

        if (! empty($recordsData['entities'])) {
            DB::table('novel_graph_vertices')->insert(array_map(function (array $row) {
                if (array_key_exists('properties', $row)) {
                    $row['properties'] = $this->normalizeJsonForInsert($row['properties']);
                }
                return $row;
            }, $recordsData['entities']));
        }

        if (! empty($recordsData['relationships'])) {
            DB::table('novel_graph_edges')->insert(array_map(function (array $row) {
                if (array_key_exists('properties', $row)) {
                    $row['properties'] = $this->normalizeJsonForInsert($row['properties']);
                }
                return $row;
            }, $recordsData['relationships']));
        }

        $nodeEditor = ProjectNodeEditor::query()->firstOrNew(['project_id' => $projectId]);
        $nodeEditor->graph_state = $multipromptData['graph_state'] ?? null;
        $nodeEditor->templates = $multipromptData['templates'] ?? null;
        $nodeEditor->save();

        foreach ($projectContent->content ?? [] as $chapter) {
            if (isset($chapter['order'])) {
                $this->clearCache($projectId, (int) $chapter['order']);
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
                        'id' => (string) Str::ulid(),
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

    /**
     * Get version tree for a chapter (all nodes and versions)
     */
    public function getChapterVersionTree(string $projectId, int $chapterOrder): array
    {
        $nodes = ContentNode::where('project_id', $projectId)
            ->where('chapter_order', $chapterOrder)
            ->with([
                'versions' => function ($query) {
                    $query->orderBy('version_index');
                },
            ])
            ->get();

        $currentState = ChapterState::where('project_id', $projectId)
            ->where('chapter_order', $chapterOrder)
            ->first();

        $currentNodeId = $currentState?->current_node_id;
        $currentVersionIndex = $currentState?->current_version_index ?? 0;

        $tree = [];
        foreach ($nodes as $node) {
            $versions = [];
            foreach ($node->versions as $version) {
                $versions[] = [
                    'version_index' => $version->version_index,
                    'content_preview' => substr($version->content, 0, 200).(strlen($version->content) > 200 ? '...' : ''),
                    'content_length' => strlen($version->content),
                    'created_at' => $version->created_at?->toIso8601String(),
                    'is_current' => $node->id === $currentNodeId && $version->version_index === $currentVersionIndex,
                ];
            }

            $tree[] = [
                'node_id' => $node->id,
                'parent_node_id' => $node->parent_node_id,
                'parent_version_index' => $node->parent_version_index,
                'is_user_generated' => $node->is_user_generated,
                'generation_settings' => $node->generation_settings,
                'created_at' => $node->created_at?->toIso8601String(),
                'is_current' => $node->id === $currentNodeId,
                'versions' => $versions,
            ];
        }

        return $tree;
    }

    /**
     * Get all chapters with their version info
     */
    public function getAllChaptersVersionInfo(string $projectId): array
    {
        $projectContent = ProjectContent::where('project_id', $projectId)->first();
        if (! $projectContent || ! $projectContent->content) {
            return [];
        }

        $chapters = [];
        foreach ($projectContent->content as $chapter) {
            $chapterOrder = $chapter['order'] ?? null;
            if ($chapterOrder === null) {
                continue;
            }

            $state = ChapterState::where('project_id', $projectId)
                ->where('chapter_order', $chapterOrder)
                ->first();

            $navigationInfo = $this->getNavigationInfo($projectId, $chapterOrder);
            $versionTree = $this->getChapterVersionTree($projectId, $chapterOrder);

            $chapters[] = [
                'order' => $chapterOrder,
                'chapter_name' => $chapter['chapter_name'] ?? "Chapter {$chapterOrder}",
                'current_node_id' => $state?->current_node_id,
                'current_version_index' => $state?->current_version_index ?? 0,
                'navigation_info' => $navigationInfo,
                'version_tree' => $versionTree,
            ];
        }

        // Sort by order
        usort($chapters, function ($a, $b) {
            return $a['order'] <=> $b['order'];
        });

        return $chapters;
    }

    /**
     * Delete all version control data for a specific chapter order.
     * This is called when a chapter is deleted to ensure no orphaned data remains.
     *
     * @param  string  $projectId  The project ID
     * @param  int  $chapterOrder  The chapter order to delete
     * @return bool True if deletion was successful
     */
    public function deleteChapterVersionControl(string $projectId, int $chapterOrder): bool
    {
        return DB::transaction(function () use ($projectId, $chapterOrder) {
            try {
                // Get all nodes for this chapter order
                $nodes = ContentNode::where('project_id', $projectId)
                    ->where('chapter_order', $chapterOrder)
                    ->get();

                $nodeIds = $nodes->pluck('id')->toArray();

                // Delete all versions associated with these nodes
                if (! empty($nodeIds)) {
                    ContentVersion::whereIn('node_id', $nodeIds)->delete();
                }

                // Delete all nodes for this chapter
                ContentNode::where('project_id', $projectId)
                    ->where('chapter_order', $chapterOrder)
                    ->delete();

                // Delete chapter state
                ChapterState::where('project_id', $projectId)
                    ->where('chapter_order', $chapterOrder)
                    ->delete();

                // Clear cache
                $this->clearCache($projectId, $chapterOrder);

                Log::info('Deleted version control data for chapter', [
                    'project_id' => $projectId,
                    'chapter_order' => $chapterOrder,
                    'nodes_deleted' => count($nodeIds),
                ]);

                return true;
            } catch (\Exception $e) {
                Log::error('Failed to delete version control data for chapter', [
                    'project_id' => $projectId,
                    'chapter_order' => $chapterOrder,
                    'error' => $e->getMessage(),
                ]);
                throw $e;
            }
        });
    }

    /**
     * Reorder version control data when chapters are reordered.
     * This maps old chapter orders to new chapter orders.
     *
     * @param  string  $projectId  The project ID
     * @param  array  $orderMapping  Array mapping old order => new order (e.g., [2 => 1, 3 => 2])
     * @return bool True if reordering was successful
     */
    public function reorderChapters(string $projectId, array $orderMapping): bool
    {
        return DB::transaction(function () use ($projectId, $orderMapping) {
            try {
                foreach ($orderMapping as $oldOrder => $newOrder) {
                    if ($oldOrder == $newOrder) {
                        continue; // No change needed
                    }

                    // Update ContentNode chapter_order
                    ContentNode::where('project_id', $projectId)
                        ->where('chapter_order', $oldOrder)
                        ->update(['chapter_order' => $newOrder]);

                    // Update ChapterState chapter_order
                    ChapterState::where('project_id', $projectId)
                        ->where('chapter_order', $oldOrder)
                        ->update(['chapter_order' => $newOrder]);

                    // Clear cache for both old and new orders
                    $this->clearCache($projectId, $oldOrder);
                    $this->clearCache($projectId, $newOrder);
                }

                Log::info('Reordered version control data for chapters', [
                    'project_id' => $projectId,
                    'mapping' => $orderMapping,
                ]);

                return true;
            } catch (\Exception $e) {
                Log::error('Failed to reorder version control data for chapters', [
                    'project_id' => $projectId,
                    'mapping' => $orderMapping,
                    'error' => $e->getMessage(),
                ]);
                throw $e;
            }
        });
    }
}

<?php

namespace App\Services;

use App\Models\ContentNode;
use App\Models\ContentVersion;
use App\Models\ChapterState;
use App\Models\ProjectContent;
use App\Models\ProjectSnapshot;
use App\Models\NovelGraphVertex;
use App\Models\NovelGraphEdge;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Cache;
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

            if (!$state)
                return null;

            $currentNode = ContentNode::find($state->current_node_id);
            if (!$currentNode || !$currentNode->parent_node_id)
                return null;

            $parentNode = ContentNode::find($currentNode->parent_node_id);
            if (!$parentNode)
                return null;

            $parentVersionIndex = $currentNode->parent_version_index ?? 0;
            $parentVersion = $parentNode->versions()
                ->where('version_index', $parentVersionIndex)
                ->first();

            if (!$parentVersion)
                return null;

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

            if (!$state)
                return null;

            $childNode = ContentNode::where('parent_node_id', $state->current_node_id)
                ->where('parent_version_index', $state->current_version_index)
                ->orderBy('created_at', 'desc')
                ->first();

            if (!$childNode)
                return null;

            $latestVersion = $childNode->versions()
                ->orderBy('version_index', 'desc')
                ->first();

            if (!$latestVersion)
                return null;

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

            if (!$state)
                return null;

            $version = ContentVersion::where('node_id', $state->current_node_id)
                ->where('version_index', $versionIndex)
                ->first();

            if (!$version)
                return null;

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

        if (!$state)
            return null;

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

        if (!$state)
            return null;

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
     * @param string $nodeId The node ID
     * @param int $versionIndex The version index within the node
     * @param string $content The new content
     * @return bool True if updated successfully, false otherwise
     */
    public function updateCurrentVersion(string $nodeId, int $versionIndex, string $content): bool
    {
        try {
            $version = ContentVersion::where('node_id', $nodeId)
                ->where('version_index', $versionIndex)
                ->first();

            if (!$version) {
                Log::warning('Version not found for update', [
                    'node_id' => $nodeId,
                    'version_index' => $versionIndex
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
                'content_length' => strlen($content)
            ]);

            return true;
        } catch (\Exception $e) {
            Log::error('Failed to update current version', [
                'node_id' => $nodeId,
                'version_index' => $versionIndex,
                'error' => $e->getMessage()
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

        if (!$state) {
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
     * Create a project snapshot of current chapter states, chapters, entities, and relationships
     */
    public function createSnapshot(string $projectId, ?string $name = null, ?string $description = null, ?int $createdBy = null): string
    {
        return DB::transaction(function () use ($projectId, $name, $description, $createdBy) {
            // Get all chapter states for this project
            $chapterStates = ChapterState::where('project_id', $projectId)->get();

            $chapterStatesData = [];
            foreach ($chapterStates as $state) {
                $chapterStatesData[$state->chapter_order] = [
                    'node_id' => $state->current_node_id,
                    'version_index' => $state->current_version_index,
                ];
            }

            // Get chapters from ProjectContent
            $projectContent = ProjectContent::where('project_id', $projectId)->first();
            $chaptersData = $projectContent ? ($projectContent->content ?? []) : [];

            // Get all entities for this project
            $entities = NovelGraphVertex::where('project_id', $projectId)
                ->whereNull('deleted_at')
                ->get()
                ->map(function ($entity) {
                    return [
                        'id' => $entity->id,
                        'entity_type' => $entity->entity_type,
                        'entity_name' => $entity->entity_name,
                        'vertex_id' => $entity->vertex_id,
                        'vertex_label' => $entity->vertex_label,
                        'properties' => $entity->properties,
                    ];
                })
                ->toArray();

            // Get all relationships for this project
            $relationships = NovelGraphEdge::where('project_id', $projectId)
                ->whereNull('deleted_at')
                ->get()
                ->map(function ($edge) {
                    return [
                        'id' => $edge->id,
                        'source_vertex_id' => $edge->source_vertex_id,
                        'target_vertex_id' => $edge->target_vertex_id,
                        'edge_id' => $edge->edge_id,
                        'edge_label' => $edge->edge_label,
                        'properties' => $edge->properties,
                        'scene_id' => $edge->scene_id,
                    ];
                })
                ->toArray();

            // Build complete snapshot data
            $snapshotData = [
                'chapter_states' => $chapterStatesData,
                'chapters' => $chaptersData,
                'entities' => $entities,
                'relationships' => $relationships,
            ];

            $snapshot = ProjectSnapshot::create([
                'project_id' => $projectId,
                'name' => $name,
                'description' => $description,
                'snapshot_data' => $snapshotData,
                'created_by' => $createdBy ?? auth()->id(),
            ]);

            Log::info('Snapshot created', [
                'snapshot_id' => $snapshot->id,
                'project_id' => $projectId,
                'chapters_count' => count($chaptersData),
                'entities_count' => count($entities),
                'relationships_count' => count($relationships),
            ]);

            return $snapshot->id;
        });
    }

    /**
     * Load a snapshot (restore chapter states, chapters, entities, and relationships)
     */
    public function loadSnapshot(string $projectId, string $snapshotId): bool
    {
        return DB::transaction(function () use ($projectId, $snapshotId) {
            $snapshot = ProjectSnapshot::where('id', $snapshotId)
                ->where('project_id', $projectId)
                ->first();

            if (!$snapshot) {
                Log::warning('Snapshot not found for load', [
                    'snapshot_id' => $snapshotId,
                    'project_id' => $projectId,
                ]);
                return false;
            }

            $snapshotData = $snapshot->snapshot_data ?? [];

            // Handle legacy snapshots (old format with chapter_states at root level)
            if (!isset($snapshotData['chapter_states']) && !isset($snapshotData['chapters'])) {
                // Legacy format: snapshot_data is just chapter states
                $chapterStatesData = $snapshotData;
                $chaptersData = [];
                $entitiesData = [];
                $relationshipsData = [];
            } else {
                // New format: structured data
                $chapterStatesData = $snapshotData['chapter_states'] ?? [];
                $chaptersData = $snapshotData['chapters'] ?? [];
                $entitiesData = $snapshotData['entities'] ?? [];
                $relationshipsData = $snapshotData['relationships'] ?? [];
            }

            Log::info('Loading snapshot', [
                'snapshot_id' => $snapshotId,
                'project_id' => $projectId,
                'chapters_count' => count($chaptersData),
                'entities_count' => count($entitiesData),
                'relationships_count' => count($relationshipsData),
            ]);

            // Clean up chapter states for chapters that are not in the snapshot
            $snapshotChapterOrders = array_keys($chapterStatesData);
            if (!empty($snapshotChapterOrders)) {
                ChapterState::where('project_id', $projectId)
                    ->whereNotIn('chapter_order', $snapshotChapterOrders)
                    ->delete();
            } else {
                // If snapshot has no chapter states, delete all chapter states
                ChapterState::where('project_id', $projectId)->delete();
            }

            // Restore chapter states
            $restoredChapterStatesCount = 0;
            foreach ($chapterStatesData as $chapterOrder => $stateData) {
                $nodeId = $stateData['node_id'] ?? null;
                $versionIndex = $stateData['version_index'] ?? 0;

                if ($nodeId) {
                    // Verify node exists and belongs to this project/chapter
                    $node = ContentNode::where('id', $nodeId)
                        ->where('project_id', $projectId)
                        ->where('chapter_order', $chapterOrder)
                        ->first();

                    if ($node) {
                        // Verify version exists
                        $version = ContentVersion::where('node_id', $nodeId)
                            ->where('version_index', $versionIndex)
                            ->first();

                        if ($version) {
                            ChapterState::updateOrCreate(
                                [
                                    'project_id' => $projectId,
                                    'chapter_order' => $chapterOrder,
                                ],
                                [
                                    'current_node_id' => $nodeId,
                                    'current_version_index' => $versionIndex,
                                ]
                            );

                            $this->clearCache($projectId, $chapterOrder);
                            $restoredChapterStatesCount++;

                            Log::info('Restored chapter state', [
                                'chapter_order' => $chapterOrder,
                                'node_id' => $nodeId,
                                'version_index' => $versionIndex,
                            ]);
                        } else {
                            Log::warning('Version not found when loading snapshot', [
                                'chapter_order' => $chapterOrder,
                                'node_id' => $nodeId,
                                'version_index' => $versionIndex,
                            ]);
                        }
                    } else {
                        Log::warning('Node not found when loading snapshot', [
                            'chapter_order' => $chapterOrder,
                            'node_id' => $nodeId,
                        ]);
                    }
                }
            }

            // Restore chapters
            $projectContent = ProjectContent::where('project_id', $projectId)->first();
            if ($projectContent) {
                // Get snapshot chapter orders
                $snapshotChapterOrders = array_column($chaptersData, 'order');

                // Delete version control data for chapters that are not in the snapshot
                $currentChapters = $projectContent->content ?? [];
                foreach ($currentChapters as $chapter) {
                    $chapterOrder = $chapter['order'] ?? null;
                    if ($chapterOrder !== null && !in_array($chapterOrder, $snapshotChapterOrders)) {
                        // Chapter exists in current state but not in snapshot - delete its version control
                        try {
                            $this->deleteChapterVersionControl($projectId, $chapterOrder);
                        } catch (\Exception $e) {
                            Log::warning('Error deleting version control for removed chapter', [
                                'project_id' => $projectId,
                                'chapter_order' => $chapterOrder,
                                'error' => $e->getMessage(),
                            ]);
                        }
                    }
                }

                // Restore chapters from snapshot
                $projectContent->content = $chaptersData;
                $projectContent->save();
                Log::info('Restored chapters', [
                    'chapters_count' => count($chaptersData),
                ]);
            } else {
                if (!empty($chaptersData)) {
                    ProjectContent::create([
                        'project_id' => $projectId,
                        'content' => $chaptersData,
                    ]);
                    Log::info('Created ProjectContent and restored chapters', [
                        'chapters_count' => count($chaptersData),
                    ]);
                }
            }

            // Restore entities
            // Get snapshot vertex_ids to know which entities should exist
            $snapshotVertexIds = [];
            if (!empty($entitiesData) && is_array($entitiesData)) {
                $snapshotVertexIds = array_filter(array_column($entitiesData, 'vertex_id'), function ($id) {
                    return $id !== null;
                });
            }

            // Soft delete entities that are not in the snapshot (only if we have snapshot data)
            if (!empty($snapshotVertexIds)) {
                NovelGraphVertex::where('project_id', $projectId)
                    ->whereNull('deleted_at')
                    ->whereNotIn('vertex_id', $snapshotVertexIds)
                    ->delete();
            } elseif (empty($entitiesData)) {
                // If snapshot has no entities, delete all current entities
                NovelGraphVertex::where('project_id', $projectId)
                    ->whereNull('deleted_at')
                    ->delete();
            }

            // Restore entities from snapshot
            $restoredEntitiesCount = 0;
            foreach ($entitiesData as $entityData) {
                // Validate required fields
                if (empty($entityData['vertex_id']) || empty($entityData['entity_name']) || empty($entityData['entity_type'])) {
                    Log::warning('Skipping invalid entity data in snapshot', [
                        'entity_data' => $entityData,
                    ]);
                    continue;
                }

                // Check if entity already exists (by vertex_id)
                $existingEntity = NovelGraphVertex::where('project_id', $projectId)
                    ->where('vertex_id', $entityData['vertex_id'])
                    ->withTrashed()
                    ->first();

                if ($existingEntity) {
                    // Restore if soft-deleted, or update if exists
                    if ($existingEntity->trashed()) {
                        $existingEntity->restore();
                    }
                    // Update properties in case they changed
                    $existingEntity->update([
                        'entity_type' => $entityData['entity_type'],
                        'entity_name' => $entityData['entity_name'],
                        'vertex_label' => $entityData['vertex_label'],
                        'properties' => $entityData['properties'] ?? null,
                    ]);
                } else {
                    // Create new entity record
                    NovelGraphVertex::create([
                        'project_id' => $projectId,
                        'entity_type' => $entityData['entity_type'],
                        'entity_name' => $entityData['entity_name'],
                        'vertex_id' => $entityData['vertex_id'],
                        'vertex_label' => $entityData['vertex_label'],
                        'properties' => $entityData['properties'] ?? null,
                    ]);
                }
                $restoredEntitiesCount++;
            }
            Log::info('Restored entities', [
                'entities_count' => $restoredEntitiesCount,
            ]);

            // Restore relationships
            // Get snapshot edge_ids to know which relationships should exist
            $snapshotEdgeIds = [];
            if (!empty($relationshipsData) && is_array($relationshipsData)) {
                $snapshotEdgeIds = array_filter(array_column($relationshipsData, 'edge_id'), function ($id) {
                    return $id !== null;
                });
            }

            // Soft delete relationships that are not in the snapshot (only if we have snapshot data)
            if (!empty($snapshotEdgeIds)) {
                NovelGraphEdge::where('project_id', $projectId)
                    ->whereNull('deleted_at')
                    ->whereNotIn('edge_id', $snapshotEdgeIds)
                    ->delete();
            } elseif (empty($relationshipsData)) {
                // If snapshot has no relationships, delete all current relationships
                NovelGraphEdge::where('project_id', $projectId)
                    ->whereNull('deleted_at')
                    ->delete();
            }

            // Restore relationships from snapshot
            $restoredRelationshipsCount = 0;
            foreach ($relationshipsData as $relationshipData) {
                // Validate required fields
                if (empty($relationshipData['edge_id']) || empty($relationshipData['source_vertex_id']) || empty($relationshipData['target_vertex_id']) || empty($relationshipData['edge_label'])) {
                    Log::warning('Skipping invalid relationship data in snapshot', [
                        'relationship_data' => $relationshipData,
                    ]);
                    continue;
                }

                // Check if relationship already exists (by edge_id)
                $existingRelationship = NovelGraphEdge::where('project_id', $projectId)
                    ->where('edge_id', $relationshipData['edge_id'])
                    ->withTrashed()
                    ->first();

                if ($existingRelationship) {
                    // Restore if soft-deleted, or update if exists
                    if ($existingRelationship->trashed()) {
                        $existingRelationship->restore();
                    }
                    // Update properties in case they changed
                    $existingRelationship->update([
                        'source_vertex_id' => $relationshipData['source_vertex_id'],
                        'target_vertex_id' => $relationshipData['target_vertex_id'],
                        'edge_label' => $relationshipData['edge_label'],
                        'properties' => $relationshipData['properties'] ?? null,
                        'scene_id' => $relationshipData['scene_id'] ?? null,
                    ]);
                } else {
                    // Create new relationship record
                    NovelGraphEdge::create([
                        'project_id' => $projectId,
                        'source_vertex_id' => $relationshipData['source_vertex_id'],
                        'target_vertex_id' => $relationshipData['target_vertex_id'],
                        'edge_id' => $relationshipData['edge_id'],
                        'edge_label' => $relationshipData['edge_label'],
                        'properties' => $relationshipData['properties'] ?? null,
                        'scene_id' => $relationshipData['scene_id'] ?? null,
                    ]);
                }
                $restoredRelationshipsCount++;
            }
            Log::info('Restored relationships', [
                'relationships_count' => $restoredRelationshipsCount,
            ]);

            Log::info('Snapshot load completed', [
                'snapshot_id' => $snapshotId,
                'chapter_states_restored' => $restoredChapterStatesCount,
                'chapters_restored' => count($chaptersData),
                'entities_restored' => $restoredEntitiesCount,
                'relationships_restored' => $restoredRelationshipsCount,
            ]);

            return true;
        });
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
                }
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
                    'content_preview' => substr($version->content, 0, 200) . (strlen($version->content) > 200 ? '...' : ''),
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
        if (!$projectContent || !$projectContent->content) {
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
     * @param string $projectId The project ID
     * @param int $chapterOrder The chapter order to delete
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
                if (!empty($nodeIds)) {
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
     * @param string $projectId The project ID
     * @param array $orderMapping Array mapping old order => new order (e.g., [2 => 1, 3 => 2])
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

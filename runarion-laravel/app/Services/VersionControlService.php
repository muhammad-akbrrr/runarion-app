<?php

namespace App\Services;

use App\Models\ContentNode;
use App\Models\ContentVersion;
use App\Models\ChapterState;
use App\Models\ProjectContent;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Log;

class VersionControlService
{
    /**
     * Initialize version control for a chapter
     */
    public function initializeChapter(string $projectId, int $chapterOrder, string $content): string
    {
        return DB::transaction(function () use ($projectId, $chapterOrder, $content) {
            // Create initial node
            $node = ContentNode::create([
                'project_id' => $projectId,
                'chapter_order' => $chapterOrder,
                'parent_node_id' => null,
                'parent_version_index' => null,
                'content' => $content,
                'generation_settings' => [],
                'is_user_generated' => true,
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

            if (!$state) return null;

            $currentNode = ContentNode::find($state->current_node_id);
            if (!$currentNode || !$currentNode->parent_node_id) return null;

            $parentNode = ContentNode::find($currentNode->parent_node_id);
            if (!$parentNode) return null;

            $parentVersionIndex = $currentNode->parent_version_index ?? 0;
            $parentVersion = $parentNode->versions()
                ->where('version_index', $parentVersionIndex)
                ->first();

            if (!$parentVersion) return null;

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

            if (!$state) return null;

            $childNode = ContentNode::where('parent_node_id', $state->current_node_id)
                ->where('parent_version_index', $state->current_version_index)
                ->orderBy('created_at', 'desc')
                ->first();

            if (!$childNode) return null;

            $latestVersion = $childNode->versions()
                ->orderBy('version_index', 'desc')
                ->first();

            if (!$latestVersion) return null;

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

            if (!$state) return null;

            $version = ContentVersion::where('node_id', $state->current_node_id)
                ->where('version_index', $versionIndex)
                ->first();

            if (!$version) return null;

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

        if (!$state) return null;

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

        if (!$state) return null;

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
            'versionDisplayText' => (string)$state->current_version_index,
        ];
    }

    private function clearCache(string $projectId, int $chapterOrder): void
    {
        Cache::forget("content:{$projectId}:{$chapterOrder}");
        Cache::forget("navigation:{$projectId}:{$chapterOrder}");
    }
}

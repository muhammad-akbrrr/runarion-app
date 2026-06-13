<?php

namespace App\Services;

use App\Models\NovelGraphEdge;
use App\Models\NovelGraphVertex;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Throwable;

class ProjectGraphRestoreService
{
    public function __construct(
        private readonly GraphDatabaseService $graphDatabaseService,
    ) {}

    public function restore(string $projectId, array $entities, array $relationships): void
    {
        $this->clearMirrorTables($projectId);

        if (! $this->graphDatabaseService->isAgeAvailable()) {
            $this->restoreMirrorOnly($entities, $relationships);

            return;
        }

        $this->clearCanonicalGraph($projectId, $entities, $relationships);
        $this->rebuildCanonicalGraph($projectId, $entities, $relationships);
    }

    private function clearMirrorTables(string $projectId): void
    {
        NovelGraphEdge::query()->withTrashed()->where('project_id', $projectId)->forceDelete();
        NovelGraphVertex::query()->withTrashed()->where('project_id', $projectId)->forceDelete();
        DB::table('record_relationship_types')->where('project_id', $projectId)->delete();
        DB::table('record_entity_types')->where('project_id', $projectId)->delete();
    }

    private function restoreMirrorOnly(array $entities, array $relationships): void
    {
        if ($entities !== []) {
            DB::table('novel_graph_vertices')->insert(array_map(function (array $row) {
                if (array_key_exists('properties', $row)) {
                    $row['properties'] = $this->normalizeJsonForInsert($row['properties']);
                }

                return $row;
            }, $entities));
        }

        if ($relationships !== []) {
            DB::table('novel_graph_edges')->insert(array_map(function (array $row) {
                if (array_key_exists('properties', $row)) {
                    $row['properties'] = $this->normalizeJsonForInsert($row['properties']);
                }

                return $row;
            }, $relationships));
        }
    }

    private function clearCanonicalGraph(string $projectId, array $entities, array $relationships): void
    {
        $draftIds = collect(array_merge(
            array_column($entities, 'draft_id'),
            array_column($relationships, 'draft_id'),
        ))
            ->filter()
            ->unique()
            ->values();

        try {
            $this->graphDatabaseService->executeCypher(
                "MATCH (n {project_id: '{$projectId}'}) DETACH DELETE n RETURN count(n) as deleted_count",
                ['deleted_count']
            );

            foreach ($draftIds as $draftId) {
                DB::select('SELECT delete_draft_graph_data(?) as deleted_count', [(string) $draftId]);
            }
        } catch (Throwable $e) {
            Log::warning('Canonical graph cleanup failed before project snapshot restore', [
                'project_id' => $projectId,
                'error' => $e->getMessage(),
            ]);
        }
    }

    private function rebuildCanonicalGraph(string $projectId, array $entities, array $relationships): void
    {
        $vertexMap = [];

        foreach ($entities as $entity) {
            $label = preg_replace('/[^A-Za-z0-9_]/', '', (string) ($entity['vertex_label'] ?? ucfirst((string) ($entity['entity_type'] ?? 'Entity'))));
            $properties = array_merge(
                is_array($entity['properties'] ?? null) ? $entity['properties'] : [],
                [
                    'project_id' => $projectId,
                    'draft_id' => $entity['draft_id'] ?? null,
                    'entity_type' => $entity['entity_type'] ?? null,
                    'entity_name' => $entity['entity_name'] ?? null,
                ],
            );

            $result = $this->graphDatabaseService->executeCypher(
                "CREATE (n:{$label} ".json_encode($properties, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES).") RETURN id(n) as vertex_id",
                ['vertex_id']
            );

            $newVertexId = (int) ($result[0]['vertex_id'] ?? 0);
            $oldVertexId = (int) ($entity['vertex_id'] ?? 0);
            $vertexMap[$oldVertexId] = $newVertexId;

            DB::table('novel_graph_vertices')->insert([
                'id' => $entity['id'] ?? null,
                'draft_id' => $entity['draft_id'] ?? null,
                'project_id' => $projectId,
                'entity_type' => $entity['entity_type'] ?? null,
                'entity_name' => $entity['entity_name'] ?? null,
                'vertex_id' => $newVertexId,
                'vertex_label' => $entity['vertex_label'] ?? $label,
                'properties' => $this->normalizeJsonForInsert($entity['properties'] ?? null),
                'created_at' => $entity['created_at'] ?? now(),
                'updated_at' => $entity['updated_at'] ?? now(),
                'deleted_at' => $entity['deleted_at'] ?? null,
            ]);
        }

        foreach ($relationships as $relationship) {
            $sourceVertexId = $vertexMap[(int) ($relationship['source_vertex_id'] ?? 0)] ?? null;
            $targetVertexId = $vertexMap[(int) ($relationship['target_vertex_id'] ?? 0)] ?? null;
            if (! $sourceVertexId || ! $targetVertexId) {
                continue;
            }

            $label = preg_replace('/[^A-Za-z0-9_]/', '', (string) ($relationship['edge_label'] ?? 'RELATES_TO'));
            $properties = array_merge(
                is_array($relationship['properties'] ?? null) ? $relationship['properties'] : [],
                [
                    'project_id' => $projectId,
                    'draft_id' => $relationship['draft_id'] ?? null,
                    'scene_id' => $relationship['scene_id'] ?? null,
                ],
            );

            $result = $this->graphDatabaseService->executeCypher(
                "MATCH (a), (b) WHERE id(a) = {$sourceVertexId} AND id(b) = {$targetVertexId} CREATE (a)-[r:{$label} ".json_encode($properties, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)."]->(b) RETURN id(r) as edge_id",
                ['edge_id']
            );

            $newEdgeId = (int) ($result[0]['edge_id'] ?? 0);

            DB::table('novel_graph_edges')->insert([
                'id' => $relationship['id'] ?? null,
                'draft_id' => $relationship['draft_id'] ?? null,
                'project_id' => $projectId,
                'scene_id' => $relationship['scene_id'] ?? null,
                'source_vertex_id' => $sourceVertexId,
                'target_vertex_id' => $targetVertexId,
                'edge_id' => $newEdgeId,
                'edge_label' => $relationship['edge_label'] ?? $label,
                'properties' => $this->normalizeJsonForInsert($relationship['properties'] ?? null),
                'created_at' => $relationship['created_at'] ?? now(),
                'updated_at' => $relationship['updated_at'] ?? now(),
                'deleted_at' => $relationship['deleted_at'] ?? null,
            ]);
        }
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

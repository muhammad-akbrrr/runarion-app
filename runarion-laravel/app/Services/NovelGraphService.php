<?php

namespace App\Services;

use App\Models\Draft;
use App\Models\Scene;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Exception;

class NovelGraphService
{
    private string $graphName = 'novel_pipeline_graph';
    private ?bool $ageAvailable = null;

    /**
     * Check if Apache AGE is available and functional
     */
    public function isAgeAvailable(): bool
    {
        if ($this->ageAvailable !== null) {
            return $this->ageAvailable;
        }

        try {
            // Check if AGE extension exists
            $result = DB::select("
                SELECT 1 FROM pg_extension WHERE extname = 'age'
            ");

            if (empty($result)) {
                $this->ageAvailable = false;
                return false;
            }

            // Check if graph exists
            $result = DB::select("
                SELECT 1 FROM ag_catalog.ag_graph WHERE name = ?
            ", [$this->graphName]);

            if (empty($result)) {
                $this->ageAvailable = false;
                return false;
            }

            // Test basic AGE functionality
            DB::select("
                SELECT ag_catalog.cypher(?, 'RETURN 1', null)
            ", [$this->graphName]);

            $this->ageAvailable = true;
            return true;

        } catch (Exception $e) {
            Log::warning("AGE availability check failed: " . $e->getMessage());
            $this->ageAvailable = false;
            return false;
        }
    }

    /**
     * Execute AGE operation with availability check and optional locking
     */
    private function executeAgeOperation(callable $operation, $fallbackResult = null, ?string $lockKey = null)
    {
        if (!$this->isAgeAvailable()) {
            Log::warning("AGE operation attempted but AGE is not available - returning fallback");
            return $fallbackResult;
        }

        if ($lockKey) {
            return $this->withLock($lockKey, $operation, $fallbackResult);
        }

        try {
            return $operation();
        } catch (Exception $e) {
            Log::error("AGE operation failed: " . $e->getMessage());
            // Mark AGE as unavailable for this request
            $this->ageAvailable = false;
            return $fallbackResult;
        }
    }

    /**
     * Execute operation with advisory lock protection
     */
    private function withLock(string $lockKey, callable $operation, $fallbackResult = null)
    {
        $lockId = crc32($lockKey);
        
        try {
            // Attempt to acquire advisory lock (non-blocking)
            $result = DB::select("SELECT pg_try_advisory_lock(?) as acquired", [$lockId]);
            
            if (!$result[0]->acquired) {
                Log::warning("Could not acquire lock for operation: {$lockKey}");
                return $fallbackResult;
            }

            try {
                $operationResult = $operation();
                
                // Release lock
                DB::select("SELECT pg_advisory_unlock(?)", [$lockId]);
                
                return $operationResult;
                
            } catch (Exception $e) {
                // Ensure lock is released even on error
                DB::select("SELECT pg_advisory_unlock(?)", [$lockId]);
                throw $e;
            }
            
        } catch (Exception $e) {
            Log::error("Lock operation failed: " . $e->getMessage());
            $this->ageAvailable = false;
            return $fallbackResult;
        }
    }

    /**
     * Initialize graph for a draft
     */
    public function initializeDraftGraph(Draft $draft): bool
    {
        if (!$this->isAgeAvailable()) {
            Log::warning("Cannot initialize graph for draft {$draft->id}: AGE not available");
            return false;
        }

        return $this->executeAgeOperation(function() use ($draft) {
            DB::beginTransaction();

            // Mark draft as graph initialized
            $draft->update([
                'graph_initialized' => true,
                'graph_last_updated' => now()
            ]);

            // Create draft vertex in graph
            $draftVertexId = $this->createDraftVertex($draft);

            Log::info("Initialized graph for draft {$draft->id}", [
                'draft_vertex_id' => $draftVertexId
            ]);

            DB::commit();
            return true;
        }, false, "draft_init_{$draft->id}");
    }

    /**
     * Create or update character vertex in graph
     */
    public function createCharacterVertex(Draft $draft, string $name, array $properties = []): ?int
    {
        return $this->executeAgeOperation(function() use ($draft, $name, $properties) {
            $result = DB::select("
                SELECT create_novel_character_vertex(?, ?, ?) as vertex_id
            ", [$draft->id, $name, json_encode($properties)]);

            return $result[0]->vertex_id ?? null;
        }, null, "character_create_{$draft->id}_{$name}");
    }

    /**
     * Create location vertex in graph
     */
    public function createLocationVertex(Draft $draft, string $name, array $properties = []): ?int
    {
        try {
            $cypherQuery = "
                CREATE (l:Location {draft_id: \$draft_id, name: \$name, properties: \$props}) 
                RETURN id(l)
            ";

            $result = DB::select("
                SELECT (ag_catalog.cypher(?, ?, ?) -> 0 -> 0)::bigint as vertex_id
            ", [
                $this->graphName,
                $cypherQuery,
                json_encode([
                    'draft_id' => $draft->id,
                    'name' => $name,
                    'props' => $properties
                ])
            ]);

            $vertexId = $result[0]->vertex_id ?? null;

            if ($vertexId) {
                // Insert metadata record
                DB::table('novel_graph_vertices')->insert([
                    'draft_id' => $draft->id,
                    'entity_type' => 'location',
                    'entity_name' => $name,
                    'vertex_id' => $vertexId,
                    'vertex_label' => 'Location',
                    'properties' => json_encode($properties),
                    'created_at' => now(),
                    'updated_at' => now()
                ]);
            }

            return $vertexId;

        } catch (Exception $e) {
            Log::error("Failed to create location vertex: " . $e->getMessage());
            return null;
        }
    }

    /**
     * Create relationship between two vertices
     */
    public function createRelationship(
        Draft $draft,
        int $sourceVertexId,
        int $targetVertexId,
        string $relationshipType,
        ?int $sceneId = null,
        array $properties = []
    ): ?int {
        try {
            $result = DB::select("
                SELECT create_novel_relationship(?, ?, ?, ?, ?, ?) as edge_id
            ", [
                $draft->id,
                $sourceVertexId,
                $targetVertexId,
                $relationshipType,
                $sceneId,
                json_encode($properties)
            ]);

            return $result[0]->edge_id ?? null;

        } catch (Exception $e) {
            Log::error("Failed to create relationship: " . $e->getMessage());
            return null;
        }
    }

    /**
     * Get all character relationships for a draft
     */
    public function getCharacterRelationships(Draft $draft): array
    {
        return $this->executeAgeOperation(function() use ($draft) {
            $result = DB::select("
                SELECT * FROM get_draft_character_relationships(?)
            ", [$draft->id]);

            return array_map(function($row) {
                return [
                    'source_name' => $row->source_name,
                    'relationship_type' => $row->relationship_type,
                    'target_name' => $row->target_name,
                    'scene_id' => $row->scene_id,
                    'properties' => json_decode($row->properties, true)
                ];
            }, $result);
        }, []);
    }

    /**
     * Find shortest path between two characters
     */
    public function findCharacterPath(Draft $draft, string $fromCharacter, string $toCharacter): array
    {
        try {
            $cypherQuery = "
                MATCH path = shortestPath((a:Character {draft_id: \$draft_id, name: \$from})-[*]-(b:Character {draft_id: \$draft_id, name: \$to}))
                RETURN path
            ";

            $result = DB::select("
                SELECT ag_catalog.cypher(?, ?, ?) as path_result
            ", [
                $this->graphName,
                $cypherQuery,
                json_encode([
                    'draft_id' => $draft->id,
                    'from' => $fromCharacter,
                    'to' => $toCharacter
                ])
            ]);

            // Parse the path result
            $pathData = json_decode($result[0]->path_result ?? '[]', true);
            return $pathData[0] ?? [];

        } catch (Exception $e) {
            Log::error("Failed to find character path: " . $e->getMessage());
            return [];
        }
    }

    /**
     * Get character network (all characters connected to a specific character)
     */
    public function getCharacterNetwork(Draft $draft, string $characterName, int $depth = 2): array
    {
        try {
            $cypherQuery = "
                MATCH (c:Character {draft_id: \$draft_id, name: \$name})-[*1..\$depth]-(connected:Character)
                RETURN DISTINCT connected.name as connected_character, 
                       count(*) as connection_strength
                ORDER BY connection_strength DESC
            ";

            $result = DB::select("
                SELECT ag_catalog.cypher(?, ?, ?) as network_result
            ", [
                $this->graphName,
                $cypherQuery,
                json_encode([
                    'draft_id' => $draft->id,
                    'name' => $characterName,
                    'depth' => $depth
                ])
            ]);

            $networkData = json_decode($result[0]->network_result ?? '[]', true);
            return $networkData ?? [];

        } catch (Exception $e) {
            Log::error("Failed to get character network: " . $e->getMessage());
            return [];
        }
    }

    /**
     * Analyze scene relationships
     */
    public function analyzeSceneRelationships(Scene $scene): bool
    {
        return $this->executeAgeOperation(function() use ($scene) {
            DB::beginTransaction();

            // Extract characters from scene
            $characters = $scene->characters ?? [];
            $characterVertices = [];

            // Create character vertices if they don't exist
            foreach ($characters as $character) {
                if (is_string($character)) {
                    $characterName = $character;
                    $characterProps = [];
                } else {
                    $characterName = $character['name'] ?? 'Unknown';
                    $characterProps = $character;
                }

                $vertexId = $this->createCharacterVertex($scene->draft, $characterName, $characterProps);
                if ($vertexId) {
                    $characterVertices[$characterName] = $vertexId;
                }
            }

            // Create interactions between characters in this scene
            $characterNames = array_keys($characterVertices);
            for ($i = 0; $i < count($characterNames); $i++) {
                for ($j = $i + 1; $j < count($characterNames); $j++) {
                    $this->createRelationship(
                        $scene->draft,
                        $characterVertices[$characterNames[$i]],
                        $characterVertices[$characterNames[$j]],
                        GraphConstants::EDGE_APPEARS_IN,
                        $scene->id,
                        ['scene_title' => $scene->title]
                    );
                }
            }

            // Mark scene as analyzed
            $scene->update([
                'graph_analyzed' => true,
                'graph_last_updated' => now()
            ]);

            DB::commit();
            return true;
        }, false, "scene_analyze_{$scene->draft_id}_{$scene->id}");
    }

    /**
     * Get graph statistics for a draft
     */
    public function getDraftGraphStats(Draft $draft): array
    {
        return $this->executeAgeOperation(function() use ($draft) {
            $cypherQuery = "
                MATCH (n {draft_id: \$draft_id})
                OPTIONAL MATCH (n)-[r]-()
                RETURN 
                    count(DISTINCT n) as vertex_count,
                    count(DISTINCT r) as edge_count,
                    count(DISTINCT CASE WHEN labels(n)[0] = 'Character' THEN n END) as character_count,
                    count(DISTINCT CASE WHEN labels(n)[0] = 'Location' THEN n END) as location_count
            ";

            $result = DB::select("
                SELECT ag_catalog.cypher(?, ?, ?) as stats_result
            ", [
                $this->graphName,
                $cypherQuery,
                json_encode(['draft_id' => $draft->id])
            ]);

            $statsData = json_decode($result[0]->stats_result ?? '[]', true);
            return $statsData[0] ?? [];
        }, [
            'vertex_count' => 0,
            'edge_count' => 0,
            'character_count' => 0,
            'location_count' => 0
        ]);
    }

    /**
     * Create draft vertex in graph
     */
    private function createDraftVertex(Draft $draft): ?int
    {
        try {
            $cypherQuery = "
                CREATE (d:Draft {
                    draft_id: \$draft_id, 
                    filename: \$filename,
                    status: \$status,
                    created_at: \$created_at
                }) 
                RETURN id(d)
            ";

            $result = DB::select("
                SELECT (ag_catalog.cypher(?, ?, ?) -> 0 -> 0)::bigint as vertex_id
            ", [
                $this->graphName,
                $cypherQuery,
                json_encode([
                    'draft_id' => $draft->id,
                    'filename' => $draft->original_filename,
                    'status' => $draft->status,
                    'created_at' => $draft->created_at->toISOString()
                ])
            ]);

            return $result[0]->vertex_id ?? null;

        } catch (Exception $e) {
            Log::error("Failed to create draft vertex: " . $e->getMessage());
            return null;
        }
    }

    /**
     * Clean up orphaned graph metadata
     */
    public function cleanupOrphanedData(?Draft $draft = null): int
    {
        return $this->executeAgeOperation(function() use ($draft) {
            $result = DB::select("
                SELECT cleanup_orphaned_graph_data(?) as cleaned_count
            ", [$draft?->id]);

            return $result[0]->cleaned_count ?? 0;
        }, 0);
    }

    /**
     * Delete all graph data for a draft
     */
    public function deleteDraftGraphData(Draft $draft): int
    {
        return $this->executeAgeOperation(function() use ($draft) {
            $result = DB::select("
                SELECT delete_draft_graph_data(?) as deleted_count
            ", [$draft->id]);

            // Mark draft as not initialized
            $draft->update([
                'graph_initialized' => false,
                'graph_last_updated' => now()
            ]);

            return $result[0]->deleted_count ?? 0;
        }, 0);
    }
}
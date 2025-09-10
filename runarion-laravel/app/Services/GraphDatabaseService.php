<?php

namespace App\Services;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Exception;

class GraphDatabaseService
{
    private string $graphName;
    private string $connection;

    public function __construct(string $connection = 'pgsql')
    {
        $this->connection = $connection;
        $this->graphName = config('database.age.graph_name', 'novel_pipeline_graph');
    }

    /**
     * Execute AGE graph operations with isolated schema context
     */
    public function executeInGraphContext(callable $callback, array $params = []): mixed
    {
        return DB::connection($this->connection)->transaction(function () use ($callback, $params) {
            // Set AGE-specific search path for this connection only
            $this->setAgeSearchPath();
            
            try {
                Log::debug('Executing graph operation with AGE context');
                $result = $callback($this, ...$params);
                
                Log::debug('Graph operation completed successfully');
                return $result;
                
            } catch (Exception $e) {
                Log::error('Graph operation failed', [
                    'error' => $e->getMessage(),
                    'trace' => $e->getTraceAsString()
                ]);
                throw $e;
                
            } finally {
                // Always restore standard search path
                $this->restoreStandardSearchPath();
            }
        });
    }

    /**
     * Create a vertex in the graph
     */
    public function createVertex(string $label, array $properties = []): array
    {
        return $this->executeInGraphContext(function () use ($label, $properties) {
            $propertiesJson = empty($properties) ? '{}' : json_encode($properties);
            
            $cypher = "SELECT * FROM cypher('{$this->graphName}', \$\$ 
                CREATE (n:{$label} {$propertiesJson})
                RETURN n
            \$\$) AS (n agtype)";
            
            $result = DB::connection($this->connection)->select($cypher);
            return $this->parseAgtypeResult($result);
        });
    }

    /**
     * Find vertices by label and properties
     */
    public function findVertices(string $label, array $properties = []): array
    {
        return $this->executeInGraphContext(function () use ($label, $properties) {
            $whereClause = '';
            if (!empty($properties)) {
                $conditions = [];
                foreach ($properties as $key => $value) {
                    $conditions[] = "n.{$key} = '" . addslashes($value) . "'";
                }
                $whereClause = 'WHERE ' . implode(' AND ', $conditions);
            }
            
            $cypher = "SELECT * FROM cypher('{$this->graphName}', \$\$ 
                MATCH (n:{$label})
                {$whereClause}
                RETURN n
            \$\$) AS (n agtype)";
            
            $result = DB::connection($this->connection)->select($cypher);
            return $this->parseAgtypeResult($result);
        });
    }

    /**
     * Create a relationship between vertices
     */
    public function createRelationship(
        array $fromVertex, 
        array $toVertex, 
        string $relationshipType, 
        array $properties = []
    ): array {
        return $this->executeInGraphContext(function () use ($fromVertex, $toVertex, $relationshipType, $properties) {
            $propertiesJson = empty($properties) ? '' : json_encode($properties);
            
            $cypher = "SELECT * FROM cypher('{$this->graphName}', \$\$ 
                MATCH (a), (b)
                WHERE id(a) = {$fromVertex['id']} AND id(b) = {$toVertex['id']}
                CREATE (a)-[r:{$relationshipType} {$propertiesJson}]->(b)
                RETURN r
            \$\$) AS (r agtype)";
            
            $result = DB::connection($this->connection)->select($cypher);
            return $this->parseAgtypeResult($result);
        });
    }

    /**
     * Find relationships between vertices
     */
    public function findRelationships(string $relationshipType = '', array $properties = []): array
    {
        return $this->executeInGraphContext(function () use ($relationshipType, $properties) {
            $relationshipPattern = $relationshipType ? ":{$relationshipType}" : '';
            
            $whereClause = '';
            if (!empty($properties)) {
                $conditions = [];
                foreach ($properties as $key => $value) {
                    $conditions[] = "r.{$key} = '" . addslashes($value) . "'";
                }
                $whereClause = 'WHERE ' . implode(' AND ', $conditions);
            }
            
            $cypher = "SELECT * FROM cypher('{$this->graphName}', \$\$ 
                MATCH (a)-[r{$relationshipPattern}]->(b)
                {$whereClause}
                RETURN a, r, b
            \$\$) AS (a agtype, r agtype, b agtype)";
            
            $result = DB::connection($this->connection)->select($cypher);
            return $this->parseAgtypeResult($result, ['a', 'r', 'b']);
        });
    }

    /**
     * Execute custom Cypher query
     */
    public function executeCypher(string $cypher, array $returnColumns = ['result']): array
    {
        return $this->executeInGraphContext(function () use ($cypher, $returnColumns) {
            $columnDefinition = implode(' agtype, ', $returnColumns) . ' agtype';
            
            $query = "SELECT * FROM cypher('{$this->graphName}', \$\$ 
                {$cypher}
            \$\$) AS ({$columnDefinition})";
            
            $result = DB::connection($this->connection)->select($query);
            return $this->parseAgtypeResult($result, $returnColumns);
        });
    }

    /**
     * Get graph statistics
     */
    public function getGraphStats(): array
    {
        return $this->executeInGraphContext(function () {
            // Get vertex count by label
            $vertexStats = DB::connection($this->connection)
                ->select("SELECT label_name, label_id FROM ag_label WHERE graph_name = ? AND label_kind = 'v'", 
                        [$this->graphName]);
            
            // Get edge count by label  
            $edgeStats = DB::connection($this->connection)
                ->select("SELECT label_name, label_id FROM ag_label WHERE graph_name = ? AND label_kind = 'e'", 
                        [$this->graphName]);
            
            return [
                'vertex_labels' => $vertexStats,
                'edge_labels' => $edgeStats,
                'graph_name' => $this->graphName
            ];
        });
    }

    /**
     * Set AGE-specific search path
     */
    private function setAgeSearchPath(): void
    {
        DB::connection($this->connection)->statement('SET search_path = ag_catalog, public');
        Log::debug('Set AGE search path: ag_catalog, public');
    }

    /**
     * Restore standard PostgreSQL search path
     */
    private function restoreStandardSearchPath(): void
    {
        DB::connection($this->connection)->statement('SET search_path = public');
        Log::debug('Restored standard search path: public');
    }

    /**
     * Parse agtype results into PHP arrays
     */
    private function parseAgtypeResult(array $result, array $columns = null): array
    {
        if (empty($result)) {
            return [];
        }

        $parsed = [];
        foreach ($result as $row) {
            $parsedRow = [];
            
            if ($columns === null) {
                // Single column result - get first property
                $firstProperty = get_object_vars($row)[array_key_first(get_object_vars($row))];
                $parsedRow = json_decode($firstProperty, true) ?? [];
            } else {
                // Multiple columns
                foreach ($columns as $column) {
                    if (isset($row->$column)) {
                        $parsedRow[$column] = json_decode($row->$column, true) ?? [];
                    }
                }
            }
            
            $parsed[] = $parsedRow;
        }
        
        return $parsed;
    }

    /**
     * Check if AGE extension is available
     */
    public function isAgeAvailable(): bool
    {
        try {
            $result = DB::connection($this->connection)
                ->select("SELECT 1 FROM pg_extension WHERE extname = 'age'");
            return !empty($result);
        } catch (Exception $e) {
            Log::warning('Failed to check AGE availability', ['error' => $e->getMessage()]);
            return false;
        }
    }

    /**
     * Get current connection search path (for debugging)
     */
    public function getCurrentSearchPath(): string
    {
        $result = DB::connection($this->connection)
            ->select("SELECT current_setting('search_path') as search_path");
        
        return $result[0]->search_path ?? 'unknown';
    }
}
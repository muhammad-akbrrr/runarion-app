<?php

namespace App\Http\Controllers\ProjectEditor;

use App\Http\Controllers\Controller;
use App\Models\Projects;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Validator;
use Illuminate\Support\Str;

class RecordsController extends Controller
{
    /**
     * Get Python service URL from environment.
     */
    private function getPythonServiceUrl(): string
    {
        // Service name in docker-compose.yml is 'python-app'
        return env('PYTHON_SERVICE_URL', 'http://python-app:5000');
    }

    /**
     * Create a new entity (character, location, item, or custom type).
     */
    public function createEntity(Request $request, string $workspace_id, string $project_id)
    {
        $validator = Validator::make($request->all(), [
            'name' => 'required|string|max:255',
            'type' => 'required|string|max:255',
            'properties' => 'nullable|array',
            'vertex_label' => 'nullable|string|max:255',
        ]);

        if ($validator->fails()) {
            return response()->json([
                'error' => 'Validation failed',
                'errors' => $validator->errors(),
            ], 422);
        }

        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $response = Http::timeout(30)
                ->post($this->getPythonServiceUrl().'/api/records/entity', [
                    'project_id' => $project_id,
                    'name' => $request->input('name'),
                    'type' => $request->input('type'),
                    'properties' => $request->input('properties', []),
                    'vertex_label' => $request->input('vertex_label'),
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 201);
            } else {
                Log::error('Python service error creating entity', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to create entity',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception creating entity', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            return response()->json([
                'error' => 'Failed to create entity: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * List all entities for a project.
     */
    public function listEntities(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            // Accept both 'type' and 'category' query params for backward compatibility
            $type = $request->query('type') ?? $request->query('category');

            $url = $this->getPythonServiceUrl().'/api/records/entities/'.$project_id;
            if ($type) {
                $url .= '?type='.urlencode($type);
            }

            $response = Http::timeout(30)->get($url);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                Log::error('Python service error listing entities', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to list entities',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception listing entities', [
                'error' => $e->getMessage(),
            ]);

            return response()->json([
                'error' => 'Failed to list entities: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * Get a single entity by vertex ID.
     */
    public function getEntity(Request $request, string $workspace_id, string $project_id, int $vertex_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $response = Http::timeout(30)
                ->get($this->getPythonServiceUrl().'/api/records/entity/'.$vertex_id, [
                    'project_id' => $project_id,
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                return response()->json([
                    'error' => 'Entity not found',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception getting entity', [
                'error' => $e->getMessage(),
            ]);

            return response()->json([
                'error' => 'Failed to get entity: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * Update an entity.
     */
    public function updateEntity(Request $request, string $workspace_id, string $project_id, int $vertex_id)
    {
        $validator = Validator::make($request->all(), [
            'name' => 'nullable|string|max:255',
            'properties' => 'nullable|array',
        ]);

        if ($validator->fails()) {
            return response()->json([
                'error' => 'Validation failed',
                'errors' => $validator->errors(),
            ], 422);
        }

        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $response = Http::timeout(30)
                ->put($this->getPythonServiceUrl().'/api/records/entity/'.$vertex_id, [
                    'project_id' => $project_id,
                    'name' => $request->input('name'),
                    'properties' => $request->input('properties'),
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                Log::error('Python service error updating entity', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to update entity',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception updating entity', [
                'error' => $e->getMessage(),
            ]);

            return response()->json([
                'error' => 'Failed to update entity: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * Delete an entity.
     */
    public function deleteEntity(Request $request, string $workspace_id, string $project_id, int $vertex_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $response = Http::timeout(30)
                ->delete($this->getPythonServiceUrl().'/api/records/entity/'.$vertex_id.'?project_id='.urlencode($project_id));

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                Log::error('Python service error deleting entity', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to delete entity',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception deleting entity', [
                'error' => $e->getMessage(),
            ]);

            return response()->json([
                'error' => 'Failed to delete entity: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * Create a relationship between two entities.
     */
    public function createRelationship(Request $request, string $workspace_id, string $project_id)
    {
        $validator = Validator::make($request->all(), [
            'source' => 'required|integer', // Vertex ID from frontend
            'target' => 'required|integer', // Vertex ID from frontend
            'type' => 'required|string|max:255',
            'properties' => 'nullable|array',
            'edge_label' => 'nullable|string|max:255',
        ]);

        if ($validator->fails()) {
            return response()->json([
                'error' => 'Validation failed',
                'errors' => $validator->errors(),
            ], 422);
        }

        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $response = Http::timeout(30)
                ->post($this->getPythonServiceUrl().'/api/records/relationship', [
                    'project_id' => $project_id,
                    'source_id' => $request->input('source'), // Frontend sends vertex IDs
                    'target_id' => $request->input('target'), // Frontend sends vertex IDs
                    'type' => $request->input('type'),
                    'properties' => $request->input('properties', []),
                    'edge_label' => $request->input('edge_label'),
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 201);
            } else {
                Log::error('Python service error creating relationship', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to create relationship',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception creating relationship', [
                'error' => $e->getMessage(),
            ]);

            return response()->json([
                'error' => 'Failed to create relationship: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * List all relationships for a project.
     */
    public function listRelationships(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $type = $request->query('type');

            $url = $this->getPythonServiceUrl().'/api/records/relationships/'.$project_id;
            if ($type) {
                $url .= '?type='.urlencode($type);
            }

            $response = Http::timeout(30)->get($url);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                Log::error('Python service error listing relationships', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to list relationships',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception listing relationships', [
                'error' => $e->getMessage(),
            ]);

            return response()->json([
                'error' => 'Failed to list relationships: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * Delete a relationship.
     */
    public function updateRelationship(Request $request, string $workspace_id, string $project_id, int $edge_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $request->validate([
            'type' => 'sometimes|string',
            'properties' => 'sometimes|array',
        ]);

        try {
            $response = Http::timeout(30)
                ->put($this->getPythonServiceUrl().'/api/records/relationship/'.$edge_id, [
                    'project_id' => $project_id,
                    'type' => $request->input('type'),
                    'properties' => $request->input('properties'),
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                Log::error('Python service error updating relationship', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to update relationship',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception updating relationship', [
                'error' => $e->getMessage(),
            ]);

            return response()->json([
                'error' => 'Failed to update relationship: '.$e->getMessage(),
            ], 500);
        }
    }

    public function deleteRelationship(Request $request, string $workspace_id, string $project_id, int $edge_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $response = Http::timeout(30)
                ->delete($this->getPythonServiceUrl().'/api/records/relationship/'.$edge_id.'?project_id='.urlencode($project_id));

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                Log::error('Python service error deleting relationship', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to delete relationship',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception deleting relationship', [
                'error' => $e->getMessage(),
            ]);

            return response()->json([
                'error' => 'Failed to delete relationship: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * Create a new collection type (custom entity type).
     */
    public function createCollectionType(Request $request, string $workspace_id, string $project_id)
    {
        $validator = Validator::make($request->all(), [
            'name' => 'required|string|max:255',
            'field_schema' => 'nullable|array',
        ]);

        if ($validator->fails()) {
            return response()->json([
                'error' => 'Validation failed',
                'errors' => $validator->errors(),
            ], 422);
        }

        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            // Create vertex label in AGE via Python service
            $vertexLabel = ucwords(str_replace(['_', '-'], ' ', $request->input('name')));
            $vertexLabel = str_replace(' ', '', $vertexLabel);

            $response = Http::timeout(30)
                ->post($this->getPythonServiceUrl().'/api/records/entity-type', [
                    'vertex_label' => $vertexLabel,
                ]);

            if ($response->successful()) {
                // Store in record_entity_types table
                $typeId = (string) Str::ulid();
                DB::table('record_entity_types')->insert([
                    'id' => $typeId,
                    'project_id' => $project_id,
                    'name' => $request->input('name'),
                    'vertex_label' => $vertexLabel,
                    'is_system' => false,
                    'field_schema' => json_encode($request->input('field_schema', [])),
                    'created_at' => now(),
                    'updated_at' => now(),
                ]);

                return response()->json([
                    'success' => true,
                    'message' => 'Collection type created successfully',
                    'collection_type' => [
                        'id' => $typeId,
                        'name' => $request->input('name'),
                        'vertex_label' => $vertexLabel,
                        'field_schema' => $request->input('field_schema', []),
                    ],
                ], 201);
            } else {
                return response()->json([
                    'error' => 'Failed to create collection type',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception creating collection type', [
                'error' => $e->getMessage(),
            ]);

            return response()->json([
                'error' => 'Failed to create collection type: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * List all collection types for a project.
     */
    public function listCollectionTypes(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            // Get system types
            $systemTypes = [
                ['id' => 'character', 'name' => 'Character', 'is_system' => true],
                ['id' => 'location', 'name' => 'Location', 'is_system' => true],
                ['id' => 'item', 'name' => 'Item', 'is_system' => true],
                ['id' => 'theme', 'name' => 'Theme', 'is_system' => true],
                ['id' => 'plot_point', 'name' => 'Plot Point', 'is_system' => true],
                ['id' => 'record_keeper', 'name' => 'Record Keeper', 'is_system' => true],
            ];

            // Get custom types from database
            $customTypes = DB::table('record_entity_types')
                ->where('project_id', $project_id)
                ->where('is_system', false)
                ->get()
                ->map(function ($type) {
                    return [
                        'id' => $type->id,
                        'name' => $type->name,
                        'vertex_label' => $type->vertex_label,
                        'is_system' => false,
                        'field_schema' => json_decode($type->field_schema, true) ?? [],
                    ];
                });

            return response()->json([
                'success' => true,
                'collection_types' => [
                    'system' => $systemTypes,
                    'custom' => $customTypes,
                ],
            ], 200);
        } catch (\Exception $e) {
            Log::error('Exception listing collection types', [
                'error' => $e->getMessage(),
            ]);

            return response()->json([
                'error' => 'Failed to list collection types: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * Update a collection type.
     */
    public function updateCollectionType(Request $request, string $workspace_id, string $project_id, string $type_id)
    {
        $validator = Validator::make($request->all(), [
            'name' => 'nullable|string|max:255',
            'field_schema' => 'nullable|array',
        ]);

        if ($validator->fails()) {
            return response()->json([
                'error' => 'Validation failed',
                'errors' => $validator->errors(),
            ], 422);
        }

        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $updateData = [];
            if ($request->has('name')) {
                $updateData['name'] = $request->input('name');
            }
            if ($request->has('field_schema')) {
                $updateData['field_schema'] = json_encode($request->input('field_schema'));
            }
            $updateData['updated_at'] = now();

            DB::table('record_entity_types')
                ->where('id', $type_id)
                ->where('project_id', $project_id)
                ->update($updateData);

            return response()->json([
                'success' => true,
                'message' => 'Collection type updated successfully',
            ], 200);
        } catch (\Exception $e) {
            Log::error('Exception updating collection type', [
                'error' => $e->getMessage(),
            ]);

            return response()->json([
                'error' => 'Failed to update collection type: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * Delete a collection type.
     */
    public function deleteCollectionType(Request $request, string $workspace_id, string $project_id, string $type_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            // Check if any entities use this type
            $entityCount = DB::table('novel_graph_vertices')
                ->where('project_id', $project_id)
                ->where('entity_type', function ($query) use ($type_id) {
                    $query->select('name')
                        ->from('record_entity_types')
                        ->where('id', $type_id);
                })
                ->count();

            if ($entityCount > 0) {
                return response()->json([
                    'error' => "Cannot delete collection type: {$entityCount} entities are using this type. Please delete or reassign those entities first.",
                ], 400);
            }

            DB::table('record_entity_types')
                ->where('id', $type_id)
                ->where('project_id', $project_id)
                ->delete();

            return response()->json([
                'success' => true,
                'message' => 'Collection type deleted successfully',
            ], 200);
        } catch (\Exception $e) {
            Log::error('Exception deleting collection type', [
                'error' => $e->getMessage(),
            ]);

            return response()->json([
                'error' => 'Failed to delete collection type: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * Summarize manuscript chapters and create Record Keeper entries.
     */
    public function summarize(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'enable_record_keeper' => 'nullable|boolean',
            'category' => 'nullable|string', // Optional - if null, only create Record Keeper entries (if enabled)
            'mode' => 'nullable|string|in:all,focused', // Required only if category is selected
            'entity_ids' => 'nullable|array',
            'entity_ids.*' => 'integer',
            'chapter_orders' => 'nullable|array',
            'chapter_orders.*' => 'integer',
            'model' => 'nullable|string',
            'provider' => 'nullable|string',
        ]);

        // Validate that at least one option is enabled
        if (! ($validated['enable_record_keeper'] ?? false) && empty($validated['category'])) {
            return response()->json(['error' => 'At least one of Record Keeper or Category must be enabled'], 400);
        }

        try {
            $response = Http::timeout(300) // 5 minutes timeout for large manuscripts
                ->post($this->getPythonServiceUrl().'/api/auditor/summarize', [
                    'project_id' => $project_id,
                    'workspace_id' => $workspace_id, // Pass workspace_id for Laravel endpoint (primary method)
                    'enable_record_keeper' => $validated['enable_record_keeper'] ?? true,
                    'category' => $validated['category'] ?? null, // Can be null, "all_categories", or specific category
                    'mode' => $validated['mode'] ?? 'all',
                    'entity_ids' => $validated['entity_ids'] ?? null,
                    'chapter_orders' => $validated['chapter_orders'] ?? null,
                    'model' => $validated['model'] ?? 'gemini-2.5-flash',
                    'provider' => $validated['provider'] ?? 'gemini',
                ]);

            if ($response->successful()) {
                $responseData = $response->json();
                Log::info('Summarization completed', [
                    'created' => $responseData['results']['record_keeper_entries_created'] ?? 0,
                    'updated' => $responseData['results']['record_keeper_entries_updated'] ?? 0,
                    'errors' => count($responseData['results']['errors'] ?? []),
                ]);

                return response()->json($responseData, 200);
            } else {
                $errorBody = $response->json();
                Log::error('Python service error summarizing', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                    'error' => $errorBody,
                ]);

                return response()->json([
                    'error' => 'Failed to summarize manuscript',
                    'details' => $errorBody,
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception summarizing manuscript', [
                'error' => $e->getMessage(),
            ]);

            return response()->json([
                'error' => 'Failed to summarize manuscript: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * Extract entities from manuscript for specified categories.
     */
    public function extractEntities(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'categories' => 'required|array',
            'categories.*' => 'string',
            'chapter_orders' => 'nullable|array',
            'chapter_orders.*' => 'integer',
            'scan_mode' => 'nullable|string|in:incremental,full,new_only',
            'model' => 'nullable|string',
            'provider' => 'nullable|string',
        ]);

        try {
            $response = Http::timeout(300) // 5 minutes timeout
                ->post($this->getPythonServiceUrl().'/api/auditor/extract', [
                    'project_id' => $project_id,
                    'workspace_id' => $workspace_id,
                    'categories' => $validated['categories'],
                    'chapter_orders' => $validated['chapter_orders'] ?? null,
                    'scan_mode' => $validated['scan_mode'] ?? 'incremental',
                    'model' => $validated['model'] ?? 'gemini-2.5-flash',
                    'provider' => $validated['provider'] ?? 'gemini',
                ]);

            if ($response->successful()) {
                $responseData = $response->json();
                Log::info('Entity extraction completed', [
                    'created' => $responseData['results']['entities_created'] ?? 0,
                    'updated' => $responseData['results']['entities_updated'] ?? 0,
                    'categories' => array_keys($responseData['results']['categories_processed'] ?? []),
                    'scan_mode' => $validated['scan_mode'] ?? 'incremental',
                ]);

                return response()->json($responseData, 200);
            } else {
                $errorBody = $response->json();
                Log::error('Python service error extracting entities', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                    'error' => $errorBody,
                ]);

                return response()->json([
                    'error' => 'Failed to extract entities',
                    'details' => $errorBody,
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception extracting entities', [
                'error' => $e->getMessage(),
            ]);

            return response()->json([
                'error' => 'Failed to extract entities: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * Get all categories for a project.
     */
    public function getCategories(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $response = Http::timeout(30)
                ->get($this->getPythonServiceUrl().'/api/records/categories', [
                    'project_id' => $project_id,
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                return response()->json([
                    'error' => 'Failed to get categories',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception getting categories', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Get entities for a project, optionally filtered by category.
     */
    public function getEntitiesByCategory(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $category = $request->query('category');

        try {
            $params = ['project_id' => $project_id];
            if ($category) {
                $params['category'] = $category;
            }

            $response = Http::timeout(30)
                ->get($this->getPythonServiceUrl().'/api/records/entities', $params);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                return response()->json([
                    'error' => 'Failed to get entities',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception getting entities', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Get scan status for all chapters in a project.
     */
    public function getScanStatus(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $response = Http::timeout(30)
                ->get($this->getPythonServiceUrl().'/api/auditor/scan-status', [
                    'project_id' => $project_id,
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                return response()->json([
                    'error' => 'Failed to get scan status',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception getting scan status', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Check consistency between database records and story content.
     */
    public function checkRecordConsistency(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'categories' => 'nullable|array',
            'categories.*' => 'string',
            'model' => 'nullable|string',
            'provider' => 'nullable|string',
        ]);

        try {
            $response = Http::timeout(300)
                ->post($this->getPythonServiceUrl().'/api/auditor/check-consistency/records', [
                    'project_id' => $project_id,
                    'workspace_id' => $workspace_id,
                    'categories' => $validated['categories'] ?? null,
                    'model' => $validated['model'] ?? 'gemini-2.5-flash',
                    'provider' => $validated['provider'] ?? 'gemini',
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                return response()->json([
                    'error' => 'Failed to check record consistency',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception checking record consistency', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Check story itself for internal consistency issues.
     */
    public function checkStoryConsistency(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'check_types' => 'nullable|array',
            'check_types.*' => 'string|in:plot_holes,timeline,character,continuity',
            'chapter_orders' => 'nullable|array',
            'chapter_orders.*' => 'integer',
            'model' => 'nullable|string',
            'provider' => 'nullable|string',
        ]);

        try {
            $response = Http::timeout(600) // 10 minutes for large stories
                ->post($this->getPythonServiceUrl().'/api/auditor/check-consistency/story', [
                    'project_id' => $project_id,
                    'workspace_id' => $workspace_id,
                    'check_types' => $validated['check_types'] ?? null,
                    'chapter_orders' => $validated['chapter_orders'] ?? null,
                    'model' => $validated['model'] ?? 'gemini-2.5-flash',
                    'provider' => $validated['provider'] ?? 'gemini',
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                return response()->json([
                    'error' => 'Failed to check story consistency',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception checking story consistency', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Find potential duplicate entities.
     */
    public function findDuplicates(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'scope' => 'nullable|string|in:all,category,entity',
            'categories' => 'nullable|array',
            'categories.*' => 'string',
            'entity_ids' => 'nullable|array',
            'entity_ids.*' => 'string',
            'model' => 'nullable|string',
            'provider' => 'nullable|string',
        ]);

        try {
            $response = Http::timeout(300)
                ->post($this->getPythonServiceUrl().'/api/auditor/find-duplicates', [
                    'project_id' => $project_id,
                    'workspace_id' => $workspace_id,
                    'scope' => $validated['scope'] ?? 'all',
                    'categories' => $validated['categories'] ?? null,
                    'entity_ids' => $validated['entity_ids'] ?? null,
                    'model' => $validated['model'] ?? 'gemini-2.5-flash',
                    'provider' => $validated['provider'] ?? 'gemini',
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                return response()->json([
                    'error' => 'Failed to find duplicates',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception finding duplicates', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Merge two entities into one.
     */
    public function mergeEntities(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'source_vertex_id' => 'required|string',
            'target_vertex_id' => 'required|string',
            'merge_strategy' => 'nullable|string|in:combine,prefer_source,prefer_target',
        ]);

        try {
            $response = Http::timeout(60)
                ->post($this->getPythonServiceUrl().'/api/auditor/merge-entities', [
                    'project_id' => $project_id,
                    'source_vertex_id' => $validated['source_vertex_id'],
                    'target_vertex_id' => $validated['target_vertex_id'],
                    'merge_strategy' => $validated['merge_strategy'] ?? 'combine',
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                $pythonResponse = $response->json();

                return response()->json([
                    'error' => $pythonResponse['error'] ?? 'Failed to merge entities',
                    'details' => $pythonResponse,
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception merging entities', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Refresh a single entity's properties to current story state (arc-aware)
     */
    public function refreshEntityProperties(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'vertex_id' => 'required|string',
            'model' => 'nullable|string',
            'provider' => 'nullable|string',
        ]);

        try {
            $response = Http::timeout(120)
                ->post($this->getPythonServiceUrl().'/api/auditor/refresh-properties', [
                    'project_id' => $project_id,
                    'workspace_id' => $workspace_id,
                    'vertex_id' => $validated['vertex_id'],
                    'model' => $validated['model'] ?? 'gemini-2.5-flash',
                    'provider' => $validated['provider'] ?? 'gemini',
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                return response()->json([
                    'error' => 'Failed to refresh entity properties',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception refreshing entity properties', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Refresh all entities' properties to current story state (arc-aware)
     */
    public function refreshAllProperties(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'categories' => 'nullable|array',
            'categories.*' => 'string',
            'entity_ids' => 'nullable|array',
            'entity_ids.*' => 'string',
            'model' => 'nullable|string',
            'provider' => 'nullable|string',
        ]);

        try {
            $response = Http::timeout(600) // 10 minute timeout for bulk operation (many entities)
                ->post($this->getPythonServiceUrl().'/api/auditor/refresh-all-properties', [
                    'project_id' => $project_id,
                    'workspace_id' => $workspace_id,
                    'categories' => $validated['categories'] ?? null,
                    'entity_ids' => $validated['entity_ids'] ?? null,
                    'model' => $validated['model'] ?? 'gemini-2.5-flash',
                    'provider' => $validated['provider'] ?? 'gemini',
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                return response()->json([
                    'error' => 'Failed to refresh all properties',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception refreshing all properties', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Apply a fix from consistency check results
     */
    public function applyConsistencyFix(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'entity_name' => 'required|string',
            'entity_type' => 'nullable|string',
            'issue_type' => 'required|string',
            'field' => 'nullable|string',
            'suggestion' => 'required|string',
            'model' => 'nullable|string',
            'provider' => 'nullable|string',
        ]);

        try {
            $response = Http::timeout(120)
                ->post($this->getPythonServiceUrl().'/api/auditor/apply-fix', [
                    'project_id' => $project_id,
                    'workspace_id' => $workspace_id,
                    'entity_name' => $validated['entity_name'],
                    'entity_type' => $validated['entity_type'] ?? null,
                    'issue_type' => $validated['issue_type'],
                    'field' => $validated['field'] ?? null,
                    'suggestion' => $validated['suggestion'],
                    'model' => $validated['model'] ?? 'gemini-2.5-flash',
                    'provider' => $validated['provider'] ?? 'gemini',
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                return response()->json([
                    'error' => 'Failed to apply fix',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception applying consistency fix', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Generate a story text fix for a consistency issue.
     * This fixes the actual chapter text, not entity properties.
     */
    public function fixStoryText(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'issue_type' => 'required|string',
            'title' => 'required|string',
            'description' => 'nullable|string',
            'evidence' => 'nullable|string',
            'location' => 'nullable|string',
            'suggestion' => 'nullable|string',
            'model' => 'nullable|string',
            'provider' => 'nullable|string',
        ]);

        try {
            $response = Http::timeout(120)
                ->post($this->getPythonServiceUrl().'/api/auditor/fix-story-text', [
                    'project_id' => $project_id,
                    'workspace_id' => $workspace_id,
                    'issue_type' => $validated['issue_type'],
                    'title' => $validated['title'],
                    'description' => $validated['description'] ?? '',
                    'evidence' => $validated['evidence'] ?? '',
                    'location' => $validated['location'] ?? '',
                    'suggestion' => $validated['suggestion'] ?? '',
                    'model' => $validated['model'] ?? 'gemini-2.5-flash',
                    'provider' => $validated['provider'] ?? 'gemini',
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                return response()->json([
                    'error' => 'Failed to generate story fix',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception generating story fix', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Generate batch story text fixes for multiple consistency issues.
     * All fixes are generated against the same content snapshot.
     */
    public function batchFixStoryText(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'issues' => 'required|array|min:1',
            'issues.*.issue_type' => 'required|string',
            'issues.*.title' => 'nullable|string',
            'issues.*.description' => 'nullable|string',
            'issues.*.evidence' => 'nullable|string',
            'issues.*.location' => 'nullable|string',
            'issues.*.suggestion' => 'nullable|string',
            'model' => 'nullable|string',
            'provider' => 'nullable|string',
        ]);

        try {
            $response = Http::timeout(180) // 3 minutes for batch processing
                ->post($this->getPythonServiceUrl().'/api/auditor/batch-fix-story-text', [
                    'project_id' => $project_id,
                    'workspace_id' => $workspace_id,
                    'issues' => $validated['issues'],
                    'model' => $validated['model'] ?? 'gemini-2.5-flash',
                    'provider' => $validated['provider'] ?? 'gemini',
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                return response()->json([
                    'error' => 'Failed to generate batch story fixes',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception generating batch story fixes', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    // =========================================================================
    // SENTIMENT ANALYZER ENDPOINTS
    // =========================================================================

    /**
     * Extract character relationships from manuscript with sentiment analysis.
     * Uses V2 chapter-based analysis for more reliable results.
     */
    public function extractRelationships(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'character_ids' => 'nullable|array',
            'character_ids.*' => 'string',
            'chapter_orders' => 'nullable|array',
            'chapter_orders.*' => 'integer',
            'model' => 'nullable|string',
            'provider' => 'nullable|string',
            'focus_mode' => 'nullable|string|in:all,selected,1-to-1',
            'use_v2' => 'nullable|boolean',  // Flag to use V2 (default: true)
        ]);

        // Use V2 by default (chapter-based analysis)
        $useV2 = $validated['use_v2'] ?? true;
        $endpoint = $useV2
            ? '/api/auditor/extract-relationships-v2'
            : '/api/auditor/extract-relationships';

        try {
            $response = Http::timeout(300) // 5 minutes for relationship extraction
                ->post($this->getPythonServiceUrl().$endpoint, [
                    'project_id' => $project_id,
                    'workspace_id' => $workspace_id,
                    'character_ids' => $validated['character_ids'] ?? null,
                    'chapter_orders' => $validated['chapter_orders'] ?? null,
                    'model' => $validated['model'] ?? 'gemini-2.5-flash',
                    'provider' => $validated['provider'] ?? 'gemini',
                    'focus_mode' => $validated['focus_mode'] ?? 'all',
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                Log::error('Python service error extracting relationships', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to extract relationships',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception extracting relationships', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Scan for relationship changes between stored state and current manuscript.
     */
    public function scanRelationshipChanges(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'model' => 'nullable|string',
            'provider' => 'nullable|string',
        ]);

        try {
            $response = Http::timeout(300)
                ->post($this->getPythonServiceUrl().'/api/auditor/scan-relationship-changes', [
                    'project_id' => $project_id,
                    'workspace_id' => $workspace_id,
                    'model' => $validated['model'] ?? 'gemini-2.5-flash',
                    'provider' => $validated['provider'] ?? 'gemini',
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                Log::error('Python service error scanning relationship changes', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to scan relationship changes',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception scanning relationship changes', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Delete all interactions for a project.
     */
    public function deleteAllInteractions(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $response = Http::timeout(60)
                ->delete($this->getPythonServiceUrl().'/api/auditor/interactions/delete-all?project_id='.urlencode($project_id));

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                Log::error('Python service error deleting interactions', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to delete interactions',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception deleting interactions', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Delete a single interaction.
     */
    public function deleteInteraction(Request $request, string $workspace_id, string $project_id, string $vertex_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $response = Http::timeout(60)
                ->delete($this->getPythonServiceUrl().'/api/auditor/interactions/'.$vertex_id.'?project_id='.urlencode($project_id));

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                Log::error('Python service error deleting interaction', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to delete interaction',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception deleting interaction', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Update a single interaction.
     */
    public function updateInteraction(Request $request, string $workspace_id, string $project_id, string $vertex_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'interaction_type' => 'nullable|string',
            'emotional_tone' => 'nullable|string',
            'sentiment_modifier' => 'nullable|integer',
            'context' => 'nullable|string',
            'text_evidence' => 'nullable|string',
        ]);

        try {
            $response = Http::timeout(60)
                ->put($this->getPythonServiceUrl().'/api/auditor/interactions/'.$vertex_id, [
                    'project_id' => $project_id,
                    ...$validated,
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                Log::error('Python service error updating interaction', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to update interaction',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception updating interaction', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Create a new interaction.
     */
    public function createInteraction(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'source_character' => 'required|string',
            'target_character' => 'required|string',
            'chapter_number' => 'required|integer',
            'chapter_name' => 'nullable|string',
            'interaction_type' => 'required|string',
            'emotional_tone' => 'required|string',
            'sentiment_modifier' => 'nullable|integer',
            'context' => 'nullable|string',
            'text_evidence' => 'nullable|string',
        ]);

        try {
            $response = Http::timeout(60)
                ->post($this->getPythonServiceUrl().'/api/auditor/interactions/create', [
                    'project_id' => $project_id,
                    ...$validated,
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 201);
            } else {
                Log::error('Python service error creating interaction', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to create interaction',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception creating interaction', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Apply selected relationship changes to the database.
     */
    public function applyRelationshipChanges(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'changes' => 'required|array',
            'changes.*.action' => 'required|string|in:update,create,delete',
        ]);

        try {
            $response = Http::timeout(120)
                ->post($this->getPythonServiceUrl().'/api/auditor/apply-relationship-changes', [
                    'project_id' => $project_id,
                    'changes' => $validated['changes'],
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                Log::error('Python service error applying relationship changes', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to apply relationship changes',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception applying relationship changes', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    // =========================================================================
    // INTERACTION RECORDS ENDPOINTS
    // =========================================================================

    /**
     * Get all interaction records for a project.
     */
    public function getInteractions(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $sourceCharacter = $request->query('source_character');
        $targetCharacter = $request->query('target_character');

        try {
            $queryParams = ['project_id' => $project_id];

            if ($sourceCharacter) {
                $queryParams['source_character'] = $sourceCharacter;
            }
            if ($targetCharacter) {
                $queryParams['target_character'] = $targetCharacter;
            }

            $response = Http::timeout(60)
                ->get($this->getPythonServiceUrl().'/api/auditor/interactions', $queryParams);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                Log::error('Python service error getting interactions', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to get interactions',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception getting interactions', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Aggregate interactions between two characters into a relationship summary.
     */
    public function aggregateInteractions(Request $request, string $workspace_id, string $project_id)
    {
        // Verify project belongs to workspace
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $sourceCharacter = $request->query('source_character');
        $targetCharacter = $request->query('target_character');

        if (! $sourceCharacter || ! $targetCharacter) {
            return response()->json(['error' => 'source_character and target_character are required'], 400);
        }

        try {
            $response = Http::timeout(60)
                ->get($this->getPythonServiceUrl().'/api/auditor/interactions/aggregate', [
                    'project_id' => $project_id,
                    'source_character' => $sourceCharacter,
                    'target_character' => $targetCharacter,
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                Log::error('Python service error aggregating interactions', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to aggregate interactions',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception aggregating interactions', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Synthesize a holistic relationship summary using AI.
     */
    public function synthesizeRelationship(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'source_character' => 'required|string',
            'target_character' => 'required|string',
            'model' => 'nullable|string',
            'provider' => 'nullable|string',
        ]);

        try {
            $response = Http::timeout(120)
                ->post($this->getPythonServiceUrl().'/api/auditor/relationships/synthesize', [
                    'project_id' => $project_id,
                    'workspace_id' => $workspace_id,
                    'source_character' => $validated['source_character'],
                    'target_character' => $validated['target_character'],
                    'model' => $validated['model'] ?? 'gemini-2.5-flash',
                    'provider' => $validated['provider'] ?? 'gemini',
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                Log::error('Python service error synthesizing relationship', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to synthesize relationship',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception synthesizing relationship', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Recalculate sentiment score for a relationship from its interactions.
     */
    public function recalculateRelationshipSentiment(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'source_character' => 'required|string',
            'target_character' => 'required|string',
        ]);

        try {
            $response = Http::timeout(60)
                ->post($this->getPythonServiceUrl().'/api/auditor/relationships/recalculate', [
                    'project_id' => $project_id,
                    'source_character' => $validated['source_character'],
                    'target_character' => $validated['target_character'],
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                Log::error('Python service error recalculating sentiment', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to recalculate sentiment',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception recalculating sentiment', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Update chapter analyses for a relationship.
     */
    public function updateChapterAnalyses(Request $request, string $workspace_id, string $project_id, int $edge_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'chapter_analyses' => 'required|array',
            'recalculate_overall' => 'nullable|boolean',
        ]);

        try {
            $response = Http::timeout(60)
                ->put($this->getPythonServiceUrl().'/api/auditor/relationship/'.$edge_id.'/chapter-analyses', [
                    'project_id' => $project_id,
                    'chapter_analyses' => $validated['chapter_analyses'],
                    'recalculate_overall' => $validated['recalculate_overall'] ?? true,
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                Log::error('Python service error updating chapter analyses', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to update chapter analyses',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception updating chapter analyses', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Get emotional tones for a project.
     */
    public function getEmotionalTones(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $response = Http::timeout(30)
                ->get($this->getPythonServiceUrl().'/api/auditor/emotional-tones/'.$project_id);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                return response()->json([
                    'error' => 'Failed to get emotional tones',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception getting emotional tones', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Create a custom emotional tone.
     */
    public function createEmotionalTone(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        $validated = $request->validate([
            'name' => 'required|string|max:100',
            'description' => 'nullable|string|max:500',
        ]);

        try {
            $response = Http::timeout(30)
                ->post($this->getPythonServiceUrl().'/api/auditor/emotional-tones/'.$project_id, [
                    'name' => $validated['name'],
                    'description' => $validated['description'] ?? '',
                ]);

            if ($response->successful()) {
                return response()->json($response->json(), 201);
            } else {
                return response()->json([
                    'error' => 'Failed to create emotional tone',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception creating emotional tone', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Delete a custom emotional tone.
     */
    public function deleteEmotionalTone(Request $request, string $workspace_id, string $project_id, string $tone_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $response = Http::timeout(30)
                ->delete($this->getPythonServiceUrl().'/api/auditor/emotional-tones/'.$project_id.'/'.$tone_id);

            if ($response->successful()) {
                return response()->json($response->json(), 200);
            } else {
                return response()->json([
                    'error' => 'Failed to delete emotional tone',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception deleting emotional tone', ['error' => $e->getMessage()]);

            return response()->json(['error' => $e->getMessage()], 500);
        }
    }
}

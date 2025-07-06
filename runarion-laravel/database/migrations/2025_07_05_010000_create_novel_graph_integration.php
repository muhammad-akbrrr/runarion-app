<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

return new class extends Migration {
    public function up(): void
    {
        // Create a metadata table to track graph vertices created for relational records
        Schema::create('novel_graph_vertices', function (Blueprint $table) {
            $table->id();
            $table->ulid('draft_id');
            $table->string('entity_type'); // 'character', 'location', 'item', 'theme', 'plot_point'
            $table->string('entity_name');
            $table->bigInteger('vertex_id'); // AGE vertex ID
            $table->string('vertex_label'); // AGE vertex label
            $table->json('properties')->nullable();
            $table->timestamps();

            $table->foreign('draft_id')->references('id')->on('drafts')->onDelete('cascade');
            $table->unique(['draft_id', 'entity_type', 'entity_name']);
            $table->index(['draft_id', 'entity_type']);
            $table->index(['vertex_id', 'vertex_label']);
        });

        // Create a metadata table to track graph edges created for relationships
        Schema::create('novel_graph_edges', function (Blueprint $table) {
            $table->id();
            $table->ulid('draft_id');
            $table->bigInteger('scene_id')->nullable(); // Reference to scene where relationship occurs
            $table->bigInteger('source_vertex_id'); // AGE vertex ID
            $table->bigInteger('target_vertex_id'); // AGE vertex ID
            $table->bigInteger('edge_id'); // AGE edge ID
            $table->string('edge_label'); // AGE edge label
            $table->json('properties')->nullable();
            $table->timestamps();

            $table->foreign('draft_id')->references('id')->on('drafts')->onDelete('cascade');
            $table->foreign('scene_id')->references('id')->on('scenes')->onDelete('cascade');
            $table->index(['draft_id', 'scene_id']);
            $table->index(['edge_id', 'edge_label']);
            $table->index(['source_vertex_id', 'target_vertex_id']);
        });

        // Add graph-related columns to existing tables if needed
        Schema::table('drafts', function (Blueprint $table) {
            $table->boolean('graph_initialized')->default(false);
            $table->timestamp('graph_last_updated')->nullable();
        });

        Schema::table('scenes', function (Blueprint $table) {
            $table->boolean('graph_analyzed')->default(false);
            $table->timestamp('graph_last_updated')->nullable();
        });

        // Create functions to interact with AGE graph
        DB::statement("
            CREATE OR REPLACE FUNCTION create_novel_character_vertex(
                draft_id_param text,
                character_name text,
                character_properties jsonb DEFAULT '{}'::jsonb
            ) RETURNS bigint AS $$
            DECLARE
                vertex_id bigint;
            BEGIN
                -- Create vertex using AGE
                SELECT (ag_catalog.cypher('novel_pipeline_graph', 
                    'CREATE (c:Character {draft_id: \$draft_id, name: \$name, properties: \$props}) RETURN id(c)',
                    jsonb_build_object('draft_id', draft_id_param, 'name', character_name, 'props', character_properties)
                ) -> 0 -> 0)::bigint INTO vertex_id;
                
                -- Insert metadata record
                INSERT INTO novel_graph_vertices (draft_id, entity_type, entity_name, vertex_id, vertex_label, properties)
                VALUES (draft_id_param, 'character', character_name, vertex_id, 'Character', character_properties);
                
                RETURN vertex_id;
            END;
            $$ LANGUAGE plpgsql;
        ");

        DB::statement("
            CREATE OR REPLACE FUNCTION create_novel_relationship(
                draft_id_param text,
                source_vertex_id_param bigint,
                target_vertex_id_param bigint,
                relationship_type text,
                scene_id_param bigint DEFAULT NULL,
                relationship_properties jsonb DEFAULT '{}'::jsonb
            ) RETURNS bigint AS $$
            DECLARE
                edge_id bigint;
            BEGIN
                -- Create edge using AGE
                SELECT (ag_catalog.cypher('novel_pipeline_graph', 
                    format('MATCH (a) WHERE id(a) = \$source_id 
                            MATCH (b) WHERE id(b) = \$target_id 
                            CREATE (a)-[r:%I \$props]->(b) 
                            RETURN id(r)', relationship_type),
                    jsonb_build_object('source_id', source_vertex_id_param, 'target_id', target_vertex_id_param, 'props', relationship_properties)
                ) -> 0 -> 0)::bigint INTO edge_id;
                
                -- Insert metadata record
                INSERT INTO novel_graph_edges (draft_id, scene_id, source_vertex_id, target_vertex_id, edge_id, edge_label, properties)
                VALUES (draft_id_param, scene_id_param, source_vertex_id_param, target_vertex_id_param, edge_id, relationship_type, relationship_properties);
                
                RETURN edge_id;
            END;
            $$ LANGUAGE plpgsql;
        ");

        DB::statement("
            CREATE OR REPLACE FUNCTION cleanup_orphaned_graph_data(draft_id_param text DEFAULT NULL)
            RETURNS integer AS $$
            DECLARE
                cleaned_count integer := 0;
                vertex_record RECORD;
                edge_record RECORD;
            BEGIN
                -- Clean up orphaned vertices (vertices that don't exist in AGE graph)
                FOR vertex_record IN 
                    SELECT vertex_id, vertex_label 
                    FROM novel_graph_vertices 
                    WHERE (draft_id_param IS NULL OR draft_id = draft_id_param)
                LOOP
                    BEGIN
                        -- Check if vertex exists in AGE graph
                        PERFORM ag_catalog.cypher('novel_pipeline_graph', 
                            'MATCH (v) WHERE id(v) = \$vertex_id RETURN v',
                            jsonb_build_object('vertex_id', vertex_record.vertex_id)
                        );
                    EXCEPTION
                        WHEN OTHERS THEN
                            -- Vertex doesn't exist, remove metadata
                            DELETE FROM novel_graph_vertices WHERE vertex_id = vertex_record.vertex_id;
                            cleaned_count := cleaned_count + 1;
                    END;
                END LOOP;
                
                -- Clean up orphaned edges (edges that don't exist in AGE graph)
                FOR edge_record IN 
                    SELECT edge_id, edge_label 
                    FROM novel_graph_edges 
                    WHERE (draft_id_param IS NULL OR draft_id = draft_id_param)
                LOOP
                    BEGIN
                        -- Check if edge exists in AGE graph
                        PERFORM ag_catalog.cypher('novel_pipeline_graph', 
                            'MATCH ()-[r]->() WHERE id(r) = \$edge_id RETURN r',
                            jsonb_build_object('edge_id', edge_record.edge_id)
                        );
                    EXCEPTION
                        WHEN OTHERS THEN
                            -- Edge doesn't exist, remove metadata
                            DELETE FROM novel_graph_edges WHERE edge_id = edge_record.edge_id;
                            cleaned_count := cleaned_count + 1;
                    END;
                END LOOP;
                
                RETURN cleaned_count;
            EXCEPTION
                WHEN OTHERS THEN
                    RAISE WARNING 'Graph cleanup failed: %', SQLERRM;
                    RETURN 0;
            END;
            $$ LANGUAGE plpgsql;
        ");

        DB::statement("
            CREATE OR REPLACE FUNCTION delete_draft_graph_data(draft_id_param text)
            RETURNS integer AS $$
            DECLARE
                deleted_count integer := 0;
            BEGIN
                -- Delete all AGE vertices for this draft
                SELECT (ag_catalog.cypher('novel_pipeline_graph', 
                    'MATCH (n {draft_id: \$draft_id}) DETACH DELETE n RETURN count(n)',
                    jsonb_build_object('draft_id', draft_id_param)
                ) -> 0 -> 0)::integer INTO deleted_count;
                
                -- Clean up metadata tables
                DELETE FROM novel_graph_edges WHERE draft_id = draft_id_param;
                DELETE FROM novel_graph_vertices WHERE draft_id = draft_id_param;
                
                RETURN deleted_count;
            EXCEPTION
                WHEN OTHERS THEN
                    RAISE WARNING 'Failed to delete graph data for draft %: %', draft_id_param, SQLERRM;
                    RETURN 0;
            END;
            $$ LANGUAGE plpgsql;
        ");

        DB::statement("
            CREATE OR REPLACE FUNCTION get_draft_character_relationships(draft_id_param text)
            RETURNS TABLE(
                source_name text,
                relationship_type text,
                target_name text,
                scene_id bigint,
                properties jsonb
            ) AS $$
            DECLARE
                relationship_record jsonb;
                relationships_result ag_catalog.agtype;
            BEGIN
                -- Single Cypher query to get all character relationships
                SELECT ag_catalog.cypher('novel_pipeline_graph', 
                    'MATCH (a:Character)-[r]->(b:Character) 
                     WHERE a.draft_id = \$draft_id 
                     RETURN a.name, type(r), b.name, r.scene_id, r.properties',
                    jsonb_build_object('draft_id', draft_id_param)
                ) INTO relationships_result;
                
                -- Parse each relationship from the result set
                FOR relationship_record IN SELECT jsonb_array_elements(relationships_result::jsonb)
                LOOP
                    source_name := (relationship_record -> 0)::text;
                    relationship_type := (relationship_record -> 1)::text;
                    target_name := (relationship_record -> 2)::text;
                    scene_id := (relationship_record -> 3)::bigint;
                    properties := (relationship_record -> 4)::jsonb;
                    
                    RETURN NEXT;
                END LOOP;
                
                RETURN;
            EXCEPTION
                WHEN OTHERS THEN
                    -- Graceful fallback if AGE is not available
                    RAISE WARNING 'AGE graph query failed: %', SQLERRM;
                    RETURN;
            END;
            $$ LANGUAGE plpgsql;
        ");
    }

    public function down(): void
    {
        // Drop functions
        DB::statement('DROP FUNCTION IF EXISTS create_novel_character_vertex');
        DB::statement('DROP FUNCTION IF EXISTS create_novel_relationship');
        DB::statement('DROP FUNCTION IF EXISTS get_draft_character_relationships');
        DB::statement('DROP FUNCTION IF EXISTS cleanup_orphaned_graph_data');
        DB::statement('DROP FUNCTION IF EXISTS delete_draft_graph_data');

        // Remove added columns
        Schema::table('scenes', function (Blueprint $table) {
            $table->dropColumn(['graph_analyzed', 'graph_last_updated']);
        });

        Schema::table('drafts', function (Blueprint $table) {
            $table->dropColumn(['graph_initialized', 'graph_last_updated']);
        });

        // Drop tables
        Schema::dropIfExists('novel_graph_edges');
        Schema::dropIfExists('novel_graph_vertices');
    }
};
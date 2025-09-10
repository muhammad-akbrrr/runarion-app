<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

return new class extends Migration {
    public function up(): void
    {
        // AGE-First Architecture: No relational backup tables needed
        // All graph operations go directly to Apache AGE graph database

        // Add graph-related columns to existing tables if needed
        Schema::table('drafts', function (Blueprint $table) {
            $table->boolean('graph_initialized')->default(false);
            $table->timestamp('graph_last_updated')->nullable();
        });

        Schema::table('scenes', function (Blueprint $table) {
            $table->boolean('graph_analyzed')->default(false);
            $table->timestamp('graph_last_updated')->nullable();
        });

        DB::statement("
            CREATE OR REPLACE FUNCTION create_novel_vertex(
                draft_id_param text,
                entity_name text,
                entity_type text,
                entity_properties jsonb DEFAULT '{}'::jsonb
            ) RETURNS bigint AS $$
            DECLARE
                vertex_id bigint;
                cypher_query text;
                original_search_path text;
            BEGIN
                -- AGE-First Architecture: Require AGE to be available
                -- Store original search path
                SELECT current_setting('search_path') INTO original_search_path;
                
                -- Load AGE extension - required for all operations
                LOAD 'age';
                
                -- Set search path to include ag_catalog
                PERFORM set_config('search_path', 'ag_catalog, ' || original_search_path, false);
                
                -- Build Cypher query for vertex creation
                cypher_query := format('CREATE (n:%I {draft_id: ''%s'', name: ''%s'', properties: ''%s''}) RETURN id(n)', 
                                     entity_type, draft_id_param, entity_name, entity_properties::text);
                
                -- Create vertex using AGE
                SELECT (result.vertex_id)::bigint INTO vertex_id
                FROM ag_catalog.cypher('novel_pipeline_graph', cypher_query) AS result(vertex_id agtype);
                
                -- Restore original search path
                PERFORM set_config('search_path', original_search_path, false);
                
                RETURN vertex_id;
                
            EXCEPTION
                WHEN OTHERS THEN
                    -- Restore original search path on error
                    PERFORM set_config('search_path', original_search_path, false);
                    RAISE EXCEPTION 'AGE vertex creation failed for % (%): %', entity_name, entity_type, SQLERRM;
            END;
            $$ LANGUAGE plpgsql;
        ");

        DB::statement("
            CREATE OR REPLACE FUNCTION create_novel_relationship(
                draft_id_param text,
                source_name text,
                target_name text,
                relationship_type text,
                scene_id_param bigint DEFAULT NULL,
                relationship_properties jsonb DEFAULT '{}'::jsonb
            ) RETURNS bigint AS $$
            DECLARE
                edge_id bigint;
                cypher_query text;
                original_search_path text;
                final_properties jsonb;
            BEGIN
                -- AGE-First Architecture: Require AGE to be available
                -- Store original search path
                SELECT current_setting('search_path') INTO original_search_path;
                
                -- Load AGE extension - required for all operations
                LOAD 'age';
                
                -- Set search path to include ag_catalog
                PERFORM set_config('search_path', 'ag_catalog, ' || original_search_path, false);
                
                -- Add scene_id to properties if provided
                final_properties := relationship_properties;
                IF scene_id_param IS NOT NULL THEN
                    final_properties := final_properties || jsonb_build_object('scene_id', scene_id_param);
                END IF;
                
                -- Build Cypher query for relationship creation
                cypher_query := format('MATCH (a {draft_id: ''%s'', name: ''%s''}) 
                                       MATCH (b {draft_id: ''%s'', name: ''%s''}) 
                                       CREATE (a)-[r:%I %s]->(b) 
                                       RETURN id(r)', 
                                     draft_id_param, source_name, 
                                     draft_id_param, target_name, 
                                     relationship_type, final_properties::text);
                
                -- Create edge using AGE
                SELECT (result.edge_id)::bigint INTO edge_id
                FROM ag_catalog.cypher('novel_pipeline_graph', cypher_query) AS result(edge_id agtype);
                
                -- Restore original search path
                PERFORM set_config('search_path', original_search_path, false);
                
                RETURN edge_id;
                
            EXCEPTION
                WHEN OTHERS THEN
                    -- Restore original search path on error
                    PERFORM set_config('search_path', original_search_path, false);
                    RAISE EXCEPTION 'AGE relationship creation failed for % -> %: %', source_name, target_name, SQLERRM;
            END;
            $$ LANGUAGE plpgsql;
        ");

        // AGE-First Architecture: No orphaned data cleanup needed
        // AGE handles all data integrity automatically

        DB::statement("
            CREATE OR REPLACE FUNCTION delete_draft_graph_data(draft_id_param text)
            RETURNS integer AS $$
            DECLARE
                deleted_count integer := 0;
                original_search_path text;
            BEGIN
                -- AGE-First Architecture: Require AGE to be available
                -- Store original search path
                SELECT current_setting('search_path') INTO original_search_path;
                
                -- Load AGE extension - required for all operations
                LOAD 'age';
                
                -- Set search path to include ag_catalog
                PERFORM set_config('search_path', 'ag_catalog, ' || original_search_path, false);
                
                -- Delete all AGE vertices and their relationships for this draft
                SELECT (ag_catalog.cypher('novel_pipeline_graph', 
                    'MATCH (n {draft_id: \$draft_id}) DETACH DELETE n RETURN count(n)',
                    jsonb_build_object('draft_id', draft_id_param)::agtype
                ) -> 0::int -> 0::int)::integer INTO deleted_count;
                
                -- Restore original search path
                PERFORM set_config('search_path', original_search_path, false);
                
                RETURN deleted_count;
                
            EXCEPTION
                WHEN OTHERS THEN
                    -- Restore original search path on error
                    PERFORM set_config('search_path', original_search_path, false);
                    RAISE EXCEPTION 'AGE draft cleanup failed for %: %', draft_id_param, SQLERRM;
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
                cypher_query text;
                original_search_path text;
            BEGIN
                -- AGE-First Architecture: Require AGE to be available
                -- Store original search path
                SELECT current_setting('search_path') INTO original_search_path;
                
                -- Load AGE extension - required for all operations
                LOAD 'age';
                
                -- Set search path to include ag_catalog
                PERFORM set_config('search_path', 'ag_catalog, ' || original_search_path, false);
                
                -- Build Cypher query for character relationships
                cypher_query := format('MATCH (a:Character)-[r]->(b:Character) 
                                       WHERE a.draft_id = ''%s'' 
                                       RETURN a.name, type(r), b.name, r.scene_id, r.properties', 
                                     draft_id_param);
                
                -- Return results from AGE with proper type casting
                RETURN QUERY
                SELECT 
                    (result.source_name#>>'{}')::text,
                    (result.rel_type#>>'{}')::text,
                    (result.target_name#>>'{}')::text,
                    (result.scene_id#>>'{}')::bigint,
                    (result.props#>>'{}')::jsonb
                FROM cypher('novel_pipeline_graph', cypher_query) 
                AS result(source_name agtype, rel_type agtype, target_name agtype, scene_id agtype, props agtype);
                
                -- Restore original search path
                PERFORM set_config('search_path', original_search_path, false);
                
            EXCEPTION
                WHEN OTHERS THEN
                    -- Restore original search path on error
                    PERFORM set_config('search_path', original_search_path, false);
                    RAISE EXCEPTION 'AGE character relationship query failed for draft %: %', draft_id_param, SQLERRM;
            END;
            $$ LANGUAGE plpgsql;
        ");
    }

    public function down(): void
    {
        // Drop AGE-only functions
        DB::statement('DROP FUNCTION IF EXISTS create_novel_vertex');
        DB::statement('DROP FUNCTION IF EXISTS create_novel_relationship');
        DB::statement('DROP FUNCTION IF EXISTS get_draft_character_relationships');
        DB::statement('DROP FUNCTION IF EXISTS delete_draft_graph_data');

        // Remove added columns
        Schema::table('scenes', function (Blueprint $table) {
            $table->dropColumn(['graph_analyzed', 'graph_last_updated']);
        });

        Schema::table('drafts', function (Blueprint $table) {
            $table->dropColumn(['graph_initialized', 'graph_last_updated']);
        });

        // AGE-First Architecture: No relational backup tables to drop
    }
};
-- =============================================================================
-- Novel Pipeline Graph Schema for Apache AGE
-- =============================================================================
-- This script creates the proper AGE graph schema for novel pipeline operations
-- Using AGE's native vertex and edge labels for true graph database functionality

-- Ensure AGE is loaded and graph exists
DO $$
BEGIN
    -- Set search path to include AGE catalog
    SET search_path = ag_catalog, "$user", public;
    
    -- Verify graph exists (created in 01-init-age.sql)
    IF NOT EXISTS (SELECT 1 FROM ag_graph WHERE name = 'novel_pipeline_graph') THEN
        PERFORM create_graph('novel_pipeline_graph');
        RAISE NOTICE 'Created novel_pipeline_graph';
    END IF;
    
    RAISE NOTICE 'Novel pipeline graph schema initialization started';
    
EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'Failed to verify graph: %', SQLERRM;
END
$$;

-- =============================================================================
-- Create Vertex Labels (Node Types)
-- =============================================================================

-- Characters in the novel
SELECT create_vlabel('novel_pipeline_graph', 'Character');

-- Locations/Settings in the novel  
SELECT create_vlabel('novel_pipeline_graph', 'Location');

-- Items/Objects in the novel
SELECT create_vlabel('novel_pipeline_graph', 'Item');

-- Themes/Concepts in the novel
SELECT create_vlabel('novel_pipeline_graph', 'Theme');

-- Plot points/Events in the novel
SELECT create_vlabel('novel_pipeline_graph', 'PlotPoint');

-- Scenes (bridge to relational data)
SELECT create_vlabel('novel_pipeline_graph', 'Scene');

-- Drafts (bridge to relational data)
SELECT create_vlabel('novel_pipeline_graph', 'Draft');

-- Interaction Records (individual character interactions that build up relationships)
SELECT create_vlabel('novel_pipeline_graph', 'Interaction');

-- =============================================================================
-- Create Edge Labels (Relationship Types)
-- =============================================================================

-- Character relationships
SELECT create_elabel('novel_pipeline_graph', 'APPEARS_IN');
SELECT create_elabel('novel_pipeline_graph', 'INTERACTS_WITH');
SELECT create_elabel('novel_pipeline_graph', 'KNOWS');
SELECT create_elabel('novel_pipeline_graph', 'LOVES');
SELECT create_elabel('novel_pipeline_graph', 'HATES');
SELECT create_elabel('novel_pipeline_graph', 'FOLLOWS');
SELECT create_elabel('novel_pipeline_graph', 'LEADS');

-- Location relationships
SELECT create_elabel('novel_pipeline_graph', 'LOCATED_IN');
SELECT create_elabel('novel_pipeline_graph', 'TRAVELS_TO');
SELECT create_elabel('novel_pipeline_graph', 'CONTAINS');

-- Item relationships
SELECT create_elabel('novel_pipeline_graph', 'OWNS');
SELECT create_elabel('novel_pipeline_graph', 'USES');
SELECT create_elabel('novel_pipeline_graph', 'FINDS');
SELECT create_elabel('novel_pipeline_graph', 'LOSES');
SELECT create_elabel('novel_pipeline_graph', 'GIVES');
SELECT create_elabel('novel_pipeline_graph', 'TAKES');

-- Theme relationships
SELECT create_elabel('novel_pipeline_graph', 'REPRESENTS');
SELECT create_elabel('novel_pipeline_graph', 'SYMBOLIZES');
SELECT create_elabel('novel_pipeline_graph', 'EMBODIES');

-- Plot relationships
SELECT create_elabel('novel_pipeline_graph', 'CAUSES');
SELECT create_elabel('novel_pipeline_graph', 'LEADS_TO');
SELECT create_elabel('novel_pipeline_graph', 'PREVENTS');
SELECT create_elabel('novel_pipeline_graph', 'RESOLVES');
SELECT create_elabel('novel_pipeline_graph', 'CONFLICTS_WITH');

-- Scene relationships
SELECT create_elabel('novel_pipeline_graph', 'HAPPENS_IN');
SELECT create_elabel('novel_pipeline_graph', 'PRECEDES');
SELECT create_elabel('novel_pipeline_graph', 'FOLLOWS_FROM');

-- Draft relationships
SELECT create_elabel('novel_pipeline_graph', 'BELONGS_TO');
SELECT create_elabel('novel_pipeline_graph', 'DERIVED_FROM');

-- Interaction relationships (link interactions to character relationships)
SELECT create_elabel('novel_pipeline_graph', 'HAS_INTERACTION');
SELECT create_elabel('novel_pipeline_graph', 'INVOLVES');

-- =============================================================================
-- Create Indexes for Performance (AGE manages its own internal indexes)
-- =============================================================================

-- Note: Apache AGE manages its own internal indexing structures
-- We rely on AGE's built-in indexing for graph operations
-- Custom indexes should be created on our metadata tables instead (done in Laravel migrations)

DO $$
BEGIN
    RAISE NOTICE 'AGE internal indexes are managed automatically by the extension';
END $$;

-- =============================================================================
-- Create Helper Functions
-- =============================================================================

-- Function to get vertex by draft_id and name
CREATE OR REPLACE FUNCTION get_novel_vertex_by_draft_and_name(
    draft_id_param text,
    name_param text,
    label_param text DEFAULT 'Character'
) RETURNS ag_catalog.agtype AS $$
DECLARE
    query_string text;
BEGIN
    query_string := format('MATCH (v:%I) WHERE v.draft_id = $draft_id_param AND v.name = $name_param RETURN v', label_param);
    RETURN ag_catalog.cypher('novel_pipeline_graph', query_string, jsonb_build_object('draft_id_param', draft_id_param, 'name_param', name_param)::agtype)::ag_catalog.agtype;
END;
$$ LANGUAGE plpgsql;

-- Function to create or update vertex
CREATE OR REPLACE FUNCTION upsert_novel_vertex(
    draft_id_param text,
    name_param text,
    label_param text,
    properties_param jsonb DEFAULT '{}'::jsonb
) RETURNS ag_catalog.agtype AS $$
DECLARE
    full_props jsonb;
BEGIN
    -- Merge draft_id and name into properties
    full_props := properties_param || jsonb_build_object('draft_id', draft_id_param, 'name', name_param);
    
    RETURN ag_catalog.cypher('novel_pipeline_graph', 
        format('MERGE (v:%I {draft_id: $draft_id, name: $name}) 
                ON CREATE SET v += $props 
                ON MATCH SET v += $props 
                RETURN v', label_param),
        jsonb_build_object('draft_id', draft_id_param, 'name', name_param, 'props', full_props)::agtype
    )::ag_catalog.agtype;
END;
$$ LANGUAGE plpgsql;

-- Function to create relationship between vertices
CREATE OR REPLACE FUNCTION create_novel_relationship(
    draft_id_param text,
    source_name text,
    source_label text,
    target_name text,
    target_label text,
    relationship_label text,
    properties_param jsonb DEFAULT '{}'::jsonb
) RETURNS ag_catalog.agtype AS $$
BEGIN
    RETURN ag_catalog.cypher('novel_pipeline_graph', 
        format('MATCH (a:%I {draft_id: $draft_id, name: $source_name})
                MATCH (b:%I {draft_id: $draft_id, name: $target_name})
                MERGE (a)-[r:%I]->(b)
                ON CREATE SET r += $props
                ON MATCH SET r += $props
                RETURN r', source_label, target_label, relationship_label),
        jsonb_build_object('draft_id', draft_id_param, 'source_name', source_name, 'target_name', target_name, 'props', properties_param)::agtype
    )::ag_catalog.agtype;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Grant Permissions
-- =============================================================================

-- Grant necessary permissions for AGE graph operations
GRANT USAGE ON SCHEMA ag_catalog TO PUBLIC;
GRANT SELECT ON ALL TABLES IN SCHEMA ag_catalog TO PUBLIC;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA ag_catalog TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_novel_vertex_by_draft_and_name TO PUBLIC;
GRANT EXECUTE ON FUNCTION upsert_novel_vertex TO PUBLIC;
GRANT EXECUTE ON FUNCTION create_novel_relationship TO PUBLIC;

-- =============================================================================
-- Verification and Completion
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '=== NOVEL PIPELINE GRAPH SCHEMA COMPLETE ===';
    RAISE NOTICE 'Vertex Labels: Character, Location, Item, Theme, PlotPoint, Scene, Draft';
    RAISE NOTICE 'Edge Labels: APPEARS_IN, INTERACTS_WITH, LOCATED_IN, OWNS, USES, CAUSES, etc.';
    RAISE NOTICE 'Helper Functions: get_novel_vertex_by_draft_and_name, upsert_novel_vertex, create_novel_relationship';
    RAISE NOTICE 'Ready for graph-based novel analysis operations';
END
$$;
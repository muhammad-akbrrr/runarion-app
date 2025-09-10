-- =============================================================================
-- Apache AGE Extension Initialization Script
-- =============================================================================
-- This script initializes the Apache AGE extension for graph database functionality
-- Required for novel pipeline graph operations in Runarion

-- Create AGE extension with enhanced error handling
DO $$ 
BEGIN
    -- Check if AGE extension is available
    IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'age') THEN
        -- Create the extension if it doesn't exist
        CREATE EXTENSION IF NOT EXISTS age;
        
        -- Load AGE library (required per official documentation)
        LOAD 'age';
        
        -- Apply search path to current session only (no database-level persistence)
        SET search_path = ag_catalog, "$user", public;
        
        -- Create graph for novel pipeline operations (with error handling)
        BEGIN
            PERFORM ag_catalog.create_graph('novel_pipeline_graph');
            RAISE NOTICE 'Created graph: novel_pipeline_graph';
        EXCEPTION
            WHEN duplicate_object THEN
                RAISE NOTICE 'Graph novel_pipeline_graph already exists, skipping creation';
            WHEN OTHERS THEN
                RAISE WARNING 'Failed to create graph: %', SQLERRM;
                -- Continue anyway, graph might be created by migration
        END;
        
        -- Create AGE session initialization function for runtime use
        CREATE OR REPLACE FUNCTION initialize_age_session()
        RETURNS boolean AS $init$
        DECLARE
            original_search_path text;
        BEGIN
            -- Store original search path for restoration
            SELECT current_setting('search_path') INTO original_search_path;
            
            -- Set search path to include ag_catalog for this session only
            PERFORM set_config('search_path', 'ag_catalog, ' || original_search_path, false);
            
            -- Test AGE functionality using correct method
            PERFORM (SELECT extversion FROM pg_extension WHERE extname = 'age');
            
            -- Verify graph exists
            IF NOT EXISTS (SELECT 1 FROM ag_catalog.ag_graph WHERE name = 'novel_pipeline_graph') THEN
                PERFORM ag_catalog.create_graph('novel_pipeline_graph');
            END IF;
            
            RETURN true;
        EXCEPTION
            WHEN OTHERS THEN
                -- Restore original search path on error
                BEGIN
                    PERFORM set_config('search_path', original_search_path, false);
                EXCEPTION
                    WHEN OTHERS THEN
                        -- If restoration fails, log but continue
                        RAISE WARNING 'Failed to restore search path after AGE error';
                END;
                
                RAISE WARNING 'AGE session initialization failed: %', SQLERRM;
                RETURN false;
        END;
        $init$ LANGUAGE plpgsql;
        
        RAISE NOTICE 'Apache AGE extension initialized successfully';
        RAISE NOTICE 'AGE session initialization function created';
        RAISE NOTICE 'Note: AGE requires session-level search path configuration';
        
    ELSE
        RAISE WARNING 'Apache AGE extension is not available - graph functionality will be disabled';
    END IF;
    
EXCEPTION 
    WHEN OTHERS THEN
        RAISE WARNING 'Failed to initialize Apache AGE extension: %', SQLERRM;
        RAISE WARNING 'Graph functionality will be disabled';
END
$$;

-- Verify AGE installation with comprehensive testing
DO $$
DECLARE
    age_version_info text;
    graph_exists boolean := false;
BEGIN
    -- Check if AGE extension is properly loaded
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'age') THEN
        RAISE NOTICE 'AGE extension verification: SUCCESS - extension loaded';
        
        -- Test AGE functions are available
        BEGIN
            SELECT extversion INTO age_version_info FROM pg_extension WHERE extname = 'age';
            RAISE NOTICE 'AGE version: %', age_version_info;
            
            -- Test graph operations
            SELECT EXISTS (
                SELECT 1 FROM ag_catalog.ag_graph WHERE name = 'novel_pipeline_graph'
            ) INTO graph_exists;
            
            IF graph_exists THEN
                RAISE NOTICE 'AGE graph verification: SUCCESS - novel_pipeline_graph exists';
                
                -- Test basic cypher operations
                PERFORM ag_catalog.cypher('novel_pipeline_graph', $cypher$
                    CREATE (test:TestNode {name: 'age_init_test', created_at: timestamp()})
                    RETURN test
                $cypher$);
                
                PERFORM ag_catalog.cypher('novel_pipeline_graph', $cypher$
                    MATCH (test:TestNode {name: 'age_init_test'})
                    DELETE test
                $cypher$);
                
                RAISE NOTICE 'AGE cypher operations verification: SUCCESS';
            ELSE
                RAISE WARNING 'AGE graph verification: FAILED - novel_pipeline_graph not found';
            END IF;
            
        EXCEPTION 
            WHEN OTHERS THEN
                RAISE WARNING 'AGE function verification failed: %', SQLERRM;
        END;
        
    ELSE
        RAISE WARNING 'AGE extension verification: FAILED - extension not found';
    END IF;
    
EXCEPTION 
    WHEN OTHERS THEN
        RAISE WARNING 'AGE extension verification failed: %', SQLERRM;
END
$$;

-- Grant necessary permissions for AGE functions
GRANT USAGE ON SCHEMA ag_catalog TO PUBLIC;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA ag_catalog TO PUBLIC;

-- AGE version can be checked via: SELECT * FROM pg_extension WHERE extname = 'age';

-- Log completion
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'age') THEN
        RAISE NOTICE '=== AGE INITIALIZATION COMPLETE ===';
        RAISE NOTICE 'Available graphs: novel_pipeline_graph';
        RAISE NOTICE 'Ready for graph operations';
    ELSE
        RAISE NOTICE '=== AGE INITIALIZATION SKIPPED ===';
        RAISE NOTICE 'AGE extension not available - using standard PostgreSQL only';
    END IF;
END
$$;
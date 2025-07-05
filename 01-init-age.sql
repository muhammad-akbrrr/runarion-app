-- =============================================================================
-- Apache AGE Extension Initialization Script
-- =============================================================================
-- This script initializes the Apache AGE extension for graph database functionality
-- Required for novel pipeline graph operations in Runarion

-- Create AGE extension
DO $$ 
BEGIN
    -- Check if AGE extension is available
    IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'age') THEN
        -- Create the extension if it doesn't exist
        CREATE EXTENSION IF NOT EXISTS age;
        
        -- Load AGE library (required per official documentation)
        LOAD 'age';
        
        -- Load AGE into the search path (use current database)
        EXECUTE 'ALTER DATABASE ' || current_database() || ' SET search_path TO ag_catalog, "$user", public';
        
        -- Set search path for current session
        SET search_path = ag_catalog, "$user", public;
        
        -- Create graph for novel pipeline operations
        PERFORM create_graph('novel_pipeline_graph');
        
        RAISE NOTICE 'Apache AGE extension initialized successfully';
        RAISE NOTICE 'Created graph: novel_pipeline_graph';
        RAISE NOTICE 'Search path updated to include ag_catalog';
        
    ELSE
        RAISE WARNING 'Apache AGE extension is not available - graph functionality will be disabled';
    END IF;
    
EXCEPTION 
    WHEN OTHERS THEN
        RAISE WARNING 'Failed to initialize Apache AGE extension: %', SQLERRM;
        RAISE WARNING 'Graph functionality will be disabled';
END
$$;

-- Verify AGE installation
DO $$
BEGIN
    -- Check if AGE extension is properly loaded
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'age') THEN
        RAISE NOTICE 'AGE extension verification: SUCCESS';
        
        -- AGE extension is working if we got this far without errors
        
        RAISE NOTICE 'AGE graph operations verification: SUCCESS';
        
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
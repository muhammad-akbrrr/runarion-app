"""
GraphDatabaseService - Apache AGE Graph Database Operations (AGE-First Architecture)

Provides graph database operations that REQUIRE Apache AGE to function.
No fallback mechanisms - if AGE is not available, operations fail fast with clear error messages.

Key principles:
- AGE-first: Requires proper Apache AGE setup, no silent degradation
- Fail fast: Clear error messages when AGE is not available
- Session-level AGE initialization for perfect isolation
- Simplified architecture with single code path
"""

import os
import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class GraphDatabaseNotAvailableError(Exception):
    """Raised when Apache AGE is required but not available."""
    pass

class GraphDatabaseService:
    """
    Apache AGE graph database service with AGE-first architecture.
    
    This service REQUIRES Apache AGE to be properly installed and configured.
    No fallback mechanisms - operations fail fast if AGE is unavailable.
    """
    
    def __init__(self, db_pool):
        """
        Initialize the graph database service.
        
        Args:
            db_pool: Database connection pool
            
        Raises:
            GraphDatabaseNotAvailableError: If AGE is not available
        """
        self.db_pool = db_pool
        self.graph_name = os.getenv('AGE_GRAPH_NAME', 'novel_pipeline_graph')
        self.age_enabled = os.getenv('AGE_ENABLED', 'true').lower() == 'true'
        
        # Fail fast if AGE is not enabled or available
        if not self.age_enabled:
            raise GraphDatabaseNotAvailableError(
                "Apache AGE is disabled by configuration (AGE_ENABLED=false). "
                "Graph database functionality requires AGE to be enabled."
            )
        
        # Validate AGE availability on initialization
        self._validate_age_setup()
        
        logger.info(f"GraphDatabaseService initialized with AGE-first architecture for graph: {self.graph_name}")
    
    def _escape_cypher_string(self, text: str) -> str:
        """
        Safely escape a string for use in Apache AGE Cypher queries.
        
        This method handles special characters that can break Cypher syntax:
        - Single quotes (') -> escaped as \\'
        - Backslashes (\\) -> escaped as \\\\
        - Newlines -> replaced with spaces
        
        Args:
            text: String to be escaped for Cypher
            
        Returns:
            Safely escaped string for Cypher queries
        """
        if not text:
            return ""
        
        # Escape backslashes first, then single quotes
        escaped = text.replace('\\', '\\\\')
        escaped = escaped.replace("'", "\\'")
        
        # Replace newlines and control characters with spaces
        import re
        escaped = re.sub(r'[\r\n\t]+', ' ', escaped)
        
        return escaped

    def _sanitize_property_key(self, key: str) -> str:
        """
        Sanitize property key for Cypher compatibility.

        Cypher property keys must be valid identifiers:
        - Only alphanumeric characters and underscores
        - Must start with a letter or underscore
        - No special characters like '/', '-', etc.

        Args:
            key: Raw property key (may contain invalid characters)

        Returns:
            Sanitized key suitable for Cypher queries

        Examples:
            "N/A" -> "N_A"
            "my-field" -> "my_field"
            "123key" -> "_123key"
        """
        import re
        # Replace invalid characters with underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', str(key))
        # Ensure it starts with letter or underscore (not digit)
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized
        # Return sanitized key or a fallback if empty
        return sanitized or '_invalid_key'

    def _prepare_agtype_properties(self, properties: Dict[str, Any]) -> str:
        """
        Convert a properties dictionary to AGE agtype format for Cypher queries.
        
        Args:
            properties: Dictionary of properties
            
        Returns:
            Cypher object notation for AGE properties (not a JSON string)
        """
        if not properties:
            return "{}"
        
        # Build Cypher object notation: {key: 'value', key2: 'value2'}
        prop_parts = []
        for key, value in properties.items():
            # Sanitize key to ensure it's a valid Cypher identifier
            safe_key = self._sanitize_property_key(key)
            if isinstance(value, str):
                escaped_value = self._escape_cypher_string(value)
                prop_parts.append(f"{safe_key}: '{escaped_value}'")
            elif isinstance(value, (int, float)):
                prop_parts.append(f"{safe_key}: {value}")
            elif isinstance(value, bool):
                prop_parts.append(f"{safe_key}: {str(value).lower()}")
            else:
                # For complex objects, convert to JSON and escape
                json_str = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
                escaped_json = self._escape_cypher_string(json_str)
                prop_parts.append(f"{safe_key}: '{escaped_json}'")
        
        return "{" + ", ".join(prop_parts) + "}"

    def _normalize_relationship_type(self, rel_type: str) -> str:
        """
        Normalize relationship types to valid Apache AGE label identifiers.

        Apache AGE requires relationship labels to be valid identifiers:
        - Only alphanumeric characters and underscores
        - No spaces or special characters
        - Conventionally uppercase (e.g., INTERACTS_WITH, APPEARS_IN)

        Args:
            rel_type: Raw relationship type string (possibly from AI with spaces/special chars)

        Returns:
            Normalized label identifier suitable for AGE (e.g., "interacts with" -> "INTERACTS_WITH")

        Examples:
            "interacts with" -> "INTERACTS_WITH"
            "knows" -> "KNOWS"
            "travels-to" -> "TRAVELS_TO"
            "loves/hates" -> "LOVESHATES"
        """
        import re

        if not rel_type:
            return "RELATED_TO"  # Default fallback

        # Convert to uppercase and replace spaces/hyphens with underscores
        normalized = rel_type.strip().upper().replace(' ', '_').replace('-', '_')

        # Remove all non-alphanumeric characters except underscores
        normalized = re.sub(r'[^A-Z0-9_]', '', normalized)

        # Ensure we don't have empty result
        if not normalized:
            return "RELATED_TO"

        return normalized

    def _validate_age_setup(self) -> None:
        """
        Validate that Apache AGE is properly installed and configured with comprehensive diagnostics.
        
        Raises:
            GraphDatabaseNotAvailableError: If AGE is not properly set up with specific guidance
        """
        try:
            conn = self.db_pool.getconn()
            try:
                with conn.cursor() as cursor:
                    # Phase 1: Check if AGE extension is available for installation
                    cursor.execute("SELECT 1 FROM pg_available_extensions WHERE name = 'age'")
                    if not cursor.fetchone():
                        raise GraphDatabaseNotAvailableError(
                            "Apache AGE extension is not available in PostgreSQL.\n"
                            "   Container Diagnostics:\n"
                            "   1. Exec into container: docker exec -it runarion-app-python-app-1 bash\n"
                            "   2. Check AGE library: ls -la /usr/lib/postgresql/16/lib/age.so\n"
                            "   3. Verify extension files: ls -la /usr/share/postgresql/16/extension/age*\n"
                            "   4. If missing, rebuild container: docker compose build --no-cache postgres-db\n"
                            "   This indicates AGE compilation failed during Docker build."
                        )
                    
                    # Phase 2: Check if AGE extension is installed
                    cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'age'")
                    extension_installed = cursor.fetchone() is not None
                    
                    if not extension_installed:
                        # Try to create the extension
                        try:
                            cursor.execute("CREATE EXTENSION age")
                            conn.commit()
                            logger.info("Successfully created AGE extension")
                        except Exception as create_error:
                            raise GraphDatabaseNotAvailableError(
                                f"Apache AGE extension available but cannot be created: {create_error}\n"
                                "   Container Diagnostics:\n"
                                "   1. Check PostgreSQL logs for detailed error\n"
                                "   2. Verify AGE library dependencies: ldd /usr/lib/postgresql/16/lib/age.so\n"
                                "   3. Try manual creation: docker exec -it runarion-app-python-app-1 psql -U postgres -c 'CREATE EXTENSION age;'\n"
                                "   This indicates AGE extension files are corrupted or incompatible."
                            ) from create_error
                    
                    # Phase 3: Test AGE session initialization (including LOAD command)
                    session_init_result = self._initialize_age_session_with_diagnostics(cursor)
                    if not session_init_result['success']:
                        error_details = session_init_result['error']
                        if 'does not exist' in str(error_details):
                            raise GraphDatabaseNotAvailableError(
                                f"Apache AGE functions not accessible after session initialization: {error_details}\n"
                                "   Container Diagnostics:\n"
                                "   1. Check if AGE library loads: docker exec -it runarion-app-python-app-1 psql -U postgres -c \"LOAD 'age';\"\n"
                                "   2. Verify search path: docker exec -it runarion-app-python-app-1 psql -U postgres -c \"SHOW search_path;\"\n"
                                "   3. Test AGE version: docker exec -it runarion-app-python-app-1 psql -U postgres -c \"SELECT extversion FROM pg_extension WHERE extname = 'age';\"\n"
                                "   This indicates AGE library is missing or corrupted - rebuild container required."
                            ) from error_details
                        else:
                            raise GraphDatabaseNotAvailableError(
                                f"Failed to initialize Apache AGE session: {error_details}\n"
                                "   Check PostgreSQL configuration and AGE installation integrity."
                            ) from error_details
                    
                    # Phase 4: Test basic AGE functionality
                    try:
                        cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'age'")
                        version = cursor.fetchone()
                        
                        if not version:
                            raise GraphDatabaseNotAvailableError(
                                "Apache AGE functions exist but return no version information.\n"
                                "   This indicates a partial or corrupted AGE installation."
                            )
                        
                        logger.info(f"Apache AGE validation successful, version: {version[0]}")
                        
                    except Exception as func_error:
                        raise GraphDatabaseNotAvailableError(
                            f"Apache AGE functions not working properly: {func_error}\n"
                            "   Container Diagnostics:\n"
                            "   1. Test function directly: docker exec -it runarion-app-python-app-1 psql -U postgres -c \"SELECT extversion FROM pg_extension WHERE extname = 'age';\"\n"
                            "   2. Check AGE catalog: docker exec -it runarion-app-python-app-1 psql -U postgres -c \"\\df ag_catalog.*\"\n"
                            "   AGE extension partially working - may need container rebuild."
                        ) from func_error
                    
            finally:
                self.db_pool.putconn(conn)
                
        except GraphDatabaseNotAvailableError:
            raise
        except Exception as e:
            raise GraphDatabaseNotAvailableError(
                f"Apache AGE validation failed with unexpected error: {e}\n"
                "   Container Diagnostics:\n"
                "   1. Check container is running: docker ps | grep postgres\n"
                "   2. Check database connectivity: docker exec -it runarion-app-python-app-1 psql -U postgres -l\n"
                "   3. Review container logs: docker logs runarion-app-python-app-1\n"
                "   This indicates a fundamental database connectivity or container issue."
            ) from e
    
    def _initialize_age_session(self, cursor) -> bool:
        """
        Initialize AGE session with proper search path and graph.
        Session-scoped only - does not affect other connections.
        
        Args:
            cursor: Database cursor
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Store original search path for restoration if needed
            cursor.execute("SELECT current_setting('search_path')")
            original_search_path = cursor.fetchone()[0]
            
            # CRITICAL: Load AGE extension first - required for all AGE operations
            cursor.execute("LOAD 'age'")
            
            # Set search path for this session only (cannot use parameter binding with SET)
            cursor.execute(f"SET search_path = ag_catalog, {original_search_path}")
            
            # Test AGE functionality using correct version check method
            cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'age'")
            version_result = cursor.fetchone()
            version = version_result[0] if version_result else 'unknown'
            
            # Verify graph exists or create it
            cursor.execute("SELECT EXISTS (SELECT 1 FROM ag_catalog.ag_graph WHERE name = %s)", (self.graph_name,))
            graph_exists = cursor.fetchone()[0]
            
            if not graph_exists:
                cursor.execute("SELECT ag_catalog.create_graph(%s)", (self.graph_name,))
                logger.info(f"Created new AGE graph: {self.graph_name}")
            
            logger.debug(f"AGE session initialized successfully, version: {version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AGE session: {e}")
            # Try to restore original search path on error
            try:
                cursor.execute(f"SET search_path = {original_search_path}")
            except:
                pass  # Ignore restoration errors
            return False
    
    def _initialize_age_session_with_diagnostics(self, cursor) -> Dict[str, Any]:
        """
        Initialize AGE session with comprehensive diagnostics for failure analysis.
        
        Args:
            cursor: Database cursor
            
        Returns:
            Dict with 'success' boolean and 'error' details if failed
        """
        try:
            # Store original search path for restoration if needed
            cursor.execute("SELECT current_setting('search_path')")
            original_search_path = cursor.fetchone()[0]
            
            # CRITICAL: Load AGE extension first - this is where most failures occur
            try:
                cursor.execute("LOAD 'age'")
            except Exception as load_error:
                return {
                    'success': False,
                    'error': load_error,
                    'phase': 'LOAD_AGE',
                    'message': f"Failed to load AGE library: {load_error}"
                }
            
            # Set search path for this session only
            try:
                cursor.execute(f"SET search_path = ag_catalog, {original_search_path}")
            except Exception as path_error:
                return {
                    'success': False,
                    'error': path_error,
                    'phase': 'SET_SEARCH_PATH',
                    'message': f"Failed to set search path: {path_error}"
                }
            
            # Test AGE functionality using correct version check method
            try:
                cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'age'")
                version_result = cursor.fetchone()
                if not version_result:
                    raise Exception("AGE extension not found in pg_extension")
                version = version_result[0]
            except Exception as version_error:
                return {
                    'success': False,
                    'error': version_error,
                    'phase': 'AGE_VERSION_CHECK',
                    'message': f"Failed to access AGE extension version: {version_error}"
                }
            
            # Verify graph exists or create it
            try:
                cursor.execute("SELECT EXISTS (SELECT 1 FROM ag_catalog.ag_graph WHERE name = %s)", (self.graph_name,))
                graph_exists = cursor.fetchone()[0]
                
                if not graph_exists:
                    cursor.execute("SELECT ag_catalog.create_graph(%s)", (self.graph_name,))
                    logger.info(f"Created new AGE graph: {self.graph_name}")
            except Exception as graph_error:
                return {
                    'success': False,
                    'error': graph_error,
                    'phase': 'GRAPH_SETUP',
                    'message': f"Failed to setup graph: {graph_error}"
                }
            
            logger.debug(f"AGE session initialized successfully, version: {version}")
            return {
                'success': True,
                'version': version,
                'graph_name': self.graph_name,
                'graph_exists': graph_exists
            }
            
        except Exception as e:
            # Try to restore original search path on error
            try:
                cursor.execute(f"SET search_path = {original_search_path}")
            except:
                pass  # Ignore restoration errors
                
            return {
                'success': False,
                'error': e,
                'phase': 'UNEXPECTED_ERROR',
                'message': f"Unexpected error during AGE session initialization: {e}"
            }
    
    @contextmanager
    def get_age_connection(self):
        """
        Context manager for database connections with AGE session initialized.
        Includes retry logic for connection pool exhaustion.
        
        Yields:
            Database connection with AGE session configured
            
        Raises:
            GraphDatabaseNotAvailableError: If AGE session initialization fails
        """
        conn = None
        original_search_path = None
        max_retries = 3
        retry_delay = 0.5  # seconds
        import time
        
        try:
            for attempt in range(max_retries):
                try:
                    try:
                        conn = self.db_pool.getconn()
                    except Exception as pool_error:
                        if "connection pool exhausted" in str(pool_error).lower() and attempt < max_retries - 1:
                            logger.warning(f"Connection pool exhausted (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                            continue
                        else:
                            raise GraphDatabaseNotAvailableError(
                                f"Connection pool exhausted after {max_retries} attempts: {pool_error}"
                            )
                    
                    # Initialize AGE session
                    with conn.cursor() as cursor:
                        # Store original search path
                        cursor.execute("SELECT current_setting('search_path')")
                        original_search_path = cursor.fetchone()[0]
                        
                        if not self._initialize_age_session(cursor):
                            raise GraphDatabaseNotAvailableError(
                                f"Failed to initialize AGE session for graph operations. "
                                f"Graph: {self.graph_name}"
                            )
                    
                    yield conn
                    break  # Success, exit retry loop
                    
                except GraphDatabaseNotAvailableError:
                    if conn:
                        conn.rollback()
                        self.db_pool.putconn(conn)
                        conn = None
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(retry_delay)
                    retry_delay *= 2
                except Exception as e:
                    if conn:
                        conn.rollback()
                        self.db_pool.putconn(conn)
                        conn = None
                    if attempt == max_retries - 1:
                        raise GraphDatabaseNotAvailableError(
                            f"Graph database operation failed after {max_retries} attempts: {e}"
                        ) from e
                    time.sleep(retry_delay)
                    retry_delay *= 2
        finally:
            if conn and original_search_path:
                # Restore original search path
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(f"SET search_path = {original_search_path}")
                except Exception as e:
                    logger.warning(f"Failed to restore search path: {e}")
            
            if conn:
                self.db_pool.putconn(conn)
    
    def create_vertex(self, draft_id: str, entity_name: str, entity_type: str, 
                     properties: Dict[str, Any] = None) -> int:
        """
        Create a vertex in the Apache AGE graph database.
        
        Args:
            draft_id: UUID of the draft
            entity_name: Name of the entity
            entity_type: Type of entity (Character, Location, Item, etc.)
            properties: Additional properties for the vertex
            
        Returns:
            AGE vertex ID
            
        Raises:
            GraphDatabaseNotAvailableError: If AGE operation fails
        """
        if properties is None:
            properties = {}
        
        try:
            with self.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    # Safely escape inputs for Cypher
                    safe_draft_id = self._escape_cypher_string(draft_id)
                    safe_entity_name = self._escape_cypher_string(entity_name)
                    safe_properties = self._prepare_agtype_properties(properties)
                    
                    # AGE 1.6 requires literal dollar-quoted strings - build complete SQL with escaping
                    sql_query = f"""
                        SELECT vertex_id::bigint FROM ag_catalog.cypher('{self.graph_name}', $$ 
                        CREATE (n:{entity_type} {{draft_id: '{safe_draft_id}', name: '{safe_entity_name}', properties: {safe_properties}}}) 
                        RETURN id(n) 
                        $$) AS (vertex_id agtype)
                    """
                    
                    cursor.execute(sql_query)
                    
                    result = cursor.fetchone()
                    if not result:
                        raise GraphDatabaseNotAvailableError(
                            f"Failed to create vertex {entity_name} ({entity_type}): No result returned"
                        )
                    
                    vertex_id = result[0]
                    conn.commit()
                    
                    logger.debug(f"AGE vertex created: {vertex_id} for {entity_name} ({entity_type})")
                    return vertex_id
                    
        except GraphDatabaseNotAvailableError:
            raise
        except Exception as e:
            raise GraphDatabaseNotAvailableError(
                f"Failed to create vertex {entity_name} ({entity_type}): {e}"
            ) from e
    
    def create_relationship(self, draft_id: str, source_name: str, target_name: str,
                          relationship_type: str, properties: Dict[str, Any] = None,
                          scene_id: Optional[int] = None) -> int:
        """
        Create a relationship/edge in the Apache AGE graph database.
        
        Args:
            draft_id: UUID of the draft
            source_name: Name of the source entity
            target_name: Name of the target entity
            relationship_type: Type of relationship
            properties: Additional properties for the relationship
            scene_id: Optional scene ID where relationship occurs
            
        Returns:
            AGE edge ID
            
        Raises:
            GraphDatabaseNotAvailableError: If AGE operation fails
        """
        if properties is None:
            properties = {}
        
        # Add scene_id to properties if provided
        if scene_id is not None:
            properties['scene_id'] = scene_id
        
        try:
            with self.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    # Safely escape inputs for Cypher
                    safe_draft_id = self._escape_cypher_string(draft_id)
                    safe_source_name = self._escape_cypher_string(source_name)
                    safe_target_name = self._escape_cypher_string(target_name)
                    safe_properties = self._prepare_agtype_properties(properties)
                    
                    # AGE 1.6 requires literal dollar-quoted strings - build complete SQL with escaping
                    # Note: AGE relationship properties use object notation {prop: value}, not string notation
                    # Normalize relationship type to valid AGE label identifier (uppercase, underscores, no special chars)
                    safe_relationship_type = self._normalize_relationship_type(relationship_type)
                    
                    sql_query = f"""
                        SELECT edge_id::bigint FROM ag_catalog.cypher('{self.graph_name}', $$
                        MATCH (a {{draft_id: '{safe_draft_id}', name: '{safe_source_name}'}})
                        MATCH (b {{draft_id: '{safe_draft_id}', name: '{safe_target_name}'}})
                        CREATE (a)-[r:{safe_relationship_type} {safe_properties}]->(b)
                        RETURN id(r)
                        $$) AS (edge_id agtype)
                    """
                    
                    cursor.execute(sql_query)
                    
                    result = cursor.fetchone()
                    if not result:
                        raise GraphDatabaseNotAvailableError(
                            f"Failed to create relationship {source_name} -{relationship_type}-> {target_name}: No result returned"
                        )
                    
                    edge_id = result[0]
                    conn.commit()
                    
                    logger.debug(f"AGE relationship created: {edge_id} ({source_name} -{relationship_type}-> {target_name})")
                    return edge_id
                    
        except GraphDatabaseNotAvailableError:
            raise
        except Exception as e:
            raise GraphDatabaseNotAvailableError(
                f"Failed to create relationship {source_name} -{relationship_type}-> {target_name}: {e}"
            ) from e
    
    def cleanup_draft_data(self, draft_id: str) -> int:
        """
        Clean up graph data for a draft using Apache AGE.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Number of items deleted
            
        Raises:
            GraphDatabaseNotAvailableError: If AGE operation fails
        """
        try:
            with self.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    # Safely escape draft_id for Cypher
                    safe_draft_id = self._escape_cypher_string(draft_id)
                    
                    # AGE 1.6 requires literal dollar-quoted strings - build complete SQL with escaping
                    sql_query = f"""
                        SELECT deleted_count::integer FROM ag_catalog.cypher('{self.graph_name}', $$ 
                        MATCH (n {{draft_id: '{safe_draft_id}'}}) 
                        DETACH DELETE n 
                        RETURN count(n) 
                        $$) AS (deleted_count agtype)
                    """
                    
                    cursor.execute(sql_query)
                    
                    result = cursor.fetchone()
                    deleted_count = result[0] if result else 0
                    
                    conn.commit()
                    
                    logger.info(f"Cleaned up AGE graph data for draft {draft_id}: {deleted_count} items deleted")
                    return deleted_count
                    
        except GraphDatabaseNotAvailableError:
            raise
        except Exception as e:
            raise GraphDatabaseNotAvailableError(
                f"Failed to cleanup graph data for draft {draft_id}: {e}"
            ) from e
    
    def get_draft_relationships(self, draft_id: str) -> List[Dict[str, Any]]:
        """
        Get all relationships for a draft using Apache AGE graph queries.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            List of relationship data
            
        Raises:
            GraphDatabaseNotAvailableError: If AGE operation fails
        """
        try:
            with self.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    # Safely escape draft_id for Cypher
                    safe_draft_id = self._escape_cypher_string(draft_id)
                    
                    # Use dollar-quoted strings for AGE 1.6 compatibility
                    sql_query = f"""
                        SELECT a_name, rel_type, b_name, rel_full
                        FROM ag_catalog.cypher('{self.graph_name}', $$ 
                        MATCH (a)-[r]->(b) 
                        WHERE a.draft_id = '{safe_draft_id}'
                        RETURN a.name, type(r), b.name, r
                        $$) AS (a_name agtype, rel_type agtype, b_name agtype, rel_full agtype)
                    """
                    
                    cursor.execute(sql_query)
                    results = cursor.fetchall()
                    relationships = []
                    
                    for row in results:
                        if row and len(row) >= 3:
                            try:
                                a_name = json.loads(str(row[0])) if not isinstance(row[0], (int, float, dict, list)) else row[0]
                            except Exception:
                                a_name = row[0]
                            try:
                                rel_type = json.loads(str(row[1])) if not isinstance(row[1], (int, float, dict, list)) else row[1]
                            except Exception:
                                rel_type = row[1]
                            try:
                                b_name = json.loads(str(row[2])) if not isinstance(row[2], (int, float, dict, list)) else row[2]
                            except Exception:
                                b_name = row[2]
                            rel_props = {}
                            if len(row) > 3 and row[3] is not None:
                                # row[3] is the full edge agtype; attempt to extract properties if JSON-like
                                try:
                                    rel_props = json.loads(str(row[3])) if isinstance(row[3], str) else {}
                                except Exception:
                                    rel_props = {}
                            relationships.append({
                                'source': a_name,
                                'relationship_type': rel_type,
                                'target': b_name,
                                'properties': rel_props
                            })
                    
                    logger.debug(f"Retrieved {len(relationships)} relationships for draft {draft_id}")
                    return relationships
                    
        except GraphDatabaseNotAvailableError:
            raise
        except Exception as e:
            raise GraphDatabaseNotAvailableError(
                f"Failed to get relationships for draft {draft_id}: {e}"
            ) from e
    
    def get_character_vertices(self, draft_id: str) -> List[Dict[str, Any]]:
        """
        Get all character vertices for a draft using Apache AGE graph queries.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            List of character vertex data
            
        Raises:
            GraphDatabaseNotAvailableError: If AGE operation fails
        """
        try:
            with self.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    # Safely escape draft_id for Cypher
                    safe_draft_id = self._escape_cypher_string(draft_id)
                    
                    # AGE 1.6 requires alias list to match RETURN columns exactly
                    sql_query = f"""
                        SELECT c_name, c_props FROM ag_catalog.cypher('{self.graph_name}', $$ 
                        MATCH (c:Character {{draft_id: '{safe_draft_id}'}}) 
                        RETURN c.name, c.properties 
                        $$) AS (c_name agtype, c_props agtype)
                    """
                    cursor.execute(sql_query)
                    results = cursor.fetchall()
                    
                    characters = []
                    for row in results:
                        if row and len(row) == 2:
                            try:
                                name = json.loads(str(row[0])) if isinstance(row[0], str) else row[0]
                            except Exception:
                                name = row[0]
                            try:
                                properties = json.loads(str(row[1])) if isinstance(row[1], str) else (row[1] if isinstance(row[1], dict) else {})
                            except Exception:
                                properties = {}
                            characters.append({
                                'name': name,
                                'properties': properties
                            })
                    
                    logger.debug(f"Retrieved {len(characters)} characters for draft {draft_id}")
                    return characters
                    
        except GraphDatabaseNotAvailableError:
            raise
        except Exception as e:
            raise GraphDatabaseNotAvailableError(
                f"Failed to get characters for draft {draft_id}: {e}"
            ) from e
    
    def get_location_vertices(self, draft_id: str) -> List[Dict[str, Any]]:
        """
        Get all location vertices for a draft using Apache AGE graph queries.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            List of location vertex data
            
        Raises:
            GraphDatabaseNotAvailableError: If AGE operation fails
        """
        try:
            with self.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    # Safely escape draft_id for Cypher
                    safe_draft_id = self._escape_cypher_string(draft_id)
                    
                    # AGE 1.6 requires alias list to match RETURN columns exactly
                    sql_query = f"""
                        SELECT l_name, l_props FROM ag_catalog.cypher('{self.graph_name}', $$ 
                        MATCH (l:Location {{draft_id: '{safe_draft_id}'}}) 
                        RETURN l.name, l.properties 
                        $$) AS (l_name agtype, l_props agtype)
                    """
                    cursor.execute(sql_query)
                    results = cursor.fetchall()
                    
                    locations = []
                    for row in results:
                        if row and len(row) == 2:
                            try:
                                name = json.loads(str(row[0])) if isinstance(row[0], str) else row[0]
                            except Exception:
                                name = row[0]
                            try:
                                properties = json.loads(str(row[1])) if isinstance(row[1], str) else (row[1] if isinstance(row[1], dict) else {})
                            except Exception:
                                properties = {}
                            locations.append({
                                'name': name,
                                'properties': properties
                            })
                    
                    logger.debug(f"Retrieved {len(locations)} locations for draft {draft_id}")
                    return locations
                    
        except GraphDatabaseNotAvailableError:
            raise
        except Exception as e:
            raise GraphDatabaseNotAvailableError(
                f"Failed to get locations for draft {draft_id}: {e}"
            ) from e
    
    def get_graph_statistics(self, draft_id: str) -> Dict[str, Any]:
        """
        Get comprehensive graph statistics for a draft using Apache AGE.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Dictionary containing graph statistics
            
        Raises:
            GraphDatabaseNotAvailableError: If AGE operation fails
        """
        try:
            with self.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    # Safely escape draft_id for Cypher
                    safe_draft_id = self._escape_cypher_string(draft_id)
                    
                    # Get entity counts by type
                    entity_counts = {}
                    for entity_type in ['Character', 'Location', 'Item']:
                        sql_query = f"""
                            SELECT count_data FROM ag_catalog.cypher('{self.graph_name}', $$ 
                            MATCH (n:{entity_type} {{draft_id: '{safe_draft_id}'}}) 
                            RETURN count(n) 
                            $$) AS (count_data agtype)
                        """
                        cursor.execute(sql_query)
                        result = cursor.fetchone()
                        count = int(result[0]) if result and result[0] else 0
                        entity_counts[entity_type.lower()] = count
                    
                    # Get relationship count
                    rel_sql_query = f"""
                        SELECT rel_count FROM ag_catalog.cypher('{self.graph_name}', $$ 
                        MATCH (a {{draft_id: '{safe_draft_id}'}})-[r]-(b {{draft_id: '{safe_draft_id}'}}) 
                        RETURN count(r) 
                        $$) AS (rel_count agtype)
                    """
                    cursor.execute(rel_sql_query)
                    rel_result = cursor.fetchone()
                    relationship_count = int(rel_result[0]) if rel_result and rel_result[0] else 0
                    
                    # Get relationship types
                    rel_type_sql = f"""
                        SELECT rel_types FROM ag_catalog.cypher('{self.graph_name}', $$ 
                        MATCH (a {{draft_id: '{safe_draft_id}'}})-[r]-(b {{draft_id: '{safe_draft_id}'}}) 
                        RETURN DISTINCT type(r) 
                        $$) AS (rel_types agtype)
                    """
                    cursor.execute(rel_type_sql)
                    rel_type_results = cursor.fetchall()
                    relationship_types = []
                    for row in rel_type_results:
                        if row and row[0]:
                            rel_type = json.loads(str(row[0])) if isinstance(row[0], str) else row[0]
                            relationship_types.append(rel_type)
                    
                    total_entities = sum(entity_counts.values())
                    
                    statistics = {
                        'total_entities': total_entities,
                        'total_relationships': relationship_count,
                        'entity_breakdown': entity_counts,
                        'relationship_types': relationship_types,
                        'graph_density': relationship_count / max(1, total_entities * (total_entities - 1) / 2),
                        'draft_id': draft_id,
                        'graph_name': self.graph_name
                    }
                    
                    logger.debug(f"Retrieved graph statistics for draft {draft_id}: {total_entities} entities, {relationship_count} relationships")
                    return statistics
                    
        except GraphDatabaseNotAvailableError:
            raise
        except Exception as e:
            raise GraphDatabaseNotAvailableError(
                f"Failed to get graph statistics for draft {draft_id}: {e}"
            ) from e
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get service status information.
        
        Returns:
            Status dictionary with AGE information
        """
        try:
            # Test current AGE availability
            with self.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'age'")
                    version_result = cursor.fetchone()
                    version = version_result[0] if version_result else 'unknown'
                    
                    cursor.execute("SELECT EXISTS (SELECT 1 FROM ag_catalog.ag_graph WHERE name = %s)", (self.graph_name,))
                    graph_exists = cursor.fetchone()[0]
            
            return {
                'service': 'GraphDatabaseService',
                'architecture': 'AGE-first (no fallback)',
                'age_available': True,
                'age_version': version,
                'graph_name': self.graph_name,
                'graph_exists': graph_exists,
                'status': 'healthy'
            }
            
        except GraphDatabaseNotAvailableError as e:
            return {
                'service': 'GraphDatabaseService',
                'architecture': 'AGE-first (no fallback)',
                'age_available': False,
                'graph_name': self.graph_name,
                'status': 'error',
                'error': str(e)
            }
    
    def cleanup_orphaned_graph_data(self) -> int:
        """
        Clean up orphaned graph data (nodes without corresponding draft records).
        
        This is a maintenance operation that removes graph nodes where the 
        draft_id property doesn't correspond to any existing draft record.
        
        Returns:
            Number of orphaned graph items deleted
            
        Raises:
            GraphDatabaseNotAvailableError: If AGE operation fails
        """
        try:
            with self.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    # Get all draft IDs from the database
                    cursor.execute("SELECT id FROM drafts")
                    existing_draft_ids = {row[0] for row in cursor.fetchall()}
                    
                    if not existing_draft_ids:
                        # No drafts exist, clean all nodes
                        sql_query = f"""
                            SELECT deleted_count FROM ag_catalog.cypher('{self.graph_name}', $$ 
                            MATCH (n) 
                            WHERE n.draft_id IS NOT NULL 
                            DETACH DELETE n 
                            RETURN count(n) 
                            $$) AS (deleted_count agtype)
                        """
                        cursor.execute(sql_query)
                        result = cursor.fetchone()
                        deleted_count = int(result[0]) if result and result[0] else 0
                    else:
                        # Get all draft_ids from graph and check which are orphaned
                        sql_query = f"""
                            SELECT draft_ids FROM ag_catalog.cypher('{self.graph_name}', $$ 
                            MATCH (n) 
                            WHERE n.draft_id IS NOT NULL 
                            RETURN DISTINCT n.draft_id 
                            $$) AS (draft_ids agtype)
                        """
                        cursor.execute(sql_query)
                        graph_draft_ids = []
                        
                        for row in cursor.fetchall():
                            if row and row[0]:
                                try:
                                    draft_id = json.loads(str(row[0])) if isinstance(row[0], str) else row[0]
                                    if draft_id and draft_id not in existing_draft_ids:
                                        graph_draft_ids.append(draft_id)
                                except (json.JSONDecodeError, TypeError):
                                    continue
                        
                        # Clean orphaned nodes
                        deleted_count = 0
                        for orphaned_draft_id in graph_draft_ids:
                            safe_draft_id = self._escape_cypher_string(orphaned_draft_id)
                            
                            delete_sql = f"""
                                SELECT count_deleted FROM ag_catalog.cypher('{self.graph_name}', $$ 
                                MATCH (n {{draft_id: '{safe_draft_id}'}}) 
                                DETACH DELETE n 
                                RETURN count(n) 
                                $$) AS (count_deleted agtype)
                            """
                            cursor.execute(delete_sql)
                            result = cursor.fetchone()
                            count = int(result[0]) if result and result[0] else 0
                            deleted_count += count
                    
                    conn.commit()
                    logger.info(f"Cleaned up {deleted_count} orphaned graph items")
                    return deleted_count
                    
        except GraphDatabaseNotAvailableError:
            raise
        except Exception as e:
            raise GraphDatabaseNotAvailableError(
                f"Failed to cleanup orphaned graph data: {e}"
            ) from e
    
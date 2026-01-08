"""
RecordsManager - Service for managing manual records (entities and relationships)
Built on top of GraphDatabaseService for shared graph database infrastructure.

This service handles:
- Project-based entity and relationship CRUD operations
- Custom entity type management (creates vertex labels in AGE)
- Custom relationship type management (creates edge labels in AGE)
- Metadata record creation in novel_graph_vertices/edges tables
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional
from services.graph_database_service import GraphDatabaseService, GraphDatabaseNotAvailableError

logger = logging.getLogger(__name__)


class RecordsManager:
    """
    Records Manager service for manual entity and relationship management.
    
    Maps project_id to graph context using prefix: project_{project_id}
    Uses GraphDatabaseService for all graph operations (no modifications to it).
    """
    
    def __init__(self, db_pool):
        """
        Initialize the Records Manager.
        
        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool
        self.graph_service = GraphDatabaseService(db_pool)
        self.graph_name = self.graph_service.graph_name
        # Cache for vertex labels to avoid repeated connection usage
        self._vertex_label_cache = set()
        
        logger.info("RecordsManager initialized")
    
    def _project_id_to_draft_id(self, project_id: str) -> str:
        """
        Convert project_id to graph draft_id format.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Graph draft_id: "project_{project_id}"
        """
        return f"project_{project_id}"
    
    def create_vertex_label(self, vertex_label: str) -> bool:
        """
        Create a vertex label in Apache AGE if it doesn't exist.
        Uses caching to avoid repeated database queries.
        
        Args:
            vertex_label: Vertex label name (e.g., "Faction")
            
        Returns:
            True if created or already exists, False on error
        """
        # Check cache first to avoid connection usage
        if vertex_label in self._vertex_label_cache:
            logger.debug(f"Vertex label {vertex_label} found in cache, skipping check")
            return True
        
        try:
            with self.graph_service.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    # Check if vertex label already exists
                    # ag_label table structure: graph_id (oid), name (name), id (oid), kind (char)
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM ag_catalog.ag_label l
                            JOIN ag_catalog.ag_graph g ON l.graph = g.graphid
                            WHERE g.name = %s AND l.name = %s AND l.kind = 'v'
                        )
                    """, (self.graph_name, vertex_label))
                    
                    exists = cursor.fetchone()[0]
                    
                    if not exists:
                        # Create vertex label using create_vlabel function
                        cursor.execute("""
                            SELECT ag_catalog.create_vlabel(%s, %s)
                        """, (self.graph_name, vertex_label))
                        conn.commit()
                        logger.info(f"Created vertex label: {vertex_label}")
                    else:
                        logger.debug(f"Vertex label already exists: {vertex_label}")
                    
                    # Add to cache
                    self._vertex_label_cache.add(vertex_label)
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to create vertex label {vertex_label}: {e}")
            return False
    
    def create_edge_label(self, edge_label: str) -> bool:
        """
        Create an edge label in Apache AGE if it doesn't exist.
        
        Args:
            edge_label: Edge label name (e.g., "ALLIED_WITH")
            
        Returns:
            True if created or already exists, False on error
        """
        try:
            with self.graph_service.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    # Check if edge label already exists
                    # ag_label table structure: graph_id (oid), name (name), id (oid), kind (char)
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM ag_catalog.ag_label l
                            JOIN ag_catalog.ag_graph g ON l.graph = g.graphid
                            WHERE g.name = %s AND l.name = %s AND l.kind = 'e'
                        )
                    """, (self.graph_name, edge_label))
                    
                    exists = cursor.fetchone()[0]
                    
                    if not exists:
                        # Create edge label using create_elabel function
                        cursor.execute("""
                            SELECT ag_catalog.create_elabel(%s, %s)
                        """, (self.graph_name, edge_label))
                        conn.commit()
                        logger.info(f"Created edge label: {edge_label}")
                    else:
                        logger.debug(f"Edge label already exists: {edge_label}")
                    
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to create edge label {edge_label}: {e}")
            return False
    
    def create_entity(
        self,
        project_id: str,
        entity_name: str,
        entity_type: str,
        properties: Dict[str, Any] = None,
        vertex_label: Optional[str] = None
    ) -> Optional[int]:
        """
        Create an entity (vertex) in the graph database.
        
        CRITICAL: All records MUST have a vertex in Apache AGE graph.
        This function creates the vertex FIRST, then creates metadata.
        If vertex creation fails, NO metadata is created.
        
        Args:
            project_id: Project UUID
            entity_name: Name of the entity
            entity_type: Entity type (lowercase: "character", "faction", etc.)
            properties: Entity properties dictionary
            vertex_label: Vertex label for AGE (defaults to capitalized entity_type)
            
        Returns:
            AGE vertex ID, or None on error (if None, no metadata is created)
        """
        if properties is None:
            properties = {}
        
        # Determine vertex label (capitalize first letter of each word)
        if vertex_label is None:
            vertex_label = entity_type.replace('_', ' ').title().replace(' ', '')
        
        # Ensure vertex label exists in AGE
        if not self.create_vertex_label(vertex_label):
            logger.error(f"Failed to ensure vertex label exists: {vertex_label}")
            return None
        
        # Map project_id to graph draft_id
        graph_draft_id = self._project_id_to_draft_id(project_id)
        
        # CRITICAL: Check for duplicate entities before creating
        # Every vertex must be unique - check both graph and metadata
        # Note: This check uses a connection, but it's important to prevent duplicates
        # If connection pool is exhausted, we'll skip the check and proceed
        try:
            # Check if entity with same name and type already exists in this project
            existing_entities = self.get_project_entities(project_id=project_id, entity_type=entity_type)
            for existing in existing_entities:
                if existing.get('name', '').strip().lower() == entity_name.strip().lower():
                    logger.warning(f"Duplicate entity detected: '{entity_name}' ({entity_type}) already exists in project {project_id} with vertex_id {existing.get('vertex_id')}")
                    # Return existing vertex_id instead of creating duplicate
                    return existing.get('vertex_id')
        except Exception as e:
            # If connection pool is exhausted, log but proceed - duplicate check is non-critical
            if "connection pool exhausted" in str(e).lower() or "pool" in str(e).lower():
                logger.warning(f"Connection pool issue during duplicate check, proceeding with creation: {e}")
            else:
                logger.warning(f"Failed to check for duplicates (non-critical): {e}, proceeding with creation")
        
        try:
            # Use GraphDatabaseService to create vertex
            vertex_id = self.graph_service.create_vertex(
                draft_id=graph_draft_id,
                entity_name=entity_name,
                entity_type=vertex_label,
                properties=properties
            )
            
            # Create metadata record in novel_graph_vertices
            self._create_vertex_metadata(
                project_id=project_id,
                entity_type=entity_type,
                entity_name=entity_name,
                vertex_id=vertex_id,
                vertex_label=vertex_label,
                properties=properties
            )
            
            logger.info(f"Created entity: {entity_name} ({entity_type}) with vertex_id: {vertex_id}")
            return vertex_id
            
        except GraphDatabaseNotAvailableError as e:
            logger.error(f"Graph database not available: {e}")
            # CRITICAL: Do not create metadata if vertex creation failed
            # All records MUST have a vertex in Apache AGE graph
            return None
        except Exception as e:
            logger.error(f"Failed to create entity {entity_name}: {e}")
            # CRITICAL: Do not create metadata if vertex creation failed
            # All records MUST have a vertex in Apache AGE graph
            return None
    
    def _create_vertex_metadata(
        self,
        project_id: str,
        entity_type: str,
        entity_name: str,
        vertex_id: int,
        vertex_label: str,
        properties: Dict[str, Any]
    ) -> None:
        """Create metadata record in novel_graph_vertices table."""
        conn = None
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                # Check if metadata already exists for this vertex_id
                cursor.execute("""
                    SELECT vertex_id FROM novel_graph_vertices 
                    WHERE vertex_id = %s AND project_id = %s
                """, (vertex_id, project_id))
                
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing record
                    cursor.execute("""
                        UPDATE novel_graph_vertices 
                        SET entity_name = %s,
                            entity_type = %s,
                            vertex_label = %s,
                            properties = %s,
                            updated_at = NOW()
                        WHERE vertex_id = %s AND project_id = %s
                    """, (
                        entity_name,
                        entity_type,
                        vertex_label,
                        json.dumps(properties),
                        vertex_id,
                        project_id
                    ))
                    logger.debug(f"Updated metadata record for vertex {vertex_id}: {entity_name} ({entity_type})")
                else:
                    # Insert new record
                    cursor.execute("""
                        INSERT INTO novel_graph_vertices 
                        (project_id, entity_type, entity_name, vertex_id, vertex_label, properties, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """, (
                        project_id,
                        entity_type,
                        entity_name,
                        vertex_id,
                        vertex_label,
                        json.dumps(properties)
                    ))
                    logger.info(f"Created metadata record for vertex {vertex_id}: {entity_name} ({entity_type})")
                
                conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"CRITICAL: Failed to create vertex metadata for {entity_name} (vertex_id: {vertex_id}): {e}", exc_info=True)
            # Re-raise to prevent silent failure - metadata is critical for entity visibility
            raise
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def update_entity(
        self,
        project_id: str,
        vertex_id: int,
        entity_name: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update an entity in the graph database with atomic transaction.

        Both graph and metadata updates happen in the same transaction.
        If either fails, the entire operation is rolled back.

        Args:
            project_id: Project UUID
            vertex_id: AGE vertex ID
            entity_name: New entity name (optional)
            properties: Updated properties (optional)

        Returns:
            True if successful, False otherwise
        """
        graph_draft_id = self._project_id_to_draft_id(project_id)

        try:
            # Single connection for BOTH graph and metadata updates (atomic transaction)
            with self.graph_service.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    # Escape for Cypher
                    safe_draft_id = self.graph_service._escape_cypher_string(graph_draft_id)

                    # Build SET clause for graph update
                    set_clauses = []
                    if entity_name is not None:
                        safe_name = self.graph_service._escape_cypher_string(entity_name)
                        set_clauses.append(f"n.name = '{safe_name}'")

                    if properties is not None:
                        safe_props = self.graph_service._prepare_agtype_properties(properties)
                        set_clauses.append(f"n.properties = {safe_props}")

                    if not set_clauses:
                        return True  # Nothing to update

                    set_clause = ", ".join(set_clauses)

                    # 1. Execute Cypher query for graph update (DO NOT COMMIT YET)
                    sql_query = f"""
                        SELECT result FROM ag_catalog.cypher('{self.graph_name}', $$
                        MATCH (n {{draft_id: '{safe_draft_id}'}})
                        WHERE id(n) = {vertex_id}
                        SET {set_clause}
                        RETURN n
                        $$) AS (result agtype)
                    """
                    cursor.execute(sql_query)

                    # 2. Execute SQL for metadata update on SAME connection
                    # (AGE search_path includes 'public' so this works)
                    if entity_name or properties:
                        meta_updates = []
                        meta_params = {'vertex_id': vertex_id, 'project_id': project_id}

                        if entity_name is not None:
                            meta_updates.append("entity_name = %(name)s")
                            meta_params['name'] = entity_name

                        if properties is not None:
                            meta_updates.append("properties = %(properties)s")
                            meta_params['properties'] = json.dumps(properties)

                        if meta_updates:
                            meta_updates.append("updated_at = NOW()")
                            meta_query = f"""
                                UPDATE novel_graph_vertices
                                SET {', '.join(meta_updates)}
                                WHERE project_id = %(project_id)s AND vertex_id = %(vertex_id)s
                            """
                            cursor.execute(meta_query, meta_params)

                    # 3. BOTH succeeded - now commit (single transaction)
                    conn.commit()

            # Connection returned to pool by context manager
            logger.info(f"Updated entity vertex_id: {vertex_id}")
            return True

        except Exception as e:
            # Transaction auto-rolled back on exception, connection returned to pool
            logger.error(f"Failed to update entity vertex_id {vertex_id}: {e}")
            return False
    
    def _update_vertex_metadata(
        self,
        vertex_id: int,
        entity_name: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update metadata record in novel_graph_vertices table."""
        conn = None
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                updates = []
                params = {'vertex_id': vertex_id}
                
                if entity_name is not None:
                    updates.append("entity_name = %(name)s")
                    params['name'] = entity_name
                
                if properties is not None:
                    updates.append("properties = %(properties)s")
                    params['properties'] = json.dumps(properties)
                
                if updates:
                    updates.append("updated_at = NOW()")
                    query = f"""
                        UPDATE novel_graph_vertices 
                        SET {', '.join(updates)}
                        WHERE vertex_id = %(vertex_id)s
                    """
                    cursor.execute(query, params)
                    conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.warning(f"Failed to update vertex metadata (non-critical): {e}")
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def _parse_agtype_vertex_id(self, agtype_result) -> Optional[int]:
        """
        Parse vertex_id from agtype result.
        
        Args:
            agtype_result: Result from agtype query (can be tuple, dict, string, int, etc.)
            
        Returns:
            Parsed vertex_id as int, or None if not found/parseable
        """
        if not agtype_result:
            return None
        
        # Handle tuple result (cursor.fetchone() returns tuple)
        if isinstance(agtype_result, tuple):
            value = agtype_result[0] if len(agtype_result) > 0 else None
        else:
            value = agtype_result
        
        if value is None:
            return None
        
        try:
            # Try direct int conversion
            if isinstance(value, (int, float)):
                return int(value)
            
            # Try parsing as string (agtype often returns JSON strings)
            if isinstance(value, str):
                # Try JSON parsing first
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, dict):
                        # Look for common keys
                        return int(parsed.get('vertex_id', parsed.get('id', parsed.get('v_id', 0))))
                    elif isinstance(parsed, (int, float)):
                        return int(parsed)
                except (json.JSONDecodeError, ValueError):
                    # If not JSON, try extracting number from string
                    numbers = re.findall(r'\d+', str(value))
                    if numbers:
                        return int(numbers[0])
            
            # Try dict access
            if isinstance(value, dict):
                return int(value.get('vertex_id', value.get('id', value.get('v_id', 0))))
            
            # Last resort: try direct conversion
            return int(value)
        except (ValueError, TypeError, KeyError) as e:
            logger.debug(f"Could not parse agtype vertex_id: {e}, value: {value}, type: {type(value)}")
            return None
    
    def delete_entity(self, project_id: str, vertex_id: int) -> bool:
        """
        Delete an entity from the graph database.
        
        Args:
            project_id: Project UUID
            vertex_id: AGE vertex ID
            
        Returns:
            True if successful, False otherwise
        """
        graph_draft_id = self._project_id_to_draft_id(project_id)
        
        logger.info(f"Delete entity: vertex_id={vertex_id}, project_id={project_id}, graph_draft_id={graph_draft_id}")
        
        # First, check if vertex exists in metadata table (source of truth)
        vertex_exists_in_metadata = False
        conn = None
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT vertex_id FROM novel_graph_vertices
                    WHERE project_id = %s AND vertex_id = %s
                """, (project_id, vertex_id))
                result = cursor.fetchone()
                vertex_exists_in_metadata = result is not None
                if vertex_exists_in_metadata:
                    logger.debug(f"Vertex {vertex_id} found in metadata table")
        except Exception as e:
            logger.warning(f"Failed to check metadata for vertex {vertex_id}: {e}")
            # Continue anyway - we'll try to delete from graph
        finally:
            if conn:
                self.db_pool.putconn(conn)
        
        try:
            with self.graph_service.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    safe_draft_id = self.graph_service._escape_cypher_string(graph_draft_id)
                    
                    # Always use the most permissive delete query (by ID only, no property filters)
                    # This ensures we can delete ALL vertices regardless of their structure, properties, or draft_id
                    # Some records may have been created with different structures or missing properties
                    sql_query = f"""
                        SELECT result FROM ag_catalog.cypher('{self.graph_name}', $$
                        MATCH (n)
                        WHERE id(n) = {vertex_id}
                        DETACH DELETE n
                        RETURN count(n) AS deleted_count
                        $$) AS (result agtype)
                    """
                    
                    logger.info(f"Attempting deletion of vertex {vertex_id} using ID-only match (handles all vertex types)")
                    
                    try:
                        logger.debug(f"Executing delete query: {sql_query}")
                        cursor.execute(sql_query)
                        result = cursor.fetchone()
                        logger.debug(f"Delete query executed, result: {result}")
                        
                        # Parse the deleted count from result
                        deleted_count = 0
                        if result and result[0] is not None:
                            try:
                                count_value = result[0]
                                if isinstance(count_value, (int, float)):
                                    deleted_count = int(count_value)
                                elif isinstance(count_value, str):
                                    numbers = re.findall(r'\d+', str(count_value))
                                    deleted_count = int(numbers[0]) if numbers else 0
                                elif isinstance(count_value, dict):
                                    deleted_count = int(count_value.get('deleted_count', count_value.get('count', 0)))
                                else:
                                    deleted_count = int(count_value) if count_value else 0
                            except Exception as parse_e:
                                logger.warning(f"Could not parse delete result: {parse_e}, result: {result}")
                        
                        if deleted_count > 0:
                            logger.info(f"Delete query returned deleted_count={deleted_count} for vertex {vertex_id}")
                        else:
                            logger.warning(f"Delete query executed but deleted_count=0 for vertex {vertex_id} (may not have existed)")
                        
                        # Commit the deletion (even if result is unclear, commit to ensure any changes are applied)
                        conn.commit()
                        logger.debug("Delete transaction committed")
                        
                        # Verify deletion by checking if vertex still exists (try without draft_id since it might be legacy)
                        verify_deleted_query = f"""
                            SELECT result FROM ag_catalog.cypher('{self.graph_name}', $$
                            MATCH (n)
                            WHERE id(n) = {vertex_id}
                            RETURN count(n) AS vertex_count
                            $$) AS (result agtype)
                        """
                        cursor.execute(verify_deleted_query)
                        verify_deleted_result = cursor.fetchone()
                        
                        vertex_still_exists = False
                        if verify_deleted_result and verify_deleted_result[0] is not None:
                            try:
                                exists_count = verify_deleted_result[0]
                                # Parse the count - agtype can be various formats
                                if isinstance(exists_count, (int, float)):
                                    exists_num = int(exists_count)
                                elif isinstance(exists_count, str):
                                    # Try to extract number from string
                                    numbers = re.findall(r'\d+', str(exists_count))
                                    exists_num = int(numbers[0]) if numbers else 0
                                elif isinstance(exists_count, dict):
                                    exists_num = int(exists_count.get('vertex_count', exists_count.get('count', exists_count.get('exists', 0))))
                                else:
                                    # Try to convert to int
                                    exists_num = int(exists_count) if exists_count else 0
                                
                                vertex_still_exists = exists_num > 0
                                logger.debug(f"Verification after delete: vertex exists count = {exists_num}, still exists = {vertex_still_exists}")
                            except Exception as parse_e:
                                logger.warning(f"Could not parse verification result: {parse_e}, result: {verify_deleted_result}")
                                # If we can't parse, assume deletion succeeded (optimistic - query executed without error)
                                vertex_still_exists = False
                        else:
                            # No verification result - vertex likely doesn't exist (was deleted)
                            vertex_still_exists = False
                            logger.debug("No verification result, assuming deletion succeeded")
                        
                        # ALWAYS clean up metadata if it exists (even if vertex doesn't exist in graph)
                        # This ensures consistency - metadata should never exist without a corresponding vertex
                        if vertex_exists_in_metadata:
                            try:
                                self._delete_vertex_metadata(project_id, vertex_id)
                                logger.info(f"Deleted metadata for vertex {vertex_id}")
                            except Exception as meta_e:
                                logger.warning(f"Failed to delete metadata (non-critical): {meta_e}")
                        
                        # Success criteria:
                        # 1. We deleted something from graph (deleted_count > 0), OR
                        # 2. Vertex no longer exists AND we cleaned up metadata, OR
                        # 3. We cleaned up metadata (orphaned metadata - vertex never existed in graph)
                        if deleted_count > 0:
                            logger.info(f"Successfully deleted entity vertex_id: {vertex_id} for project {project_id} (deleted {deleted_count} vertex from graph)")
                            return True
                        elif not vertex_still_exists:
                            if vertex_exists_in_metadata:
                                logger.info(f"Successfully cleaned up orphaned metadata for vertex {vertex_id} (vertex never existed in graph)")
                            else:
                                logger.info(f"Vertex {vertex_id} does not exist in graph or metadata - nothing to delete")
                            return True
                        else:
                            # Vertex still exists in graph after delete attempt - this is a failure
                            logger.error(f"Failed to delete vertex {vertex_id} - vertex still exists in graph after delete attempt")
                            return False
                            
                    except Exception as delete_e:
                        logger.error(f"Error executing delete query: {delete_e}", exc_info=True)
                        conn.rollback()
                        # Still try to clean up metadata if it exists
                        if vertex_exists_in_metadata:
                            try:
                                self._delete_vertex_metadata(project_id, vertex_id)
                                logger.info(f"Cleaned up metadata for vertex {vertex_id} after graph deletion error")
                            except Exception as meta_e:
                                logger.warning(f"Failed to delete metadata after error: {meta_e}")
                        return False
                    
        except Exception as e:
            logger.error(f"Failed to delete entity vertex_id {vertex_id}: {e}", exc_info=True)
            # Still try to clean up metadata if it exists
            if vertex_exists_in_metadata:
                try:
                    self._delete_vertex_metadata(project_id, vertex_id)
                    logger.info(f"Cleaned up metadata for vertex {vertex_id} after exception")
                except Exception as meta_e:
                    logger.warning(f"Failed to delete metadata after exception: {meta_e}")
            return False
    
    def _delete_vertex_metadata(self, project_id: str, vertex_id: int) -> None:
        """Delete metadata record from novel_graph_vertices table."""
        conn = None
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM novel_graph_vertices 
                    WHERE project_id = %s AND vertex_id = %s
                """, (project_id, vertex_id))
                conn.commit()
                logger.debug(f"Deleted metadata for vertex {vertex_id}")
        except Exception as e:
            if conn:
                conn.rollback()
            logger.warning(f"Failed to delete vertex metadata (non-critical): {e}")
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def get_project_entities(
        self,
        project_id: str,
        entity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all entities for a project.
        
        Args:
            project_id: Project UUID
            entity_type: Optional filter by entity type
            
        Returns:
            List of entity dictionaries
        """
        graph_draft_id = self._project_id_to_draft_id(project_id)
        
        logger.debug(f"Getting entities for project {project_id}, entity_type: {entity_type}, draft_id: {graph_draft_id}")
        
        try:
            with self.graph_service.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    safe_draft_id = self.graph_service._escape_cypher_string(graph_draft_id)
                    
                    # Always fetch ALL entities from graph, then filter by metadata type
                    # The vertex label in AGE may not match entity_type stored in metadata
                    # IMPORTANT: Cast vertex_id to bigint to ensure consistent parsing
                    logger.debug(f"Querying all entities for project (will filter by type={entity_type} from metadata)")
                    sql_query = f"""
                        SELECT v_name, v_props, v_id::bigint FROM ag_catalog.cypher('{self.graph_name}', $$
                        MATCH (v {{draft_id: '{safe_draft_id}'}})
                        WHERE v.name IS NOT NULL
                        RETURN v.name, v.properties, id(v)
                        $$) AS (v_name agtype, v_props agtype, v_id agtype)
                    """
                    
                    cursor.execute(sql_query)
                    results = cursor.fetchall()
                    
                    # Get entity types from metadata table
                    vertex_ids = []
                    entities_dict = {}
                    seen_vertex_ids = set()  # Track seen vertex_ids to prevent duplicates
                    for row in results:
                        if row and len(row) >= 3:
                            try:
                                # Parse vertex_id from agtype - can be int, string, or JSON
                                raw_vertex_id = row[2]
                                vertex_id = None
                                if raw_vertex_id is not None:
                                    if isinstance(raw_vertex_id, (int, float)):
                                        vertex_id = int(raw_vertex_id)
                                    elif isinstance(raw_vertex_id, str):
                                        # Try JSON parsing first (agtype often returns JSON strings)
                                        try:
                                            parsed = json.loads(raw_vertex_id)
                                            vertex_id = int(parsed)
                                        except (json.JSONDecodeError, ValueError, TypeError):
                                            # Try extracting number from string
                                            import re
                                            numbers = re.findall(r'\d+', raw_vertex_id)
                                            if numbers:
                                                vertex_id = int(numbers[0])
                                    else:
                                        vertex_id = int(raw_vertex_id)
                                
                                if vertex_id:
                                    # Skip if we've already seen this vertex_id (prevent duplicates)
                                    if vertex_id in seen_vertex_ids:
                                        logger.warning(f"Duplicate vertex_id {vertex_id} found in query results, skipping")
                                        continue
                                    
                                    seen_vertex_ids.add(vertex_id)
                                    vertex_ids.append(vertex_id)
                                    name = json.loads(str(row[0])) if isinstance(row[0], str) else row[0]
                                    props = json.loads(str(row[1])) if isinstance(row[1], str) else (row[1] if isinstance(row[1], dict) else {})
                                    # Ensure properties is a dict and preserve all keys including _settings
                                    if not isinstance(props, dict):
                                        props = {}
                                    
                                    # If _settings is a JSON string (from AGE storage), parse it
                                    if '_settings' in props and isinstance(props['_settings'], str):
                                        try:
                                            props['_settings'] = json.loads(props['_settings'])
                                        except (json.JSONDecodeError, TypeError):
                                            logger.warning(f"Failed to parse _settings JSON for entity {vertex_id}")
                                    
                                    # If _summaries is a JSON string (from AGE storage), parse it
                                    if '_summaries' in props and isinstance(props['_summaries'], str):
                                        try:
                                            props['_summaries'] = json.loads(props['_summaries'])
                                        except (json.JSONDecodeError, TypeError):
                                            logger.warning(f"Failed to parse _summaries JSON for entity {vertex_id}")
                                    
                                    entities_dict[vertex_id] = {
                                        'vertex_id': str(vertex_id),  # Convert to string to avoid JS precision loss
                                        'name': name,
                                        'properties': props
                                    }
                                    # Debug: log if _settings is present
                                    if '_settings' in props:
                                        logger.debug(f"Entity {vertex_id} has _settings: {type(props.get('_settings'))} - {props.get('_settings')}")
                            except Exception as e:
                                logger.warning(f"Error processing entity row: {e}, row: {row}")
                                pass
                    
                    # Fetch entity types and created_at from metadata - use the same connection to avoid pool exhaustion
                    # IMPORTANT: Only include entities that exist in metadata (exclude deleted/soft-deleted)
                    if vertex_ids:
                        try:
                            with conn.cursor() as meta_cursor:
                                placeholders = ','.join(['%s'] * len(vertex_ids))
                                meta_cursor.execute(f"""
                                    SELECT vertex_id, entity_type, created_at 
                                    FROM novel_graph_vertices
                                    WHERE project_id = %s AND vertex_id IN ({placeholders})
                                    AND deleted_at IS NULL
                                """, [project_id] + vertex_ids)
                                meta_results = meta_cursor.fetchall()
                                for meta_row in meta_results:
                                    meta_vertex_id, meta_entity_type, created_at = meta_row
                                    if meta_vertex_id in entities_dict:
                                        entities_dict[meta_vertex_id]['type'] = meta_entity_type
                                        if created_at:
                                            entities_dict[meta_vertex_id]['created_at'] = created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at)
                        except Exception as e:
                            logger.warning(f"Failed to fetch entity types from metadata: {e}")
                    
                    # Only return entities that have metadata (exclude orphaned graph vertices)
                    # This ensures consistency - if metadata was deleted, entity should not appear
                    # Also exclude 'interaction' type - those are stored separately
                    # Filter by entity_type if specified (based on metadata, not graph label)
                    entities = []
                    for vertex_id, entity_data in entities_dict.items():
                        # Only include if we have metadata for it (entity_type was set from metadata query)
                        if 'type' in entity_data:
                            # Exclude interaction entities from regular entity list - they have their own view
                            if entity_data['type'].lower() == 'interaction':
                                continue
                            # Apply entity_type filter based on metadata type (not graph label)
                            if entity_type:
                                # Normalize for comparison: handle underscores, spaces, and case
                                normalized_filter = entity_type.lower().replace('_', ' ').replace('-', ' ')
                                normalized_type = entity_data['type'].lower().replace('_', ' ').replace('-', ' ')
                                if normalized_filter != normalized_type:
                                    continue
                            entities.append(entity_data)
                        else:
                            logger.warning(f"Excluding orphaned vertex {vertex_id} - exists in graph but not in metadata")
                    
                    logger.info(f"Retrieved {len(entities)} entities for project {project_id} (entity_type filter: {entity_type}, filtered from {len(entities_dict)} graph vertices)")
                    if entity_type and len(entities) == 0:
                        logger.warning(f"No entities found for entity_type '{entity_type}'")
                    return entities
                    
        except Exception as e:
            logger.error(f"Failed to get entities for project {project_id}: {e}", exc_info=True)
            return []
    
    def create_relationship(
        self,
        project_id: str,
        source_name: str,
        target_name: str,
        relationship_type: str,
        properties: Dict[str, Any] = None,
        edge_label: Optional[str] = None
    ) -> Optional[int]:
        """
        Create a relationship (edge) between two entities.
        
        Args:
            project_id: Project UUID
            source_name: Source entity name
            target_name: Target entity name
            relationship_type: Relationship type (will be normalized)
            properties: Relationship properties
            edge_label: Edge label for AGE (defaults to normalized relationship_type)
            
        Returns:
            AGE edge ID, or None on error
        """
        if properties is None:
            properties = {}
        
        # Normalize relationship type to edge label
        if edge_label is None:
            edge_label = self.graph_service._normalize_relationship_type(relationship_type)
        
        # Ensure edge label exists in AGE
        if not self.create_edge_label(edge_label):
            logger.error(f"Failed to ensure edge label exists: {edge_label}")
            return None
        
        # Map project_id to graph draft_id
        graph_draft_id = self._project_id_to_draft_id(project_id)
        
        try:
            # Use GraphDatabaseService to create relationship
            edge_id = self.graph_service.create_relationship(
                draft_id=graph_draft_id,
                source_name=source_name,
                target_name=target_name,
                relationship_type=edge_label,
                properties=properties
            )
            
            # Get vertex IDs for metadata
            source_vertex_id = self._get_vertex_id_by_name(project_id, source_name)
            target_vertex_id = self._get_vertex_id_by_name(project_id, target_name)
            
            # Create metadata record
            if source_vertex_id and target_vertex_id:
                self._create_edge_metadata(
                    project_id=project_id,
                    source_vertex_id=source_vertex_id,
                    target_vertex_id=target_vertex_id,
                    edge_id=edge_id,
                    edge_label=edge_label,
                    properties=properties
                )
            
            logger.info(f"Created relationship: {source_name} -{edge_label}-> {target_name} (edge_id: {edge_id})")
            return edge_id
            
        except GraphDatabaseNotAvailableError as e:
            logger.error(f"Graph database not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return None
    
    def upsert_relationship(
        self,
        project_id: str,
        source_name: str,
        target_name: str,
        relationship_type: str,
        properties: Dict[str, Any] = None,
        edge_label: Optional[str] = None
    ) -> Optional[int]:
        """
        Create or update a relationship between two entities.
        If a relationship already exists between source and target, update it.
        Otherwise, create a new one.
        
        Args:
            project_id: Project UUID
            source_name: Source entity name
            target_name: Target entity name
            relationship_type: Relationship type
            properties: Relationship properties (including sentiment_score)
            edge_label: Edge label for AGE
            
        Returns:
            AGE edge ID, or None on error
        """
        graph_draft_id = self._project_id_to_draft_id(project_id)
        
        try:
            # Check if relationship already exists
            with self.graph_service.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    safe_draft_id = self.graph_service._escape_cypher_string(graph_draft_id)
                    safe_source = self.graph_service._escape_cypher_string(source_name)
                    safe_target = self.graph_service._escape_cypher_string(target_name)
                    
                    # Check for existing relationship (either direction for undirected sentiment)
                    check_query = f"""
                        SELECT edge_id FROM ag_catalog.cypher('{self.graph_name}', $$
                        MATCH (a {{draft_id: '{safe_draft_id}', name: '{safe_source}'}})-[r]->(b {{draft_id: '{safe_draft_id}', name: '{safe_target}'}})
                        RETURN id(r)
                        $$) AS (edge_id agtype)
                    """
                    cursor.execute(check_query)
                    result = cursor.fetchone()
                    
                    if result and result[0]:
                        # Relationship exists - update it
                        edge_id = int(result[0])
                        logger.info(f"Relationship exists (edge_id: {edge_id}), updating...")
                        
                        # Update the existing relationship
                        success = self.update_relationship(
                            project_id=project_id,
                            edge_id=edge_id,
                            relationship_type=relationship_type,
                            properties=properties
                        )
                        
                        if success:
                            logger.info(f"Updated relationship: {source_name} -> {target_name} with sentiment_score: {properties.get('sentiment_score')}")
                            return edge_id
                        else:
                            logger.warning(f"Failed to update relationship, will create new one")
            
            # No existing relationship or update failed - create new one
            return self.create_relationship(
                project_id=project_id,
                source_name=source_name,
                target_name=target_name,
                relationship_type=relationship_type,
                properties=properties,
                edge_label=edge_label
            )
            
        except Exception as e:
            logger.error(f"Error in upsert_relationship: {e}")
            # Fallback to create
            return self.create_relationship(
                project_id=project_id,
                source_name=source_name,
                target_name=target_name,
                relationship_type=relationship_type,
                properties=properties,
                edge_label=edge_label
            )
    
    def create_relationship_by_ids(
        self,
        project_id: str,
        source_vertex_id: int,
        target_vertex_id: int,
        relationship_type: str,
        properties: Dict[str, Any] = None,
        edge_label: Optional[str] = None
    ) -> Optional[int]:
        """
        Create a relationship (edge) between two entities by their vertex IDs.
        
        Args:
            project_id: Project UUID
            source_vertex_id: Source entity vertex ID
            target_vertex_id: Target entity vertex ID
            relationship_type: Relationship type (will be normalized)
            properties: Relationship properties
            edge_label: Edge label for AGE (defaults to normalized relationship_type)
            
        Returns:
            AGE edge ID, or None on error
        """
        if properties is None:
            properties = {}
        
        # Normalize relationship type to edge label
        if edge_label is None:
            edge_label = self.graph_service._normalize_relationship_type(relationship_type)
        
        # Ensure edge label exists in AGE
        if not self.create_edge_label(edge_label):
            logger.error(f"Failed to ensure edge label exists: {edge_label}")
            return None
        
        # Map project_id to graph draft_id
        graph_draft_id = self._project_id_to_draft_id(project_id)
        
        try:
            with self.graph_service.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    safe_properties = self.graph_service._prepare_agtype_properties(properties)
                    safe_draft_id = self.graph_service._escape_cypher_string(graph_draft_id)
                    
                    # First verify both vertices exist and belong to this project
                    verify_query = f"""
                        SELECT result FROM ag_catalog.cypher('{self.graph_name}', $$
                        MATCH (a), (b)
                        WHERE id(a) = {source_vertex_id} AND a.draft_id = '{safe_draft_id}'
                        AND id(b) = {target_vertex_id} AND b.draft_id = '{safe_draft_id}'
                        RETURN count(a) + count(b) AS vertex_count
                        $$) AS (result agtype)
                    """
                    cursor.execute(verify_query)
                    verify_result = cursor.fetchone()
                    if not verify_result:
                        logger.error(f"Verification query returned no result. source_id={source_vertex_id}, target_id={target_vertex_id}, draft_id={graph_draft_id}")
                        return None
                    
                    # Parse the count result
                    count_value = verify_result[0]
                    try:
                        if isinstance(count_value, str):
                            count = json.loads(count_value) if count_value.startswith('{') else int(count_value)
                        else:
                            count = int(count_value) if not isinstance(count_value, dict) else int(count_value.get('vertex_count', 0))
                        
                        if count < 2:
                            logger.error(f"Vertices not found or don't belong to project. Found {count} vertices. source_id={source_vertex_id}, target_id={target_vertex_id}, draft_id={graph_draft_id}")
                            return None
                    except (ValueError, TypeError, json.JSONDecodeError) as e:
                        logger.warning(f"Could not parse verification count, proceeding anyway: {e}")
                    
                    # Build the Cypher query to create the relationship
                    # Note: Edge label in CREATE must be a valid identifier (no spaces, special chars)
                    sql_query = f"""
                        SELECT edge_id FROM ag_catalog.cypher('{self.graph_name}', $$
                        MATCH (a), (b)
                        WHERE id(a) = {source_vertex_id} AND a.draft_id = '{safe_draft_id}'
                        AND id(b) = {target_vertex_id} AND b.draft_id = '{safe_draft_id}'
                        CREATE (a)-[r:{edge_label} {safe_properties}]->(b)
                        RETURN id(r) AS edge_id
                        $$) AS (edge_id agtype)
                    """
                    logger.debug(f"Creating relationship query: {sql_query}")
                    cursor.execute(sql_query)
                    result = cursor.fetchone()
                    logger.debug(f"Query result: {result}, type: {type(result)}")
                    
                    if not result:
                        logger.error("No result returned from relationship creation query")
                        return None
                    
                    edge_id_value = result[0]
                    logger.debug(f"Edge ID value: {edge_id_value}, type: {type(edge_id_value)}")
                    
                    if edge_id_value is None:
                        logger.error("Edge ID is None in result")
                        return None
                    
                    # Parse agtype result - it's usually a dict with 'id' key or direct value
                    try:
                        # agtype results are often returned as strings that need JSON parsing
                        if isinstance(edge_id_value, str):
                            try:
                                parsed = json.loads(edge_id_value)
                                if isinstance(parsed, dict):
                                    edge_id = int(parsed.get('id', parsed.get('edge_id', 0)))
                                else:
                                    edge_id = int(parsed)
                            except (json.JSONDecodeError, ValueError):
                                # If not JSON, try direct conversion
                                edge_id = int(edge_id_value)
                        elif isinstance(edge_id_value, (int, float)):
                            edge_id = int(edge_id_value)
                        elif isinstance(edge_id_value, dict):
                            edge_id = int(edge_id_value.get('id', edge_id_value.get('edge_id', 0)))
                        else:
                            # Try to convert to string and parse
                            edge_id = int(str(edge_id_value))
                        
                        if edge_id == 0:
                            logger.error("Edge ID is 0, which is invalid")
                            return None
                        
                        conn.commit()
                        logger.info(f"Successfully created edge with ID: {edge_id}")
                        
                        # Create metadata record
                        self._create_edge_metadata(
                            project_id=project_id,
                            source_vertex_id=source_vertex_id,
                            target_vertex_id=target_vertex_id,
                            edge_id=edge_id,
                            edge_label=edge_label,
                            properties=properties
                        )
                        
                        logger.info(f"Created relationship by IDs: {source_vertex_id} -{edge_label}-> {target_vertex_id} (edge_id: {edge_id})")
                        return edge_id
                    except (ValueError, TypeError, KeyError) as e:
                        logger.error(f"Failed to parse edge_id from result: {e}, value: {edge_id_value}")
                        return None
                    return None
                    
        except GraphDatabaseNotAvailableError as e:
            logger.error(f"Graph database not available: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create relationship by IDs: {e}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def _get_vertex_id_by_name(self, project_id: str, entity_name: str) -> Optional[int]:
        """Get vertex ID by entity name from metadata table."""
        conn = None
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT vertex_id FROM novel_graph_vertices
                    WHERE project_id = %s AND entity_name = %s
                    LIMIT 1
                """, (project_id, entity_name))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.warning(f"Failed to get vertex_id for {entity_name}: {e}")
            return None
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def get_relationship_metadata_by_names(
        self,
        project_id: str,
        source_name: str,
        target_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get relationship metadata from PostgreSQL by source and target names.
        This is more reliable than reading from AGE for large JSON properties like chapter_analyses.
        
        Args:
            project_id: Project UUID
            source_name: Source entity name
            target_name: Target entity name
            
        Returns:
            Dict with properties including chapter_analyses, or None if not found
        """
        conn = None
        try:
            # First get vertex IDs for source and target
            source_vertex_id = self._get_vertex_id_by_name(project_id, source_name)
            target_vertex_id = self._get_vertex_id_by_name(project_id, target_name)
            
            logger.debug(f"Vertex ID lookup: source={source_name} -> {source_vertex_id}, target={target_name} -> {target_vertex_id}")
            
            if not source_vertex_id or not target_vertex_id:
                logger.debug(f"Could not find vertex IDs for {source_name} or {target_name}")
                return None
            
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT edge_id, edge_label, properties
                    FROM novel_graph_edges
                    WHERE project_id = %s 
                    AND source_vertex_id = %s 
                    AND target_vertex_id = %s
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (project_id, source_vertex_id, target_vertex_id))
                
                result = cursor.fetchone()
                if result:
                    edge_id, edge_label, properties_json = result
                    
                    # Debug: Log raw properties type and content
                    logger.debug(f"Raw properties_json type: {type(properties_json)}")
                    
                    # Parse properties - handle both string and dict cases
                    if properties_json is None:
                        properties = {}
                    elif isinstance(properties_json, str):
                        try:
                            properties = json.loads(properties_json)
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse properties JSON string: {e}")
                            properties = {}
                    elif isinstance(properties_json, dict):
                        properties = properties_json
                    else:
                        logger.warning(f"Unexpected properties type: {type(properties_json)}")
                        properties = {}
                    
                    # Debug: Log parsed properties keys and chapter_analyses info
                    logger.debug(f"Parsed properties keys: {list(properties.keys()) if properties else 'empty'}")
                    if 'chapter_analyses' in properties:
                        ch_val = properties['chapter_analyses']
                        logger.debug(f"chapter_analyses type: {type(ch_val)}, length: {len(str(ch_val)) if ch_val else 0}")
                    else:
                        logger.debug("chapter_analyses key NOT found in properties")
                    
                    return {
                        'edge_id': edge_id,
                        'source': source_name,
                        'target': target_name,
                        'relationship_type': edge_label,
                        'properties': properties or {}
                    }
                else:
                    logger.debug(f"No edge found in metadata table for {source_name} -> {target_name}")
            return None
        except Exception as e:
            logger.warning(f"Error getting relationship metadata by names: {e}", exc_info=True)
            return None
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def _create_edge_metadata(
        self,
        project_id: str,
        source_vertex_id: int,
        target_vertex_id: int,
        edge_id: int,
        edge_label: str,
        properties: Dict[str, Any]
    ) -> None:
        """Create or update metadata record in novel_graph_edges table."""
        conn = None
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                # Check if record exists
                cursor.execute("""
                    SELECT id FROM novel_graph_edges 
                    WHERE project_id = %s AND source_vertex_id = %s AND target_vertex_id = %s
                    LIMIT 1
                """, (project_id, source_vertex_id, target_vertex_id))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    cursor.execute("""
                        UPDATE novel_graph_edges 
                        SET edge_id = %s, edge_label = %s, properties = %s, updated_at = NOW()
                        WHERE project_id = %s AND source_vertex_id = %s AND target_vertex_id = %s
                    """, (
                        edge_id,
                        edge_label,
                        json.dumps(properties),
                        project_id,
                        source_vertex_id,
                        target_vertex_id
                    ))
                    logger.debug(f"Updated metadata record for edge {edge_id}")
                else:
                    # Insert new record
                    cursor.execute("""
                        INSERT INTO novel_graph_edges 
                        (project_id, source_vertex_id, target_vertex_id, edge_id, edge_label, properties, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """, (
                        project_id,
                        source_vertex_id,
                        target_vertex_id,
                        edge_id,
                        edge_label,
                        json.dumps(properties)
                    ))
                    logger.debug(f"Created metadata record for edge {edge_id}")
                conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.warning(f"Failed to create edge metadata (non-critical): {e}")
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def get_project_relationships(
        self,
        project_id: str,
        relationship_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all relationships for a project.
        
        Args:
            project_id: Project UUID
            relationship_type: Optional filter by relationship type
            
        Returns:
            List of relationship dictionaries
        """
        graph_draft_id = self._project_id_to_draft_id(project_id)
        
        try:
            with self.graph_service.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    safe_draft_id = self.graph_service._escape_cypher_string(graph_draft_id)
                    
                    if relationship_type:
                        edge_label = self.graph_service._normalize_relationship_type(relationship_type)
                        sql_query = f"""
                            SELECT a_name, rel_type, b_name, rel_props, rel_id
                            FROM ag_catalog.cypher('{self.graph_name}', $$
                            MATCH (a {{draft_id: '{safe_draft_id}'}})-[r:{edge_label}]->(b {{draft_id: '{safe_draft_id}'}})
                            RETURN a.name, type(r), b.name, r, id(r)
                            $$) AS (a_name agtype, rel_type agtype, b_name agtype, rel_props agtype, rel_id agtype)
                        """
                    else:
                        sql_query = f"""
                            SELECT a_name, rel_type, b_name, rel_props, rel_id
                            FROM ag_catalog.cypher('{self.graph_name}', $$
                            MATCH (a {{draft_id: '{safe_draft_id}'}})-[r]->(b {{draft_id: '{safe_draft_id}'}})
                            RETURN a.name, type(r), b.name, r, id(r)
                            $$) AS (a_name agtype, rel_type agtype, b_name agtype, rel_props agtype, rel_id agtype)
                        """
                    
                    cursor.execute(sql_query)
                    results = cursor.fetchall()
                    
                    relationships = []
                    for row in results:
                        if row and len(row) >= 5:
                            try:
                                source_raw = json.loads(str(row[0])) if isinstance(row[0], str) else row[0]
                                rel_type_raw = json.loads(str(row[1])) if isinstance(row[1], str) else row[1]
                                target_raw = json.loads(str(row[2])) if isinstance(row[2], str) else row[2]
                                
                                # Parse relationship object - AGE returns full edge object {id, label, properties, ...}
                                rel_obj_raw = row[3]
                                rel_obj = json.loads(str(rel_obj_raw)) if isinstance(rel_obj_raw, str) else (rel_obj_raw if isinstance(rel_obj_raw, dict) else {})
                                
                                # Debug: log raw relationship data
                                logger.debug(f"Raw rel_obj type: {type(rel_obj_raw)}, value: {str(rel_obj_raw)[:200]}")
                                logger.debug(f"Parsed rel_obj keys: {rel_obj.keys() if isinstance(rel_obj, dict) else 'not a dict'}")
                                
                                # Extract properties from the edge object
                                if isinstance(rel_obj, dict) and 'properties' in rel_obj:
                                    rel_props = rel_obj.get('properties', {})
                                    logger.debug(f"Extracted properties from 'properties' key: {list(rel_props.keys()) if rel_props else 'empty'}")
                                elif isinstance(rel_obj, dict):
                                    # Might already be properties or raw object without 'properties' key
                                    # Filter out AGE internal fields
                                    rel_props = {k: v for k, v in rel_obj.items() if k not in ['id', 'label', 'end_id', 'start_id']}
                                    logger.debug(f"Using rel_obj as properties (filtered): {list(rel_props.keys()) if rel_props else 'empty'}")
                                else:
                                    rel_props = {}
                                    logger.debug("rel_props set to empty dict")
                                
                                edge_id = int(row[4]) if row[4] else None
                                
                                # Clean up source and target - remove extra quotes if present
                                # Handle cases where agtype returns JSON-encoded strings with quotes
                                def clean_string(value):
                                    if value is None:
                                        return ""
                                    s = str(value)
                                    # Remove surrounding quotes if present (handle both single and double)
                                    while (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
                                        s = s[1:-1]
                                    return s
                                
                                source = clean_string(source_raw)
                                target = clean_string(target_raw)
                                rel_type = clean_string(rel_type_raw)
                            except Exception:
                                source_raw = row[0]
                                rel_type_raw = row[1]
                                target_raw = row[2]
                                rel_props = {}
                                edge_id = int(row[4]) if row[4] else None
                                
                                # Clean up source and target - remove extra quotes if present
                                # Handle cases where agtype returns JSON-encoded strings with quotes
                                def clean_string(value):
                                    if value is None:
                                        return ""
                                    s = str(value)
                                    # Remove surrounding quotes if present (handle both single and double)
                                    while (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
                                        s = s[1:-1]
                                    return s
                                
                                source = clean_string(source_raw)
                                target = clean_string(target_raw)
                                rel_type = clean_string(rel_type_raw)
                            
                            relationships.append({
                                'edge_id': str(edge_id),  # Convert to string to avoid JS precision loss
                                'source': source,
                                'target': target,
                                'relationship_type': rel_type,
                                'properties': rel_props
                            })
                    
                    logger.debug(f"Retrieved {len(relationships)} relationships for project {project_id}")
                    
                    # Enrich with metadata table properties (may have more complete data)
                    relationships = self._enrich_relationships_from_metadata(project_id, relationships)
                    
                    return relationships
                    
        except Exception as e:
            logger.error(f"Failed to get relationships for project {project_id}: {e}")
            return []
    
    def _enrich_relationships_from_metadata(
        self, 
        project_id: str, 
        relationships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich relationship data with properties from metadata table.
        AGE may not store all properties in the edge, so we supplement from metadata.
        """
        if not relationships:
            return relationships
        
        conn = None
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                # Get all edge metadata for this project
                cursor.execute("""
                    SELECT edge_id, properties
                    FROM novel_graph_edges
                    WHERE project_id = %s
                """, (project_id,))
                
                metadata_rows = cursor.fetchall()
                
                # Build lookup by edge_id
                metadata_map = {}
                for row in metadata_rows:
                    edge_id = str(row[0]) if row[0] else None
                    props_json = row[1]
                    if edge_id and props_json:
                        try:
                            props = json.loads(props_json) if isinstance(props_json, str) else props_json
                            metadata_map[edge_id] = props
                        except:
                            pass
                
                logger.debug(f"Found {len(metadata_map)} metadata records for enrichment")
                
                # Enrich each relationship
                for rel in relationships:
                    edge_id = rel.get('edge_id')
                    if edge_id and edge_id in metadata_map:
                        metadata_props = metadata_map[edge_id]
                        current_props = rel.get('properties', {})
                        
                        # Merge: metadata takes precedence for missing keys
                        for key, value in metadata_props.items():
                            if key not in current_props or current_props.get(key) in [None, '', {}, []]:
                                current_props[key] = value
                        
                        rel['properties'] = current_props
                        
                        if metadata_props.get('sentiment_score') is not None:
                            logger.debug(f"Enriched edge {edge_id} with metadata: score={metadata_props.get('sentiment_score')}, tone={metadata_props.get('emotional_tone')}")
                
                return relationships
                
        except Exception as e:
            logger.warning(f"Failed to enrich relationships from metadata: {e}")
            return relationships
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def update_relationship(
        self,
        project_id: str,
        edge_id: int,
        relationship_type: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        edge_label: Optional[str] = None
    ) -> bool:
        """
        Update a relationship in the graph database.
        
        Args:
            project_id: Project UUID
            edge_id: AGE edge ID
            relationship_type: New relationship type (optional)
            properties: New properties (optional)
            edge_label: New edge label (optional, defaults to normalized relationship_type)
            
        Returns:
            True if successful, False otherwise
        """
        graph_draft_id = self._project_id_to_draft_id(project_id)
        
        try:
            with self.graph_service.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    safe_draft_id = self.graph_service._escape_cypher_string(graph_draft_id)
                    
                    # First, get the current relationship to preserve what we're not updating
                    get_query = f"""
                        SELECT rel_type, rel_props, source_id, target_id
                        FROM ag_catalog.cypher('{self.graph_name}', $$
                        MATCH (a {{draft_id: '{safe_draft_id}'}})-[r]->(b {{draft_id: '{safe_draft_id}'}})
                        WHERE id(r) = {edge_id}
                        RETURN type(r) AS rel_type, r AS rel_props, id(a) AS source_id, id(b) AS target_id
                        $$) AS (rel_type agtype, rel_props agtype, source_id agtype, target_id agtype)
                    """
                    cursor.execute(get_query)
                    result = cursor.fetchone()
                    
                    if not result:
                        logger.error(f"Relationship {edge_id} not found")
                        return False
                    
                    # Parse current values
                    try:
                        current_type_raw = result[0]
                        current_type = json.loads(str(current_type_raw)) if isinstance(current_type_raw, str) else current_type_raw
                        # Clean quotes if present
                        if isinstance(current_type, str):
                            current_type = current_type.strip('"').strip("'")
                        
                        current_props_raw = result[1]
                        current_props = json.loads(str(current_props_raw)) if isinstance(current_props_raw, str) else (current_props_raw if isinstance(current_props_raw, dict) else {})
                        if not isinstance(current_props, dict):
                            current_props = {}
                    except Exception as e:
                        logger.warning(f"Error parsing current relationship values: {e}")
                        current_type = ""
                        current_props = {}
                    
                    # Use new values or keep current
                    new_type = relationship_type if relationship_type else current_type
                    new_props = properties if properties is not None else current_props
                    
                    # Normalize edge label
                    if edge_label is None:
                        edge_label = self.graph_service._normalize_relationship_type(new_type)
                    
                    # Delete old relationship
                    delete_query = f"""
                        SELECT result FROM ag_catalog.cypher('{self.graph_name}', $$
                        MATCH (a {{draft_id: '{safe_draft_id}'}})-[r]->(b {{draft_id: '{safe_draft_id}'}})
                        WHERE id(r) = {edge_id}
                        DELETE r
                        RETURN 1
                        $$) AS (result agtype)
                    """
                    cursor.execute(delete_query)
                    delete_result = cursor.fetchone()
                    if not delete_result:
                        logger.error(f"Failed to delete old relationship {edge_id}")
                        return False
                    
                    # Create new relationship with updated values
                    # Parse source_id and target_id from result
                    try:
                        source_id_raw = result[2]
                        target_id_raw = result[3]
                        
                        # Parse agtype results
                        if isinstance(source_id_raw, str):
                            source_id = int(json.loads(source_id_raw)) if source_id_raw.startswith('{') else int(source_id_raw)
                        else:
                            source_id = int(source_id_raw) if source_id_raw else None
                            
                        if isinstance(target_id_raw, str):
                            target_id = int(json.loads(target_id_raw)) if target_id_raw.startswith('{') else int(target_id_raw)
                        else:
                            target_id = int(target_id_raw) if target_id_raw else None
                    except (ValueError, TypeError, json.JSONDecodeError) as e:
                        logger.error(f"Failed to parse source/target IDs: {e}")
                        return False
                    
                    if not source_id or not target_id:
                        logger.error(f"Could not get source/target IDs for relationship {edge_id}. source_id={source_id}, target_id={target_id}")
                        return False
                    
                    # Ensure edge label exists
                    if not self.create_edge_label(edge_label):
                        logger.error(f"Failed to ensure edge label exists: {edge_label}")
                        return False
                    
                    safe_properties = self.graph_service._prepare_agtype_properties(new_props)
                    
                    create_query = f"""
                        SELECT edge_id FROM ag_catalog.cypher('{self.graph_name}', $$
                        MATCH (a), (b)
                        WHERE id(a) = {source_id} AND a.draft_id = '{safe_draft_id}'
                        AND id(b) = {target_id} AND b.draft_id = '{safe_draft_id}'
                        CREATE (a)-[r:{edge_label} {safe_properties}]->(b)
                        RETURN id(r) AS edge_id
                        $$) AS (edge_id agtype)
                    """
                    cursor.execute(create_query)
                    create_result = cursor.fetchone()
                    
                    if not create_result:
                        logger.error("Failed to recreate relationship")
                        return False
                    
                    # Parse new edge ID
                    new_edge_id_value = create_result[0]
                    try:
                        if isinstance(new_edge_id_value, str):
                            parsed = json.loads(new_edge_id_value)
                            new_edge_id = int(parsed.get('id', parsed.get('edge_id', 0))) if isinstance(parsed, dict) else int(parsed)
                        else:
                            new_edge_id = int(new_edge_id_value)
                    except (ValueError, TypeError, json.JSONDecodeError):
                        logger.error(f"Failed to parse new edge ID: {new_edge_id_value}")
                        return False
                    
                    # Update metadata - use same connection to avoid pool exhaustion
                    try:
                        with conn.cursor() as meta_cursor:
                            meta_cursor.execute("""
                                UPDATE novel_graph_edges
                                SET edge_id = %s, edge_label = %s, properties = %s, updated_at = NOW()
                                WHERE edge_id = %s AND project_id = %s
                            """, (
                                new_edge_id,
                                edge_label,
                                json.dumps(new_props),
                                edge_id,
                                project_id
                            ))
                    except Exception as e:
                        logger.warning(f"Failed to update edge metadata (non-critical): {e}")
                    
                    conn.commit()
                    logger.info(f"Updated relationship {edge_id} -> {new_edge_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to update relationship {edge_id}: {e}", exc_info=True)
            return False
    
    def delete_relationship(self, project_id: str, edge_id: int, cascade_interactions: bool = True) -> bool:
        """
        Delete a relationship from the graph database.
        
        Args:
            project_id: Project UUID
            edge_id: AGE edge ID
            cascade_interactions: If True, also delete all interactions between the two characters
            
        Returns:
            True if successful, False otherwise
        """
        try:
            source_name = None
            target_name = None
            
            with self.graph_service.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    # First, get the source and target names for cascade delete
                    if cascade_interactions:
                        get_names_query = f"""
                            SELECT source_name, target_name FROM ag_catalog.cypher('{self.graph_name}', $$
                            MATCH (a)-[r]->(b)
                            WHERE id(r) = {edge_id}
                            RETURN a.name, b.name
                            $$) AS (source_name agtype, target_name agtype)
                        """
                        cursor.execute(get_names_query)
                        names_result = cursor.fetchone()
                        if names_result:
                            source_name = json.loads(str(names_result[0])) if isinstance(names_result[0], str) else names_result[0]
                            target_name = json.loads(str(names_result[1])) if isinstance(names_result[1], str) else names_result[1]
                            # Clean quotes
                            if isinstance(source_name, str):
                                source_name = source_name.strip('"').strip("'")
                            if isinstance(target_name, str):
                                target_name = target_name.strip('"').strip("'")
                    
                    # Delete the relationship edge
                    sql_query = f"""
                        SELECT result FROM ag_catalog.cypher('{self.graph_name}', $$
                        MATCH ()-[r]->()
                        WHERE id(r) = {edge_id}
                        DELETE r
                        RETURN count(r)
                        $$) AS (result agtype)
                    """
                    
                    cursor.execute(sql_query)
                    result = cursor.fetchone()
                    conn.commit()
                    
                    # Check if anything was actually deleted
                    deleted_count = 0
                    if result and result[0]:
                        try:
                            if isinstance(result[0], (int, float)):
                                deleted_count = int(result[0])
                            elif isinstance(result[0], str):
                                import re
                                numbers = re.findall(r'\d+', str(result[0]))
                                deleted_count = int(numbers[0]) if numbers else 0
                        except:
                            pass
                    
                    # Delete metadata record regardless
                    self._delete_edge_metadata(edge_id)
                    
                    if deleted_count > 0:
                        logger.info(f"Deleted relationship edge_id: {edge_id} (deleted {deleted_count} from graph)")
                    else:
                        logger.info(f"Deleted relationship metadata edge_id: {edge_id} (edge may not have existed in graph)")
            
            # CASCADE: Delete all interactions between these two characters
            if cascade_interactions and source_name and target_name:
                interactions_deleted = self._delete_interactions_for_character_pair(
                    project_id, source_name, target_name
                )
                logger.info(f"Cascade deleted {interactions_deleted} interactions between {source_name} and {target_name}")
                    
            return True
                    
        except Exception as e:
            logger.error(f"Failed to delete relationship edge_id {edge_id}: {e}")
            return False
    
    def _delete_interactions_for_character_pair(
        self, 
        project_id: str, 
        source_character: str, 
        target_character: str
    ) -> int:
        """
        Delete all interactions between two specific characters (both directions).
        
        Args:
            project_id: Project UUID
            source_character: First character name
            target_character: Second character name
            
        Returns:
            Number of interactions deleted
        """
        # Get all interactions for this project
        all_interactions = self.get_all_interactions_for_project(project_id)
        
        if not all_interactions:
            return 0
        
        deleted_count = 0
        source_lower = source_character.lower().strip()
        target_lower = target_character.lower().strip()
        
        for interaction in all_interactions:
            src = interaction.get('source_character', '').lower().strip()
            tgt = interaction.get('target_character', '').lower().strip()
            
            # Check both directions (A->B and B->A)
            if (src == source_lower and tgt == target_lower) or \
               (src == target_lower and tgt == source_lower):
                vertex_id = interaction.get('vertex_id')
                if vertex_id:
                    try:
                        if self.delete_entity(project_id, int(vertex_id)):
                            deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Could not delete interaction {vertex_id}: {e}")
        
        return deleted_count
    
    def _delete_edge_metadata(self, edge_id: int) -> None:
        """Delete metadata record from novel_graph_edges table."""
        conn = None
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM novel_graph_edges 
                    WHERE edge_id = %s
                """, (edge_id,))
                conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.warning(f"Failed to delete edge metadata (non-critical): {e}")
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    # =========================================================================
    # Interaction Records Methods
    # =========================================================================
    
    def create_interaction(
        self,
        project_id: str,
        source_character: str,
        target_character: str,
        chapter_number: int,
        chapter_name: str,
        interaction_type: str,
        emotional_tone: str,
        sentiment_modifier: int,
        context: str,
        text_evidence: str,
        properties: Dict[str, Any] = None
    ) -> Optional[int]:
        """
        Create an interaction record vertex in the graph.
        
        Interactions are individual moments where two characters interact,
        which aggregate to form their overall relationship.
        
        Args:
            project_id: Project UUID
            source_character: Source character name
            target_character: Target character name
            chapter_number: Chapter order number
            chapter_name: Chapter name/title
            interaction_type: Type of interaction (e.g., SAVES, ARGUES_WITH, SUPPORTS)
            emotional_tone: Emotional tone (hostile, neutral, friendly, etc.)
            sentiment_modifier: Sentiment score contribution (-100 to +100)
            context: Description of the interaction
            text_evidence: Actual quote from the manuscript
            properties: Additional properties
            
        Returns:
            AGE vertex ID of the interaction, or None on error
        """
        if properties is None:
            properties = {}
        
        # Ensure Interaction vertex label exists
        if not self.create_vertex_label('Interaction'):
            logger.error("Failed to ensure Interaction vertex label exists")
            return None
        
        graph_draft_id = self._project_id_to_draft_id(project_id)
        
        # Build interaction name for uniqueness
        interaction_name = f"{source_character}_{target_character}_ch{chapter_number}_{interaction_type}"
        
        # Build full properties
        full_properties = {
            **properties,
            'source_character': source_character,
            'target_character': target_character,
            'chapter_number': chapter_number,
            'chapter_name': chapter_name,
            'interaction_type': interaction_type,
            'emotional_tone': emotional_tone,
            'sentiment_modifier': sentiment_modifier,
            'context': context,
            'text_evidence': text_evidence,
        }
        
        try:
            # Create vertex in AGE
            vertex_id = self.graph_service.create_vertex(
                draft_id=graph_draft_id,
                entity_name=interaction_name,
                entity_type='Interaction',
                properties=full_properties
            )
            
            # Create metadata record
            self._create_vertex_metadata(
                project_id=project_id,
                entity_type='interaction',
                entity_name=interaction_name,
                vertex_id=vertex_id,
                vertex_label='Interaction',
                properties=full_properties
            )
            
            logger.info(f"Created interaction: {interaction_name} (vertex_id: {vertex_id})")
            return vertex_id
            
        except Exception as e:
            logger.error(f"Failed to create interaction {interaction_name}: {e}")
            return None
    
    def get_interactions_for_characters(
        self,
        project_id: str,
        source_character: str,
        target_character: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get all interactions involving a character (or character pair).
        
        Args:
            project_id: Project UUID
            source_character: Character name (required)
            target_character: Optional second character for pair-specific interactions
            
        Returns:
            List of interaction records with properties
        """
        # Fetch all interactions and filter in Python (AGE Cypher JSON accessor issues)
        all_interactions = self.get_all_interactions_for_project(project_id)
        
        if not all_interactions:
            logger.info(f"No interactions found for project {project_id}")
            return []
        
        # Filter based on characters
        filtered = []
        source_lower = source_character.lower().strip()
        target_lower = target_character.lower().strip() if target_character else None
        
        for interaction in all_interactions:
            src = interaction.get('source_character', '').lower().strip()
            tgt = interaction.get('target_character', '').lower().strip()
            
            if target_lower:
                # Check both directions for character pair
                if (src == source_lower and tgt == target_lower) or \
                   (src == target_lower and tgt == source_lower):
                    filtered.append(interaction)
            else:
                # Any interaction involving the character
                if src == source_lower or tgt == source_lower:
                    filtered.append(interaction)
        
        # Sort by chapter number
        filtered.sort(key=lambda x: x.get('chapter_number', 0))
        
        logger.info(f"Retrieved {len(filtered)} interactions for {source_character}" + 
                   (f" <-> {target_character}" if target_character else ""))
        
        return filtered
    
    def get_all_interactions_for_project(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get all interactions for a project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            List of all interaction records
        """
        graph_draft_id = self._project_id_to_draft_id(project_id)
        interactions = []
        
        try:
            with self.graph_service.get_age_connection() as conn:
                with conn.cursor() as cursor:
                    safe_draft_id = self.graph_service._escape_cypher_string(graph_draft_id)
                    
                    # Simplified query without ORDER BY to avoid AGE JSON accessor issues
                    sql_query = f"""
                        SELECT v_name, v_props, v_id::bigint FROM ag_catalog.cypher('{self.graph_name}', $$
                        MATCH (v:Interaction {{draft_id: '{safe_draft_id}'}})
                        RETURN v.name, v.properties, id(v)
                        $$) AS (v_name agtype, v_props agtype, v_id agtype)
                    """
                    
                    cursor.execute(sql_query)
                    results = cursor.fetchall()
                    
                    for row in results:
                        try:
                            name_raw, props_raw, vid_raw = row
                            
                            name = str(name_raw).strip('"') if name_raw else ''
                            
                            props = {}
                            if props_raw:
                                if isinstance(props_raw, str):
                                    try:
                                        props = json.loads(props_raw)
                                    except json.JSONDecodeError:
                                        # Try with quote replacement
                                        props = json.loads(props_raw.replace("'", '"'))
                                elif isinstance(props_raw, dict):
                                    props = props_raw
                            
                            vertex_id = self._parse_agtype_vertex_id(vid_raw)
                            
                            interactions.append({
                                'vertex_id': vertex_id,
                                'name': name,
                                'source_character': props.get('source_character', ''),
                                'target_character': props.get('target_character', ''),
                                'chapter_number': props.get('chapter_number', 0),
                                'chapter_name': props.get('chapter_name', ''),
                                'interaction_type': props.get('interaction_type', ''),
                                'emotional_tone': props.get('emotional_tone', 'neutral'),
                                'sentiment_modifier': props.get('sentiment_modifier', 0),
                                'context': props.get('context', ''),
                                'text_evidence': props.get('text_evidence', ''),
                            })
                        except Exception as e:
                            logger.warning(f"Failed to parse interaction row: {e}")
                            continue
                    
                    # Sort by chapter number in Python
                    interactions.sort(key=lambda x: x.get('chapter_number', 0))
                    
                    logger.info(f"Retrieved {len(interactions)} total interactions for project {project_id}")
                    
        except Exception as e:
            logger.error(f"Failed to get all interactions: {e}")
        
        return interactions
    
    def aggregate_relationship_from_interactions(
        self,
        project_id: str,
        source_character: str,
        target_character: str
    ) -> Dict[str, Any]:
        """
        Aggregate interactions between two characters into a relationship summary.
        
        Args:
            project_id: Project UUID
            source_character: Source character name
            target_character: Target character name
            
        Returns:
            Aggregated relationship data with total sentiment score
        """
        interactions = self.get_interactions_for_characters(
            project_id, source_character, target_character
        )
        
        if not interactions:
            return {
                'source': source_character,
                'target': target_character,
                'sentiment_score': 0,
                'interaction_count': 0,
                'interactions': [],
                'dominant_tone': 'neutral'
            }
        
        # Calculate total sentiment
        total_sentiment = sum(i.get('sentiment_modifier', 0) for i in interactions)
        total_sentiment = max(-100, min(100, total_sentiment))  # Clamp to -100 to +100
        
        # Count emotional tones
        tone_counts = {}
        for i in interactions:
            tone = i.get('emotional_tone', 'neutral')
            tone_counts[tone] = tone_counts.get(tone, 0) + 1
        
        dominant_tone = max(tone_counts, key=tone_counts.get) if tone_counts else 'neutral'
        
        return {
            'source': source_character,
            'target': target_character,
            'sentiment_score': total_sentiment,
            'interaction_count': len(interactions),
            'interactions': interactions,
            'dominant_tone': dominant_tone,
            'tone_breakdown': tone_counts
        }
    
    def delete_interaction(self, project_id: str, vertex_id: int) -> bool:
        """
        Delete an interaction record.
        
        Args:
            project_id: Project UUID
            vertex_id: Interaction vertex ID
            
        Returns:
            True if successful, False otherwise
        """
        return self.delete_entity(project_id, vertex_id)
    
    def delete_all_interactions(self, project_id: str) -> int:
        """
        Delete ALL interaction records for a project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Number of interactions deleted
        """
        # First get all interactions
        interactions = self.get_all_interactions_for_project(project_id)
        deleted_count = 0
        
        for interaction in interactions:
            vertex_id = interaction.get('vertex_id')
            if vertex_id:
                try:
                    vertex_id_int = int(vertex_id)
                    if self.delete_entity(project_id, vertex_id_int):
                        deleted_count += 1
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not delete interaction {vertex_id}: {e}")
        
        logger.info(f"Deleted {deleted_count} interactions for project {project_id}")
        return deleted_count
    
    # =========================================================================
    # Custom Emotional Tones Management
    # =========================================================================
    
    def get_custom_emotional_tones(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get custom emotional tones for a project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            List of custom tone dictionaries
        """
        conn = None
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, name, description, created_at
                    FROM custom_emotional_tones
                    WHERE project_id = %s
                    ORDER BY name ASC
                """, (project_id,))
                
                rows = cursor.fetchall()
                tones = []
                for row in rows:
                    tones.append({
                        'id': str(row[0]),
                        'name': row[1],
                        'description': row[2] or '',
                        'created_at': row[3].isoformat() if row[3] else None,
                        'is_base': False
                    })
                
                return tones
                
        except Exception as e:
            # Table might not exist yet
            logger.debug(f"Could not get custom tones: {e}")
            return []
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def create_custom_emotional_tone(
        self, 
        project_id: str, 
        name: str, 
        description: str = ''
    ) -> Optional[str]:
        """
        Create a custom emotional tone.
        
        Args:
            project_id: Project UUID
            name: Tone name
            description: Tone description
            
        Returns:
            Tone ID if successful, None otherwise
        """
        conn = None
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                # Ensure table exists
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS custom_emotional_tones (
                        id SERIAL PRIMARY KEY,
                        project_id VARCHAR(255) NOT NULL,
                        name VARCHAR(100) NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(project_id, name)
                    )
                """)
                
                # Insert tone
                cursor.execute("""
                    INSERT INTO custom_emotional_tones (project_id, name, description)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (project_id, name, description))
                
                result = cursor.fetchone()
                conn.commit()
                
                if result:
                    tone_id = str(result[0])
                    logger.info(f"Created custom emotional tone: {name} (id: {tone_id})")
                    return tone_id
                
                return None
                
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to create custom tone: {e}")
            return None
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def delete_custom_emotional_tone(self, project_id: str, tone_id: str) -> bool:
        """
        Delete a custom emotional tone.
        
        Args:
            project_id: Project UUID
            tone_id: Tone ID
            
        Returns:
            True if successful, False otherwise
        """
        conn = None
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM custom_emotional_tones
                    WHERE id = %s AND project_id = %s
                """, (tone_id, project_id))
                
                deleted = cursor.rowcount > 0
                conn.commit()
                
                if deleted:
                    logger.info(f"Deleted custom emotional tone: {tone_id}")
                
                return deleted
                
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to delete custom tone: {e}")
            return False
        finally:
            if conn:
                self.db_pool.putconn(conn)


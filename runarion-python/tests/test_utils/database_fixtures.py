"""
Database fixtures and utilities for testing the deconstructor pipeline.
Provides setup/teardown, transaction isolation, and test data management.
"""

import uuid
import json
import logging
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from .sample_data import generate_ulid
from .database_operation_tracker import (
    get_operation_tracker, tracked_database_connection, 
    start_operation_tracking, stop_operation_tracking
)

logger = logging.getLogger(__name__)

class DatabaseFixture:
    """
    Manages database setup and teardown for testing.
    Provides transaction isolation and test data management.
    """
    
    def __init__(self, connection_pool):
        """
        Initialize the database fixture.
        
        Args:
            connection_pool: Database connection pool
        """
        self.connection_pool = connection_pool
        self.test_data = {}
        self._dependency_mode = False
        self._protected_records = set()
        self._persist_data = False  # Flag for data persistence
        self._operation_tracker = get_operation_tracker()
        self.created_records = {
            'drafts': [],
            'draft_chunks': [],
            'scenes': [],
            'plot_issues': [],
            'analysis_reports': [],
            'chapters': [],
            'final_manuscripts': [],
            'workspace_members': [],
            'workspaces': []
        }
    
    def setup(self):
        """Setup test database with necessary tables and data."""
        try:
            # Start operation tracking
            start_operation_tracking()
            
            # Ensure test tables exist (they should from migrations)
            self._ensure_test_tables()
            
            # Setup Apache AGE graph if enabled
            self._setup_age_graph()
            
            logger.info("Database fixture setup completed")
            
        except Exception as e:
            logger.error(f"Database fixture setup failed: {e}")
            raise
    
    def cleanup(self):
        """Clean up test data from database with enhanced transaction isolation."""
        try:
            # Stop operation tracking
            stop_operation_tracking()
            
            # Check if data persistence is enabled
            if self._persist_data:
                logger.info("Skipping database cleanup due to --persist-data flag")
                return
            
            conn = self.connection_pool.getconn()
            conn.autocommit = False  # Use transaction for cleanup
            
            try:
                with conn.cursor() as cursor:
                    # Clean up in reverse dependency order to respect foreign keys
                    cleanup_order = [
                        'draft_chunks',      # References drafts
                        'scenes',           # References drafts  
                        'plot_issues',      # References drafts
                        'analysis_reports', # References drafts
                        'chapters',         # References drafts
                        'final_manuscripts', # References drafts
                        'drafts',           # References workspaces and users
                        'workspace_members', # References workspaces and users
                        'workspaces'        # Base table
                    ]
                    
                    total_cleaned = 0
                    for table_name in cleanup_order:
                        if table_name in self.created_records and self.created_records[table_name]:
                            ids = self.created_records[table_name]
                            if ids:  # Only proceed if there are IDs to clean
                                # Filter out protected records if in dependency mode
                                if self._dependency_mode:
                                    protected_ids = {record_id for table, record_id in self._protected_records if table == table_name}
                                    ids_to_clean = [id for id in ids if id not in protected_ids]
                                    
                                    if protected_ids:
                                        logger.debug(f"Protecting {len(protected_ids)} records in {table_name} from cleanup")
                                else:
                                    ids_to_clean = ids
                                
                                if ids_to_clean:
                                    placeholders = ','.join(['%s'] * len(ids_to_clean))
                                    
                                    try:
                                        # Use appropriate ID column based on table
                                        id_column = 'id'
                                        if table_name == 'draft_chunks':
                                            id_column = 'id'  # draft_chunks uses auto-increment id
                                        
                                        delete_query = f"DELETE FROM {table_name} WHERE {id_column} IN ({placeholders})"
                                        cursor.execute(delete_query, ids_to_clean)
                                        
                                        cleaned_count = cursor.rowcount
                                        total_cleaned += cleaned_count
                                        
                                        if self._dependency_mode:
                                            logger.debug(f"Cleaned {cleaned_count} records from {table_name} (dependency mode: {len(ids) - len(ids_to_clean)} protected)")
                                        else:
                                            logger.debug(f"Cleaned {cleaned_count} records from {table_name}")
                                        
                                    except Exception as table_error:
                                        logger.warning(f"Could not clean table {table_name}: {table_error}")
                                        # Continue with other tables
                                else:
                                    logger.debug(f"All records in {table_name} are protected from cleanup")
                    
                    # Clean up graph data if AGE is enabled
                    try:
                        # Check if AGE extension exists
                        cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'age')")
                        age_exists = cursor.fetchone()[0]
                        
                        if age_exists:
                            # Check if AGE graph exists before cleaning
                            cursor.execute("""
                                SELECT EXISTS(SELECT 1 FROM ag_catalog.ag_graph WHERE name = 'novel_pipeline_graph_test')
                            """)
                            graph_exists = cursor.fetchone()[0]
                            
                            if graph_exists:
                                # Use direct cypher call for cleanup
                                cursor.execute("""
                                    SELECT * FROM ag_catalog.cypher('novel_pipeline_graph_test', $$
                                        MATCH (n)
                                        WHERE n.test_data = true
                                        DETACH DELETE n
                                        RETURN count(n)
                                    $$) AS (deleted_count agtype)
                                """)
                                logger.debug("Cleaned up test graph data")
                    except Exception as graph_error:
                        logger.warning(f"Could not clean graph data: {graph_error}")
                
                # Commit the cleanup transaction
                conn.commit()
                logger.info(f"Database fixture cleanup completed. Cleaned {total_cleaned} total records")
                
            except Exception as cleanup_error:
                # Rollback on any error
                conn.rollback()
                logger.error(f"Database cleanup transaction failed, rolled back: {cleanup_error}")
                raise
            finally:
                # Reset created_records tracking
                for key in self.created_records:
                    self.created_records[key] = []
                
                self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Database fixture cleanup failed: {e}")
            if 'conn' in locals():
                self.connection_pool.putconn(conn)
    
    def _ensure_test_tables(self):
        """Ensure all required test tables exist."""
        required_tables = [
            'drafts', 'draft_chunks', 'scenes', 'plot_issues',
            'analysis_reports', 'chapters', 'final_manuscripts',
            'workspace_members', 'workspaces'
        ]
        
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                for table in required_tables:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = %s
                        )
                    """, (table,))
                    
                    exists = cursor.fetchone()[0]
                    if not exists:
                        logger.warning(f"Table {table} does not exist - may need to run migrations")
        finally:
            self.connection_pool.putconn(conn)
    
    def _setup_age_graph(self):
        """Setup Apache AGE graph for testing."""
        try:
            conn = self.connection_pool.getconn()
            with conn.cursor() as cursor:
                # Check if AGE is available
                cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'age')")
                age_exists = cursor.fetchone()[0]
                
                if age_exists:
                    # Check if test graph already exists
                    cursor.execute("""
                        SELECT EXISTS(
                            SELECT 1 FROM ag_catalog.ag_graph 
                            WHERE name = 'novel_pipeline_graph_test'
                        )
                    """)
                    graph_exists = cursor.fetchone()[0]
                    
                    if not graph_exists:
                        # Create test graph only if it doesn't exist
                        cursor.execute("""
                            SELECT * FROM ag_catalog.create_graph('novel_pipeline_graph_test')
                        """)
                        logger.debug("Created test graph for AGE")
                    else:
                        logger.debug("Test graph already exists for AGE")
                else:
                    logger.warning("Apache AGE not available - graph tests may be skipped")
            
            self.connection_pool.putconn(conn)
            
        except Exception as e:
            logger.warning(f"Could not setup AGE graph: {e}")
            if 'conn' in locals():
                self.connection_pool.putconn(conn)
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions with rollback support and operation tracking."""
        with tracked_database_connection(self.connection_pool) as conn:
            try:
                conn.autocommit = False
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction rolled back: {e}")
                raise
    
    def get_existing_user_id(self) -> int:
        """
        Get an existing user ID from the Laravel-seeded database.
        Prefers the Super Admin user, falls back to any existing user.
        
        Returns:
            A valid user ID from the users table
            
        Raises:
            Exception: If no users are found in the database
        """
        conn = self.connection_pool.getconn()
        try:
            cursor = conn.cursor()
            
            # First try to get the Super Admin user created by Laravel seeding
            cursor.execute("""
                SELECT id FROM users 
                WHERE email = 'admin@runarion.com'
                LIMIT 1
            """)
            result = cursor.fetchone()
            
            if result:
                logger.debug(f"Using Laravel-seeded Super Admin user: {result[0]}")
                return result[0]
            
            # Fall back to any existing user
            cursor.execute("""
                SELECT id FROM users 
                ORDER BY id 
                LIMIT 1
            """)
            result = cursor.fetchone()
            
            if not result:
                raise Exception("No users found in database. Ensure Laravel seeders have been run with 'php artisan migrate:fresh --seed'.")
            
            logger.debug(f"Using existing user from Laravel seeding: {result[0]}")
            return result[0]
        finally:
            self.connection_pool.putconn(conn)
    
    def create_test_workspace(self, workspace_id: str = None, user_id: int = None) -> Dict[str, Any]:
        """
        Get or create a test workspace with user membership.
        Prefers using Laravel-seeded workspaces to avoid constraint violations.
        
        Args:
            workspace_id: Optional workspace ID (generates one if not provided)
            user_id: Optional user ID for workspace membership (uses existing user if not provided)
            
        Returns:
            Workspace data (may be existing Laravel-seeded workspace)
        """
        if user_id is None:
            user_id = self.get_existing_user_id()
        
        # First, try to use an existing Laravel-seeded workspace
        try:
            existing_workspace = self._get_existing_workspace_for_user(user_id)
            if existing_workspace:
                logger.debug(f"Using existing Laravel-seeded workspace: {existing_workspace['workspace_id']}")
                return existing_workspace
        except Exception as e:
            logger.warning(f"Could not get existing workspace: {e}")
        
        # If no existing workspace available, create a new one with improved uniqueness
        if workspace_id is None:
            workspace_id = generate_ulid()
        
        # Create workspace with enhanced uniqueness to avoid collisions
        import time
        import random
        timestamp_suffix = str(int(time.time() * 1000))[-6:]  # Last 6 digits of timestamp
        random_suffix = ''.join(random.choices('0123456789abcdef', k=4))
        workspace_name = f"Test Workspace {workspace_id[:8]}"
        base_slug = f"test-workspace-{workspace_id[:8].lower()}-{timestamp_suffix}-{random_suffix}"
        
        max_attempts = 3  # Reduced since we have better uniqueness
        
        for attempt in range(max_attempts):
            workspace_slug = base_slug
            if attempt > 0:
                # Add additional randomness for retries
                extra_suffix = ''.join(random.choices('0123456789abcdef', k=2))
                workspace_slug = f"{base_slug}-{extra_suffix}"
            
            try:
                # Use a fresh transaction for each attempt
                with self.transaction() as conn:
                    cursor = conn.cursor()
                    
                    # Try to create workspace
                    cursor.execute("""
                        INSERT INTO workspaces (id, name, slug, created_at, updated_at)
                        VALUES (%s, %s, %s, NOW(), NOW())
                        RETURNING id
                    """, (workspace_id, workspace_name, workspace_slug))
                    
                    workspace_result = cursor.fetchone()
                    if workspace_result:
                        self.created_records['workspaces'].append(workspace_result[0])
                    
                    # Create workspace membership in the same transaction
                    membership_id = generate_ulid()
                    cursor.execute("""
                        INSERT INTO workspace_members (id, workspace_id, user_id, role, created_at, updated_at)
                        VALUES (%s, %s, %s, 'owner', NOW(), NOW())
                    """, (membership_id, workspace_id, user_id))
                    
                    self.created_records['workspace_members'].append(membership_id)
                    
                    # If we get here, both insertions succeeded
                    break
                    
            except Exception as e:
                if "unique constraint" in str(e).lower() and "slug" in str(e).lower():
                    if attempt == max_attempts - 1:
                        logger.error(f"Failed to create unique workspace slug after {max_attempts} attempts. Last error: {e}")
                        raise Exception(f"Failed to create unique workspace slug after {max_attempts} attempts")
                    # Try again with a different slug and fresh transaction
                    logger.warning(f"Slug collision on attempt {attempt + 1}, retrying with different slug")
                    continue
                else:
                    # Re-raise non-slug related errors
                    logger.error(f"Non-slug error creating workspace: {e}")
                    raise
        
        workspace_data = {
            'workspace_id': workspace_id,
            'user_id': user_id,
            'role': 'owner'
        }
        
        logger.debug(f"Created test workspace: {workspace_id} with slug: {workspace_slug}")
        return workspace_data
    
    def create_test_draft(self, draft_id: str = None, workspace_id: str = None, 
                         user_id: int = 1, file_path: str = '/app/tests/sample_files/inputs/test_manuscript.txt') -> Dict[str, Any]:
        """
        Create a test draft record.
        
        Args:
            draft_id: Optional draft ID (generates one if not provided)
            workspace_id: Workspace ID (creates one if not provided)
            user_id: User ID
            file_path: Full path to the file for the draft
            
        Returns:
            Created draft data
        """
        if draft_id is None:
            draft_id = generate_ulid()
        
        if workspace_id is None:
            workspace_data = self.create_test_workspace(user_id=user_id)
            workspace_id = workspace_data['workspace_id']
        
        # Extract filename from path
        import os
        original_filename = os.path.basename(file_path)
        
        with self.transaction() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO drafts (
                    id, workspace_id, user_id, original_filename, file_path, file_size, 
                    status, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id
            """, (draft_id, workspace_id, user_id, original_filename, file_path, 1024, 'pending'))
            
            result = cursor.fetchone()
            if result:
                self.created_records['drafts'].append(result[0])
            
            draft_data = {
                'draft_id': draft_id,
                'workspace_id': workspace_id,
                'user_id': user_id,
                'original_filename': original_filename,
                'status': 'pending'
            }
            
            logger.debug(f"Created test draft: {draft_id}")
            return draft_data
    
    def create_test_chunks(self, draft_id: str, chunk_count: int = 3) -> List[Dict[str, Any]]:
        """
        Create test chunks for a draft.
        
        Args:
            draft_id: Draft ID
            chunk_count: Number of chunks to create
            
        Returns:
            List of created chunk data
        """
        chunks = []
        
        with self.transaction() as conn:
            cursor = conn.cursor()
            
            for i in range(chunk_count):
                chunk_text = f"Test chunk {i+1} content. This is sample text for testing purposes."
                
                cursor.execute("""
                    INSERT INTO draft_chunks (draft_id, chunk_number, raw_text, cleaned_text)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (draft_id, i+1, chunk_text, chunk_text))
                
                result = cursor.fetchone()
                if result:
                    self.created_records['draft_chunks'].append(result[0])
                
                chunks.append({
                    'chunk_id': result[0],
                    'draft_id': draft_id,
                    'chunk_number': i+1,
                    'raw_text': chunk_text,
                    'cleaned_text': chunk_text
                })
            
            logger.debug(f"Created {len(chunks)} test chunks for draft {draft_id}")
        
        return chunks
    
    def create_test_scenes(self, draft_id: str, scene_count: int = 2) -> List[Dict[str, Any]]:
        """
        Create test scenes for a draft.
        
        Args:
            draft_id: Draft ID
            scene_count: Number of scenes to create
            
        Returns:
            List of created scene data
        """
        scenes = []
        
        with self.transaction() as conn:
            cursor = conn.cursor()
            
            for i in range(scene_count):
                scene_data = {
                    'draft_id': draft_id,
                    'scene_number': i+1,
                    'title': f"Test Scene {i+1}",
                    'summary': f"Summary of test scene {i+1}",
                    'setting': f"Test setting {i+1}",
                    'characters': ['Character A', 'Character B'],
                    'original_content': f"Original content for scene {i+1}. This is test content."
                }
                
                cursor.execute("""
                    INSERT INTO scenes (
                        draft_id, scene_number, title, summary, setting, 
                        characters, original_content
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    draft_id, i+1, scene_data['title'], scene_data['summary'],
                    scene_data['setting'], json.dumps(scene_data['characters']),
                    scene_data['original_content']
                ))
                
                result = cursor.fetchone()
                if result:
                    self.created_records['scenes'].append(result[0])
                    scene_data['scene_id'] = result[0]
                
                scenes.append(scene_data)
            
            logger.debug(f"Created {len(scenes)} test scenes for draft {draft_id}")
        
        return scenes
    
    def get_draft_status(self, draft_id: str) -> Optional[str]:
        """
        Get the current status of a draft using standardized transaction pattern.
        
        Args:
            draft_id: Draft ID
            
        Returns:
            Current draft status or None if not found
        """
        from utils.database_utils import utf8_database_connection
        
        with utf8_database_connection(self.connection_pool) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT status FROM drafts WHERE id = %s", (draft_id,))
                result = cursor.fetchone()
                return result[0] if result else None
    
    def count_records(self, table_name: str, draft_id: str = None) -> int:
        """
        Count records in a table, optionally filtered by draft_id using standardized transaction pattern.
        
        Args:
            table_name: Name of the table
            draft_id: Optional draft ID filter
            
        Returns:
            Number of records
        """
        from utils.database_utils import utf8_database_connection
        
        with utf8_database_connection(self.connection_pool) as conn:
            with conn.cursor() as cursor:
                if draft_id:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE draft_id = %s", (draft_id,))
                else:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                
                result = cursor.fetchone()
                return result[0] if result else 0
    
    def execute_query(self, query: str, params: Tuple = None) -> List[Tuple]:
        """
        Execute a custom query and return results using standardized transaction pattern.
        
        Args:
            query: SQL query to execute
            params: Optional query parameters
            
        Returns:
            Query results
        """
        from utils.database_utils import utf8_database_connection
        
        # Use same transaction pattern as business logic
        with utf8_database_connection(self.connection_pool) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                
                # Commit for data-modifying operations to ensure changes are persisted
                if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                    conn.commit()
                
                # Check if the query returns results
                if cursor.description:
                    return cursor.fetchall()
                else:
                    # For INSERT, UPDATE, DELETE operations that don't return results
                    return []
    
    def simulate_processing_states(self, draft_id: str, target_stage: str) -> None:
        """
        Simulate different processing states for testing.
        
        Args:
            draft_id: Draft ID
            target_stage: Target stage to simulate ('stage_1_complete', 'stage_2_complete', etc.)
        """
        stage_mapping = {
            'processing': 'processing',
            'stage_1_complete': 'stage_1_complete',
            'stage_2_complete': 'stage_2_complete',
            'stage_3_complete': 'stage_3_complete',
            'stage_4_complete': 'stage_4_complete',
            'stage_5_complete': 'stage_5_complete',
            'stage_6_complete': 'stage_6_complete',
            'completed': 'completed',
            'failed': 'failed'
        }
        
        if target_stage not in stage_mapping:
            raise ValueError(f"Invalid target stage: {target_stage}")
        
        with self.transaction() as conn:
            cursor = conn.cursor()
            
            # Update draft status
            cursor.execute("""
                UPDATE drafts 
                SET status = %s, processing_started_at = NOW()
                WHERE id = %s
            """, (stage_mapping[target_stage], draft_id))
            
            # Create appropriate test data based on stage
            if target_stage in ['stage_1_complete', 'stage_2_complete', 'stage_3_complete']:
                # Create chunks
                if not self.count_records('draft_chunks', draft_id):
                    self.create_test_chunks(draft_id)
            
            if target_stage in ['stage_3_complete', 'stage_4_complete', 'stage_5_complete']:
                # Create scenes
                if not self.count_records('scenes', draft_id):
                    self.create_test_scenes(draft_id)
            
            logger.debug(f"Simulated processing state {target_stage} for draft {draft_id}")
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """
        Get column names for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column names
        """
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = %s 
                    ORDER BY ordinal_position
                """, (table_name,))
                
                columns = [row[0] for row in cursor.fetchall()]
                return columns
        finally:
            self.connection_pool.putconn(conn)
    
    def restore_table_from_json(self, table_name: str, json_file_path: str) -> bool:
        """
        Restore table data from a JSON file created by the output generator.
        
        Args:
            table_name: Name of the table to restore
            json_file_path: Path to JSON file containing table data
            
        Returns:
            True if restoration was successful, False otherwise
        """
        try:
            # Load JSON data
            with open(json_file_path, 'r', encoding='utf-8') as f:
                seed_data = json.load(f)
            
            if 'data' not in seed_data:
                logger.error(f"Invalid JSON structure in {json_file_path}: missing 'data' field")
                return False
                
            table_data = seed_data['data']
            if not table_data:
                logger.info(f"No data to restore for table {table_name}")
                return True
                
            # Get table columns
            columns = self.get_table_columns(table_name)
            if not columns:
                logger.error(f"Could not get columns for table {table_name}")
                return False
                
            with self.transaction() as conn:
                cursor = conn.cursor()
                
                # Clear existing data for this table (be careful!)
                # Only clear if we're restoring test data
                metadata = seed_data.get('metadata', {})
                draft_id = metadata.get('draft_id')
                
                if draft_id:
                    # Clear only data related to this draft
                    if table_name in ['drafts']:
                        cursor.execute(f"DELETE FROM {table_name} WHERE id = %s", (draft_id,))
                    else:
                        cursor.execute(f"DELETE FROM {table_name} WHERE draft_id = %s", (draft_id,))
                else:
                    logger.warning(f"No draft_id in metadata, clearing all data from {table_name}")
                    cursor.execute(f"DELETE FROM {table_name}")
                
                # Restore data
                for record in table_data:
                    # Build INSERT query dynamically
                    record_columns = list(record.keys())
                    record_values = [record[col] for col in record_columns]
                    
                    # Ensure all columns exist in the table
                    valid_columns = [col for col in record_columns if col in columns]
                    valid_values = [record[col] for col in valid_columns]
                    
                    if valid_columns:
                        placeholders = ','.join(['%s'] * len(valid_columns))
                        columns_str = ','.join(valid_columns)
                        
                        insert_query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
                        cursor.execute(insert_query, valid_values)
                
                # Track restored records for cleanup
                if table_name in self.created_records:
                    restored_ids = [record.get('id') for record in table_data if record.get('id')]
                    self.created_records[table_name].extend(restored_ids)
                
                logger.info(f"Restored {len(table_data)} records to {table_name} from {json_file_path}")
                return True
                
        except Exception as e:
            logger.error(f"Error restoring table {table_name} from {json_file_path}: {e}")
            return False
    
    def export_table_to_json(self, table_name: str, output_path: str, 
                           draft_id: str = None, additional_metadata: Dict[str, Any] = None) -> bool:
        """
        Export table data to JSON file for debugging or seeding.
        
        Args:
            table_name: Name of the table to export
            output_path: Path where to save the JSON file
            draft_id: Optional draft ID to filter data
            additional_metadata: Additional metadata to include
            
        Returns:
            True if export was successful, False otherwise
        """
        try:
            # Get table data
            if draft_id:
                if table_name == 'drafts':
                    query = f"SELECT * FROM {table_name} WHERE id = %s"
                else:
                    query = f"SELECT * FROM {table_name} WHERE draft_id = %s"
                rows = self.execute_query(query, (draft_id,))
            else:
                rows = self.execute_query(f"SELECT * FROM {table_name}")
            
            if not rows:
                logger.info(f"No data found in {table_name} for export")
                return True
                
            # Get column names
            columns = self.get_table_columns(table_name)
            
            # Convert to list of dictionaries
            table_data = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                table_data.append(row_dict)
            
            # Build export data
            export_data = {
                'metadata': {
                    'table_name': table_name,
                    'export_timestamp': datetime.now(timezone.utc).isoformat(),
                    'record_count': len(table_data),
                    'draft_id': draft_id
                },
                'data': table_data
            }
            
            # Add additional metadata
            if additional_metadata:
                export_data['metadata'].update(additional_metadata)
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Exported {len(table_data)} records from {table_name} to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting table {table_name} to {output_path}: {e}")
            return False
    
    def create_database_snapshot(self, draft_id: str, snapshot_dir: str, 
                               tables: List[str] = None) -> Dict[str, str]:
        """
        Create a complete database snapshot for a draft.
        
        Args:
            draft_id: Draft ID to create snapshot for
            snapshot_dir: Directory to save snapshot files
            tables: List of table names to include (defaults to all pipeline tables)
            
        Returns:
            Dictionary mapping table names to snapshot file paths
        """
        if tables is None:
            tables = ['drafts', 'draft_chunks', 'scenes', 'analysis_reports', 
                     'plot_issues', 'chapters', 'final_manuscripts']
        
        snapshot_files = {}
        
        for table_name in tables:
            snapshot_file = os.path.join(snapshot_dir, f"{table_name}.json")
            success = self.export_table_to_json(
                table_name=table_name,
                output_path=snapshot_file,
                draft_id=draft_id,
                additional_metadata={'snapshot_type': 'database_snapshot'}
            )
            
            if success:
                snapshot_files[table_name] = snapshot_file
            else:
                logger.warning(f"Failed to create snapshot for table {table_name}")
        
        logger.info(f"Created database snapshot with {len(snapshot_files)} tables in {snapshot_dir}")
        return snapshot_files
    
    def _get_existing_workspace_for_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get an existing workspace that the user is already a member of from Laravel seeding.
        
        Args:
            user_id: User ID to find workspace for
            
        Returns:
            Workspace data if found, None otherwise
        """
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Look for an existing workspace where the user is already a member
                cursor.execute("""
                    SELECT w.id, wm.role
                    FROM workspaces w
                    JOIN workspace_members wm ON w.id = wm.workspace_id
                    WHERE wm.user_id = %s
                    ORDER BY w.name = 'Demo Workspace' DESC, w.created_at ASC
                    LIMIT 1
                """, (user_id,))
                
                result = cursor.fetchone()
                if result:
                    workspace_id, role = result
                    return {
                        'workspace_id': workspace_id,
                        'user_id': user_id,
                        'role': role
                    }
                
                return None
        finally:
            self.connection_pool.putconn(conn)
    
    def enable_dependency_mode(self):
        """Enable dependency mode to prevent cleanup of stage dependency data."""
        self._dependency_mode = True
        logger.debug("Dependency mode enabled - stage data will be protected from cleanup")
    
    def disable_dependency_mode(self):
        """Disable dependency mode and allow normal cleanup."""
        self._dependency_mode = False
        self._protected_records.clear()
        logger.debug("Dependency mode disabled - normal cleanup will resume")
    
    def protect_records(self, table_name: str, record_ids: List[str]):
        """Protect specific records from cleanup during dependency mode."""
        if self._dependency_mode:
            for record_id in record_ids:
                self._protected_records.add((table_name, record_id))
            logger.debug(f"Protected {len(record_ids)} records in {table_name} from cleanup")
            
    def enable_data_persistence(self):
        """Enable data persistence (skip cleanup)."""
        self._persist_data = True
        logger.info("Data persistence enabled - cleanup will be skipped")
        
    def disable_data_persistence(self):
        """Disable data persistence (allow cleanup)."""
        self._persist_data = False
        logger.info("Data persistence disabled - cleanup will occur normally")
        
    def force_cleanup(self):
        """Force cleanup even if data persistence is enabled."""
        persist_state = self._persist_data
        self._persist_data = False
        try:
            self.cleanup()
        finally:
            self._persist_data = persist_state
            
            
    def cleanup_test_output_files(self):
        """Clean up test output files from previous runs."""
        try:
            from .path_manager import get_path_manager
            path_manager = get_path_manager()
            
            # Clean up temporary files
            path_manager.cleanup_temp_outputs()
            
            # Clean up stage output directories (but keep the directory structure)
            for stage in range(1, 8):
                stage_dir = path_manager.get_stage_expected_outputs_dir(stage)
                
                # Clean specific subdirectories
                for subdir in ['database_seeds', 'logs', 'performance', 'results']:
                    subdir_path = stage_dir / subdir
                    if subdir_path.exists():
                        cleaned_files = 0
                        for file_path in subdir_path.iterdir():
                            if file_path.is_file() and file_path.name != '.gitkeep':
                                file_path.unlink()
                                cleaned_files += 1
                        if cleaned_files > 0:
                            logger.info(f"Cleaned {cleaned_files} files from {subdir_path}")
            
            logger.info("Test output files cleanup completed")
            
        except Exception as e:
            logger.warning(f"Failed to clean test output files: {e}")
            
            
    def get_tracked_operations(self) -> List[Dict[str, Any]]:
        """Get all database operations tracked during this test."""
        return self._operation_tracker.get_operations()
        
    def get_operations_summary(self) -> Dict[str, Any]:
        """Get a summary of tracked database operations."""
        return self._operation_tracker.get_operations_summary()
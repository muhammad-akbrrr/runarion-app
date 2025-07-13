"""
Database fixtures and utilities for testing the deconstructor pipeline.
Provides setup/teardown, transaction isolation, and test data management.
"""

import uuid
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from .sample_data import generate_ulid

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
            # Ensure test tables exist (they should from migrations)
            self._ensure_test_tables()
            
            # Setup Apache AGE graph if enabled
            self._setup_age_graph()
            
            logger.info("Database fixture setup completed")
            
        except Exception as e:
            logger.error(f"Database fixture setup failed: {e}")
            raise
    
    def cleanup(self):
        """Clean up test data from database."""
        try:
            conn = self.connection_pool.getconn()
            conn.autocommit = True
            
            with conn.cursor() as cursor:
                # Clean up in reverse dependency order
                for table_name in reversed(list(self.created_records.keys())):
                    if self.created_records[table_name]:
                        ids = self.created_records[table_name]
                        placeholders = ','.join(['%s'] * len(ids))
                        
                        # All tables use 'id' as primary key, including workspace_members
                        cursor.execute(f"DELETE FROM {table_name} WHERE id IN ({placeholders})", ids)
                        
                        logger.debug(f"Cleaned {cursor.rowcount} records from {table_name}")
                
                # Clean up graph data if AGE is enabled
                try:
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
            
            self.connection_pool.putconn(conn)
            logger.info("Database fixture cleanup completed")
            
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
        """Context manager for database transactions with rollback support."""
        conn = self.connection_pool.getconn()
        try:
            conn.autocommit = False
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise
        finally:
            self.connection_pool.putconn(conn)
    
    def get_existing_user_id(self) -> int:
        """
        Get a random existing user ID from the seeded database.
        
        Returns:
            A valid user ID from the users table
            
        Raises:
            Exception: If no users are found in the database
        """
        conn = self.connection_pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM users 
                ORDER BY RANDOM() 
                LIMIT 1
            """)
            result = cursor.fetchone()
            if not result:
                raise Exception("No users found in database. Ensure Laravel seeders have been run.")
            return result[0]
        finally:
            self.connection_pool.putconn(conn)
    
    def create_test_workspace(self, workspace_id: str = None, user_id: int = None) -> Dict[str, Any]:
        """
        Create a test workspace with user membership.
        
        Args:
            workspace_id: Optional workspace ID (generates one if not provided)
            user_id: Optional user ID for workspace membership (uses existing user if not provided)
            
        Returns:
            Created workspace data
        """
        if workspace_id is None:
            workspace_id = generate_ulid()
        
        if user_id is None:
            user_id = self.get_existing_user_id()
        
        # Create workspace with unique slug handling - retry with fresh transactions
        workspace_name = f"Test Workspace {workspace_id[:8]}"
        base_slug = f"test-workspace-{workspace_id[:8].lower()}"
        
        max_attempts = 5
        workspace_slug = None
        
        for attempt in range(max_attempts):
            if attempt == 0:
                workspace_slug = base_slug
            else:
                # Add random suffix to ensure uniqueness
                import random
                random_suffix = ''.join(random.choices('0123456789abcdef', k=4))
                workspace_slug = f"{base_slug}-{random_suffix}"
            
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
                        raise Exception(f"Failed to create unique workspace slug after {max_attempts} attempts")
                    # Try again with a different slug and fresh transaction
                    continue
                else:
                    # Re-raise non-slug related errors
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
        Get the current status of a draft.
        
        Args:
            draft_id: Draft ID
            
        Returns:
            Current draft status or None if not found
        """
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT status FROM drafts WHERE id = %s", (draft_id,))
                result = cursor.fetchone()
                return result[0] if result else None
        finally:
            self.connection_pool.putconn(conn)
    
    def count_records(self, table_name: str, draft_id: str = None) -> int:
        """
        Count records in a table, optionally filtered by draft_id.
        
        Args:
            table_name: Name of the table
            draft_id: Optional draft ID filter
            
        Returns:
            Number of records
        """
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                if draft_id:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE draft_id = %s", (draft_id,))
                else:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                
                result = cursor.fetchone()
                return result[0] if result else 0
        finally:
            self.connection_pool.putconn(conn)
    
    def execute_query(self, query: str, params: Tuple = None) -> List[Tuple]:
        """
        Execute a custom query and return results.
        
        Args:
            query: SQL query to execute
            params: Optional query parameters
            
        Returns:
            Query results
        """
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        finally:
            self.connection_pool.putconn(conn)
    
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
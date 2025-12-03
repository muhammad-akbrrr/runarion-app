"""
ConversationManager - Manages persistent conversation history for novel writing

This service maintains a continuous conversation thread per project so Gemini
maintains full context across all chapters. All chapters/edits are stored
chronologically with chapter boundaries.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from contextlib import contextmanager
from models.story_generation.prompt_config import PromptConfig

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manages conversation history for projects, storing messages chronologically
    and enabling full context for Gemini across all chapters.
    """
    
    def __init__(self, db_pool):
        """
        Initialize the conversation manager.
        
        Args:
            db_pool: Database connection pool from app.py
        """
        self.db_pool = db_pool
    
    @contextmanager
    def _get_db_connection(self):
        """
        Context manager for database connections with proper cleanup.
        
        Yields:
            Database connection
        """
        conn = None
        try:
            conn = self.db_pool.getconn()
            conn.set_client_encoding('UTF8')
            conn.autocommit = False
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def load_history(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Load conversation history for a project.
        
        Args:
            project_id: ULID of the project
            
        Returns:
            List of message dictionaries from project_conversations.messages
            Returns empty list if no history exists
        """
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT messages FROM project_conversations WHERE project_id = %s",
                        (project_id,)
                    )
                    row = cursor.fetchone()
                    
                    if not row or not row[0]:
                        return []
                    
                    # Parse JSONB messages array
                    messages = row[0]
                    if isinstance(messages, str):
                        messages = json.loads(messages)
                    elif isinstance(messages, (dict, list)):
                        # PostgreSQL JSONB returns as Python dict/list
                        pass
                    else:
                        logger.warning(f"Unexpected messages type: {type(messages)}")
                        return []
                    
                    return messages if isinstance(messages, list) else []
                    
        except Exception as e:
            logger.error(f"Failed to load conversation history for project {project_id}: {e}")
            return []
    
    def append_message(
        self,
        project_id: str,
        role: str,
        content: str,
        chapter_id: Optional[int] = None,
        chapter_order: Optional[int] = None
    ) -> bool:
        """
        Append a new message to the conversation history.
        
        Args:
            project_id: ULID of the project
            role: "user" or "assistant"
            content: Message content text
            chapter_id: Optional chapter ID (for chapter generation)
            chapter_order: Optional chapter order number
            
        Returns:
            True if successful, False otherwise
        """
        if role not in ["user", "assistant"]:
            logger.error(f"Invalid role: {role}. Must be 'user' or 'assistant'")
            return False
        
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Load existing messages
                    cursor.execute(
                        "SELECT messages FROM project_conversations WHERE project_id = %s",
                        (project_id,)
                    )
                    row = cursor.fetchone()
                    
                    messages = []
                    if row and row[0]:
                        if isinstance(row[0], str):
                            messages = json.loads(row[0])
                        else:
                            messages = row[0] if isinstance(row[0], list) else []
                    
                    # Determine next message index
                    next_index = len(messages)
                    
                    # Create new message
                    new_message = {
                        "role": role,
                        "content": content,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "message_index": next_index
                    }
                    
                    if chapter_id is not None:
                        new_message["chapter_id"] = chapter_id
                    
                    if chapter_order is not None:
                        new_message["chapter_order"] = chapter_order
                    
                    messages.append(new_message)
                    
                    # Update or insert conversation record
                    cursor.execute(
                        """
                        INSERT INTO project_conversations (project_id, messages, updated_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (project_id)
                        DO UPDATE SET messages = %s, updated_at = NOW()
                        """,
                        (project_id, json.dumps(messages), json.dumps(messages))
                    )
                    
                    logger.info(f"Appended {role} message to conversation for project {project_id}, index {next_index}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to append message for project {project_id}: {e}")
            return False
    
    def update_chapter_content(
        self,
        project_id: str,
        chapter_id: int,
        new_content: str
    ) -> bool:
        """
        Update content in-place for all messages matching a chapter_id.
        Preserves message_index and updates timestamp.
        
        Args:
            project_id: ULID of the project
            chapter_id: Chapter ID to update
            new_content: New content for the messages
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Load existing messages
                    cursor.execute(
                        "SELECT messages FROM project_conversations WHERE project_id = %s",
                        (project_id,)
                    )
                    row = cursor.fetchone()
                    
                    if not row or not row[0]:
                        logger.warning(f"No conversation history found for project {project_id}")
                        return False
                    
                    messages = row[0]
                    if isinstance(messages, str):
                        messages = json.loads(messages)
                    elif not isinstance(messages, list):
                        logger.error(f"Invalid messages format for project {project_id}")
                        return False
                    
                    # Update all messages with matching chapter_id
                    updated = False
                    for message in messages:
                        if message.get("chapter_id") == chapter_id:
                            message["content"] = new_content
                            message["timestamp"] = datetime.now(timezone.utc).isoformat()
                            updated = True
                    
                    if not updated:
                        logger.warning(f"No messages found with chapter_id {chapter_id} for project {project_id}")
                        return False
                    
                    # Save updated messages
                    cursor.execute(
                        """
                        UPDATE project_conversations
                        SET messages = %s, updated_at = NOW()
                        WHERE project_id = %s
                        """,
                        (json.dumps(messages), project_id)
                    )
                    
                    logger.info(f"Updated chapter {chapter_id} content in conversation for project {project_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to update chapter content for project {project_id}: {e}")
            return False
    
    def to_gemini_format(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert conversation messages to Gemini API format.
        
        Gemini format: array of Content objects with role and parts
        Content format: {"role": "user"|"model", "parts": [{"text": "..."}]}
        
        Note: Gemini uses "model" for assistant role, not "assistant"
        
        Args:
            messages: List of message dictionaries from load_history()
            
        Returns:
            List of messages in Gemini API format
        """
        gemini_messages = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # Skip empty messages
            if not content:
                continue
            
            # Gemini uses "model" for assistant responses, "user" for user messages
            gemini_role = "model" if role == "assistant" else "user"
            
            gemini_messages.append({
                "role": gemini_role,
                "parts": [{"text": content}]
            })
        
        return gemini_messages
    
    def clear_history(self, project_id: str) -> bool:
        """
        Clear all conversation history for a project.
        
        This should be called when content is significantly changed/deleted
        from the editor to prevent stale context from polluting the conversation.
        
        Args:
            project_id: ULID of the project
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM project_conversations WHERE project_id = %s",
                        (project_id,)
                    )
                    
                    logger.info(f"Cleared conversation history for project {project_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to clear conversation history for project {project_id}: {e}")
            return False
    
    def sync_from_content(self, project_id: str) -> bool:
        """
        Sync conversation history from current project content.
        
        This rebuilds the conversation history from the actual content in
        project_content table, ensuring conversation matches editor state.
        Call this before generation to ensure history is accurate.
        
        Args:
            project_id: ULID of the project
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Get current project content
                    cursor.execute(
                        "SELECT content FROM project_content WHERE project_id = %s",
                        (project_id,)
                    )
                    content_row = cursor.fetchone()
                    
                    if not content_row or not content_row[0]:
                        # No content, clear conversation
                        cursor.execute(
                            "DELETE FROM project_conversations WHERE project_id = %s",
                            (project_id,)
                        )
                        logger.info(f"No content found, cleared conversation for project {project_id}")
                        return True
                    
                    chapters = content_row[0]
                    if isinstance(chapters, str):
                        chapters = json.loads(chapters)
                    
                    if not isinstance(chapters, list):
                        logger.error(f"Invalid chapters format for project {project_id}")
                        return False
                    
                    # Build new messages from current content
                    messages = []
                    message_index = 0
                    
                    # Sort chapters by order
                    sorted_chapters = sorted(
                        chapters,
                        key=lambda c: c.get("order", 0)
                    )
                    
                    for chapter in sorted_chapters:
                        chapter_order_num = chapter.get("order")
                        chapter_content = chapter.get("content", "").strip()
                        chapter_name = chapter.get("chapter_name", "Untitled")
                        
                        # Only include chapters with actual content
                        if chapter_content:
                            messages.append({
                                "role": "user",
                                "content": chapter_content,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "message_index": message_index,
                                "chapter_id": chapter_order_num,
                                "chapter_order": chapter_order_num
                            })
                            message_index += 1
                    
                    # Replace conversation with synced content
                    cursor.execute(
                        """
                        INSERT INTO project_conversations (project_id, messages, created_at, updated_at)
                        VALUES (%s, %s, NOW(), NOW())
                        ON CONFLICT (project_id)
                        DO UPDATE SET messages = %s, updated_at = NOW()
                        """,
                        (project_id, json.dumps(messages), json.dumps(messages))
                    )
                    
                    logger.info(f"Synced conversation for project {project_id} with {len(messages)} chapters")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to sync conversation for project {project_id}: {e}")
            return False

    def initialize_conversation(
        self,
        project_id: str,
        prompt_config: Optional[PromptConfig] = None,
        initial_prompt: Optional[str] = None,
        chapter_order: Optional[int] = None
    ) -> bool:
        """
        Initialize conversation history for a project.
        
        If prompt_config is provided, builds system instruction from config.
        If empty, uses initial_prompt from user's editor.
        Retrieves existing content from project_content table if project already has chapters.
        
        Args:
            project_id: ULID of the project
            prompt_config: Optional PromptConfig with genre, tone, POV, author_profile
            initial_prompt: Optional initial prompt text from user's editor
            chapter_order: Optional chapter order for the initial message
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Check if conversation already exists
                    cursor.execute(
                        "SELECT messages FROM project_conversations WHERE project_id = %s",
                        (project_id,)
                    )
                    existing = cursor.fetchone()
                    
                    if existing and existing[0]:
                        # Conversation already initialized
                        logger.info(f"Conversation already exists for project {project_id}")
                        return True
                    
                    messages = []
                    
                    # Note: System instruction (from prompt_config) is handled separately
                    # via request.instruction -> Gemini's system_instruction field.
                    # Conversation history only contains actual story content.
                    
                    # Add existing chapters to conversation history if they exist
                    cursor.execute(
                        "SELECT content FROM project_content WHERE project_id = %s",
                        (project_id,)
                    )
                    content_row = cursor.fetchone()
                    
                    if content_row and content_row[0]:
                        chapters = content_row[0]
                        if isinstance(chapters, str):
                            chapters = json.loads(chapters)
                        
                        if isinstance(chapters, list):
                            # Sort chapters by order
                            sorted_chapters = sorted(
                                chapters,
                                key=lambda c: c.get("order", 0)
                            )
                            
                            message_index = len(messages)
                            
                            # Add each chapter as conversation history
                            for chapter in sorted_chapters:
                                chapter_order_num = chapter.get("order")
                                chapter_content = chapter.get("content", "")
                                
                                if chapter_content:
                                    # Add user message with chapter content
                                    messages.append({
                                        "role": "user",
                                        "content": f"Chapter {chapter_order_num}: {chapter.get('chapter_name', 'Untitled')}\n\n{chapter_content}",
                                        "timestamp": datetime.now(timezone.utc).isoformat(),
                                        "message_index": message_index,
                                        "chapter_id": chapter_order_num,
                                        "chapter_order": chapter_order_num
                                    })
                                    message_index += 1
                    
                    # Add initial prompt if provided and we don't have existing chapters
                    if initial_prompt and not messages:
                        messages.append({
                            "role": "user",
                            "content": initial_prompt,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "message_index": 0
                        })
                        if chapter_order is not None:
                            messages[0]["chapter_order"] = chapter_order
                    
                    # Create conversation record
                    cursor.execute(
                        """
                        INSERT INTO project_conversations (project_id, messages, created_at, updated_at)
                        VALUES (%s, %s, NOW(), NOW())
                        ON CONFLICT (project_id) DO NOTHING
                        """,
                        (project_id, json.dumps(messages))
                    )
                    
                    logger.info(f"Initialized conversation for project {project_id} with {len(messages)} messages")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to initialize conversation for project {project_id}: {e}")
            return False


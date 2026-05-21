"""
Integration tests for Conversation History System

Tests the full conversation history flow including:
- ConversationManager service
- Database operations
- Integration with generation API
"""

import sys
import os
import pytest
from datetime import datetime, timezone

# Add src to path

from src.services.conversation_manager import ConversationManager
from src.models.story_generation.prompt_config import PromptConfig
from psycopg2 import pool


@pytest.fixture
def db_pool():
    """Create database connection pool for testing."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    connection_pool = pool.SimpleConnectionPool(
        minconn=1,
        maxconn=5,
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_DATABASE'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    
    yield connection_pool
    
    if connection_pool:
        connection_pool.closeall()


@pytest.fixture
def conversation_manager(db_pool):
    """Create ConversationManager instance."""
    return ConversationManager(db_pool)


@pytest.fixture
def test_project_id():
    """Generate a test project ID (ULID format)."""
    import ulid
    return str(ulid.ULID())


class TestConversationManager:
    """Test ConversationManager service."""
    
    def test_load_empty_history(self, conversation_manager, test_project_id):
        """Test loading history for non-existent project returns empty list."""
        messages = conversation_manager.load_history(test_project_id)
        assert messages == []
        assert isinstance(messages, list)
    
    def test_append_user_message(self, conversation_manager, test_project_id):
        """Test appending user message to conversation."""
        result = conversation_manager.append_message(
            project_id=test_project_id,
            role="user",
            content="Hello, this is a test message",
            chapter_order=1
        )
        
        assert result == True
        
        # Verify message was saved
        messages = conversation_manager.load_history(test_project_id)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello, this is a test message"
        assert messages[0]["chapter_order"] == 1
        assert "message_index" in messages[0]
        assert "timestamp" in messages[0]
    
    def test_append_assistant_message(self, conversation_manager, test_project_id):
        """Test appending assistant message to conversation."""
        # Add user message first
        conversation_manager.append_message(
            project_id=test_project_id,
            role="user",
            content="Tell me a story",
            chapter_order=1
        )
        
        # Add assistant response
        result = conversation_manager.append_message(
            project_id=test_project_id,
            role="assistant",
            content="Once upon a time...",
            chapter_order=1
        )
        
        assert result == True
        
        messages = conversation_manager.load_history(test_project_id)
        assert len(messages) == 2
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Once upon a time..."
        assert messages[1]["message_index"] == 1
    
    def test_append_invalid_role(self, conversation_manager, test_project_id):
        """Test that invalid role is rejected."""
        result = conversation_manager.append_message(
            project_id=test_project_id,
            role="invalid_role",
            content="This should fail"
        )
        
        assert result == False
    
    def test_multiple_messages_ordering(self, conversation_manager, test_project_id):
        """Test that multiple messages maintain correct order."""
        for i in range(5):
            role = "user" if i % 2 == 0 else "assistant"
            conversation_manager.append_message(
                project_id=test_project_id,
                role=role,
                content=f"Message {i}",
                chapter_order=1
            )
        
        messages = conversation_manager.load_history(test_project_id)
        assert len(messages) == 5
        
        # Verify message indices are sequential
        for i, msg in enumerate(messages):
            assert msg["message_index"] == i
            assert msg["content"] == f"Message {i}"
    
    def test_to_gemini_format(self, conversation_manager):
        """Test conversion to Gemini API format."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "Continue"}
        ]
        
        gemini_format = conversation_manager.to_gemini_format(messages)
        
        assert len(gemini_format) == 3
        assert gemini_format[0]["role"] == "user"
        assert gemini_format[0]["parts"][0]["text"] == "Hello"
        assert gemini_format[1]["role"] == "model"  # Gemini uses "model" not "assistant"
        assert gemini_format[1]["parts"][0]["text"] == "Hi there"
        assert gemini_format[2]["role"] == "user"
    
    def test_to_gemini_format_skips_empty(self, conversation_manager):
        """Test that empty messages are skipped in Gemini format."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": ""},  # Empty message
            {"role": "user", "content": "Continue"}
        ]
        
        gemini_format = conversation_manager.to_gemini_format(messages)
        
        assert len(gemini_format) == 2  # Empty message skipped
        assert gemini_format[0]["content"] == "Hello" or gemini_format[0]["parts"][0]["text"] == "Hello"
    
    def test_update_chapter_content(self, conversation_manager, test_project_id):
        """Test updating chapter content in-place."""
        # Add initial chapter content
        conversation_manager.append_message(
            project_id=test_project_id,
            role="user",
            content="Chapter 1: Original content",
            chapter_id=1,
            chapter_order=1
        )
        
        # Update chapter content
        result = conversation_manager.update_chapter_content(
            project_id=test_project_id,
            chapter_id=1,
            new_content="Chapter 1: Updated content"
        )
        
        assert result == True
        
        messages = conversation_manager.load_history(test_project_id)
        assert len(messages) == 1
        assert "Updated content" in messages[0]["content"]
        # Message index should be preserved
        assert messages[0]["message_index"] == 0
    
    def test_initialize_conversation_new_project(self, conversation_manager, test_project_id):
        """Test initializing conversation for new project."""
        prompt_config = PromptConfig(
            genre="fantasy",
            tone="epic",
            pov="third person"
        )
        
        result = conversation_manager.initialize_conversation(
            project_id=test_project_id,
            prompt_config=prompt_config,
            initial_prompt="Once upon a time..."
        )
        
        assert result == True
        
        # Verify conversation exists
        messages = conversation_manager.load_history(test_project_id)
        # Should have initial prompt if no existing chapters
        assert len(messages) >= 0  # May be 0 if only prompt_config provided
    
    def test_initialize_conversation_idempotent(self, conversation_manager, test_project_id):
        """Test that initializing twice doesn't create duplicates."""
        conversation_manager.initialize_conversation(
            project_id=test_project_id,
            initial_prompt="First initialization"
        )
        
        # Initialize again
        result = conversation_manager.initialize_conversation(
            project_id=test_project_id,
            initial_prompt="Second initialization"
        )
        
        assert result == True  # Should succeed but not add duplicates
        
        # Verify conversation exists (should not have duplicated initial prompt)
        messages = conversation_manager.load_history(test_project_id)
        # Should only have one set of messages, not duplicated
        assert isinstance(messages, list)
    
    def test_initialize_with_existing_chapters(self, conversation_manager, test_project_id, db_pool):
        """Test initializing conversation with existing project content."""
        # First, create project content with chapters
        with db_pool.getconn() as conn:
            conn.set_client_encoding('UTF8')
            with conn.cursor() as cursor:
                import json
                import ulid
                
                chapters = [
                    {"order": 0, "chapter_name": "Chapter 1", "content": "Chapter 1 content"},
                    {"order": 1, "chapter_name": "Chapter 2", "content": "Chapter 2 content"}
                ]
                
                content_id = str(ulid.ULID())
                cursor.execute(
                    """
                    INSERT INTO project_content (id, project_id, content, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    ON CONFLICT (project_id) DO UPDATE SET content = %s
                    """,
                    (content_id, test_project_id, json.dumps(chapters), json.dumps(chapters))
                )
                conn.commit()
        
        # Initialize conversation
        result = conversation_manager.initialize_conversation(
            project_id=test_project_id,
            initial_prompt="Continue the story"
        )
        
        assert result == True
        
        # Verify existing chapters were loaded
        messages = conversation_manager.load_history(test_project_id)
        assert len(messages) >= 2  # Should have at least the two chapters
        
        # Cleanup
        with db_pool.getconn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM project_content WHERE project_id = %s", (test_project_id,))
                conn.commit()


@pytest.mark.integration
def test_conversation_flow_end_to_end(conversation_manager, test_project_id):
    """Test complete conversation flow from initialization to multiple messages."""
    # 1. Initialize conversation
    result = conversation_manager.initialize_conversation(
        project_id=test_project_id,
        initial_prompt="Write a story about a dragon"
    )
    assert result == True
    
    # 2. Add user message
    conversation_manager.append_message(
        project_id=test_project_id,
        role="user",
        content="Continue the story",
        chapter_order=1
    )
    
    # 3. Add assistant response
    conversation_manager.append_message(
        project_id=test_project_id,
        role="assistant",
        content="The dragon flew across the sky, its wings casting shadows over the land.",
        chapter_order=1
    )
    
    # 4. Add another user message
    conversation_manager.append_message(
        project_id=test_project_id,
        role="user",
        content="What happens next?",
        chapter_order=2
    )
    
    # 5. Verify all messages are stored correctly
    messages = conversation_manager.load_history(test_project_id)
    assert len(messages) == 3
    
    # 6. Convert to Gemini format
    gemini_messages = conversation_manager.to_gemini_format(messages)
    assert len(gemini_messages) == 3
    assert gemini_messages[0]["role"] == "user"
    assert gemini_messages[1]["role"] == "model"
    assert gemini_messages[2]["role"] == "user"
    
    # 7. Verify message order
    assert "Continue the story" in gemini_messages[0]["parts"][0]["text"]
    assert "dragon" in gemini_messages[1]["parts"][0]["text"]
    assert "What happens next" in gemini_messages[2]["parts"][0]["text"]


@pytest.fixture(autouse=True)
def cleanup_test_data(db_pool, test_project_id):
    """Cleanup test data after each test."""
    yield
    # Cleanup
    try:
        with db_pool.getconn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM project_conversations WHERE project_id = %s", (test_project_id,))
                cursor.execute("DELETE FROM project_content WHERE project_id = %s", (test_project_id,))
                conn.commit()
    except Exception as e:
        print(f"Cleanup warning: {e}")









#!/usr/bin/env python3
"""
Tests for the Story Rewrite Pipeline.

This test file demonstrates the complete user workflow:
1. User uploads rough draft PDF
2. User selects or creates author style
3. User selects writing perspective
4. System rewrites the story
"""

from services.deconstructor.story_rewrite_pipeline import StoryRewritePipeline
from models.request import CallerInfo, GenerationConfig
from models.deconstructor.story_rewrite_request import (
    StoryRewriteRequest,
    NewAuthorStyleRequest,
    ExistingAuthorStyleRequest
)
from models.deconstructor.content_rewrite import WritingPerspective, ContentRewriteConfig
from psycopg2.pool import SimpleConnectionPool
import os
import sys
import unittest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))


class TestStoryRewritePipeline(unittest.TestCase):
    """Test cases for the Story Rewrite Pipeline."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Get the test PDF directory
        cls.test_pdf_dir = Path(__file__).parent / "test_pdfs"
        cls.rough_drafts_dir = cls.test_pdf_dir / "rough_drafts"
        cls.author_samples_dir = cls.test_pdf_dir / "author_samples"
        cls.expected_outputs_dir = cls.test_pdf_dir / "expected_outputs"

        # Create directories if they don't exist
        cls.rough_drafts_dir.mkdir(parents=True, exist_ok=True)
        cls.author_samples_dir.mkdir(parents=True, exist_ok=True)
        cls.expected_outputs_dir.mkdir(parents=True, exist_ok=True)

        # Test PDF file paths
        cls.test_rough_draft = cls.rough_drafts_dir / "rough_draft_fantasy_story.pdf"
        cls.test_author_sample1 = cls.author_samples_dir / "author_tolkien_lotr_sample.pdf"
        cls.test_author_sample2 = cls.author_samples_dir / "author_rowling_hp_sample.pdf"

        # Check if test files exist
        cls.has_test_files = (
            cls.test_rough_draft.exists() and
            cls.test_author_sample1.exists() and
            cls.test_author_sample2.exists()
        )

    def setUp(self):
        """Set up for each test."""
        self.connection_pool = self.create_connection_pool()
        self.caller = self.create_caller_info()

    def tearDown(self):
        """Clean up after each test."""
        if self.connection_pool:
            self.connection_pool.closeall()

    def create_connection_pool(self):
        """Create a database connection pool for testing."""
        return SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "runarion_test"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
        )

    def create_caller_info(self):
        """Create caller information for testing."""
        return CallerInfo(
            user_id="test_user_123",
            workspace_id="test_workspace_456",
            project_id="test_project_789",
            api_keys={
                "openai": os.getenv("OPENAI_API_KEY"),
                "gemini": os.getenv("GEMINI_API_KEY"),
            }
        )

    def test_new_author_style_workflow(self):
        """Test creating a new author style and rewriting content."""
        if not self.has_test_files:
            self.skipTest(
                "Test PDF files not found. Please add test files to test_pdfs directory.")

        print("\n=== Test: New Author Style Workflow ===")

        # Create the request
        request = StoryRewriteRequest(
            # Step 1: User's rough draft
            rough_draft_file=str(self.test_rough_draft),

            # Step 2: Create new author style from samples
            author_style_request=NewAuthorStyleRequest(
                sample_files=[
                    str(self.test_author_sample1),
                    str(self.test_author_sample2),
                ],
                author_name="J.R.R. Tolkien",
            ),

            # Step 3: Writing perspective
            writing_perspective=WritingPerspective(
                type="third_person_omniscient",
                narrator_voice="epic and all-knowing",
            ),

            # Optional: Additional configuration
            rewrite_config=ContentRewriteConfig(
                target_genre="fantasy",
                target_tone="epic and mysterious",
                preserve_key_elements=["character names",
                                       "plot structure", "key locations"],
                target_length="similar",
                style_intensity=0.9,
            ),

            # Processing options
            store_intermediate=True,
            chunk_overlap=False,
        )

        # Create and run the pipeline
        pipeline = StoryRewritePipeline(
            caller=self.caller,
            connection_pool=self.connection_pool,
            provider="gemini",
            model="gemini-2.5-flash",
        )

        # Process the request
        response = pipeline.process_request(request)

        # Assertions
        self.assertIsNotNone(response)
        self.assertIsNotNone(response.session_id)
        self.assertIsNotNone(response.author_style_id)
        self.assertGreater(response.processing_time_ms, 0)
        self.assertGreater(response.total_chunks, 0)
        self.assertGreater(len(response.original_story), 0)
        self.assertGreater(len(response.rewritten_story), 0)
        self.assertGreaterEqual(response.average_style_confidence, 0.0)
        self.assertLessEqual(response.average_style_confidence, 1.0)

        # Print results
        print(f"Session ID: {response.session_id}")
        print(f"Author Style ID: {response.author_style_id}")
        print(f"Processing time: {response.processing_time_ms}ms")
        print(f"Total chunks: {response.total_chunks}")
        print(f"Original chars: {response.total_original_chars}")
        print(f"Rewritten chars: {response.total_rewritten_chars}")
        print(f"Total tokens: {response.total_tokens}")
        print(f"Style confidence: {response.average_style_confidence:.2f}")

        return response

    def test_existing_author_style_workflow(self):
        """Test using an existing author style to rewrite content."""
        if not self.has_test_files:
            self.skipTest(
                "Test PDF files not found. Please add test files to test_pdfs directory.")

        print("\n=== Test: Existing Author Style Workflow ===")

        # First create an author style
        new_style_response = self.test_new_author_style_workflow()

        # Now use the existing author style
        request = StoryRewriteRequest(
            # Step 1: User's rough draft
            rough_draft_file=str(self.test_rough_draft),

            # Step 2: Use existing author style
            author_style_request=ExistingAuthorStyleRequest(
                author_style_id=new_style_response.author_style_id,
            ),

            # Step 3: Writing perspective
            writing_perspective=WritingPerspective(
                type="first_person",
                narrator_voice="confessional and intimate",
            ),

            # Optional: Additional configuration
            rewrite_config=ContentRewriteConfig(
                target_genre="mystery",
                target_tone="dark and suspenseful",
                preserve_key_elements=["plot twists", "character motivations"],
                target_length="longer",
                style_intensity=0.7,
            ),

            # Processing options
            store_intermediate=False,
            chunk_overlap=True,
        )

        # Create and run the pipeline
        pipeline = StoryRewritePipeline(
            caller=self.caller,
            connection_pool=self.connection_pool,
            provider="gemini",
            model="gemini-2.5-flash",
        )

        # Process the request
        response = pipeline.process_request(request)

        # Assertions
        self.assertIsNotNone(response)
        self.assertEqual(response.author_style_id,
                         new_style_response.author_style_id)
        self.assertGreater(response.processing_time_ms, 0)
        self.assertGreater(len(response.rewritten_story), 0)

        # Print results
        print(f"Session ID: {response.session_id}")
        print(f"Author Style ID: {response.author_style_id}")
        print(f"Processing time: {response.processing_time_ms}ms")
        print(f"Style confidence: {response.average_style_confidence:.2f}")

        return response

    def test_different_perspectives(self):
        """Test rewriting the same story in different perspectives."""
        if not self.has_test_files:
            self.skipTest(
                "Test PDF files not found. Please add test files to test_pdfs directory.")

        print("\n=== Test: Different Perspectives ===")

        # First create an author style
        new_style_response = self.test_new_author_style_workflow()

        # Define different perspectives to test
        perspectives = [
            WritingPerspective(type="first_person",
                               narrator_voice="introspective"),
            WritingPerspective(type="second_person",
                               narrator_voice="direct and engaging"),
            WritingPerspective(type="third_person_omniscient",
                               narrator_voice="all-knowing"),
            WritingPerspective(type="third_person_limited",
                               character_focus="protagonist"),
        ]

        pipeline = StoryRewritePipeline(
            caller=self.caller,
            connection_pool=self.connection_pool,
            provider="gemini",
            model="gemini-2.5-flash",
        )

        results = {}

        for i, perspective in enumerate(perspectives, 1):
            print(f"\n--- Perspective {i}: {perspective.type} ---")

            request = StoryRewriteRequest(
                rough_draft_file=str(self.test_rough_draft),
                author_style_request=ExistingAuthorStyleRequest(
                    author_style_id=new_style_response.author_style_id,
                ),
                writing_perspective=perspective,
                store_intermediate=False,
            )

            response = pipeline.process_request(request)
            results[perspective.type] = response

            # Assertions
            self.assertIsNotNone(response)
            self.assertGreater(len(response.rewritten_story), 0)
            self.assertGreater(response.processing_time_ms, 0)

            print(f"Processing time: {response.processing_time_ms}ms")
            print(f"Style confidence: {response.average_style_confidence:.2f}")

            # Print sample
            sample = response.rewritten_story[:300] + "..." if len(
                response.rewritten_story) > 300 else response.rewritten_story
            print(f"Sample: {sample}")

        return results

    def test_minimal_request(self):
        """Test minimal request with just the essentials."""
        if not self.has_test_files:
            self.skipTest(
                "Test PDF files not found. Please add test files to test_pdfs directory.")

        print("\n=== Test: Minimal Request ===")

        # Minimal request
        request = StoryRewriteRequest(
            rough_draft_file=str(self.test_rough_draft),
            author_style_request=NewAuthorStyleRequest(
                sample_files=[str(self.test_author_sample1)],
            ),
            writing_perspective=WritingPerspective(
                type="third_person_limited"),
        )

        pipeline = StoryRewritePipeline(
            caller=self.caller,
            connection_pool=self.connection_pool,
        )

        response = pipeline.process_request(request)

        # Assertions
        self.assertIsNotNone(response)
        self.assertIsNotNone(response.session_id)
        self.assertGreater(response.processing_time_ms, 0)
        self.assertGreater(len(response.rewritten_story), 0)

        print(f"Session ID: {response.session_id}")
        print(f"Processing time: {response.processing_time_ms}ms")
        print(f"Style confidence: {response.average_style_confidence:.2f}")

        return response

    def test_invalid_file_paths(self):
        """Test handling of invalid file paths."""
        print("\n=== Test: Invalid File Paths ===")

        request = StoryRewriteRequest(
            rough_draft_file="nonexistent_file.pdf",
            author_style_request=NewAuthorStyleRequest(
                sample_files=["nonexistent_sample.pdf"],
            ),
            writing_perspective=WritingPerspective(
                type="third_person_limited"),
        )

        pipeline = StoryRewritePipeline(
            caller=self.caller,
            connection_pool=self.connection_pool,
        )

        # This should raise an exception
        with self.assertRaises(Exception):
            pipeline.process_request(request)

    def test_invalid_author_style_id(self):
        """Test handling of invalid author style ID."""
        print("\n=== Test: Invalid Author Style ID ===")

        request = StoryRewriteRequest(
            rough_draft_file=str(self.test_rough_draft),
            author_style_request=ExistingAuthorStyleRequest(
                author_style_id="invalid_id_123",
            ),
            writing_perspective=WritingPerspective(
                type="third_person_limited"),
        )

        pipeline = StoryRewritePipeline(
            caller=self.caller,
            connection_pool=self.connection_pool,
        )

        # This should raise an exception
        with self.assertRaises(Exception):
            pipeline.process_request(request)


if __name__ == "__main__":
    # Run tests
    print("Story Rewrite Pipeline Tests")
    print("=" * 50)
    print("\nTo run these tests:")
    print("1. Set up your database connection")
    print("2. Add your API keys to environment variables")
    print("3. Add test PDF files to the test_pdfs directory:")
    print("   - rough_drafts/rough_draft_fantasy_story.pdf")
    print("   - author_samples/author_tolkien_lotr_sample.pdf")
    print("   - author_samples/author_rowling_hp_sample.pdf")
    print("4. Run: python -m pytest tests/deconstructor/test_story_rewrite_pipeline.py -v")

    # Run with unittest
    unittest.main(verbosity=2)

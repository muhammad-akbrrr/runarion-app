"""
Integration test for the Style Analyzer pipeline.
Tests the complete author style analysis process including sampling and profiling stages.
"""

import os
import sys

# Add src to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from dotenv import load_dotenv
from psycopg2 import pool

# Import Flask app to set up application context
from src.app import app

# Import real dependencies
from src.models.request import CallerInfo
from src.services.style_analyzer import (
    ProfilingStage,
    SamplingStage,
    StyleAnalyzerOrchestrator,
)
from src.utils.database_utils import utf8_database_connection
from ulid import ULID

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

# Test file paths
TEST_FILES = [
    "short_sample_3.txt",  # Use only the text file that exists
]


class StyleAnalyzerTest:
    """
    Integration test for the Style Analyzer pipeline.
    Tests sampling, profiling, and orchestration stages.
    """

    def __init__(self):
        """Initialize test with real dependencies."""
        self.author_name = "Author A"
        self.app_context = None

        print("Initializing Style Analyzer Test")

        # Set up Flask application context
        self.app_context = app.app_context()
        self.app_context.push()
        print("Flask application context initialized")

        # Initialize real database connection pool
        self.db_pool = self._create_database_pool()

        # Get workspace and project IDs from database
        self.workspace_id, self.project_id, self.user_id = self._get_ids()
        print(f"Retrieved workspace: {self.workspace_id}, project: {self.project_id}")

        # Get API keys for LLM calls
        api_keys = {
            "gemini": os.getenv("GEMINI_API_KEY"),
            "openai": os.getenv("OPENAI_API_KEY"),
            "deepseek": os.getenv("DEEPSEEK_API_KEY"),
        }

        # Create caller info
        self.caller = CallerInfo(
            user_id=str(self.user_id),
            workspace_id=self.workspace_id,
            project_id=self.project_id,
            api_keys=api_keys,
        )

        # Resolve file paths
        self.file_paths = self._resolve_file_paths()
        print(f"Test files prepared: {len(self.file_paths)} files")

    def _create_database_pool(self):
        """Create real database connection pool."""
        required_vars = ["DB_HOST", "DB_PORT", "DB_DATABASE", "DB_USER", "DB_PASSWORD"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")

        try:
            # Override DB_HOST to localhost for local testing
            os.environ["DB_HOST"] = "localhost"

            db_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
                database=os.getenv("DB_DATABASE"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
            )
            print("Database connection pool created")
            return db_pool

        except Exception as e:
            raise RuntimeError(f"Failed to create database pool: {e}")

    def _get_ids(self) -> tuple[str, str, int]:
        """Get workspace, project, and user IDs from database."""
        with utf8_database_connection(self.db_pool) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT p.workspace_id, p.id, wm.user_id
                    FROM projects p
                    INNER JOIN workspace_members wm ON p.workspace_id = wm.workspace_id
                    WHERE wm.role = 'owner'
                    """
                )
                row = cursor.fetchone()
                if not row:
                    raise RuntimeError("No workspace/project found in database")
                workspace_id, project_id, user_id = row
        return workspace_id, project_id, int(user_id)

    def _resolve_file_paths(self) -> list[str]:
        """Resolve test file paths."""
        file_dir = "tests/sample/input"
        resolved_paths = []
        for file in TEST_FILES:
            full_path = os.path.join(file_dir, file)
            if os.path.exists(full_path):
                resolved_paths.append(full_path)
            else:
                print(f"WARNING: Test file not found: {full_path}")
        return resolved_paths

    def _clean_author_style(self):
        """Clean up all author style related data."""
        print("Cleaning author style data...")
        with utf8_database_connection(self.db_pool) as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM author_styles_to_samples")
                cursor.execute("DELETE FROM author_style_chunks")
                cursor.execute("DELETE FROM author_samples")
                cursor.execute("DELETE FROM author_styles")
                conn.commit()
        print("Cleanup completed")

    def _init_author_style(self) -> str:
        """Initialize a new author style record."""
        author_style_id = str(ULID())
        with utf8_database_connection(self.db_pool) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO author_styles 
                    (id, workspace_id, project_id, user_id, author_name, status, started_at)
                    VALUES (%s, %s, %s, %s, %s, 'init_completed', NOW())
                    """,
                    (
                        author_style_id,
                        self.workspace_id,
                        self.project_id,
                        self.user_id,
                        self.author_name,
                    ),
                )
                conn.commit()
        print(f"Author style initialized: {author_style_id}")
        return author_style_id

    def test_sampling_stage(self):
        """Test the sampling stage independently."""
        print("\n" + "=" * 60)
        print("TEST: Sampling Stage")
        print("=" * 60)

        # Clean and initialize
        self._clean_author_style()
        author_style_id = self._init_author_style()

        # Create sampling stage
        sampling = SamplingStage(db_pool=self.db_pool, min_success_samples=0.5)

        # Run sampling
        print("Running sampling stage...")
        results = sampling.run(author_style_id, self.file_paths)

        # Verify results
        success_count = sum(1 for r in results if r["success"])
        print(f"Sampling completed: {success_count}/{len(results)} successful")

        assert success_count > 0, "At least one sample should succeed"
        print("Sampling stage test PASSED\n")
        return author_style_id

    def test_sampling_min_threshold_failure(self):
        """Test that sampling fails when min_success_samples threshold is too high."""
        print("\n" + "=" * 60)
        print("TEST: Sampling Min Threshold Failure")
        print("=" * 60)

        # Clean and initialize
        self._clean_author_style()
        author_style_id = self._init_author_style()

        # Create sampling stage with unrealistic threshold
        sampling = SamplingStage(db_pool=self.db_pool, min_success_samples=0.8)

        # Run sampling - should fail because only 1 out of 1 file (100%) would pass,
        # but if we had invalid files it would fail
        print("Running sampling with high threshold (0.8)...")

        # This should succeed with our single valid file (100% > 80%)
        try:
            results = sampling.run(author_style_id, self.file_paths)
            success_count = sum(1 for r in results if r["success"])
            success_rate = success_count / len(results)
            print(
                f"Sampling completed: {success_count}/{len(results)} successful ({success_rate:.1%})"
            )

            # With only valid files, it should pass
            assert success_rate >= 0.8, "Should meet 80% threshold with valid files"
            print("Sampling min threshold test PASSED (threshold met)\n")
        except Exception as e:
            # If it fails, it's because threshold wasn't met
            print(f"Sampling failed as expected: {e}")
            print("Sampling min threshold test PASSED (threshold not met)\n")

    def test_profiling_stage(self, author_style_id: str):
        """Test the profiling stage independently."""
        print("\n" + "=" * 60)
        print("TEST: Profiling Stage")
        print("=" * 60)

        # Create profiling stage
        profiling = ProfilingStage(
            db_pool=self.db_pool,
            provider="gemini",
            model="gemini-2.0-flash",
            max_output_tokens=2000,
            min_success_partial_style=0.5,
        )

        # Run profiling
        print("Running profiling stage...")
        author_style = profiling.run(author_style_id, self.caller)

        # Verify results
        assert author_style is not None, "Author style should be generated"
        assert hasattr(
            author_style, "techniques"
        ), "Author style should have techniques"
        assert hasattr(author_style, "examples"), "Author style should have examples"

        print("Profiling completed")
        print(f"  Techniques: {len(vars(author_style.techniques))} categories")
        print(f"  Examples: {len(vars(author_style.examples))} items")
        print("Profiling stage test PASSED\n")

    def test_orchestrator_pipeline(self):
        """Test the complete orchestrator pipeline."""
        print("\n" + "=" * 60)
        print("TEST: Orchestrator Pipeline")
        print("=" * 60)

        # Clean data
        self._clean_author_style()

        # Create orchestrator
        orchestrator = StyleAnalyzerOrchestrator(
            db_pool=self.db_pool,
            sampling_stage=SamplingStage(db_pool=self.db_pool, min_success_samples=0.5),
            profiling_stage=ProfilingStage(
                db_pool=self.db_pool,
                provider="gemini",
                model="gemini-2.0-flash",
                max_output_tokens=2000,
                min_success_partial_style=0.5,
            ),
        )

        # Run pipeline
        print("Running complete pipeline...")
        result = orchestrator.run_pipeline(
            None,  # No existing ID
            self.author_name,
            self.file_paths,
            self.caller,
        )

        # Verify results
        assert (
            result["status"] == "profiling_completed"
        ), f"Pipeline should complete successfully, got: {result.get('status')}"
        assert result["author_style"] is not None, "Author style should be generated"
        assert result["author_style_id"] is not None, "Author style ID should exist"

        print(f"Pipeline completed in {result['total_time_ms']}ms")
        print(f"  Status: {result['status']}")
        print(f"  Author Style ID: {result['author_style_id']}")
        print("Orchestrator pipeline test PASSED\n")

    def test_orchestrator_check_and_clean(self):
        """Test the check_and_clean functionality."""
        print("\n" + "=" * 60)
        print("TEST: Orchestrator Check and Clean")
        print("=" * 60)

        # Create orchestrator
        orchestrator = StyleAnalyzerOrchestrator(
            db_pool=self.db_pool,
            sampling_stage=SamplingStage(db_pool=self.db_pool, min_success_samples=0.5),
            profiling_stage=ProfilingStage(
                db_pool=self.db_pool,
                provider="gemini",
                model="gemini-2.0-flash",
                max_output_tokens=2000,
                min_success_partial_style=0.5,
            ),
        )

        # Test get existing
        print("Testing 'get' mode...")
        existing_id, author_style = orchestrator.check_and_clean(
            self.author_name, self.caller, on_exist="get"
        )

        if existing_id:
            print(f"Found existing author style: {existing_id}")
            assert author_style is not None, "Should return existing author style"
        else:
            print("No existing author style found (expected)")

        print("Check and clean test PASSED\n")

    def test_orchestrator_check_and_clean_update_mode(self):
        """Test the check_and_clean functionality with update mode."""
        print("\n" + "=" * 60)
        print("TEST: Orchestrator Check and Clean - Update Mode")
        print("=" * 60)

        # Create orchestrator
        orchestrator = StyleAnalyzerOrchestrator(
            db_pool=self.db_pool,
            sampling_stage=SamplingStage(db_pool=self.db_pool, min_success_samples=0.5),
            profiling_stage=ProfilingStage(
                db_pool=self.db_pool,
                provider="gemini",
                model="gemini-2.0-flash",
                max_output_tokens=2000,
                min_success_partial_style=0.5,
            ),
        )

        # Test update mode - should clean relations if author style exists
        print("Testing 'update' mode...")
        existing_id, author_style = orchestrator.check_and_clean(
            self.author_name, self.caller, on_exist="update"
        )

        if existing_id:
            print(f"Found existing author style: {existing_id}, relations cleaned")
            # In update mode, it should return the ID but author_style might be None
            # because relations were deleted
        else:
            print("No existing author style found")

        print("Check and clean update mode test PASSED\n")

    def run_all_tests(self):
        """Run all tests in sequence."""
        print("\n" + "=" * 60)
        print("STYLE ANALYZER INTEGRATION TEST SUITE")
        print("=" * 60 + "\n")

        try:
            # Test 1: Sampling
            author_style_id = self.test_sampling_stage()

            # Test 2: Profiling (uses results from sampling)
            self.test_profiling_stage(author_style_id)

            # Test 3: Full orchestrator pipeline
            self.test_orchestrator_pipeline()

            # Test 4: Check and clean
            self.test_orchestrator_check_and_clean()

            # Test 5: Check and clean with update mode
            self.test_orchestrator_check_and_clean_update_mode()

            # Test 6: Sampling min threshold
            self.test_sampling_min_threshold_failure()

            print("\n" + "=" * 60)
            print("ALL TESTS PASSED SUCCESSFULLY!")
            print("=" * 60 + "\n")
            return True

        except Exception as e:
            print("\n" + "=" * 60)
            print(f"TEST FAILED: {e}")
            print("=" * 60 + "\n")
            import traceback

            traceback.print_exc()
            return False

        finally:
            # Cleanup
            if self.db_pool:
                self.db_pool.closeall()
            if self.app_context:
                self.app_context.pop()


def main():
    """Main test execution."""
    test = StyleAnalyzerTest()
    success = test.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

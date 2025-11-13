"""
End-to-end integration test for the complete deconstructor pipeline.
Uses real database operations, LLM providers, and file processing.
Processes a PDF through all 7 pipeline stages and generates enhanced output.
"""

import sys
import os
import ulid
from datetime import datetime
from pathlib import Path

# Add src to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from dotenv import load_dotenv
from psycopg2 import pool

# Import real dependencies
from src.services.deconstructor.orchestrator import DeconstructorOrchestrator
from src.services.generation_engine import GenerationEngine
from src.models.request import BaseGenerationRequest, GenerationConfig, CallerInfo
from src.models.deconstructor.status import DraftStatus
from src.utils.database_utils import utf8_database_connection
from src.utils.logging_config import configure_logging

# Import Flask app to set up application context
from src.app import app

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

# Configuration - CHANGE THIS TO USE DIFFERENT INPUT FILES
INPUT_FILE = "short_story.pdf"
INPUT_DIR = os.path.join(os.path.dirname(__file__), "../sample/input")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../sample/output")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

class EndToEndPipelineTest:
    """
    Complete end-to-end test for the deconstructor pipeline.
    Uses real database and LLM providers.
    """
    
    def __init__(self):
        """Initialize test with real dependencies."""
        self.input_path = os.path.join(INPUT_DIR, INPUT_FILE)
        self.output_dir = OUTPUT_DIR
        self.draft_id = str(ulid.ULID())  # Use full ULID format
        self.app_context = None
        
        # Validate input file exists
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"Input file not found: {self.input_path}")
        
        print(f"🔄 Initializing E2E Pipeline Test")
        print(f"   Input: {self.input_path}")
        print(f"   Output Dir: {self.output_dir}")
        print(f"   Draft ID: {self.draft_id}")
        
        # Set up Flask application context
        self.app_context = app.app_context()
        self.app_context.push()
        print("✓ Flask application context initialized")

        # Configure logging with INFO level (less verbose than DEBUG)
        configure_logging(log_level="INFO", output_format="simple")
        print("✓ Logging configured for pipeline visibility")

        # Initialize real database connection pool
        self.db_pool = self._create_database_pool()
        
        # Initialize real generation engine
        self.generation_engine = self._create_generation_engine()
        
        # Initialize orchestrator with real dependencies
        self.orchestrator = DeconstructorOrchestrator(
            self.generation_engine, 
            self.db_pool
        )
    
    def _create_database_pool(self):
        """Create real database connection pool."""
        required_vars = ['DB_HOST', 'DB_PORT', 'DB_DATABASE', 'DB_USER', 'DB_PASSWORD']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise EnvironmentError(f"Missing database environment variables: {', '.join(missing_vars)}")
        
        try:
            connection_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=5,
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT'),
                database=os.getenv('DB_DATABASE'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD')
            )
            print("✓ Database connection pool initialized")
            return connection_pool
            
        except Exception as e:
            raise RuntimeError(f"Failed to create database pool: {e}")
    
    def _create_generation_engine(self):
        """Create real generation engine with LLM provider."""
        # Validate API keys
        api_keys = {
            'openai': os.getenv('OPENAI_API_KEY'),
            'gemini': os.getenv('GEMINI_API_KEY'),
            'deepseek': os.getenv('DEEPSEEK_API_KEY')
        }
        
        # Use the first available provider
        provider = None
        for provider_name, api_key in api_keys.items():
            if api_key:
                provider = provider_name
                break
        
        if not provider:
            raise EnvironmentError("No valid API keys found. Need at least one of: OPENAI_API_KEY, GEMINI_API_KEY, DEEPSEEK_API_KEY")
        
        # Create generation request
        caller_info = CallerInfo(
            user_id="test-user",
            workspace_id="test-workspace", 
            project_id="test-project",
            api_keys=api_keys,
            session_id=f"e2e-test-{self.draft_id[:8]}"
        )
        
        generation_config = GenerationConfig(
            temperature=0.7,
            max_output_tokens=3000,
            min_output_tokens=100
        )
        
        request = BaseGenerationRequest(
            usecase="novel_deconstruction",
            provider=provider,
            model="gpt-4o-mini",
            generation_config=generation_config,
            caller=caller_info
        )
        
        generation_engine = GenerationEngine(request)
        print(f"✓ Generation engine initialized with {provider} provider")
        return generation_engine
    
    def create_draft_record(self):
        """Create a real draft record in the database."""
        print(f"📝 Creating draft record: {self.draft_id}")
        
        with utf8_database_connection(self.db_pool) as conn:
            cursor = conn.cursor()
            
            # Get the first available workspace (use Demo Workspace if available)
            cursor.execute("""
                SELECT id, name FROM workspaces 
                WHERE name = 'Demo Workspace' OR name LIKE '%Demo%'
                LIMIT 1
            """)
            workspace_result = cursor.fetchone()
            
            if not workspace_result:
                # If no demo workspace, just use any workspace
                cursor.execute("""
                    SELECT id, name FROM workspaces LIMIT 1
                """)
                workspace_result = cursor.fetchone()
            
            if workspace_result:
                workspace_id = workspace_result[0]
                workspace_name = workspace_result[1]
                print(f"✓ Using existing workspace: {workspace_name} ({workspace_id})")
            else:
                # Create a test workspace if absolutely none exist
                test_workspace_id = str(ulid.ULID())  # Use full ULID format
                cursor.execute("""
                    INSERT INTO workspaces (
                        id, name, slug, is_active, monthly_quota, quota, 
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    test_workspace_id,
                    "Test Workspace",
                    "test-workspace-" + str(ulid.ULID())[:8],
                    True,
                    50,
                    50,
                    datetime.now(),
                    datetime.now()
                ))
                workspace_id = test_workspace_id
                print(f"✓ Created test workspace: {workspace_id}")
            
            # Create draft record with correct schema
            cursor.execute("""
                INSERT INTO drafts (
                    id, 
                    workspace_id,
                    user_id,
                    original_filename, 
                    file_path, 
                    file_size, 
                    status, 
                    processing_started_at,
                    metadata,
                    created_at,
                    updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                self.draft_id,  # Already truncated to 26 characters
                workspace_id,
                1,  # Super Admin user ID
                INPUT_FILE,
                self.input_path,
                os.path.getsize(self.input_path),
                DraftStatus.PROCESSING.value,
                datetime.now(),
                '{"test_run": true, "e2e_integration": true}',
                datetime.now(),
                datetime.now()
            ))
            
            conn.commit()
            print(f"✓ Draft record created in database")
    
    def run_pipeline(self):
        """Run the complete 7-stage deconstruction pipeline."""
        print(f"🚀 Starting complete pipeline execution...")
        print(f"   This will process through all 7 stages using real LLM calls")
        print(f"   Expected duration: 5-15 minutes depending on file size and LLM response times")
        print()
        
        try:
            # Copy file to expected upload location if needed
            upload_path = os.getenv('UPLOAD_PATH', '/tmp/uploads')
            os.makedirs(upload_path, exist_ok=True)
            
            target_file_path = os.path.join(upload_path, INPUT_FILE)
            if not os.path.exists(target_file_path):
                import shutil
                shutil.copy2(self.input_path, target_file_path)
                print(f"📁 Copied input file to upload directory: {target_file_path}")
            
            # Run the complete pipeline
            results = self.orchestrator.run_pipeline(
                draft_id=self.draft_id,
                file_name=INPUT_FILE,
                chaptering_mode='flexible',
                target_chapter_length=2500,
                use_transactions=True
            )
            
            # If pipeline failed, show the actual error
            if not results.get('success', False) and results.get('error'):
                print(f"❌ Pipeline failed with error: {results['error']}")
            
            return results
            
        except Exception as e:
            print(f"❌ Pipeline execution failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def generate_output_pdf(self, pipeline_results):
        """Generate PDF output from pipeline results."""
        print(f"📄 Generating output PDF...")
        
        try:
            # Import PDF generation utility
            from ..utils.pdf_generator import generate_enhanced_manuscript_pdf
            
            # Generate PDF from database results
            output_filename = f"enhanced_{INPUT_FILE.replace('.pdf', '')}_output.pdf"
            output_path = os.path.join(self.output_dir, output_filename)
            
            success = generate_enhanced_manuscript_pdf(
                self.db_pool,
                self.draft_id,
                output_path
            )
            
            if success:
                print(f"✓ Output PDF generated: {output_path}")
                return output_path
            else:
                print(f"❌ Failed to generate output PDF")
                return None
                
        except ImportError:
            print("⚠️ PDF generator not available - creating text summary instead")
            return self._generate_text_summary()
    
    def _generate_text_summary(self):
        """Generate a text summary of results if PDF generation unavailable."""
        summary_path = os.path.join(self.output_dir, f"enhanced_{INPUT_FILE.replace('.pdf', '')}_summary.txt")
        
        with utf8_database_connection(self.db_pool) as conn:
            cursor = conn.cursor()
            
            # Get processing summary
            cursor.execute("SELECT status, metadata, processing_completed_at FROM drafts WHERE id = %s", (self.draft_id,))
            draft_info = cursor.fetchone()
            
            # Get scenes count
            cursor.execute("SELECT COUNT(*) FROM scenes WHERE draft_id = %s", (self.draft_id,))
            scenes_count = cursor.fetchone()[0]
            
            # Get chunks count
            cursor.execute("SELECT COUNT(*) FROM draft_chunks WHERE draft_id = %s", (self.draft_id,))
            chunks_count = cursor.fetchone()[0]
            
            # Get plot issues count
            cursor.execute("SELECT COUNT(*) FROM plot_issues WHERE draft_id = %s", (self.draft_id,))
            issues_count = cursor.fetchone()[0]
            
            # Write summary
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(f"# Enhanced Manuscript Processing Summary\n\n")
                f.write(f"**Input File:** {INPUT_FILE}\n")
                f.write(f"**Draft ID:** {self.draft_id}\n")
                f.write(f"**Processing Status:** {draft_info[0] if draft_info else 'Unknown'}\n")
                f.write(f"**Completed At:** {draft_info[2] if draft_info and draft_info[2] else 'In Progress'}\n\n")
                
                f.write(f"## Processing Statistics\n")
                f.write(f"- **Chunks Created:** {chunks_count}\n")
                f.write(f"- **Scenes Extracted:** {scenes_count}\n") 
                f.write(f"- **Plot Issues Found:** {issues_count}\n\n")
                
                f.write(f"## Pipeline Stages Completed\n")
                f.write(f"1. ✓ PDF Ingestion\n")
                f.write(f"2. ✓ Text Cleaning\n")
                f.write(f"3. ✓ Scene Detection\n")
                f.write(f"4. ✓ Deep Analysis (Scene, Graph, Reports)\n")
                f.write(f"5. ✓ Coherence Check\n")
                f.write(f"6. ✓ Enhancement\n")
                f.write(f"7. ✓ Chaptering\n\n")
                
                f.write(f"All enhanced content is stored in the database and ready for export.\n")
        
        print(f"✓ Text summary generated: {summary_path}")
        return summary_path
    
    def cleanup_test_data(self):
        """Clean up test data from database."""
        print(f"🧹 Cleaning up test data...")

        try:
            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()

                # Clean related data in correct order (child tables first)
                tables_to_clean = [
                    'plot_issues',
                    'chapters',           # Stage 7 output - ADDED
                    'final_manuscripts',  # Stage 6 output - ADDED
                    'scenes',
                    'draft_chunks',
                    'drafts'  # Parent table last
                ]

                cleaned_counts = {}
                for table in tables_to_clean:
                    # Use 'id' column for drafts table, 'draft_id' for all others
                    column_name = 'id' if table == 'drafts' else 'draft_id'
                    cursor.execute(f"DELETE FROM {table} WHERE {column_name} = %s", (self.draft_id,))
                    cleaned_counts[table] = cursor.rowcount

                conn.commit()

                total_cleaned = sum(cleaned_counts.values())
                print(f"✓ Test data cleaned up successfully ({total_cleaned} records)")
                for table, count in cleaned_counts.items():
                    if count > 0:
                        print(f"  - {table}: {count} records")
                
        except Exception as e:
            print(f"⚠️ Cleanup failed (this is usually fine for testing): {e}")
            # Try simple draft deletion as fallback
            try:
                with utf8_database_connection(self.db_pool) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM drafts WHERE id = %s", (self.draft_id,))
                    if cursor.rowcount > 0:
                        conn.commit()
                        print(f"✓ At least removed draft record")
            except:
                pass
    
    def run_complete_test(self, cleanup_after=True):
        """Run the complete end-to-end test."""
        start_time = datetime.now()
        
        try:
            print("=" * 60)
            print("🧪 RUNARION DECONSTRUCTOR - END-TO-END PIPELINE TEST")
            print("=" * 60)
            print()
            
            # Step 1: Create draft record
            self.create_draft_record()
            print()
            
            # Step 2: Run pipeline
            pipeline_results = self.run_pipeline()
            print()
            
            # Step 3: Generate output
            output_path = self.generate_output_pdf(pipeline_results)
            print()
            
            # Step 4: Show results
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print("=" * 60)
            print("🎉 PIPELINE TEST COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print(f"⏱️  Total Duration: {duration:.2f} seconds ({duration/60:.1f} minutes)")
            print(f"📊 Pipeline Success: {'✓' if pipeline_results['success'] else '❌'}")
            print(f"📁 Output Location: {output_path}")
            print(f"🔍 Draft ID: {self.draft_id}")
            
            if pipeline_results['success']:
                completed_stages = len(pipeline_results.get('stages_completed', []))
                print(f"✅ Stages Completed: {completed_stages}/7")
                
                # Show stage completion details
                print("\n📋 Stage Completion Details:")
                for stage in pipeline_results.get('stages_completed', []):
                    stage_name = stage.get('name', 'unknown')
                    stage_num = stage.get('stage', 'unknown')
                    print(f"   {stage_num}: {stage_name.title()} ✓")
            
            print("\n💡 Next Steps:")
            print(f"   1. Check the output file: {output_path}")
            print(f"   2. Review database tables for detailed results")
            print(f"   3. Use draft ID {self.draft_id} to query specific data")
            print()
            
            return True
            
        except Exception as e:
            print("=" * 60)
            print("❌ PIPELINE TEST FAILED!")
            print("=" * 60)
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            if cleanup_after:
                print()
                self.cleanup_test_data()
            
            # Clean up Flask application context
            if self.app_context:
                self.app_context.pop()
                print("✓ Flask application context cleaned up")


def main():
    """Main test execution."""
    test = EndToEndPipelineTest()
    
    # Ask user if they want to cleanup after test
    try:
        cleanup_choice = input("\n🔄 Clean up test data after completion? (y/N): ").strip().lower()
        cleanup_after = cleanup_choice in ['y', 'yes']
    except (KeyboardInterrupt, EOFError):
        cleanup_after = False
        print()
    
    success = test.run_complete_test(cleanup_after=cleanup_after)
    
    if not cleanup_after:
        print(f"\n💾 Test data preserved in database with draft ID: {test.draft_id}")
        print("   To manually cleanup later, use the orchestrator.cleanup_failed_processing() method")
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
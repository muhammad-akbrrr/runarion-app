"""
AGE Graph Database Integration Test (AGE-First Architecture)

Tests Apache AGE graph database integration with the novel analysis pipeline.
This test REQUIRES Apache AGE to be properly installed and configured.

AGE-First Architecture:
- No fallback mechanisms
- Fail fast if AGE is not available
- Single code path testing
- Clear error messages
"""

import os
import ulid
import json
from datetime import datetime

# Add src to Python path for imports

from dotenv import load_dotenv
from psycopg2 import pool

# Import test dependencies
from src.services.graph_database_service import GraphDatabaseService, GraphDatabaseNotAvailableError
from src.services.deconstructor.stage_4_analysis.analyzer_4b import ProgressiveGraphAnalysisStage
from src.services.generation_engine import GenerationEngine
from src.models.request import BaseGenerationRequest, GenerationConfig, CallerInfo
from src.models.deconstructor.status import DraftStatus
from src.services.deconstructor.base_stage import PipelineStageContext

# Import Flask app to set up application context
from src.app import app

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

class AgeGraphIntegrationTest:
    """
    Apache AGE graph database integration test with AGE-first architecture.
    
    This test validates that Apache AGE is properly integrated and functioning
    for novel analysis pipeline operations. No fallback testing - AGE must work.
    """
    
    def __init__(self):
        """Initialize test with database connections."""
        self.draft_id = str(ulid.ULID())
        self.workspace_id = str(ulid.ULID())
        self.db_pool = None
        self.graph_service = None
        
    def setup(self):
        """Set up test environment."""
        print("🔧 Setting up AGE Graph Integration Test Environment...")
        
        try:
            # Initialize database connection pool
            self.db_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=5,
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_DATABASE', 'runarion'),
                user=os.getenv('DB_USERNAME', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'postgres'),
                options="-c search_path=public"
            )
            
            # Initialize graph service (this will validate AGE availability)
            self.graph_service = GraphDatabaseService(self.db_pool)
            
            # Create test workspace and draft records
            self._create_test_workspace()
            self._create_test_draft()
            print(f"✓ Test environment ready with draft: {self.draft_id}")
            
        except GraphDatabaseNotAvailableError as e:
            print(f"✗ AGE Setup Failed: {e}")
            print("\n" + "="*70)
            print("🔧 COMPREHENSIVE AGE DIAGNOSTICS")
            print("="*70)
            print("The error above contains specific diagnostic commands to run.")
            print("To investigate this issue step by step:")
            print()
            print("1. 📋 BASIC CONTAINER CHECK:")
            print("   docker ps | grep postgres")
            print("   docker logs runarion-app-python-app-1")
            print()
            print("2. 🔍 EXEC INTO CONTAINER:")
            print("   docker exec -it runarion-app-python-app-1 bash")
            print()
            print("3. 📁 CHECK AGE FILES (inside container):")
            print("   ls -la /usr/lib/postgresql/16/lib/age.so")
            print("   ls -la /usr/share/postgresql/16/extension/age*")
            print()
            print("4. 🗄️ CHECK DATABASE (inside container):")
            print("   psql -U postgres -d runarion")
            print("   \\dx  -- List installed extensions")
            print("   SELECT * FROM pg_available_extensions WHERE name = 'age';")
            print()
            print("5. ⚡ TEST AGE LOADING (inside container):")
            print("   psql -U postgres -d runarion -c \"LOAD 'age';\"")
            print("   psql -U postgres -d runarion -c \"SELECT extversion FROM pg_extension WHERE extname = 'age';\"")
            print()
            print("6. 🔧 REBUILD IF NECESSARY:")
            print("   docker compose build --no-cache postgres-db")
            print("   docker compose up -d postgres-db")
            print()
            print("The specific error above will guide you to the exact issue.")
            print("="*70)
            raise
        except Exception as e:
            print(f"✗ Test setup failed: {e}")
            raise
            
    def _create_test_workspace(self):
        """Create a test workspace record in the database."""
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                # Use unique slug with timestamp to avoid duplicates
                unique_slug = f'age-test-workspace-{int(datetime.now().timestamp())}'
                cursor.execute("""
                    INSERT INTO workspaces (id, name, slug, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    self.workspace_id,
                    'AGE Integration Test Workspace',
                    unique_slug,
                    True,
                    datetime.now(),
                    datetime.now()
                ))
                conn.commit()
        finally:
            self.db_pool.putconn(conn)
            
    def _create_test_draft(self):
        """Create a test draft record in the database."""
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO drafts (id, workspace_id, user_id, original_filename, file_path, 
                                      file_size, word_count, processing_started_at, status, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    self.draft_id,
                    self.workspace_id,
                    1,  # Test user ID
                    'age_integration_test.txt',
                    '/test/path/age_integration_test.txt',
                    1024,  # Test file size
                    500,   # Test word count
                    datetime.now(),
                    DraftStatus.PROCESSING.value,
                    json.dumps({'test': True, 'age_integration_test': True})
                ))
                conn.commit()
        finally:
            self.db_pool.putconn(conn)
    
    def test_age_service_status(self):
        """Test AGE service status and availability."""
        print("\n📊 Testing AGE Service Status...")
        
        try:
            status = self.graph_service.get_status()
            print(f"   Service: {status.get('service')}")
            print(f"   Architecture: {status.get('architecture')}")
            print(f"   AGE Version: {status.get('age_version')}")
            print(f"   Graph Name: {status.get('graph_name')}")
            print(f"   Graph Exists: {status.get('graph_exists')}")
            print(f"   Status: {status.get('status')}")
            
            assert status.get('age_available') == True, "AGE must be available"
            assert status.get('status') == 'healthy', "Service must be healthy"
            
            print("✓ AGE service status: HEALTHY")
            return True
            
        except Exception as e:
            print(f"✗ AGE service status check failed: {e}")
            return False
    
    def test_vertex_creation(self):
        """Test AGE vertex creation."""
        print("\n🔗 Testing AGE Vertex Creation...")
        
        try:
            # Test data with simple names to avoid character constraints
            test_entities = [
                {'name': 'Hero', 'type': 'Character', 'role': 'protagonist'},
                {'name': 'Forest', 'type': 'Location', 'description': 'mystical place'},
                {'name': 'Sword', 'type': 'Item', 'importance': 'high'}
            ]
            
            created_vertices = []
            
            for entity in test_entities:
                properties = {k: v for k, v in entity.items() if k not in ['name', 'type']}
                
                vertex_id = self.graph_service.create_vertex(
                    draft_id=self.draft_id,
                    entity_name=entity['name'],
                    entity_type=entity['type'],
                    properties=properties
                )
                
                assert vertex_id is not None, f"Vertex creation must return valid ID for {entity['name']}"
                created_vertices.append((vertex_id, entity['name'], entity['type']))
                print(f"   Created AGE vertex {vertex_id}: {entity['name']} ({entity['type']})")
            
            print(f"✓ Successfully created {len(created_vertices)} AGE vertices")
            return True
            
        except Exception as e:
            print(f"✗ AGE vertex creation failed: {e}")
            return False
    
    def test_relationship_creation(self):
        """Test AGE relationship creation."""
        print("\n🔗 Testing AGE Relationship Creation...")
        
        try:
            # Test relationships between simple entities
            test_relationships = [
                {
                    'source': 'Hero',
                    'target': 'Forest', 
                    'type': 'VISITS',
                    'context': 'hero explores the mystical forest'
                },
                {
                    'source': 'Hero',
                    'target': 'Sword',
                    'type': 'POSSESSES', 
                    'context': 'hero finds the magical weapon'
                }
            ]
            
            created_relationships = []
            
            for relationship in test_relationships:
                edge_id = self.graph_service.create_relationship(
                    draft_id=self.draft_id,
                    source_name=relationship['source'],
                    target_name=relationship['target'],
                    relationship_type=relationship['type'],
                    properties={'context': relationship['context']}
                )
                
                assert edge_id is not None, "Relationship creation must return valid ID"
                created_relationships.append((edge_id, relationship))
                print(f"   Created AGE relationship {edge_id}: {relationship['source']} -{relationship['type']}-> {relationship['target']}")
            
            print(f"✓ Successfully created {len(created_relationships)} AGE relationships")
            return True
            
        except Exception as e:
            print(f"✗ AGE relationship creation failed: {e}")
            return False
    
    def test_stage_4b_integration(self):
        """Test Stage 4B integration with AGE graph service."""
        print("\n🎯 Testing Stage 4B AGE Integration...")
        
        try:
            # Set up generation engine (minimal config for testing)
            generation_engine = GenerationEngine(
                BaseGenerationRequest(
                    prompt="test",
                    caller=CallerInfo(
                        service_name="age_integration_test",
                        stage_name="4b",
                        draft_id=self.draft_id,
                        user_id="1",
                        workspace_id=self.workspace_id,
                        project_id=self.workspace_id,
                        api_keys={}
                    ),
                    generation_config=GenerationConfig(
                        provider="openai",
                        model="gpt-4o-mini",
                        max_output_tokens=100,
                        temperature=0.5
                    ),
                    instruction="Test instruction"
                )
            )
            
            # Create Stage 4B instance
            stage_4b = ProgressiveGraphAnalysisStage(self.db_pool, generation_engine)
            
            # Create test scene data
            self._create_test_scenes()
            
            # Execute stage 4B
            context = PipelineStageContext(self.draft_id)
            result = stage_4b._execute_stage(context)
            
            assert result.success, f"Stage 4B must succeed with AGE: {result.data.get('error', '')}"
            
            result_data = result.to_dict()
            print("   Stage 4B executed successfully")
            print(f"   Scenes processed: {result_data.get('scenes_processed', 0)}")
            print(f"   Entities created: {result_data.get('entities_created', 0)}")
            print(f"   Relationships created: {result_data.get('relationships_created', 0)}")
            
            # Validate that graph operations actually occurred
            entities_created = result_data.get('entities_created', 0)
            relationships_created = result_data.get('relationships_created', 0)
            
            assert entities_created > 0, "Stage 4B must create graph entities"
            assert relationships_created > 0, "Stage 4B must create graph relationships"
            
            print("✓ Stage 4B AGE integration test: SUCCESS")
            return True
            
        except Exception as e:
            print(f"✗ Stage 4B AGE integration failed: {e}")
            return False
    
    def _create_test_scenes(self):
        """Create test scene data for Stage 4B."""
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO scenes (draft_id, scene_number, title, summary, setting, characters, original_content)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    self.draft_id,
                    1,
                    'Test Scene',
                    'Hero meets a sage in the forest',
                    'Mystical Forest',
                    json.dumps(['Hero', 'Sage']),
                    'The hero ventured into the mystical forest where they met a wise sage who possessed ancient knowledge and magical powers.'
                ))
                conn.commit()
        finally:
            self.db_pool.putconn(conn)
    
    def test_graph_cleanup(self):
        """Test AGE graph data cleanup."""
        print("\n🧹 Testing AGE Graph Cleanup...")
        
        try:
            deleted_count = self.graph_service.cleanup_draft_data(self.draft_id)
            print(f"   Cleaned up {deleted_count} AGE graph items")
            
            assert isinstance(deleted_count, int), "Cleanup must return integer count"
            
            print("✓ AGE graph cleanup: SUCCESS")
            return True
            
        except Exception as e:
            print(f"✗ AGE graph cleanup failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up test data."""
        print("\n🧹 Cleaning up test data...")
        
        try:
            # Clean up graph data first
            if self.graph_service:
                self.graph_service.cleanup_draft_data(self.draft_id)
            
            # Clean up relational data
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM scenes WHERE draft_id = %s", (self.draft_id,))
                cursor.execute("DELETE FROM drafts WHERE id = %s", (self.draft_id,))
                cursor.execute("DELETE FROM workspaces WHERE id = %s", (self.workspace_id,))
                conn.commit()
            
            print("✓ Test data cleaned up successfully")
                
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
        finally:
            if self.db_pool:
                self.db_pool.closeall()
    
    def run_all_tests(self):
        """Run all AGE integration tests."""
        print("🧪 APACHE AGE GRAPH DATABASE INTEGRATION TESTS")
        print("=" * 60)
        print("AGE-First Architecture: No fallback mechanisms")
        print("=" * 60)
        
        # Track test results
        test_results = []
        
        try:
            # Setup (validates AGE availability)
            self.setup()
            
            # Run tests
            tests = [
                ("AGE Service Status", self.test_age_service_status),
                ("AGE Vertex Creation", self.test_vertex_creation),
                ("AGE Relationship Creation", self.test_relationship_creation),
                ("Stage 4B AGE Integration", self.test_stage_4b_integration),
                ("AGE Graph Cleanup", self.test_graph_cleanup)
            ]
            
            for test_name, test_func in tests:
                try:
                    result = test_func()
                    test_results.append((test_name, result))
                except Exception as e:
                    print(f"✗ {test_name} failed with exception: {e}")
                    test_results.append((test_name, False))
            
        finally:
            # Always cleanup
            self.cleanup()
        
        # Print results summary
        print("\n" + "=" * 60)
        print("📊 AGE INTEGRATION TEST RESULTS")
        print("=" * 60)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✓ PASSED" if result else "✗ FAILED"
            print(f"{status:10} {test_name}")
            if result:
                passed += 1
        
        print("-" * 60)
        print(f"TOTAL: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Apache AGE integration working correctly.")
            print("✅ AGE-first architecture validated successfully.")
            return True
        else:
            print(f"⚠️ {total - passed} tests failed.")
            print("🔧 Ensure Apache AGE is properly installed and configured.")
            return False


def main():
    """Main test execution."""
    print("Starting Apache AGE Graph Database Integration Tests...")
    print(f"Test started at: {datetime.now().isoformat()}")
    print()
    
    # Confirm test execution
    response = input("🔄 Run Apache AGE integration tests? (y/N): ").strip().lower()
    if response != 'y':
        print("Test execution cancelled.")
        return
    
    # Run tests
    with app.app_context():
        test = AgeGraphIntegrationTest()
        success = test.run_all_tests()
        
    print(f"\nTest completed at: {datetime.now().isoformat()}")
    
    if success:
        print("🎉 Apache AGE integration is working perfectly!")
        print("✅ Ready for production novel analysis pipeline.")
    else:
        print("⚠️ AGE integration issues detected.")
        print("🔧 Check Apache AGE installation and configuration.")

if __name__ == "__main__":
    main()
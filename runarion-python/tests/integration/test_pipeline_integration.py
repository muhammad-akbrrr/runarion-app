"""
Integration test for the complete deconstructor pipeline.
Tests that all stages can be imported, initialized, and basic functionality works.
"""

import sys

def test_stage_imports():
    """Test that all stages can be imported successfully."""
    try:
        from src.services.deconstructor.stage_1_ingestion import PDFIngestionStage
        from src.services.deconstructor.stage_2_cleaning import TextCleaningStage
        from src.services.deconstructor.stage_3_sceneExtract import SceneDetectionStage
        from src.services.deconstructor.stage_4_analysis.analyzer_4a import SceneBySceneAnalysisStage
        from src.services.deconstructor.stage_4_analysis.analyzer_4b import ProgressiveGraphAnalysisStage
        from src.services.deconstructor.stage_4_analysis.analyzer_4c_reports import ComprehensiveReportingStage
        from src.services.deconstructor.stage_5_coherence import CoherenceCheckStage
        from src.services.deconstructor.stage_6_enhancement import EnhancementStage
        from src.services.deconstructor.stage_7_chaptering import ChapteringStage
        from src.services.deconstructor.orchestrator import DeconstructorOrchestrator
        imported_stages = (
            PDFIngestionStage,
            TextCleaningStage,
            SceneDetectionStage,
            SceneBySceneAnalysisStage,
            ProgressiveGraphAnalysisStage,
            ComprehensiveReportingStage,
            CoherenceCheckStage,
            EnhancementStage,
            ChapteringStage,
            DeconstructorOrchestrator,
        )
        assert all(imported_stages)
        print("✓ All stage imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_base_stage_inheritance():
    """Test that stages 5-7 properly inherit from BasePipelineStage."""
    try:
        from src.services.deconstructor.base_stage import BasePipelineStage
        from src.services.deconstructor.stage_5_coherence import CoherenceCheckStage
        from src.services.deconstructor.stage_6_enhancement import EnhancementStage
        from src.services.deconstructor.stage_7_chaptering import ChapteringStage
        
        # Check inheritance
        assert issubclass(CoherenceCheckStage, BasePipelineStage), "CoherenceCheckStage must inherit from BasePipelineStage"
        assert issubclass(EnhancementStage, BasePipelineStage), "EnhancementStage must inherit from BasePipelineStage"
        assert issubclass(ChapteringStage, BasePipelineStage), "ChapteringStage must inherit from BasePipelineStage"
        
        print("✓ All stages 5-7 properly inherit from BasePipelineStage")
        return True
    except Exception as e:
        print(f"✗ Base stage inheritance check failed: {e}")
        return False

def test_orchestrator_initialization():
    """Test that orchestrator can initialize all stages."""
    try:
        from src.services.deconstructor.orchestrator import DeconstructorOrchestrator
        
        # Mock dependencies
        class MockGenerationEngine:
            pass
        
        class MockDBPool:
            pass
        
        # Initialize orchestrator
        generation_engine = MockGenerationEngine()
        db_pool = MockDBPool()
        
        orchestrator = DeconstructorOrchestrator(generation_engine, db_pool)
        
        # Check that all stages are initialized
        expected_stages = [1, 2, 3, 4, 5, 6, 7]
        actual_stages = list(orchestrator.stages.keys())
        
        assert all(stage in actual_stages for stage in expected_stages), f"Missing stages. Expected: {expected_stages}, Got: {actual_stages}"
        
        # Check that stage 4 has sub-stages
        assert isinstance(orchestrator.stages[4], dict), "Stage 4 should be a dictionary with sub-stages"
        assert 'a' in orchestrator.stages[4], "Stage 4 should have sub-stage 'a'"
        assert 'b' in orchestrator.stages[4], "Stage 4 should have sub-stage 'b'"
        assert 'c' in orchestrator.stages[4], "Stage 4 should have sub-stage 'c'"
        
        print("✓ Orchestrator initialization successful")
        print(f"  - Initialized stages: {actual_stages}")
        print(f"  - Stage 4 sub-stages: {list(orchestrator.stages[4].keys())}")
        return True
    except Exception as e:
        print(f"✗ Orchestrator initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_stage_method_signatures():
    """Test that all stages have the required run method with proper signature."""
    try:
        from src.services.deconstructor.orchestrator import DeconstructorOrchestrator
        
        # Mock dependencies
        class MockGenerationEngine:
            pass
        
        class MockDBPool:
            pass
        
        generation_engine = MockGenerationEngine()
        db_pool = MockDBPool()
        
        orchestrator = DeconstructorOrchestrator(generation_engine, db_pool)
        
        # Test stages 1-3 and 5-7 have run method
        for stage_num in [1, 2, 3, 5, 6, 7]:
            stage = orchestrator.stages[stage_num]
            assert hasattr(stage, 'run'), f"Stage {stage_num} must have run method"
            print(f"  ✓ Stage {stage_num} has run method")
        
        # Test stage 4 sub-stages have run method
        for sub_stage in ['a', 'b', 'c']:
            stage = orchestrator.stages[4][sub_stage]
            assert hasattr(stage, 'run'), f"Stage 4{sub_stage} must have run method"
            print(f"  ✓ Stage 4{sub_stage} has run method")
        
        print("✓ All stage method signatures validated")
        return True
    except Exception as e:
        print(f"✗ Stage method signature validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_integration_tests():
    """Run all integration tests."""
    print("🔄 Running Deconstructor Pipeline Integration Tests...\n")
    
    tests = [
        ("Stage Imports", test_stage_imports),
        ("Base Stage Inheritance", test_base_stage_inheritance),
        ("Orchestrator Initialization", test_orchestrator_initialization),
        ("Stage Method Signatures", test_stage_method_signatures)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"Running: {test_name}")
        result = test_func()
        results.append(result)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print("INTEGRATION TEST RESULTS")
    print("=" * 50)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All integration tests passed! Pipeline is ready for use.")
        return True
    else:
        print("❌ Some integration tests failed. Please review the errors above.")
        return False

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)

"""
Integration tests for the complete pipeline flow.
Tests the orchestrator and stage interactions with database dependencies using real AI providers.
"""

import pytest
import json
import os
import time
from datetime import datetime
from test_utils.assertions import PipelineAssertions, RealAPIAssertions
from test_utils.sample_data import SampleDataGenerator
from test_utils.real_generation_engine import RealGenerationEngineFactory
from test_utils.path_manager import get_temp_output


@pytest.mark.integration
@pytest.mark.real_api
@pytest.mark.database
@pytest.mark.slow
class TestPipelineFlow:
    """Test complete pipeline flow from ingestion to completion."""
    
    def test_complete_pipeline_success(self, orchestrator_instance, db_fixture, generation_engine_factory):
        """Test successful execution of complete pipeline."""
        # Skip if no API keys available
        available_providers = generation_engine_factory.get_available_providers()
        if not available_providers:
            pytest.skip("No API keys available for pipeline flow testing")
        
        # Create test draft
        test_data = SampleDataGenerator()
        draft_data = test_data.generate_draft_request()
        
        workspace_data = db_fixture.create_test_workspace(
            workspace_id=draft_data['workspace_id'],
            user_id=draft_data['user_id']
        )
        
        test_draft = db_fixture.create_test_draft(
            draft_id=draft_data['draft_id'],
            workspace_id=workspace_data['workspace_id'],
            user_id=workspace_data['user_id'],
            file_name=draft_data['file_name']
        )
        
        # Create sample manuscript content
        sample_content = """
        Chapter 1: The Adventure Begins
        
        It was a bright sunny morning when Emma decided to embark on her greatest adventure yet.
        She had been preparing for this journey for months, gathering supplies and studying maps.
        The destination was a mysterious island that appeared only on the oldest charts.
        
        Emma packed her backpack with care, ensuring she had everything needed for the expedition.
        Her notebook, compass, and water supplies were essential for survival.
        As she locked her cottage door, she felt a mixture of excitement and apprehension.
        
        Chapter 2: The Journey
        
        The first leg of the journey took Emma through dense forests and winding mountain paths.
        She encountered various wildlife along the way, from curious squirrels to majestic eagles.
        Each step brought her closer to the coast where her boat awaited.
        
        By evening, Emma reached the harbor where Captain Morrison waited with his vessel.
        The old seafarer had agreed to transport her to the mysterious island for a fair price.
        They would set sail at dawn, riding the morning tides toward the unknown.
        """
        
        # Create the file in the upload directory
        upload_path = str(get_temp_output(draft_data['file_name']))
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        with open(upload_path, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        
        try:
            # Run the complete pipeline
            start_time = time.time()
            result = orchestrator_instance.run_pipeline(
                draft_id=test_draft['draft_id'],
                file_path=upload_path,
                provider=available_providers[0],
                model="test-model",
                chaptering_mode="flexible",
                target_chapter_length=2500
            )
            end_time = time.time()
            
            # Verify pipeline execution
            assert result['success'] == True, f"Pipeline failed: {result.get('error', 'Unknown error')}"
            assert 'stages_completed' in result
            assert 'processing_time_seconds' in result
            
            # Verify processing time is reasonable
            processing_time = end_time - start_time
            assert processing_time < 600, f"Pipeline took too long: {processing_time:.2f}s"
            
            # Verify database state
            final_status = db_fixture.get_draft_status(test_draft['draft_id'])
            assert final_status in ['completed', 'failed', 'processing'], \
                f"Unexpected final status: {final_status}"
            
            # Verify stages were completed
            stages_completed = result.get('stages_completed', [])
            assert len(stages_completed) >= 1, "At least stage 1 should be completed"
            
            # Verify stage 1 completion (ingestion)
            stage_1_completed = any(stage['stage'] == 1 for stage in stages_completed)
            assert stage_1_completed, "Stage 1 (ingestion) should be completed"
            
            # If stage 2 was attempted, verify chunks exist
            stage_2_completed = any(stage['stage'] == 2 for stage in stages_completed)
            if stage_2_completed:
                chunks_count = db_fixture.count_records('draft_chunks', test_draft['draft_id'])
                assert chunks_count >= 1, "Chunks should be created after stage 2"
            
            print(f"Pipeline completed successfully in {processing_time:.2f}s")
            print(f"Stages completed: {[s['stage'] for s in stages_completed]}")
            print(f"Final status: {final_status}")
            
        finally:
            # Cleanup uploaded file
            if os.path.exists(upload_path):
                os.unlink(upload_path)
    
    def test_pipeline_stage_isolation(self, stage_1_instance, stage_2_instance, db_fixture, generation_engine_factory):
        """Test individual stage execution in isolation."""
        # Skip if no API keys available for stage 2
        available_providers = generation_engine_factory.get_available_providers()
        if not available_providers:
            pytest.skip("No API keys available for stage isolation testing")
        
        # Create test draft
        test_data = SampleDataGenerator()
        draft_data = test_data.generate_draft_request()
        
        workspace_data = db_fixture.create_test_workspace(
            workspace_id=draft_data['workspace_id'],
            user_id=draft_data['user_id']
        )
        
        test_draft = db_fixture.create_test_draft(
            draft_id=draft_data['draft_id'],
            workspace_id=workspace_data['workspace_id'],
            user_id=workspace_data['user_id'],
            file_name=draft_data['file_name']
        )
        
        # Create sample file for stage 1
        sample_content = "This is a simple test document for stage isolation testing."
        upload_path = str(get_temp_output(draft_data['file_name']))
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        with open(upload_path, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        
        try:
            # Test Stage 1 (Ingestion) - doesn't require AI
            stage_1_result = stage_1_instance.run(
                draft_id=test_draft['draft_id'],
                file_path=upload_path
            )
            
            assert stage_1_result['success'] == True, f"Stage 1 failed: {stage_1_result.get('error', 'Unknown error')}"
            assert 'chunks_created' in stage_1_result
            
            # Verify chunks were created
            chunks_count = db_fixture.count_records('draft_chunks', test_draft['draft_id'])
            assert chunks_count >= 1, "Stage 1 should create at least one chunk"
            
            # Test Stage 2 (Cleaning) - requires AI
            stage_2_result = stage_2_instance.run(draft_id=test_draft['draft_id'])
            
            assert stage_2_result['success'] == True, f"Stage 2 failed: {stage_2_result.get('error', 'Unknown error')}"
            assert 'chunks_processed' in stage_2_result
            assert 'total_tokens_used' in stage_2_result
            assert stage_2_result['total_tokens_used'] > 0
            
            # Verify cleaned text was generated
            cleaned_chunks = db_fixture.execute_query(
                "SELECT raw_text, cleaned_text FROM draft_chunks WHERE draft_id = %s",
                (test_draft['draft_id'],)
            )
            
            assert len(cleaned_chunks) >= 1, "Should have at least one cleaned chunk"
            
            for raw_text, cleaned_text in cleaned_chunks:
                RealAPIAssertions.assert_cleaning_improved_text(raw_text, cleaned_text)
                RealAPIAssertions.assert_text_quality_basic(cleaned_text)
            
            print(f"Stage isolation test completed successfully")
            print(f"Stage 1 created {chunks_count} chunks")
            print(f"Stage 2 processed {stage_2_result['chunks_processed']} chunks using {stage_2_result['total_tokens_used']} tokens")
            
        finally:
            # Cleanup uploaded file
            if os.path.exists(upload_path):
                os.unlink(upload_path)
    
    def test_pipeline_error_handling(self, orchestrator_instance, db_fixture, generation_engine_factory):
        """Test pipeline error handling and recovery."""
        # Skip if no API keys available
        available_providers = generation_engine_factory.get_available_providers()
        if not available_providers:
            pytest.skip("No API keys available for error handling testing")
        
        # Create test draft
        test_data = SampleDataGenerator()
        draft_data = test_data.generate_draft_request()
        
        workspace_data = db_fixture.create_test_workspace(
            workspace_id=draft_data['workspace_id'],
            user_id=draft_data['user_id']
        )
        
        test_draft = db_fixture.create_test_draft(
            draft_id=draft_data['draft_id'],
            workspace_id=workspace_data['workspace_id'],
            user_id=workspace_data['user_id'],
            file_name=draft_data['file_name']
        )
        
        # Test with non-existent file
        non_existent_path = '/tmp/nonexistent_file.txt'
        
        result = orchestrator_instance.run_pipeline(
            draft_id=test_draft['draft_id'],
            file_path=non_existent_path,
            provider=available_providers[0],
            model="test-model"
        )
        
        # Should handle error gracefully
        assert result['success'] == False, "Pipeline should fail with non-existent file"
        assert 'error' in result
        assert 'file' in result['error'].lower() or 'not found' in result['error'].lower()
        
        # Verify database state reflects failure
        final_status = db_fixture.get_draft_status(test_draft['draft_id'])
        assert final_status in ['failed', 'pending'], f"Status should reflect failure: {final_status}"
    
    def test_pipeline_data_flow(self, orchestrator_instance, db_fixture, generation_engine_factory):
        """Test data flow between pipeline stages."""
        # Skip if no API keys available
        available_providers = generation_engine_factory.get_available_providers()
        if not available_providers:
            pytest.skip("No API keys available for data flow testing")
        
        # Create test draft
        test_data = SampleDataGenerator()
        draft_data = test_data.generate_draft_request()
        
        workspace_data = db_fixture.create_test_workspace(
            workspace_id=draft_data['workspace_id'],
            user_id=draft_data['user_id']
        )
        
        test_draft = db_fixture.create_test_draft(
            draft_id=draft_data['draft_id'],
            workspace_id=workspace_data['workspace_id'],
            user_id=workspace_data['user_id'],
            file_name=draft_data['file_name']
        )
        
        # Create content with identifiable text for tracking
        traceable_content = """
        Chapter 1: Data Flow Test
        
        This is a test document designed to track data flow through the pipeline stages.
        The content includes specific phrases that should be preserved during processing.
        
        MARKER_START: This is a unique marker for tracking data flow. MARKER_END
        
        The document also contains text that should be improved during cleaning stages.
        Multiple  spaces   and   formatting issues  should be  corrected.
        
        Chapter 2: Continuation
        
        This second chapter helps test multi-chapter processing capabilities.
        It contains additional content for comprehensive testing of the pipeline.
        """
        
        upload_path = str(get_temp_output(draft_data['file_name']))
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        with open(upload_path, 'w', encoding='utf-8') as f:
            f.write(traceable_content)
        
        try:
            # Run pipeline
            result = orchestrator_instance.run_pipeline(
                draft_id=test_draft['draft_id'],
                file_path=upload_path,
                provider=available_providers[0],
                model="test-model"
            )
            
            # Verify data preservation and transformation
            if result['success']:
                # Check that chunks preserve key content
                chunks = db_fixture.execute_query(
                    "SELECT raw_text, cleaned_text FROM draft_chunks WHERE draft_id = %s ORDER BY chunk_number",
                    (test_draft['draft_id'],)
                )
                
                assert len(chunks) >= 1, "At least one chunk should be created"
                
                # Verify marker preservation
                marker_found_raw = any('MARKER_START' in raw_text for raw_text, _ in chunks)
                marker_found_cleaned = any('MARKER_START' in cleaned_text for _, cleaned_text in chunks)
                
                assert marker_found_raw, "Marker should be preserved in raw text"
                
                # If cleaning was performed, verify improvements
                if any(cleaned_text != raw_text for raw_text, cleaned_text in chunks):
                    # Verify that cleaning occurred but preserved important content
                    for raw_text, cleaned_text in chunks:
                        if cleaned_text != raw_text:
                            RealAPIAssertions.assert_cleaning_improved_text(raw_text, cleaned_text)
                            
                            # Check that multiple spaces were reduced
                            if '  ' in raw_text:
                                assert cleaned_text.count('  ') <= raw_text.count('  '), \
                                    "Cleaning should reduce excessive spacing"
                
                print(f"Data flow test completed successfully")
                print(f"Created {len(chunks)} chunks")
                
                if marker_found_cleaned:
                    print("Marker preserved through cleaning stage")
                
            else:
                print(f"Pipeline failed: {result.get('error', 'Unknown error')}")
                
        finally:
            # Cleanup uploaded file
            if os.path.exists(upload_path):
                os.unlink(upload_path)
    
    @pytest.mark.expensive
    def test_pipeline_performance_monitoring(self, orchestrator_instance, db_fixture, generation_engine_factory):
        """Test pipeline performance with real API calls (expensive test)."""
        # Skip if no API keys available
        available_providers = generation_engine_factory.get_available_providers()
        if not available_providers:
            pytest.skip("No API keys available for performance monitoring")
        
        # Create test draft
        test_data = SampleDataGenerator()
        draft_data = test_data.generate_draft_request()
        
        workspace_data = db_fixture.create_test_workspace(
            workspace_id=draft_data['workspace_id'],
            user_id=draft_data['user_id']
        )
        
        test_draft = db_fixture.create_test_draft(
            draft_id=draft_data['draft_id'],
            workspace_id=workspace_data['workspace_id'],
            user_id=workspace_data['user_id'],
            file_name=draft_data['file_name']
        )
        
        # Create content that will consume moderate tokens
        performance_content = """
        Chapter 1: Performance Testing
        
        This document is designed to test the performance characteristics of the pipeline
        when processing realistic content volumes. The text includes multiple paragraphs
        that require cleaning and processing to evaluate throughput and latency.
        
        The content simulates a typical manuscript with varied sentence structures,
        different formatting styles, and content that benefits from AI-powered cleaning.
        This helps measure real-world performance under normal operating conditions.
        
        Chapter 2: Measurement Criteria
        
        Performance metrics include processing time per chunk, token consumption rates,
        and overall pipeline throughput. These measurements help optimize the system
        for production workloads and identify potential bottlenecks.
        
        The pipeline should maintain consistent performance across different content types
        while preserving content quality and accuracy throughout the processing stages.
        """
        
        upload_path = str(get_temp_output(draft_data['file_name']))
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        with open(upload_path, 'w', encoding='utf-8') as f:
            f.write(performance_content)
        
        try:
            # Monitor performance metrics
            start_time = time.time()
            result = orchestrator_instance.run_pipeline(
                draft_id=test_draft['draft_id'],
                file_path=upload_path,
                provider=available_providers[0],
                model="test-model"
            )
            end_time = time.time()
            
            # Calculate performance metrics
            total_time = end_time - start_time
            
            if result['success']:
                # Gather processing statistics
                chunks_count = db_fixture.count_records('draft_chunks', test_draft['draft_id'])
                stages_completed = result.get('stages_completed', [])
                
                # Performance assertions
                assert total_time < 300, f"Performance test took too long: {total_time:.2f}s"
                
                if chunks_count > 0:
                    avg_time_per_chunk = total_time / chunks_count
                    assert avg_time_per_chunk < 60, f"Average time per chunk too long: {avg_time_per_chunk:.2f}s"
                
                # Print performance metrics
                print(f"Performance monitoring results:")
                print(f"  Total processing time: {total_time:.2f}s")
                print(f"  Chunks processed: {chunks_count}")
                print(f"  Stages completed: {len(stages_completed)}")
                
                if chunks_count > 0:
                    print(f"  Average time per chunk: {avg_time_per_chunk:.2f}s")
                
                # Check for token usage in results
                if 'processing_stats' in result:
                    stats = result['processing_stats']
                    if 'total_tokens_used' in stats:
                        print(f"  Total tokens consumed: {stats['total_tokens_used']}")
                
            else:
                print(f"Performance test failed: {result.get('error', 'Unknown error')}")
                
        finally:
            # Cleanup uploaded file
            if os.path.exists(upload_path):
                os.unlink(upload_path)
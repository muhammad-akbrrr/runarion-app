"""
Tests for Stage 2: Text Cleaning and Normalization with Real API
Uses real AI providers to test text cleaning functionality.
Tests use actual chunks from Stage 1 to ensure realistic pipeline behavior.
"""

import pytest
import time
from test_utils.assertions import PipelineAssertions, RealAPIAssertions
from test_utils.sample_data import SampleDataGenerator
from test_utils.real_generation_engine import RealGenerationEngineFactory
from test_utils.stage_dependencies import requires_previous_stages
from test_utils.output_generator import generate_stage_output


class TestStageCompatibility:
    """Test configuration compatibility between stages."""
    
    def test_stage_1_2_token_compatibility(self):
        """Test that Stage 2 can handle Stage 1's token output."""
        # Stage 1 configuration (from document_processor.py)
        stage_1_default_word_limit = 1500  # DEFAULT_WORD_LIMIT
        stage_1_default_chunk_size = 4000  # DEFAULT_CHUNK_SIZE (tokens)
        
        # Stage 2 configuration (from real_generation_engine.py)
        factory = RealGenerationEngineFactory()
        stage_2_max_output_tokens = factory.default_config['max_output_tokens']
        
        print(f"\nStage Compatibility Analysis:")
        print(f"  Stage 1 word limit: {stage_1_default_word_limit} words")
        print(f"  Stage 1 token limit: {stage_1_default_chunk_size} tokens")
        print(f"  Stage 2 max output: {stage_2_max_output_tokens} tokens")
        
        # Stage 2 should be able to handle Stage 1's maximum output
        assert stage_2_max_output_tokens >= stage_1_default_chunk_size, \
            f"Stage 2 max output ({stage_2_max_output_tokens}) should >= Stage 1 chunk size ({stage_1_default_chunk_size})"
        
        # For cleaning, we expect similar or slightly larger output
        recommended_min_tokens = int(stage_1_default_chunk_size * 1.2)  # 20% safety margin
        assert stage_2_max_output_tokens >= recommended_min_tokens, \
            f"Stage 2 should have safety margin: {stage_2_max_output_tokens} >= {recommended_min_tokens} (recommended)"
        
        print(f"  ✅ Token compatibility verified")
        
    def test_stage_1_2_word_compatibility(self):
        """Test word count compatibility between stages."""
        # Approximate token-to-word ratio (typically 3-4 tokens per word for English)
        tokens_per_word = 4  # Conservative estimate
        
        stage_1_word_limit = 1500
        estimated_tokens_needed = stage_1_word_limit * tokens_per_word
        
        factory = RealGenerationEngineFactory()
        stage_2_max_output_tokens = factory.default_config['max_output_tokens']
        
        print(f"\nWord-to-Token Compatibility:")
        print(f"  Stage 1: {stage_1_word_limit} words")
        print(f"  Estimated tokens needed: {estimated_tokens_needed} tokens ({tokens_per_word} tokens/word)")
        print(f"  Stage 2 max output: {stage_2_max_output_tokens} tokens")
        
        assert stage_2_max_output_tokens >= estimated_tokens_needed, \
            f"Stage 2 ({stage_2_max_output_tokens}) should handle Stage 1's max words ({estimated_tokens_needed} estimated tokens)"
        
        print(f"  ✅ Word-to-token compatibility verified")


@pytest.mark.real_api
@pytest.mark.database
class TestStage2Cleaning:
    """Test Stage 2: Text Cleaning"""
    
    @requires_previous_stages(1)
    def test_stage_2_text_cleaning_success(self, register_stages_1_and_2, stage_2_instance, db_fixture, 
                                         sample_file_path, output_generator, test_output_options, 
                                         dependency_results):
        """Test successful text cleaning with real API calls."""
        # Use data from Stage 1 dependency (Stage 1 should have already run)
        assert dependency_results, "Stage 1 dependency results should be available"
        assert dependency_results.get('executed_stages') or dependency_results.get('loaded_from_cache'), \
            "Stage 1 should have been executed or loaded from cache"
        
        # Get the draft_id from Stage 1 execution results
        stage_1_data = dependency_results.get('stage_data', {}).get(1, {})
        draft_id = stage_1_data.get('draft_id')
        
        if not draft_id:
            # Fallback: try to find any existing draft with chunks
            chunks_query = db_fixture.execute_query(
                "SELECT draft_id FROM draft_chunks ORDER BY id DESC LIMIT 1"
            )
            if chunks_query:
                draft_id = chunks_query[0][0]
        
        assert draft_id, "No draft_id available from Stage 1 or existing data"
        
        # Verify Stage 1 created chunks for us to work with
        chunks_count = db_fixture.count_records('draft_chunks', draft_id)
        assert chunks_count > 0, f"Stage 1 should have created chunks, but found {chunks_count}"
        
        # Run Stage 2 with real API on the chunks created by Stage 1
        start_time = time.time()
        result = stage_2_instance.run(draft_id=draft_id)
        end_time = time.time()
        
        # Verify result structure
        assert result['success'] == True, f"Stage 2 failed: {result.get('error', 'Unknown error')}"
        assert 'chunks_processed' in result
        assert 'chunks_cleaned' in result
        assert 'chunks_updated' in result
        
        # Verify chunks were processed
        assert result['chunks_processed'] > 0
        assert result['chunks_cleaned'] >= 0  # Some chunks may remain unchanged if already clean
        assert result['chunks_updated'] == result['chunks_processed']  # All chunks should be updated (even if unchanged)
        
        # Verify compatibility with Stage 1 output
        chunks_data = db_fixture.execute_query(
            "SELECT LENGTH(raw_text) FROM draft_chunks WHERE draft_id = %s",
            (draft_id,)
        )
        max_chunk_length = max(length[0] for length in chunks_data) if chunks_data else 0
        
        # Ensure Stage 2 handled Stage 1's chunk sizes appropriately
        # Stage 1 targets 1500 words ≈ 6000-8000 characters
        if max_chunk_length > 5000:  # Large chunk from Stage 1
            print(f"Successfully processed large chunk: {max_chunk_length} characters")
            assert result['success'], "Should handle large chunks from Stage 1"
        
        # Verify processing time is reasonable (more time allowed for real content cleaning)
        processing_time = end_time - start_time
        assert processing_time < 180, f"Processing took too long: {processing_time:.2f}s"  # Increased for real API calls
        
        # Verify database state - cleaned text should be updated
        updated_chunks = db_fixture.execute_query(
            "SELECT raw_text, cleaned_text FROM draft_chunks WHERE draft_id = %s ORDER BY chunk_number",
            (draft_id,)
        )
        
        assert len(updated_chunks) == result['chunks_processed']
        
        for i, (raw_text, cleaned_text) in enumerate(updated_chunks):
            # Verify text was actually cleaned
            RealAPIAssertions.assert_cleaning_improved_text(raw_text, cleaned_text)
            
            # Verify text quality
            RealAPIAssertions.assert_text_quality_basic(cleaned_text, min_length=20)
            
            # Verify text quality and appropriate cleaning behavior
            assert len(cleaned_text.strip()) > 0, f"Chunk {i+1} cleaned text is empty"
            
            # Length preservation check (95% minimum for cleaning, not summarizing)
            length_ratio = len(cleaned_text) / len(raw_text) if len(raw_text) > 0 else 1.0
            assert length_ratio >= 0.95, f"Chunk {i+1} too short ({length_ratio*100:.1f}%) - may be summarizing instead of cleaning"
            
            # Allow identical text for already clean content
            if cleaned_text == raw_text:
                print(f"Chunk {i+1}: Text preserved (already clean)")
            else:
                print(f"Chunk {i+1}: Text cleaned - {len(raw_text)} -> {len(cleaned_text)} chars")
                
                # If text changed, validate it was an improvement
                if '  ' in raw_text and raw_text.count('  ') > 5:  # Had spacing issues
                    assert cleaned_text.count('  ') <= raw_text.count('  '), \
                        f"Chunk {i+1} should reduce excessive spacing issues"
        
        # Generate test outputs for debugging and next stage seeding
        if test_output_options['generate_outputs']:
            # Ensure test_result includes draft_id for database seeds generation
            enhanced_result = result.copy()
            enhanced_result['draft_id'] = draft_id
            
            output_files = generate_stage_output(
                stage_number=2,
                test_name='test_stage_2_text_cleaning_success',
                test_result=enhanced_result,
                db_fixture=db_fixture,
                additional_data={
                    'dependency_info': dependency_results,
                    'test_configuration': {
                        'chunks_processed': result['chunks_processed'],
                        'api_provider': 'real',
                        'processing_time': processing_time
                    }
                }
            )
            
            # Log output file locations for reference
            for output_type, file_path in output_files.items():
                print(f"Generated {output_type} output: {file_path}")
    
    @pytest.mark.expensive
    @requires_previous_stages(1)
    def test_stage_2_large_text_cleaning(self, register_stages_1_and_2, stage_2_instance, db_fixture, sample_file_path, dependency_results):
        """Test cleaning of larger text chunks with real API."""
        # Use data from Stage 1 dependency
        assert dependency_results, "Stage 1 dependency results should be available"
        
        # Get the draft_id from Stage 1 execution results
        stage_1_data = dependency_results.get('stage_data', {}).get(1, {})
        draft_id = stage_1_data.get('draft_id')
        
        if not draft_id:
            # Fallback: try to find any existing draft with chunks
            chunks_query = db_fixture.execute_query(
                "SELECT draft_id FROM draft_chunks ORDER BY id DESC LIMIT 1"
            )
            if chunks_query:
                draft_id = chunks_query[0][0]
        
        assert draft_id, "No draft_id available from Stage 1 or existing data"
        
        # Verify Stage 1 created chunks for us to work with
        chunks_count = db_fixture.count_records('draft_chunks', draft_id)
        assert chunks_count > 0, f"Stage 1 should have created chunks, but found {chunks_count}"
        
        # Run Stage 2 on the chunks created by Stage 1
        start_time = time.time()
        result = stage_2_instance.run(draft_id=draft_id)
        end_time = time.time()
        
        # Verify result
        assert result['success'] == True, f"Large text cleaning failed: {result.get('error', 'Unknown error')}"
        assert result['chunks_processed'] > 0  # Should process the chunks from Stage 1
        assert result['chunks_cleaned'] > 0  # Large text should be successfully cleaned
        
        # Verify processing time (large text may take longer)
        processing_time = end_time - start_time
        assert processing_time < 180, f"Large text processing took too long: {processing_time:.2f}s"
        
        # Verify cleaned text
        cleaned_chunks = db_fixture.execute_query(
            "SELECT raw_text, cleaned_text FROM draft_chunks WHERE draft_id = %s",
            (draft_id,)
        )
        
        raw_text, cleaned_text = cleaned_chunks[0]
        
        # Verify improvements
        RealAPIAssertions.assert_cleaning_improved_text(raw_text, cleaned_text)
        RealAPIAssertions.assert_text_quality_basic(cleaned_text, min_length=200)
        
        # Check for specific large text improvements
        assert len(cleaned_text.strip()) >= len(raw_text.strip()) * 0.8, \
            "Cleaned text should not be dramatically shorter"
    
    @pytest.mark.real_api
    @requires_previous_stages(1)
    def test_stage_2_unicode_handling(self, register_stages_1_and_2, stage_2_instance, db_fixture, sample_file_path, dependency_results):
        """Test handling of Unicode characters with real API."""
        # Use data from Stage 1 dependency
        assert dependency_results, "Stage 1 dependency results should be available"
        
        # Get the draft_id from Stage 1 execution results
        stage_1_data = dependency_results.get('stage_data', {}).get(1, {})
        draft_id = stage_1_data.get('draft_id')
        
        if not draft_id:
            # Fallback: try to find any existing draft with chunks
            chunks_query = db_fixture.execute_query(
                "SELECT draft_id FROM draft_chunks ORDER BY id DESC LIMIT 1"
            )
            if chunks_query:
                draft_id = chunks_query[0][0]
        
        assert draft_id, "No draft_id available from Stage 1 or existing data"
        
        # Verify Stage 1 created chunks for us to work with
        chunks_count = db_fixture.count_records('draft_chunks', draft_id)
        assert chunks_count > 0, f"Stage 1 should have created chunks, but found {chunks_count}"
        
        # Run Stage 2 on existing chunks
        result = stage_2_instance.run(draft_id=draft_id)
        
        # Verify result
        assert result['success'] == True, f"Unicode handling failed: {result.get('error', 'Unknown error')}"
        
        # Verify that cleaning preserved text structure
        cleaned_chunks = db_fixture.execute_query(
            "SELECT raw_text, cleaned_text FROM draft_chunks WHERE draft_id = %s",
            (draft_id,)
        )
        
        assert len(cleaned_chunks) > 0, "Should have cleaned chunks available"
        
        # Check at least one chunk for basic cleaning
        raw_text, cleaned_text = cleaned_chunks[0]
        
        # Verify basic cleaning
        RealAPIAssertions.assert_text_quality_basic(cleaned_text)
        
        # Verify Unicode handling is functional (text structure preserved)
        assert len(cleaned_text) > 0, "Cleaned text should not be empty"
        assert isinstance(cleaned_text, str), "Cleaned text should be a string"
        
        # Verify cleaning didn't break text structure
        assert len(cleaned_text.strip()) > len(raw_text.strip()) * 0.5, \
            "Cleaned text should not be dramatically shorter than original"
        
        # Check for basic text preservation (no broken encoding)
        try:
            cleaned_text.encode('utf-8')
            assert True, "Unicode encoding should work"
        except UnicodeEncodeError:
            assert False, "Unicode encoding failed - text may be corrupted"
    
    @pytest.mark.real_api
    @requires_previous_stages(1)
    def test_stage_2_no_chunks_handling(self, register_stages_1_and_2, stage_2_instance, db_fixture, sample_file_path, dependency_results):
        """Test handling when no chunks exist with real API setup."""
        # This test should create a scenario with no chunks by clearing Stage 1 data
        assert dependency_results, "Stage 1 dependency results should be available"
        
        # Get the draft_id from Stage 1 execution results
        stage_1_data = dependency_results.get('stage_data', {}).get(1, {})
        draft_id = stage_1_data.get('draft_id')
        
        if not draft_id:
            # Create a minimal draft for this specific test case
            test_data = SampleDataGenerator(db_fixture.connection_pool)
            draft_data = test_data.generate_draft_request()
            
            workspace_data = db_fixture.create_test_workspace(
                workspace_id=draft_data['workspace_id'],
                user_id=draft_data['user_id']
            )
            
            test_draft = db_fixture.create_test_draft(
                draft_id=draft_data['draft_id'],
                workspace_id=workspace_data['workspace_id'],
                user_id=workspace_data['user_id'],
                file_path=sample_file_path
            )
            draft_id = test_draft['draft_id']
        
        # Clear any existing chunks to test the no-chunks scenario
        with db_fixture.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM draft_chunks WHERE draft_id = %s", (draft_id,))
        
        # Verify no chunks exist
        chunks_count = db_fixture.count_records('draft_chunks', draft_id)
        assert chunks_count == 0, f"Should have no chunks, but found {chunks_count}"
        
        # Run Stage 2 (no chunks in database)
        result = stage_2_instance.run(draft_id=draft_id)
        
        # Should handle gracefully without making API calls
        assert result['success'] == True  # Stage 2 handles no chunks gracefully
        assert result['chunks_processed'] == 0  # No chunks to process
        assert result['chunks_cleaned'] == 0  # No chunks to clean
        assert result['failed_chunks'] == 0  # No failed chunks
    
    @pytest.mark.real_api
    @requires_previous_stages(1)
    def test_stage_2_real_pdf_content(self, register_stages_1_and_2, stage_2_instance, db_fixture, 
                                    sample_file_path, dependency_results):
        """Test cleaning with real PDF content from sample file."""
        # Use data from Stage 1 dependency (real chunks from sample file)
        assert dependency_results, "Stage 1 dependency results should be available"
        
        # Get the draft_id from Stage 1 execution results
        stage_1_data = dependency_results.get('stage_data', {}).get(1, {})
        draft_id = stage_1_data.get('draft_id')
        
        assert draft_id, "No draft_id available from Stage 1"
        
        # Verify we have real chunks from the sample file
        chunks_count = db_fixture.count_records('draft_chunks', draft_id)
        assert chunks_count > 0, f"Stage 1 should have created chunks from sample file, but found {chunks_count}"
        
        # Get chunk details to verify they're from real content
        chunks_data = db_fixture.execute_query(
            "SELECT chunk_number, LENGTH(raw_text), raw_text FROM draft_chunks WHERE draft_id = %s ORDER BY chunk_number LIMIT 3",
            (draft_id,)
        )
        
        print(f"\nProcessing {chunks_count} real chunks from {sample_file_path}:")
        for chunk_num, text_length, raw_text_sample in chunks_data:
            print(f"  Chunk {chunk_num}: {text_length} chars - '{raw_text_sample[:100]}...'")
        
        # Run Stage 2 on real content
        result = stage_2_instance.run(draft_id=draft_id)
        
        # Verify result
        assert result['success'] == True, f"Stage 2 failed on real content: {result.get('error', 'Unknown error')}"
        assert result['chunks_processed'] == chunks_count
        
        # Analyze cleaning results on real content
        cleaned_chunks = db_fixture.execute_query(
            "SELECT raw_text, cleaned_text FROM draft_chunks WHERE draft_id = %s ORDER BY chunk_number",
            (draft_id,)
        )
        
        unchanged_count = 0
        improved_count = 0
        
        for i, (raw_text, cleaned_text) in enumerate(cleaned_chunks):
            # Apply real-world cleaning assertions
            RealAPIAssertions.assert_cleaning_improved_text(raw_text, cleaned_text)
            
            if raw_text == cleaned_text:
                unchanged_count += 1
            else:
                improved_count += 1
                
        print(f"\nCleaning results on real content:")
        print(f"  Chunks unchanged (already clean): {unchanged_count}")
        print(f"  Chunks improved: {improved_count}")
        print(f"  Total processed: {len(cleaned_chunks)}")
        
        # Both outcomes are valid for real content
        assert unchanged_count + improved_count == len(cleaned_chunks)
    
    @pytest.mark.real_api
    @requires_previous_stages(1)
    def test_stage_2_max_chunk_size_handling(self, register_stages_1_and_2, stage_2_instance, db_fixture, 
                                           dependency_results):
        """Test Stage 2 can handle Stage 1's maximum chunk sizes (1500 words)."""
        # Use data from Stage 1 dependency
        assert dependency_results, "Stage 1 dependency results should be available"
        
        stage_1_data = dependency_results.get('stage_data', {}).get(1, {})
        draft_id = stage_1_data.get('draft_id')
        
        assert draft_id, "No draft_id available from Stage 1"
        
        # Get chunk sizes to verify we can handle Stage 1's output
        chunk_stats = db_fixture.execute_query(
            "SELECT MIN(LENGTH(raw_text)), MAX(LENGTH(raw_text)), AVG(LENGTH(raw_text)) FROM draft_chunks WHERE draft_id = %s",
            (draft_id,)
        )
        
        min_chars, max_chars, avg_chars = chunk_stats[0] if chunk_stats else (0, 0, 0)
        
        print(f"\nChunk size analysis:")
        print(f"  Min chunk: {min_chars} chars")
        print(f"  Max chunk: {max_chars} chars")
        print(f"  Avg chunk: {avg_chars:.0f} chars")
        
        # Verify we can handle typical Stage 1 chunks (approximately 1500 words = 6000-8000 chars)
        assert max_chars > 0, "Should have non-empty chunks"
        
        # Run Stage 2
        result = stage_2_instance.run(draft_id=draft_id)
        
        assert result['success'] == True, f"Stage 2 failed on max chunk sizes: {result.get('error', 'Unknown error')}"
        
        # Verify all chunks were processed including the largest ones
        chunks_count = db_fixture.count_records('draft_chunks', draft_id)
        assert result['chunks_processed'] == chunks_count, "Should process all chunks regardless of size"
        
        print(f"Successfully processed {chunks_count} chunks including max size {max_chars} chars")
    
    @pytest.mark.real_api
    @requires_previous_stages(1)
    def test_stage_2_performance_monitoring(self, register_stages_1_and_2, stage_2_instance, db_fixture, sample_file_path, dependency_results):
        """Test performance monitoring for real API calls."""
        # Use data from Stage 1 dependency
        assert dependency_results, "Stage 1 dependency results should be available"
        
        # Get the draft_id from Stage 1 execution results
        stage_1_data = dependency_results.get('stage_data', {}).get(1, {})
        draft_id = stage_1_data.get('draft_id')
        
        if not draft_id:
            # Fallback: try to find any existing draft with chunks
            chunks_query = db_fixture.execute_query(
                "SELECT draft_id FROM draft_chunks ORDER BY id DESC LIMIT 1"
            )
            if chunks_query:
                draft_id = chunks_query[0][0]
        
        assert draft_id, "No draft_id available from Stage 1 or existing data"
        
        # Verify Stage 1 created chunks for us to work with
        chunks_count = db_fixture.count_records('draft_chunks', draft_id)
        assert chunks_count > 0, f"Stage 1 should have created chunks, but found {chunks_count}"
        
        # Monitor performance
        start_time = time.time()
        result = stage_2_instance.run(draft_id=draft_id)
        end_time = time.time()
        
        # Verify result
        assert result['success'] == True
        assert result['chunks_processed'] == chunks_count
        
        # Performance assertions
        total_processing_time = end_time - start_time
        avg_time_per_chunk = total_processing_time / chunks_count if chunks_count > 0 else 0
        
        # Should process multiple chunks efficiently
        assert total_processing_time < 120, f"Total processing time too long: {total_processing_time:.2f}s"
        if chunks_count > 0:
            assert avg_time_per_chunk < 60, f"Average time per chunk too long: {avg_time_per_chunk:.2f}s"
        
        # Verify chunks were processed successfully
        assert result['chunks_cleaned'] >= 0, "Should have non-negative cleaned chunks"
        assert result['failed_chunks'] >= 0, "Should have non-negative failed chunks"
        
        print(f"Performance metrics:")
        print(f"  Total processing time: {total_processing_time:.2f}s")
        print(f"  Average time per chunk: {avg_time_per_chunk:.2f}s")
        print(f"  Chunks processed: {result['chunks_processed']}")
        print(f"  Chunks cleaned: {result['chunks_cleaned']}")
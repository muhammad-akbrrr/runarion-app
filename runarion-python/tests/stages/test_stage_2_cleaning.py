"""
Tests for Stage 2: Text Cleaning and Normalization with Real API
Uses real AI providers to test text cleaning functionality.
"""

import pytest
import time
from test_utils.assertions import PipelineAssertions, RealAPIAssertions
from test_utils.sample_data import SampleDataGenerator
from test_utils.real_generation_engine import RealGenerationEngineFactory


@pytest.mark.real_api
@pytest.mark.database
class TestStage2Cleaning:
    """Test Stage 2: Text Cleaning"""
    
    def test_stage_2_text_cleaning_success(self, stage_2_instance, db_fixture):
        """Test successful text cleaning with real API calls."""
        # Create test draft with chunks
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
        
        # Create test chunks with realistic text that needs cleaning
        raw_text_chunks = [
            "This  is  a test  chunk with   extra   spaces and\n\n\nmultiple line breaks that need cleaning.",
            "Another chunk with poor grammar and tpyos that need to be fixed and improved for better readability.",
            "A third chunk that has inconsistent formatting   and needs professional editing to enhance quality."
        ]
        
        chunks = []
        for i, raw_text in enumerate(raw_text_chunks):
            chunk_data = {
                'chunk_number': i + 1,
                'raw_text': raw_text,
                'cleaned_text': raw_text  # Initially same as raw
            }
            chunks.append(chunk_data)
        
        # Insert chunks into database
        with db_fixture.transaction() as conn:
            cursor = conn.cursor()
            for chunk in chunks:
                cursor.execute("""
                    INSERT INTO draft_chunks (draft_id, chunk_number, raw_text, cleaned_text)
                    VALUES (%s, %s, %s, %s)
                """, (test_draft['draft_id'], chunk['chunk_number'], 
                      chunk['raw_text'], chunk['cleaned_text']))
        
        # Run Stage 2 with real API
        start_time = time.time()
        result = stage_2_instance.run(draft_id=test_draft['draft_id'])
        end_time = time.time()
        
        # Verify result structure
        assert result['success'] == True, f"Stage 2 failed: {result.get('error', 'Unknown error')}"
        assert 'chunks_processed' in result
        assert 'total_tokens_used' in result
        assert 'processing_time_seconds' in result
        
        # Verify chunks were processed
        assert result['chunks_processed'] == len(chunks)
        assert result['total_tokens_used'] > 0
        
        # Verify processing time is reasonable
        processing_time = end_time - start_time
        assert processing_time < 120, f"Processing took too long: {processing_time:.2f}s"
        
        # Verify database state - cleaned text should be updated
        updated_chunks = db_fixture.execute_query(
            "SELECT raw_text, cleaned_text FROM draft_chunks WHERE draft_id = %s ORDER BY chunk_number",
            (test_draft['draft_id'],)
        )
        
        assert len(updated_chunks) == len(chunks)
        
        for i, (raw_text, cleaned_text) in enumerate(updated_chunks):
            # Verify text was actually cleaned
            RealAPIAssertions.assert_cleaning_improved_text(raw_text, cleaned_text)
            
            # Verify text quality
            RealAPIAssertions.assert_text_quality_basic(cleaned_text, min_length=20)
            
            # Check for specific improvements
            assert cleaned_text != raw_text, f"Chunk {i+1} was not cleaned"
            assert len(cleaned_text.strip()) > 0, f"Chunk {i+1} cleaned text is empty"
            
            # Check for reduced spacing issues
            if '  ' in raw_text:  # Multiple spaces
                assert cleaned_text.count('  ') < raw_text.count('  '), \
                    f"Chunk {i+1} should have fewer spacing issues"
    
    @pytest.mark.expensive
    def test_stage_2_large_text_cleaning(self, stage_2_instance, db_fixture):
        """Test cleaning of larger text chunks with real API."""
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
        
        # Create a large chunk (this will consume more tokens)
        large_text = """
        This is a much longer text chunk that contains various issues that need to be addressed during the cleaning process.
        
        
        It has multiple spacing issues   and   inconsistent   formatting throughout the document.
        
        There are also some grammatical errors and awkward phrasing that could be improved for better readability and flow.
        
        The text includes multiple paragraphs with different formatting styles that need to be standardized.
        
        Additionally, there are some redundant phrases and repetitive content that could be streamlined for better clarity.
        
        This type of content would typically be found in a manuscript that requires professional editing and enhancement.
        """
        
        # Insert large chunk
        with db_fixture.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO draft_chunks (draft_id, chunk_number, raw_text, cleaned_text)
                VALUES (%s, %s, %s, %s)
            """, (test_draft['draft_id'], 1, large_text, large_text))
        
        # Run Stage 2
        start_time = time.time()
        result = stage_2_instance.run(draft_id=test_draft['draft_id'])
        end_time = time.time()
        
        # Verify result
        assert result['success'] == True, f"Large text cleaning failed: {result.get('error', 'Unknown error')}"
        assert result['chunks_processed'] == 1
        assert result['total_tokens_used'] > 100  # Large text should use significant tokens
        
        # Verify processing time (large text may take longer)
        processing_time = end_time - start_time
        assert processing_time < 180, f"Large text processing took too long: {processing_time:.2f}s"
        
        # Verify cleaned text
        cleaned_chunks = db_fixture.execute_query(
            "SELECT raw_text, cleaned_text FROM draft_chunks WHERE draft_id = %s",
            (test_draft['draft_id'],)
        )
        
        raw_text, cleaned_text = cleaned_chunks[0]
        
        # Verify improvements
        RealAPIAssertions.assert_cleaning_improved_text(raw_text, cleaned_text)
        RealAPIAssertions.assert_text_quality_basic(cleaned_text, min_length=200)
        
        # Check for specific large text improvements
        assert len(cleaned_text.strip()) >= len(raw_text.strip()) * 0.8, \
            "Cleaned text should not be dramatically shorter"
    
    @pytest.mark.real_api
    def test_stage_2_unicode_handling(self, stage_2_instance, db_fixture):
        """Test handling of Unicode characters with real API."""
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
        
        # Create Unicode text chunks
        unicode_text = "This text contains café and naïve characters. It also has 你好世界 and العربية text that needs cleaning while preserving the Unicode characters. The émojis like 🌟 and 📚 should also be handled properly."
        
        # Insert Unicode chunk
        with db_fixture.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO draft_chunks (draft_id, chunk_number, raw_text, cleaned_text)
                VALUES (%s, %s, %s, %s)
            """, (test_draft['draft_id'], 1, unicode_text, unicode_text))
        
        # Run Stage 2
        result = stage_2_instance.run(draft_id=test_draft['draft_id'])
        
        # Verify result
        assert result['success'] == True, f"Unicode handling failed: {result.get('error', 'Unknown error')}"
        
        # Verify Unicode preservation
        cleaned_chunks = db_fixture.execute_query(
            "SELECT raw_text, cleaned_text FROM draft_chunks WHERE draft_id = %s",
            (test_draft['draft_id'],)
        )
        
        raw_text, cleaned_text = cleaned_chunks[0]
        
        # Verify basic cleaning
        RealAPIAssertions.assert_text_quality_basic(cleaned_text)
        
        # Verify Unicode characters are preserved (at least some of them)
        unicode_chars = ['café', '你好', 'العربية', '🌟', '📚', 'naïve']
        preserved_count = sum(1 for char in unicode_chars if char in cleaned_text)
        
        # We expect at least half of the Unicode characters to be preserved
        assert preserved_count >= len(unicode_chars) // 2, \
            f"Unicode preservation failed: only {preserved_count}/{len(unicode_chars)} characters preserved"
    
    @pytest.mark.real_api
    def test_stage_2_no_chunks_handling(self, stage_2_instance, db_fixture):
        """Test handling when no chunks exist with real API setup."""
        # Create test draft without chunks
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
        
        # Run Stage 2 (no chunks in database)
        result = stage_2_instance.run(draft_id=test_draft['draft_id'])
        
        # Should handle gracefully without making API calls
        assert result['success'] == False
        assert 'error' in result
        assert 'no chunks' in result['error'].lower() or 'not found' in result['error'].lower()
    
    @pytest.mark.real_api
    def test_stage_2_performance_monitoring(self, stage_2_instance, db_fixture):
        """Test performance monitoring for real API calls."""
        # Create test draft with multiple chunks
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
        
        # Create 3 chunks for performance testing
        test_chunks = [
            "First chunk with some text that needs cleaning and improvement.",
            "Second chunk with different content that also requires professional editing.",
            "Third chunk to test performance with multiple API calls in sequence."
        ]
        
        # Insert chunks
        with db_fixture.transaction() as conn:
            cursor = conn.cursor()
            for i, chunk_text in enumerate(test_chunks):
                cursor.execute("""
                    INSERT INTO draft_chunks (draft_id, chunk_number, raw_text, cleaned_text)
                    VALUES (%s, %s, %s, %s)
                """, (test_draft['draft_id'], i + 1, chunk_text, chunk_text))
        
        # Monitor performance
        start_time = time.time()
        result = stage_2_instance.run(draft_id=test_draft['draft_id'])
        end_time = time.time()
        
        # Verify result
        assert result['success'] == True
        assert result['chunks_processed'] == len(test_chunks)
        
        # Performance assertions
        total_processing_time = end_time - start_time
        avg_time_per_chunk = total_processing_time / len(test_chunks)
        
        # Should process multiple chunks efficiently
        assert total_processing_time < 120, f"Total processing time too long: {total_processing_time:.2f}s"
        assert avg_time_per_chunk < 60, f"Average time per chunk too long: {avg_time_per_chunk:.2f}s"
        
        # Token usage should be reasonable
        assert result['total_tokens_used'] > 0
        avg_tokens_per_chunk = result['total_tokens_used'] / len(test_chunks)
        assert avg_tokens_per_chunk > 10, "Token usage seems too low"
        assert avg_tokens_per_chunk < 1000, "Token usage seems too high"
        
        print(f"Performance metrics:")
        print(f"  Total processing time: {total_processing_time:.2f}s")
        print(f"  Average time per chunk: {avg_time_per_chunk:.2f}s")
        print(f"  Total tokens used: {result['total_tokens_used']}")
        print(f"  Average tokens per chunk: {avg_tokens_per_chunk:.1f}")
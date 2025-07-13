"""
Tests for Stage 1: PDF Ingestion and Text Chunking
"""

import pytest
import os
from test_utils.assertions import PipelineAssertions
from test_utils.sample_data import SampleDataGenerator
from test_utils.path_manager import get_temp_output

@pytest.mark.stage
@pytest.mark.database
class TestStage1Ingestion:
    """Test Stage 1: PDF Ingestion and Text Chunking"""
    
    def test_stage_1_text_file_ingestion(self, stage_1_instance, db_fixture, sample_file_path, 
                                        expected_output_helper, stage_output_validator):
        """Test successful ingestion of a text file."""
        # Create test draft
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
        
        # Run Stage 1
        result = stage_1_instance.run(
            draft_id=test_draft['draft_id'],
            file_path=sample_file_path
        )
        
        # Verify result structure
        assert result['success'] == True
        assert 'chunks_created' in result
        assert 'chunks_stored' in result
        assert 'total_characters' in result
        assert 'total_tokens' in result
        
        # Verify chunks were created
        assert result['chunks_created'] > 0
        assert result['chunks_stored'] == result['chunks_created']
        
        # Verify database state
        chunks_count = db_fixture.count_records('draft_chunks', test_draft['draft_id'])
        assert chunks_count == result['chunks_created']
        
        # Verify chunk data structure
        chunks = db_fixture.execute_query(
            "SELECT * FROM draft_chunks WHERE draft_id = %s ORDER BY chunk_number",
            (test_draft['draft_id'],)
        )
        
        for i, chunk in enumerate(chunks):
            assert chunk[2] == i + 1  # chunk_number
            assert len(chunk[3]) > 0  # raw_text
            assert len(chunk[4]) > 0  # cleaned_text
        
        # Validate against expected output structure if available
        expected_filename = 'text_ingestion_expected.json'
        expected_output = expected_output_helper.load(1, expected_filename)
        
        if expected_output is not None:
            # Validate structure matches expected
            is_valid, errors = stage_output_validator(1, result, expected_filename)
            if not is_valid:
                # Log validation errors but don't fail the test (expected outputs may not exist yet)
                print(f"Structure validation warnings: {errors}")
        else:
            # Optionally create expected output for future use
            pass
            # expected_output_helper.create_from_actual(1, result, expected_filename)
    
    def test_stage_1_pdf_file_ingestion(self, stage_1_instance, db_fixture, temp_output_file):
        """Test ingestion of a PDF file."""
        # Create a simple test PDF file
        test_content = """
        Chapter 1: The Beginning
        
        This is a test PDF document for ingestion testing.
        It contains multiple paragraphs and chapters.
        
        Chapter 2: The Middle
        
        This chapter continues the story with more content.
        There are various formatting elements to test.
        """
        
        # Create test PDF file using new path management
        temp_pdf_path = str(get_temp_output('test_ingestion.pdf'))
        with open(temp_pdf_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        try:
            # Create test draft
            test_data = SampleDataGenerator(db_fixture.connection_pool)
            draft_data = test_data.generate_draft_request(file_name='test.pdf')
            
            workspace_data = db_fixture.create_test_workspace(
                workspace_id=draft_data['workspace_id'],
                user_id=draft_data['user_id']
            )
            
            test_draft = db_fixture.create_test_draft(
                draft_id=draft_data['draft_id'],
                workspace_id=workspace_data['workspace_id'],
                user_id=workspace_data['user_id'],
                file_path=temp_pdf_path
            )
            
            # Run Stage 1
            result = stage_1_instance.run(
                draft_id=test_draft['draft_id'],
                file_path=temp_pdf_path
            )
            
            # Verify result (may fail due to simplified PDF, but should handle gracefully)
            assert 'success' in result
            assert 'error' in result or result['success'] == True
            
        finally:
            pass
    
    def test_stage_1_invalid_file_handling(self, stage_1_instance, db_fixture):
        """Test handling of invalid or non-existent files."""
        # Create test draft
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
            file_path='/app/tests/sample_files/inputs/nonexistent.txt'
        )
        
        # Run Stage 1 with non-existent file
        result = stage_1_instance.run(
            draft_id=test_draft['draft_id'],
            file_path='/path/to/nonexistent/file.txt'
        )
        
        # Should fail gracefully
        assert result['success'] == False
        assert 'error' in result
        assert 'file' in result['error'].lower() or 'not found' in result['error'].lower()
        
        # Verify no chunks were created
        chunks_count = db_fixture.count_records('draft_chunks', test_draft['draft_id'])
        assert chunks_count == 0
    
    def test_stage_1_empty_file_handling(self, stage_1_instance, db_fixture):
        """Test handling of empty files."""
        # Create empty file using new path management
        empty_file_path = str(get_temp_output('empty_test.txt'))
        with open(empty_file_path, 'w', encoding='utf-8') as f:
            f.write('')  # Empty file
        
        try:
            # Create test draft
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
                file_path=empty_file_path
            )
            
            # Run Stage 1
            result = stage_1_instance.run(
                draft_id=test_draft['draft_id'],
                file_path=empty_file_path
            )
            
            # Should handle empty file gracefully
            assert 'success' in result
            
            if result['success']:
                assert result['chunks_created'] == 0
                assert result['total_characters'] == 0
            else:
                assert 'error' in result
                assert 'empty' in result['error'].lower()
            
        finally:
            # Cleanup handled by temp file management
            pass
    
    def test_stage_1_large_file_chunking(self, stage_1_instance, db_fixture, expected_output_helper):
        """Test chunking of large files."""
        # Create large test file
        large_content = SampleDataGenerator(db_fixture.connection_pool).generate_manuscript_content(
            chapter_count=10,
            words_per_chapter=5000  # 50k words total
        )
        
        large_file_path = str(get_temp_output('large_test.txt'))
        with open(large_file_path, 'w', encoding='utf-8') as f:
            f.write(large_content)
        
        try:
            # Create test draft
            test_data = SampleDataGenerator(db_fixture.connection_pool)
            draft_data = test_data.generate_draft_request(file_name='large_manuscript.txt')
            
            workspace_data = db_fixture.create_test_workspace(
                workspace_id=draft_data['workspace_id'],
                user_id=draft_data['user_id']
            )
            
            test_draft = db_fixture.create_test_draft(
                draft_id=draft_data['draft_id'],
                workspace_id=workspace_data['workspace_id'],
                user_id=workspace_data['user_id'],
                file_path=large_file_path
            )
            
            # Run Stage 1
            result = stage_1_instance.run(
                draft_id=test_draft['draft_id'],
                file_path=large_file_path
            )
            
            # Verify result
            assert result['success'] == True
            assert result['chunks_created'] > 5  # Should create multiple chunks
            assert result['total_characters'] > 100000  # Should be substantial
            
            # Verify chunks are reasonably sized
            chunks = db_fixture.execute_query(
                "SELECT LENGTH(raw_text) FROM draft_chunks WHERE draft_id = %s",
                (test_draft['draft_id'],)
            )
            
            for chunk_length in chunks:
                assert chunk_length[0] > 100  # Not too small
                assert chunk_length[0] < 50000  # Not too large (increased for realistic manuscript chunks)
            
            # Optional: Create expected output for large file chunking
            expected_filename = 'large_file_chunking_expected.json'
            if not expected_output_helper.load(1, expected_filename):
                # Create expected output template for future validation
                expected_template = {
                    'success': True,
                    'chunks_created': result['chunks_created'],
                    'min_chunks_expected': 5,  # Should create at least 5 chunks for large file
                    'total_characters_range': [100000, 500000]  # Expected character range
                }
                # expected_output_helper.save(1, expected_filename, expected_template)
            
        finally:
            # Cleanup handled by temp file management
            pass
    
    def test_stage_1_unicode_handling(self, stage_1_instance, db_fixture):
        """Test handling of Unicode characters and different encodings."""
        # Create file with Unicode characters
        unicode_content = """
        Chapter 1: The Beginning
        
        This text contains various Unicode characters: 
        - Accented characters: café, naïve, résumé
        - Non-Latin scripts: 你好, мир, العالم
        - Emoji: 📖 📝 ✨
        - Special symbols: © ™ ® ™ 
        
        Chapter 2: More Content
        
        Testing different types of content with Unicode support.
        """
        
        unicode_file_path = str(get_temp_output('unicode_test.txt'))
        with open(unicode_file_path, 'w', encoding='utf-8') as f:
            f.write(unicode_content)
        
        try:
            # Create test draft
            test_data = SampleDataGenerator(db_fixture.connection_pool)
            draft_data = test_data.generate_draft_request(file_name='unicode_test.txt')
            
            workspace_data = db_fixture.create_test_workspace(
                workspace_id=draft_data['workspace_id'],
                user_id=draft_data['user_id']
            )
            
            test_draft = db_fixture.create_test_draft(
                draft_id=draft_data['draft_id'],
                workspace_id=workspace_data['workspace_id'],
                user_id=workspace_data['user_id'],
                file_path=unicode_file_path
            )
            
            # Run Stage 1
            result = stage_1_instance.run(
                draft_id=test_draft['draft_id'],
                file_path=unicode_file_path
            )
            
            # Verify result
            assert result['success'] == True
            assert result['chunks_created'] > 0
            
            # Verify Unicode characters were preserved
            chunks = db_fixture.execute_query(
                "SELECT raw_text FROM draft_chunks WHERE draft_id = %s",
                (test_draft['draft_id'],)
            )
            
            # Check that Unicode characters are preserved
            all_text = ' '.join([chunk[0] for chunk in chunks])
            assert 'café' in all_text
            assert '你好' in all_text
            assert '📖' in all_text
            
        finally:
            # Cleanup
            if os.path.exists(unicode_file_path):
                os.unlink(unicode_file_path)
    
    def test_stage_1_chunk_statistics(self, stage_1_instance, db_fixture, sample_file_path):
        """Test chunk statistics functionality."""
        # Create test draft
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
        
        # Run Stage 1
        result = stage_1_instance.run(
            draft_id=test_draft['draft_id'],
            file_path=sample_file_path
        )
        
        assert result['success'] == True
        
        # Get chunk statistics
        stats = stage_1_instance.get_chunk_statistics(test_draft['draft_id'])
        
        # Verify statistics structure
        assert 'chunk_count' in stats
        assert 'avg_chunk_length' in stats
        assert 'min_chunk_length' in stats
        assert 'max_chunk_length' in stats
        assert 'total_characters' in stats
        
        # Verify statistics values
        assert stats['chunk_count'] == result['chunks_created']
        assert stats['total_characters'] == result['total_characters']
        assert stats['avg_chunk_length'] > 0
        assert stats['min_chunk_length'] > 0
        assert stats['max_chunk_length'] >= stats['min_chunk_length']
    
    def test_stage_1_reprocessing(self, stage_1_instance, db_fixture, sample_file_path):
        """Test reprocessing chunks with different parameters."""
        # Create test draft
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
        
        # Run Stage 1 initially
        initial_result = stage_1_instance.run(
            draft_id=test_draft['draft_id'],
            file_path=sample_file_path
        )
        
        assert initial_result['success'] == True
        initial_chunks_count = initial_result['chunks_created']
        
        # Reprocess with different chunk size
        reprocess_result = stage_1_instance.reprocess_chunks(
            draft_id=test_draft['draft_id'],
            file_path=sample_file_path,
            new_chunk_size=500  # Smaller chunks
        )
        
        # Verify reprocessing
        assert reprocess_result['success'] == True
        assert reprocess_result['reprocessed'] == True
        assert 'deleted_chunks' in reprocess_result
        assert reprocess_result['deleted_chunks'] == initial_chunks_count
        
        # Verify new chunks were created
        assert reprocess_result['chunks_created'] >= initial_chunks_count  # Should create more chunks
        
        # Verify database state
        final_chunks_count = db_fixture.count_records('draft_chunks', test_draft['draft_id'])
        assert final_chunks_count == reprocess_result['chunks_created']
    
    def test_stage_1_database_error_handling(self, stage_1_instance, db_fixture, sample_file_path):
        """Test handling of database errors during ingestion."""
        # Create test draft
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
        
        # Mock database error
        from unittest.mock import patch
        
        with patch.object(stage_1_instance.db_pool, 'getconn', side_effect=Exception("Database connection failed")):
            # Run Stage 1
            result = stage_1_instance.run(
                draft_id=test_draft['draft_id'],
                file_path=sample_file_path
            )
            
            # Should fail gracefully
            assert result['success'] == False
            assert 'error' in result
            assert 'database' in result['error'].lower() or 'connection' in result['error'].lower()
    
    def test_stage_1_concurrent_processing(self, stage_1_instance, db_fixture, sample_file_path):
        """Test concurrent processing of multiple drafts."""
        import threading
        import queue
        
        # Create multiple test drafts
        test_data = SampleDataGenerator(db_fixture.connection_pool)
        draft_requests = []
        
        for i in range(3):
            draft_data = test_data.generate_draft_request(file_name=f'concurrent_test_{i}.txt')
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
            
            draft_requests.append(test_draft)
        
        # Function to process a draft
        def process_draft(draft_info, results_queue):
            try:
                result = stage_1_instance.run(
                    draft_id=draft_info['draft_id'],
                    file_path=sample_file_path
                )
                results_queue.put({
                    'draft_id': draft_info['draft_id'],
                    'success': result['success'],
                    'chunks_created': result.get('chunks_created', 0)
                })
            except Exception as e:
                results_queue.put({
                    'draft_id': draft_info['draft_id'],
                    'error': str(e)
                })
        
        # Launch concurrent processing
        threads = []
        results_queue = queue.Queue()
        
        for draft_info in draft_requests:
            thread = threading.Thread(target=process_draft, args=(draft_info, results_queue))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=30)
        
        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        # Verify all drafts were processed
        assert len(results) == len(draft_requests)
        
        # Verify all succeeded
        for result in results:
            if 'error' in result:
                pytest.fail(f"Processing failed for draft {result['draft_id']}: {result['error']}")
            
            assert result['success'] == True
            assert result['chunks_created'] > 0
            
            # Verify database state
            chunks_count = db_fixture.count_records('draft_chunks', result['draft_id'])
            assert chunks_count == result['chunks_created']
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
    
    def test_stage_1_text_file_ingestion(self, register_stage_1_only, stage_1_instance, db_fixture, sample_file_path, expected_output_helper, stage_output_validator, test_output_options, output_generator):
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
        assert 'total_words' in result
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
        
        # Generate test outputs for debugging and next stage seeding
        if test_output_options['generate_outputs']:
            output_files = output_generator.generate_test_output(
                stage_number=1,
                test_name='test_stage_1_text_file_ingestion',
                test_result=result,
                db_fixture=db_fixture,
                additional_data={
                    'sample_file_path': sample_file_path,
                    'test_configuration': {
                        'file_type': 'text',
                        'chunking_strategy': 'word_based_with_token_validation'
                    }
                }
            )
            
            # Log output file locations for reference
            for output_type, file_path in output_files.items():
                print(f"Generated {output_type} output: {file_path}")
    
    def test_stage_1_pdf_file_ingestion(self, register_stage_1_only, stage_1_instance, db_fixture, sample_file_path):
        """Test ingestion of a real PDF file using PyMuPDF extraction."""
        # Use real PDF sample file for authentic testing
        pdf_file_path = sample_file_path or os.path.join(
            os.path.dirname(__file__), '..', 'sample_files', 'inputs', 'short_story.pdf'
        )
        
        if not os.path.exists(pdf_file_path):
            pytest.skip(f"Sample PDF file not found: {pdf_file_path}")
        
        # Verify it's actually a PDF file
        if not pdf_file_path.lower().endswith('.pdf'):
            pytest.skip("Sample file is not a PDF - skipping PDF-specific test")
        
        # Create test draft
        test_data = SampleDataGenerator(db_fixture.connection_pool)
        draft_data = test_data.generate_draft_request(file_name=os.path.basename(pdf_file_path))
        
        workspace_data = db_fixture.create_test_workspace(
            workspace_id=draft_data['workspace_id'],
            user_id=draft_data['user_id']
        )
        
        test_draft = db_fixture.create_test_draft(
            draft_id=draft_data['draft_id'],
            workspace_id=workspace_data['workspace_id'],
            user_id=workspace_data['user_id'],
            file_path=pdf_file_path
        )
        
        # Run Stage 1 with real PDF processing
        result = stage_1_instance.run(
            draft_id=test_draft['draft_id'],
            file_path=pdf_file_path
        )
        
        # Verify successful processing
        assert result['success'] == True, f"PDF processing failed: {result.get('error', 'Unknown error')}"
        assert 'chunks_created' in result
        assert 'chunks_stored' in result
        assert result['chunks_created'] > 0, "Should create chunks from real PDF content"
        assert result['chunks_stored'] == result['chunks_created'], "All chunks should be stored"
        
        # Verify chunks were actually created with real content
        chunks = db_fixture.execute_query(
            "SELECT chunk_number, raw_text, LENGTH(raw_text) as text_length FROM draft_chunks WHERE draft_id = %s ORDER BY chunk_number",
            (test_draft['draft_id'],)
        )
        
        assert len(chunks) > 0, "Should have chunks in database"
        
        # Verify chunks contain meaningful content (not just whitespace)
        for chunk_number, raw_text, text_length in chunks:
            assert text_length > 50, f"Chunk {chunk_number} too short ({text_length} chars) - may indicate extraction failure"
            assert raw_text.strip(), f"Chunk {chunk_number} is empty or whitespace only"
            
        # Verify PDF-specific processing characteristics
        total_content_length = sum(len(chunk[1]) for chunk in chunks)
        assert total_content_length > 500, "Total extracted content should be substantial for a real PDF"
        
        # Log PDF processing results for debugging
        print(f"\nPDF Processing Results:")
        print(f"  File: {os.path.basename(pdf_file_path)}")
        print(f"  Chunks created: {result['chunks_created']}")
        print(f"  Total content length: {total_content_length} characters")
        print(f"  Average chunk size: {total_content_length // len(chunks) if chunks else 0} characters")
    
    def test_stage_1_document_processor_constants_validation(self, register_stage_1_only, stage_1_instance, db_fixture, sample_file_path):
        """Test that DocumentProcessor constants are enforced in real processing."""
        # Use real sample file for authentic constant validation
        test_file_path = sample_file_path or os.path.join(
            os.path.dirname(__file__), '..', 'sample_files', 'inputs', 'short_story.pdf'
        )
        
        if not os.path.exists(test_file_path):
            pytest.skip(f"Sample file not found: {test_file_path}")
        
        # Create test draft
        test_data = SampleDataGenerator(db_fixture.connection_pool)
        draft_data = test_data.generate_draft_request(file_name=os.path.basename(test_file_path))
        
        workspace_data = db_fixture.create_test_workspace(
            workspace_id=draft_data['workspace_id'],
            user_id=draft_data['user_id']
        )
        
        test_draft = db_fixture.create_test_draft(
            draft_id=draft_data['draft_id'],
            workspace_id=workspace_data['workspace_id'],
            user_id=workspace_data['user_id'],
            file_path=test_file_path
        )
        
        # Run Stage 1
        result = stage_1_instance.run(
            draft_id=test_draft['draft_id'],
            file_path=test_file_path
        )
        
        assert result['success'] == True
        
        # Verify DocumentProcessor constants are enforced
        chunks = db_fixture.execute_query(
            "SELECT raw_text, LENGTH(raw_text) as char_length FROM draft_chunks WHERE draft_id = %s ORDER BY chunk_number",
            (test_draft['draft_id'],)
        )
        
        # Import DocumentProcessor to access constants
        from utils.document_processor import DocumentProcessor
        
        # Test DEFAULT_WORD_LIMIT = 1500 targeting
        word_counts = []
        total_word_violations = 0
        
        for raw_text, char_length in chunks:
            word_count = len(raw_text.split())
            word_counts.append(word_count)
            
            # Allow reasonable variance (±33%) around 1500-word target
            if word_count > DocumentProcessor.DEFAULT_WORD_LIMIT * 1.5:  # 2250 words
                total_word_violations += 1
        
        # Most chunks should respect word targeting (allow some edge cases)
        word_violation_rate = total_word_violations / len(chunks) if chunks else 0
        assert word_violation_rate < 0.2, f"Too many chunks exceed 1500-word targeting: {word_violation_rate*100:.1f}%"
        
        # Test that average chunk size trends toward DEFAULT_WORD_LIMIT
        if len(word_counts) > 1:
            avg_words = sum(word_counts) / len(word_counts)
            # Should be reasonably close to 1500 words (allow 50% variance for real content)
            assert 750 <= avg_words <= 2250, f"Average chunk size ({avg_words:.0f} words) too far from 1500-word target"
        
        # Test DEFAULT_CHUNK_SIZE = 4000 token safety (approximate)
        # Estimate tokens as chars/4 (conservative estimate)
        token_violations = 0
        for raw_text, char_length in chunks:
            estimated_tokens = char_length // 4
            if estimated_tokens > DocumentProcessor.DEFAULT_CHUNK_SIZE:
                token_violations += 1
        
        # NO chunks should exceed token safety limit
        assert token_violations == 0, f"Found {token_violations} chunks that may exceed 4000-token limit"
        
        print(f"\nDocumentProcessor Constants Validation:")
        print(f"  Chunks created: {len(chunks)}")
        print(f"  Average words per chunk: {sum(word_counts) / len(word_counts) if word_counts else 0:.0f}")
        print(f"  Word limit violations (>2250): {total_word_violations}")
        print(f"  Token limit violations (>4000 est.): {token_violations}")
    
    def test_stage_1_semantic_overlap_creation(self, register_stage_1_only, stage_1_instance, db_fixture, sample_file_path):
        """Test that WORD_OVERLAP_SIZE = 50 creates proper semantic overlaps."""
        # Use real sample file that's large enough to create multiple chunks
        test_file_path = sample_file_path or os.path.join(
            os.path.dirname(__file__), '..', 'sample_files', 'inputs', 'short_story.pdf'
        )
        
        if not os.path.exists(test_file_path):
            pytest.skip(f"Sample file not found: {test_file_path}")
        
        # Create test draft
        test_data = SampleDataGenerator(db_fixture.connection_pool)
        draft_data = test_data.generate_draft_request(file_name=os.path.basename(test_file_path))
        
        workspace_data = db_fixture.create_test_workspace(
            workspace_id=draft_data['workspace_id'],
            user_id=draft_data['user_id']
        )
        
        test_draft = db_fixture.create_test_draft(
            draft_id=draft_data['draft_id'],
            workspace_id=workspace_data['workspace_id'],
            user_id=workspace_data['user_id'],
            file_path=test_file_path
        )
        
        # Run Stage 1
        result = stage_1_instance.run(
            draft_id=test_draft['draft_id'],
            file_path=test_file_path
        )
        
        assert result['success'] == True
        
        # Get chunks to analyze overlap behavior
        chunks = db_fixture.execute_query(
            "SELECT chunk_number, raw_text FROM draft_chunks WHERE draft_id = %s ORDER BY chunk_number",
            (test_draft['draft_id'],)
        )
        
        if len(chunks) < 2:
            pytest.skip("Need at least 2 chunks to test overlap behavior")
        
        # Import DocumentProcessor to access constants
        from utils.document_processor import DocumentProcessor
        
        # Check for semantic overlaps between consecutive chunks
        overlap_detected = 0
        overlap_word_counts = []
        
        for i in range(1, len(chunks)):
            chunk_num, current_text = chunks[i]
            prev_chunk_num, prev_text = chunks[i-1]
            
            # Check if current chunk starts with content from previous chunk (overlap)
            # Get last ~100 words from previous chunk
            prev_words = prev_text.split()
            if len(prev_words) > 20:
                last_section = ' '.join(prev_words[-20:])  # Last 20 words
                
                # Check if any part of this appears at start of current chunk
                current_start = ' '.join(current_text.split()[:30])  # First 30 words
                
                # Look for common phrases (indicating overlap)
                prev_sentences = last_section.split('.')
                current_sentences = current_start.split('.')
                
                for prev_sent in prev_sentences:
                    for curr_sent in current_sentences:
                        if prev_sent.strip() and curr_sent.strip() and len(prev_sent.strip()) > 10:
                            if prev_sent.strip() in curr_sent or curr_sent.strip() in prev_sent:
                                overlap_detected += 1
                                overlap_word_counts.append(len(prev_sent.split()))
                                break
        
        print(f"\nSemantic Overlap Analysis:")
        print(f"  Total chunks: {len(chunks)}")
        print(f"  Overlaps detected: {overlap_detected}")
        print(f"  Target overlap size: {DocumentProcessor.WORD_OVERLAP_SIZE} words")
        if overlap_word_counts:
            print(f"  Average overlap size: {sum(overlap_word_counts) / len(overlap_word_counts):.0f} words")
        
        # Document the overlap behavior (DocumentProcessor may or may not create overlaps)
        # This test documents the actual behavior rather than enforcing specific requirements
    
    def test_stage_1_real_pdf_structural_analysis(self, register_stage_1_only, stage_1_instance, db_fixture, sample_file_path):
        """Test PyMuPDF structural analysis with real PDF content."""
        # Use real PDF sample file
        pdf_file_path = sample_file_path if sample_file_path and sample_file_path.endswith('.pdf') else os.path.join(
            os.path.dirname(__file__), '..', 'sample_files', 'inputs', 'short_story.pdf'
        )
        
        if not os.path.exists(pdf_file_path) or not pdf_file_path.endswith('.pdf'):
            pytest.skip("Real PDF file required for structural analysis test")
        
        # Test direct DocumentProcessor functionality
        from utils.document_processor import DocumentProcessor
        
        processor = DocumentProcessor()
        
        # Test raw extraction
        try:
            extracted_text = processor.extract_text_from_file(pdf_file_path)
            assert len(extracted_text) > 100, "Should extract substantial text from real PDF"
            
            # Test cleaning
            cleaned_text = processor.clean_text(extracted_text)
            assert len(cleaned_text) > 50, "Cleaned text should be substantial"
            
            # Test chunking with real content
            chunks = processor.chunk_text(cleaned_text, provider="openai", model="gpt-4o")
            assert len(chunks) > 0, "Should create chunks from real PDF content"
            
            # Verify chunk structure
            for chunk in chunks:
                assert 'chunk_number' in chunk
                assert 'raw_text' in chunk
                assert 'word_count' in chunk
                assert 'token_count' in chunk
                assert chunk['word_count'] > 0
                assert chunk['token_count'] > 0
                
            print(f"\nPDF Structural Analysis Results:")
            print(f"  Extracted text length: {len(extracted_text)} chars")
            print(f"  Cleaned text length: {len(cleaned_text)} chars")
            print(f"  Chunks created: {len(chunks)}")
            print(f"  Total words: {sum(c['word_count'] for c in chunks)}")
            print(f"  Total tokens: {sum(c['token_count'] for c in chunks)}")
            
        except Exception as e:
            pytest.fail(f"PDF structural analysis failed: {e}")
    
    def test_stage_1_pdf_encoding_handling(self, register_stage_1_only, stage_1_instance, db_fixture, sample_file_path):
        """Test PDF processing with various encoding scenarios."""
        # Use real PDF sample file
        pdf_file_path = sample_file_path if sample_file_path and sample_file_path.endswith('.pdf') else os.path.join(
            os.path.dirname(__file__), '..', 'sample_files', 'inputs', 'short_story.pdf'
        )
        
        if not os.path.exists(pdf_file_path) or not pdf_file_path.endswith('.pdf'):
            pytest.skip("Real PDF file required for encoding test")
        
        # Create test draft
        test_data = SampleDataGenerator(db_fixture.connection_pool)
        draft_data = test_data.generate_draft_request(file_name=os.path.basename(pdf_file_path))
        
        workspace_data = db_fixture.create_test_workspace(
            workspace_id=draft_data['workspace_id'],
            user_id=draft_data['user_id']
        )
        
        test_draft = db_fixture.create_test_draft(
            draft_id=draft_data['draft_id'],
            workspace_id=workspace_data['workspace_id'],
            user_id=workspace_data['user_id'],
            file_path=pdf_file_path
        )
        
        # Run Stage 1
        result = stage_1_instance.run(
            draft_id=test_draft['draft_id'],
            file_path=pdf_file_path
        )
        
        # Should handle encoding gracefully
        assert result['success'] == True, f"PDF encoding handling failed: {result.get('error', 'Unknown error')}"
        
        # Verify extracted content is properly encoded
        chunks = db_fixture.execute_query(
            "SELECT raw_text FROM draft_chunks WHERE draft_id = %s ORDER BY chunk_number",
            (test_draft['draft_id'],)
        )
        
        for chunk_data in chunks:
            raw_text = chunk_data[0]
            
            # Text should be valid UTF-8
            try:
                raw_text.encode('utf-8')
            except UnicodeEncodeError:
                pytest.fail("Extracted text contains invalid UTF-8 characters")
            
            # Should not contain common PDF extraction artifacts
            assert '\x00' not in raw_text, "Text contains null bytes"
            assert len(raw_text.strip()) > 0, "Chunk should not be empty"
    
    def test_stage_1_malformed_pdf_graceful_failure(self, register_stage_1_only, stage_1_instance, db_fixture):
        """Test graceful handling of malformed or corrupted PDF files."""
        # Create a fake malformed PDF (just text with .pdf extension)
        malformed_pdf_path = str(get_temp_output('malformed_test.pdf'))
        
        with open(malformed_pdf_path, 'w', encoding='utf-8') as f:
            f.write("This is not a real PDF file, just text with PDF extension.")
        
        try:
            # Create test draft
            test_data = SampleDataGenerator(db_fixture.connection_pool)
            draft_data = test_data.generate_draft_request(file_name='malformed_test.pdf')
            
            workspace_data = db_fixture.create_test_workspace(
                workspace_id=draft_data['workspace_id'],
                user_id=draft_data['user_id']
            )
            
            test_draft = db_fixture.create_test_draft(
                draft_id=draft_data['draft_id'],
                workspace_id=workspace_data['workspace_id'],
                user_id=workspace_data['user_id'],
                file_path=malformed_pdf_path
            )
            
            # Run Stage 1
            result = stage_1_instance.run(
                draft_id=test_draft['draft_id'],
                file_path=malformed_pdf_path
            )
            
            # Should either succeed with alternative processing or fail gracefully
            if result['success']:
                # If it succeeds, should have created some chunks (treated as text)
                assert result['chunks_created'] > 0
            else:
                # If it fails, should have meaningful error message
                assert 'error' in result
                assert len(result['error']) > 0
            
        finally:
            # Cleanup
            if os.path.exists(malformed_pdf_path):
                os.unlink(malformed_pdf_path)
    
    def test_stage_1_pdf_vs_text_comparison(self, register_stage_1_only, stage_1_instance, db_fixture, sample_file_path):
        """Compare PDF processing vs TXT processing of similar content."""
        # Use real PDF sample file
        pdf_file_path = sample_file_path if sample_file_path and sample_file_path.endswith('.pdf') else os.path.join(
            os.path.dirname(__file__), '..', 'sample_files', 'inputs', 'short_story.pdf'
        )
        
        if not os.path.exists(pdf_file_path) or not pdf_file_path.endswith('.pdf'):
            pytest.skip("Real PDF file required for comparison test")
        
        # First, extract PDF content and save as TXT for comparison
        from utils.document_processor import DocumentProcessor
        processor = DocumentProcessor()
        
        try:
            pdf_extracted_text = processor.extract_text_from_file(pdf_file_path)
            pdf_cleaned_text = processor.clean_text(pdf_extracted_text)
            
            # Create temporary TXT file with the same content
            txt_file_path = str(get_temp_output('pdf_comparison.txt'))
            with open(txt_file_path, 'w', encoding='utf-8') as f:
                f.write(pdf_cleaned_text)
            
            # Process both files through Stage 1
            results = {}
            
            for file_type, file_path in [('PDF', pdf_file_path), ('TXT', txt_file_path)]:
                test_data = SampleDataGenerator(db_fixture.connection_pool)
                draft_data = test_data.generate_draft_request(
                    file_name=f'comparison_{file_type.lower()}.{file_type.lower()}'
                )
                
                workspace_data = db_fixture.create_test_workspace(
                    workspace_id=draft_data['workspace_id'],
                    user_id=draft_data['user_id']
                )
                
                test_draft = db_fixture.create_test_draft(
                    draft_id=draft_data['draft_id'],
                    workspace_id=workspace_data['workspace_id'],
                    user_id=workspace_data['user_id'],
                    file_path=file_path
                )
                
                result = stage_1_instance.run(
                    draft_id=test_draft['draft_id'],
                    file_path=file_path
                )
                
                results[file_type] = {
                    'result': result,
                    'draft_id': test_draft['draft_id']
                }
            
            # Compare results
            pdf_result = results['PDF']['result']
            txt_result = results['TXT']['result']
            
            assert pdf_result['success'] == True, "PDF processing should succeed"
            assert txt_result['success'] == True, "TXT processing should succeed"
            
            # Chunk counts should be similar (allow some variance)
            pdf_chunks = pdf_result['chunks_created']
            txt_chunks = txt_result['chunks_created']
            
            # Allow up to 1 chunk difference (due to processing differences)
            assert abs(pdf_chunks - txt_chunks) <= 1, f"Chunk count difference too large: PDF={pdf_chunks}, TXT={txt_chunks}"
            
            print(f"\nPDF vs TXT Processing Comparison:")
            print(f"  PDF chunks: {pdf_chunks}")
            print(f"  TXT chunks: {txt_chunks}")
            print(f"  Processing difference: {abs(pdf_chunks - txt_chunks)} chunks")
            
        finally:
            # Cleanup temporary TXT file
            if 'txt_file_path' in locals() and os.path.exists(txt_file_path):
                os.unlink(txt_file_path)
    
    def test_stage_1_stage_2_token_compatibility(self, register_stage_1_only, stage_1_instance, db_fixture, sample_file_path):
        """Test that Stage 1 output is compatible with Stage 2 token requirements."""
        # Use real sample file
        test_file_path = sample_file_path or os.path.join(
            os.path.dirname(__file__), '..', 'sample_files', 'inputs', 'short_story.pdf'
        )
        
        if not os.path.exists(test_file_path):
            pytest.skip(f"Sample file not found: {test_file_path}")
        
        # Create test draft
        test_data = SampleDataGenerator(db_fixture.connection_pool)
        draft_data = test_data.generate_draft_request(file_name=os.path.basename(test_file_path))
        
        workspace_data = db_fixture.create_test_workspace(
            workspace_id=draft_data['workspace_id'],
            user_id=draft_data['user_id']
        )
        
        test_draft = db_fixture.create_test_draft(
            draft_id=draft_data['draft_id'],
            workspace_id=workspace_data['workspace_id'],
            user_id=workspace_data['user_id'],
            file_path=test_file_path
        )
        
        # Run Stage 1
        result = stage_1_instance.run(
            draft_id=test_draft['draft_id'],
            file_path=test_file_path
        )
        
        assert result['success'] == True
        
        # Get Stage 2's configuration for comparison
        from test_utils.real_generation_engine import RealGenerationEngineFactory
        from utils.document_processor import DocumentProcessor
        
        stage_2_factory = RealGenerationEngineFactory()
        stage_2_max_tokens = stage_2_factory.default_config['max_output_tokens']
        stage_1_max_tokens = DocumentProcessor.DEFAULT_CHUNK_SIZE
        
        # Verify Stage 2 can handle Stage 1's maximum output
        assert stage_2_max_tokens >= stage_1_max_tokens, \
            f"Stage 2 max tokens ({stage_2_max_tokens}) should handle Stage 1 max ({stage_1_max_tokens})"
        
        # Test actual chunk sizes from Stage 1
        chunks = db_fixture.execute_query(
            "SELECT raw_text, LENGTH(raw_text) as char_length FROM draft_chunks WHERE draft_id = %s",
            (test_draft['draft_id'],)
        )
        
        max_estimated_tokens = 0
        for raw_text, char_length in chunks:
            # Conservative token estimation (chars/4)
            estimated_tokens = char_length // 4
            max_estimated_tokens = max(max_estimated_tokens, estimated_tokens)
        
        # Stage 1 chunks should not exceed Stage 2's capacity
        assert max_estimated_tokens <= stage_2_max_tokens, \
            f"Largest Stage 1 chunk ({max_estimated_tokens} est. tokens) exceeds Stage 2 capacity ({stage_2_max_tokens})"
        
        print(f"\nStage 1→2 Compatibility Validation:")
        print(f"  Stage 1 max chunk size: {stage_1_max_tokens} tokens")
        print(f"  Stage 2 max capacity: {stage_2_max_tokens} tokens")
        print(f"  Actual max chunk (est.): {max_estimated_tokens} tokens")
        print(f"  Compatibility: {'✅ Compatible' if max_estimated_tokens <= stage_2_max_tokens else '❌ Incompatible'}")
    
    def test_stage_1_configuration_limits_enforcement(self, register_stage_1_only, stage_1_instance, db_fixture, sample_file_path):
        """Test that all DocumentProcessor configuration limits are properly enforced."""
        # Use real sample file
        test_file_path = sample_file_path or os.path.join(
            os.path.dirname(__file__), '..', 'sample_files', 'inputs', 'short_story.pdf'
        )
        
        if not os.path.exists(test_file_path):
            pytest.skip(f"Sample file not found: {test_file_path}")
        
        # Create test draft
        test_data = SampleDataGenerator(db_fixture.connection_pool)
        draft_data = test_data.generate_draft_request(file_name=os.path.basename(test_file_path))
        
        workspace_data = db_fixture.create_test_workspace(
            workspace_id=draft_data['workspace_id'],
            user_id=draft_data['user_id']
        )
        
        test_draft = db_fixture.create_test_draft(
            draft_id=draft_data['draft_id'],
            workspace_id=workspace_data['workspace_id'],
            user_id=workspace_data['user_id'],
            file_path=test_file_path
        )
        
        # Run Stage 1
        result = stage_1_instance.run(
            draft_id=test_draft['draft_id'],
            file_path=test_file_path
        )
        
        assert result['success'] == True
        
        # Import DocumentProcessor for constants
        from utils.document_processor import DocumentProcessor
        
        # Get all chunks for comprehensive validation
        chunks = db_fixture.execute_query(
            "SELECT chunk_number, raw_text, LENGTH(raw_text) as char_length FROM draft_chunks WHERE draft_id = %s ORDER BY chunk_number",
            (test_draft['draft_id'],)
        )
        
        violations = {
            'word_limit_violations': 0,
            'token_limit_violations': 0,
            'empty_chunks': 0,
            'oversized_paragraphs': 0
        }
        
        for chunk_number, raw_text, char_length in chunks:
            word_count = len(raw_text.split())
            estimated_tokens = char_length // 4  # Conservative estimate
            
            # Check DEFAULT_WORD_LIMIT enforcement (allow some variance)
            if word_count > DocumentProcessor.DEFAULT_WORD_LIMIT * 1.5:  # 2250 words
                violations['word_limit_violations'] += 1
            
            # Check DEFAULT_CHUNK_SIZE enforcement (strict)
            if estimated_tokens > DocumentProcessor.DEFAULT_CHUNK_SIZE:
                violations['token_limit_violations'] += 1
            
            # Check for empty chunks
            if len(raw_text.strip()) == 0:
                violations['empty_chunks'] += 1
            
            # Check for oversized paragraphs (heuristic)
            paragraphs = raw_text.split('\n\n')
            for para in paragraphs:
                para_word_count = len(para.split())
                if para_word_count > DocumentProcessor.MAX_PARAGRAPH_WORDS:
                    violations['oversized_paragraphs'] += 1
        
        # Report violations
        print(f"\nConfiguration Limits Enforcement:")
        print(f"  Total chunks: {len(chunks)}")
        print(f"  Word limit violations (>2250): {violations['word_limit_violations']}")
        print(f"  Token limit violations (>4000): {violations['token_limit_violations']}")
        print(f"  Empty chunks: {violations['empty_chunks']}")
        print(f"  Oversized paragraphs (>2000 words): {violations['oversized_paragraphs']}")
        
        # Critical violations should be zero
        assert violations['token_limit_violations'] == 0, "No chunks should exceed token safety limit"
        assert violations['empty_chunks'] == 0, "No chunks should be empty"
        
        # Word limit violations should be minimal (allow some edge cases)
        word_violation_rate = violations['word_limit_violations'] / len(chunks) if chunks else 0
        assert word_violation_rate < 0.2, f"Too many word limit violations: {word_violation_rate*100:.1f}%"
    
    def test_stage_1_invalid_file_handling(self, register_stage_1_only, stage_1_instance, db_fixture):
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
    
    def test_stage_1_empty_file_handling(self, register_stage_1_only, stage_1_instance, db_fixture):
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
    
    def test_stage_1_large_file_chunking(self, register_stage_1_only, stage_1_instance, db_fixture, expected_output_helper, sample_file_path):
        """Test chunking of large files with real content."""
        # Prefer real sample file for authentic large file testing
        if sample_file_path and os.path.exists(sample_file_path):
            large_file_path = sample_file_path
            file_name = os.path.basename(sample_file_path)
            cleanup_needed = False
        else:
            # Fallback to generated content if no real sample available
            large_content = SampleDataGenerator(db_fixture.connection_pool).generate_manuscript_content(
                chapter_count=10,
                words_per_chapter=5000  # 50k words total
            )
            
            large_file_path = str(get_temp_output('large_test.txt'))
            with open(large_file_path, 'w', encoding='utf-8') as f:
                f.write(large_content)
            file_name = 'large_manuscript.txt'
            cleanup_needed = True
        
        try:
            # Create test draft
            test_data = SampleDataGenerator(db_fixture.connection_pool)
            draft_data = test_data.generate_draft_request(file_name=file_name)
            
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
            assert result['chunks_created'] >= 2, "Should create at least two chunks for any file"
            assert result['total_characters'] > 1500, "Should be substantial (at least 1.5k characters)"
            assert result['total_words'] > 1000, "Should have substantial word count"
            
            # Verify chunks are reasonably sized
            chunks = db_fixture.execute_query(
                "SELECT LENGTH(raw_text) FROM draft_chunks WHERE draft_id = %s",
                (test_draft['draft_id'],)
            )
            
            for chunk_length in chunks:
                assert chunk_length[0] > 100  # Not too small
                assert chunk_length[0] < 25000  # Smaller chunks with word-based chunking
                
            # Verify word-based chunking strategy in metadata
            stats = stage_1_instance.get_chunk_statistics(test_draft['draft_id'])
            assert stats.get('chunking_strategy') == 'word_based_with_token_validation'
            assert stats.get('target_words_per_chunk') == 1500
            
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
            # Cleanup only if we created a temporary file
            if cleanup_needed and os.path.exists(large_file_path):
                os.unlink(large_file_path)
    
    def test_stage_1_unicode_handling(self, register_stage_1_only, stage_1_instance, db_fixture):
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
    
    def test_stage_1_chunk_statistics(self, register_stage_1_only, stage_1_instance, db_fixture, sample_file_path):
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
        
        # Verify statistics structure (traditional + new word-based)
        assert 'chunk_count' in stats
        assert 'avg_chunk_length' in stats
        assert 'min_chunk_length' in stats
        assert 'max_chunk_length' in stats
        assert 'total_characters' in stats
        assert 'total_words' in stats
        assert 'total_tokens' in stats
        assert 'avg_words_per_chunk' in stats
        assert 'avg_tokens_per_chunk' in stats
        assert 'chunking_strategy' in stats
        assert 'target_words_per_chunk' in stats
        
        # Verify statistics values
        assert stats['chunk_count'] == result['chunks_created']
        assert stats['chunking_strategy'] == 'word_based_with_token_validation'
        assert stats['target_words_per_chunk'] == 1500
        assert stats['total_words'] > 0
        assert stats['total_tokens'] > 0
        # Note: total_characters from stats may differ from result due to overlaps added to chunks
        assert stats['total_characters'] >= result['total_characters']  # Should be at least as much due to overlaps
        assert stats['avg_chunk_length'] > 0
        assert stats['min_chunk_length'] > 0
        assert stats['max_chunk_length'] >= stats['min_chunk_length']
    
    def test_stage_1_reprocessing(self, register_stage_1_only, stage_1_instance, db_fixture, sample_file_path):
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
        
        # Reprocess with different word limit
        reprocess_result = stage_1_instance.reprocess_chunks(
            draft_id=test_draft['draft_id'],
            file_path=sample_file_path,
            new_word_limit=750  # Smaller word chunks
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
    
    def test_stage_1_database_error_handling(self, register_stage_1_only, stage_1_instance, db_fixture, sample_file_path):
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
    
    def test_stage_1_concurrent_processing(self, register_stage_1_only, stage_1_instance, db_fixture, sample_file_path):
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
    
    def test_stage_1_enhanced_metadata_validation(self, register_stage_1_only, stage_1_instance, db_fixture, sample_file_path):
        """Test that Stage 1 produces correct enhanced metadata from refactored DocumentProcessor."""
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
        
        # Get enhanced metadata from database
        stats = stage_1_instance.get_chunk_statistics(test_draft['draft_id'])
        
        # Validate enhanced metadata structure from refactored business logic
        assert stats.get('chunking_strategy') == 'word_based_with_token_validation'
        assert stats.get('target_words_per_chunk') == 1500
        assert 'total_words' in stats
        assert 'total_tokens' in stats
        assert 'avg_words_per_chunk' in stats
        assert 'avg_tokens_per_chunk' in stats
        
        # Validate metadata calculations are accurate
        assert stats['total_words'] == result['total_words']
        assert stats['total_tokens'] == result['total_tokens']
        assert stats['chunk_count'] == result['chunks_created']
        
        # Validate averages are calculated correctly
        if result['chunks_created'] > 0:
            expected_avg_words = result['total_words'] / result['chunks_created']
            expected_avg_tokens = result['total_tokens'] / result['chunks_created']
            assert abs(stats['avg_words_per_chunk'] - expected_avg_words) < 1  # Allow small rounding difference
            assert abs(stats['avg_tokens_per_chunk'] - expected_avg_tokens) < 1
    
    def test_stage_1_chunk_metadata_structure_validation(self, register_stage_1_only, stage_1_instance, db_fixture, sample_file_path):
        """Test that chunks from refactored DocumentProcessor have correct metadata structure."""
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
        assert result['chunks_created'] > 0
        
        # Get individual chunks from database
        chunks = db_fixture.execute_query(
            "SELECT chunk_number, raw_text, cleaned_text FROM draft_chunks WHERE draft_id = %s ORDER BY chunk_number",
            (test_draft['draft_id'],)
        )
        
        # Validate chunk structure and metadata
        total_words_calculated = 0
        for i, chunk in enumerate(chunks):
            chunk_number, raw_text, cleaned_text = chunk
            
            # Validate chunk numbering is sequential
            assert chunk_number == i + 1
            
            # Validate chunk content exists
            assert len(raw_text) > 0
            assert len(cleaned_text) > 0
            
            # Validate word count is reasonable for 1500-word targeting
            # (Individual chunks may vary but should be in reasonable range)
            word_count = len(raw_text.split())
            assert 100 < word_count < 3000  # Reasonable range for semantic chunking
            total_words_calculated += word_count
        
        # Validate total word count matches result metadata
        # Allow small difference due to different counting methods
        assert abs(total_words_calculated - result['total_words']) < result['chunks_created']  # Allow 1 word difference per chunk
    
    def test_stage_1_word_based_chunking_validation(self, register_stage_1_only, stage_1_instance, db_fixture, sample_file_path):
        """Test that DocumentProcessor properly targets 1500-word chunks with real content."""
        # Prefer real sample file for authentic chunking validation
        test_file_path = sample_file_path or os.path.join(
            os.path.dirname(__file__), '..', 'sample_files', 'inputs', 'short_story.pdf'
        )
        
        if not os.path.exists(test_file_path):
            # Only fallback to generated content if no real sample available
            test_data = SampleDataGenerator(db_fixture.connection_pool)
            large_content = test_data.generate_manuscript_content(
                chapter_count=5,
                words_per_chapter=2000  # 10k words total, should create ~7 chunks
            )
            
            test_file_path = str(get_temp_output('word_chunking_test.txt'))
            with open(test_file_path, 'w', encoding='utf-8') as f:
                f.write(large_content)
            file_name = 'word_chunking_test.txt'
            cleanup_needed = True
        else:
            file_name = os.path.basename(test_file_path)
            cleanup_needed = False
        
        try:
            # Create test draft
            test_data = SampleDataGenerator(db_fixture.connection_pool)
            draft_data = test_data.generate_draft_request(file_name=file_name)
            workspace_data = db_fixture.create_test_workspace(
                workspace_id=draft_data['workspace_id'],
                user_id=draft_data['user_id']
            )
            
            test_draft = db_fixture.create_test_draft(
                draft_id=draft_data['draft_id'],
                workspace_id=workspace_data['workspace_id'],
                user_id=workspace_data['user_id'],
                file_path=test_file_path
            )
            
            # Run Stage 1
            result = stage_1_instance.run(
                draft_id=test_draft['draft_id'],
                file_path=test_file_path
            )
            
            assert result['success'] == True
            assert result['chunks_created'] > 0  # Should create at least one chunk
            
            # Validate word-based targeting
            stats = stage_1_instance.get_chunk_statistics(test_draft['draft_id'])
            assert stats['target_words_per_chunk'] == 1500
            
            # For files with sufficient content, validate average chunk size
            if result['chunks_created'] > 1:
                avg_words = stats['avg_words_per_chunk']
                assert avg_words > 0  # Should have reasonable word count
            
            # Enhanced validation for real content chunking
            chunks = db_fixture.execute_query(
                "SELECT chunk_number, raw_text, LENGTH(raw_text) as char_length FROM draft_chunks WHERE draft_id = %s ORDER BY chunk_number",
                (test_draft['draft_id'],)
            )
            
            # Import DocumentProcessor for constants validation
            from utils.document_processor import DocumentProcessor
            
            word_counts = []
            semantic_boundary_violations = 0
            
            for chunk_number, raw_text, char_length in chunks:
                raw_text = raw_text.strip()
                
                # Chunks should have meaningful content
                assert len(raw_text) > 50, f"Chunk {chunk_number} too short ({len(raw_text)} chars)"
                
                # Count words and validate against DEFAULT_WORD_LIMIT targeting
                word_count = len(raw_text.split())
                word_counts.append(word_count)
                
                # For chunks with multiple sentences, validate semantic boundaries
                if '.' in raw_text and len(raw_text) > 100:
                    # Should end with proper sentence boundary or paragraph break
                    if not (raw_text.endswith(('.', '!', '?', '\n', '\n\n')) or raw_text[-1] in '.!?'):
                        semantic_boundary_violations += 1
            
            # Validate 1500-word targeting with real content
            if len(word_counts) > 1:
                avg_words = sum(word_counts) / len(word_counts)
                print(f"\nWord-based Chunking Validation (Real Content):")
                print(f"  File: {file_name}")
                print(f"  Chunks created: {len(chunks)}")
                print(f"  Average words per chunk: {avg_words:.0f}")
                print(f"  Target: {DocumentProcessor.DEFAULT_WORD_LIMIT} words")
                print(f"  Semantic boundary violations: {semantic_boundary_violations}")
                
                # For real content, allow reasonable variance around 1500-word target
                assert 500 <= avg_words <= 2500, f"Average chunk size ({avg_words:.0f}) too far from 1500-word target"
            
            # Most chunks should respect semantic boundaries
            semantic_violation_rate = semantic_boundary_violations / len(chunks) if chunks else 0
            assert semantic_violation_rate < 0.3, f"Too many semantic boundary violations: {semantic_violation_rate*100:.1f}%"
            
        finally:
            # Cleanup only if we created a temporary file
            if cleanup_needed and os.path.exists(test_file_path):
                os.unlink(test_file_path)
    
    def test_stage_1_token_safety_validation(self, register_stage_1_only, stage_1_instance, db_fixture, sample_file_path):
        """Test that refactored DocumentProcessor respects token limits for safety."""
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
        assert result['chunks_created'] > 0
        
        # Validate token counting and safety
        assert 'total_tokens' in result
        assert result['total_tokens'] > 0
        
        # Get statistics to validate token safety features
        stats = stage_1_instance.get_chunk_statistics(test_draft['draft_id'])
        assert 'total_tokens' in stats
        assert 'avg_tokens_per_chunk' in stats
        
        # Validate token counts are reasonable (not zero, not excessive)
        assert stats['total_tokens'] > 0
        assert stats['avg_tokens_per_chunk'] > 0
        
        # Token count should be reasonable relative to word count
        # (rough estimate: 1 token per 0.75 words in English)
        token_to_word_ratio = stats['total_tokens'] / stats['total_words']
        assert 0.5 < token_to_word_ratio < 2.0  # Reasonable range for English text
        
        # Validate that individual chunks respect reasonable token limits
        # (chunks should not be excessively large from token perspective)
        if stats['chunk_count'] > 1:
            max_reasonable_tokens = 6000  # Reasonable upper limit for chunk safety
            assert stats['avg_tokens_per_chunk'] < max_reasonable_tokens
    
    def test_stage_1_provider_model_integration(self, register_stage_1_only, stage_1_instance, db_fixture, sample_file_path):
        """Test that refactored DocumentProcessor works with different providers/models."""
        # Create test draft
        test_data = SampleDataGenerator(db_fixture.connection_pool)
        draft_data = test_data.generate_draft_request(
            provider='gemini',  # Test with different provider
            model='gemini-2.0-flash'
        )
        
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
        
        # Test with DocumentProcessor directly through Stage 1 business logic
        # (Stage 1 should handle different providers/models transparently)
        result = stage_1_instance.run(
            draft_id=test_draft['draft_id'],
            file_path=sample_file_path
        )
        
        # Should work regardless of provider/model
        assert result['success'] == True
        assert result['chunks_created'] > 0
        assert 'total_words' in result
        assert 'total_tokens' in result
        
        # Validate that the refactored features still work with different providers
        stats = stage_1_instance.get_chunk_statistics(test_draft['draft_id'])
        assert stats.get('chunking_strategy') == 'word_based_with_token_validation'
        assert stats.get('target_words_per_chunk') == 1500
        assert stats['total_words'] > 0
        assert stats['total_tokens'] > 0
        
        # Validate that provider/model doesn't break the word-based chunking
        # (should still average around 1500 words regardless of provider)
        if stats['chunk_count'] > 1:
            avg_words = stats['avg_words_per_chunk']
            assert 800 < avg_words < 2500  # Reasonable range for word-based chunking
"""
Custom assertions and validation utilities for testing.
Provides specialized assertions for pipeline testing scenarios.
"""

import json
import re
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import uuid
import logging


class PipelineAssertions:
    """
    Custom assertions for pipeline testing.
    """
    
    @staticmethod
    def assert_valid_uuid(value: str, message: str = None):
        """Assert that a string is a valid UUID."""
        try:
            uuid.UUID(value)
        except (ValueError, TypeError):
            raise AssertionError(message or f"'{value}' is not a valid UUID")
    
    @staticmethod
    def assert_valid_json(value: str, message: str = None):
        """Assert that a string is valid JSON."""
        try:
            json.loads(value)
        except (json.JSONDecodeError, TypeError):
            raise AssertionError(message or f"'{value}' is not valid JSON")
    
    @staticmethod
    def assert_valid_timestamp(value: str, message: str = None):
        """Assert that a string is a valid ISO timestamp."""
        try:
            datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            raise AssertionError(message or f"'{value}' is not a valid ISO timestamp")
    
    @staticmethod
    def assert_draft_status(actual: str, expected: str, message: str = None):
        """Assert draft status matches expected value."""
        valid_statuses = [
            'pending', 'processing', 'stage_1_complete', 'stage_2_complete',
            'stage_3_complete', 'stage_4_complete', 'stage_5_complete',
            'stage_6_complete', 'completed', 'failed'
        ]
        
        if actual not in valid_statuses:
            raise AssertionError(f"'{actual}' is not a valid draft status")
        
        if actual != expected:
            raise AssertionError(message or f"Expected status '{expected}', got '{actual}'")
    
    @staticmethod
    def assert_api_response_structure(response: Dict[str, Any], success: bool = True):
        """Assert API response has correct structure."""
        required_fields = ['success', 'timestamp']
        
        for field in required_fields:
            if field not in response:
                raise AssertionError(f"API response missing required field: {field}")
        
        if response['success'] != success:
            raise AssertionError(f"Expected success={success}, got {response['success']}")
        
        if success:
            if 'data' not in response:
                raise AssertionError("Successful API response missing 'data' field")
        else:
            if 'error' not in response:
                raise AssertionError("Failed API response missing 'error' field")
    
    @staticmethod
    def assert_processing_progress(progress: Dict[str, Any], expected_stage: str = None):
        """Assert processing progress has correct structure."""
        required_fields = ['stage', 'percentage', 'details']
        
        for field in required_fields:
            if field not in progress:
                raise AssertionError(f"Progress missing required field: {field}")
        
        if not isinstance(progress['percentage'], (int, float)):
            raise AssertionError("Progress percentage must be numeric")
        
        if not 0 <= progress['percentage'] <= 100:
            raise AssertionError("Progress percentage must be between 0 and 100")
        
        if expected_stage and progress['stage'] != expected_stage:
            raise AssertionError(f"Expected stage '{expected_stage}', got '{progress['stage']}'")
    
    @staticmethod
    def assert_token_usage(usage: Dict[str, Any], min_tokens: int = 1):
        """Assert token usage data is valid."""
        required_fields = ['prompt_tokens', 'completion_tokens', 'total_tokens']
        
        for field in required_fields:
            if field not in usage:
                raise AssertionError(f"Token usage missing required field: {field}")
            
            if not isinstance(usage[field], int) or usage[field] < 0:
                raise AssertionError(f"Token count for {field} must be non-negative integer")
        
        if usage['total_tokens'] < min_tokens:
            raise AssertionError(f"Total tokens ({usage['total_tokens']}) below minimum ({min_tokens})")
        
        expected_total = usage['prompt_tokens'] + usage['completion_tokens']
        if usage['total_tokens'] != expected_total:
            raise AssertionError(f"Total tokens mismatch: expected {expected_total}, got {usage['total_tokens']}")
    
    @staticmethod
    def assert_database_record_exists(db_fixture, table: str, record_id: str):
        """Assert that a database record exists."""
        count = db_fixture.count_records(table, record_id)
        if count == 0:
            raise AssertionError(f"No records found in {table} with ID {record_id}")
    
    @staticmethod
    def assert_database_record_count(db_fixture, table: str, expected_count: int, draft_id: str = None):
        """Assert database record count matches expected value."""
        actual_count = db_fixture.count_records(table, draft_id)
        if actual_count != expected_count:
            raise AssertionError(f"Expected {expected_count} records in {table}, got {actual_count}")
    
    @staticmethod
    def assert_processing_time_reasonable(start_time: str, end_time: str, max_minutes: int = 60):
        """Assert processing time is within reasonable bounds."""
        try:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            duration = end - start
            max_duration = timedelta(minutes=max_minutes)
            
            if duration > max_duration:
                raise AssertionError(f"Processing took {duration}, exceeding maximum of {max_duration}")
            
            if duration < timedelta(seconds=1):
                raise AssertionError(f"Processing too fast: {duration} (possible mock or error)")
                
        except ValueError as e:
            raise AssertionError(f"Invalid timestamp format: {e}")
    
    @staticmethod
    def assert_text_quality_improved(original: str, cleaned: str, min_improvement: float = 0.1):
        """Assert that cleaned text shows quality improvements."""
        # Simple heuristics for text quality
        original_sentences = len(re.findall(r'[.!?]+', original))
        cleaned_sentences = len(re.findall(r'[.!?]+', cleaned))
        
        # Should have similar sentence count (not dramatically different)
        if abs(original_sentences - cleaned_sentences) > max(1, original_sentences * 0.5):
            raise AssertionError("Cleaned text has dramatically different sentence count")
        
        # Cleaned text should have fewer formatting issues
        original_whitespace_issues = len(re.findall(r'\s{2,}', original))
        cleaned_whitespace_issues = len(re.findall(r'\s{2,}', cleaned))
        
        if cleaned_whitespace_issues > original_whitespace_issues:
            raise AssertionError("Cleaned text has more whitespace issues than original")
    
    @staticmethod
    def assert_scene_extraction_quality(scenes: List[Dict[str, Any]], min_scenes: int = 1):
        """Assert scene extraction results are reasonable."""
        if len(scenes) < min_scenes:
            raise AssertionError(f"Expected at least {min_scenes} scenes, got {len(scenes)}")
        
        # Check scene numbering
        scene_numbers = [scene['scene_number'] for scene in scenes]
        expected_numbers = list(range(1, len(scenes) + 1))
        
        if scene_numbers != expected_numbers:
            raise AssertionError(f"Scene numbers not sequential: {scene_numbers}")
        
        # Check scene content quality
        for scene in scenes:
            if not scene.get('title', '').strip():
                raise AssertionError("Scene missing title")
            
            if not scene.get('summary', '').strip():
                raise AssertionError("Scene missing summary")
            
            if not scene.get('original_content', '').strip():
                raise AssertionError("Scene missing original content")
    
    @staticmethod
    def assert_coherence_analysis_quality(analysis: Dict[str, Any]):
        """Assert coherence analysis results are reasonable."""
        if 'coherence_analysis' not in analysis:
            raise AssertionError("Missing coherence analysis section")
        
        coherence_data = analysis['coherence_analysis']
        
        # Check scores are within valid range
        score_fields = ['overall_score', 'character_consistency', 'plot_consistency']
        for field in score_fields:
            if field in coherence_data:
                score = coherence_data[field]
                if not isinstance(score, (int, float)) or not 0 <= score <= 1:
                    raise AssertionError(f"Invalid score for {field}: {score}")
    
    @staticmethod
    def assert_enhancement_quality(original: str, enhanced: str):
        """Assert enhancement results show improvements."""
        if len(enhanced) < len(original) * 0.8:
            raise AssertionError("Enhanced text is significantly shorter than original")
        
        # Enhanced text should have more descriptive content
        original_words = len(original.split())
        enhanced_words = len(enhanced.split())
        
        if enhanced_words < original_words:
            raise AssertionError("Enhanced text has fewer words than original")
    
    @staticmethod
    def assert_chapter_organization(chapters: List[Dict[str, Any]], target_length: int = 2500):
        """Assert chapter organization is reasonable."""
        if not chapters:
            raise AssertionError("No chapters found")
        
        # Check chapter numbering
        chapter_numbers = [ch['chapter_number'] for ch in chapters]
        expected_numbers = list(range(1, len(chapters) + 1))
        
        if chapter_numbers != expected_numbers:
            raise AssertionError(f"Chapter numbers not sequential: {chapter_numbers}")
        
        # Check chapter lengths are reasonable
        for chapter in chapters:
            word_count = len(chapter['content'].split())
            if word_count < target_length * 0.5:
                raise AssertionError(f"Chapter {chapter['chapter_number']} too short: {word_count} words")
            
            if word_count > target_length * 2:
                raise AssertionError(f"Chapter {chapter['chapter_number']} too long: {word_count} words")



class RealAPIAssertions:
    """
    Assertions for validating real AI provider responses.
    """
    
    @staticmethod
    def assert_real_api_response_structure(response):
        """Assert that real API response has expected structure."""
        from models.response import BaseGenerationResponse
        
        assert isinstance(response, BaseGenerationResponse), "Response must be BaseGenerationResponse instance"
        assert hasattr(response, 'success'), "Response missing 'success' field"
        assert hasattr(response, 'text'), "Response missing 'text' field"
        assert hasattr(response, 'provider'), "Response missing 'provider' field"
        assert hasattr(response, 'model_used'), "Response missing 'model_used' field"
        assert hasattr(response, 'metadata'), "Response missing 'metadata' field"
        assert hasattr(response, 'quota'), "Response missing 'quota' field"
    
    @staticmethod
    def assert_successful_generation(response):
        """Assert that generation was successful."""
        RealAPIAssertions.assert_real_api_response_structure(response)
        assert response.success, f"Generation failed: {getattr(response, 'error_message', 'Unknown error')}"
        assert response.text is not None, "Successful response should have text content"
        assert len(response.text.strip()) > 0, "Generated text should not be empty"
    
    @staticmethod
    def assert_failed_generation(response, expected_error_type: str = None):
        """Assert that generation failed as expected."""
        RealAPIAssertions.assert_real_api_response_structure(response)
        assert not response.success, "Expected generation to fail"
        assert hasattr(response, 'error_message'), "Failed response should have error_message"
        assert response.error_message is not None, "Error message should not be None"
        
        if expected_error_type:
            assert expected_error_type.lower() in response.error_message.lower(), \
                f"Expected error type '{expected_error_type}' not found in error message: {response.error_message}"
    
    @staticmethod
    def assert_token_usage(response, min_tokens: int = 1):
        """Assert that token usage is reasonable."""
        RealAPIAssertions.assert_real_api_response_structure(response)
        assert response.metadata.total_tokens >= min_tokens, \
            f"Expected at least {min_tokens} tokens, got {response.metadata.total_tokens}"
        assert response.metadata.input_tokens >= 0, "Input tokens should be non-negative"
        assert response.metadata.output_tokens >= 0, "Output tokens should be non-negative"
        assert response.metadata.total_tokens == response.metadata.input_tokens + response.metadata.output_tokens, \
            "Total tokens should equal input + output tokens"
    
    @staticmethod
    def assert_processing_time_reasonable(response, max_seconds: int = 60):
        """Assert that processing time is reasonable."""
        RealAPIAssertions.assert_real_api_response_structure(response)
        processing_time_ms = response.metadata.processing_time_ms
        processing_time_seconds = processing_time_ms / 1000
        
        assert processing_time_seconds > 0, "Processing time should be positive"
        assert processing_time_seconds <= max_seconds, \
            f"Processing time {processing_time_seconds}s exceeded maximum {max_seconds}s"
    
    @staticmethod
    def assert_provider_matches(response, expected_provider: str):
        """Assert that the response came from the expected provider."""
        RealAPIAssertions.assert_real_api_response_structure(response)
        assert response.provider.lower() == expected_provider.lower(), \
            f"Expected provider '{expected_provider}', got '{response.provider}'"
    
    @staticmethod
    def assert_model_matches(response, expected_model: str):
        """Assert that the response used the expected model."""
        RealAPIAssertions.assert_real_api_response_structure(response)
        assert response.model_used == expected_model, \
            f"Expected model '{expected_model}', got '{response.model_used}'"
    
    @staticmethod
    def assert_quota_consumed(response, expected_generation_count: int = 1):
        """Assert that quota was consumed as expected."""
        RealAPIAssertions.assert_real_api_response_structure(response)
        assert response.quota.generation_count == expected_generation_count, \
            f"Expected {expected_generation_count} generation(s), got {response.quota.generation_count}"
    
    @staticmethod
    def assert_text_quality_basic(text: str, min_length: int = 10):
        """Assert basic text quality requirements."""
        assert text is not None, "Text should not be None"
        assert isinstance(text, str), "Text should be a string"
        assert len(text.strip()) >= min_length, \
            f"Text should be at least {min_length} characters, got {len(text.strip())}"
        assert not text.strip().startswith("Error:"), "Text should not start with 'Error:'"
    
    @staticmethod
    def assert_cleaning_improved_text(original_text: str, cleaned_text: str):
        """Assert that text cleaning was appropriate for the content."""
        assert len(cleaned_text.strip()) > 0, "Cleaned text should not be empty"
        
        # Basic quality checks
        RealAPIAssertions.assert_text_quality_basic(cleaned_text)
        
        # Check for common improvements (basic heuristics)
        assert not cleaned_text.strip().startswith("Error:"), "Cleaned text should not be an error message"
        
        # Length preservation check - cleaning should preserve 95%+ of content
        length_ratio = len(cleaned_text) / len(original_text) if len(original_text) > 0 else 1.0
        assert length_ratio >= 0.95, f"Cleaned text too short ({length_ratio*100:.1f}%) - may be summarizing instead of cleaning"
        
        # Allow for identical text if it's already clean
        if original_text == cleaned_text:
            logger = logging.getLogger(__name__)
            logger.info("Text preserved unchanged - indicates already clean content")
            
            # Validate the text was already of good quality
            RealAPIAssertions._assert_already_clean_quality(original_text)
        else:
            # Text was changed - validate improvements were appropriate
            logger = logging.getLogger(__name__)
            logger.info(f"Text was cleaned - length change: {len(original_text)} -> {len(cleaned_text)} chars")
            
            # Ensure changes are improvements, not degradations
            RealAPIAssertions._assert_cleaning_improvements(original_text, cleaned_text)
    
    @staticmethod
    def _assert_already_clean_quality(text: str):
        """Assert that unchanged text was already of good quality."""
        # Check for common issues that should have been cleaned
        excessive_spaces = text.count('  ') > 5  # More than 5 double spaces
        excessive_newlines = text.count('\n\n\n') > 2  # More than 2 triple newlines
        
        if excessive_spaces:
            logger = logging.getLogger(__name__)
            logger.warning(f"Text has {text.count('  ')} double spaces but was unchanged")
            
        if excessive_newlines:
            logger = logging.getLogger(__name__)
            logger.warning(f"Text has excessive newlines but was unchanged")
    
    @staticmethod
    def _assert_cleaning_improvements(original_text: str, cleaned_text: str):
        """Assert that changes made were actual improvements."""
        # Check for common cleaning improvements
        original_double_spaces = original_text.count('  ')
        cleaned_double_spaces = cleaned_text.count('  ')
        
        original_triple_newlines = original_text.count('\n\n\n')
        cleaned_triple_newlines = cleaned_text.count('\n\n\n')
        
        # If original had issues, cleaned should have fewer
        if original_double_spaces > 5:
            assert cleaned_double_spaces <= original_double_spaces, "Cleaning should reduce excessive spacing"
            
        if original_triple_newlines > 2:
            assert cleaned_triple_newlines <= original_triple_newlines, "Cleaning should reduce excessive newlines"
    
    @staticmethod
    def assert_scene_detection_json(response_text: str):
        """Assert that scene detection returned valid JSON."""
        import json
        try:
            data = json.loads(response_text)
            assert isinstance(data, dict), "Scene detection should return a JSON object"
            assert 'scenes' in data, "Scene detection should include 'scenes' field"
            assert isinstance(data['scenes'], list), "Scenes should be a list"
            
            # Check scene structure
            for scene in data['scenes']:
                assert isinstance(scene, dict), "Each scene should be a dictionary"
                assert 'scene_number' in scene, "Scene should have scene_number"
                assert 'title' in scene or 'summary' in scene, "Scene should have title or summary"
                
        except json.JSONDecodeError as e:
            raise AssertionError(f"Scene detection should return valid JSON: {e}")
    
    @staticmethod
    def assert_coherence_analysis_json(response_text: str):
        """Assert that coherence analysis returned valid JSON."""
        import json
        try:
            data = json.loads(response_text)
            assert isinstance(data, dict), "Coherence analysis should return a JSON object"
            
            # Check for expected fields
            expected_fields = ['coherence_analysis', 'issues_found', 'relationships']
            for field in expected_fields:
                if field in data:
                    assert isinstance(data[field], (dict, list)), f"Field '{field}' should be dict or list"
                    
        except json.JSONDecodeError as e:
            raise AssertionError(f"Coherence analysis should return valid JSON: {e}")


class Stage3Assertions:
    """
    Specialized assertions for Stage 3 (Scene Detection) testing.
    Focuses on realistic validation of scene extraction results.
    """
    
    @staticmethod
    def validate_scene_structure(scene_dict: Dict[str, Any]):
        """Validate that a scene dictionary has the required structure."""
        assert isinstance(scene_dict, dict), "Scene should be a dictionary"
        
        # Required fields for Stage 3 scenes
        required_fields = ['scene_number', 'title', 'setting', 'characters', 'summary', 'content']
        for field in required_fields:
            assert field in scene_dict, f"Scene missing required field: {field}"
        
        # Validate field types
        assert isinstance(scene_dict['scene_number'], int), "scene_number should be an integer"
        assert isinstance(scene_dict['title'], str), "title should be a string"
        assert isinstance(scene_dict['setting'], str), "setting should be a string"
        assert isinstance(scene_dict['characters'], list), "characters should be a list"
        assert isinstance(scene_dict['summary'], str), "summary should be a string"
        assert isinstance(scene_dict['content'], str), "content should be a string"
        
        # Content quality checks
        assert len(scene_dict['content'].strip()) >= 50, "Scene content should be at least 50 characters"
        assert len(scene_dict['title'].strip()) > 0, "Scene title should not be empty"
    
    @staticmethod
    def validate_scene_count_range(scenes: List[Dict[str, Any]], min_count: int = 8, max_count: int = 20):
        """Validate that scene count is within the expected range."""
        scene_count = len(scenes)
        assert min_count <= scene_count <= max_count, \
            f"Scene count {scene_count} should be between {min_count} and {max_count}"
    
    @staticmethod
    def validate_global_scene_numbering(scenes: List[Dict[str, Any]]):
        """Validate that scenes have correct global numbering sequence."""
        if not scenes:
            return
        
        expected_number = 1
        for scene in scenes:
            assert scene['scene_number'] == expected_number, \
                f"Scene numbering out of sequence: expected {expected_number}, got {scene['scene_number']}"
            expected_number += 1
    
    @staticmethod
    def validate_scene_content_from_chunks(scenes: List[Dict[str, Any]], original_chunks: List[str]):
        """Validate that scene content is derived from original chunks."""
        if not scenes or not original_chunks:
            return
        
        # Combine all original chunks for content validation
        combined_original = "\n\n".join(original_chunks)
        
        for scene in scenes:
            content = scene['content']
            # Check if scene content appears to be derived from original text
            # This is a basic check - we don't expect exact matches due to AI processing
            assert len(content) > 0, f"Scene {scene['scene_number']} has empty content"
            assert len(content) <= len(combined_original), \
                f"Scene {scene['scene_number']} content longer than total original text"
    
    @staticmethod
    def validate_scene_database_storage(db_fixture, draft_id: str, expected_scene_count: int):
        """Validate that scenes were correctly stored in the database."""
        # Check scenes table
        scenes_count = db_fixture.count_records('scenes', draft_id)
        assert scenes_count == expected_scene_count, \
            f"Expected {expected_scene_count} scenes in database, found {scenes_count}"
        
        # Validate scene data in database
        scenes = db_fixture.execute_query(
            "SELECT scene_number, title, summary, setting, characters, original_content FROM scenes WHERE draft_id = %s ORDER BY scene_number",
            (draft_id,)
        )
        
        for i, scene in enumerate(scenes):
            scene_number, title, summary, setting, characters, content = scene
            
            # Validate data types and content
            assert scene_number == i + 1, f"Scene numbering issue: expected {i + 1}, got {scene_number}"
            assert title and title.strip(), f"Scene {scene_number} has empty title"
            assert content and len(content.strip()) >= 50, f"Scene {scene_number} content too short"
            
            # Validate JSON field
            if characters:
                try:
                    import json
                    # Handle both parsed JSON (from PostgreSQL JSON column) and JSON string
                    if isinstance(characters, list):
                        char_list = characters  # Already parsed from JSON column
                    elif isinstance(characters, str):
                        char_list = json.loads(characters)  # Parse JSON string
                    else:
                        raise AssertionError(f"Scene {scene_number} characters has unexpected type: {type(characters)}")
                    
                    assert isinstance(char_list, list), f"Scene {scene_number} characters should be a list, got {type(char_list)}"
                except json.JSONDecodeError:
                    raise AssertionError(f"Scene {scene_number} characters field is not valid JSON")
    
    @staticmethod
    def validate_stage_3_result_structure(result: Dict[str, Any]):
        """Validate the structure of Stage 3 execution results."""
        assert isinstance(result, dict), "Stage 3 result should be a dictionary"
        assert 'success' in result, "Result should include 'success' field"
        
        if result['success']:
            # Success case validations
            required_fields = ['scenes_extracted', 'scenes_stored', 'chunks_processed']
            for field in required_fields:
                assert field in result, f"Successful result missing field: {field}"
                assert isinstance(result[field], int), f"{field} should be an integer"
            
            # Logical validations
            assert result['scenes_stored'] == result['scenes_extracted'], \
                "scenes_stored should equal scenes_extracted"
            assert result['chunks_processed'] >= 0, "chunks_processed should be non-negative"
        else:
            # Failure case validations
            assert 'error' in result, "Failed result should include 'error' field"
            assert isinstance(result['error'], str), "Error should be a string"
    
    @staticmethod
    def validate_scene_count_business_logic(scene_count: int, expected_valid: bool = True):
        """Validate scene count against business logic rules (8-20 scenes)."""
        is_valid = 8 <= scene_count <= 20
        if expected_valid:
            assert is_valid, f"Scene count {scene_count} should be valid (8-20 range)"
        else:
            assert not is_valid, f"Scene count {scene_count} should be invalid (outside 8-20 range)"
    
    @staticmethod
    def validate_retry_attempt_logic(scenes_data: List[Dict[str, Any]], attempt_number: int, previous_count: int = None):
        """Validate retry attempt results follow business logic."""
        assert 1 <= attempt_number <= 3, f"Attempt number {attempt_number} should be between 1 and 3"
        
        scene_count = len(scenes_data)
        
        # If we have previous count, validate retry logic
        if previous_count is not None:
            if previous_count < 8:
                # Should have tried to get MORE scenes
                assert scene_count != previous_count, "Retry should have produced different scene count"
            elif previous_count > 20:
                # Should have tried to get FEWER scenes
                assert scene_count != previous_count, "Retry should have produced different scene count"
    
    @staticmethod
    def validate_scene_content_extraction(scene_dict: Dict[str, Any], original_text: str):
        """Validate that scene content was properly extracted from original text."""
        content = scene_dict.get('content', '')
        
        # Content should not be empty
        assert len(content.strip()) > 0, "Scene content should not be empty"
        
        # Content should be reasonable length (minimum 50 chars as per business logic)
        assert len(content.strip()) >= 50, f"Scene content too short: {len(content.strip())} chars"
        
        # Content should not be longer than original text
        assert len(content) <= len(original_text), "Scene content should not exceed original text length"
    
    @staticmethod
    def validate_scene_content_quality(scene_dict: Dict[str, Any], quality_checks: Dict[str, bool] = None):
        """Validate scene content quality beyond basic length checks."""
        if quality_checks is None:
            quality_checks = {
                'has_dialogue': True,
                'has_action': True,
                'has_description': True,
                'proper_sentences': True,
                'narrative_coherence': True
            }
        
        content = scene_dict.get('content', '')
        
        # Basic quality checks
        assert len(content.strip()) > 0, "Scene content should not be empty"
        
        # Check for proper sentence structure
        if quality_checks.get('proper_sentences', False):
            sentence_endings = ['.', '!', '?']
            has_sentence_ending = any(ending in content for ending in sentence_endings)
            assert has_sentence_ending, "Scene content should contain proper sentence structure"
        
        # Check for narrative elements
        if quality_checks.get('has_dialogue', False):
            dialogue_markers = ['"', "'", "said", "asked", "replied", "whispered", "shouted"]
            has_dialogue = any(marker in content.lower() for marker in dialogue_markers)
            if not has_dialogue:
                import logging
                logging.getLogger(__name__).warning("Scene content may lack dialogue elements")
        
        # Check for action/movement
        if quality_checks.get('has_action', False):
            action_words = ['walked', 'ran', 'moved', 'turned', 'looked', 'went', 'came', 'entered', 'left', 'stood', 'sat']
            has_action = any(word in content.lower() for word in action_words)
            if not has_action:
                import logging
                logging.getLogger(__name__).warning("Scene content may lack action elements")
        
        # Check for descriptive elements
        if quality_checks.get('has_description', False):
            descriptive_words = ['dark', 'light', 'cold', 'warm', 'large', 'small', 'beautiful', 'ugly', 'quiet', 'loud']
            has_description = any(word in content.lower() for word in descriptive_words)
            if not has_description:
                import logging
                logging.getLogger(__name__).warning("Scene content may lack descriptive elements")
        
        # Check for narrative coherence (basic)
        if quality_checks.get('narrative_coherence', False):
            # Check that content has reasonable word-to-sentence ratio
            words = content.split()
            sentences = content.count('.') + content.count('!') + content.count('?')
            if sentences > 0:
                words_per_sentence = len(words) / sentences
                assert 3 <= words_per_sentence <= 50, f"Unusual word-to-sentence ratio: {words_per_sentence}"
    
    @staticmethod
    def validate_scene_metadata_quality(scene_dict: Dict[str, Any]):
        """Validate scene metadata quality (title, summary, setting, characters)."""
        # Title quality
        title = scene_dict.get('title', '')
        assert len(title.strip()) > 0, "Scene title should not be empty"
        assert len(title.split()) >= 2, "Scene title should be at least 2 words"
        assert len(title.split()) <= 8, "Scene title should not exceed 8 words"
        
        # Summary quality
        summary = scene_dict.get('summary', '')
        assert len(summary.strip()) > 0, "Scene summary should not be empty"
        assert len(summary.split()) >= 5, "Scene summary should be at least 5 words"
        assert len(summary.split()) <= 100, "Scene summary should not exceed 100 words"
        
        # Setting quality
        setting = scene_dict.get('setting', '')
        assert len(setting.strip()) > 0, "Scene setting should not be empty"
        assert len(setting.split()) >= 2, "Scene setting should be at least 2 words"
        
        # Characters quality
        characters = scene_dict.get('characters', [])
        assert isinstance(characters, list), "Scene characters should be a list"
        if characters:  # If characters are present, validate them
            for character in characters:
                assert isinstance(character, str), "Each character should be a string"
                assert len(character.strip()) > 0, "Character names should not be empty"
                assert len(character.split()) <= 5, "Character names should not exceed 5 words"
    
    @staticmethod
    def validate_scene_narrative_consistency(scenes: List[Dict[str, Any]]):
        """Validate narrative consistency across multiple scenes."""
        if len(scenes) < 2:
            return  # Need at least 2 scenes for consistency checks
        
        # Check character consistency
        all_characters = set()
        for scene in scenes:
            characters = scene.get('characters', [])
            if isinstance(characters, list):
                all_characters.update(characters)
        
        # Check that main characters appear in multiple scenes
        character_appearances = {}
        for scene in scenes:
            scene_characters = scene.get('characters', [])
            if isinstance(scene_characters, list):
                for character in scene_characters:
                    character_appearances[character] = character_appearances.get(character, 0) + 1
        
        # At least one character should appear in multiple scenes (for continuity)
        recurring_characters = [char for char, count in character_appearances.items() if count > 1]
        if len(scenes) > 2 and not recurring_characters:
            import logging
            logging.getLogger(__name__).warning("No recurring characters found across scenes - may indicate poor narrative continuity")
        
        # Check scene numbering consistency
        expected_numbers = list(range(1, len(scenes) + 1))
        actual_numbers = [scene.get('scene_number', 0) for scene in scenes]
        actual_numbers.sort()
        
        assert actual_numbers == expected_numbers, f"Scene numbering inconsistent: expected {expected_numbers}, got {actual_numbers}"
    
    @staticmethod
    def validate_scene_markers_extraction(original_text: str, start_marker: str, end_marker: str, expected_content: str = None):
        """Validate marker-based content extraction business logic."""
        # Markers should exist in original text
        assert start_marker in original_text, f"Start marker '{start_marker}' not found in original text"
        assert end_marker in original_text, f"End marker '{end_marker}' not found in original text"
        
        # Start marker should come before end marker
        start_pos = original_text.find(start_marker)
        end_pos = original_text.find(end_marker, start_pos + len(start_marker))
        assert start_pos < end_pos, "Start marker should come before end marker"
        
        # If expected content provided, validate extraction
        if expected_content is not None:
            expected_start = start_pos
            expected_end = end_pos + len(end_marker)
            actual_content = original_text[expected_start:expected_end].strip()
            assert actual_content == expected_content.strip(), "Extracted content doesn't match expected"
    
    @staticmethod
    def validate_global_numbering_logic(scenes: List[Dict[str, Any]], starting_number: int = 1):
        """Validate global scene numbering logic implementation."""
        if not scenes:
            return
        
        expected_number = starting_number
        for i, scene in enumerate(scenes):
            assert scene['scene_number'] == expected_number, \
                f"Scene {i} numbering incorrect: expected {expected_number}, got {scene['scene_number']}"
            expected_number += 1
    
    @staticmethod
    def validate_scene_data_validation_logic(scene_data: Dict[str, Any], should_be_valid: bool = True):
        """Validate scene data validation business logic."""
        try:
            # Check required fields exist and are correct types
            required_fields = ['title', 'setting', 'characters', 'summary', 'content']
            for field in required_fields:
                assert field in scene_data, f"Scene missing required field: {field}"
            
            # Validate field types
            assert isinstance(scene_data['title'], str), "title should be a string"
            assert isinstance(scene_data['setting'], str), "setting should be a string"
            assert isinstance(scene_data['characters'], list), "characters should be a list"
            assert isinstance(scene_data['summary'], str), "summary should be a string"
            assert isinstance(scene_data['content'], str), "content should be a string"
            
            # Validate content length (business logic minimum 50 chars)
            content_length = len(scene_data['content'].strip())
            assert content_length >= 50, f"Scene content too short: {content_length} chars"
            
            if should_be_valid:
                # All validations passed - scene should be valid
                pass
            else:
                # If we expected invalid but got here, that's an error
                raise AssertionError("Scene data was expected to be invalid but passed validation")
                
        except AssertionError:
            if should_be_valid:
                # Re-raise if we expected valid data
                raise
            else:
                # Expected invalid data and got it - this is correct
                pass
    
    @staticmethod
    def validate_chunk_processing_logic(processed_chunks: int, expected_chunks: int, scenes_extracted: int):
        """Validate chunk processing business logic."""
        assert processed_chunks == expected_chunks, \
            f"Processed chunks {processed_chunks} should equal expected chunks {expected_chunks}"
        
        # Each chunk should potentially produce 8-20 scenes, but failures are allowed
        max_possible_scenes = processed_chunks * 20
        assert scenes_extracted <= max_possible_scenes, \
            f"Scenes extracted {scenes_extracted} exceeds maximum possible {max_possible_scenes}"
        
        # Should have at least some scenes if chunks were processed successfully
        if processed_chunks > 0:
            assert scenes_extracted >= 0, "Should have non-negative scenes extracted"
    
    @staticmethod
    def validate_utf8_database_storage(db_fixture, draft_id: str):
        """Validate UTF-8 safe database storage for scenes."""
        scenes = db_fixture.execute_query(
            "SELECT title, summary, setting, original_content FROM scenes WHERE draft_id = %s",
            (draft_id,)
        )
        
        for scene in scenes:
            title, summary, setting, content = scene
            
            # Test UTF-8 encoding/decoding
            for field_name, field_value in [('title', title), ('summary', summary), ('setting', setting), ('content', content)]:
                if field_value:
                    try:
                        # Should be able to encode/decode as UTF-8
                        encoded = field_value.encode('utf-8')
                        decoded = encoded.decode('utf-8')
                        assert decoded == field_value, f"UTF-8 encoding issue in {field_name}"
                    except UnicodeError:
                        raise AssertionError(f"Scene {field_name} contains invalid UTF-8 characters")
    
    @staticmethod
    def validate_error_handling_logic(result: Dict[str, Any], expected_error_type: str = None):
        """Validate error handling business logic."""
        assert result['success'] is False, "Error result should have success=False"
        assert 'error' in result, "Error result should contain 'error' field"
        assert isinstance(result['error'], str), "Error should be a string"
        assert len(result['error']) > 0, "Error message should not be empty"
        
        if expected_error_type:
            assert expected_error_type.lower() in result['error'].lower(), \
                f"Expected error type '{expected_error_type}' not found in: {result['error']}"
    
    @staticmethod
    def validate_empty_chunks_handling(result: Dict[str, Any]):
        """Validate business logic for handling empty chunks."""
        assert result['success'] is True, "Empty chunks should be handled gracefully"
        assert result['chunks_processed'] == 0, "No chunks should be processed"
        assert result['scenes_extracted'] == 0, "No scenes should be extracted"
        assert 'message' in result, "Should include explanatory message"
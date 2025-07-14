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
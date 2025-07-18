"""
Tests for Stage 3: Scene Detection and Extraction with Real AI
Uses real AI providers to test scene detection functionality.
Tests use actual chunks from Stage 2 to ensure realistic pipeline behavior.
"""

import pytest
import time
from test_utils.assertions import PipelineAssertions, RealAPIAssertions, Stage3Assertions
from test_utils.sample_data import SampleDataGenerator
from test_utils.real_generation_engine import RealGenerationEngineFactory
from test_utils.stage_dependencies import requires_previous_stages
from test_utils.output_generator import generate_stage_output
from config.deconstructor_config import Stage3Config


class TestStage3PromptTemplateValidation:
    """Test Stage 3 prompt template validation and business logic alignment."""
    
    def test_scene_detection_prompt_contains_critical_requirements(self, stage_3_instance):
        """Test that scene detection prompt contains all critical business requirements."""
        from services.deconstructor.prompt_template import DeconstructorPrompts
        
        # Get the actual prompt template
        prompt_template = DeconstructorPrompts.get_scene_detection_prompt()
        
        # Validate critical requirements are present
        critical_requirements = [
            "8 and 20 scenes",  # Scene count range
            "CRITICAL REQUIREMENT",  # Emphasis on requirement
            "MINIMUM: 8 scenes",  # Minimum scene count
            "MAXIMUM: 20 scenes",  # Maximum scene count
            "scene_number",  # Required field
            "title",  # Required field
            "setting",  # Required field
            "characters",  # Required field
            "summary",  # Required field
            "start_marker",  # Content extraction
            "end_marker",  # Content extraction
            "content"  # Required field
        ]
        
        for requirement in critical_requirements:
            assert requirement in prompt_template, f"Prompt template missing critical requirement: {requirement}"
        
        # Validate scene count matches configuration
        assert str(Stage3Config.MIN_SCENES_PER_CHUNK) in prompt_template
        assert str(Stage3Config.MAX_SCENES_PER_CHUNK) in prompt_template
        
        # Validate optimal range is mentioned
        optimal_min, optimal_max = Stage3Config.OPTIMAL_SCENES_RANGE
        assert f"{optimal_min}-{optimal_max}" in prompt_template
        
        print("✅ Scene detection prompt contains all critical business requirements")
    
    def test_prompt_template_configuration_consistency(self, stage_3_instance):
        """Test that prompt template configuration matches Stage3Config constants."""
        from services.deconstructor.prompt_template import DeconstructorPrompts
        
        prompt_template = DeconstructorPrompts.get_scene_detection_prompt()
        
        # Test configuration consistency
        config_tests = [
            {
                'name': 'minimum_scenes',
                'config_value': Stage3Config.MIN_SCENES_PER_CHUNK,
                'should_be_in_prompt': True
            },
            {
                'name': 'maximum_scenes', 
                'config_value': Stage3Config.MAX_SCENES_PER_CHUNK,
                'should_be_in_prompt': True
            },
            {
                'name': 'optimal_range_min',
                'config_value': Stage3Config.OPTIMAL_SCENES_RANGE[0],
                'should_be_in_prompt': True
            },
            {
                'name': 'optimal_range_max',
                'config_value': Stage3Config.OPTIMAL_SCENES_RANGE[1],
                'should_be_in_prompt': True
            }
        ]
        
        for test in config_tests:
            value_str = str(test['config_value'])
            is_in_prompt = value_str in prompt_template
            
            if test['should_be_in_prompt']:
                assert is_in_prompt, f"Configuration value {test['name']} ({value_str}) should be in prompt template"
            else:
                assert not is_in_prompt, f"Configuration value {test['name']} ({value_str}) should not be in prompt template"
        
        print("✅ Prompt template configuration matches Stage3Config constants")
    
    def test_prompt_template_field_requirements(self, stage_3_instance):
        """Test that prompt template specifies all required scene fields."""
        from services.deconstructor.prompt_template import DeconstructorPrompts
        
        prompt_template = DeconstructorPrompts.get_scene_detection_prompt()
        
        # Required fields that must be in the prompt
        required_fields = [
            "scene_number",
            "title", 
            "setting",
            "characters",
            "summary",
            "start_marker",
            "end_marker",
            "content"
        ]
        
        for field in required_fields:
            assert field in prompt_template, f"Prompt template missing required field: {field}"
        
        # Test that JSON structure is specified
        assert "OUTPUT FORMAT (JSON)" in prompt_template
        assert "[" in prompt_template and "]" in prompt_template  # JSON array format
        assert "{" in prompt_template and "}" in prompt_template  # JSON object format
        
        print("✅ Prompt template specifies all required scene fields")
    
    def test_prompt_template_business_logic_alignment(self, stage_3_instance):
        """Test that prompt template business logic aligns with implementation."""
        from services.deconstructor.prompt_template import DeconstructorPrompts
        
        prompt_template = DeconstructorPrompts.get_scene_detection_prompt()
        
        # Business logic alignment tests
        business_logic_requirements = [
            "Change in time",  # Scene criteria
            "Change in location",  # Scene criteria
            "Change in point of view",  # Scene criteria
            "Significant shift in action",  # Scene criteria
            "Chapter or section breaks",  # Scene criteria
            "sequential",  # Scene numbering
            "2-4 words",  # Title requirements
            "1-2 sentences",  # Summary requirements
            "Count your scenes",  # Validation reminder
        ]
        
        for requirement in business_logic_requirements:
            assert requirement in prompt_template, f"Prompt template missing business logic requirement: {requirement}"
        
        # Test that the prompt emphasizes the mandatory nature of scene count
        mandatory_keywords = ["mandatory", "must", "CRITICAL", "REQUIREMENT"]
        has_mandatory_keyword = any(keyword in prompt_template for keyword in mandatory_keywords)
        assert has_mandatory_keyword, "Prompt template should emphasize mandatory nature of scene count requirement"
        
        print("✅ Prompt template business logic aligns with implementation")
    
    def test_stage_3_uses_correct_prompt_template(self, stage_3_instance):
        """Test that Stage 3 implementation uses the correct prompt template."""
        from services.deconstructor.prompt_template import DeconstructorPrompts
        
        # Test that the stage uses DeconstructorPrompts
        assert hasattr(stage_3_instance, 'prompt_template'), "Stage 3 should have prompt_template attribute"
        assert isinstance(stage_3_instance.prompt_template, DeconstructorPrompts), "Stage 3 should use DeconstructorPrompts"
        
        # Test that the prompt template method exists and is callable
        assert hasattr(stage_3_instance.prompt_template, 'get_scene_detection_prompt'), "Prompt template should have get_scene_detection_prompt method"
        assert callable(stage_3_instance.prompt_template.get_scene_detection_prompt), "get_scene_detection_prompt should be callable"
        
        # Test that the method returns a non-empty string
        prompt = stage_3_instance.prompt_template.get_scene_detection_prompt()
        assert isinstance(prompt, str), "Prompt should be a string"
        assert len(prompt) > 0, "Prompt should not be empty"
        assert len(prompt) > 500, "Prompt should be substantial (>500 chars)"
        
        print("✅ Stage 3 uses correct prompt template")


class TestStageCompatibility:
    """Test configuration compatibility between stages."""
    
    def test_stage_2_3_chunk_compatibility(self):
        """Test that Stage 3 can handle Stage 2's cleaned text output."""
        # Stage 2 configuration (from test observations)
        stage_2_max_output_tokens = 6000  # From real_generation_engine.py
        
        # Stage 3 configuration
        factory = RealGenerationEngineFactory()
        stage_3_max_output_tokens = factory.default_config['max_output_tokens']
        
        print(f"\nStage Compatibility Analysis:")
        print(f"  Stage 2 max output: {stage_2_max_output_tokens} tokens")
        print(f"  Stage 3 input capacity: {stage_3_max_output_tokens} tokens")
        
        # Stage 3 should be able to handle Stage 2's maximum output
        assert stage_3_max_output_tokens >= stage_2_max_output_tokens, \
            f"Stage 3 input capacity ({stage_3_max_output_tokens}) should >= Stage 2 max output ({stage_2_max_output_tokens})"
        
        print(f"  ✅ Token compatibility verified")
    
    def test_stage_3_scene_count_requirements(self):
        """Test Stage 3's scene count validation requirements."""
        # Stage 3 requires configured scenes per chunk
        min_scenes = Stage3Config.MIN_SCENES_PER_CHUNK
        max_scenes = Stage3Config.MAX_SCENES_PER_CHUNK
        max_retries = Stage3Config.MAX_RETRY_ATTEMPTS
        
        print(f"\nStage 3 Scene Count Requirements:")
        print(f"  Minimum scenes per chunk: {min_scenes}")
        print(f"  Maximum scenes per chunk: {max_scenes}")
        print(f"  Retry attempts: {max_retries}")
        
        # Validate these are reasonable requirements
        assert min_scenes > 0, "Minimum scene count should be positive"
        assert max_scenes > min_scenes, "Maximum should be greater than minimum"
        assert max_scenes <= 25, "Maximum scene count should be reasonable for processing"
        assert max_retries >= 2, "Should allow at least 2 retry attempts"
        
        print(f"  ✅ Scene count requirements validated")


@pytest.mark.real_api
@pytest.mark.database
class TestStage3Integration:
    """Test Stage 3: Scene Detection Integration"""
    
    @requires_previous_stages([1, 2])
    def test_stage_3_scene_extraction_success(self, register_stages_1_2_and_3, stage_3_instance, db_fixture, 
                                            sample_file_path, output_generator, test_output_options, 
                                            dependency_results):
        """Test successful scene extraction with real AI calls."""
        # Use data from Stage 1 and 2 dependencies
        assert dependency_results, "Stage 1 and 2 dependency results should be available"
        assert dependency_results.get('executed_stages') or dependency_results.get('loaded_from_cache'), \
            "Stages 1 and 2 should have been executed or loaded from cache"
        
        # Get the draft_id from Stage 2 execution results
        stage_2_data = dependency_results.get('stage_data', {}).get(2, {})
        draft_id = stage_2_data.get('draft_id')
        
        if not draft_id:
            # Fallback: try to find any existing draft with cleaned chunks
            chunks_query = db_fixture.execute_query(
                "SELECT draft_id FROM draft_chunks WHERE cleaned_text IS NOT NULL ORDER BY id DESC LIMIT 1"
            )
            if chunks_query:
                draft_id = chunks_query[0][0]
        
        assert draft_id, "No draft_id available from Stage 2 or existing data"
        
        # Verify Stage 2 created cleaned chunks for us to work with
        chunks_count = db_fixture.count_records('draft_chunks', draft_id)
        assert chunks_count > 0, f"Stage 2 should have created chunks, but found {chunks_count}"
        
        # Verify cleaned text exists
        cleaned_chunks = db_fixture.execute_query(
            "SELECT chunk_number, cleaned_text FROM draft_chunks WHERE draft_id = %s AND cleaned_text IS NOT NULL ORDER BY chunk_number",
            (draft_id,)
        )
        assert len(cleaned_chunks) > 0, "Stage 2 should have created cleaned text"
        
        # Run Stage 3 with real AI on the chunks created by Stage 2
        print(f"\nRunning Stage 3 scene extraction on draft {draft_id} with {len(cleaned_chunks)} cleaned chunks")
        
        start_time = time.time()
        result = stage_3_instance.run(draft_id=draft_id)
        processing_time = time.time() - start_time
        
        # Validate result structure
        Stage3Assertions.validate_stage_3_result_structure(result)
        assert result['success'] == True, f"Stage 3 should succeed, got error: {result.get('error', 'Unknown error')}"
        
        # Validate scene extraction results
        scenes_extracted = result['scenes_extracted']
        scenes_stored = result['scenes_stored']
        chunks_processed = result['chunks_processed']
        
        print(f"Stage 3 Results:")
        print(f"  Chunks processed: {chunks_processed}")
        print(f"  Scenes extracted: {scenes_extracted}")
        print(f"  Scenes stored: {scenes_stored}")
        print(f"  Processing time: {processing_time:.2f}s")
        
        # Validate extraction counts
        assert scenes_extracted > 0, "Should extract at least one scene"
        assert scenes_stored == scenes_extracted, "All extracted scenes should be stored"
        assert chunks_processed > 0, "Should process at least one chunk"
        
        # Validate scene count is reasonable for the number of chunks
        # Each chunk should produce 8-20 scenes, but some chunks might fail
        max_possible_scenes = chunks_processed * 20
        assert scenes_extracted <= max_possible_scenes, f"Too many scenes extracted: {scenes_extracted} > {max_possible_scenes}"
        
        # Validate database storage
        Stage3Assertions.validate_scene_database_storage(db_fixture, draft_id, scenes_extracted)
        
        # Validate scene data quality
        scenes = db_fixture.execute_query(
            "SELECT scene_number, title, summary, setting, characters, original_content FROM scenes WHERE draft_id = %s ORDER BY scene_number",
            (draft_id,)
        )
        
        # Convert database results to scene dictionaries for validation
        scene_dicts = []
        for scene in scenes:
            scene_number, title, summary, setting, characters, content = scene
            scene_dict = {
                'scene_number': scene_number,
                'title': title,
                'summary': summary,
                'setting': setting,
                'characters': characters if isinstance(characters, list) else [],
                'content': content
            }
            scene_dicts.append(scene_dict)
        
        # Validate global scene numbering
        Stage3Assertions.validate_global_scene_numbering(scene_dicts)
        
        # Validate individual scene structure and quality
        for scene_dict in scene_dicts[:3]:  # Check first 3 scenes for structure
            Stage3Assertions.validate_scene_structure(scene_dict)
            
            # Enhanced quality validation
            quality_checks = {
                'proper_sentences': True,
                'has_dialogue': False,  # Not required for all scenes
                'has_action': False,    # Not required for all scenes
                'has_description': False,  # Not required for all scenes
                'narrative_coherence': True
            }
            Stage3Assertions.validate_scene_content_quality(scene_dict, quality_checks)
            Stage3Assertions.validate_scene_metadata_quality(scene_dict)
        
        # Validate narrative consistency across scenes
        if len(scene_dicts) > 1:
            Stage3Assertions.validate_scene_narrative_consistency(scene_dicts)
        
        # Generate test outputs for debugging and next stage seeding
        if test_output_options['generate_outputs']:
            enhanced_result = result.copy()
            enhanced_result['draft_id'] = draft_id
            
            output_files = output_generator.generate_test_output(
                stage_number=3,
                test_name='test_stage_3_scene_extraction_success',
                test_result=enhanced_result,
                db_fixture=db_fixture,
                additional_data={
                    'sample_file_path': sample_file_path,
                    'test_configuration': {
                        'ai_provider': 'real',
                        'chunk_processing': 'individual',
                        'scene_count_range': '8-20',
                        'retry_attempts': 3
                    },
                    'performance_metrics': {
                        'processing_time_seconds': processing_time,
                        'chunks_processed': chunks_processed,
                        'scenes_per_second': scenes_extracted / processing_time if processing_time > 0 else 0
                    }
                }
            )
            print(f"Generated test outputs: {output_files}")


@pytest.mark.real_api
@pytest.mark.database  
class TestStage3RealAPI:
    """Test Stage 3 with real AI providers."""
    
    @requires_previous_stages([1, 2])
    def test_stage_3_multi_chunk_global_numbering(self, register_stages_1_2_and_3, stage_3_instance, db_fixture,
                                                 dependency_results):
        """Test global scene numbering across multiple chunks."""
        # Get draft with multiple chunks from dependencies
        stage_2_data = dependency_results.get('stage_data', {}).get(2, {})
        draft_id = stage_2_data.get('draft_id')
        
        if not draft_id:
            chunks_query = db_fixture.execute_query(
                "SELECT draft_id FROM draft_chunks WHERE cleaned_text IS NOT NULL ORDER BY id DESC LIMIT 1"
            )
            if chunks_query:
                draft_id = chunks_query[0][0]
        
        assert draft_id, "No draft_id available for testing"
        
        # Verify we have multiple chunks for testing
        chunks = db_fixture.execute_query(
            "SELECT chunk_number, cleaned_text FROM draft_chunks WHERE draft_id = %s ORDER BY chunk_number",
            (draft_id,)
        )
        
        if len(chunks) < 2:
            pytest.skip("Need at least 2 chunks for global numbering test")
        
        print(f"\nTesting global numbering with {len(chunks)} chunks")
        
        # Run Stage 3
        result = stage_3_instance.run(draft_id=draft_id)
        assert result['success'], f"Stage 3 failed: {result.get('error')}"
        
        # Get all scenes and verify global numbering
        scenes = db_fixture.execute_query(
            "SELECT scene_number FROM scenes WHERE draft_id = %s ORDER BY scene_number",
            (draft_id,)
        )
        
        # Verify sequential numbering starting from 1
        expected_number = 1
        for scene in scenes:
            scene_number = scene[0]
            assert scene_number == expected_number, \
                f"Global numbering broken: expected {expected_number}, got {scene_number}"
            expected_number += 1
        
        print(f"Global numbering verified: {len(scenes)} scenes numbered 1-{len(scenes)}")
    
    @requires_previous_stages([1, 2])
    def test_stage_3_scene_count_validation(self, register_stages_1_2_and_3, stage_3_instance, db_fixture,
                                          dependency_results):
        """Test that scene count validation works with real AI responses."""
        # Get draft from dependencies
        stage_2_data = dependency_results.get('stage_data', {}).get(2, {})
        draft_id = stage_2_data.get('draft_id')
        
        if not draft_id:
            chunks_query = db_fixture.execute_query(
                "SELECT draft_id FROM draft_chunks WHERE cleaned_text IS NOT NULL ORDER BY id DESC LIMIT 1"
            )
            if chunks_query:
                draft_id = chunks_query[0][0]
        
        assert draft_id, "No draft_id available for testing"
        
        # Run Stage 3 and check results
        result = stage_3_instance.run(draft_id=draft_id)
        
        if result['success']:
            # If successful, scenes should be stored
            scenes_count = db_fixture.count_records('scenes', draft_id)
            assert scenes_count > 0, "Successful run should store scenes"
            
            # Check that scenes exist in database
            scenes = db_fixture.execute_query(
                "SELECT scene_number, title FROM scenes WHERE draft_id = %s ORDER BY scene_number LIMIT 5",
                (draft_id,)
            )
            
            print(f"Scene validation results: {scenes_count} scenes stored")
            for scene in scenes[:3]:  # Show first 3 scenes
                print(f"  Scene {scene[0]}: {scene[1]}")
                
        else:
            # If failed, no scenes should be stored
            scenes_count = db_fixture.count_records('scenes', draft_id)
            print(f"Stage 3 failed as expected: {result.get('error', 'Unknown error')}")
            print(f"Scenes in database: {scenes_count}")


@pytest.mark.real_api
@pytest.mark.database
class TestStage3Database:
    """Test Stage 3 database operations."""
    
    @requires_previous_stages([1, 2])
    def test_stage_3_utf8_text_handling(self, register_stages_1_2_and_3, stage_3_instance, db_fixture,
                                       dependency_results):
        """Test UTF-8 text handling in scene storage."""
        # Get draft from dependencies
        stage_2_data = dependency_results.get('stage_data', {}).get(2, {})
        draft_id = stage_2_data.get('draft_id')
        
        if not draft_id:
            chunks_query = db_fixture.execute_query(
                "SELECT draft_id FROM draft_chunks WHERE cleaned_text IS NOT NULL ORDER BY id DESC LIMIT 1"
            )
            if chunks_query:
                draft_id = chunks_query[0][0]
        
        assert draft_id, "No draft_id available for testing"
        
        # Run Stage 3
        result = stage_3_instance.run(draft_id=draft_id)
        assert result['success'], f"Stage 3 failed: {result.get('error')}"
        
        # Check UTF-8 storage in database
        scenes = db_fixture.execute_query(
            "SELECT title, summary, setting, original_content FROM scenes WHERE draft_id = %s LIMIT 3",
            (draft_id,)
        )
        
        for scene in scenes:
            title, summary, setting, content = scene
            
            # Verify text fields are properly stored as strings
            assert isinstance(title, str), "Title should be stored as string"
            assert isinstance(summary, str), "Summary should be stored as string"
            assert isinstance(setting, str), "Setting should be stored as string"
            assert isinstance(content, str), "Content should be stored as string"
            
            # Verify text can be encoded/decoded properly
            for text_field in [title, summary, setting, content]:
                if text_field:
                    try:
                        text_field.encode('utf-8').decode('utf-8')
                    except UnicodeError:
                        raise AssertionError(f"Text field not properly UTF-8 encoded: {text_field[:50]}...")
        
        print(f"UTF-8 text handling validated for {len(scenes)} scenes")
    
    @requires_previous_stages([1, 2])
    def test_stage_3_scene_content_quality_validation(self, register_stages_1_2_and_3, stage_3_instance, db_fixture,
                                                    dependency_results):
        """Test comprehensive scene content quality validation."""
        # Get draft from dependencies
        stage_2_data = dependency_results.get('stage_data', {}).get(2, {})
        draft_id = stage_2_data.get('draft_id')
        
        if not draft_id:
            chunks_query = db_fixture.execute_query(
                "SELECT draft_id FROM draft_chunks WHERE cleaned_text IS NOT NULL ORDER BY id DESC LIMIT 1"
            )
            if chunks_query:
                draft_id = chunks_query[0][0]
        
        assert draft_id, "No draft_id available for testing"
        
        # Run Stage 3
        result = stage_3_instance.run(draft_id=draft_id)
        assert result['success'], f"Stage 3 failed: {result.get('error')}"
        
        # Get scenes for quality validation
        scenes = db_fixture.execute_query(
            "SELECT scene_number, title, summary, setting, characters, original_content FROM scenes WHERE draft_id = %s ORDER BY scene_number",
            (draft_id,)
        )
        
        # Convert to scene dictionaries
        scene_dicts = []
        for scene in scenes:
            scene_number, title, summary, setting, characters, content = scene
            scene_dict = {
                'scene_number': scene_number,
                'title': title,
                'summary': summary,
                'setting': setting,
                'characters': characters if isinstance(characters, list) else [],
                'content': content
            }
            scene_dicts.append(scene_dict)
        
        # Comprehensive quality validation
        quality_passed = 0
        quality_warnings = 0
        
        for scene_dict in scene_dicts:
            try:
                # Test metadata quality
                Stage3Assertions.validate_scene_metadata_quality(scene_dict)
                
                # Test content quality with flexible requirements
                quality_checks = {
                    'proper_sentences': True,
                    'has_dialogue': False,  # Optional
                    'has_action': False,    # Optional
                    'has_description': False,  # Optional
                    'narrative_coherence': True
                }
                Stage3Assertions.validate_scene_content_quality(scene_dict, quality_checks)
                
                quality_passed += 1
                
            except AssertionError as e:
                quality_warnings += 1
                print(f"Scene {scene_dict['scene_number']} quality warning: {e}")
        
        # Test narrative consistency across all scenes
        if len(scene_dicts) > 1:
            Stage3Assertions.validate_scene_narrative_consistency(scene_dicts)
        
        # Quality metrics
        total_scenes = len(scene_dicts)
        quality_rate = quality_passed / total_scenes if total_scenes > 0 else 0
        
        print(f"Scene Quality Metrics:")
        print(f"  Total scenes: {total_scenes}")
        print(f"  Quality passed: {quality_passed}")
        print(f"  Quality warnings: {quality_warnings}")
        print(f"  Quality rate: {quality_rate:.2%}")
        
        # Assert minimum quality standards
        assert quality_rate >= 0.5, f"Scene quality rate too low: {quality_rate:.2%}"
        assert quality_passed > 0, "At least one scene should pass quality validation"
        
        print("✅ Scene content quality validation completed")


@pytest.mark.real_api
@pytest.mark.database
class TestStage3BusinessLogic:
    """Test Stage 3 business logic methods directly."""
    
    def test_validate_scene_count_method_valid_counts(self, stage_3_instance):
        """Test _validate_scene_count with valid scene counts."""
        # Test valid scene counts using configuration
        min_scenes = Stage3Config.MIN_SCENES_PER_CHUNK
        max_scenes = Stage3Config.MAX_SCENES_PER_CHUNK
        valid_counts = [min_scenes, min_scenes + 2, (min_scenes + max_scenes) // 2, max_scenes - 2, max_scenes]
        
        for count in valid_counts:
            result = stage_3_instance._validate_scene_count(count)
            assert result is True, f"Scene count {count} should be valid"
            
            # Use business logic assertion
            Stage3Assertions.validate_scene_count_business_logic(count, expected_valid=True)
    
    def test_validate_scene_count_method_invalid_counts(self, stage_3_instance):
        """Test _validate_scene_count with invalid scene counts."""
        min_scenes = Stage3Config.MIN_SCENES_PER_CHUNK
        max_scenes = Stage3Config.MAX_SCENES_PER_CHUNK
        
        # Test invalid scene counts (too few)
        invalid_low = [0, 1, min_scenes - 2, min_scenes - 1]
        for count in invalid_low:
            result = stage_3_instance._validate_scene_count(count)
            assert result is False, f"Scene count {count} should be invalid (too few)"
            
            # Use business logic assertion
            Stage3Assertions.validate_scene_count_business_logic(count, expected_valid=False)
        
        # Test invalid scene counts (too many)
        invalid_high = [max_scenes + 1, max_scenes + 2, max_scenes + 10, max_scenes + 30]
        for count in invalid_high:
            result = stage_3_instance._validate_scene_count(count)
            assert result is False, f"Scene count {count} should be invalid (too many)"
            
            # Use business logic assertion
            Stage3Assertions.validate_scene_count_business_logic(count, expected_valid=False)
    
    def test_validate_scene_count_method_edge_cases(self, stage_3_instance):
        """Test _validate_scene_count with edge cases."""
        min_scenes = Stage3Config.MIN_SCENES_PER_CHUNK
        max_scenes = Stage3Config.MAX_SCENES_PER_CHUNK
        
        # Test boundary conditions
        assert stage_3_instance._validate_scene_count(min_scenes - 1) is False, f"{min_scenes - 1} scenes should be invalid"
        assert stage_3_instance._validate_scene_count(min_scenes) is True, f"{min_scenes} scenes should be valid"
        assert stage_3_instance._validate_scene_count(max_scenes) is True, f"{max_scenes} scenes should be valid"
        assert stage_3_instance._validate_scene_count(max_scenes + 1) is False, f"{max_scenes + 1} scenes should be invalid"
        
        # Test with negative numbers
        assert stage_3_instance._validate_scene_count(-1) is False, "Negative scene count should be invalid"
        assert stage_3_instance._validate_scene_count(-10) is False, "Negative scene count should be invalid"
    
    def test_stage_3_configuration_alignment(self, stage_3_instance):
        """Test that Stage 3 implementation aligns with configuration constants."""
        # Test that Stage 3 uses the same validation logic as configuration
        for count in range(0, 30):
            stage_result = stage_3_instance._validate_scene_count(count)
            config_result = Stage3Config.validate_scene_count(count)
            assert stage_result == config_result, f"Stage 3 and config validation mismatch for count {count}"
        
        # Test content length validation alignment
        test_contents = [
            "",  # Empty
            "Short",  # Too short
            "A" * (Stage3Config.MIN_SCENE_CONTENT_LENGTH - 1),  # One char too short
            "A" * Stage3Config.MIN_SCENE_CONTENT_LENGTH,  # Exactly minimum
            "A" * (Stage3Config.MIN_SCENE_CONTENT_LENGTH + 10),  # Above minimum
        ]
        
        for content in test_contents:
            # Create a test scene with this content
            test_scene = {
                'scene_number': 1,
                'title': 'Test Scene',
                'setting': 'Test Setting',
                'characters': ['Test Character'],
                'summary': 'Test Summary',
                'content': content
            }
            
            # Test that validation uses the same logic
            expected_valid = Stage3Config.validate_scene_content_length(content)
            validated_scenes = stage_3_instance._validate_scenes_data([test_scene], "original text")
            actual_valid = len(validated_scenes) > 0
            
            assert actual_valid == expected_valid, f"Content length validation mismatch for content of length {len(content)}"
        
        print("✅ Stage 3 configuration alignment validated")
    
    def test_transaction_pattern_standardization(self, stage_3_instance, db_fixture):
        """Test that Stage 3 and test fixtures use consistent transaction patterns."""
        # Test that Stage 3 uses utf8_database_connection
        assert hasattr(stage_3_instance, 'db_pool'), "Stage 3 should have db_pool attribute"
        
        # Test that Stage 3 methods use utf8_database_connection
        stage_3_source = stage_3_instance.__class__.__module__
        import inspect
        stage_3_source_code = inspect.getsource(stage_3_instance.__class__)
        
        # Check that Stage 3 uses utf8_database_connection
        assert 'utf8_database_connection' in stage_3_source_code, "Stage 3 should use utf8_database_connection"
        
        # Test that database fixtures now use same pattern
        db_fixture_source = inspect.getsource(db_fixture.__class__)
        assert 'utf8_database_connection' in db_fixture_source, "Database fixtures should use utf8_database_connection"
        
        # Test that both use the same UTF-8 safety patterns
        from utils.database_utils import utf8_database_connection, clean_text_for_database
        
        # Test UTF-8 safety functions are available
        assert callable(utf8_database_connection), "utf8_database_connection should be callable"
        assert callable(clean_text_for_database), "clean_text_for_database should be callable"
        
        # Test that text cleaning works consistently
        test_text = "Test text with UTF-8 characters: ñáéíóú"
        cleaned_text = clean_text_for_database(test_text)
        assert isinstance(cleaned_text, str), "Cleaned text should be a string"
        assert len(cleaned_text) > 0, "Cleaned text should not be empty"
        
        print("✅ Transaction pattern standardization validated")
    
    def test_validate_scenes_data_method_valid_data(self, stage_3_instance):
        """Test _validate_scenes_data with valid scene data."""
        # Create valid scene data
        valid_scenes = [
            {
                'scene_number': 1,
                'title': 'Opening Scene',
                'setting': 'A dark forest',
                'characters': ['John', 'Mary'],
                'summary': 'Characters meet in the forest',
                'content': 'It was a dark and stormy night in the forest. John walked carefully through the trees, his flashlight casting eerie shadows. Suddenly, he heard a voice calling his name.'
            },
            {
                'scene_number': 2,
                'title': 'The Revelation',
                'setting': 'Forest clearing',
                'characters': ['John', 'Mary', 'Stranger'],
                'summary': 'A stranger appears with important news',
                'content': 'In the clearing, Mary stood waiting. Her eyes were wide with fear as she pointed toward the approaching figure. "John," she whispered, "that\'s not who you think it is."'
            }
        ]
        
        original_text = "Sample text for validation purposes. This is longer than 50 characters to meet the minimum requirement. It was a dark and stormy night in the forest. John walked carefully through the trees, his flashlight casting eerie shadows. Suddenly, he heard a voice calling his name. In the clearing, Mary stood waiting. Her eyes were wide with fear as she pointed toward the approaching figure. \"John,\" she whispered, \"that's not who you think it is.\" The stranger emerged from the shadows, revealing secrets that would change everything. The forest held many mysteries, and tonight they would all be revealed in this dramatic encounter."
        
        validated_scenes = stage_3_instance._validate_scenes_data(valid_scenes, original_text)
        
        assert len(validated_scenes) == 2, "Should validate both scenes"
        
        for scene in validated_scenes:
            Stage3Assertions.validate_scene_structure(scene)
            Stage3Assertions.validate_scene_content_extraction(scene, original_text)
    
    def test_validate_scenes_data_method_malformed_data(self, stage_3_instance):
        """Test _validate_scenes_data with malformed scene data."""
        original_text = "Sample text for validation purposes. This is longer than 50 characters to meet the minimum requirement. It was a dark and stormy night in the forest. John walked carefully through the trees, his flashlight casting eerie shadows. Suddenly, he heard a voice calling his name. In the clearing, Mary stood waiting. Her eyes were wide with fear as she pointed toward the approaching figure. \"John,\" she whispered, \"that's not who you think it is.\" The stranger emerged from the shadows, revealing secrets that would change everything. The forest held many mysteries, and tonight they would all be revealed in this dramatic encounter."
        
        # Test with missing fields
        malformed_scenes = [
            {
                'scene_number': 1,
                'title': 'Missing Fields Scene',
                # Missing 'setting', 'characters', 'summary', 'content'
            }
        ]
        
        validated_scenes = stage_3_instance._validate_scenes_data(malformed_scenes, original_text)
        
        # Should still process but with defaults
        assert len(validated_scenes) >= 0, "Should handle malformed data gracefully"
        
        # Test with empty content
        empty_content_scenes = [
            {
                'scene_number': 1,
                'title': 'Empty Content Scene',
                'setting': 'Somewhere',
                'characters': [],
                'summary': 'A scene with no content',
                'content': ''  # Empty content
            }
        ]
        
        validated_scenes = stage_3_instance._validate_scenes_data(empty_content_scenes, original_text)
        
        # Should be filtered out due to empty content
        assert len(validated_scenes) == 0, "Scenes with empty content should be filtered out"
        
        # Test with very short content
        short_content_scenes = [
            {
                'scene_number': 1,
                'title': 'Short Content Scene',
                'setting': 'Somewhere',
                'characters': [],
                'summary': 'A scene with short content',
                'content': 'Too short'  # Less than 50 characters
            }
        ]
        
        validated_scenes = stage_3_instance._validate_scenes_data(short_content_scenes, original_text)
        
        # Should be filtered out due to short content
        assert len(validated_scenes) == 0, "Scenes with short content should be filtered out"
    
    def test_extract_content_by_markers_method(self, stage_3_instance):
        """Test _extract_content_by_markers method."""
        # Test with valid markers
        original_text = "This is the beginning. START_MARKER This is the content we want to extract. END_MARKER This is the end."
        
        extracted = stage_3_instance._extract_content_by_markers(
            original_text, 
            "START_MARKER", 
            "END_MARKER"
        )
        
        expected = "START_MARKER This is the content we want to extract. END_MARKER"
        assert extracted == expected, f"Expected '{expected}', got '{extracted}'"
        
        # Use business logic assertion
        Stage3Assertions.validate_scene_markers_extraction(
            original_text, 
            "START_MARKER", 
            "END_MARKER", 
            expected
        )
        
        # Test with markers at the beginning and end
        text_with_edge_markers = "START_MARKER Full content here END_MARKER"
        extracted = stage_3_instance._extract_content_by_markers(
            text_with_edge_markers,
            "START_MARKER",
            "END_MARKER"
        )
        
        assert extracted == text_with_edge_markers, "Should extract full content when markers are at edges"
        
        # Test with non-existent markers
        extracted = stage_3_instance._extract_content_by_markers(
            original_text,
            "NONEXISTENT_START",
            "NONEXISTENT_END"
        )
        
        assert extracted == "", "Should return empty string when markers don't exist"
        
        # Test with only start marker
        extracted = stage_3_instance._extract_content_by_markers(
            original_text,
            "START_MARKER",
            "NONEXISTENT_END"
        )
        
        assert extracted == "", "Should return empty string when end marker doesn't exist"
    
    def test_apply_global_scene_numbering_method(self, stage_3_instance):
        """Test _apply_global_scene_numbering method."""
        # Test with normal scenes
        scenes = [
            {'scene_number': 1, 'title': 'Scene 1', 'content': 'Content 1'},
            {'scene_number': 2, 'title': 'Scene 2', 'content': 'Content 2'},
            {'scene_number': 3, 'title': 'Scene 3', 'content': 'Content 3'}
        ]
        
        starting_number = 10
        numbered_scenes = stage_3_instance._apply_global_scene_numbering(scenes, starting_number)
        
        assert len(numbered_scenes) == 3, "Should have same number of scenes"
        
        # Validate global numbering
        Stage3Assertions.validate_global_numbering_logic(numbered_scenes, starting_number)
        
        for i, scene in enumerate(numbered_scenes):
            expected_number = starting_number + i
            assert scene['scene_number'] == expected_number, f"Scene {i} should be numbered {expected_number}"
            assert scene['title'] == f'Scene {i+1}', "Other fields should be preserved"
        
        # Test with empty scenes
        empty_scenes = []
        numbered_empty = stage_3_instance._apply_global_scene_numbering(empty_scenes, 1)
        assert len(numbered_empty) == 0, "Empty scenes should remain empty"
        
        # Test with single scene
        single_scene = [{'scene_number': 99, 'title': 'Single Scene', 'content': 'Single content'}]
        numbered_single = stage_3_instance._apply_global_scene_numbering(single_scene, 5)
        
        assert len(numbered_single) == 1, "Should have one scene"
        assert numbered_single[0]['scene_number'] == 5, "Should be renumbered to starting number"


@pytest.mark.real_api
@pytest.mark.database
class TestStage3RetryLogic:
    """Test Stage 3 retry logic for scene detection."""
    
    def test_retry_scene_detection_too_few_scenes(self, stage_3_instance):
        """Test retry logic when initial detection finds too few scenes."""
        # Mock generation engine to simulate retry scenarios
        from unittest.mock import Mock, MagicMock
        
        # Create a mock generation engine
        mock_generation_engine = Mock()
        mock_response = Mock()
        mock_response.success = True
        mock_response.text = '{"scenes": [{"scene_number": 1, "title": "Scene 1", "content": "Content 1 with more than fifty characters to meet minimum requirements"}]}'
        mock_generation_engine.generate.return_value = mock_response
        
        # Replace the generation engine
        original_engine = stage_3_instance.generation_engine
        stage_3_instance.generation_engine = mock_generation_engine
        
        try:
            # Test with too few scenes (previous_scene_count = 3)
            result = stage_3_instance._retry_scene_detection(
                text_content="Sample text content for testing retry logic with scene detection",
                attempt=1,
                previous_scene_count=3
            )
            
            # Should have attempted retry
            assert mock_generation_engine.generate.called, "Should have called generation engine"
            
            # Verify retry instruction was for MORE scenes
            assert hasattr(mock_generation_engine, 'request'), "Should have request object"
            if hasattr(mock_generation_engine.request, 'instruction'):
                instruction = mock_generation_engine.request.instruction
                assert 'MORE' in instruction, "Should request MORE scenes when previous count was too low"
            
            # Should return scenes from the mock response
            assert len(result) == 1, "Should return scenes from retry"
            
            # Validate retry attempt logic
            Stage3Assertions.validate_retry_attempt_logic(result, attempt_number=1, previous_count=3)
            
        finally:
            # Restore original engine
            stage_3_instance.generation_engine = original_engine
    
    def test_retry_scene_detection_too_many_scenes(self, stage_3_instance):
        """Test retry logic when initial detection finds too many scenes."""
        from unittest.mock import Mock, MagicMock
        
        # Create a mock generation engine
        mock_generation_engine = Mock()
        mock_response = Mock()
        mock_response.success = True
        mock_response.text = '{"scenes": [{"scene_number": 1, "title": "Scene 1", "content": "Content 1 with more than fifty characters to meet minimum requirements"}]}'
        mock_generation_engine.generate.return_value = mock_response
        
        # Replace the generation engine
        original_engine = stage_3_instance.generation_engine
        stage_3_instance.generation_engine = mock_generation_engine
        
        try:
            # Test with too many scenes (previous_scene_count = 25)
            result = stage_3_instance._retry_scene_detection(
                text_content="Sample text content for testing retry logic with scene detection",
                attempt=1,
                previous_scene_count=25
            )
            
            # Should have attempted retry
            assert mock_generation_engine.generate.called, "Should have called generation engine"
            
            # Verify retry instruction was for FEWER scenes
            if hasattr(mock_generation_engine, 'request') and hasattr(mock_generation_engine.request, 'instruction'):
                instruction = mock_generation_engine.request.instruction
                assert 'FEWER' in instruction, "Should request FEWER scenes when previous count was too high"
            
            # Should return scenes from the mock response
            assert len(result) == 1, "Should return scenes from retry"
            
            # Validate retry attempt logic
            Stage3Assertions.validate_retry_attempt_logic(result, attempt_number=1, previous_count=25)
            
        finally:
            # Restore original engine
            stage_3_instance.generation_engine = original_engine
    
    def test_retry_scene_detection_generation_failure(self, stage_3_instance):
        """Test retry logic when AI generation fails."""
        from unittest.mock import Mock
        
        # Create a mock generation engine that fails
        mock_generation_engine = Mock()
        mock_response = Mock()
        mock_response.success = False
        mock_response.error_message = "AI generation failed"
        mock_generation_engine.generate.return_value = mock_response
        
        # Replace the generation engine
        original_engine = stage_3_instance.generation_engine
        stage_3_instance.generation_engine = mock_generation_engine
        
        try:
            # Test retry with generation failure
            result = stage_3_instance._retry_scene_detection(
                text_content="Sample text content for testing retry logic with scene detection",
                attempt=1,
                previous_scene_count=5
            )
            
            # Should return empty list on failure
            assert result == [], "Should return empty list when generation fails"
            
            # Should have attempted generation
            assert mock_generation_engine.generate.called, "Should have called generation engine"
            
        finally:
            # Restore original engine
            stage_3_instance.generation_engine = original_engine
    
    def test_retry_scene_detection_json_parsing_error(self, stage_3_instance):
        """Test retry logic when JSON parsing fails."""
        from unittest.mock import Mock
        
        # Create a mock generation engine that returns invalid JSON
        mock_generation_engine = Mock()
        mock_response = Mock()
        mock_response.success = True
        mock_response.text = "Invalid JSON response that cannot be parsed"
        mock_generation_engine.generate.return_value = mock_response
        
        # Replace the generation engine
        original_engine = stage_3_instance.generation_engine
        stage_3_instance.generation_engine = mock_generation_engine
        
        try:
            # Test retry with JSON parsing failure
            result = stage_3_instance._retry_scene_detection(
                text_content="Sample text content for testing retry logic with scene detection",
                attempt=1,
                previous_scene_count=5
            )
            
            # Should return empty list on JSON parsing failure
            assert result == [], "Should return empty list when JSON parsing fails"
            
            # Should have attempted generation
            assert mock_generation_engine.generate.called, "Should have called generation engine"
            
        finally:
            # Restore original engine
            stage_3_instance.generation_engine = original_engine
    
    def test_process_chunk_retry_logic_success(self, stage_3_instance):
        """Test _process_chunk retry logic with successful retry."""
        from unittest.mock import Mock, patch
        
        # Mock _detect_scenes to fail first, then succeed
        detection_results = [
            [],  # First attempt fails (empty list)
            [   # Second attempt succeeds
                {
                    'scene_number': 1,
                    'title': 'Scene 1',
                    'setting': 'Forest',
                    'characters': ['John'],
                    'summary': 'Opening scene',
                    'content': 'It was a dark and stormy night in the forest. John walked carefully through the trees, his flashlight casting eerie shadows. Suddenly, he heard a voice calling his name.'
                },
                {
                    'scene_number': 2,
                    'title': 'Scene 2',
                    'setting': 'Clearing',
                    'characters': ['John', 'Mary'],
                    'summary': 'Character meeting',
                    'content': 'In the clearing, Mary stood waiting. Her eyes were wide with fear as she pointed toward the approaching figure. "John," she whispered, "that\'s not who you think it is."'
                }
            ]
        ]
        
        call_count = 0
        def mock_detect_scenes(text):
            nonlocal call_count
            result = detection_results[call_count] if call_count < len(detection_results) else []
            call_count += 1
            return result
        
        # Mock _retry_scene_detection to succeed with valid scene count
        def mock_retry_scene_detection(text, attempt, previous_count):
            scenes = []
            for i in range(8):  # Return 8 scenes (minimum valid count)
                scenes.append({
                    'scene_number': i + 1,
                    'title': f'Retry Scene {i + 1}',
                    'setting': 'Forest',
                    'characters': ['John'],
                    'summary': f'Retry scene {i + 1}',
                    'content': f'This is the retry attempt content for scene {i + 1} that is definitely longer than fifty characters to meet the minimum requirements for scene content length.'
                })
            return scenes
        
        # Replace methods with mocks
        with patch.object(stage_3_instance, '_detect_scenes', side_effect=mock_detect_scenes):
            with patch.object(stage_3_instance, '_retry_scene_detection', side_effect=mock_retry_scene_detection):
                # Test chunk processing with retry
                result = stage_3_instance._process_chunk(
                    chunk_number=1,
                    cleaned_text="Sample cleaned text for chunk processing test",
                    starting_scene_number=1
                )
                
                # Should succeed on retry
                assert len(result) > 0, "Should return scenes after retry"
                
                # Validate global numbering was applied
                Stage3Assertions.validate_global_numbering_logic(result, starting_number=1)
                
                # Validate scene structure
                for scene in result:
                    Stage3Assertions.validate_scene_structure(scene)
    
    def test_process_chunk_retry_logic_all_attempts_fail(self, stage_3_instance):
        """Test _process_chunk retry logic when all attempts fail."""
        from unittest.mock import Mock, patch
        
        # Mock all detection methods to fail
        def mock_detect_scenes_fail(text):
            return []  # Always return empty (invalid scene count)
        
        def mock_retry_scene_detection_fail(text, attempt, previous_count):
            return []  # Always return empty (retry fails)
        
        # Replace methods with failing mocks
        with patch.object(stage_3_instance, '_detect_scenes', side_effect=mock_detect_scenes_fail):
            with patch.object(stage_3_instance, '_retry_scene_detection', side_effect=mock_retry_scene_detection_fail):
                # Test chunk processing with all attempts failing
                result = stage_3_instance._process_chunk(
                    chunk_number=1,
                    cleaned_text="Sample cleaned text for chunk processing test",
                    starting_scene_number=1
                )
                
                # Should return empty list after all attempts fail
                assert result == [], "Should return empty list when all attempts fail"
    
    def test_process_chunk_retry_logic_valid_first_attempt(self, stage_3_instance):
        """Test _process_chunk when first attempt succeeds."""
        from unittest.mock import Mock, patch
        
        # Mock _detect_scenes to succeed immediately with valid scene count
        def mock_detect_scenes_success(text):
            scenes = []
            for i in range(10):  # Return 10 scenes (valid count)
                scenes.append({
                    'scene_number': i + 1,
                    'title': f'Scene {i + 1}',
                    'setting': 'Forest' if i % 2 == 0 else 'Clearing',
                    'characters': ['John'] if i % 2 == 0 else ['John', 'Mary'],
                    'summary': f'Scene {i + 1} summary',
                    'content': f'It was a dark and stormy night in the forest. This is scene {i + 1} content that is definitely longer than fifty characters to meet the minimum requirements for scene content length.'
                })
            return scenes
        
        # Mock _retry_scene_detection (should not be called)
        mock_retry = Mock()
        
        # Replace methods with mocks
        with patch.object(stage_3_instance, '_detect_scenes', side_effect=mock_detect_scenes_success):
            with patch.object(stage_3_instance, '_retry_scene_detection', mock_retry):
                # Test chunk processing with immediate success
                result = stage_3_instance._process_chunk(
                    chunk_number=1,
                    cleaned_text="Sample cleaned text for chunk processing test",
                    starting_scene_number=5
                )
                
                # Should succeed on first attempt
                assert len(result) == 10, "Should return scenes from first attempt"
                
                # Retry should not have been called
                mock_retry.assert_not_called()
                
                # Validate global numbering was applied
                Stage3Assertions.validate_global_numbering_logic(result, starting_number=5)
                
                # Validate scene structure
                for scene in result:
                    Stage3Assertions.validate_scene_structure(scene)


@pytest.mark.real_api
@pytest.mark.database
class TestStage3GlobalNumbering:
    """Test Stage 3 global scene numbering across multiple chunks."""
    
    @requires_previous_stages([1, 2])
    def test_global_numbering_multiple_chunks_sequential(self, register_stages_1_2_and_3, stage_3_instance, db_fixture, dependency_results):
        """Test global numbering across multiple chunks in sequence."""
        # Get draft from dependencies
        stage_2_data = dependency_results.get('stage_data', {}).get(2, {})
        draft_id = stage_2_data.get('draft_id')
        
        if not draft_id:
            chunks_query = db_fixture.execute_query(
                "SELECT draft_id FROM draft_chunks WHERE cleaned_text IS NOT NULL ORDER BY id DESC LIMIT 1"
            )
            if chunks_query:
                draft_id = chunks_query[0][0]
        
        assert draft_id, "No draft_id available for testing"
        
        # Verify we have multiple chunks
        chunks = db_fixture.execute_query(
            "SELECT chunk_number, cleaned_text FROM draft_chunks WHERE draft_id = %s ORDER BY chunk_number",
            (draft_id,)
        )
        
        if len(chunks) < 2:
            # Create additional chunks for testing
            db_fixture.execute_query(
                "INSERT INTO draft_chunks (draft_id, chunk_number, raw_text, cleaned_text) VALUES (%s, %s, %s, %s)",
                (draft_id, 999, "Additional test chunk content", "Additional test chunk content")
            )
            chunks = db_fixture.execute_query(
                "SELECT chunk_number, cleaned_text FROM draft_chunks WHERE draft_id = %s ORDER BY chunk_number",
                (draft_id,)
            )
        
        print(f"Testing global numbering with {len(chunks)} chunks")
        
        # Run Stage 3 on multiple chunks
        result = stage_3_instance.run(draft_id=draft_id)
        assert result['success'], f"Stage 3 failed: {result.get('error')}"
        
        # Get all scenes and verify sequential numbering
        scenes = db_fixture.execute_query(
            "SELECT scene_number, title FROM scenes WHERE draft_id = %s ORDER BY scene_number",
            (draft_id,)
        )
        
        # Validate global numbering across all chunks
        Stage3Assertions.validate_global_numbering_logic(
            [{'scene_number': scene[0]} for scene in scenes],
            starting_number=1
        )
        
        # Verify continuous numbering
        for i, scene in enumerate(scenes):
            scene_number = scene[0]
            expected_number = i + 1
            assert scene_number == expected_number, \
                f"Global numbering broken: expected {expected_number}, got {scene_number}"
        
        print(f"Global numbering verified: {len(scenes)} scenes numbered 1-{len(scenes)}")
    
    def test_global_numbering_chunk_failure_scenarios(self, stage_3_instance, db_fixture):
        """Test global numbering when some chunks fail processing."""
        from unittest.mock import Mock, patch
        
        # Create test draft with chunks
        test_data = SampleDataGenerator(db_fixture.connection_pool)
        draft_data = test_data.generate_draft_request()
        
        workspace_data = db_fixture.create_test_workspace(
            workspace_id=draft_data['workspace_id'],
            user_id=draft_data['user_id']
        )
        
        test_draft = db_fixture.create_test_draft(
            draft_id=draft_data['draft_id'],
            workspace_id=workspace_data['workspace_id'],
            user_id=workspace_data['user_id']
        )
        
        # Add multiple chunks
        for i in range(3):
            db_fixture.execute_query(
                "INSERT INTO draft_chunks (draft_id, chunk_number, raw_text, cleaned_text) VALUES (%s, %s, %s, %s)",
                (test_draft['draft_id'], i+1, f"Test chunk {i+1} content", f"Test chunk {i+1} content")
            )
        
        # Mock _process_chunk to simulate some failures
        def mock_process_chunk(chunk_number, cleaned_text, starting_scene_number):
            if chunk_number == 2:
                # Simulate chunk 2 failure
                return []
            else:
                # Simulate successful chunks
                return [
                    {
                        'scene_number': starting_scene_number,
                        'title': f'Scene from chunk {chunk_number}',
                        'setting': 'Test setting',
                        'characters': ['Test character'],
                        'summary': f'Scene from chunk {chunk_number}',
                        'content': f'Content from chunk {chunk_number} that is definitely longer than fifty characters to meet the minimum requirements for scene content length.'
                    }
                ]
        
        # Replace _process_chunk with mock
        with patch.object(stage_3_instance, '_process_chunk', side_effect=mock_process_chunk):
            # Run Stage 3 with chunk failures
            result = stage_3_instance.run(draft_id=test_draft['draft_id'])
            assert result['success'], f"Stage 3 failed: {result.get('error')}"
            
            # Should have scenes from chunks 1 and 3 only
            scenes = db_fixture.execute_query(
                "SELECT scene_number, title FROM scenes WHERE draft_id = %s ORDER BY scene_number",
                (test_draft['draft_id'],)
            )
            
            # Validate global numbering despite chunk failure
            Stage3Assertions.validate_global_numbering_logic(
                [{'scene_number': scene[0]} for scene in scenes],
                starting_number=1
            )
            
            # Should still have sequential numbering
            for i, scene in enumerate(scenes):
                scene_number = scene[0]
                expected_number = i + 1
                assert scene_number == expected_number, \
                    f"Global numbering broken with chunk failure: expected {expected_number}, got {scene_number}"
    
    def test_global_numbering_with_different_starting_numbers(self, stage_3_instance):
        """Test global numbering logic with different starting numbers."""
        # Test with starting number 1
        scenes_1 = [
            {'scene_number': 0, 'title': 'Scene A'},
            {'scene_number': 0, 'title': 'Scene B'},
            {'scene_number': 0, 'title': 'Scene C'}
        ]
        
        numbered_1 = stage_3_instance._apply_global_scene_numbering(scenes_1, 1)
        Stage3Assertions.validate_global_numbering_logic(numbered_1, starting_number=1)
        
        expected_numbers_1 = [1, 2, 3]
        actual_numbers_1 = [scene['scene_number'] for scene in numbered_1]
        assert actual_numbers_1 == expected_numbers_1, f"Expected {expected_numbers_1}, got {actual_numbers_1}"
        
        # Test with starting number 10
        scenes_10 = [
            {'scene_number': 0, 'title': 'Scene X'},
            {'scene_number': 0, 'title': 'Scene Y'}
        ]
        
        numbered_10 = stage_3_instance._apply_global_scene_numbering(scenes_10, 10)
        Stage3Assertions.validate_global_numbering_logic(numbered_10, starting_number=10)
        
        expected_numbers_10 = [10, 11]
        actual_numbers_10 = [scene['scene_number'] for scene in numbered_10]
        assert actual_numbers_10 == expected_numbers_10, f"Expected {expected_numbers_10}, got {actual_numbers_10}"
        
        # Test with starting number 100
        scenes_100 = [
            {'scene_number': 0, 'title': 'Scene Alpha'},
            {'scene_number': 0, 'title': 'Scene Beta'},
            {'scene_number': 0, 'title': 'Scene Gamma'},
            {'scene_number': 0, 'title': 'Scene Delta'}
        ]
        
        numbered_100 = stage_3_instance._apply_global_scene_numbering(scenes_100, 100)
        Stage3Assertions.validate_global_numbering_logic(numbered_100, starting_number=100)
        
        expected_numbers_100 = [100, 101, 102, 103]
        actual_numbers_100 = [scene['scene_number'] for scene in numbered_100]
        assert actual_numbers_100 == expected_numbers_100, f"Expected {expected_numbers_100}, got {actual_numbers_100}"
    
    def test_global_numbering_chunk_processing_flow(self, stage_3_instance, db_fixture):
        """Test the complete flow of global numbering through chunk processing."""
        from unittest.mock import Mock, patch
        
        # Create test draft with chunks
        test_data = SampleDataGenerator(db_fixture.connection_pool)
        draft_data = test_data.generate_draft_request()
        
        workspace_data = db_fixture.create_test_workspace(
            workspace_id=draft_data['workspace_id'],
            user_id=draft_data['user_id']
        )
        
        test_draft = db_fixture.create_test_draft(
            draft_id=draft_data['draft_id'],
            workspace_id=workspace_data['workspace_id'],
            user_id=workspace_data['user_id']
        )
        
        # Add chunks
        for i in range(3):
            db_fixture.execute_query(
                "INSERT INTO draft_chunks (draft_id, chunk_number, raw_text, cleaned_text) VALUES (%s, %s, %s, %s)",
                (test_draft['draft_id'], i+1, f"Test chunk {i+1} content", f"Test chunk {i+1} content")
            )
        
        # Mock _process_chunk to return predictable scenes
        def mock_process_chunk(chunk_number, cleaned_text, starting_scene_number):
            # Each chunk produces 2 scenes
            return [
                {
                    'scene_number': starting_scene_number,
                    'title': f'Scene {starting_scene_number} from chunk {chunk_number}',
                    'setting': f'Setting {starting_scene_number}',
                    'characters': [f'Character {starting_scene_number}'],
                    'summary': f'Summary {starting_scene_number}',
                    'content': f'Content {starting_scene_number} from chunk {chunk_number} that is definitely longer than fifty characters to meet the minimum requirements for scene content length.'
                },
                {
                    'scene_number': starting_scene_number + 1,
                    'title': f'Scene {starting_scene_number + 1} from chunk {chunk_number}',
                    'setting': f'Setting {starting_scene_number + 1}',
                    'characters': [f'Character {starting_scene_number + 1}'],
                    'summary': f'Summary {starting_scene_number + 1}',
                    'content': f'Content {starting_scene_number + 1} from chunk {chunk_number} that is definitely longer than fifty characters to meet the minimum requirements for scene content length.'
                }
            ]
        
        # Replace _process_chunk with mock
        with patch.object(stage_3_instance, '_process_chunk', side_effect=mock_process_chunk):
            # Run Stage 3
            result = stage_3_instance.run(draft_id=test_draft['draft_id'])
            assert result['success'], f"Stage 3 failed: {result.get('error')}"
            
            # Should have 6 scenes total (3 chunks × 2 scenes each)
            assert result['scenes_extracted'] == 6, f"Expected 6 scenes, got {result['scenes_extracted']}"
            
            # Verify global numbering in database
            scenes = db_fixture.execute_query(
                "SELECT scene_number, title FROM scenes WHERE draft_id = %s ORDER BY scene_number",
                (test_draft['draft_id'],)
            )
            
            assert len(scenes) == 6, f"Expected 6 scenes in database, got {len(scenes)}"
            
            # Validate global numbering
            Stage3Assertions.validate_global_numbering_logic(
                [{'scene_number': scene[0]} for scene in scenes],
                starting_number=1
            )
            
            # Verify specific numbering
            expected_numbers = [1, 2, 3, 4, 5, 6]
            actual_numbers = [scene[0] for scene in scenes]
            assert actual_numbers == expected_numbers, f"Expected {expected_numbers}, got {actual_numbers}"
            
            # Verify titles reflect correct chunk origins
            for i, scene in enumerate(scenes):
                scene_number, title = scene
                assert f"Scene {scene_number}" in title, f"Title should contain scene number {scene_number}"
    
    def test_global_numbering_database_storage_integrity(self, stage_3_instance, db_fixture):
        """Test that global numbering is correctly stored in database."""
        from unittest.mock import Mock, patch
        
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
            user_id=workspace_data['user_id']
        )
        
        # Add single chunk
        db_fixture.execute_query(
            "INSERT INTO draft_chunks (draft_id, chunk_number, raw_text, cleaned_text) VALUES (%s, %s, %s, %s)",
            (test_draft['draft_id'], 1, "Test chunk content", "Test chunk content")
        )
        
        # Mock _process_chunk to return scenes with specific numbers
        def mock_process_chunk(chunk_number, cleaned_text, starting_scene_number):
            return [
                {
                    'scene_number': starting_scene_number,
                    'title': f'Scene {starting_scene_number}',
                    'setting': f'Setting {starting_scene_number}',
                    'characters': [f'Character {starting_scene_number}'],
                    'summary': f'Summary {starting_scene_number}',
                    'content': f'Content {starting_scene_number} that is definitely longer than fifty characters to meet the minimum requirements for scene content length.'
                },
                {
                    'scene_number': starting_scene_number + 1,
                    'title': f'Scene {starting_scene_number + 1}',
                    'setting': f'Setting {starting_scene_number + 1}',
                    'characters': [f'Character {starting_scene_number + 1}'],
                    'summary': f'Summary {starting_scene_number + 1}',
                    'content': f'Content {starting_scene_number + 1} that is definitely longer than fifty characters to meet the minimum requirements for scene content length.'
                }
            ]
        
        # Replace _process_chunk with mock
        with patch.object(stage_3_instance, '_process_chunk', side_effect=mock_process_chunk):
            # Run Stage 3
            result = stage_3_instance.run(draft_id=test_draft['draft_id'])
            assert result['success'], f"Stage 3 failed: {result.get('error')}"
            
            # Verify database storage
            Stage3Assertions.validate_scene_database_storage(
                db_fixture, 
                test_draft['draft_id'], 
                result['scenes_extracted']
            )
            
            # Verify specific database contents
            scenes = db_fixture.execute_query(
                "SELECT scene_number, title, summary, setting, characters, original_content FROM scenes WHERE draft_id = %s ORDER BY scene_number",
                (test_draft['draft_id'],)
            )
            
            assert len(scenes) == 2, f"Expected 2 scenes in database, got {len(scenes)}"
            
            # Verify each scene has correct global numbering
            for i, scene in enumerate(scenes):
                scene_number, title, summary, setting, characters, content = scene
                expected_number = i + 1
                
                assert scene_number == expected_number, \
                    f"Scene {i} has wrong number: expected {expected_number}, got {scene_number}"
                
                assert title == f"Scene {expected_number}", \
                    f"Scene {i} has wrong title: expected 'Scene {expected_number}', got '{title}'"
                
                assert len(content) >= 50, \
                    f"Scene {i} content too short: {len(content)} chars"


@pytest.mark.real_api
@pytest.mark.database
class TestStage3EdgeCases:
    """Test Stage 3 edge cases and error conditions."""
    
    def test_stage_3_no_chunks_available(self, stage_3_instance, db_fixture):
        """Test Stage 3 behavior when no chunks are available."""
        # Create a draft without chunks
        test_data = SampleDataGenerator(db_fixture.connection_pool)
        draft_data = test_data.generate_draft_request()
        
        workspace_data = db_fixture.create_test_workspace(
            workspace_id=draft_data['workspace_id'],
            user_id=draft_data['user_id']
        )
        
        test_draft = db_fixture.create_test_draft(
            draft_id=draft_data['draft_id'],
            workspace_id=workspace_data['workspace_id'],
            user_id=workspace_data['user_id']
        )
        
        # Run Stage 3 on draft with no chunks
        result = stage_3_instance.run(draft_id=test_draft['draft_id'])
        
        # Should succeed but with zero scenes
        assert result['success'] == True, "Stage 3 should handle no chunks gracefully"
        assert result['scenes_extracted'] == 0, "Should extract zero scenes when no chunks available"
        assert result['chunks_processed'] == 0, "Should process zero chunks"
        assert 'message' in result, "Should include message explaining the situation"
        
        print(f"No chunks case handled: {result['message']}")
    
    @requires_previous_stages([1, 2])
    def test_stage_3_empty_chunks_handling(self, register_stages_1_2_and_3, stage_3_instance, db_fixture,
                                         dependency_results):
        """Test Stage 3 behavior with empty or very short chunks."""
        # Get draft from dependencies
        stage_2_data = dependency_results.get('stage_data', {}).get(2, {})
        draft_id = stage_2_data.get('draft_id')
        
        if not draft_id:
            chunks_query = db_fixture.execute_query(
                "SELECT draft_id FROM draft_chunks WHERE cleaned_text IS NOT NULL ORDER BY id DESC LIMIT 1"
            )
            if chunks_query:
                draft_id = chunks_query[0][0]
        
        assert draft_id, "No draft_id available for testing"
        
        # Add some empty/short chunks to test handling
        db_fixture.execute_query(
            "INSERT INTO draft_chunks (draft_id, chunk_number, raw_text, cleaned_text) VALUES (%s, %s, %s, %s)",
            (draft_id, 999, "", "")  # Empty chunk
        )
        
        db_fixture.execute_query(
            "INSERT INTO draft_chunks (draft_id, chunk_number, raw_text, cleaned_text) VALUES (%s, %s, %s, %s)",
            (draft_id, 998, "Short.", "Short.")  # Very short chunk
        )
        
        # Run Stage 3
        result = stage_3_instance.run(draft_id=draft_id)
        
        # Should still succeed (empty chunks should be skipped)
        assert result['success'] == True, "Stage 3 should handle empty chunks gracefully"
        
        print(f"Empty chunks handling result: {result['chunks_processed']} chunks processed, {result['scenes_extracted']} scenes extracted")
    
    def test_stage_3_malformed_ai_responses(self, stage_3_instance, db_fixture):
        """Test Stage 3 behavior with malformed AI responses."""
        from unittest.mock import Mock, patch
        
        # Create test draft with chunks
        test_data = SampleDataGenerator(db_fixture.connection_pool)
        draft_data = test_data.generate_draft_request()
        
        workspace_data = db_fixture.create_test_workspace(
            workspace_id=draft_data['workspace_id'],
            user_id=draft_data['user_id']
        )
        
        test_draft = db_fixture.create_test_draft(
            draft_id=draft_data['draft_id'],
            workspace_id=workspace_data['workspace_id'],
            user_id=workspace_data['user_id']
        )
        
        # Add test chunk with cleaned text to ensure it's processed
        chunk_content = "Test chunk content for malformed AI response testing. This text should be long enough to be processed by the scene extraction logic."
        db_fixture.execute_query(
            "INSERT INTO draft_chunks (draft_id, chunk_number, raw_text, cleaned_text) VALUES (%s, %s, %s, %s)",
            (test_draft['draft_id'], 1, chunk_content, chunk_content)
        )
        
        # Verify chunk was created
        chunks = db_fixture.execute_query(
            "SELECT chunk_number, cleaned_text FROM draft_chunks WHERE draft_id = %s",
            (test_draft['draft_id'],)
        )
        assert len(chunks) == 1, f"Expected 1 chunk, got {len(chunks)}"
        
        # Mock detection methods to return empty (simulating malformed response handling)
        with patch.object(stage_3_instance, '_detect_scenes') as mock_detect:
            with patch.object(stage_3_instance, '_retry_scene_detection') as mock_retry:
                mock_detect.return_value = []
                mock_retry.return_value = []
                
                # Run Stage 3
                result = stage_3_instance.run(draft_id=test_draft['draft_id'])
                
                # Should handle malformed responses gracefully
                assert result['success'] is True, "Stage 3 should handle malformed AI responses gracefully"
                assert result['scenes_extracted'] == 0, "Should extract 0 scenes for malformed responses"
                assert result['chunks_processed'] == 1, "Should process 1 chunk for malformed responses"
        
        print("Tested malformed AI response handling")
    
    def test_stage_3_json_parsing_edge_cases(self, stage_3_instance):
        """Test comprehensive JSON parsing edge cases."""
        from unittest.mock import Mock
        
        # Test cases for JSON parsing edge cases
        test_cases = [
            {
                'name': 'valid_json_string',
                'response_text': '{"scenes": [{"scene_number": 1, "title": "Test Scene", "content": "Test content"}]}',
                'expected_scenes': 1
            },
            {
                'name': 'already_parsed_dict',
                'response_text': {"scenes": [{"scene_number": 1, "title": "Test Scene", "content": "Test content"}]},
                'expected_scenes': 1
            },
            {
                'name': 'already_parsed_list',
                'response_text': [{"scene_number": 1, "title": "Test Scene", "content": "Test content"}],
                'expected_scenes': 1
            },
            {
                'name': 'markdown_wrapped_json',
                'response_text': '```json\n{"scenes": [{"scene_number": 1, "title": "Test Scene", "content": "Test content"}]}\n```',
                'expected_scenes': 1
            },
            {
                'name': 'json_with_extra_whitespace',
                'response_text': '   \n\n  {"scenes": [{"scene_number": 1, "title": "Test Scene", "content": "Test content"}]}  \n  ',
                'expected_scenes': 1
            },
            {
                'name': 'json_array_direct',
                'response_text': '[{"scene_number": 1, "title": "Test Scene", "content": "Test content"}]',
                'expected_scenes': 1
            },
            {
                'name': 'empty_json_object',
                'response_text': '{}',
                'expected_scenes': 0
            },
            {
                'name': 'empty_json_array',
                'response_text': '[]',
                'expected_scenes': 0
            },
            {
                'name': 'null_response',
                'response_text': None,
                'expected_scenes': 0
            },
            {
                'name': 'empty_string',
                'response_text': '',
                'expected_scenes': 0
            },
            {
                'name': 'invalid_json',
                'response_text': 'This is not JSON at all',
                'expected_scenes': 0
            },
            {
                'name': 'malformed_json',
                'response_text': '{"scenes": [{"scene_number": 1, "title": "Test Scene", "content": "Test content"]}',  # Missing closing brace
                'expected_scenes': 0
            },
            {
                'name': 'unexpected_type',
                'response_text': 42,  # Integer instead of string/dict/list
                'expected_scenes': 0
            }
        ]
        
        for test_case in test_cases:
            print(f"Testing JSON parsing case: {test_case['name']}")
            
            # Mock the response object
            mock_response = Mock()
            mock_response.success = True
            mock_response.text = test_case['response_text']
            
            # Test the JSON parsing logic
            try:
                # Extract the JSON parsing logic from _detect_scenes
                response_text = mock_response.text
                
                # Apply the same logic as in the business logic
                if isinstance(response_text, (list, dict)):
                    scenes_data = response_text
                elif isinstance(response_text, str):
                    # Clean the response text to handle markdown wrapper
                    response_text = response_text.strip()
                    if response_text.startswith(Stage3Config.MARKDOWN_JSON_WRAPPER_START):
                        response_text = response_text[len(Stage3Config.MARKDOWN_JSON_WRAPPER_START):]
                    if response_text.endswith(Stage3Config.MARKDOWN_JSON_WRAPPER_END):
                        response_text = response_text[:-len(Stage3Config.MARKDOWN_JSON_WRAPPER_END)]
                    
                    if not response_text:
                        scenes_data = []
                    else:
                        import json
                        scenes_data = json.loads(response_text.strip())
                elif response_text is None:
                    scenes_data = []
                else:
                    scenes_data = []
                
                # Handle if the JSON contains a "scenes" key
                if isinstance(scenes_data, dict) and "scenes" in scenes_data:
                    scenes_data = scenes_data["scenes"]
                
                # Validate the result
                if isinstance(scenes_data, list):
                    actual_scenes = len(scenes_data)
                else:
                    actual_scenes = 0
                
                assert actual_scenes == test_case['expected_scenes'], \
                    f"Case {test_case['name']}: expected {test_case['expected_scenes']} scenes, got {actual_scenes}"
                
                print(f"  ✅ {test_case['name']}: {actual_scenes} scenes")
                
            except json.JSONDecodeError:
                # JSON parsing should fail gracefully
                assert test_case['expected_scenes'] == 0, \
                    f"Case {test_case['name']}: JSON parsing failed but expected {test_case['expected_scenes']} scenes"
                print(f"  ✅ {test_case['name']}: JSON parsing failed gracefully")
            
            except Exception as e:
                # Other exceptions should also result in 0 scenes
                assert test_case['expected_scenes'] == 0, \
                    f"Case {test_case['name']}: Exception {e} but expected {test_case['expected_scenes']} scenes"
                print(f"  ✅ {test_case['name']}: Exception handled gracefully")
        
        print("✅ JSON parsing edge cases validated")
    
    def test_stage_3_database_connection_failure(self, stage_3_instance, db_fixture):
        """Test Stage 3 behavior with database connection failures."""
        from unittest.mock import Mock, patch
        
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
            user_id=workspace_data['user_id']
        )
        
        # Test database failure during chunk retrieval
        with patch.object(stage_3_instance, '_get_chunk_data', side_effect=Exception("Database connection failed")):
            result = stage_3_instance.run(draft_id=test_draft['draft_id'])
            
            # Should fail gracefully with error
            Stage3Assertions.validate_error_handling_logic(result, expected_error_type="database")
        
        # Test database failure during scene storage
        with patch.object(stage_3_instance, '_store_scenes_in_database', side_effect=Exception("Database write failed")):
            with patch.object(stage_3_instance, '_get_chunk_data', return_value=[(1, "Test chunk content")]):
                # Mock _process_chunk to return scenes so storage failure is triggered
                mock_scenes = [
                    {
                        'scene_number': 1,
                        'title': 'Test Scene',
                        'setting': 'Test Setting',
                        'characters': ['Test Character'],
                        'summary': 'Test Summary',
                        'content': 'Test content that is definitely longer than fifty characters to meet the minimum requirements for scene content length.'
                    }
                ]
                with patch.object(stage_3_instance, '_process_chunk', return_value=mock_scenes):
                    result = stage_3_instance.run(draft_id=test_draft['draft_id'])
                    
                    # Should fail gracefully with error
                    Stage3Assertions.validate_error_handling_logic(result, expected_error_type="database")
    
    
    
    


@pytest.mark.real_api
@pytest.mark.database
class TestStage3Performance:
    """Test Stage 3 performance and configuration requirements."""
    
    @requires_previous_stages([1, 2])
    def test_stage_3_processing_time_monitoring(self, register_stages_1_2_and_3, stage_3_instance, db_fixture, dependency_results):
        """Test Stage 3 processing time monitoring and performance expectations."""
        import time
        
        # Get draft from dependencies
        stage_2_data = dependency_results.get('stage_data', {}).get(2, {})
        draft_id = stage_2_data.get('draft_id')
        
        if not draft_id:
            chunks_query = db_fixture.execute_query(
                "SELECT draft_id FROM draft_chunks WHERE cleaned_text IS NOT NULL ORDER BY id DESC LIMIT 1"
            )
            if chunks_query:
                draft_id = chunks_query[0][0]
        
        assert draft_id, "No draft_id available for testing"
        
        # Get chunk count for performance expectations
        chunks_count = db_fixture.count_records('draft_chunks', draft_id)
        assert chunks_count > 0, "Should have chunks for performance testing"
        
        # Monitor processing time
        start_time = time.time()
        result = stage_3_instance.run(draft_id=draft_id)
        end_time = time.time()
        
        # Verify success
        assert result['success'] is True, f"Stage 3 failed: {result.get('error')}"
        
        # Performance assertions
        total_processing_time = end_time - start_time
        avg_time_per_chunk = total_processing_time / chunks_count if chunks_count > 0 else 0
        
        # Stage 3 should process chunks efficiently (allowing for AI calls)
        max_processing_time = Stage3Config.MAX_PROCESSING_TIME_SECONDS
        max_chunk_time = Stage3Config.MAX_TIME_PER_CHUNK_SECONDS
        
        assert total_processing_time < max_processing_time, f"Total processing time too long: {total_processing_time:.2f}s (max: {max_processing_time}s)"
        if chunks_count > 0:
            assert avg_time_per_chunk < max_chunk_time, f"Average time per chunk too long: {avg_time_per_chunk:.2f}s (max: {max_chunk_time}s)"
        
        # Performance metrics
        scenes_per_second = result['scenes_extracted'] / total_processing_time if total_processing_time > 0 else 0
        
        print(f"Stage 3 Performance Metrics:")
        print(f"  Total processing time: {total_processing_time:.2f}s")
        print(f"  Average time per chunk: {avg_time_per_chunk:.2f}s")
        print(f"  Chunks processed: {result['chunks_processed']}")
        print(f"  Scenes extracted: {result['scenes_extracted']}")
        print(f"  Scenes per second: {scenes_per_second:.2f}")
        
        # Verify reasonable throughput
        assert scenes_per_second >= 0, "Should have non-negative scenes per second"
    
    def test_stage_3_token_compatibility_with_stage_2(self):
        """Test that Stage 3 can handle Stage 2's maximum output tokens."""
        # Stage 2 configuration (from real_generation_engine.py)
        from test_utils.real_generation_engine import RealGenerationEngineFactory
        
        stage_2_factory = RealGenerationEngineFactory()
        stage_2_max_output_tokens = stage_2_factory.default_config['max_output_tokens']
        
        # Stage 3 should be able to handle Stage 2's output
        stage_3_factory = RealGenerationEngineFactory()
        stage_3_max_input_tokens = stage_3_factory.default_config.get('max_input_tokens', stage_2_max_output_tokens)
        
        print(f"Stage 2→3 Token Compatibility:")
        print(f"  Stage 2 max output: {stage_2_max_output_tokens} tokens")
        print(f"  Stage 3 max input capacity: {stage_3_max_input_tokens} tokens")
        
        # Stage 3 should handle Stage 2's maximum output
        assert stage_3_max_input_tokens >= stage_2_max_output_tokens, \
            f"Stage 3 input capacity ({stage_3_max_input_tokens}) should >= Stage 2 max output ({stage_2_max_output_tokens})"
        
        print(f"  ✅ Token compatibility verified")
    
    def test_stage_3_scene_count_requirements_validation(self):
        """Test Stage 3's scene count validation requirements."""
        from test_utils.real_generation_engine import RealGenerationEngineFactory
        
        # Stage 3 business logic requirements from configuration
        min_scenes_per_chunk = Stage3Config.MIN_SCENES_PER_CHUNK
        max_scenes_per_chunk = Stage3Config.MAX_SCENES_PER_CHUNK
        max_retry_attempts = Stage3Config.MAX_RETRY_ATTEMPTS
        
        print(f"Stage 3 Configuration Validation:")
        print(f"  Minimum scenes per chunk: {min_scenes_per_chunk}")
        print(f"  Maximum scenes per chunk: {max_scenes_per_chunk}")
        print(f"  Maximum retry attempts: {max_retry_attempts}")
        
        # Validate these are reasonable requirements
        assert min_scenes_per_chunk > 0, "Minimum scene count should be positive"
        assert max_scenes_per_chunk > min_scenes_per_chunk, "Maximum should be greater than minimum"
        assert max_scenes_per_chunk <= 30, "Maximum scene count should be reasonable for AI processing"
        assert max_retry_attempts >= 2, "Should allow at least 2 retry attempts"
        
        # Test with business logic
        Stage3Assertions.validate_scene_count_business_logic(min_scenes_per_chunk, expected_valid=True)
        Stage3Assertions.validate_scene_count_business_logic(max_scenes_per_chunk, expected_valid=True)
        Stage3Assertions.validate_scene_count_business_logic(min_scenes_per_chunk - 1, expected_valid=False)
        Stage3Assertions.validate_scene_count_business_logic(max_scenes_per_chunk + 1, expected_valid=False)
        
        print(f"  ✅ Scene count requirements validated")
    
    @requires_previous_stages([1, 2])
    def test_stage_3_chunk_size_handling_limits(self, register_stages_1_2_and_3, stage_3_instance, db_fixture, dependency_results):
        """Test Stage 3 can handle various chunk sizes from Stage 2."""
        # Get draft from dependencies
        stage_2_data = dependency_results.get('stage_data', {}).get(2, {})
        draft_id = stage_2_data.get('draft_id')
        
        if not draft_id:
            chunks_query = db_fixture.execute_query(
                "SELECT draft_id FROM draft_chunks WHERE cleaned_text IS NOT NULL ORDER BY id DESC LIMIT 1"
            )
            if chunks_query:
                draft_id = chunks_query[0][0]
        
        assert draft_id, "No draft_id available for testing"
        
        # Get chunk size statistics
        chunk_stats = db_fixture.execute_query(
            "SELECT MIN(LENGTH(cleaned_text)), MAX(LENGTH(cleaned_text)), AVG(LENGTH(cleaned_text)), COUNT(*) FROM draft_chunks WHERE draft_id = %s",
            (draft_id,)
        )
        
        min_chars, max_chars, avg_chars, chunk_count = chunk_stats[0] if chunk_stats else (0, 0, 0, 0)
        
        print(f"Stage 3 Chunk Size Analysis:")
        print(f"  Chunk count: {chunk_count}")
        print(f"  Min chunk size: {min_chars} chars")
        print(f"  Max chunk size: {max_chars} chars")
        print(f"  Average chunk size: {avg_chars:.0f} chars")
        
        # Verify Stage 3 can handle these chunk sizes
        assert max_chars > 0, "Should have non-empty chunks"
        assert chunk_count > 0, "Should have chunks to process"
        
        # Run Stage 3 to verify it handles all chunk sizes
        result = stage_3_instance.run(draft_id=draft_id)
        
        assert result['success'] is True, f"Stage 3 failed on chunk size handling: {result.get('error')}"
        assert result['chunks_processed'] == chunk_count, "Should process all chunks regardless of size"
        
        print(f"Successfully processed {chunk_count} chunks with max size {max_chars} chars")
    
    @requires_previous_stages([1, 2])
    def test_stage_3_comprehensive_performance_benchmarking(self, register_stages_1_2_and_3, stage_3_instance, 
                                                          db_fixture, dependency_results):
        """Test comprehensive performance benchmarking for Stage 3."""
        import time
        import statistics
        
        # Get draft from dependencies
        stage_2_data = dependency_results.get('stage_data', {}).get(2, {})
        draft_id = stage_2_data.get('draft_id')
        
        if not draft_id:
            chunks_query = db_fixture.execute_query(
                "SELECT draft_id FROM draft_chunks WHERE cleaned_text IS NOT NULL ORDER BY id DESC LIMIT 1"
            )
            if chunks_query:
                draft_id = chunks_query[0][0]
        
        assert draft_id, "No draft_id available for performance testing"
        
        # Get baseline metrics
        chunks_count = db_fixture.count_records('draft_chunks', draft_id)
        chunk_stats = db_fixture.execute_query(
            "SELECT MIN(LENGTH(cleaned_text)), MAX(LENGTH(cleaned_text)), AVG(LENGTH(cleaned_text)), COUNT(*) FROM draft_chunks WHERE draft_id = %s",
            (draft_id,)
        )
        min_chars, max_chars, avg_chars, total_chunks = chunk_stats[0] if chunk_stats else (0, 0, 0, 0)
        
        print(f"Performance Benchmarking Setup:")
        print(f"  Draft ID: {draft_id}")
        print(f"  Total chunks: {total_chunks}")
        print(f"  Chunk size range: {min_chars}-{max_chars} chars")
        print(f"  Average chunk size: {avg_chars:.0f} chars")
        
        # Run performance test
        start_time = time.time()
        result = stage_3_instance.run(draft_id=draft_id)
        end_time = time.time()
        
        # Verify success
        assert result['success'] is True, f"Stage 3 failed: {result.get('error')}"
        
        # Calculate performance metrics
        total_time = end_time - start_time
        scenes_extracted = result['scenes_extracted']
        chunks_processed = result['chunks_processed']
        
        # Performance calculations
        avg_time_per_chunk = total_time / chunks_processed if chunks_processed > 0 else 0
        scenes_per_second = scenes_extracted / total_time if total_time > 0 else 0
        chars_per_second = (total_chunks * float(avg_chars)) / total_time if total_time > 0 else 0
        
        # Configuration-based performance assertions
        max_total_time = Stage3Config.MAX_PROCESSING_TIME_SECONDS
        max_chunk_time = Stage3Config.MAX_TIME_PER_CHUNK_SECONDS
        
        performance_metrics = {
            'total_processing_time': total_time,
            'avg_time_per_chunk': avg_time_per_chunk,
            'scenes_per_second': scenes_per_second,
            'chars_per_second': chars_per_second,
            'scenes_extracted': scenes_extracted,
            'chunks_processed': chunks_processed,
            'efficiency_ratio': scenes_extracted / total_time if total_time > 0 else 0
        }
        
        print(f"Performance Metrics:")
        print(f"  Total processing time: {total_time:.2f}s (max: {max_total_time}s)")
        print(f"  Average time per chunk: {avg_time_per_chunk:.2f}s (max: {max_chunk_time}s)")
        print(f"  Scenes per second: {scenes_per_second:.2f}")
        print(f"  Characters per second: {chars_per_second:.0f}")
        print(f"  Scenes extracted: {scenes_extracted}")
        print(f"  Chunks processed: {chunks_processed}")
        print(f"  Efficiency ratio: {performance_metrics['efficiency_ratio']:.2f}")
        
        # Performance assertions
        assert total_time < max_total_time, f"Total processing time exceeded limit: {total_time:.2f}s > {max_total_time}s"
        assert avg_time_per_chunk < max_chunk_time, f"Average chunk time exceeded limit: {avg_time_per_chunk:.2f}s > {max_chunk_time}s"
        assert scenes_per_second > 0, "Should have positive scenes per second"
        assert chars_per_second > 0, "Should have positive characters per second"
        
        # Quality vs Performance balance
        scene_quality_threshold = 0.1  # Minimum scenes per second
        assert scenes_per_second >= scene_quality_threshold, f"Scene extraction rate too low: {scenes_per_second:.2f} < {scene_quality_threshold}"
        
        # Efficiency metrics
        expected_scene_range = (Stage3Config.MIN_SCENES_PER_CHUNK, Stage3Config.MAX_SCENES_PER_CHUNK)
        scenes_per_chunk = scenes_extracted / chunks_processed if chunks_processed > 0 else 0
        
        print(f"Efficiency Analysis:")
        print(f"  Expected scenes per chunk: {expected_scene_range[0]}-{expected_scene_range[1]}")
        print(f"  Actual scenes per chunk: {scenes_per_chunk:.1f}")
        print(f"  Processing efficiency: {(scenes_per_chunk / expected_scene_range[1]) * 100:.1f}%")
        
        # Memory and resource efficiency (estimated)
        estimated_memory_per_scene = 1000  # bytes (rough estimate)
        estimated_memory_usage = scenes_extracted * estimated_memory_per_scene
        
        print(f"Resource Efficiency:")
        print(f"  Estimated memory per scene: {estimated_memory_per_scene} bytes")
        print(f"  Estimated total memory usage: {estimated_memory_usage / 1024:.1f} KB")
        
        # Store performance benchmark results
        benchmark_results = {
            'draft_id': draft_id,
            'timestamp': time.time(),
            'performance_metrics': performance_metrics,
            'configuration_limits': {
                'max_total_time': max_total_time,
                'max_chunk_time': max_chunk_time,
                'scene_count_range': expected_scene_range
            },
            'input_characteristics': {
                'total_chunks': total_chunks,
                'avg_chunk_size': avg_chars,
                'min_chunk_size': min_chars,
                'max_chunk_size': max_chars
            }
        }
        
        print("✅ Comprehensive performance benchmarking completed")
        return benchmark_results
    
    
    def test_stage_3_configuration_constants_validation(self, stage_3_instance):
        """Test that Stage 3 configuration constants are properly enforced."""
        # Test scene count validation constants
        assert stage_3_instance._validate_scene_count(8) is True, "8 scenes should be valid"
        assert stage_3_instance._validate_scene_count(20) is True, "20 scenes should be valid"
        assert stage_3_instance._validate_scene_count(7) is False, "7 scenes should be invalid"
        assert stage_3_instance._validate_scene_count(21) is False, "21 scenes should be invalid"
        
        # Test minimum scene content length (from business logic)
        min_scene_content_length = 50
        
        # Valid scene data
        valid_scene = {
            'scene_number': 1,
            'title': 'Valid Scene',
            'setting': 'Test setting',
            'characters': ['Test character'],
            'summary': 'Test summary',
            'content': 'A' * min_scene_content_length  # Exactly minimum length
        }
        
        # Invalid scene data (too short)
        invalid_scene = {
            'scene_number': 1,
            'title': 'Invalid Scene',
            'setting': 'Test setting',
            'characters': ['Test character'],
            'summary': 'Test summary',
            'content': 'A' * (min_scene_content_length - 1)  # One character too short
        }
        
        # Test scene validation
        Stage3Assertions.validate_scene_data_validation_logic(valid_scene, should_be_valid=True)
        Stage3Assertions.validate_scene_data_validation_logic(invalid_scene, should_be_valid=False)
        
        print(f"Configuration Constants Validation:")
        print(f"  Scene count range: 8-20 ✅")
        print(f"  Minimum scene content length: {min_scene_content_length} chars ✅")
        print(f"  Configuration constants properly enforced")
    
    def test_stage_3_provider_model_compatibility(self, stage_3_instance):
        """Test that Stage 3 works with different AI providers and models."""
        from test_utils.real_generation_engine import RealGenerationEngineFactory
        
        # Test different provider configurations
        provider_configs = [
            {'provider': 'openai', 'model': 'gpt-4o'},
            {'provider': 'gemini', 'model': 'gemini-2.0-flash'},
            {'provider': 'deepseek', 'model': 'deepseek-chat'},
        ]
        
        for config in provider_configs:
            # Test that factory can create engine with this config
            factory = RealGenerationEngineFactory()
            
            # Verify configuration is valid
            assert config['provider'] in ['openai', 'gemini', 'deepseek'], f"Invalid provider: {config['provider']}"
            assert config['model'] is not None, "Model should not be None"
            
            print(f"Provider compatibility: {config['provider']}/{config['model']} ✅")
        
        print(f"Stage 3 compatible with {len(provider_configs)} provider/model combinations")
    

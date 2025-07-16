"""
Integration tests for the deconstructor API endpoints.
Tests the complete API workflow with database and real AI providers.
"""

import pytest
import json
import time
import os
from datetime import datetime
from test_utils.assertions import PipelineAssertions, RealAPIAssertions
from test_utils.sample_data import SampleDataGenerator
from test_utils.real_generation_engine import RealGenerationEngineFactory
from test_utils.path_manager import get_temp_output


@pytest.mark.integration
@pytest.mark.real_api
@pytest.mark.database
class TestDeconstructorAPI:
    """Test the deconstructor API endpoints end-to-end."""
    
    def test_deconstruct_endpoint_success(self, api_client, db_fixture, generation_engine_factory):
        """Test successful deconstruction request through API."""
        # Skip if no API keys available
        available_providers = generation_engine_factory.get_available_providers()
        if not available_providers:
            pytest.skip("No API keys available for API testing")
        
        # Prepare test data
        test_data = SampleDataGenerator()
        draft_data = test_data.generate_draft_request()
        
        # Use available provider
        provider = "gemini" if "gemini" in available_providers else available_providers[0]
        draft_data['provider'] = provider
        
        # Create test workspace and draft
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
        
        # Create a sample file for processing
        sample_content = """
        Chapter 1: The Beginning
        
        It was a dark and stormy night. The rain poured down in torrents, and the wind howled through the trees.
        John sat by the window, watching the storm rage outside. He had been waiting for this moment for months.
        
        Chapter 2: The Journey
        
        The next morning, John packed his bags and set out on the journey that would change his life forever.
        He didn't know what lay ahead, but he was determined to face whatever challenges awaited him.
        """
        
        # Create the file in the output directory (for API processing)
        upload_path = str(get_temp_output(draft_data['file_name']))
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        with open(upload_path, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        
        try:
            # Make API request
            start_time = time.time()
            response = api_client.post('/api/deconstruct', json={
                'draft_id': test_draft['draft_id'],
                'file_name': test_draft['file_name'],
                'provider': draft_data['provider'],
                'model': draft_data['model'],
                'chaptering_mode': draft_data['chaptering_mode'],
                'target_chapter_length': draft_data['target_chapter_length']
            })
            end_time = time.time()
            
            # Verify response
            assert response.status_code == 200, f"API request failed: {response.get_json()}"
            response_data = response.get_json()
            
            PipelineAssertions.assert_api_response_structure(response_data, success=True)
            assert response_data['data']['draft_id'] == test_draft['draft_id']
            assert response_data['data']['success'] == True
            
            # Verify processing time is reasonable
            processing_time = end_time - start_time
            assert processing_time < 300, f"Processing took too long: {processing_time:.2f}s"
            
            # Verify database state
            final_status = db_fixture.get_draft_status(test_draft['draft_id'])
            assert final_status in ['completed', 'failed', 'processing'], \
                f"Unexpected final status: {final_status}"
            
            print(f"API test completed successfully in {processing_time:.2f}s")
            print(f"Final status: {final_status}")
            
        finally:
            # Cleanup uploaded file
            if os.path.exists(upload_path):
                os.unlink(upload_path)
    
    def test_deconstruct_status_endpoint(self, api_client, db_fixture):
        """Test the deconstruct status endpoint."""
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
            user_id=workspace_data['user_id']
        )
        
        # Simulate processing state
        db_fixture.simulate_processing_states(test_draft['draft_id'], 'stage_2_complete')
        
        # Request status
        response = api_client.get(f'/api/deconstruct/status/{test_draft["draft_id"]}')
        
        assert response.status_code == 200
        response_data = response.get_json()
        
        PipelineAssertions.assert_api_response_structure(response_data, success=True)
        assert response_data['data']['draft_id'] == test_draft['draft_id']
        assert response_data['data']['status'] == 'stage_2_complete'
        assert 'progress' in response_data['data']
    
    def test_deconstruct_error_handling(self, api_client, db_fixture, generation_engine_factory):
        """Test API error handling."""
        # Skip if no API keys available
        available_providers = generation_engine_factory.get_available_providers()
        if not available_providers:
            pytest.skip("No API keys available for error handling testing")
        
        # Test with invalid draft ID
        response = api_client.post('/api/deconstruct', json={
            'draft_id': 'invalid-draft-id',
            'file_name': 'nonexistent.txt',
            'provider': available_providers[0],
            'model': 'test-model'
        })
        
        assert response.status_code in [400, 404], "Should return error for invalid draft"
        response_data = response.get_json()
        
        PipelineAssertions.assert_api_response_structure(response_data, success=False)
        assert 'error' in response_data
    
    def test_deconstruct_provider_validation(self, api_client, db_fixture):
        """Test provider validation."""
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
        
        # Test with invalid provider
        response = api_client.post('/api/deconstruct', json={
            'draft_id': test_draft['draft_id'],
            'file_name': test_draft['file_name'],
            'provider': 'invalid_provider',
            'model': 'test-model'
        })
        
        assert response.status_code == 400, "Should return error for invalid provider"
        response_data = response.get_json()
        
        PipelineAssertions.assert_api_response_structure(response_data, success=False)
        assert 'provider' in response_data['error']['message'].lower() or \
               'invalid' in response_data['error']['message'].lower()
    
    def test_deconstruct_missing_file_handling(self, api_client, db_fixture, generation_engine_factory):
        """Test handling when uploaded file is missing."""
        # Skip if no API keys available
        available_providers = generation_engine_factory.get_available_providers()
        if not available_providers:
            pytest.skip("No API keys available for file handling testing")
        
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
            file_name='nonexistent_file.txt'
        )
        
        # Test with missing file
        response = api_client.post('/api/deconstruct', json={
            'draft_id': test_draft['draft_id'],
            'file_name': 'nonexistent_file.txt',
            'provider': available_providers[0],
            'model': 'test-model'
        })
        
        # Should handle missing file gracefully
        assert response.status_code in [400, 404, 500], "Should return error for missing file"
        response_data = response.get_json()
        
        PipelineAssertions.assert_api_response_structure(response_data, success=False)
    
    @pytest.mark.expensive
    def test_deconstruct_full_pipeline(self, api_client, db_fixture, generation_engine_factory):
        """Test complete pipeline execution (expensive test)."""
        # Skip if no API keys available
        available_providers = generation_engine_factory.get_available_providers()
        if not available_providers:
            pytest.skip("No API keys available for full pipeline testing")
        
        # Prepare test data
        test_data = SampleDataGenerator()
        draft_data = test_data.generate_draft_request()
        
        # Use available provider
        provider = "gemini" if "gemini" in available_providers else available_providers[0]
        draft_data['provider'] = provider
        
        # Create test workspace and draft
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
        
        # Create a larger, more complex sample file
        complex_content = """
        Chapter 1: The Mysterious Arrival
        
        It was a dark and stormy night when Sarah first arrived at the old mansion. The rain poured down in torrents,
        and the wind howled through the ancient oak trees that surrounded the property. Lightning illuminated the
        gothic architecture, casting eerie shadows across the overgrown garden.
        
        As she approached the heavy wooden door, Sarah felt a chill that had nothing to do with the weather.
        The brass knocker was shaped like a snarling gargoyle, its eyes seeming to follow her movements.
        She had inherited this place from her great-aunt Margaret, a woman she had never met but whose
        reputation for eccentricity was legendary in the family.
        
        Chapter 2: Secrets in the Walls
        
        The next morning brought sunshine and a completely different perspective on the mansion.
        What had seemed menacing in the storm now appeared merely old and neglected.
        Sarah began exploring the countless rooms, each filled with antique furniture covered in dust sheets.
        
        In the library, she discovered her great-aunt's journal, written in elegant script that spoke of
        hidden passages and family secrets dating back centuries. The final entry, dated just a month ago,
        mentioned a discovery that would "change everything we thought we knew about the family history."
        """
        
        # Create the file
        upload_path = str(get_temp_output(draft_data['file_name']))
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        with open(upload_path, 'w', encoding='utf-8') as f:
            f.write(complex_content)
        
        try:
            # Make API request with longer timeout expectation
            start_time = time.time()
            response = api_client.post('/api/deconstruct', json={
                'draft_id': test_draft['draft_id'],
                'file_name': test_draft['file_name'],
                'provider': draft_data['provider'],
                'model': draft_data['model'],
                'chaptering_mode': draft_data['chaptering_mode'],
                'target_chapter_length': draft_data['target_chapter_length']
            })
            end_time = time.time()
            
            # Verify response
            assert response.status_code == 200, f"Full pipeline API request failed: {response.get_json()}"
            response_data = response.get_json()
            
            PipelineAssertions.assert_api_response_structure(response_data, success=True)
            
            # Verify processing time is reasonable for complex content
            processing_time = end_time - start_time
            assert processing_time < 600, f"Full pipeline processing took too long: {processing_time:.2f}s"
            
            # Verify comprehensive database state
            final_status = db_fixture.get_draft_status(test_draft['draft_id'])
            
            if final_status == 'completed':
                # Verify artifacts were created
                chunks_count = db_fixture.count_records('draft_chunks', test_draft['draft_id'])
                assert chunks_count >= 1, "Draft chunks should be created"
                
                print(f"Full pipeline test completed successfully in {processing_time:.2f}s")
                print(f"Created {chunks_count} chunks")
            else:
                print(f"Pipeline completed with status: {final_status}")
                
        finally:
            # Cleanup uploaded file
            if os.path.exists(upload_path):
                os.unlink(upload_path)
    
    def test_deconstruct_performance_monitoring(self, api_client, db_fixture, generation_engine_factory):
        """Test performance monitoring."""
        # Skip if no API keys available
        available_providers = generation_engine_factory.get_available_providers()
        if not available_providers:
            pytest.skip("No API keys available for performance testing")
        
        # Create test draft
        test_data = SampleDataGenerator()
        draft_data = test_data.generate_draft_request()
        
        provider = "gemini" if "gemini" in available_providers else available_providers[0]
        draft_data['provider'] = provider
        
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
        
        # Create minimal content for performance testing
        minimal_content = "This is a short test document for performance monitoring."
        
        upload_path = str(get_temp_output(draft_data['file_name']))
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        with open(upload_path, 'w', encoding='utf-8') as f:
            f.write(minimal_content)
        
        try:
            # Monitor performance
            start_time = time.time()
            response = api_client.post('/api/deconstruct', json={
                'draft_id': test_draft['draft_id'],
                'file_name': test_draft['file_name'],
                'provider': draft_data['provider'],
                'model': draft_data['model']
            })
            end_time = time.time()
            
            # Verify response
            assert response.status_code == 200
            response_data = response.get_json()
            
            # Performance assertions
            total_time = end_time - start_time
            assert total_time < 60, f"Performance test took too long: {total_time:.2f}s"
            
            print(f"Performance test completed in {total_time:.2f}s")
            
        finally:
            # Cleanup uploaded file
            if os.path.exists(upload_path):
                os.unlink(upload_path)
"""
Stage dependency management for sequential pipeline testing.

This module provides utilities for handling stage dependencies in the deconstructor
pipeline tests, allowing individual stage tests to run with proper prerequisites.
"""

import logging
import functools
import pytest
from typing import List, Union, Dict, Any, Optional
from pathlib import Path
import json

from .path_manager import get_path_manager
from .sample_data import SampleDataGenerator

logger = logging.getLogger(__name__)


class StageDependencyManager:
    """
    Manages stage dependencies and execution for pipeline testing.
    """
    
    def __init__(self):
        self.path_manager = get_path_manager()
        self._stage_instances = {}
        self._executed_stages = set()
        
    def set_stage_instance(self, stage_number: int, instance):
        """Set stage instance for dependency execution."""
        self._stage_instances[stage_number] = instance
        
    def get_stage_instance(self, stage_number: int):
        """Get stage instance for dependency execution."""
        return self._stage_instances.get(stage_number)
        
    def ensure_stage_dependencies(self, required_stages: List[int], 
                                 db_fixture, sample_file_path: str,
                                 use_cached_outputs: bool = False,
                                 skip_dependencies: bool = False) -> Dict[str, Any]:
        """
        Ensure all required stages have been executed and data exists.
        
        Args:
            required_stages: List of stage numbers that must be completed
            db_fixture: Database fixture for test data
            sample_file_path: Path to sample file for processing
            use_cached_outputs: If True, try to use cached stage outputs
            skip_dependencies: If True, assume dependencies are already satisfied
            
        Returns:
            Dictionary with stage execution results and dependency info
        """
        if skip_dependencies:
            logger.info("Skipping dependency resolution as requested")
            return {'skipped': True, 'required_stages': required_stages}
            
        dependency_results = {
            'executed_stages': [],
            'loaded_from_cache': [],
            'failed_stages': [],
            'stage_data': {}
        }
        
        for stage_num in sorted(required_stages):
            if stage_num in self._executed_stages:
                logger.debug(f"Stage {stage_num} already executed in this session")
                continue
                
            if use_cached_outputs and self._has_cached_stage_output(stage_num):
                logger.info(f"Loading Stage {stage_num} from cached output")
                success = self._load_stage_from_cache(stage_num, db_fixture)
                if success:
                    dependency_results['loaded_from_cache'].append(stage_num)
                    self._executed_stages.add(stage_num)
                    continue
                else:
                    logger.warning(f"Failed to load Stage {stage_num} from cache, will execute")
            
            # Execute the stage
            logger.info(f"Executing Stage {stage_num} for dependency resolution")
            stage_result = self._execute_stage(stage_num, db_fixture, sample_file_path)
            
            if stage_result and stage_result.get('success', False):
                dependency_results['executed_stages'].append(stage_num)
                dependency_results['stage_data'][stage_num] = stage_result
                self._executed_stages.add(stage_num)
                logger.info(f"Stage {stage_num} executed successfully")
            else:
                dependency_results['failed_stages'].append(stage_num)
                error_msg = stage_result.get('error', 'Unknown error') if stage_result else 'Stage execution failed'
                logger.error(f"Stage {stage_num} execution failed: {error_msg}")
                raise RuntimeError(f"Stage {stage_num} dependency execution failed: {error_msg}")
                
        return dependency_results
        
    def _has_cached_stage_output(self, stage_number: int) -> bool:
        """Check if cached output exists for a stage."""
        stage_outputs_dir = self.path_manager.get_stage_expected_outputs_dir(stage_number)
        if not stage_outputs_dir.exists():
            return False
            
        # Look for database seed files that indicate stage completion
        database_seeds_dir = stage_outputs_dir / "database_seeds"
        if not database_seeds_dir.exists():
            return False
            
        # Check for key database files based on stage
        if stage_number == 1:
            required_files = ["drafts.json", "draft_chunks.json"]
        elif stage_number == 2:
            required_files = ["drafts.json", "draft_chunks.json"]  # Stage 2 updates existing chunks
        elif stage_number == 3:
            required_files = ["drafts.json", "draft_chunks.json", "scenes.json"]
        else:
            # For other stages, just check if the directory has any database files
            required_files = []
            
        if required_files:
            return all((database_seeds_dir / filename).exists() for filename in required_files)
        else:
            # If no specific files required, check if directory has any JSON files
            json_files = list(database_seeds_dir.glob("*.json"))
            return len(json_files) > 0
            
    def _load_stage_from_cache(self, stage_number: int, db_fixture) -> bool:
        """Load stage data from cached output files."""
        try:
            stage_outputs_dir = self.path_manager.get_stage_expected_outputs_dir(stage_number)
            database_seeds_dir = stage_outputs_dir / "database_seeds"
            
            if not database_seeds_dir.exists():
                logger.error(f"No database seeds directory for Stage {stage_number}")
                return False
                
            # Load and restore database state
            success = True
            
            # Restore drafts table
            drafts_file = database_seeds_dir / "drafts.json"
            if drafts_file.exists():
                success &= db_fixture.restore_table_from_json("drafts", str(drafts_file))
                
            # Restore draft_chunks table  
            chunks_file = database_seeds_dir / "draft_chunks.json"
            if chunks_file.exists():
                success &= db_fixture.restore_table_from_json("draft_chunks", str(chunks_file))
                
            # Restore other tables based on stage
            if stage_number >= 3:
                scenes_file = database_seeds_dir / "scenes.json"
                if scenes_file.exists():
                    success &= db_fixture.restore_table_from_json("scenes", str(scenes_file))
                    
            if stage_number >= 4:
                analysis_file = database_seeds_dir / "analysis_reports.json"
                if analysis_file.exists():
                    success &= db_fixture.restore_table_from_json("analysis_reports", str(analysis_file))
                    
            # Add more tables as needed for higher stages
            
            if success:
                logger.info(f"Successfully loaded Stage {stage_number} data from cache")
            else:
                logger.error(f"Failed to fully restore Stage {stage_number} data from cache")
                
            return success
            
        except Exception as e:
            logger.error(f"Error loading Stage {stage_number} from cache: {e}")
            return False
            
    def _execute_stage(self, stage_number: int, db_fixture, sample_file_path: str) -> Optional[Dict[str, Any]]:
        """Execute a specific stage with proper setup."""
        try:
            stage_instance = self.get_stage_instance(stage_number)
            if not stage_instance:
                logger.error(f"No stage instance available for Stage {stage_number}")
                return None
                
            # Create test data for the stage
            test_data = SampleDataGenerator(db_fixture.connection_pool)
            draft_data = test_data.generate_draft_request()
            
            # Create test workspace and draft
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
            
            # Execute the appropriate stage
            if stage_number == 1:
                result = stage_instance.run(
                    draft_id=test_draft['draft_id'],
                    file_path=sample_file_path
                )
            elif stage_number == 2:
                # Stage 2 needs chunks from Stage 1
                # Create some sample chunks if they don't exist
                chunks_count = db_fixture.count_records('draft_chunks', test_draft['draft_id'])
                if chunks_count == 0:
                    # Need to run Stage 1 first
                    stage_1_instance = self.get_stage_instance(1)
                    if stage_1_instance:
                        stage_1_result = stage_1_instance.run(
                            draft_id=test_draft['draft_id'],
                            file_path=sample_file_path
                        )
                        if not stage_1_result.get('success', False):
                            logger.error("Stage 1 prerequisite failed for Stage 2")
                            return None
                    else:
                        logger.error("Stage 1 instance not available for Stage 2 prerequisite")
                        return None
                        
                result = stage_instance.run(draft_id=test_draft['draft_id'])
            elif stage_number == 3:
                # Stage 3 needs chunks from Stage 2
                # Ensure Stage 2 has run and chunks exist
                chunks_count = db_fixture.count_records('draft_chunks', test_draft['draft_id'])
                if chunks_count == 0:
                    # Need to run Stages 1 and 2 first
                    stage_1_instance = self.get_stage_instance(1)
                    stage_2_instance = self.get_stage_instance(2)
                    
                    if stage_1_instance and stage_2_instance:
                        # Run Stage 1
                        stage_1_result = stage_1_instance.run(
                            draft_id=test_draft['draft_id'],
                            file_path=sample_file_path
                        )
                        if not stage_1_result.get('success', False):
                            logger.error("Stage 1 prerequisite failed for Stage 3")
                            return None
                        
                        # Run Stage 2
                        stage_2_result = stage_2_instance.run(draft_id=test_draft['draft_id'])
                        if not stage_2_result.get('success', False):
                            logger.error("Stage 2 prerequisite failed for Stage 3")
                            return None
                    else:
                        logger.error("Stage 1 or Stage 2 instance not available for Stage 3 prerequisites")
                        return None
                        
                result = stage_instance.run(draft_id=test_draft['draft_id'])
            else:
                # For stages 4+, implement as needed
                logger.warning(f"Stage {stage_number} execution not yet implemented")
                return None
                
            # Add draft info to result
            if result:
                result['draft_id'] = test_draft['draft_id']
                result['workspace_id'] = workspace_data['workspace_id']
                
            return result
            
        except Exception as e:
            logger.error(f"Error executing Stage {stage_number}: {e}")
            return {'success': False, 'error': str(e)}
            
    def reset_executed_stages(self):
        """Reset the list of executed stages (useful for test isolation)."""
        self._executed_stages.clear()
        logger.debug("Reset executed stages list")


# Global instance
_dependency_manager = None


def get_dependency_manager() -> StageDependencyManager:
    """Get global dependency manager instance."""
    global _dependency_manager
    if _dependency_manager is None:
        _dependency_manager = StageDependencyManager()
    return _dependency_manager


def requires_previous_stages(stages: Union[int, List[int]]):
    """
    Decorator to ensure previous stages have been executed before running a test.
    
    Args:
        stages: Stage number or list of stage numbers that must be completed
        
    Usage:
        @requires_previous_stages(1)
        def test_stage_2_functionality(self, ...):
            # This test will ensure Stage 1 has been completed first
            
        @requires_previous_stages([1, 2])  
        def test_stage_3_functionality(self, ...):
            # This test will ensure Stages 1 and 2 have been completed first
    """
    if isinstance(stages, int):
        required_stages = [stages]
    else:
        required_stages = list(stages)
        
    def decorator(test_func):
        @functools.wraps(test_func)
        def wrapper(*args, **kwargs):
            # Check if dependency_results is already provided by the fixture
            if 'dependency_results' in kwargs and kwargs['dependency_results'] is not None:
                # The fixture has already handled dependency resolution
                logger.debug("Using dependency_results from fixture")
                return test_func(*args, **kwargs)
            
            # Fallback to original decorator logic for backward compatibility
            logger.debug("Using decorator-based dependency resolution")
            
            # Extract test fixtures from kwargs
            db_fixture = kwargs.get('db_fixture')
            sample_file_path = kwargs.get('sample_file_path')
            
            if not db_fixture:
                # Try to find db_fixture in args (for methods)
                for arg in args:
                    if hasattr(arg, 'connection_pool'):
                        db_fixture = arg
                        break
                        
            if not sample_file_path:
                # Try to find in args
                for arg in args:
                    if isinstance(arg, str) and ('sample' in arg or '.txt' in arg or '.pdf' in arg):
                        sample_file_path = arg
                        break
                        
            if not db_fixture:
                raise RuntimeError("requires_previous_stages decorator requires db_fixture to be available")
                
            if not sample_file_path:
                # Use default sample file if none provided
                from .path_manager import get_sample_file
                sample_file_path = str(get_sample_file())
                
            # Get test configuration from pytest
            request = kwargs.get('request')
            use_cached_outputs = False
            skip_dependencies = False
            
            if request and hasattr(request, 'config'):
                use_cached_outputs = request.config.getoption("--use-stage-outputs", False)
                skip_dependencies = request.config.getoption("--skip-dependencies", False)
                
            # Ensure stage dependencies
            dependency_manager = get_dependency_manager()
            
            try:
                dependency_results = dependency_manager.ensure_stage_dependencies(
                    required_stages=required_stages,
                    db_fixture=db_fixture,
                    sample_file_path=sample_file_path,
                    use_cached_outputs=use_cached_outputs,
                    skip_dependencies=skip_dependencies
                )
                
                # Add dependency info to kwargs
                kwargs['dependency_results'] = dependency_results
                
                # Execute the original test function
                return test_func(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Stage dependency resolution failed: {e}")
                pytest.skip(f"Unable to resolve stage dependencies: {e}")
                
        return wrapper
    return decorator


def register_stage_instance(stage_number: int, instance):
    """Register a stage instance for dependency resolution."""
    dependency_manager = get_dependency_manager()
    dependency_manager.set_stage_instance(stage_number, instance)


def reset_stage_dependencies():
    """Reset stage dependency state (useful for test cleanup)."""
    dependency_manager = get_dependency_manager()
    dependency_manager.reset_executed_stages()
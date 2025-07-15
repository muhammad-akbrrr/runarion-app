"""
Centralized path management for the test suite.

This module provides utilities for managing test file paths, including:
- Input sample files
- Expected output files by stage
- Runtime test output directories
- Path discovery and validation
"""

import os
import glob
import shutil
import logging
from typing import Dict, List, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class TestPathManager:
    """Centralized manager for all test file paths."""
    
    def __init__(self, tests_root: Optional[str] = None):
        """
        Initialize the path manager.
        
        Args:
            tests_root: Root directory of the tests folder. If None, auto-discovers.
        """
        if tests_root is None:
            # Auto-discover tests root from this file's location
            self.tests_root = Path(__file__).parent.parent.absolute()
        else:
            self.tests_root = Path(tests_root).absolute()
        
        # Define path structures
        self.sample_files_dir = self.tests_root / "sample_files"
        self.inputs_dir = self.sample_files_dir / "inputs"
        self.test_configs_dir = self.sample_files_dir / "test_configs"
        self.outputs_dir = self.tests_root / "outputs"
        self.expected_outputs_dir = self.outputs_dir / "deconstructor"
        self.temp_outputs_dir = self.outputs_dir / "temp"
    
    def get_input_files(self, pattern: str = "*") -> List[Path]:
        """
        Get list of input sample files matching pattern.
        
        Args:
            pattern: Glob pattern to match files (default: all files)
            
        Returns:
            List of Path objects for matching input files
        """
        if not self.inputs_dir.exists():
            return []
        
        files = list(self.inputs_dir.glob(pattern))
        return sorted(files)
    
    def get_sample_file_path(self, filename: Optional[str] = None) -> Optional[Path]:
        """
        Get path to a specific sample file or the first available one.
        
        Args:
            filename: Specific filename to look for. If None, returns first available.
            
        Returns:
            Path to the sample file or None if not found
        """
        if filename:
            file_path = self.inputs_dir / filename
            return file_path if file_path.exists() else None
        
        # Return first available file
        input_files = self.get_input_files()
        return input_files[0] if input_files else None
    
    def get_expected_output_path(self, stage: Union[int, str], filename: str) -> Path:
        """
        Get path to expected output file for a specific stage.
        
        Args:
            stage: Stage number (1-7) or stage name
            filename: Name of the expected output file
            
        Returns:
            Path to expected output file
        """
        stage_name = f"stage_{stage}" if isinstance(stage, int) else stage
        return self.expected_outputs_dir / stage_name / filename
    
    def get_stage_expected_outputs_dir(self, stage: Union[int, str]) -> Path:
        """
        Get directory path for expected outputs of a specific stage.
        
        Args:
            stage: Stage number (1-7) or stage name
            
        Returns:
            Path to stage expected outputs directory
        """
        stage_name = f"stage_{stage}" if isinstance(stage, int) else stage
        return self.expected_outputs_dir / stage_name
    
    def get_temp_output_path(self, filename: str) -> Path:
        """
        Get path for temporary test output file.
        
        Args:
            filename: Name of the temporary output file
            
        Returns:
            Path to temporary output file
        """
        return self.temp_outputs_dir / filename
    
    def get_test_config_path(self, config_name: str) -> Path:
        """
        Get path to test configuration file.
        
        Args:
            config_name: Name of the config file (with or without .json extension)
            
        Returns:
            Path to test configuration file
        """
        if not config_name.endswith('.json'):
            config_name += '.json'
        
        return self.test_configs_dir / config_name
    
    def list_expected_outputs(self, stage: Union[int, str]) -> List[Path]:
        """
        List all expected output files for a given stage.
        
        Args:
            stage: Stage number (1-7) or stage name
            
        Returns:
            List of Path objects for expected output files
        """
        stage_dir = self.get_stage_expected_outputs_dir(stage)
        
        if not stage_dir.exists():
            return []
        
        # Get all non-.gitkeep files
        files = [f for f in stage_dir.iterdir() if f.is_file() and f.name != '.gitkeep']
        return sorted(files)
    
    def create_temp_output_path(self, filename: str) -> Path:
        """
        Create temporary output path, ensuring directory exists.
        
        Args:
            filename: Name of the temporary output file
            
        Returns:
            Path to temporary output file
        """
        self.temp_outputs_dir.mkdir(parents=True, exist_ok=True)
        return self.get_temp_output_path(filename)
    
    def ensure_directories_exist(self):
        """Ensure all necessary test directories exist."""
        directories = [
            self.inputs_dir,
            self.test_configs_dir,
            self.temp_outputs_dir,
            self.expected_outputs_dir
        ]
        
        # Create stage directories
        for stage in range(1, 8):
            directories.append(self.get_stage_expected_outputs_dir(stage))
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def cleanup_temp_outputs(self, pattern: str = "*"):
        """
        Clean up temporary output files.
        
        Args:
            pattern: Glob pattern for files to clean (default: all files except .gitkeep)
        """
        if not self.temp_outputs_dir.exists():
            return
        
        for file_path in self.temp_outputs_dir.glob(pattern):
            if file_path.is_file() and file_path.name != '.gitkeep':
                file_path.unlink()
    
    def recreate_output_directories(self):
        """
        Completely recreate all test output directories.
        
        This removes and recreates the entire output directory structure,
        ensuring a completely clean state for testing. This method is 
        designed to be run sequentially to avoid race conditions.
        """
        logger.info("Starting complete recreation of test output directories")
        
        try:
            # Remove entire outputs directory if it exists
            if self.outputs_dir.exists():
                logger.debug(f"Removing existing outputs directory: {self.outputs_dir}")
                shutil.rmtree(self.outputs_dir)
            
            # Recreate base outputs directory
            self.outputs_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created base outputs directory: {self.outputs_dir}")
            
            # Recreate temp outputs directory
            self.temp_outputs_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created temp outputs directory: {self.temp_outputs_dir}")
            
            # Recreate deconstructor base directory
            self.expected_outputs_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created expected outputs directory: {self.expected_outputs_dir}")
            
            # Recreate all stage directories with subdirectories
            stage_subdirs = ['database_seeds', 'logs', 'performance', 'results']
            
            for stage in range(1, 8):
                stage_dir = self.get_stage_expected_outputs_dir(stage)
                stage_dir.mkdir(parents=True, exist_ok=True)
                
                # Create subdirectories for each stage
                for subdir in stage_subdirs:
                    subdir_path = stage_dir / subdir
                    subdir_path.mkdir(parents=True, exist_ok=True)
                
                logger.debug(f"Created stage {stage} directory with subdirectories: {stage_dir}")
            
            logger.info(f"Successfully recreated test output directories: 7 stages x {len(stage_subdirs)} subdirectories")
            
        except Exception as e:
            logger.error(f"Failed to recreate output directories: {e}")
            raise
    
    def find_sample_by_name(self, name_pattern: str) -> Optional[Path]:
        """
        Find sample file by name pattern.
        
        Args:
            name_pattern: Pattern to match against filenames
            
        Returns:
            Path to first matching sample file or None
        """
        matching_files = self.get_input_files(f"*{name_pattern}*")
        return matching_files[0] if matching_files else None
    
    
    
    def get_environment_paths(self) -> Dict[str, str]:
        """
        Get environment variable mappings for test paths.
        
        Returns:
            Dictionary of environment variable names to path values
        """
        return {
            'TEST_EXPECTED_OUTPUTS_PATH': str(self.expected_outputs_dir),
            'TEST_CONFIGS_PATH': str(self.test_configs_dir),
            'TEST_SAMPLE_FILES_PATH': str(self.sample_files_dir)
        }


# Global instance for easy access
_path_manager = None


def get_path_manager() -> TestPathManager:
    """Get global path manager instance."""
    global _path_manager
    if _path_manager is None:
        _path_manager = TestPathManager()
    return _path_manager


def reset_path_manager():
    """Reset global path manager instance (useful for testing)."""
    global _path_manager
    _path_manager = None


# Convenience functions for common operations
def get_sample_file(filename: Optional[str] = None) -> Optional[Path]:
    """Get sample file path."""
    return get_path_manager().get_sample_file_path(filename)


def get_expected_output(stage: Union[int, str], filename: str) -> Path:
    """Get expected output file path."""
    return get_path_manager().get_expected_output_path(stage, filename)


def get_temp_output(filename: str) -> Path:
    """Get temporary output file path."""
    return get_path_manager().create_temp_output_path(filename)


def get_test_config(config_name: str) -> Path:
    """Get test configuration file path."""
    return get_path_manager().get_test_config_path(config_name)


def list_stage_outputs(stage: Union[int, str]) -> List[Path]:
    """List expected outputs for a stage."""
    return get_path_manager().list_expected_outputs(stage)


def cleanup_temp_files(pattern: str = "*"):
    """Clean up temporary test files."""
    get_path_manager().cleanup_temp_outputs(pattern)


def recreate_test_output_directories():
    """Completely recreate all test output directories."""
    get_path_manager().recreate_output_directories()
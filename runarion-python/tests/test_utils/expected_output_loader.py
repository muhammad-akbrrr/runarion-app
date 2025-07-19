"""
Expected output loader utilities for test validation.

This module provides utilities for loading and validating expected test outputs
for different pipeline stages, enabling regression testing and output validation.
"""

import json
import os
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
import logging

from .path_manager import get_path_manager


logger = logging.getLogger(__name__)


class ExpectedOutputLoader:
    """Loader for expected test outputs with validation capabilities."""
    
    def __init__(self):
        self.path_manager = get_path_manager()
    
    def load_expected_output(self, stage: Union[int, str], filename: str) -> Optional[Dict[str, Any]]:
        """
        Load expected output JSON file for a given stage.
        
        Args:
            stage: Stage number (1-7) or stage name
            filename: Name of the expected output file
            
        Returns:
            Dictionary containing expected output data or None if not found
        """
        expected_path = self.path_manager.get_expected_output_path(stage, filename)
        
        if expected_path.exists():
            return self._load_json_file(expected_path)
        
        logger.warning(f"Expected output not found: {filename} for stage {stage}")
        return None
    
    def _load_json_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load JSON file with error handling."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in expected output file {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading expected output file {file_path}: {e}")
            return None
    
    def save_expected_output(self, stage: Union[int, str], filename: str, data: Dict[str, Any]) -> bool:
        """
        Save expected output data to file.
        
        Args:
            stage: Stage number (1-7) or stage name
            filename: Name of the expected output file
            data: Data to save as expected output
            
        Returns:
            True if saved successfully, False otherwise
        """
        expected_path = self.path_manager.get_expected_output_path(stage, filename)
        
        try:
            # Ensure directory exists
            expected_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(expected_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved expected output: {expected_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving expected output {expected_path}: {e}")
            return False
    
    def list_expected_outputs_for_stage(self, stage: Union[int, str]) -> List[str]:
        """
        List available expected output files for a stage.
        
        Args:
            stage: Stage number (1-7) or stage name
            
        Returns:
            List of expected output filenames
        """
        expected_files = self.path_manager.list_expected_outputs(stage)
        return [f.name for f in expected_files]
    
    def validate_output_structure(self, stage: Union[int, str], actual_output: Dict[str, Any], 
                                expected_filename: str) -> Tuple[bool, List[str]]:
        """
        Validate that actual output matches expected structure.
        
        Args:
            stage: Stage number (1-7) or stage name
            actual_output: Actual output from pipeline stage
            expected_filename: Name of expected output file to compare against
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        expected_output = self.load_expected_output(stage, expected_filename)
        
        if expected_output is None:
            return False, [f"Expected output file not found: {expected_filename}"]
        
        errors = []
        
        # Validate structure recursively
        self._validate_dict_structure(actual_output, expected_output, "", errors)
        
        return len(errors) == 0, errors
    
    def _validate_dict_structure(self, actual: Any, expected: Any, path: str, errors: List[str]):
        """Recursively validate dictionary structure."""
        if type(actual) != type(expected):
            errors.append(f"Type mismatch at {path}: expected {type(expected).__name__}, got {type(actual).__name__}")
            return
        
        if isinstance(expected, dict):
            for key in expected:
                if key not in actual:
                    errors.append(f"Missing key at {path}.{key}")
                else:
                    self._validate_dict_structure(
                        actual[key], expected[key], 
                        f"{path}.{key}" if path else key, 
                        errors
                    )
        elif isinstance(expected, list):
            if len(actual) == 0 and len(expected) > 0:
                errors.append(f"Empty list at {path}, expected non-empty")
            elif len(actual) > 0 and len(expected) > 0:
                # Validate first item structure
                self._validate_dict_structure(
                    actual[0], expected[0], 
                    f"{path}[0]", 
                    errors
                )
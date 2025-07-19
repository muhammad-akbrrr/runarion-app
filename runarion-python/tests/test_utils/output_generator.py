"""
Test output generation utilities for comprehensive test result capture.

This module provides utilities for generating test outputs including:
- Test results in JSON format
- Database state snapshots for stage seeding
- Structured logs for debugging
- Performance metrics and metadata
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import traceback

from .path_manager import get_path_manager

logger = logging.getLogger(__name__)


class TestOutputGenerator:
    """
    Generates comprehensive test outputs for debugging and stage seeding.
    """
    
    def __init__(self):
        self.path_manager = get_path_manager()
        self._ensure_output_directories()
        
    def _format_timestamp_for_filename(self, timestamp: str) -> str:
        """Convert ISO timestamp to filename-safe format."""
        # Convert 2025-07-14T15:54:26.592106+00:00 to 20250714_155426
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime('%Y%m%d_%H%M%S')
        except Exception:
            # Fallback to current time if timestamp parsing fails
            return datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        
    def _ensure_output_directories(self):
        """Ensure all necessary output directories exist."""
        for stage in range(1, 8):
            stage_dir = self.path_manager.get_stage_expected_outputs_dir(stage)
            
            # Create subdirectories for different output types
            (stage_dir / "results").mkdir(parents=True, exist_ok=True)
            (stage_dir / "database_seeds").mkdir(parents=True, exist_ok=True)
            (stage_dir / "logs").mkdir(parents=True, exist_ok=True)
            (stage_dir / "performance").mkdir(parents=True, exist_ok=True)
            
    def generate_test_output(self, 
                           stage_number: int,
                           test_name: str,
                           test_result: Dict[str, Any],
                           db_fixture = None,
                           additional_data: Optional[Dict[str, Any]] = None,
                           capture_database: bool = True,
                           include_performance: bool = True) -> Dict[str, str]:
        """
        Generate comprehensive test output including results and database state.
        
        Args:
            stage_number: Stage number (1-7)
            test_name: Name of the test function
            test_result: Result data from the stage execution
            db_fixture: Database fixture for capturing database state
            additional_data: Additional data to include in output
            capture_database: Whether to capture database state for seeding
            include_performance: Whether to include performance metrics
            
        Returns:
            Dictionary with paths to generated output files
        """
        # Ensure output directories exist (in case they were deleted by cleanup)
        self._ensure_output_directories()
        
        output_files = {}
        timestamp = datetime.now(timezone.utc).isoformat()
        
        try:
            # Generate main test result output
            result_file = self._generate_test_result_output(
                stage_number, test_name, test_result, additional_data, timestamp
            )
            output_files['result'] = result_file
            
            # Generate database state snapshot for next stage seeding
            if capture_database and db_fixture:
                database_files = self._generate_database_seeds(
                    stage_number, test_name, db_fixture, test_result, timestamp
                )
                output_files.update(database_files)
                
            # Generate log file
            log_file = self._generate_test_log(
                stage_number, test_name, test_result, timestamp
            )
            output_files['log'] = log_file
            
            # Generate performance metrics
            if include_performance:
                performance_file = self._generate_performance_output(
                    stage_number, test_name, test_result, timestamp
                )
                output_files['performance'] = performance_file
                
            logger.info(f"Generated test outputs for {test_name} (Stage {stage_number}): {len(output_files)} files")
            
        except Exception as e:
            logger.error(f"Error generating test output for {test_name}: {e}")
            # Create error output file
            error_file = self._generate_error_output(stage_number, test_name, e, timestamp)
            output_files['error'] = error_file
            
        return output_files
        
    def _generate_test_result_output(self, stage_number: int, test_name: str, 
                                   test_result: Dict[str, Any], 
                                   additional_data: Optional[Dict[str, Any]],
                                   timestamp: str) -> str:
        """Generate main test result JSON file."""
        stage_dir = self.path_manager.get_stage_expected_outputs_dir(stage_number)
        results_dir = stage_dir / "results"
        
        # Clean test name for filename and add timestamp
        clean_test_name = test_name.replace('test_', '').replace('_', '_')
        timestamp_str = self._format_timestamp_for_filename(timestamp)
        result_filename = f"{clean_test_name}_{timestamp_str}_output.json"
        result_path = results_dir / result_filename
        
        # Build comprehensive output data
        output_data = {
            'metadata': {
                'stage_number': stage_number,
                'test_name': test_name,
                'timestamp': timestamp,
                'generator_version': '1.0.0'
            },
            'test_result': test_result,
            'success': test_result.get('success', False),
            'execution_summary': {
                'total_processing_time': additional_data.get('test_configuration', {}).get('processing_time') if additional_data else test_result.get('processing_time', 'N/A'),
                'chunks_processed': test_result.get('chunks_created', test_result.get('chunks_processed', 0)),
                'errors_encountered': 1 if not test_result.get('success', False) else 0,
                'api_calls_made': test_result.get('execution_metadata', {}).get('api_calls_made', False),
                'stage_type': 'ingestion' if stage_number == 1 else 'cleaning' if stage_number == 2 else f'stage_{stage_number}'
            }
        }
        
        # Add additional data if provided
        if additional_data:
            output_data['additional_data'] = additional_data
            
        # Add execution metadata if available
        execution_metadata = test_result.get('execution_metadata', {})
        if execution_metadata:
            output_data['execution_metadata'] = execution_metadata
            
        # Add stage-specific information
        if stage_number == 1:
            metadata = test_result.get('metadata', {})
            output_data['stage_1_specifics'] = {
                'total_characters': test_result.get('total_characters', 0),
                'total_words': test_result.get('total_words', 0),
                'total_tokens': test_result.get('total_tokens', 0),
                'chunks_created': test_result.get('chunks_created', 0),
                'processing_model': metadata.get('processing_model', 'N/A'),
                'file_path': metadata.get('file_path', 'unknown'),
                'file_size': metadata.get('file_size', 0)
            }
        elif stage_number == 2:
            output_data['stage_2_specifics'] = {
                'chunks_cleaned': test_result.get('chunks_cleaned', 0),
                'chunks_processed': test_result.get('chunks_processed', 0),
                'failed_chunks': test_result.get('failed_chunks', 0),
                'cleaning_improvements': test_result.get('cleaning_summary', {}),
                'actual_provider': execution_metadata.get('actual_provider', 'unknown'),
                'actual_model': execution_metadata.get('actual_model', 'unknown'),
                'api_calls_made': execution_metadata.get('api_calls_made', False)
            }
            
        # Save to file
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
            
        logger.debug(f"Generated test result output: {result_path}")
        return str(result_path)
        
    def _generate_database_seeds(self, stage_number: int, test_name: str, 
                               db_fixture, test_result: Dict[str, Any],
                               timestamp: str) -> Dict[str, str]:
        """Generate database state snapshots for next stage seeding with operation details."""
        stage_dir = self.path_manager.get_stage_expected_outputs_dir(stage_number)
        seeds_dir = stage_dir / "database_seeds"
        
        database_files = {}
        
        try:
            # Get tracked operations from database fixture
            operations = db_fixture.get_tracked_operations() if db_fixture else []
            operations_summary = db_fixture.get_operations_summary() if db_fixture else {}
            
            # Get draft_id from test result or additional_data
            draft_id = test_result.get('draft_id')
            if not draft_id:
                # Try to get draft_id from additional_data
                if additional_data and 'draft_id' in additional_data:
                    draft_id = additional_data['draft_id']
                    logger.debug("Found draft_id in additional_data")
                elif db_fixture and hasattr(db_fixture, 'created_records') and db_fixture.created_records.get('drafts'):
                    # Fallback: try to get the most recent draft_id from database fixture
                    draft_ids = db_fixture.created_records['drafts']
                    if draft_ids:
                        draft_id = draft_ids[-1]  # Use the most recent one
                        logger.debug(f"Using most recent draft_id from db_fixture: {draft_id}")
                
            if not draft_id:
                logger.error(f"No draft_id found in test_result, additional_data, or database fixture. Cannot generate database seeds for test: {test_name}")
                return database_files
            
            logger.info(f"Generating database seeds for draft_id: {draft_id} (test: {test_name})")
                
            # Core tables that are always needed
            core_tables = ['drafts', 'draft_chunks']
            
            # Additional tables based on stage
            stage_specific_tables = {
                3: ['scenes'],
                4: ['analysis_reports', 'plot_issues'],
                5: ['scenes'],  # Updated scenes after coherence analysis
                6: ['scenes'],  # Enhanced scenes
                7: ['chapters', 'final_manuscripts']
            }
            
            all_tables = core_tables + stage_specific_tables.get(stage_number, [])
            
            for table_name in all_tables:
                try:
                    # Export table data related to this test's draft
                    table_data = self._export_table_data(db_fixture, table_name, draft_id)
                    
                    if table_data:
                        timestamp_str = self._format_timestamp_for_filename(timestamp)
                        seed_filename = f"{table_name}_{timestamp_str}.json"
                        seed_path = seeds_dir / seed_filename
                        
                        # Filter operations for this table
                        table_operations = [op for op in operations if op.get('table') == table_name]
                        
                        # Add metadata to the seed data with operation details
                        seed_data = {
                            'metadata': {
                                'table_name': table_name,
                                'stage_number': stage_number,
                                'test_name': test_name,
                                'draft_id': draft_id,
                                'timestamp': timestamp,
                                'record_count': len(table_data),
                                'operations_performed': len(table_operations)
                            },
                            'operations': table_operations,
                            'final_state': table_data,
                            'operations_summary': {
                                'total_operations': len(table_operations),
                                'operation_types': list(set(op.get('operation', 'unknown') for op in table_operations))
                            }
                        }
                        
                        with open(seed_path, 'w', encoding='utf-8') as f:
                            json.dump(seed_data, f, indent=2, ensure_ascii=False, default=str)
                            
                        database_files[f'database_seed_{table_name}'] = str(seed_path)
                        logger.debug(f"Generated database seed for {table_name}: {seed_path}")
                        
                except Exception as e:
                    logger.warning(f"Failed to export {table_name} for database seeding: {e}")
            
            # Generate overall operations summary file
            if operations:
                timestamp_str = self._format_timestamp_for_filename(timestamp)
                operations_filename = f"operations_summary_{timestamp_str}.json"
                operations_path = seeds_dir / operations_filename
                
                operations_data = {
                    'metadata': {
                        'stage_number': stage_number,
                        'test_name': test_name,
                        'draft_id': draft_id,
                        'timestamp': timestamp,
                        'total_operations': len(operations)
                    },
                    'all_operations': operations,
                    'summary': operations_summary
                }
                
                with open(operations_path, 'w', encoding='utf-8') as f:
                    json.dump(operations_data, f, indent=2, ensure_ascii=False, default=str)
                    
                database_files['operations_summary'] = str(operations_path)
                logger.debug(f"Generated operations summary: {operations_path}")
                    
        except Exception as e:
            logger.error(f"Error generating database seeds: {e}")
            
        return database_files
        
    def _export_table_data(self, db_fixture, table_name: str, draft_id: str) -> List[Dict[str, Any]]:
        """Export data from a specific table related to the draft."""
        try:
            # Define queries for different tables
            queries = {
                'drafts': "SELECT * FROM drafts WHERE id = %s",
                'draft_chunks': "SELECT * FROM draft_chunks WHERE draft_id = %s ORDER BY chunk_number",
                'scenes': "SELECT * FROM scenes WHERE draft_id = %s ORDER BY scene_number",
                'analysis_reports': "SELECT * FROM analysis_reports WHERE draft_id = %s",
                'plot_issues': "SELECT * FROM plot_issues WHERE draft_id = %s",
                'chapters': "SELECT * FROM chapters WHERE draft_id = %s ORDER BY chapter_number",
                'final_manuscripts': "SELECT * FROM final_manuscripts WHERE draft_id = %s"
            }
            
            query = queries.get(table_name)
            if not query:
                logger.warning(f"No query defined for table: {table_name}")
                return []
                
            # Execute query
            rows = db_fixture.execute_query(query, (draft_id,))
            
            if not rows:
                return []
                
            # Get column names
            column_names = db_fixture.get_table_columns(table_name)
            
            # Convert to list of dictionaries
            table_data = []
            for row in rows:
                row_dict = dict(zip(column_names, row))
                table_data.append(row_dict)
                
            logger.debug(f"Exported {len(table_data)} records from {table_name}")
            return table_data
            
        except Exception as e:
            logger.error(f"Error exporting data from {table_name}: {e}")
            return []
            
    def _generate_test_log(self, stage_number: int, test_name: str, 
                         test_result: Dict[str, Any], timestamp: str) -> str:
        """Generate structured log file for the test."""
        stage_dir = self.path_manager.get_stage_expected_outputs_dir(stage_number)
        logs_dir = stage_dir / "logs"
        
        clean_test_name = test_name.replace('test_', '').replace('_', '_')
        timestamp_str = self._format_timestamp_for_filename(timestamp)
        log_filename = f"{clean_test_name}_{timestamp_str}.log"
        log_path = logs_dir / log_filename
        
        # Generate log content
        log_content = [
            f"=== Test Log for {test_name} ===",
            f"Stage: {stage_number}",
            f"Timestamp: {timestamp}",
            f"Success: {test_result.get('success', False)}",
            ""
        ]
        
        # Add test results
        log_content.append("=== Test Results ===")
        for key, value in test_result.items():
            if key != 'metadata':  # Skip complex metadata in log
                log_content.append(f"{key}: {value}")
        log_content.append("")
        
        # Add error information if test failed
        if not test_result.get('success', False):
            log_content.append("=== Error Information ===")
            error = test_result.get('error', 'No error message available')
            log_content.append(f"Error: {error}")
            log_content.append("")
            
        # Add metadata if available
        metadata = test_result.get('metadata', {})
        if metadata:
            log_content.append("=== Metadata ===")
            for key, value in metadata.items():
                log_content.append(f"{key}: {value}")
            log_content.append("")
            
        # Add execution environment info
        log_content.append("=== Execution Environment ===")
        log_content.append(f"Python PID: {os.getpid()}")
        log_content.append(f"Working Directory: {os.getcwd()}")
        log_content.append("")
        
        # Write log file
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_content))
            
        logger.debug(f"Generated test log: {log_path}")
        return str(log_path)
        
    def _generate_performance_output(self, stage_number: int, test_name: str,
                                   test_result: Dict[str, Any], timestamp: str) -> str:
        """Generate performance metrics output."""
        stage_dir = self.path_manager.get_stage_expected_outputs_dir(stage_number)
        performance_dir = stage_dir / "performance"
        
        clean_test_name = test_name.replace('test_', '').replace('_', '_')
        timestamp_str = self._format_timestamp_for_filename(timestamp)
        perf_filename = f"{clean_test_name}_{timestamp_str}_performance.json"
        perf_path = performance_dir / perf_filename
        
        # Collect performance data
        performance_data = {
            'metadata': {
                'stage_number': stage_number,
                'test_name': test_name,
                'timestamp': timestamp
            },
            'execution_metrics': {
                'processing_time': test_result.get('processing_time', 'N/A'),
                'success': test_result.get('success', False)
            },
            'data_metrics': {
                'input_size': test_result.get('total_characters', 0),
                'output_count': test_result.get('chunks_created', test_result.get('chunks_processed', 0))
            }
        }
        
        # Add stage-specific performance metrics
        if stage_number == 1:
            performance_data['stage_1_metrics'] = {
                'words_per_second': self._calculate_words_per_second(test_result),
                'tokens_per_second': self._calculate_tokens_per_second(test_result),
                'chunks_per_second': self._calculate_chunks_per_second(test_result)
            }
            
        # Save performance data
        with open(perf_path, 'w', encoding='utf-8') as f:
            json.dump(performance_data, f, indent=2, ensure_ascii=False)
            
        logger.debug(f"Generated performance output: {perf_path}")
        return str(perf_path)
        
    def _generate_error_output(self, stage_number: int, test_name: str, 
                             error: Exception, timestamp: str) -> str:
        """Generate error output file when test output generation fails."""
        stage_dir = self.path_manager.get_stage_expected_outputs_dir(stage_number)
        results_dir = stage_dir / "results"
        
        clean_test_name = test_name.replace('test_', '').replace('_', '_')
        timestamp_str = self._format_timestamp_for_filename(timestamp)
        error_filename = f"{clean_test_name}_{timestamp_str}_error.json"
        error_path = results_dir / error_filename
        
        error_data = {
            'metadata': {
                'stage_number': stage_number,
                'test_name': test_name,
                'timestamp': timestamp,
                'error_in_output_generation': True
            },
            'error': {
                'type': type(error).__name__,
                'message': str(error),
                'traceback': traceback.format_exc()
            }
        }
        
        try:
            with open(error_path, 'w', encoding='utf-8') as f:
                json.dump(error_data, f, indent=2, ensure_ascii=False)
        except Exception:
            # If we can't even write the error file, just log it
            logger.critical(f"Failed to write error output file for {test_name}: {error}")
            
        return str(error_path)
        
    def _calculate_words_per_second(self, test_result: Dict[str, Any]) -> float:
        """Calculate words processed per second."""
        try:
            total_words = test_result.get('total_words', 0)
            processing_time = test_result.get('processing_time', 0)
            
            if processing_time > 0:
                return total_words / processing_time
        except (TypeError, ZeroDivisionError):
            pass
        return 0.0
        
    def _calculate_tokens_per_second(self, test_result: Dict[str, Any]) -> float:
        """Calculate tokens processed per second."""
        try:
            total_tokens = test_result.get('total_tokens', 0)
            processing_time = test_result.get('processing_time', 0)
            
            if processing_time > 0:
                return total_tokens / processing_time
        except (TypeError, ZeroDivisionError):
            pass
        return 0.0
        
    def _calculate_chunks_per_second(self, test_result: Dict[str, Any]) -> float:
        """Calculate chunks processed per second."""
        try:
            chunks_count = test_result.get('chunks_created', test_result.get('chunks_processed', 0))
            processing_time = test_result.get('processing_time', 0)
            
            if processing_time > 0:
                return chunks_count / processing_time
        except (TypeError, ZeroDivisionError):
            pass
        return 0.0


# Global instance
_output_generator = None


def get_output_generator() -> TestOutputGenerator:
    """Get global output generator instance."""
    global _output_generator
    if _output_generator is None:
        _output_generator = TestOutputGenerator()
    return _output_generator


# Convenience functions
def generate_stage_output(stage_number: int, test_name: str, test_result: Dict[str, Any], 
                         db_fixture = None, **kwargs) -> Dict[str, str]:
    """Generate comprehensive stage test output."""
    generator = get_output_generator()
    return generator.generate_test_output(
        stage_number=stage_number,
        test_name=test_name,
        test_result=test_result,
        db_fixture=db_fixture,
        **kwargs
    )


def generate_test_log(stage_number: int, test_name: str, test_result: Dict[str, Any]) -> str:
    """Generate test log file."""
    generator = get_output_generator()
    timestamp = datetime.now(timezone.utc).isoformat()
    return generator._generate_test_log(stage_number, test_name, test_result, timestamp)
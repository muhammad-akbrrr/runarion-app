"""
Structured logging configuration for the Runarion Python service.
Provides consistent logging format across all modules with proper JSON structuring.
"""

import logging
import json
import sys
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    """
    Custom logging formatter that outputs structured JSON logs.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as structured JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON formatted log string
        """
        # Create base log structure
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'process': record.process
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'getMessage']:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str, separators=(',', ':'))


class PipelineLogger:
    """
    Specialized logger for pipeline operations with structured context.
    """
    
    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
        self.context = {}
    
    def set_context(self, **kwargs):
        """Set context fields that will be included in all log messages."""
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear all context fields."""
        self.context.clear()
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with context and additional fields."""
        extra_fields = {**self.context, **kwargs}
        self.logger.log(level, message, extra=extra_fields)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with context."""
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    def stage_start(self, stage_name: str, draft_id: str, **kwargs):
        """Log stage start with standardized format."""
        self.info(
            f"Stage {stage_name} started",
            event_type="stage_start",
            stage_name=stage_name,
            draft_id=draft_id,
            **kwargs
        )
    
    def stage_complete(self, stage_name: str, draft_id: str, duration_seconds: float = None, **kwargs):
        """Log stage completion with standardized format."""
        self.info(
            f"Stage {stage_name} completed",
            event_type="stage_complete",
            stage_name=stage_name,
            draft_id=draft_id,
            duration_seconds=duration_seconds,
            **kwargs
        )
    
    def stage_retry(self, stage_name: str, draft_id: str, attempt: int, max_attempts: int, error: str = None, **kwargs):
        """Log stage retry with standardized format."""
        self.warning(
            f"Stage {stage_name} retry attempt {attempt}/{max_attempts}",
            event_type="stage_retry",
            stage_name=stage_name,
            draft_id=draft_id,
            attempt=attempt,
            max_attempts=max_attempts,
            error=error,
            **kwargs
        )
    
    def stage_failed(self, stage_name: str, draft_id: str, error: str = None, **kwargs):
        """Log stage failure with standardized format."""
        self.error(
            f"Stage {stage_name} failed permanently",
            event_type="stage_failed",
            stage_name=stage_name,
            draft_id=draft_id,
            error=error,
            **kwargs
        )
    
    def pipeline_start(self, draft_id: str, **kwargs):
        """Log pipeline start with standardized format."""
        self.info(
            "Pipeline execution started",
            event_type="pipeline_start",
            draft_id=draft_id,
            **kwargs
        )
    
    def pipeline_complete(self, draft_id: str, duration_seconds: float = None, **kwargs):
        """Log pipeline completion with standardized format."""
        self.info(
            "Pipeline execution completed",
            event_type="pipeline_complete",
            draft_id=draft_id,
            duration_seconds=duration_seconds,
            **kwargs
        )
    
    def pipeline_failed(self, draft_id: str, error: str = None, **kwargs):
        """Log pipeline failure with standardized format."""
        self.error(
            "Pipeline execution failed",
            event_type="pipeline_failed",
            draft_id=draft_id,
            error=error,
            **kwargs
        )


def configure_logging(log_level: str = "INFO", output_format: str = "structured"):
    """
    Configure logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        output_format: Format type ('structured' for JSON, 'simple' for plain text)
    """
    
    # Define log levels
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    log_level_int = level_map.get(log_level.upper(), logging.INFO)
    
    # Define formatters
    if output_format == "structured":
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level_int)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level_int)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set levels for specific loggers to reduce noise
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('psycopg2').setLevel(logging.WARNING)
    
    logging.info(f"Logging configured with level: {log_level}, format: {output_format}")


def get_pipeline_logger(name: str) -> PipelineLogger:
    """
    Get a pipeline logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        PipelineLogger instance
    """
    return PipelineLogger(name)


# Create module-level logger
logger = get_pipeline_logger(__name__)
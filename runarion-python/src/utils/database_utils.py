"""
Database utilities for standardizing UTF-8 encoding and safe database operations.
Provides helper functions for consistent text handling across the pipeline.
Includes transaction management with retry capabilities.
"""

import json
import re
import logging
import time
from typing import Any, Dict, List, Callable
from functools import wraps
import psycopg2
from contextlib import contextmanager

logger = logging.getLogger(__name__)


# =============================================================================
# Error Classification for Transaction Retry
# =============================================================================

class TransientDatabaseError(Exception):
    """
    Database error that may succeed on retry.
    Examples: pool exhaustion, connection timeout, deadlock, network issues.
    """
    pass


class PermanentDatabaseError(Exception):
    """
    Database error that will NOT succeed on retry.
    Examples: constraint violation, syntax error, entity not found.
    """
    pass


# Indicators of transient (retryable) errors
TRANSIENT_ERROR_INDICATORS = [
    'connection pool exhausted',
    'pool exhausted',
    'connection timed out',
    'connection refused',
    'network error',
    'deadlock',
    'could not connect',
    'server closed the connection',
    'connection reset',
    'too many connections',
    'serialization failure',
    'lock wait timeout',
    'timeout expired',
    'connection lost',
]


def classify_db_error(error: Exception) -> str:
    """
    Classify database errors as transient (retryable) or permanent.

    Args:
        error: The exception to classify

    Returns:
        'transient' or 'permanent'
    """
    error_str = str(error).lower()

    # Check for known transient indicators
    for indicator in TRANSIENT_ERROR_INDICATORS:
        if indicator in error_str:
            return 'transient'

    # Check psycopg2 specific error types
    if isinstance(error, psycopg2.OperationalError):
        return 'transient'  # Usually connection issues

    if isinstance(error, (psycopg2.IntegrityError, psycopg2.ProgrammingError)):
        return 'permanent'  # Constraint violations, syntax errors

    # Default to permanent for unknown errors (fail fast for safety)
    return 'permanent'


def ensure_utf8_text(text: Any) -> str:
    """
    Ensure text is properly UTF-8 encoded string.
    
    Args:
        text: Input text (str, bytes, or other)
        
    Returns:
        UTF-8 encoded string
    """
    if text is None:
        return ""
    
    if isinstance(text, bytes):
        # Try to decode bytes as UTF-8
        try:
            return text.decode('utf-8')
        except UnicodeDecodeError:
            # Fallback to latin-1 and then encode as UTF-8
            try:
                return text.decode('latin-1').encode('utf-8').decode('utf-8')
            except (UnicodeDecodeError, UnicodeEncodeError):
                # Final fallback - replace invalid characters
                return text.decode('utf-8', errors='replace')
    
    if isinstance(text, str):
        # Ensure string is properly UTF-8 by re-encoding
        try:
            # This will raise an exception if there are encoding issues
            text.encode('utf-8')
            return text
        except UnicodeEncodeError:
            # Fix encoding issues by replacing problematic characters
            return text.encode('utf-8', errors='replace').decode('utf-8')
    
    # Convert other types to string and ensure UTF-8
    return ensure_utf8_text(str(text))


def ensure_utf8_json(data: Any) -> str:
    """
    Ensure JSON data is properly UTF-8 encoded.
    
    Args:
        data: Data to convert to JSON
        
    Returns:
        UTF-8 encoded JSON string
    """
    if data is None:
        return "{}"
    
    if isinstance(data, str):
        # If it's already a JSON string, validate and re-encode
        try:
            parsed = json.loads(data)
            return json.dumps(parsed, ensure_ascii=False, separators=(',', ':'))
        except (json.JSONDecodeError, TypeError):
            # If parsing fails, treat as regular text
            return json.dumps(ensure_utf8_text(data), ensure_ascii=False, separators=(',', ':'))
    
    try:
        # Convert data to JSON with UTF-8 support
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'), default=str)
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to serialize data to JSON: {e}")
        return json.dumps({"error": "Failed to serialize data"}, ensure_ascii=False)


def safe_execute_query(cursor, query: str, params: tuple = (), 
                      encoding_fields: List[str] = None) -> Any:
    """
    Execute database query with UTF-8 encoding safety.
    
    Args:
        cursor: Database cursor
        query: SQL query
        params: Query parameters
        encoding_fields: List of parameter indices that should be UTF-8 encoded
        
    Returns:
        Query result
    """
    # Ensure all text parameters are UTF-8 encoded
    safe_params = []
    encoding_fields = encoding_fields or []
    
    for i, param in enumerate(params):
        if i in encoding_fields or isinstance(param, (str, bytes)):
            safe_params.append(ensure_utf8_text(param))
        else:
            safe_params.append(param)
    
    try:
        cursor.execute(query, tuple(safe_params))
        return cursor.fetchall() if cursor.description else None
    except (psycopg2.DataError, psycopg2.DatabaseError, UnicodeError) as e:
        logger.error(f"Database query failed with encoding error: {e}")
        logger.error(f"Query: {query}")
        logger.error(f"Params: {safe_params}")
        raise


def safe_insert_text(cursor, table: str, data: Dict[str, Any], 
                    text_fields: List[str] = None) -> bool:
    """
    Safely insert data with UTF-8 text fields into database.
    
    Args:
        cursor: Database cursor
        table: Table name
        data: Data dictionary
        text_fields: List of fields that contain text data
        
    Returns:
        Success status
    """
    text_fields = text_fields or []
    
    # Prepare data with UTF-8 encoding
    safe_data = {}
    for key, value in data.items():
        if key in text_fields or isinstance(value, (str, bytes)):
            safe_data[key] = ensure_utf8_text(value)
        elif isinstance(value, dict) or isinstance(value, list):
            safe_data[key] = ensure_utf8_json(value)
        else:
            safe_data[key] = value
    
    # Build INSERT query
    columns = list(safe_data.keys())
    placeholders = ["%s"] * len(columns)
    values = [safe_data[col] for col in columns]
    
    query = f"""
        INSERT INTO {table} ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
    """
    
    try:
        cursor.execute(query, values)
        return True
    except (psycopg2.DataError, psycopg2.DatabaseError, UnicodeError) as e:
        logger.error(f"Failed to insert data into {table}: {e}")
        logger.error(f"Data: {safe_data}")
        return False


def safe_update_text(cursor, table: str, data: Dict[str, Any], 
                    where_clause: str, where_params: tuple,
                    text_fields: List[str] = None) -> bool:
    """
    Safely update data with UTF-8 text fields in database.
    
    Args:
        cursor: Database cursor
        table: Table name
        data: Data dictionary to update
        where_clause: WHERE clause (without WHERE keyword)
        where_params: Parameters for WHERE clause
        text_fields: List of fields that contain text data
        
    Returns:
        Success status
    """
    text_fields = text_fields or []
    
    # Prepare data with UTF-8 encoding
    safe_data = {}
    for key, value in data.items():
        if key in text_fields or isinstance(value, (str, bytes)):
            safe_data[key] = ensure_utf8_text(value)
        elif isinstance(value, dict) or isinstance(value, list):
            safe_data[key] = ensure_utf8_json(value)
        else:
            safe_data[key] = value
    
    # Build UPDATE query
    set_clauses = [f"{col} = %s" for col in safe_data.keys()]
    values = list(safe_data.values())
    
    # Add WHERE parameters
    safe_where_params = []
    for param in where_params:
        if isinstance(param, (str, bytes)):
            safe_where_params.append(ensure_utf8_text(param))
        else:
            safe_where_params.append(param)
    
    query = f"""
        UPDATE {table}
        SET {', '.join(set_clauses)}
        WHERE {where_clause}
    """
    
    all_params = values + safe_where_params
    
    try:
        cursor.execute(query, all_params)
        return True
    except (psycopg2.DataError, psycopg2.DatabaseError, UnicodeError) as e:
        logger.error(f"Failed to update data in {table}: {e}")
        logger.error(f"Data: {safe_data}")
        logger.error(f"WHERE: {where_clause} with params {safe_where_params}")
        return False


@contextmanager
def utf8_database_connection(
    connection_pool,
    max_retries: int = 1,
    initial_delay: float = 0.5,
    max_delay: float = 4.0,
    operation_name: str = "database_operation"
):
    """
    Context manager that ensures UTF-8 encoding for database connection.
    Supports automatic retry with exponential backoff for transient errors.

    Args:
        connection_pool: Database connection pool
        max_retries: Maximum retry attempts (default 1 = no retry, backward compatible)
        initial_delay: Initial delay between retries in seconds (default 0.5)
        max_delay: Maximum delay cap for exponential backoff (default 4.0)
        operation_name: Name for logging purposes

    Yields:
        Database connection with UTF-8 encoding set

    Raises:
        TransientDatabaseError: After all retries exhausted for transient errors
        PermanentDatabaseError: Immediately for permanent errors
    """
    conn = None
    attempt = 0
    delay = initial_delay
    last_error = None

    while attempt < max_retries:
        attempt += 1
        conn = None  # Reset for each attempt

        try:
            # Acquire connection
            try:
                conn = connection_pool.getconn()
            except Exception as pool_error:
                error_type = classify_db_error(pool_error)
                if error_type == 'transient' and attempt < max_retries:
                    logger.warning(
                        f"[{operation_name}] Pool error (attempt {attempt}/{max_retries}): "
                        f"{pool_error}. Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, max_delay)
                    continue
                else:
                    raise TransientDatabaseError(
                        f"Connection pool error after {attempt} attempts: {pool_error}"
                    ) from pool_error

            # Set connection encoding to UTF-8
            conn.set_client_encoding('UTF8')

            # Set connection to autocommit=False for transactions
            conn.autocommit = False

            if max_retries > 1:
                logger.debug(f"[{operation_name}] Transaction started (attempt {attempt})")

            # Yield connection for use
            yield conn

            # If we reach here, caller's code succeeded
            if max_retries > 1:
                logger.debug(f"[{operation_name}] Transaction completed successfully")
            return  # Success - exit retry loop

        except (TransientDatabaseError, PermanentDatabaseError):
            # Re-raise our custom errors without wrapping
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise

        except Exception as e:
            last_error = e

            # Rollback the failed transaction
            if conn:
                try:
                    conn.rollback()
                    if max_retries > 1:
                        logger.debug(f"[{operation_name}] Transaction rolled back")
                except Exception as rollback_error:
                    logger.warning(f"[{operation_name}] Rollback failed: {rollback_error}")

            # Classify error
            error_type = classify_db_error(e)

            if error_type == 'permanent':
                logger.error(f"[{operation_name}] Permanent error (no retry): {e}")
                raise PermanentDatabaseError(
                    f"Permanent database error in {operation_name}: {e}"
                ) from e

            # Transient error - maybe retry
            if attempt < max_retries:
                logger.warning(
                    f"[{operation_name}] Transient error (attempt {attempt}/{max_retries}): "
                    f"{e}. Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
                delay = min(delay * 2, max_delay)
            else:
                logger.error(
                    f"[{operation_name}] All {max_retries} retry attempts exhausted. "
                    f"Last error: {e}"
                )
                raise TransientDatabaseError(
                    f"Database operation '{operation_name}' failed after {max_retries} attempts: {e}"
                ) from e

        finally:
            # ALWAYS return connection to pool
            if conn:
                try:
                    connection_pool.putconn(conn)
                    if max_retries > 1:
                        logger.debug(f"[{operation_name}] Connection returned to pool")
                except Exception as putconn_error:
                    logger.error(f"[{operation_name}] Failed to return connection: {putconn_error}")
                conn = None

    # Safety fallback - should not be reached
    if last_error:
        raise TransientDatabaseError(
            f"Database operation '{operation_name}' failed: {last_error}"
        ) from last_error


def with_db_transaction(
    operation_name: str = None,
    max_retries: int = 3,
    initial_delay: float = 0.5
) -> Callable:
    """
    Decorator that wraps a method in a database transaction with retry.

    The decorated method must be a method of a class that has `self.db_pool`.
    The method will receive `conn` as its first argument (after self),
    which is an active database connection with a transaction started.

    Args:
        operation_name: Name for logging (defaults to method name)
        max_retries: Maximum retry attempts (default 3)
        initial_delay: Initial retry delay in seconds (default 0.5)

    Example:
        @with_db_transaction(operation_name="save_entity")
        def _save_entity(self, conn, entity_id, data):
            with conn.cursor() as cursor:
                cursor.execute(...)
            conn.commit()
            return {'success': True}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            name = operation_name or func.__name__

            with utf8_database_connection(
                self.db_pool,
                max_retries=max_retries,
                initial_delay=initial_delay,
                operation_name=name
            ) as conn:
                return func(self, conn, *args, **kwargs)

        return wrapper
    return decorator


def clean_text_for_database(text: str, preserve_line_breaks: bool = False) -> str:
    """
    Clean text for safe database storage.
    
    Args:
        text: Input text
        preserve_line_breaks: Keep paragraph/newline structure while still
            removing unsafe control characters.
        
    Returns:
        Cleaned text safe for database storage
    """
    if not text:
        return ""
    
    # Ensure UTF-8 encoding
    text = ensure_utf8_text(text)
    
    # Remove null bytes that can cause PostgreSQL issues
    text = text.replace('\x00', '')
    
    # Replace other problematic control characters
    control_chars = ['\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', '\x08', 
                    '\x0b', '\x0c', '\x0e', '\x0f', '\x10', '\x11', '\x12', '\x13', 
                    '\x14', '\x15', '\x16', '\x17', '\x18', '\x19', '\x1a', '\x1b', 
                    '\x1c', '\x1d', '\x1e', '\x1f']
    
    for char in control_chars:
        text = text.replace(char, '')
    
    if preserve_line_breaks:
        # Normalize line endings first.
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Normalize spacing within each line but preserve paragraph boundaries.
        normalized_lines = []
        blank_run = 0
        for raw_line in text.split('\n'):
            line = re.sub(r'[ \t]+', ' ', raw_line).strip()
            if not line:
                blank_run += 1
                if blank_run <= 2:
                    normalized_lines.append("")
                continue

            blank_run = 0
            normalized_lines.append(line)

        text = '\n'.join(normalized_lines).strip()
    else:
        # Normalize whitespace to a single-space stream for non-prose fields.
        text = ' '.join(text.split())
    
    return text


def validate_utf8_compliance(connection_pool) -> Dict[str, Any]:
    """
    Validate UTF-8 compliance across pipeline tables.
    
    Args:
        connection_pool: Database connection pool
        
    Returns:
        Validation results
    """
    results = {
        'tables_checked': [],
        'encoding_issues': [],
        'success': True
    }
    
    # Tables and text columns to check
    tables_to_check = {
        'drafts': ['original_filename', 'file_path', 'error_message'],
        'draft_chunks': ['raw_text', 'cleaned_text'],
        'scenes': ['title', 'setting', 'original_content', 'enhanced_content'],
        'plot_issues': ['description', 'suggested_fix'],
        # 'analysis_reports': ['report_subject'],
        # 'chapters': ['title', 'content'],
        # 'final_manuscripts': ['final_content', 'processing_summary']
    }
    
    with utf8_database_connection(connection_pool) as conn:
        cursor = conn.cursor()
        
        for table, text_columns in tables_to_check.items():
            try:
                # Check if table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    )
                """, (table,))
                
                if not cursor.fetchone()[0]:
                    continue
                
                results['tables_checked'].append(table)
                
                # Check encoding for each text column
                for column in text_columns:
                    try:
                        # Check for non-UTF8 characters
                        cursor.execute(f"""
                            SELECT id, {column}
                            FROM {table}
                            WHERE {column} IS NOT NULL
                            AND NOT validate_utf8({column})
                            LIMIT 10
                        """)
                        
                        invalid_rows = cursor.fetchall()
                        
                        if invalid_rows:
                            results['encoding_issues'].append({
                                'table': table,
                                'column': column,
                                'invalid_rows': len(invalid_rows),
                                'sample_ids': [row[0] for row in invalid_rows[:5]]
                            })
                            results['success'] = False
                            
                    except psycopg2.Error:
                        # validate_utf8 function might not exist, skip
                        pass
                        
            except Exception as e:
                logger.error(f"Failed to check encoding for table {table}: {e}")
                results['encoding_issues'].append({
                    'table': table,
                    'error': str(e)
                })
                results['success'] = False
    
    return results

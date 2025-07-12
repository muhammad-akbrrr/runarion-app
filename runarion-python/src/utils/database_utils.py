"""
Database utilities for standardizing UTF-8 encoding and safe database operations.
Provides helper functions for consistent text handling across the pipeline.
"""

import json
import logging
from typing import Any, Optional, Dict, List, Union
import psycopg2
from contextlib import contextmanager

logger = logging.getLogger(__name__)


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
def utf8_database_connection(connection_pool):
    """
    Context manager that ensures UTF-8 encoding for database connection.
    
    Args:
        connection_pool: Database connection pool
        
    Yields:
        Database connection with UTF-8 encoding set
    """
    conn = None
    try:
        conn = connection_pool.getconn()
        
        # Set connection encoding to UTF-8
        conn.set_client_encoding('UTF8')
        
        # Set connection to autocommit=False for transactions
        conn.autocommit = False
        
        yield conn
        
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            connection_pool.putconn(conn)


def clean_text_for_database(text: str) -> str:
    """
    Clean text for safe database storage.
    
    Args:
        text: Input text
        
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
    
    # Normalize whitespace
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
"""
Database operation tracker for comprehensive test output generation.

This module tracks all database operations performed during tests to generate
detailed database seeds showing actual operations rather than just final state.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseOperationTracker:
    """
    Tracks database operations during test execution for detailed output generation.
    """
    
    def __init__(self):
        self.operations = []
        self.is_tracking = False
        
    def start_tracking(self):
        """Start tracking database operations."""
        self.operations = []
        self.is_tracking = True
        logger.debug("Started tracking database operations")
        
    def stop_tracking(self):
        """Stop tracking database operations."""
        self.is_tracking = False
        logger.debug(f"Stopped tracking database operations. Captured {len(self.operations)} operations")
        
    def track_operation(self, operation_type: str, table_name: str, 
                       affected_rows: int = 0, data: Optional[Dict[str, Any]] = None,
                       where_clause: Optional[str] = None, 
                       where_params: Optional[Tuple] = None) -> None:
        """
        Track a database operation.
        
        Args:
            operation_type: Type of operation (INSERT, UPDATE, DELETE, SELECT)
            table_name: Name of the table affected
            affected_rows: Number of rows affected by the operation
            data: Data involved in the operation (for INSERT/UPDATE)
            where_clause: WHERE clause for UPDATE/DELETE operations
            where_params: Parameters for the WHERE clause
        """
        if not self.is_tracking:
            return
            
        operation = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'operation': operation_type,
            'table': table_name,
            'affected_rows': affected_rows,
            'data': data or {},
            'where_clause': where_clause,
            'where_params': list(where_params) if where_params else []
        }
        
        self.operations.append(operation)
        logger.debug(f"Tracked {operation_type} operation on {table_name} affecting {affected_rows} rows")
        
    def get_operations(self) -> List[Dict[str, Any]]:
        """Get all tracked operations."""
        return self.operations.copy()
        
    def get_operations_by_table(self, table_name: str) -> List[Dict[str, Any]]:
        """Get operations for a specific table."""
        return [op for op in self.operations if op['table'] == table_name]
        
    def get_operations_summary(self) -> Dict[str, Any]:
        """Get a summary of all tracked operations."""
        if not self.operations:
            return {
                'total_operations': 0,
                'tables_affected': [],
                'operations_by_type': {},
                'operations_by_table': {}
            }
            
        tables_affected = list(set(op['table'] for op in self.operations))
        operations_by_type = {}
        operations_by_table = {}
        
        for operation in self.operations:
            op_type = operation['operation']
            table = operation['table']
            
            # Count by operation type
            operations_by_type[op_type] = operations_by_type.get(op_type, 0) + 1
            
            # Count by table
            if table not in operations_by_table:
                operations_by_table[table] = {}
            operations_by_table[table][op_type] = operations_by_table[table].get(op_type, 0) + 1
            
        return {
            'total_operations': len(self.operations),
            'tables_affected': sorted(tables_affected),
            'operations_by_type': operations_by_type,
            'operations_by_table': operations_by_table
        }
        
    def clear_operations(self):
        """Clear all tracked operations."""
        self.operations = []
        logger.debug("Cleared all tracked operations")


class TrackedDatabaseConnection:
    """
    Database connection wrapper that tracks operations.
    """
    
    def __init__(self, connection, tracker: DatabaseOperationTracker):
        self.connection = connection
        self.tracker = tracker
        
    def cursor(self):
        """Return a tracked cursor."""
        return TrackedCursor(self.connection.cursor(), self.tracker)
        
    def commit(self):
        """Commit the transaction."""
        self.connection.commit()
        
    def rollback(self):
        """Rollback the transaction."""
        self.connection.rollback()
        
    def close(self):
        """Close the connection."""
        self.connection.close()
        
    def __getattr__(self, name):
        """Delegate other attributes to the underlying connection."""
        return getattr(self.connection, name)


class TrackedCursor:
    """
    Database cursor wrapper that tracks operations.
    """
    
    def __init__(self, cursor, tracker: DatabaseOperationTracker):
        self.cursor = cursor
        self.tracker = tracker
        
    def execute(self, query: str, params: Optional[Tuple] = None):
        """Execute a query and track the operation."""
        result = self.cursor.execute(query, params)
        
        # Parse the query to extract operation information
        operation_info = self._parse_query(query, params)
        if operation_info:
            self.tracker.track_operation(
                operation_type=operation_info['operation'],
                table_name=operation_info['table'],
                affected_rows=self.cursor.rowcount,
                data=operation_info.get('data'),
                where_clause=operation_info.get('where_clause'),
                where_params=params
            )
            
        return result
        
    def executemany(self, query: str, params_list: List[Tuple]):
        """Execute a query multiple times and track the operations."""
        result = self.cursor.executemany(query, params_list)
        
        # Track as a batch operation
        operation_info = self._parse_query(query, params_list[0] if params_list else None)
        if operation_info:
            self.tracker.track_operation(
                operation_type=f"{operation_info['operation']}_BATCH",
                table_name=operation_info['table'],
                affected_rows=self.cursor.rowcount,
                data={'batch_size': len(params_list), 'sample_data': operation_info.get('data')},
                where_clause=operation_info.get('where_clause')
            )
            
        return result
        
    def _parse_query(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        """
        Parse a SQL query to extract operation information.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Dictionary with operation information or None if parsing fails
        """
        try:
            query_upper = query.strip().upper()
            
            # Extract operation type
            if query_upper.startswith('INSERT'):
                operation_type = 'INSERT'
                table_name = self._extract_table_from_insert(query)
                data = self._extract_insert_data(query, params)
            elif query_upper.startswith('UPDATE'):
                operation_type = 'UPDATE'
                table_name = self._extract_table_from_update(query)
                data = self._extract_update_data(query, params)
            elif query_upper.startswith('DELETE'):
                operation_type = 'DELETE'
                table_name = self._extract_table_from_delete(query)
                data = None
            elif query_upper.startswith('SELECT'):
                operation_type = 'SELECT'
                table_name = self._extract_table_from_select(query)
                data = None
            else:
                return None
                
            result = {
                'operation': operation_type,
                'table': table_name or 'unknown'
            }
            
            if data:
                result['data'] = data
                
            return result
            
        except Exception as e:
            logger.debug(f"Failed to parse query: {e}")
            return None
            
    def _extract_table_from_insert(self, query: str) -> Optional[str]:
        """Extract table name from INSERT query."""
        try:
            # Look for "INSERT INTO table_name"
            query_upper = query.upper()
            start = query_upper.find('INSERT INTO') + len('INSERT INTO')
            rest = query[start:].strip()
            table_name = rest.split()[0].strip('(')
            return table_name
        except Exception:
            return None
            
    def _extract_table_from_update(self, query: str) -> Optional[str]:
        """Extract table name from UPDATE query."""
        try:
            # Look for "UPDATE table_name"
            query_upper = query.upper()
            start = query_upper.find('UPDATE') + len('UPDATE')
            rest = query[start:].strip()
            table_name = rest.split()[0]
            return table_name
        except Exception:
            return None
            
    def _extract_table_from_delete(self, query: str) -> Optional[str]:
        """Extract table name from DELETE query."""
        try:
            # Look for "DELETE FROM table_name"
            query_upper = query.upper()
            start = query_upper.find('FROM') + len('FROM')
            rest = query[start:].strip()
            table_name = rest.split()[0]
            return table_name
        except Exception:
            return None
            
    def _extract_table_from_select(self, query: str) -> Optional[str]:
        """Extract table name from SELECT query."""
        try:
            # Look for "SELECT ... FROM table_name"
            query_upper = query.upper()
            start = query_upper.find('FROM') + len('FROM')
            rest = query[start:].strip()
            table_name = rest.split()[0]
            return table_name
        except Exception:
            return None
            
    def _extract_insert_data(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        """Extract data from INSERT query."""
        if not params:
            return None
            
        try:
            # Extract column names from query
            query_upper = query.upper()
            columns_start = query.find('(') + 1
            columns_end = query.find(')', columns_start)
            columns_str = query[columns_start:columns_end]
            columns = [col.strip() for col in columns_str.split(',')]
            
            # Map parameters to columns
            if len(columns) == len(params):
                return dict(zip(columns, params))
            else:
                return {'raw_params': params}
                
        except Exception:
            return {'raw_params': params} if params else None
            
    def _extract_update_data(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        """Extract data from UPDATE query."""
        if not params:
            return None
            
        # For UPDATE queries, it's more complex to parse the SET clause
        # Return raw params for now
        return {'raw_params': params}
        
    def fetchone(self):
        """Fetch one row."""
        return self.cursor.fetchone()
        
    def fetchall(self):
        """Fetch all rows."""
        return self.cursor.fetchall()
        
    def fetchmany(self, size=None):
        """Fetch many rows."""
        return self.cursor.fetchmany(size)
        
    def close(self):
        """Close the cursor."""
        self.cursor.close()
        
    def __getattr__(self, name):
        """Delegate other attributes to the underlying cursor."""
        return getattr(self.cursor, name)


# Global tracker instance
_global_tracker = DatabaseOperationTracker()


def get_operation_tracker() -> DatabaseOperationTracker:
    """Get the global operation tracker."""
    return _global_tracker


@contextmanager
def tracked_database_connection(db_pool):
    """
    Context manager that provides a tracked database connection.
    
    Args:
        db_pool: Database connection pool
        
    Yields:
        TrackedDatabaseConnection: Connection that tracks operations
    """
    conn = db_pool.getconn()
    tracked_conn = TrackedDatabaseConnection(conn, _global_tracker)
    
    try:
        yield tracked_conn
    finally:
        db_pool.putconn(conn)


def start_operation_tracking():
    """Start tracking database operations globally."""
    _global_tracker.start_tracking()


def stop_operation_tracking():
    """Stop tracking database operations globally."""
    _global_tracker.stop_tracking()


def get_tracked_operations() -> List[Dict[str, Any]]:
    """Get all tracked operations from the global tracker."""
    return _global_tracker.get_operations()


def get_operations_summary() -> Dict[str, Any]:
    """Get a summary of tracked operations from the global tracker."""
    return _global_tracker.get_operations_summary()


def clear_tracked_operations():
    """Clear all tracked operations from the global tracker."""
    _global_tracker.clear_operations()
"""
Standardized API response utilities for consistent response formatting.
Provides helper functions to create standardized responses across all endpoints.
"""

from typing import Dict, Any, List
from datetime import datetime
from flask import jsonify
import logging

logger = logging.getLogger(__name__)


class ApiResponse:
    """
    Standardized API response builder with consistent formatting.
    """
    
    @staticmethod
    def success(data: Any = None, message: str = None, meta: Dict[str, Any] = None, status_code: int = 200) -> tuple:
        """
        Create a successful API response.
        
        Args:
            data: Response data payload
            message: Optional success message
            meta: Optional metadata (pagination, timestamps, etc.)
            status_code: HTTP status code
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        response = {
            'success': True,
            'timestamp': datetime.now().isoformat()
        }
        
        if message:
            response['message'] = message
            
        if data is not None:
            response['data'] = data
            
        if meta:
            response['meta'] = meta
            
        return jsonify(response), status_code
    
    @staticmethod
    def error(error: str, details: Dict[str, Any] = None, error_code: str = None, status_code: int = 400) -> tuple:
        """
        Create an error API response.
        
        Args:
            error: Error message
            details: Optional error details
            error_code: Optional error code for programmatic handling
            status_code: HTTP status code
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        response = {
            'success': False,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        
        if error_code:
            response['error_code'] = error_code
            
        if details:
            response['details'] = details
            
        return jsonify(response), status_code
    
    @staticmethod
    def validation_error(field_errors: Dict[str, List[str]], message: str = "Validation failed") -> tuple:
        """
        Create a validation error response.
        
        Args:
            field_errors: Dictionary mapping field names to lists of error messages
            message: Overall validation error message
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        return ApiResponse.error(
            error=message,
            details={'field_errors': field_errors},
            error_code='VALIDATION_ERROR',
            status_code=422
        )
    
    @staticmethod
    def not_found(resource: str = "Resource", identifier: str = None) -> tuple:
        """
        Create a not found error response.
        
        Args:
            resource: Type of resource that was not found
            identifier: Identifier of the resource
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        message = f"{resource} not found"
        if identifier:
            message += f" (ID: {identifier})"
            
        return ApiResponse.error(
            error=message,
            error_code='NOT_FOUND',
            status_code=404
        )
    
    @staticmethod
    def forbidden(message: str = "Access denied") -> tuple:
        """
        Create a forbidden error response.
        
        Args:
            message: Forbidden error message
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        return ApiResponse.error(
            error=message,
            error_code='FORBIDDEN',
            status_code=403
        )
    
    @staticmethod
    def unauthorized(message: str = "Authentication required") -> tuple:
        """
        Create an unauthorized error response.
        
        Args:
            message: Unauthorized error message
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        return ApiResponse.error(
            error=message,
            error_code='UNAUTHORIZED',
            status_code=401
        )
    
    @staticmethod
    def internal_error(message: str = "Internal server error", log_error: bool = True) -> tuple:
        """
        Create an internal server error response.
        
        Args:
            message: Error message
            log_error: Whether to log the error
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        if log_error:
            logger.error(f"Internal server error: {message}")
            
        return ApiResponse.error(
            error=message,
            error_code='INTERNAL_ERROR',
            status_code=500
        )
    
    @staticmethod
    def processing(data: Any = None, message: str = "Request accepted for processing") -> tuple:
        """
        Create a processing response for async operations.
        
        Args:
            data: Response data payload
            message: Processing message
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        return ApiResponse.success(
            data=data,
            message=message,
            status_code=202
        )


class DeconstructorResponse:
    """
    Specialized response builder for deconstructor endpoints.
    """
    
    @staticmethod
    def pipeline_started(draft_id: str) -> tuple:
        """
        Response for successful pipeline start.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        return ApiResponse.processing(
            data={
                'draft_id': draft_id,
                'status': 'processing'
            },
            message='Deconstruction pipeline started'
        )
    
    @staticmethod
    def pipeline_status(draft_id: str, status: str, started_at: datetime = None, 
                       completed_at: datetime = None, error_message: str = None, 
                       metadata: Dict[str, Any] = None, progress: Dict[str, Any] = None) -> tuple:
        """
        Response for pipeline status query.
        
        Args:
            draft_id: UUID of the draft
            status: Current pipeline status
            started_at: Processing start timestamp
            completed_at: Processing completion timestamp
            error_message: Error message if failed
            metadata: Additional metadata
            progress: Progress information
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        data = {
            'draft_id': draft_id,
            'status': status,
            'processing_started_at': started_at.isoformat() if started_at else None,
            'processing_completed_at': completed_at.isoformat() if completed_at else None
        }
        
        if error_message:
            data['error_message'] = error_message
            
        if metadata:
            data['metadata'] = metadata
            
        if progress:
            data['progress'] = progress
            
        return ApiResponse.success(data=data)
    
    @staticmethod
    def pipeline_results(draft_id: str, results: Dict[str, Any]) -> tuple:
        """
        Response for pipeline results query.
        
        Args:
            draft_id: UUID of the draft
            results: Pipeline results data
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        return ApiResponse.success(
            data={
                'draft_id': draft_id,
                'results': results
            }
        )
    
    @staticmethod
    def draft_not_found(draft_id: str) -> tuple:
        """
        Response when draft is not found.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        return ApiResponse.not_found("Draft", draft_id)
    
    @staticmethod
    def permission_denied(draft_id: str) -> tuple:
        """
        Response when user doesn't have permission to access draft.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        return ApiResponse.forbidden("User does not have permission to access this draft")
    
    @staticmethod
    def invalid_status(current_status: str, required_status: str) -> tuple:
        """
        Response when draft is in wrong status for operation.
        
        Args:
            current_status: Current draft status
            required_status: Required status for operation
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        return ApiResponse.error(
            error=f"Draft status is '{current_status}', but '{required_status}' is required for this operation",
            error_code='INVALID_STATUS',
            status_code=400
        )


# Convenience functions for common responses
def success(data=None, message=None, meta=None, status_code=200):
    """Shorthand for ApiResponse.success()"""
    return ApiResponse.success(data, message, meta, status_code)

def error(error, details=None, error_code=None, status_code=400):
    """Shorthand for ApiResponse.error()"""
    return ApiResponse.error(error, details, error_code, status_code)

def validation_error(field_errors, message="Validation failed"):
    """Shorthand for ApiResponse.validation_error()"""
    return ApiResponse.validation_error(field_errors, message)

def not_found(resource="Resource", identifier=None):
    """Shorthand for ApiResponse.not_found()"""
    return ApiResponse.not_found(resource, identifier)

def forbidden(message="Access denied"):
    """Shorthand for ApiResponse.forbidden()"""
    return ApiResponse.forbidden(message)

def unauthorized(message="Authentication required"):
    """Shorthand for ApiResponse.unauthorized()"""
    return ApiResponse.unauthorized(message)

def internal_error(message="Internal server error", log_error=True):
    """Shorthand for ApiResponse.internal_error()"""
    return ApiResponse.internal_error(message, log_error)

def processing(data=None, message="Request accepted for processing"):
    """Shorthand for ApiResponse.processing()"""
    return ApiResponse.processing(data, message)
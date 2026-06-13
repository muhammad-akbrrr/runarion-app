/**
 * Error handling utilities for the editor
 * Provides centralized error logging, categorization, and user-friendly messaging
 */

export interface ErrorContext {
    component?: string;
    action?: string;
    projectId?: string;
    workspaceId?: string;
    chapterOrder?: number;
    [key: string]: any;
}

export interface ErrorDetails {
    message: string;
    type: string;
    isRetryable: boolean;
    userMessage: string;
    context?: ErrorContext;
}

/**
 * Error types for categorization
 */
export enum ErrorType {
    NETWORK = 'network',
    VALIDATION = 'validation',
    AUTHENTICATION = 'authentication',
    LOCKED = 'locked',
    NOT_FOUND = 'not_found',
    SERVER = 'server',
    TIMEOUT = 'timeout',
    QUOTA = 'quota',
    UNKNOWN = 'unknown',
}

/**
 * Categorize an error based on its properties
 */
export function categorizeError(error: any): ErrorType {
    if (!error) return ErrorType.UNKNOWN;

    // Check error message
    const message = error.message?.toLowerCase() || '';
    
    if (message.includes('network') || message.includes('connection')) {
        return ErrorType.NETWORK;
    }
    
    if (message.includes('timeout')) {
        return ErrorType.TIMEOUT;
    }
    
    if (message.includes('quota') || message.includes('limit')) {
        return ErrorType.QUOTA;
    }
    
    if (message.includes('validation')) {
        return ErrorType.VALIDATION;
    }
    
    if (message.includes('authentication') || message.includes('unauthorized')) {
        return ErrorType.AUTHENTICATION;
    }
    
    if (message.includes('not found')) {
        return ErrorType.NOT_FOUND;
    }

    // Check HTTP status code
    const status = error.status || error.response?.status;
    
    if (status === 401 || status === 403) {
        return ErrorType.AUTHENTICATION;
    }

    if (status === 423) {
        return ErrorType.LOCKED;
    }
    
    if (status === 404) {
        return ErrorType.NOT_FOUND;
    }
    
    if (status === 422) {
        return ErrorType.VALIDATION;
    }
    
    if (status === 429) {
        return ErrorType.QUOTA;
    }
    
    if (status === 408 || status === 504) {
        return ErrorType.TIMEOUT;
    }
    
    if (status >= 500 && status < 600) {
        return ErrorType.SERVER;
    }
    
    // Check error code
    if (error.code === 'ECONNREFUSED' || error.code === 'ETIMEDOUT') {
        return ErrorType.NETWORK;
    }

    return ErrorType.UNKNOWN;
}

/**
 * Determine if an error is retryable
 */
export function isRetryableError(error: any): boolean {
    const type = categorizeError(error);
    
    // Network, timeout, server, and quota errors are typically retryable
    return [
        ErrorType.NETWORK,
        ErrorType.TIMEOUT,
        ErrorType.SERVER,
        ErrorType.QUOTA,
    ].includes(type);
}

/**
 * Get a user-friendly error message
 */
export function getUserFriendlyMessage(error: any, context?: ErrorContext): string {
    const type = categorizeError(error);
    
    switch (type) {
        case ErrorType.NETWORK:
            return 'Network connection error. Please check your internet connection and try again.';
        
        case ErrorType.TIMEOUT:
            return 'Request timed out. Please try again.';
        
        case ErrorType.QUOTA:
            return 'Usage quota exceeded. Please try again later or upgrade your plan.';
        
        case ErrorType.VALIDATION:
            if (error.errors) {
                // Extract first validation error
                const firstError = Object.values(error.errors)[0];
                if (Array.isArray(firstError) && firstError.length > 0) {
                    return firstError[0] as string;
                }
            }
            return 'Invalid input. Please check your data and try again.';

        case ErrorType.LOCKED:
            return error.message || error.error || 'This project is locked by an active operation.';
        
        case ErrorType.AUTHENTICATION:
            return 'Authentication failed. Please refresh the page and log in again.';
        
        case ErrorType.NOT_FOUND:
            if (context?.action === 'save') {
                return 'Project or chapter not found. Please refresh the page.';
            }
            return 'Resource not found. Please refresh the page.';
        
        case ErrorType.SERVER:
            return 'Server error. Please try again in a moment.';
        
        case ErrorType.UNKNOWN:
        default:
            if (error.message) {
                return error.message;
            }
            return 'An unexpected error occurred. Please try again.';
    }
}

/**
 * Parse error details from various error formats
 */
export function parseErrorDetails(error: any, context?: ErrorContext): ErrorDetails {
    const type = categorizeError(error);
    const isRetryable = isRetryableError(error);
    const userMessage = getUserFriendlyMessage(error, context);
    
    return {
        message: error.message || 'Unknown error',
        type: type,
        isRetryable,
        userMessage,
        context,
    };
}

/**
 * Log error to console with context
 */
export function logError(error: any, context?: ErrorContext): void {
    const details = parseErrorDetails(error, context);
    
    console.error('[Error Handler]', {
        type: details.type,
        message: details.message,
        isRetryable: details.isRetryable,
        userMessage: details.userMessage,
        context: details.context,
        originalError: error,
        timestamp: new Date().toISOString(),
    });
}

/**
 * Handle error with logging and optional callback
 */
export function handleError(
    error: any,
    context?: ErrorContext,
    onError?: (details: ErrorDetails) => void
): ErrorDetails {
    const details = parseErrorDetails(error, context);
    
    // Log the error
    logError(error, context);
    
    // Call optional error callback
    if (onError) {
        onError(details);
    }
    
    return details;
}

/**
 * Create a retry-aware error handler
 */
export function createRetryHandler(
    maxRetries: number = 3,
    onRetry?: (attempt: number, error: any) => void
) {
    let retryCount = 0;
    
    return {
        shouldRetry: (error: any): boolean => {
            const canRetry = isRetryableError(error) && retryCount < maxRetries;
            
            if (canRetry) {
                retryCount++;
                if (onRetry) {
                    onRetry(retryCount, error);
                }
            }
            
            return canRetry;
        },
        
        reset: (): void => {
            retryCount = 0;
        },
        
        getRetryCount: (): number => {
            return retryCount;
        },
    };
}

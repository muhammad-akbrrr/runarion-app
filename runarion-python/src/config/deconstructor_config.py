"""
Stage 3 Configuration Constants
Centralized configuration for Scene Detection and Extraction stage.
"""

class Stage3Config:
    """
    Configuration constants for Stage 3: Scene Detection and Extraction
    """
    
    # Scene count validation
    MIN_SCENES_PER_CHUNK = 8
    MAX_SCENES_PER_CHUNK = 20
    OPTIMAL_SCENES_RANGE = (12, 16)  # Optimal range mentioned in prompt template
    
    # Content validation
    # Increased from 50 to 150 chars to align with Stage 3 hydration threshold
    MIN_SCENE_CONTENT_LENGTH = 150  # Minimum characters for scene content
    
    # Retry configuration (Stage 3 scene-count loop)
    MAX_RETRY_ATTEMPTS = 3  # Initial attempt + 2 retries
    RETRY_BASE_DELAY = 1.0  # Base delay in seconds for exponential backoff
    RETRY_RATE_LIMIT_DELAY = 0.5  # Rate limiting delay between API calls

    # API retry multipliers
    NORMAL_RETRY_MULTIPLIER = 2  # Normal exponential backoff multiplier
    OVERLOAD_RETRY_MULTIPLIER = 3  # Aggressive multiplier for 503 errors

    # 429 rate-limit cap: never sleep longer than this when honouring retryDelay
    MAX_RATE_LIMIT_SLEEP_SECONDS = 90

    # ------------------------------------------------------------------
    # Shared LLM transient-error retry defaults (used by call_llm_with_retry
    # across all pipeline phases and stages).
    # ------------------------------------------------------------------
    LLM_MAX_RETRY_ATTEMPTS = 5    # total attempts (initial + 4 retries)
    LLM_RETRY_BASE_DELAY   = 2.0  # seconds; doubles each attempt
    LLM_RETRY_MAX_DELAY    = 120.0  # hard cap per sleep (seconds)
    LLM_RETRY_JITTER       = 1.0  # random 0–1s added per sleep
    
    # Performance expectations
    MAX_PROCESSING_TIME_SECONDS = 300  # 5 minutes total processing time
    MAX_TIME_PER_CHUNK_SECONDS = 120  # 2 minutes per chunk
    
    # Database configuration
    BULK_INSERT_BATCH_SIZE = 100  # Batch size for bulk scene insertion
    
    # Text processing
    MARKDOWN_JSON_WRAPPER_START = "```json"
    MARKDOWN_JSON_WRAPPER_END = "```"
    
    @classmethod
    def validate_scene_count(cls, scene_count: int) -> bool:
        """
        Validate that scene count is within the required range.
        
        Args:
            scene_count: Number of scenes to validate
            
        Returns:
            True if scene count is valid (8-20), False otherwise
        """
        return cls.MIN_SCENES_PER_CHUNK <= scene_count <= cls.MAX_SCENES_PER_CHUNK
    
    @classmethod
    def is_optimal_scene_count(cls, scene_count: int) -> bool:
        """
        Check if scene count is within optimal range.
        
        Args:
            scene_count: Number of scenes to check
            
        Returns:
            True if scene count is in optimal range (12-16), False otherwise
        """
        return cls.OPTIMAL_SCENES_RANGE[0] <= scene_count <= cls.OPTIMAL_SCENES_RANGE[1]
    
    @classmethod
    def validate_scene_content_length(cls, content: str) -> bool:
        """
        Validate that scene content meets minimum length requirement.
        
        Args:
            content: Scene content to validate
            
        Returns:
            True if content meets minimum length requirement, False otherwise
        """
        return len(content.strip()) >= cls.MIN_SCENE_CONTENT_LENGTH
    
    @classmethod
    def parse_rate_limit_delay(cls, error_message: str) -> float:
        """
        Extract the server-prescribed retry delay from a Gemini 429 error message.

        Gemini embeds a human-readable delay in its RESOURCE_EXHAUSTED responses, e.g.
        "Please retry in 38.062874945s."  This parses that value and caps it at
        MAX_RATE_LIMIT_SLEEP_SECONDS so we never stall a thread indefinitely.

        Args:
            error_message: The error string from the failed generation call.

        Returns:
            Seconds to sleep, or 0.0 if no delay hint was found in the message.
        """
        import re
        match = re.search(r'retry in ([\d.]+)s', str(error_message))
        if match:
            prescribed = float(match.group(1))
            return min(prescribed + 2.0, cls.MAX_RATE_LIMIT_SLEEP_SECONDS)
        return 0.0

    @classmethod
    def get_retry_delay(cls, attempt: int, is_overload_error: bool = False,
                        error_message: str = '') -> float:
        """
        Calculate retry delay based on attempt number and error type.

        If a Gemini 429 retryDelay hint is present in error_message, that value
        takes precedence over the normal exponential-backoff calculation so we
        honour the server's prescribed window instead of hammering immediately.

        Args:
            attempt: Retry attempt number (0-based)
            is_overload_error: Whether this is a 503/overload error
            error_message: Optional error string; used to extract 429 retryDelay hint

        Returns:
            Delay in seconds
        """
        # Honour Gemini's prescribed retry window for 429s
        if '429' in str(error_message) or 'RESOURCE_EXHAUSTED' in str(error_message):
            prescribed = cls.parse_rate_limit_delay(error_message)
            if prescribed > 0:
                return prescribed

        multiplier = cls.OVERLOAD_RETRY_MULTIPLIER if is_overload_error else cls.NORMAL_RETRY_MULTIPLIER
        return cls.RETRY_BASE_DELAY * (multiplier ** attempt)
    
    @classmethod
    def get_config_summary(cls) -> dict:
        """
        Get a summary of all configuration values.
        
        Returns:
            Dictionary containing all configuration constants
        """
        return {
            'scene_count_range': f"{cls.MIN_SCENES_PER_CHUNK}-{cls.MAX_SCENES_PER_CHUNK}",
            'optimal_scene_range': f"{cls.OPTIMAL_SCENES_RANGE[0]}-{cls.OPTIMAL_SCENES_RANGE[1]}",
            'min_content_length': cls.MIN_SCENE_CONTENT_LENGTH,
            'max_retry_attempts': cls.MAX_RETRY_ATTEMPTS,
            'retry_base_delay': cls.RETRY_BASE_DELAY,
            'rate_limit_delay': cls.RETRY_RATE_LIMIT_DELAY,
            'max_processing_time': cls.MAX_PROCESSING_TIME_SECONDS,
            'max_time_per_chunk': cls.MAX_TIME_PER_CHUNK_SECONDS,
            'bulk_insert_batch_size': cls.BULK_INSERT_BATCH_SIZE
        }
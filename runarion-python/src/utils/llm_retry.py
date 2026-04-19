"""
Shared LLM transient-error retry utility.

Provides call_llm_with_retry(), a thin wrapper that retries any LLM call
when the provider returns a transient error (503 overload, 429 rate-limit).
Non-transient failures (bad prompt, blocked content, JSON errors, etc.) are
returned immediately without retrying.

Usage:
    from utils.llm_retry import call_llm_with_retry

    response = call_llm_with_retry(
        lambda: self.generation_engine.generate(skip_quota=True)
    )

The wrapper is transparent to the caller — it always returns a
BaseGenerationResponse, so existing response.success checks and fallback
logic in each stage are completely unaffected.
"""

import logging
import random
import re
import time
from typing import Callable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Transient error detection
# ---------------------------------------------------------------------------

# Keywords that identify a transient / server-side error worth retrying.
# Matched case-insensitively against response.error_message.
_TRANSIENT_SIGNALS = (
    '503',
    'overload',
    'unavailable',
    'service unavailable',
    '429',
    'resource_exhausted',
    'rate limit',
    'rate_limit',
    'too many requests',
    'high demand',
    'quota',
    'temporarily',
)


def _is_transient(error_message: str) -> bool:
    """Return True if the error message indicates a transient API condition."""
    lowered = error_message.lower()
    return any(signal in lowered for signal in _TRANSIENT_SIGNALS)


def _parse_retry_after(error_message: str, cap: float) -> float:
    """
    Extract the server-prescribed retry delay from a Gemini 429 message.

    Gemini embeds a human-readable delay, e.g. "Please retry in 38.06s."
    Returns the prescribed value + 2s safety margin, capped at cap.
    Returns 0.0 if no hint found.
    """
    match = re.search(r'retry in ([\d.]+)s', str(error_message))
    if match:
        prescribed = float(match.group(1))
        return min(prescribed + 2.0, cap)
    return 0.0


# ---------------------------------------------------------------------------
# Main utility
# ---------------------------------------------------------------------------

def call_llm_with_retry(
    generate_fn: Callable,
    *,
    max_attempts: int = 5,
    base_delay: float = 2.0,
    max_delay: float = 120.0,
    jitter: float = 1.0,
):
    """
    Call generate_fn() and retry on transient LLM errors with exponential
    backoff and jitter.

    Args:
        generate_fn:   Zero-argument callable that performs the LLM call and
                       returns a BaseGenerationResponse (e.g.
                       ``lambda: engine.generate(skip_quota=True)``).
        max_attempts:  Total number of attempts (initial + retries).
                       Default 5 -> up to 4 retries.
        base_delay:    Base sleep in seconds for exponential backoff.
                       Actual delay = min(base * 2^attempt, max_delay) + jitter.
        max_delay:     Hard cap on sleep time in seconds (default 120s).
        jitter:        Upper bound for the random jitter added to every sleep
                       (default 1.0s). Prevents thundering herd.

    Returns:
        The BaseGenerationResponse from the final attempt, regardless of
        whether it succeeded or not. The caller is responsible for checking
        response.success as before.

    Notes:
        - Only transient errors trigger a retry (503 overload, 429 rate-limit,
          quota exhaustion, "high demand", etc.).
        - Non-transient failures are returned immediately after the first
          attempt — no unnecessary delay.
        - Gemini's "Please retry in Xs." hint is honoured for 429 responses
          and takes precedence over the exponential-backoff calculation.
        - If generate_fn() raises an exception (which providers normally
          don't — they return error responses), the exception propagates
          unchanged so nothing is silently swallowed.
    """
    response = None

    for attempt in range(max_attempts):
        response = generate_fn()

        # Success — return immediately
        if response is None or response.success:
            return response

        error_msg = getattr(response, 'error_message', '') or ''

        # Non-transient failure — return immediately, don't waste time
        if not _is_transient(error_msg):
            return response

        # Transient failure — decide whether to retry
        is_last_attempt = (attempt == max_attempts - 1)
        if is_last_attempt:
            logger.warning(
                f"LLM transient error on final attempt {attempt + 1}/{max_attempts}: "
                f"{error_msg[:200]}"
            )
            return response

        # Calculate sleep duration
        prescribed = _parse_retry_after(error_msg, max_delay)
        if prescribed > 0:
            sleep_secs = prescribed
        else:
            sleep_secs = min(base_delay * (2 ** attempt), max_delay)
        sleep_secs += random.uniform(0, jitter)

        logger.warning(
            f"LLM transient error (attempt {attempt + 1}/{max_attempts}), "
            f"retrying in {sleep_secs:.1f}s: {error_msg[:200]}"
        )
        time.sleep(sleep_secs)

    return response

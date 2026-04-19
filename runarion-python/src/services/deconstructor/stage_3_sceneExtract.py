"""
Stage 3: Scene Detection and Extraction
Analyzes cleaned text to identify and extract distinct scenes.
"""

import json
import logging
import time
from typing import Dict, Any, List, Tuple
from .prompt_template import DeconstructorPrompts
from utils.database_utils import clean_text_for_database
from utils.json_response_parser import parse_scene_detection_response, JSONResponseParser
from config.deconstructor_config import Stage3Config
from utils.llm_retry import call_llm_with_retry
from .base_stage import BasePipelineStage, PipelineStageResult, PipelineStageContext

logger = logging.getLogger(__name__)

class SceneDetectionStage(BasePipelineStage):
    """
    Stage 3 of the deconstruction pipeline.
    Detects scene boundaries and extracts individual scenes with metadata.
    """
    
    def __init__(self, db_pool, generation_engine):
        """
        Initialize the scene detection stage.
        
        Args:
            db_pool: Database connection pool
            generation_engine: AI generation engine
        """
        super().__init__(db_pool, "SceneDetectionStage", generation_engine)
        self.prompt_template = DeconstructorPrompts()
    
    def _execute_stage(self, context: PipelineStageContext) -> PipelineStageResult:
        """
        Execute Stage 3: Scene detection and extraction using per-chunk processing.
        
        Args:
            context: Stage execution context containing draft_id
            
        Returns:
            PipelineStageResult with stage execution results
        """
        draft_id = context.draft_id
        
        try:
            # Get chunk data from database
            chunk_data = self._get_chunk_data(context)
            
            if not chunk_data:
                return PipelineStageResult.success_result(
                    self.stage_name,
                    scenes_extracted=0,
                    scenes_stored=0,
                    chunks_processed=0,
                    message='No chunks to process'
                )
            
            self.logger.info(f"Processing {len(chunk_data)} chunks for draft {draft_id}")
            
            # Process each chunk individually
            all_scenes = []
            current_scene_number = 1
            chunks_processed = 0
            total_text_length = 0

            # Accumulate hydration stats across chunks
            total_hydration_stats = {
                'attempted': 0,
                'succeeded': 0,
                'failed': 0,
                'success_rate': 1.0
            }

            for chunk_number, cleaned_text in chunk_data:
                if not cleaned_text.strip():
                    self.logger.warning(f"Skipping empty chunk {chunk_number}")
                    continue

                self.logger.info(f"Processing chunk {chunk_number} ({len(cleaned_text)} characters)")
                total_text_length += len(cleaned_text)

                # Process this chunk to extract 8-20 scenes
                chunk_scenes = self._process_chunk(chunk_number, cleaned_text, current_scene_number)

                if chunk_scenes:
                    # Hydrate scene content from original chunk using markers when content is truncated/missing
                    hydrated, hydration_result = self._hydrate_scene_contents_from_markers(cleaned_text, chunk_scenes)

                    # Accumulate hydration stats
                    total_hydration_stats['attempted'] += hydration_result['attempted']
                    total_hydration_stats['succeeded'] += hydration_result['succeeded']
                    total_hydration_stats['failed'] += hydration_result['failed']

                    all_scenes.extend(hydrated)
                    current_scene_number += len(chunk_scenes)
                    self.logger.info(f"Chunk {chunk_number}: Successfully extracted {len(chunk_scenes)} scenes")
                else:
                    self.logger.warning(f"Chunk {chunk_number}: No scenes extracted")

                chunks_processed += 1

            # Calculate overall hydration success rate
            if total_hydration_stats['attempted'] > 0:
                total_hydration_stats['success_rate'] = total_hydration_stats['succeeded'] / total_hydration_stats['attempted']
            
            if not all_scenes:
                return PipelineStageResult.success_result(
                    self.stage_name,
                    scenes_extracted=0,
                    scenes_stored=0,
                    chunks_processed=chunks_processed,
                    message='No scenes detected across all chunks'
                )
            
            # Store all scenes in database
            scenes_stored = self._store_scenes_in_database(context, all_scenes)

            return PipelineStageResult.success_result(
                self.stage_name,
                scenes_extracted=len(all_scenes),
                scenes_stored=scenes_stored,
                chunks_processed=chunks_processed,
                total_text_length=total_text_length,
                avg_scene_length=sum(len(scene.get('content', '')) for scene in all_scenes) // len(all_scenes) if all_scenes else 0,
                scenes_per_chunk=len(all_scenes) / chunks_processed if chunks_processed > 0 else 0,
                hydration_stats=total_hydration_stats  # Include hydration quality stats
            )
            
        except Exception as e:
            return PipelineStageResult.error_result(
                self.stage_name,
                error=str(e),
                draft_id=draft_id
            )
    
    def _call_api_with_retry(self, max_retries: int = None, base_delay: float = None, rate_limit_delay: float = None) -> Any:
        """
        Call the generation API with exponential backoff retry logic and rate limiting.
        
        Args:
            max_retries: Maximum number of retry attempts (defaults to config)
            base_delay: Base delay in seconds for exponential backoff (defaults to config)
            rate_limit_delay: Base delay between all API calls to prevent overload (defaults to config)
            
        Returns:
            API response object
        """
        # Use configuration defaults if not provided
        if max_retries is None:
            max_retries = Stage3Config.MAX_RETRY_ATTEMPTS - 1  # Subtract 1 for initial attempt
        if base_delay is None:
            base_delay = Stage3Config.RETRY_BASE_DELAY
        if rate_limit_delay is None:
            rate_limit_delay = Stage3Config.RETRY_RATE_LIMIT_DELAY
        
        # Add a small delay before any API call to prevent overwhelming the service
        time.sleep(rate_limit_delay)
        
        for attempt in range(max_retries + 1):
            try:
                # call_llm_with_retry handles transient 503/429 errors with
                # exponential backoff; the scene-count loop above handles the
                # case where we got a valid response but the wrong scene count.
                response = call_llm_with_retry(
                    lambda: self.generation_engine.generate(skip_quota=True)
                )

                # Check if response was truncated due to token limit
                if response.success and hasattr(response, 'metadata') and response.metadata.finish_reason == 'length':
                    current_limit = self.generation_engine.request.generation_config.max_output_tokens
                    new_limit = int(current_limit * 1.5)  # Increase by 50%
                    self.logger.warning(
                        f"Stage 3 scene extraction truncated (finish_reason='length'). "
                        f"Tokens: {response.metadata.output_tokens}. "
                        f"Increasing max_output_tokens from {current_limit} to {new_limit} and retrying..."
                    )
                    self.generation_engine.request.generation_config.max_output_tokens = new_limit
                    response = call_llm_with_retry(
                        lambda: self.generation_engine.generate(skip_quota=True)
                    )

                # Return on success or non-retryable errors
                # (transient errors were already retried by call_llm_with_retry)
                return response

            except Exception as e:
                if attempt < max_retries:
                    delay = Stage3Config.get_retry_delay(
                        attempt, is_overload_error=False, error_message=str(e)
                    )
                    self.logger.warning(f"API call failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {delay:.1f}s: {e}")
                    time.sleep(delay)
                else:
                    self.logger.error(f"API call failed after {max_retries} retries: {e}")
                    raise
        
        # This should not be reached, but just in case
        return None
    
    def run(self, draft_id: str) -> Dict[str, Any]:
        """
        Execute Stage 3 with legacy interface (backward compatibility).
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Stage execution results
        """
        return super().run(draft_id)
    
    def _get_chunk_data(self, context: PipelineStageContext) -> List[Tuple[int, str]]:
        """
        Retrieve individual cleaned text chunks with UTF-8 safety.
        
        Args:
            context: Stage execution context
            
        Returns:
            List of (chunk_number, cleaned_text) tuples ordered by chunk_number
        """
        draft_id = context.draft_id
        
        try:
            db_connection = self.get_database_connection(context)
            with db_connection as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT chunk_number, cleaned_text
                    FROM draft_chunks 
                    WHERE draft_id = %s
                    ORDER BY chunk_number
                """, (draft_id,))
                
                chunks = cursor.fetchall()
            
            # Filter out empty chunks and return as list of tuples
            chunk_data = [(chunk[0], chunk[1]) for chunk in chunks if chunk[1] and chunk[1].strip()]
            
            self.logger.debug(f"Retrieved {len(chunk_data)} chunks for draft {draft_id} (UTF-8 safe)")
            return chunk_data
            
        except Exception as e:
            self.logger.error(f"Failed to get chunk data for draft {draft_id}: {e}")
            raise
    
    def _validate_scene_count(self, scene_count: int) -> bool:
        """
        Validate that scene count is within the required range.
        
        Args:
            scene_count: Number of scenes detected
            
        Returns:
            True if scene count is valid (8-20), False otherwise
        """
        return Stage3Config.validate_scene_count(scene_count)
    
    def _process_chunk(self, chunk_number: int, cleaned_text: str, starting_scene_number: int) -> List[Dict[str, Any]]:
        """
        Process a single chunk to extract 8-20 scenes with retry logic.
        
        Args:
            chunk_number: Number of the chunk being processed
            cleaned_text: Cleaned text content of the chunk
            starting_scene_number: Starting scene number for global numbering
            
        Returns:
            List of scene dictionaries with global scene numbering
        """
        self.logger.info(f"Processing chunk {chunk_number} for scene extraction (starting from scene {starting_scene_number})")
        
        # Try up to configured attempts (initial + retries)
        for attempt in range(Stage3Config.MAX_RETRY_ATTEMPTS):
            try:
                if attempt == 0:
                    self.logger.debug(f"Chunk {chunk_number}: Initial scene detection attempt")
                    scenes = self._detect_scenes(cleaned_text)
                elif attempt == 1:
                    self.logger.debug(f"Chunk {chunk_number}: Retry attempt 1 - adjusting for scene count")
                    scenes = self._retry_scene_detection(cleaned_text, attempt, len(scenes) if 'scenes' in locals() else 0)
                else:
                    self.logger.debug(f"Chunk {chunk_number}: Retry attempt 2 - final attempt")
                    scenes = self._retry_scene_detection(cleaned_text, attempt, len(scenes) if 'scenes' in locals() else 0)
                
                scene_count = len(scenes)
                self.logger.debug(f"Chunk {chunk_number}: Found {scene_count} scenes (attempt {attempt + 1})")
                
                # Validate scene count
                if self._validate_scene_count(scene_count):
                    self.logger.info(f"Chunk {chunk_number}: Valid scene count ({scene_count}) - applying global numbering")
                    # Apply global scene numbering
                    numbered_scenes = self._apply_global_scene_numbering(scenes, starting_scene_number)
                    return numbered_scenes
                else:
                    self.logger.warning(f"Chunk {chunk_number}: Invalid scene count ({scene_count}) - expected 8-20 scenes")
                    
            except Exception as e:
                self.logger.error(f"Chunk {chunk_number}: Error in attempt {attempt + 1}: {e}")
                continue
        
        # All retries failed, return empty list to indicate failure
        self.logger.error(f"Chunk {chunk_number}: All AI attempts failed, chunk will contribute 0 scenes")
        return []
    
    def _apply_global_scene_numbering(self, scenes: List[Dict[str, Any]], starting_scene_number: int) -> List[Dict[str, Any]]:
        """
        Apply global scene numbering to scenes from a chunk.
        
        Args:
            scenes: List of scene dictionaries
            starting_scene_number: Starting scene number for global numbering
            
        Returns:
            Scene dictionaries with updated global scene numbers
        """
        numbered_scenes = []
        for i, scene in enumerate(scenes):
            scene_copy = scene.copy()
            scene_copy['scene_number'] = starting_scene_number + i
            numbered_scenes.append(scene_copy)
        return numbered_scenes

    def _hydrate_scene_contents_from_markers(self, chunk_text: str, scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ensure each scene has full content. If AI returned short/ellipsis content
        but provided start/end markers, extract the content from the original chunk.

        Enhanced with:
        - Fuzzy marker matching (normalize whitespace, quotes, OCR artifacts)
        - Next scene boundary detection
        - Snippet expansion with paragraph alignment
        - Comprehensive logging for debugging
        - Quality-preserving validation (75% threshold)

        Uses 4 quality-preserving strategies:
        1. Exact marker matching
        2. Fuzzy marker matching (enhanced normalization)
        3. Next scene boundary detection
        4. Content snippet expansion

        Args:
            chunk_text: The original cleaned text for this chunk
            scenes: Scene dicts as returned by the parser

        Returns:
            Tuple of (hydrated_scenes, hydration_stats)
            - hydrated_scenes: Scenes with 'content' hydrated when possible
            - hydration_stats: Dict with attempted, succeeded, failed, success_rate
        """
        hydrated = []
        hydration_stats = {'attempted': 0, 'succeeded': 0, 'failed': 0}

        for idx, scene in enumerate(scenes):
            scene_number = scene.get('scene_number', idx + 1)
            content = (scene.get('content') or '').strip()
            start_marker = (scene.get('start_marker') or '').strip()
            end_marker = (scene.get('end_marker') or '').strip()

            # Determine if content looks truncated/placeholder
            # Reduced from 300 to 150 chars to reduce hydration failure rate (was 11.8%, target <5%)
            content_looks_truncated = len(content) < 150 or content.endswith('...')

            if content_looks_truncated:
                hydration_stats['attempted'] += 1
                self.logger.debug(f"Scene {scene_number}: Attempting hydration (current length: {len(content)})")

                extracted = ""
                extraction_method = None

                # Strategy 1: Exact marker matching
                if start_marker and end_marker:
                    try:
                        extracted = self._extract_content_by_markers(chunk_text, start_marker, end_marker)
                        if extracted and len(extracted) >= 150:
                            extraction_method = "exact_markers"
                    except Exception as e:
                        self.logger.debug(f"Scene {scene_number}: Exact marker extraction failed: {e}")

                # Strategy 2: Fuzzy marker matching (normalize whitespace)
                if (not extracted or len(extracted) < 150) and start_marker and end_marker:
                    try:
                        extracted = self._extract_content_by_markers_fuzzy(chunk_text, start_marker, end_marker)
                        if extracted and len(extracted) >= 150:
                            extraction_method = "fuzzy_markers"
                    except Exception as e:
                        self.logger.debug(f"Scene {scene_number}: Fuzzy marker extraction failed: {e}")

                # Strategy 3: Use next scene's start as end boundary
                if (not extracted or len(extracted) < 150) and start_marker and idx + 1 < len(scenes):
                    next_start = (scenes[idx + 1].get('start_marker') or '').strip()
                    if next_start:
                        try:
                            start_idx = chunk_text.find(start_marker)
                            end_idx = chunk_text.find(next_start, start_idx + len(start_marker))
                            if start_idx != -1 and end_idx != -1:
                                candidate = chunk_text[start_idx:end_idx].strip()
                                if len(candidate) >= 150:
                                    extracted = candidate
                                    extraction_method = "next_scene_boundary"
                        except Exception as e:
                            self.logger.debug(f"Scene {scene_number}: Next scene boundary extraction failed: {e}")

                # Strategy 4: Content snippet alignment + paragraph expansion
                if (not extracted or len(extracted) < 150) and content and len(content) > 50:
                    try:
                        snippet = content[:min(120, len(content))]
                        pos = chunk_text.find(snippet)
                        if pos != -1:
                            # Expand to nearest double newline or generous character bounds
                            before = chunk_text.rfind('\n\n', max(0, pos - 1000), pos)
                            if before == -1:
                                before = max(0, pos - 500)
                            after = chunk_text.find('\n\n', pos + len(snippet))
                            if after == -1:
                                after = min(len(chunk_text), pos + len(snippet) + 2000)
                            candidate = chunk_text[before:after].strip()
                            if len(candidate) >= 150:
                                extracted = candidate
                                extraction_method = "snippet_expansion"
                    except Exception as e:
                        self.logger.debug(f"Scene {scene_number}: Snippet expansion failed: {e}")

                # Apply extraction if successful
                if extracted and len(extracted) >= 150:
                    scene = scene.copy()
                    scene['content'] = extracted
                    hydration_stats['succeeded'] += 1
                    self.logger.debug(f"Scene {scene_number}: Hydration succeeded via {extraction_method} (new length: {len(extracted)})")
                else:
                    hydration_stats['failed'] += 1
                    self.logger.warning(
                        f"Scene {scene_number}: Hydration failed - keeping truncated content "
                        f"(length: {len(content)}, start_marker: {bool(start_marker)}, end_marker: {bool(end_marker)})"
                    )

            hydrated.append(scene)

        # Log overall hydration statistics
        if hydration_stats['attempted'] > 0:
            success_rate = (hydration_stats['succeeded'] / hydration_stats['attempted']) * 100
            self.logger.info(
                f"Content hydration stats: {hydration_stats['succeeded']}/{hydration_stats['attempted']} succeeded "
                f"({success_rate:.1f}%), {hydration_stats['failed']} failed"
            )

            # Add success rate to stats
            hydration_result = {
                'attempted': hydration_stats['attempted'],
                'succeeded': hydration_stats['succeeded'],
                'failed': hydration_stats['failed'],
                'success_rate': success_rate / 100  # Convert to decimal (0.0-1.0)
            }

            # QUALITY CHECK: Fail if hydration success rate is too low
            if success_rate < 75.0:  # Less than 75% success
                error_msg = (
                    f"Content hydration quality too low: {success_rate:.1f}% "
                    f"({hydration_stats['failed']}/{hydration_stats['attempted']} scenes failed). "
                    "Cannot proceed with incomplete scene data."
                )
                self.logger.error(error_msg)
                raise ValueError(error_msg)

            return hydrated, hydration_result
        else:
            # No hydration attempted - all scenes had complete content
            return hydrated, {
                'attempted': 0,
                'succeeded': 0,
                'failed': 0,
                'success_rate': 1.0
            }
    
    def _retry_scene_detection(self, text_content: str, attempt: int, previous_scene_count: int) -> List[Dict[str, Any]]:
        """
        Retry scene detection with adjusted prompts based on previous results.
        
        Args:
            text_content: Text content to analyze
            attempt: Retry attempt number (1 or 2)
            previous_scene_count: Number of scenes found in previous attempt
            
        Returns:
            List of scene dictionaries
        """
        try:
            # Determine the adjustment needed based on previous scene count
            if previous_scene_count < 8:
                # Too few scenes, ask for more
                adjustment = "MORE"
                instruction = f"Previous attempt found only {previous_scene_count} scenes. Extract MORE scenes (aim for 8-20 scenes). Look for subtle scene transitions, changes in setting, time jumps, or shifts in narrative focus."
            elif previous_scene_count > 20:
                # Too many scenes, ask for fewer
                adjustment = "FEWER"
                instruction = f"Previous attempt found {previous_scene_count} scenes. Extract FEWER scenes (aim for 8-20 scenes). Focus on major scene transitions and combine minor transitions into longer scenes."
            else:
                # This shouldn't happen since we only retry for invalid counts
                adjustment = "OPTIMAL"
                instruction = "Analyze the text and identify distinct scenes with their boundaries and metadata. Aim for 8-20 scenes total."
            
            # Prepare the scene detection prompt with emphasis
            base_prompt = self.prompt_template.get_scene_detection_prompt().format(
                text_content=text_content
            )
            
            # Add retry instruction
            enhanced_prompt = f"{base_prompt}\n\nRETRY INSTRUCTION: {instruction}"
            
            # Update the generation request
            self.generation_engine.request.prompt = enhanced_prompt
            self.generation_engine.request.instruction = f"Extract {adjustment} scenes to get 8-20 scenes total. {instruction}"
            
            # Set provider-aware token limit for scene detection JSON
            self.generation_engine.request.generation_config.max_output_tokens = self._get_output_budget("json_analytical")

            # Enable JSON mode for Gemini structured output
            self.generation_engine.request.generation_config.response_mime_type = "application/json"

            try:
                # Generate scene analysis
                response = self._call_api_with_retry()
            finally:
                # Reset to avoid leaking into subsequent plain-text stages
                self.generation_engine.request.generation_config.response_mime_type = None

            if not response or not response.success:
                self.logger.error(f"AI generation failed on retry attempt {attempt}: {response.error_message if response else 'No response'}")
                return []
            
            # Parse the JSON response using unified parser
            try:
                validated_scenes = parse_scene_detection_response(response)
                self.logger.debug(f"Successfully parsed {len(validated_scenes)} scenes on retry attempt {attempt}")
                return validated_scenes
                
            except Exception as e:
                self.logger.error(f"Failed to parse scene detection JSON on retry attempt {attempt}: {e}")
                if hasattr(response, 'text'):
                    self.logger.error(f"Raw response (full): {str(response.text)}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error in retry scene detection (attempt {attempt}): {e}")
            return []
    
    def _detect_scenes(self, text_content: str) -> List[Dict[str, Any]]:
        """
        Use AI to detect and extract scenes from the text.
        
        Args:
            text_content: Complete text to analyze
            
        Returns:
            List of scene dictionaries
        """
        try:
            # Prepare the scene detection prompt
            prompt = self.prompt_template.get_scene_detection_prompt().format(
                text_content=text_content
            )
            
            # Update the generation request
            self.generation_engine.request.prompt = prompt
            self.generation_engine.request.instruction = "Analyze the text and identify distinct scenes with their boundaries and metadata."
            
            # Set provider-aware token limit for scene detection JSON
            self.generation_engine.request.generation_config.max_output_tokens = self._get_output_budget("json_analytical")

            # Enable JSON mode for Gemini structured output
            self.generation_engine.request.generation_config.response_mime_type = "application/json"

            try:
                # Generate scene analysis
                response = self._call_api_with_retry()
            finally:
                # Reset to avoid leaking into subsequent plain-text stages
                self.generation_engine.request.generation_config.response_mime_type = None

            if not response or not response.success:
                self.logger.error(f"AI generation failed: {response.error_message if response else 'No response'}")
                return []

            # Parse the JSON response using unified parser
            try:
                validated_scenes = parse_scene_detection_response(response)
                self.logger.debug(f"Successfully parsed {len(validated_scenes)} scenes")
                return validated_scenes

            except Exception as e:
                self.logger.error(f"Failed to parse scene detection JSON: {e}")
                if hasattr(response, 'text'):
                    self.logger.error(f"Raw response (full): {str(response.text)}")
                return []

        except Exception as e:
            self.logger.error(f"Error detecting scenes: {e}")
            return []
    
    
    def _extract_content_by_markers(self, text: str, start_marker: str, end_marker: str) -> str:
        """
        Extract content between start and end markers.

        Args:
            text: Full text to search
            start_marker: Start boundary text
            end_marker: End boundary text

        Returns:
            Extracted content
        """
        try:
            start_idx = text.find(start_marker)
            end_idx = text.find(end_marker, start_idx + len(start_marker))

            if start_idx != -1 and end_idx != -1:
                return text[start_idx:end_idx + len(end_marker)].strip()

        except Exception as e:
            self.logger.error(f"Error extracting content by markers: {e}")

        return ""

    def _extract_content_by_markers_fuzzy(self, text: str, start_marker: str, end_marker: str) -> str:
        """
        Extract content between start and end markers using enhanced fuzzy matching.
        Normalizes whitespace, punctuation, quotes, and OCR artifacts for better matching.

        Args:
            text: Full text to search
            start_marker: Start boundary text
            end_marker: End boundary text

        Returns:
            Extracted content or empty string if not found
        """
        try:
            # Enhanced normalization for fuzzy matching
            def normalize_for_matching(s: str) -> str:
                """
                Normalize text for fuzzy matching.
                Handles whitespace, punctuation, quotes, and OCR artifacts.
                """
                import re

                # Collapse multiple spaces/newlines into single space
                s = re.sub(r'\s+', ' ', s).strip()

                # Normalize punctuation spacing
                s = re.sub(r'\s+([.,!?;:])', r'\1', s)  # Remove space before punctuation
                s = re.sub(r'([.,!?;:])\s+', r'\1 ', s)  # Normalize space after punctuation

                # Normalize quotes (smart quotes → straight quotes)
                s = s.replace('"', '"').replace('"', '"')  # Smart double quotes
                s = s.replace("'", "'").replace("'", "'")  # Smart single quotes
                s = s.replace('`', "'")                      # Backtick → single quote

                # Remove common OCR artifacts
                s = s.replace('- ', '')  # Hyphen line breaks (e.g., "hyphen- ation" → "hyphenation")
                s = re.sub(r'\s*-\s*\n\s*', '', s)  # Hyphen with newline

                # Normalize em/en dashes
                s = s.replace('—', '--')  # Em dash → double hyphen
                s = s.replace('–', '-')   # En dash → single hyphen

                # Normalize ellipsis
                s = s.replace('…', '...')  # Unicode ellipsis → three dots

                return s.lower()  # Case-insensitive matching

            normalized_text = normalize_for_matching(text)
            normalized_start = normalize_for_matching(start_marker)
            normalized_end = normalize_for_matching(end_marker)

            # Try to find normalized markers in normalized text
            start_idx = normalized_text.find(normalized_start)
            if start_idx == -1:
                return ""

            end_idx = normalized_text.find(normalized_end, start_idx + len(normalized_start))
            if end_idx == -1:
                return ""

            # Extract from normalized positions, then map back to original text
            # Simple approximation: use character offsets from normalized text
            extracted_normalized = normalized_text[start_idx:end_idx + len(normalized_end)].strip()

            # Try to find this content in original text (may have different whitespace)
            # Use progressively shorter anchors for better matching flexibility
            anchor_lengths = [100, 50, 30]  # Try multiple anchor sizes
            anchor_idx = -1

            for anchor_len in anchor_lengths:
                if len(extracted_normalized) >= anchor_len:
                    anchor = extracted_normalized[:anchor_len]
                    # Try both normalized and original text search
                    anchor_idx = text.lower().find(anchor)
                    if anchor_idx != -1:
                        break

            if anchor_idx != -1:
                # Found anchor, estimate end position
                estimated_length = len(extracted_normalized) * 1.2  # Account for whitespace differences
                estimated_end = min(len(text), anchor_idx + int(estimated_length))

                # Expand to nearest paragraph boundary
                end_boundary = text.find('\n\n', estimated_end)
                if end_boundary == -1 or end_boundary - anchor_idx > len(extracted_normalized) * 2:
                    end_boundary = estimated_end

                return text[anchor_idx:end_boundary].strip()

            # Fallback: return normalized extraction (better than nothing)
            return extracted_normalized

        except Exception as e:
            self.logger.debug(f"Error in fuzzy marker extraction: {e}")
            return ""

    def _store_scenes_in_database(self, context: PipelineStageContext, scenes: List[Dict[str, Any]]) -> int:
        """
        Store extracted scenes in the database with UTF-8 safety.
        
        Args:
            context: Stage execution context
            scenes: List of scene dictionaries
            
        Returns:
            Number of scenes stored
        """
        draft_id = context.draft_id
        
        if not scenes:
            return 0
        
        try:
            db_connection = self.get_database_connection(context)
            with db_connection as conn:
                cursor = conn.cursor()
                
                # Prepare bulk insert data with UTF-8 cleaning
                scene_data = []
                for scene in scenes:
                    scene_data.append((
                        draft_id,
                        scene['scene_number'],
                        clean_text_for_database(scene['title']),
                        clean_text_for_database(scene['summary']),
                        clean_text_for_database(scene['setting']),
                        json.dumps(scene['characters'], ensure_ascii=False),  # Store as UTF-8 JSON
                        clean_text_for_database(scene['content'])
                    ))
                
                # Bulk insert scenes
                cursor.executemany("""
                    INSERT INTO scenes (
                        draft_id, scene_number, title, summary, 
                        setting, characters, original_content
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, scene_data)
                
                scenes_inserted = cursor.rowcount
                conn.commit()
            
            self.logger.info(f"Stored {scenes_inserted} scenes for draft {draft_id} (UTF-8 safe)")
            return scenes_inserted
            
        except Exception as e:
            self.logger.error(f"Failed to store scenes for draft {draft_id}: {e}")
            raise

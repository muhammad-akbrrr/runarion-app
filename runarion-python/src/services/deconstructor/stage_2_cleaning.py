"""
Stage 2: Text Cleaning and Normalization
Processes raw text chunks through AI cleaning to improve quality.
"""

import json
import logging
from typing import Dict, Any, List, Tuple
from .prompt_template import DeconstructorPrompts
from utils.database_utils import clean_text_for_database
from .base_stage import BasePipelineStage, PipelineStageResult, PipelineStageContext

logger = logging.getLogger(__name__)

class TextCleaningStage(BasePipelineStage):
    """
    Stage 2 of the deconstruction pipeline.
    Cleans and normalizes text chunks using AI processing.
    """
    
    def __init__(self, db_pool, generation_engine):
        """
        Initialize the text cleaning stage.
        
        Args:
            db_pool: Database connection pool
            generation_engine: AI generation engine
        """
        super().__init__(db_pool, "TextCleaningStage", generation_engine)
        self.prompt_template = DeconstructorPrompts()
    
    def _execute_stage(self, context: PipelineStageContext) -> PipelineStageResult:
        """
        Execute Stage 2: Text cleaning for all chunks.
        
        Args:
            context: Stage execution context containing draft_id
            
        Returns:
            PipelineStageResult with stage execution results
        """
        draft_id = context.draft_id
        
        try:
            # Get all chunks for this draft
            chunks = self._get_draft_chunks(context)
            
            if not chunks:
                return PipelineStageResult.success_result(
                    self.stage_name,
                    chunks_processed=0,
                    chunks_cleaned=0,
                    chunks_updated=0,
                    failed_chunks=0,
                    message='No chunks to process'
                )
            
            # Process each chunk through AI cleaning
            cleaned_chunks = []
            failed_chunks = []
            
            for chunk_id, chunk_number, raw_text in chunks:
                try:
                    cleaned_text = self._clean_text_chunk(raw_text)
                    cleaned_chunks.append((chunk_id, cleaned_text))
                    
                    self.logger.debug(f"Cleaned chunk {chunk_number} for draft {draft_id}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to clean chunk {chunk_number}: {e}")
                    failed_chunks.append((chunk_id, chunk_number, str(e)))
                    # Use original text as fallback
                    cleaned_chunks.append((chunk_id, raw_text))
            
            # Update chunks in database
            updated_count = self._update_cleaned_chunks(context, cleaned_chunks)
            
            return PipelineStageResult.success_result(
                self.stage_name,
                chunks_processed=len(chunks),
                chunks_cleaned=len(cleaned_chunks) - len(failed_chunks),
                chunks_updated=updated_count,
                failed_chunks=len(failed_chunks),
                failures=failed_chunks if failed_chunks else None,
                execution_metadata={
                    'actual_provider': self.generation_engine.request.provider,
                    'actual_model': self.generation_engine.request.model,
                    'api_calls_made': len(chunks) > 0
                }
            )
            
        except Exception as e:
            return PipelineStageResult.error_result(
                self.stage_name,
                error=str(e),
                draft_id=draft_id,
                execution_metadata={
                    'actual_provider': self.generation_engine.request.provider if self.generation_engine else 'unknown',
                    'actual_model': self.generation_engine.request.model if self.generation_engine else 'unknown',
                    'api_calls_made': False
                }
            )
    
    def run(self, draft_id: str) -> Dict[str, Any]:
        """
        Execute Stage 2 with legacy interface (backward compatibility).
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Stage execution results
        """
        return super().run(draft_id)
    
    def _get_draft_chunks(self, context: PipelineStageContext) -> List[Tuple[int, int, str]]:
        """
        Retrieve all chunks for a draft from the database with UTF-8 safety.
        
        Args:
            context: Stage execution context
            
        Returns:
            List of (chunk_id, chunk_number, raw_text) tuples
        """
        draft_id = context.draft_id
        
        try:
            db_connection = self.get_database_connection(context)
            with db_connection as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, chunk_number, raw_text
                    FROM draft_chunks 
                    WHERE draft_id = %s
                    ORDER BY chunk_number
                """, (draft_id,))
                
                chunks = cursor.fetchall()
            
            self.logger.debug(f"Retrieved {len(chunks)} chunks for draft {draft_id}")
            return chunks
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve chunks for draft {draft_id}: {e}")
            raise
    
    def _clean_text_chunk(self, raw_text: str, max_retries: int = 2) -> str:
        """
        Clean a single text chunk using AI processing with retry logic.
        
        Args:
            raw_text: Raw text to clean
            max_retries: Maximum number of retry attempts
            
        Returns:
            Cleaned text
        """
        if not raw_text.strip():
            return raw_text
        
        for attempt in range(max_retries + 1):
            try:
                # Prepare the cleaning prompt
                prompt = self.prompt_template.get_text_cleaning_prompt().format(
                    text_chunk=raw_text
                )
                
                # Update the generation request
                self.generation_engine.request.prompt = prompt
                self.generation_engine.request.instruction = "Clean and normalize the provided text while preserving all narrative content."
                
                # Set appropriate token limit for text cleaning (match input chunk size ~3000 tokens)
                self.generation_engine.request.generation_config.max_output_tokens = 3000
                
                # Generate cleaned text
                response = self.generation_engine.generate(skip_quota=True)
                
                if response.success:
                    cleaned_text = response.text.strip()
                    
                    # Validate that we got reasonable output - use 95% threshold for cleaning (not summarizing)
                    if len(cleaned_text) < len(raw_text) * 0.95:
                        if attempt < max_retries:
                            logger.warning(f"Cleaned text too short ({len(cleaned_text)}/{len(raw_text)} chars, {len(cleaned_text)/len(raw_text)*100:.1f}%) - attempt {attempt + 1}/{max_retries + 1}, retrying...")
                            continue
                        else:
                            logger.warning(f"Cleaned text significantly shorter than original ({len(cleaned_text)/len(raw_text)*100:.1f}%), may be summarizing instead of cleaning - using original")
                            return raw_text
                    
                    # Additional check for truncated responses
                    if len(cleaned_text) < len(raw_text) * 0.98 and not cleaned_text.rstrip().endswith(('.', '!', '?', '"', "'")):
                        if attempt < max_retries:
                            logger.warning(f"Cleaned text may be truncated (doesn't end properly) - attempt {attempt + 1}/{max_retries + 1}, retrying...")
                            continue
                        else:
                            logger.warning("Cleaned text may be truncated (improper ending), using original")
                            return raw_text
                    
                    return cleaned_text
                else:
                    if attempt < max_retries:
                        logger.warning(f"AI generation failed (attempt {attempt + 1}/{max_retries + 1}): {response.error_message}, retrying...")
                        continue
                    else:
                        logger.error(f"AI generation failed after {max_retries + 1} attempts: {response.error_message}")
                        return raw_text
                        
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Error cleaning text chunk (attempt {attempt + 1}/{max_retries + 1}): {e}, retrying...")
                    continue
                else:
                    logger.error(f"Error cleaning text chunk after {max_retries + 1} attempts: {e}")
                    return raw_text
        
        return raw_text
    
    def _update_cleaned_chunks(self, context: PipelineStageContext, cleaned_chunks: List[Tuple[int, str]]) -> int:
        """
        Update the cleaned text for chunks in the database with UTF-8 safety.
        
        Args:
            context: Stage execution context
            cleaned_chunks: List of (chunk_id, cleaned_text) tuples
            
        Returns:
            Number of chunks updated
        """
        if not cleaned_chunks:
            return 0
        
        try:
            db_connection = self.get_database_connection(context)
            with db_connection as conn:
                cursor = conn.cursor()
                
                # Prepare data with UTF-8 cleaning
                safe_updates = [
                    (clean_text_for_database(cleaned_text), chunk_id) 
                    for chunk_id, cleaned_text in cleaned_chunks
                ]
                
                # Bulk update cleaned text
                cursor.executemany("""
                    UPDATE draft_chunks 
                    SET cleaned_text = %s
                    WHERE id = %s
                """, safe_updates)
                
                updated_count = cursor.rowcount
                conn.commit()
            
            self.logger.info(f"Updated {updated_count} chunks with cleaned text (UTF-8 safe)")
            return updated_count
            
        except Exception as e:
            self.logger.error(f"Failed to update cleaned chunks: {e}")
            raise    

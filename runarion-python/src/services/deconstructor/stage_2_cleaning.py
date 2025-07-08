"""
Stage 2: Text Cleaning and Normalization
Processes raw text chunks through AI cleaning to improve quality.
"""

import json
import logging
from typing import Dict, Any, List, Tuple
from models.request import BaseGenerationRequest
from .prompt_template import DeconstructorPrompts
from utils.database_utils import utf8_database_connection, clean_text_for_database, safe_update_text

logger = logging.getLogger(__name__)

class TextCleaningStage:
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
        self.db_pool = db_pool
        self.generation_engine = generation_engine
        self.prompt_template = DeconstructorPrompts()
    
    def run(self, draft_id: str) -> Dict[str, Any]:
        """
        Execute Stage 2: Text cleaning for all chunks.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Stage execution results
        """
        logger.info(f"Starting Stage 2 text cleaning for draft {draft_id}")
        
        try:
            # Get all chunks for this draft
            chunks = self._get_draft_chunks(draft_id)
            
            if not chunks:
                logger.warning(f"No chunks found for draft {draft_id}")
                return {
                    'success': True,
                    'chunks_processed': 0,
                    'message': 'No chunks to process'
                }
            
            # Process each chunk through AI cleaning
            cleaned_chunks = []
            failed_chunks = []
            
            for chunk_id, chunk_number, raw_text in chunks:
                try:
                    cleaned_text = self._clean_text_chunk(raw_text)
                    cleaned_chunks.append((chunk_id, cleaned_text))
                    
                    logger.debug(f"Cleaned chunk {chunk_number} for draft {draft_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to clean chunk {chunk_number}: {e}")
                    failed_chunks.append((chunk_id, chunk_number, str(e)))
                    # Use original text as fallback
                    cleaned_chunks.append((chunk_id, raw_text))
            
            # Update chunks in database
            updated_count = self._update_cleaned_chunks(cleaned_chunks)
            
            result = {
                'success': True,
                'chunks_processed': len(chunks),
                'chunks_cleaned': len(cleaned_chunks) - len(failed_chunks),
                'chunks_updated': updated_count,
                'failed_chunks': len(failed_chunks),
                'failures': failed_chunks if failed_chunks else None
            }
            
            logger.info(f"Stage 2 completed for draft {draft_id}: {updated_count} chunks cleaned")
            return result
            
        except Exception as e:
            logger.error(f"Stage 2 failed for draft {draft_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'draft_id': draft_id
            }
    
    def _get_draft_chunks(self, draft_id: str) -> List[Tuple[int, int, str]]:
        """
        Retrieve all chunks for a draft from the database with UTF-8 safety.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            List of (chunk_id, chunk_number, raw_text) tuples
        """
        try:
            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, chunk_number, raw_text
                    FROM draft_chunks 
                    WHERE draft_id = %s
                    ORDER BY chunk_number
                """, (draft_id,))
                
                chunks = cursor.fetchall()
            
            logger.debug(f"Retrieved {len(chunks)} chunks for draft {draft_id}")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to retrieve chunks for draft {draft_id}: {e}")
            raise
    
    def _clean_text_chunk(self, raw_text: str) -> str:
        """
        Clean a single text chunk using AI processing.
        
        Args:
            raw_text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if not raw_text.strip():
            return raw_text
        
        try:
            # Prepare the cleaning prompt
            prompt = self.prompt_template.get_text_cleaning_prompt().format(
                text_chunk=raw_text
            )
            
            # Update the generation request
            self.generation_engine.request.prompt = prompt
            self.generation_engine.request.instruction = "Clean and normalize the provided text while preserving all narrative content."
            
            # Generate cleaned text
            response = self.generation_engine.generate(skip_quota=True)
            
            if response.success:
                cleaned_text = response.text.strip()
                
                # Validate that we got reasonable output
                if len(cleaned_text) < len(raw_text) * 0.5:
                    logger.warning("Cleaned text is significantly shorter than original, using original")
                    return raw_text
                
                return cleaned_text
            else:
                logger.error(f"AI generation failed: {response.error_message}")
                return raw_text
                
        except Exception as e:
            logger.error(f"Error cleaning text chunk: {e}")
            return raw_text
    
    def _update_cleaned_chunks(self, cleaned_chunks: List[Tuple[int, str]]) -> int:
        """
        Update the cleaned text for chunks in the database with UTF-8 safety.
        
        Args:
            cleaned_chunks: List of (chunk_id, cleaned_text) tuples
            
        Returns:
            Number of chunks updated
        """
        if not cleaned_chunks:
            return 0
        
        try:
            with utf8_database_connection(self.db_pool) as conn:
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
            
            logger.info(f"Updated {updated_count} chunks with cleaned text (UTF-8 safe)")
            return updated_count
            
        except Exception as e:
            logger.error(f"Failed to update cleaned chunks: {e}")
            raise
    
    def get_cleaning_statistics(self, draft_id: str) -> Dict[str, Any]:
        """
        Get statistics about the text cleaning process.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Cleaning statistics
        """
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_chunks,
                        COUNT(CASE WHEN cleaned_text != raw_text THEN 1 END) as cleaned_chunks,
                        AVG(LENGTH(raw_text)) as avg_raw_length,
                        AVG(LENGTH(cleaned_text)) as avg_cleaned_length,
                        AVG(LENGTH(cleaned_text) - LENGTH(raw_text)) as avg_length_change
                    FROM draft_chunks 
                    WHERE draft_id = %s
                """, (draft_id,))
                
                result = cursor.fetchone()
                
                if result:
                    stats = {
                        'total_chunks': result[0],
                        'cleaned_chunks': result[1],
                        'unchanged_chunks': result[0] - result[1],
                        'avg_raw_length': int(result[2]) if result[2] else 0,
                        'avg_cleaned_length': int(result[3]) if result[3] else 0,
                        'avg_length_change': int(result[4]) if result[4] else 0,
                        'cleaning_percentage': (result[1] / result[0] * 100) if result[0] > 0 else 0
                    }
                else:
                    stats = {
                        'total_chunks': 0,
                        'cleaned_chunks': 0,
                        'unchanged_chunks': 0,
                        'avg_raw_length': 0,
                        'avg_cleaned_length': 0,
                        'avg_length_change': 0,
                        'cleaning_percentage': 0
                    }
            
            self.db_pool.putconn(conn)
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get cleaning statistics for draft {draft_id}: {e}")
            if 'conn' in locals():
                self.db_pool.putconn(conn)
            return {'error': str(e)}
    
    def reprocess_failed_chunks(self, draft_id: str) -> Dict[str, Any]:
        """
        Retry cleaning for chunks that still have uncleaned text.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Reprocessing results
        """
        try:
            # Get chunks where cleaned_text equals raw_text (likely uncleaned)
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, chunk_number, raw_text
                    FROM draft_chunks 
                    WHERE draft_id = %s AND cleaned_text = raw_text
                    ORDER BY chunk_number
                """, (draft_id,))
                
                failed_chunks = cursor.fetchall()
            
            self.db_pool.putconn(conn)
            
            if not failed_chunks:
                return {
                    'success': True,
                    'message': 'No failed chunks to reprocess',
                    'chunks_reprocessed': 0
                }
            
            # Reprocess failed chunks
            cleaned_chunks = []
            still_failed = []
            
            for chunk_id, chunk_number, raw_text in failed_chunks:
                try:
                    cleaned_text = self._clean_text_chunk(raw_text)
                    if cleaned_text != raw_text:  # Successfully cleaned
                        cleaned_chunks.append((chunk_id, cleaned_text))
                    else:
                        still_failed.append((chunk_id, chunk_number))
                        
                except Exception as e:
                    logger.error(f"Failed to reprocess chunk {chunk_number}: {e}")
                    still_failed.append((chunk_id, chunk_number))
            
            # Update successfully cleaned chunks
            updated_count = self._update_cleaned_chunks(cleaned_chunks)
            
            return {
                'success': True,
                'chunks_attempted': len(failed_chunks),
                'chunks_reprocessed': updated_count,
                'still_failed': len(still_failed),
                'failed_chunk_numbers': [chunk_num for _, chunk_num in still_failed]
            }
            
        except Exception as e:
            logger.error(f"Failed to reprocess chunks for draft {draft_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'draft_id': draft_id
            }
    
    def get_cleaned_text(self, draft_id: str) -> str:
        """
        Get the complete cleaned text for a draft by concatenating all chunks.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Complete cleaned text
        """
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT cleaned_text
                    FROM draft_chunks 
                    WHERE draft_id = %s
                    ORDER BY chunk_number
                """, (draft_id,))
                
                chunks = cursor.fetchall()
            
            self.db_pool.putconn(conn)
            
            # Concatenate all cleaned text chunks
            complete_text = "\n\n".join(chunk[0] for chunk in chunks if chunk[0])
            
            return complete_text
            
        except Exception as e:
            logger.error(f"Failed to get cleaned text for draft {draft_id}: {e}")
            if 'conn' in locals():
                self.db_pool.putconn(conn)
            return ""
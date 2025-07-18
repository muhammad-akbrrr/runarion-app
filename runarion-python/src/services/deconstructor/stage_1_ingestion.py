"""
Stage 1: PDF Ingestion and Text Chunking
Handles document extraction and creates initial chunks for processing.
"""

import logging
from typing import Dict, Any, List, Optional
from utils.document_processor import Chunk, DocumentProcessor
from utils.database_utils import safe_update_text, clean_text_for_database, utf8_database_connection

logger = logging.getLogger(__name__)

class PDFIngestionStage:
    """
    Stage 1 of the deconstruction pipeline.
    Extracts text from uploaded documents and creates manageable chunks.
    """
    
    def __init__(self, db_pool):
        """
        Initialize the ingestion stage.
        
        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool
        self.document_processor = DocumentProcessor(provider="openai", model="gpt-4o", chunk_word_limit=2000)
    
    def run(self, draft_id: str, file_path: str) -> Dict[str, Any]:
        """
        Execute Stage 1: Document ingestion and chunking.
        
        Args:
            draft_id: UUID of the draft
            file_path: Path to the uploaded document
            
        Returns:
            Stage execution results
        """
        logger.info(f"Starting Stage 1 ingestion for draft {draft_id}, file: {file_path}")
        
        try:
            # Validate file
            is_valid, error_message = self.document_processor.validate_file(file_path)
            if not is_valid:
                raise ValueError(f"File validation failed: {error_message}")
            
            # Process document
            processing_result = self.document_processor.process_document(file_path)
            
            if processing_result['status'] != 'success':
                raise Exception(f"Document processing failed: {processing_result['error']}")
            
            # Extract components
            cleaned_text = processing_result['cleaned_text']
            chunks = processing_result['chunks']
            metadata = processing_result['metadata']
            
            # Store chunks in database
            chunks_stored = self._store_chunks_in_database(draft_id, chunks)
            
            # Enhance metadata with word and token statistics
            enhanced_metadata = {
                **metadata,
                'chunking_strategy': 'word_based_with_token_validation',
                'target_words_per_chunk': 1500,
                'chunks_word_counts': [chunk.get('word_count', 0) for chunk in chunks],
                'chunks_token_counts': [chunk.get('token_count', 0) for chunk in chunks],
                'total_words': sum(chunk.get('word_count', 0) for chunk in chunks),
                'total_tokens': sum(chunk.get('token_count', 0) for chunk in chunks),
                'average_words_per_chunk': sum(chunk.get('word_count', 0) for chunk in chunks) / len(chunks) if chunks else 0,
                'average_tokens_per_chunk': sum(chunk.get('token_count', 0) for chunk in chunks) / len(chunks) if chunks else 0
            }
            
            # Update draft metadata
            self._update_draft_metadata(draft_id, enhanced_metadata)
            
            result = {
                'success': True,
                'chunks_created': len(chunks),
                'chunks_stored': chunks_stored,
                'total_characters': len(cleaned_text),
                'total_words': sum(chunk.get('word_count', 0) for chunk in chunks),
                'total_tokens': sum(chunk['token_count'] for chunk in chunks),
                'metadata': metadata
            }
            
            logger.info(f"Stage 1 completed for draft {draft_id}: {chunks_stored} chunks created")
            return result
            
        except Exception as e:
            logger.error(f"Stage 1 failed for draft {draft_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'draft_id': draft_id
            }
    
    def _store_chunks_in_database(self, draft_id: str, chunks: List[Chunk]) -> int:
        """
        Store text chunks in the database with UTF-8 encoding safety.
        
        Args:
            draft_id: UUID of the draft
            chunks: List of chunk dictionaries
            
        Returns:
            Number of chunks stored
        """
        if not chunks:
            logger.warning(f"No chunks to store for draft {draft_id}")
            return 0
        
        try:
            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()
                
                # Prepare bulk insert data with UTF-8 safety
                chunk_data = []
                for chunk in chunks:
                    # Clean and ensure UTF-8 encoding for text fields
                    raw_text = clean_text_for_database(chunk['raw_text'])
                    cleaned_text = clean_text_for_database(chunk['raw_text'])  # Initially same as raw
                    
                    chunk_data.append((
                        draft_id,
                        chunk['chunk_number'],
                        raw_text,
                        cleaned_text
                    ))
                
                # Bulk insert chunks
                cursor.executemany("""
                    INSERT INTO draft_chunks (draft_id, chunk_number, raw_text, cleaned_text)
                    VALUES (%s, %s, %s, %s)
                """, chunk_data)
                
                chunks_inserted = cursor.rowcount
                conn.commit()
            
            logger.info(f"Stored {chunks_inserted} chunks for draft {draft_id} with UTF-8 encoding")
            return chunks_inserted
            
        except Exception as e:
            logger.error(f"Failed to store chunks for draft {draft_id}: {e}")
            raise
    
    def _update_draft_metadata(self, draft_id: str, metadata: Dict[str, Any]) -> None:
        """
        Update draft metadata with processing information using UTF-8 safe operations.
        
        Args:
            draft_id: UUID of the draft
            metadata: Metadata dictionary to store
        """
        try:
            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()
                
                # Use safe_update_text for UTF-8 handling
                safe_update_text(
                    cursor=cursor,
                    table='drafts',
                    data={'metadata': metadata},
                    where_clause='id = %s',
                    where_params=(draft_id,)
                )
                
                conn.commit()
            
            logger.debug(f"Updated metadata for draft {draft_id} with UTF-8 safety")
            
        except Exception as e:
            logger.error(f"Failed to update metadata for draft {draft_id}: {e}")
            raise
    
    def get_chunk_statistics(self, draft_id: str) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the chunks for a draft, including word and token counts.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Chunk statistics with both character-based and word/token-based metrics
        """
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                # Get basic chunk statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as chunk_count,
                        AVG(LENGTH(raw_text)) as avg_chunk_length,
                        MIN(LENGTH(raw_text)) as min_chunk_length,
                        MAX(LENGTH(raw_text)) as max_chunk_length,
                        SUM(LENGTH(raw_text)) as total_characters
                    FROM draft_chunks 
                    WHERE draft_id = %s
                """, (draft_id,))
                
                result = cursor.fetchone()
                
                # Get word/token statistics from draft metadata
                cursor.execute("""
                    SELECT metadata FROM drafts WHERE id = %s
                """, (draft_id,))
                
                metadata_result = cursor.fetchone()
                metadata = metadata_result[0] if metadata_result and metadata_result[0] else {}
                
                if result:
                    stats = {
                        'chunk_count': result[0],
                        'avg_chunk_length': int(result[1]) if result[1] else 0,
                        'min_chunk_length': result[2] or 0,
                        'max_chunk_length': result[3] or 0,
                        'total_characters': result[4] or 0,
                        # Add word/token statistics from metadata
                        'total_words': metadata.get('total_words', 0),
                        'total_tokens': metadata.get('total_tokens', 0),
                        'avg_words_per_chunk': metadata.get('average_words_per_chunk', 0),
                        'avg_tokens_per_chunk': metadata.get('average_tokens_per_chunk', 0),
                        'chunking_strategy': metadata.get('chunking_strategy', 'legacy'),
                        'target_words_per_chunk': metadata.get('target_words_per_chunk', 'N/A')
                    }
                else:
                    stats = {
                        'chunk_count': 0,
                        'avg_chunk_length': 0,
                        'min_chunk_length': 0,
                        'max_chunk_length': 0,
                        'total_characters': 0,
                        'total_words': 0,
                        'total_tokens': 0,
                        'avg_words_per_chunk': 0,
                        'avg_tokens_per_chunk': 0,
                        'chunking_strategy': 'unknown',
                        'target_words_per_chunk': 'N/A'
                    }
            
            self.db_pool.putconn(conn)
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get chunk statistics for draft {draft_id}: {e}")
            if 'conn' in locals():
                self.db_pool.putconn(conn)
            return {'error': str(e)}
    
    def reprocess_chunks(self, draft_id: str, file_path: str, 
                        new_word_limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Reprocess chunks with different word-based parameters.
        
        Args:
            draft_id: UUID of the draft
            file_path: Path to the original document
            new_word_limit: New word limit to use (defaults to 1500)
            
        Returns:
            Reprocessing results
        """
        try:
            # Delete existing chunks
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM draft_chunks WHERE draft_id = %s", (draft_id,))
                deleted_count = cursor.rowcount
                conn.commit()
            
            self.db_pool.putconn(conn)
            
            logger.info(f"Deleted {deleted_count} existing chunks for draft {draft_id}")
            
            # Reprocess with new parameters
            if new_word_limit:
                # Override word limit in document processor
                original_word_limit = self.document_processor.chunk_word_limit
                self.document_processor.chunk_word_limit = new_word_limit
            
            result = self.run(draft_id, file_path)
            
            # Restore original word limit
            if new_word_limit:
                self.document_processor.chunk_word_limit = original_word_limit
            
            result['reprocessed'] = True
            result['deleted_chunks'] = deleted_count
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to reprocess chunks for draft {draft_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'draft_id': draft_id
            }
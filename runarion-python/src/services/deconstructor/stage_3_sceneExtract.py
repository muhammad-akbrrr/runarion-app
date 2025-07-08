"""
Stage 3: Scene Detection and Extraction
Analyzes cleaned text to identify and extract distinct scenes.
"""

import json
import logging
from typing import Dict, Any, List, Tuple
from models.request import BaseGenerationRequest
from .prompt_template import DeconstructorPrompts
from utils.database_utils import utf8_database_connection, clean_text_for_database, safe_insert_text

logger = logging.getLogger(__name__)

class SceneDetectionStage:
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
        self.db_pool = db_pool
        self.generation_engine = generation_engine
        self.prompt_template = DeconstructorPrompts()
    
    def run(self, draft_id: str) -> Dict[str, Any]:
        """
        Execute Stage 3: Scene detection and extraction.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Stage execution results
        """
        logger.info(f"Starting Stage 3 scene detection for draft {draft_id}")
        
        try:
            # Get cleaned text from all chunks
            cleaned_text = self._get_cleaned_text(draft_id)
            
            if not cleaned_text.strip():
                logger.warning(f"No cleaned text found for draft {draft_id}")
                return {
                    'success': True,
                    'scenes_extracted': 0,
                    'message': 'No text to process'
                }
            
            # Detect scenes using AI
            scenes = self._detect_scenes(cleaned_text)
            
            if not scenes:
                logger.warning(f"No scenes detected for draft {draft_id}")
                return {
                    'success': True,
                    'scenes_extracted': 0,
                    'message': 'No scenes detected'
                }
            
            # Store scenes in database
            scenes_stored = self._store_scenes_in_database(draft_id, scenes)
            
            result = {
                'success': True,
                'scenes_extracted': len(scenes),
                'scenes_stored': scenes_stored,
                'total_text_length': len(cleaned_text),
                'avg_scene_length': sum(len(scene.get('content', '')) for scene in scenes) // len(scenes) if scenes else 0
            }
            
            logger.info(f"Stage 3 completed for draft {draft_id}: {scenes_stored} scenes extracted")
            return result
            
        except Exception as e:
            logger.error(f"Stage 3 failed for draft {draft_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'draft_id': draft_id
            }
    
    def _get_cleaned_text(self, draft_id: str) -> str:
        """
        Retrieve and concatenate all cleaned text chunks with UTF-8 safety.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Complete cleaned text
        """
        try:
            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT cleaned_text
                    FROM draft_chunks 
                    WHERE draft_id = %s
                    ORDER BY chunk_number
                """, (draft_id,))
                
                chunks = cursor.fetchall()
            
            # Concatenate chunks with proper spacing
            complete_text = "\n\n".join(chunk[0] for chunk in chunks if chunk[0] and chunk[0].strip())
            
            logger.debug(f"Retrieved {len(complete_text)} characters of cleaned text for draft {draft_id} (UTF-8 safe)")
            return complete_text
            
        except Exception as e:
            logger.error(f"Failed to get cleaned text for draft {draft_id}: {e}")
            raise
    
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
            
            # Generate scene analysis
            response = self.generation_engine.generate(skip_quota=True)
            
            if not response.success:
                logger.error(f"AI generation failed: {response.error_message}")
                return []
            
            # Parse the JSON response
            try:
                scenes_data = json.loads(response.text.strip())
                
                # Validate and clean the scenes data
                validated_scenes = self._validate_scenes_data(scenes_data, text_content)
                
                return validated_scenes
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse scene detection JSON: {e}")
                logger.error(f"Raw response: {response.text[:500]}...")
                
                # Fallback: try to extract scenes manually
                return self._fallback_scene_detection(text_content)
                
        except Exception as e:
            logger.error(f"Error detecting scenes: {e}")
            return []
    
    def _validate_scenes_data(self, scenes_data: List[Dict], original_text: str) -> List[Dict[str, Any]]:
        """
        Validate and clean the scenes data from AI response.
        
        Args:
            scenes_data: Raw scenes data from AI
            original_text: Original text for validation
            
        Returns:
            Validated scenes list
        """
        validated_scenes = []
        
        for i, scene in enumerate(scenes_data):
            try:
                # Ensure required fields exist
                scene_dict = {
                    'scene_number': scene.get('scene_number', i + 1),
                    'title': scene.get('title', f'Scene {i + 1}'),
                    'setting': scene.get('setting', 'Unknown location'),
                    'characters': scene.get('characters', []),
                    'summary': scene.get('summary', ''),
                    'content': scene.get('content', '')
                }
                
                # Validate content exists
                if not scene_dict['content'].strip():
                    # Try to extract content using markers
                    start_marker = scene.get('start_marker', '')
                    end_marker = scene.get('end_marker', '')
                    
                    if start_marker and end_marker:
                        content = self._extract_content_by_markers(original_text, start_marker, end_marker)
                        scene_dict['content'] = content
                
                # Ensure we have meaningful content
                if len(scene_dict['content'].strip()) > 50:  # Minimum scene length
                    validated_scenes.append(scene_dict)
                else:
                    logger.warning(f"Scene {i + 1} too short, skipping")
                
            except Exception as e:
                logger.error(f"Error validating scene {i + 1}: {e}")
                continue
        
        return validated_scenes
    
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
            logger.error(f"Error extracting content by markers: {e}")
        
        return ""
    
    def _fallback_scene_detection(self, text_content: str) -> List[Dict[str, Any]]:
        """
        Fallback scene detection using simple heuristics.
        
        Args:
            text_content: Text to analyze
            
        Returns:
            List of basic scenes
        """
        logger.info("Using fallback scene detection")
        
        # Split by common scene break indicators
        scene_breaks = [
            '\n\n\n',  # Multiple line breaks
            'Chapter ',  # Chapter markers
            '* * *',     # Scene separators
            '---',       # Dashes
            '\n\n',      # Double line breaks (less strict)
        ]
        
        scenes = []
        current_text = text_content
        
        # Try each break pattern
        for break_pattern in scene_breaks:
            if break_pattern in current_text:
                parts = current_text.split(break_pattern)
                break
        else:
            # No breaks found, treat as single scene
            parts = [current_text]
        
        # Create scene objects
        for i, part in enumerate(parts):
            part = part.strip()
            if len(part) > 100:  # Minimum meaningful scene length
                scene = {
                    'scene_number': i + 1,
                    'title': f'Scene {i + 1}',
                    'setting': 'Unknown location',
                    'characters': [],
                    'summary': part[:200] + '...' if len(part) > 200 else part,
                    'content': part
                }
                scenes.append(scene)
        
        logger.info(f"Fallback detection found {len(scenes)} scenes")
        return scenes
    
    def _store_scenes_in_database(self, draft_id: str, scenes: List[Dict[str, Any]]) -> int:
        """
        Store extracted scenes in the database with UTF-8 safety.
        
        Args:
            draft_id: UUID of the draft
            scenes: List of scene dictionaries
            
        Returns:
            Number of scenes stored
        """
        if not scenes:
            return 0
        
        try:
            with utf8_database_connection(self.db_pool) as conn:
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
            
            logger.info(f"Stored {scenes_inserted} scenes for draft {draft_id} (UTF-8 safe)")
            return scenes_inserted
            
        except Exception as e:
            logger.error(f"Failed to store scenes for draft {draft_id}: {e}")
            raise
    
    def get_scene_statistics(self, draft_id: str) -> Dict[str, Any]:
        """
        Get statistics about extracted scenes.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Scene statistics
        """
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as scene_count,
                        AVG(LENGTH(original_content)) as avg_scene_length,
                        MIN(LENGTH(original_content)) as min_scene_length,
                        MAX(LENGTH(original_content)) as max_scene_length,
                        SUM(LENGTH(original_content)) as total_content_length
                    FROM scenes 
                    WHERE draft_id = %s
                """, (draft_id,))
                
                result = cursor.fetchone()
                
                if result:
                    stats = {
                        'scene_count': result[0],
                        'avg_scene_length': int(result[1]) if result[1] else 0,
                        'min_scene_length': result[2] or 0,
                        'max_scene_length': result[3] or 0,
                        'total_content_length': result[4] or 0
                    }
                else:
                    stats = {
                        'scene_count': 0,
                        'avg_scene_length': 0,
                        'min_scene_length': 0,
                        'max_scene_length': 0,
                        'total_content_length': 0
                    }
                
                # Get character frequency
                cursor.execute("""
                    SELECT characters 
                    FROM scenes 
                    WHERE draft_id = %s AND characters IS NOT NULL
                """, (draft_id,))
                
                character_results = cursor.fetchall()
                all_characters = []
                
                for char_result in character_results:
                    try:
                        chars = json.loads(char_result[0]) if char_result[0] else []
                        all_characters.extend(chars)
                    except:
                        continue
                
                # Count character frequencies
                character_counts = {}
                for char in all_characters:
                    character_counts[char] = character_counts.get(char, 0) + 1
                
                stats['unique_characters'] = len(character_counts)
                stats['most_frequent_characters'] = sorted(
                    character_counts.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:10]
            
            self.db_pool.putconn(conn)
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get scene statistics for draft {draft_id}: {e}")
            if 'conn' in locals():
                self.db_pool.putconn(conn)
            return {'error': str(e)}
    
    def redetect_scenes(self, draft_id: str) -> Dict[str, Any]:
        """
        Re-run scene detection for a draft.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Redetection results
        """
        try:
            # Delete existing scenes
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM scenes WHERE draft_id = %s", (draft_id,))
                deleted_count = cursor.rowcount
                conn.commit()
            
            self.db_pool.putconn(conn)
            
            logger.info(f"Deleted {deleted_count} existing scenes for draft {draft_id}")
            
            # Re-run scene detection
            result = self.run(draft_id)
            result['redetected'] = True
            result['deleted_scenes'] = deleted_count
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to redetect scenes for draft {draft_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'draft_id': draft_id
            }
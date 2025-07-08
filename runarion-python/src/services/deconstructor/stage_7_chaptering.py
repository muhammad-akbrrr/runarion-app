"""
Stage 7: Chaptering
Organizes the final manuscript into well-structured chapters with titles.
"""

import json
import logging
import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from .prompt_template import DeconstructorPrompts
from utils.database_utils import utf8_database_connection, clean_text_for_database, ensure_utf8_json

logger = logging.getLogger(__name__)

class ChapteringStage:
    """
    Stage 7 of the deconstruction pipeline.
    Organizes final manuscript into logical chapters with compelling titles.
    """
    
    def __init__(self, db_pool, generation_engine):
        """
        Initialize the chaptering stage.
        
        Args:
            db_pool: Database connection pool
            generation_engine: AI generation engine
        """
        self.db_pool = db_pool
        self.generation_engine = generation_engine
        self.prompt_template = DeconstructorPrompts()
    
    def run(self, draft_id: str, chaptering_mode: str = 'flexible', 
           target_chapter_length: int = 2500) -> Dict[str, Any]:
        """
        Execute Stage 7: Chapter organization.
        
        Args:
            draft_id: UUID of the draft
            chaptering_mode: 'flexible' or 'constrained' chaptering approach
            target_chapter_length: Target word count per chapter
            
        Returns:
            Stage execution results
        """
        logger.info(f"Starting Stage 7 chaptering for draft {draft_id} (mode: {chaptering_mode}, target: {target_chapter_length} words)")
        
        try:
            # Get final manuscript
            manuscript_data = self._get_final_manuscript(draft_id)
            
            if not manuscript_data:
                logger.warning(f"No final manuscript found for chaptering in draft {draft_id}")
                return {
                    'success': True,
                    'chapters_created': 0,
                    'message': 'No final manuscript to chapter'
                }
            
            # Get scene information for chapter break guidance
            scene_info = self._get_scene_information(draft_id)
            
            # Perform chaptering based on mode
            if chaptering_mode == 'constrained':
                chapters = self._constrained_chaptering(
                    manuscript_data['content'], 
                    scene_info, 
                    target_chapter_length
                )
            else:  # flexible mode (default)
                chapters = self._flexible_chaptering(
                    manuscript_data['content'], 
                    scene_info, 
                    target_chapter_length
                )
            
            # Generate compelling chapter titles
            chapters_with_titles = self._generate_chapter_titles(chapters, scene_info)
            
            # Store chapters in database
            chapters_stored = self._store_chapters(draft_id, chapters_with_titles)
            
            # Calculate statistics
            total_word_count = sum(chapter.get('word_count', 0) for chapter in chapters_with_titles)
            
            result = {
                'success': True,
                'chapters_created': len(chapters_with_titles),
                'chapters_stored': chapters_stored,
                'total_word_count': total_word_count,
                'chaptering_mode': chaptering_mode,
                'target_chapter_length': target_chapter_length,
                'avg_chapter_length': total_word_count // len(chapters_with_titles) if chapters_with_titles else 0,
                'manuscript_word_count': manuscript_data['word_count']
            }
            
            logger.info(f"Stage 7 completed for draft {draft_id}: {chapters_stored} chapters created")
            return result
            
        except Exception as e:
            logger.error(f"Stage 7 failed for draft {draft_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'draft_id': draft_id
            }
    
    def _get_final_manuscript(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the final manuscript for chaptering.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Manuscript data or None if not found
        """
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT final_content, word_count, generated_at
                    FROM final_manuscripts
                    WHERE draft_id = %s
                    ORDER BY generated_at DESC
                    LIMIT 1
                """, (draft_id,))
                
                result = cursor.fetchone()
                
                if not result:
                    return None
                
                content, word_count, generated_at = result
                
                manuscript_data = {
                    'content': content,
                    'word_count': word_count,
                    'generated_at': generated_at
                }
            
            self.db_pool.putconn(conn)
            
            logger.debug(f"Retrieved final manuscript for draft {draft_id}: {word_count} words")
            return manuscript_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve final manuscript for draft {draft_id}: {e}")
            if 'conn' in locals():
                self.db_pool.putconn(conn)
            return None
    
    def _get_scene_information(self, draft_id: str) -> List[Dict[str, Any]]:
        """
        Get scene information to guide chapter breaks.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            List of scene information
        """
        try:
            conn = self.db_pool.getconn()
            scene_info = []
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT scene_number, title, setting, characters, analysis_json
                    FROM scenes
                    WHERE draft_id = %s
                    ORDER BY scene_number
                """, (draft_id,))
                
                scenes = cursor.fetchall()
                
                for scene in scenes:
                    scene_number, title, setting, characters, analysis_json = scene
                    
                    try:
                        analysis = json.loads(analysis_json) if analysis_json else {}
                        characters_list = json.loads(characters) if characters else []
                    except (json.JSONDecodeError, TypeError):
                        analysis = {}
                        characters_list = []
                    
                    scene_info.append({
                        'scene_number': scene_number,
                        'title': title,
                        'setting': setting,
                        'characters': characters_list,
                        'plot_function': analysis.get('plot_function', ''),
                        'significance': analysis.get('overall_significance', ''),
                        'conflicts': analysis.get('conflicts', [])
                    })
            
            self.db_pool.putconn(conn)
            
            logger.debug(f"Retrieved scene information for {len(scene_info)} scenes")
            return scene_info
            
        except Exception as e:
            logger.error(f"Failed to retrieve scene information for draft {draft_id}: {e}")
            if 'conn' in locals():
                self.db_pool.putconn(conn)
            return []
    
    def _flexible_chaptering(self, manuscript: str, scene_info: List[Dict[str, Any]], 
                           target_length: int) -> List[Dict[str, Any]]:
        """
        Create chapters using flexible AI-guided approach.
        
        Args:
            manuscript: Full manuscript text
            scene_info: Scene information for guidance
            target_length: Target chapter length in words
            
        Returns:
            List of chapter data
        """
        try:
            # Prepare scene information summary
            scene_summary = []
            for scene in scene_info:
                summary = f"Scene {scene['scene_number']}: {scene['title']}"
                if scene['plot_function']:
                    summary += f" - {scene['plot_function'][:100]}"
                scene_summary.append(summary)
            
            # Use AI to determine optimal chapter breaks
            prompt = self.prompt_template.get_chaptering_prompt().format(
                manuscript_text=manuscript[:10000],  # First 10k chars for analysis
                scene_information='\n'.join(scene_summary),
                target_length=target_length,
                chaptering_mode='flexible'
            )
            
            self.generation_engine.request.prompt = prompt
            self.generation_engine.request.instruction = f"Organize this manuscript into {len(scene_info) // 3} to {len(scene_info) // 2} chapters with natural breaks."
            
            response = self.generation_engine.generate(skip_quota=True)
            
            if response.success:
                try:
                    ai_chaptering = json.loads(response.text.strip())
                    return self._process_ai_chaptering(ai_chaptering, manuscript)
                except json.JSONDecodeError:
                    logger.warning("Could not parse AI chaptering response, falling back to constrained approach")
                    return self._constrained_chaptering(manuscript, scene_info, target_length)
            else:
                logger.warning("AI chaptering failed, using constrained approach")
                return self._constrained_chaptering(manuscript, scene_info, target_length)
                
        except Exception as e:
            logger.error(f"Error in flexible chaptering: {e}")
            return self._constrained_chaptering(manuscript, scene_info, target_length)
    
    def _constrained_chaptering(self, manuscript: str, scene_info: List[Dict[str, Any]], 
                              target_length: int) -> List[Dict[str, Any]]:
        """
        Create chapters using constrained word-count approach.
        
        Args:
            manuscript: Full manuscript text
            scene_info: Scene information for guidance
            target_length: Target chapter length in words
            
        Returns:
            List of chapter data
        """
        try:
            chapters = []
            words = manuscript.split()
            total_words = len(words)
            
            # Calculate approximate number of chapters
            estimated_chapters = max(1, total_words // target_length)
            
            # Find scene breaks in the manuscript
            scene_breaks = self._find_scene_breaks_in_text(manuscript, scene_info)
            
            current_pos = 0
            chapter_num = 1
            
            while current_pos < total_words:
                # Determine chapter end position
                target_end = min(current_pos + target_length, total_words)
                
                # Find the best scene break near the target position
                best_break = self._find_best_chapter_break(
                    scene_breaks, current_pos, target_end, words
                )
                
                if best_break > current_pos:
                    # Extract chapter content
                    chapter_words = words[current_pos:best_break]
                    chapter_content = ' '.join(chapter_words)
                    
                    chapters.append({
                        'chapter_number': chapter_num,
                        'content': chapter_content,
                        'word_count': len(chapter_words),
                        'start_position': current_pos,
                        'end_position': best_break
                    })
                    
                    current_pos = best_break
                    chapter_num += 1
                else:
                    # If no good break found, just use remaining content
                    remaining_words = words[current_pos:]
                    chapters.append({
                        'chapter_number': chapter_num,
                        'content': ' '.join(remaining_words),
                        'word_count': len(remaining_words),
                        'start_position': current_pos,
                        'end_position': total_words
                    })
                    break
                
                # Safety check to prevent infinite loops
                if chapter_num > estimated_chapters + 5:
                    break
            
            logger.info(f"Created {len(chapters)} chapters using constrained approach")
            return chapters
            
        except Exception as e:
            logger.error(f"Error in constrained chaptering: {e}")
            # Fallback: create single chapter with all content
            return [{
                'chapter_number': 1,
                'content': manuscript,
                'word_count': len(manuscript.split()),
                'start_position': 0,
                'end_position': len(manuscript.split())
            }]
    
    def _find_scene_breaks_in_text(self, manuscript: str, scene_info: List[Dict[str, Any]]) -> List[int]:
        """
        Find approximate positions of scene breaks in the manuscript text.
        
        Args:
            manuscript: Full manuscript text
            scene_info: Scene information
            
        Returns:
            List of word positions where scenes likely break
        """
        scene_breaks = []
        words = manuscript.split()
        
        try:
            # Look for scene markers in the text
            scene_markers = [
                '=== ',  # Scene headers we added
                'Chapter ',
                '\n\n\n',  # Multiple line breaks
                '* * *',   # Scene separators
                '---'      # Dashes
            ]
            
            text_lower = manuscript.lower()
            
            for i, word in enumerate(words):
                # Check if this position might be a scene break
                word_position = manuscript.lower().find(word.lower())
                
                # Look for scene markers near this position
                for marker in scene_markers:
                    marker_pos = text_lower.find(marker.lower(), max(0, word_position - 50))
                    if marker_pos != -1 and abs(marker_pos - word_position) < 100:
                        scene_breaks.append(i)
                        break
            
            # Also add breaks based on scene titles
            for scene in scene_info:
                scene_title = scene['title'].lower()
                title_pos = text_lower.find(scene_title)
                if title_pos != -1:
                    # Find approximate word position
                    word_pos = len(manuscript[:title_pos].split())
                    if word_pos not in scene_breaks:
                        scene_breaks.append(word_pos)
            
            # Sort and remove duplicates
            scene_breaks = sorted(list(set(scene_breaks)))
            
            logger.debug(f"Found {len(scene_breaks)} potential scene breaks")
            return scene_breaks
            
        except Exception as e:
            logger.warning(f"Error finding scene breaks: {e}")
            return []
    
    def _find_best_chapter_break(self, scene_breaks: List[int], start_pos: int, 
                               target_pos: int, words: List[str]) -> int:
        """
        Find the best position for a chapter break.
        
        Args:
            scene_breaks: List of potential scene break positions
            start_pos: Chapter start position
            target_pos: Target chapter end position
            words: All words in the manuscript
            
        Returns:
            Best chapter break position
        """
        try:
            # Filter scene breaks to those in our range
            candidate_breaks = [
                pos for pos in scene_breaks 
                if start_pos < pos <= target_pos + 500  # Allow some overage
            ]
            
            if not candidate_breaks:
                # No scene breaks found, look for natural paragraph breaks
                return self._find_paragraph_break(start_pos, target_pos, words)
            
            # Find the break closest to our target
            best_break = min(candidate_breaks, key=lambda x: abs(x - target_pos))
            
            # Don't allow chapters that are too short
            min_chapter_length = 500  # Minimum 500 words
            if best_break - start_pos < min_chapter_length:
                # Look for a later break
                later_breaks = [pos for pos in candidate_breaks if pos - start_pos >= min_chapter_length]
                if later_breaks:
                    best_break = min(later_breaks, key=lambda x: abs(x - target_pos))
            
            return best_break
            
        except Exception as e:
            logger.warning(f"Error finding best chapter break: {e}")
            return target_pos
    
    def _find_paragraph_break(self, start_pos: int, target_pos: int, words: List[str]) -> int:
        """
        Find a natural paragraph break near the target position.
        
        Args:
            start_pos: Chapter start position
            target_pos: Target chapter end position
            words: All words in the manuscript
            
        Returns:
            Paragraph break position
        """
        try:
            # Look for paragraph endings (words ending with . ! ? followed by capitalized words)
            search_range = range(max(start_pos, target_pos - 200), min(len(words), target_pos + 200))
            
            for i in search_range:
                if i < len(words) - 1:
                    current_word = words[i].strip()
                    next_word = words[i + 1].strip()
                    
                    # Check for sentence ending
                    if (current_word.endswith(('.', '!', '?')) and 
                        next_word and next_word[0].isupper()):
                        return i + 1
            
            # If no good break found, just use target position
            return min(target_pos, len(words))
            
        except Exception as e:
            logger.warning(f"Error finding paragraph break: {e}")
            return target_pos
    
    def _process_ai_chaptering(self, ai_result: Dict[str, Any], manuscript: str) -> List[Dict[str, Any]]:
        """
        Process AI chaptering results into standard format.
        
        Args:
            ai_result: AI chaptering analysis
            manuscript: Full manuscript text
            
        Returns:
            Processed chapter data
        """
        try:
            chapters = []
            ai_chapters = ai_result.get('chapters', [])
            
            if not ai_chapters:
                # Fallback to simple division
                words = manuscript.split()
                chapter_size = len(words) // 5  # Default to 5 chapters
                
                for i in range(5):
                    start = i * chapter_size
                    end = start + chapter_size if i < 4 else len(words)
                    
                    chapters.append({
                        'chapter_number': i + 1,
                        'content': ' '.join(words[start:end]),
                        'word_count': end - start,
                        'title': f'Chapter {i + 1}'
                    })
            else:
                # Process AI-generated chapters
                for ai_chapter in ai_chapters:
                    chapter_content = ai_chapter.get('content', '')
                    word_count = len(chapter_content.split()) if chapter_content else 0
                    
                    chapters.append({
                        'chapter_number': ai_chapter.get('chapter_number', len(chapters) + 1),
                        'content': chapter_content,
                        'word_count': word_count,
                        'title': ai_chapter.get('title', f"Chapter {len(chapters) + 1}"),
                        'summary': ai_chapter.get('summary', ''),
                        'key_events': ai_chapter.get('key_events', []),
                        'cliffhanger': ai_chapter.get('cliffhanger', 'No')
                    })
            
            return chapters
            
        except Exception as e:
            logger.error(f"Error processing AI chaptering: {e}")
            # Return single chapter as fallback
            return [{
                'chapter_number': 1,
                'content': manuscript,
                'word_count': len(manuscript.split()),
                'title': 'Chapter 1'
            }]
    
    def _generate_chapter_titles(self, chapters: List[Dict[str, Any]], 
                               scene_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate compelling titles for chapters that don't have them.
        
        Args:
            chapters: List of chapter data
            scene_info: Scene information for context
            
        Returns:
            Chapters with generated titles
        """
        try:
            for chapter in chapters:
                # Skip if chapter already has a meaningful title
                current_title = chapter.get('title', '')
                if current_title and not current_title.startswith('Chapter '):
                    continue
                
                # Extract key content for title generation
                content = chapter.get('content', '')
                if not content:
                    continue
                
                # Get first few sentences for context
                sentences = content.split('.')[: 3]  # First 3 sentences
                context = '. '.join(sentences)[:500]  # Limit context length
                
                # Try to generate a title using AI
                generated_title = self._ai_generate_title(context, chapter['chapter_number'])
                
                if generated_title:
                    chapter['title'] = generated_title
                else:
                    # Fallback to descriptive title
                    chapter['title'] = self._create_fallback_title(content, chapter['chapter_number'])
            
            return chapters
            
        except Exception as e:
            logger.warning(f"Error generating chapter titles: {e}")
            # Ensure all chapters have titles
            for i, chapter in enumerate(chapters):
                if not chapter.get('title'):
                    chapter['title'] = f"Chapter {i + 1}"
            return chapters
    
    def _ai_generate_title(self, content_context: str, chapter_number: int) -> Optional[str]:
        """
        Generate a chapter title using AI.
        
        Args:
            content_context: Chapter content context
            chapter_number: Chapter number
            
        Returns:
            Generated title or None if generation failed
        """
        try:
            prompt = f"""Create a compelling, concise chapter title (2-5 words) for Chapter {chapter_number} based on this content:

{content_context}

The title should:
1. Capture the essence of the chapter
2. Be intriguing but not spoil major plot points
3. Fit the tone of the story
4. Be 2-5 words long

Respond with only the title, no quotes or explanation."""
            
            self.generation_engine.request.prompt = prompt
            self.generation_engine.request.instruction = f"Generate a chapter title for Chapter {chapter_number}."
            
            response = self.generation_engine.generate(skip_quota=True)
            
            if response.success:
                title = response.text.strip().strip('"').strip("'")
                
                # Validate title
                if len(title) > 0 and len(title.split()) <= 6:
                    return title
            
            return None
            
        except Exception as e:
            logger.warning(f"Error generating AI title for chapter {chapter_number}: {e}")
            return None
    
    def _create_fallback_title(self, content: str, chapter_number: int) -> str:
        """
        Create a fallback title based on content analysis.
        
        Args:
            content: Chapter content
            chapter_number: Chapter number
            
        Returns:
            Fallback title
        """
        try:
            # Extract key nouns and action words
            words = content.lower().split()[:200]  # First 200 words
            
            # Common action words that might make good titles
            action_words = ['battle', 'journey', 'discovery', 'escape', 'arrival', 'departure', 
                          'meeting', 'confrontation', 'revelation', 'decision', 'choice']
            
            # Look for action words in the content
            found_actions = [word for word in action_words if word in words]
            
            if found_actions:
                return f"The {found_actions[0].title()}"
            
            # Look for character names (capitalized words)
            capitalized = [word.strip('.,!?') for word in content.split() if word[0].isupper() and len(word) > 2]
            
            if capitalized:
                return f"{capitalized[0]}'s Tale"
            
            # Generic fallback
            return f"Chapter {chapter_number}"
            
        except Exception as e:
            logger.warning(f"Error creating fallback title: {e}")
            return f"Chapter {chapter_number}"
    
    def _store_chapters(self, draft_id: str, chapters: List[Dict[str, Any]]) -> int:
        """
        Store chapters in the database.
        
        Args:
            draft_id: UUID of the draft
            chapters: List of chapter data
            
        Returns:
            Number of chapters stored
        """
        if not chapters:
            return 0
        
        try:
            conn = self.db_pool.getconn()
            chapters_stored = 0
            
            with conn.cursor() as cursor:
                # Clear existing chapters for this draft
                cursor.execute("DELETE FROM chapters WHERE draft_id = %s", (draft_id,))
                
                # Prepare bulk insert data
                chapter_data = []
                for chapter in chapters:
                    chapter_data.append((
                        draft_id,
                        chapter.get('chapter_number', 1),
                        chapter.get('title', 'Untitled Chapter'),
                        chapter.get('content', '')
                    ))
                
                # Bulk insert chapters
                if chapter_data:
                    cursor.executemany("""
                        INSERT INTO chapters (draft_id, chapter_number, title, content)
                        VALUES (%s, %s, %s, %s)
                    """, chapter_data)
                    
                    chapters_stored = cursor.rowcount
                    conn.commit()
            
            self.db_pool.putconn(conn)
            
            logger.info(f"Stored {chapters_stored} chapters for draft {draft_id}")
            return chapters_stored
            
        except Exception as e:
            logger.error(f"Failed to store chapters for draft {draft_id}: {e}")
            if 'conn' in locals():
                conn.rollback()
                self.db_pool.putconn(conn)
            raise
    
    def get_chaptering_statistics(self, draft_id: str) -> Dict[str, Any]:
        """
        Get statistics about the chaptering process.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Chaptering statistics
        """
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                # Get chapter statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as chapter_count,
                        AVG(LENGTH(content)) as avg_chapter_length,
                        MIN(LENGTH(content)) as min_chapter_length,
                        MAX(LENGTH(content)) as max_chapter_length,
                        SUM(LENGTH(content)) as total_content_length
                    FROM chapters
                    WHERE draft_id = %s
                """, (draft_id,))
                
                result = cursor.fetchone()
                
                if result:
                    count, avg_len, min_len, max_len, total_len = result
                    
                    # Convert to word counts (approximate)
                    avg_words = int(avg_len / 5) if avg_len else 0  # ~5 chars per word
                    min_words = int(min_len / 5) if min_len else 0
                    max_words = int(max_len / 5) if max_len else 0
                    total_words = int(total_len / 5) if total_len else 0
                    
                    stats = {
                        'chapter_count': count,
                        'avg_chapter_words': avg_words,
                        'min_chapter_words': min_words,
                        'max_chapter_words': max_words,
                        'total_words': total_words
                    }
                else:
                    stats = {
                        'chapter_count': 0,
                        'avg_chapter_words': 0,
                        'min_chapter_words': 0,
                        'max_chapter_words': 0,
                        'total_words': 0
                    }
                
                # Get chapter titles
                cursor.execute("""
                    SELECT chapter_number, title
                    FROM chapters
                    WHERE draft_id = %s
                    ORDER BY chapter_number
                """, (draft_id,))
                
                titles = cursor.fetchall()
                stats['chapter_titles'] = [{'number': num, 'title': title} for num, title in titles]
            
            self.db_pool.putconn(conn)
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get chaptering statistics for draft {draft_id}: {e}")
            if 'conn' in locals():
                self.db_pool.putconn(conn)
            return {'error': str(e)}
    
    def rechapter_manuscript(self, draft_id: str, new_mode: str = 'flexible', 
                           new_target_length: int = 2500) -> Dict[str, Any]:
        """
        Re-run chaptering with different parameters.
        
        Args:
            draft_id: UUID of the draft
            new_mode: New chaptering mode
            new_target_length: New target chapter length
            
        Returns:
            Re-chaptering results
        """
        try:
            # Delete existing chapters
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM chapters WHERE draft_id = %s", (draft_id,))
                deleted_count = cursor.rowcount
                conn.commit()
            
            self.db_pool.putconn(conn)
            
            logger.info(f"Deleted {deleted_count} existing chapters for re-chaptering")
            
            # Re-run chaptering
            result = self.run(draft_id, new_mode, new_target_length)
            result['rechaptered'] = True
            result['deleted_chapters'] = deleted_count
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to rechapter manuscript for draft {draft_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'draft_id': draft_id
            }
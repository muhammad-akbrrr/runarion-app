"""
Stage 6: Enhancement
Enhances scenes based on identified plot issues and generates final manuscript.
"""

import json
import logging
import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from .prompt_template import DeconstructorPrompts
from utils.database_utils import utf8_database_connection, clean_text_for_database, ensure_utf8_json

logger = logging.getLogger(__name__)

class EnhancementStage:
    """
    Stage 6 of the deconstruction pipeline.
    Enhances scenes by addressing plot issues and generates final manuscript.
    """
    
    def __init__(self, db_pool, generation_engine):
        """
        Initialize the enhancement stage.
        
        Args:
            db_pool: Database connection pool
            generation_engine: AI generation engine
        """
        self.db_pool = db_pool
        self.generation_engine = generation_engine
        self.prompt_template = DeconstructorPrompts()
    
    def run(self, draft_id: str, chaptering_mode: str = 'flexible', target_chapter_length: int = 2500) -> Dict[str, Any]:
        """
        Execute Stage 6: Scene enhancement and manuscript generation.
        
        Args:
            draft_id: UUID of the draft
            chaptering_mode: Chaptering approach ('flexible' or 'constrained')
            target_chapter_length: Target word count per chapter
            
        Returns:
            Stage execution results
        """
        logger.info(f"Starting Stage 6 enhancement for draft {draft_id} (chaptering_mode: {chaptering_mode}, target_length: {target_chapter_length})")
        
        try:
            # Get scenes and their associated issues
            scenes_data = self._get_scenes_and_issues(draft_id)
            
            if not scenes_data['scenes']:
                logger.warning(f"No scenes found for enhancement in draft {draft_id}")
                return {
                    'success': True,
                    'scenes_enhanced': 0,
                    'message': 'No scenes to enhance'
                }
            
            # Get supporting context data with chaptering information
            context_data = self._get_enhancement_context(draft_id)
            context_data['chaptering_mode'] = chaptering_mode
            context_data['target_chapter_length'] = target_chapter_length
            
            # Track enhancement progress
            enhanced_scenes = 0
            failed_enhancements = []
            
            # Process each scene for enhancement
            for scene in scenes_data['scenes']:
                try:
                    # Get issues specific to this scene
                    scene_issues = [issue for issue in scenes_data['issues'] 
                                  if issue['affected_scene_id'] == scene['id']]
                    
                    # Only enhance scenes that have issues or can benefit from improvement
                    if scene_issues or self._needs_enhancement(scene):
                        enhanced_content = self._enhance_scene(scene, scene_issues, context_data)
                        
                        if enhanced_content:
                            self._update_scene_enhancement(scene['id'], enhanced_content)
                            enhanced_scenes += 1
                            logger.debug(f"Enhanced scene {scene['scene_number']} for draft {draft_id}")
                        else:
                            failed_enhancements.append(scene['scene_number'])
                    
                except Exception as e:
                    logger.error(f"Failed to enhance scene {scene['scene_number']}: {e}")
                    failed_enhancements.append(scene['scene_number'])
            
            # Generate final manuscript from enhanced scenes
            final_manuscript = self._generate_final_manuscript(draft_id, scenes_data['scenes'])
            manuscript_stored = False
            
            if final_manuscript:
                manuscript_stored = self._store_final_manuscript(draft_id, final_manuscript)
            
            result = {
                'success': True,
                'total_scenes': len(scenes_data['scenes']),
                'scenes_enhanced': enhanced_scenes,
                'failed_enhancements': len(failed_enhancements),
                'failed_scene_numbers': failed_enhancements if failed_enhancements else None,
                'issues_addressed': len(scenes_data['issues']),
                'final_manuscript_generated': manuscript_stored,
                'final_word_count': len(final_manuscript.split()) if final_manuscript else 0
            }
            
            logger.info(f"Stage 6 completed for draft {draft_id}: {enhanced_scenes} scenes enhanced, manuscript generated: {manuscript_stored}")
            return result
            
        except Exception as e:
            logger.error(f"Stage 6 failed for draft {draft_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'draft_id': draft_id
            }
    
    def _get_scenes_and_issues(self, draft_id: str) -> Dict[str, Any]:
        """
        Retrieve scenes and their associated plot issues.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Dictionary containing scenes and issues data
        """
        try:
            conn = self.db_pool.getconn()
            
            scenes_data = {
                'scenes': [],
                'issues': []
            }
            
            with conn.cursor() as cursor:
                # Get all scenes with their content and analysis
                cursor.execute("""
                    SELECT id, scene_number, title, setting, characters, 
                           original_content, enhanced_content, analysis_json
                    FROM scenes 
                    WHERE draft_id = %s
                    ORDER BY scene_number
                """, (draft_id,))
                
                scenes = cursor.fetchall()
                
                for scene in scenes:
                    scene_id, scene_number, title, setting, characters, original_content, enhanced_content, analysis_json = scene
                    
                    try:
                        analysis = json.loads(analysis_json) if analysis_json else {}
                        characters_list = json.loads(characters) if characters else []
                    except (json.JSONDecodeError, TypeError):
                        analysis = {}
                        characters_list = []
                    
                    scenes_data['scenes'].append({
                        'id': scene_id,
                        'scene_number': scene_number,
                        'title': title,
                        'setting': setting,
                        'characters': characters_list,
                        'original_content': original_content,
                        'enhanced_content': enhanced_content,
                        'analysis': analysis
                    })
                
                # Get all plot issues
                cursor.execute("""
                    SELECT pi.id, pi.affected_scene_id, pi.issue_type, 
                           pi.description, pi.severity, pi.suggested_fix,
                           s.scene_number
                    FROM plot_issues pi
                    JOIN scenes s ON pi.affected_scene_id = s.id
                    WHERE pi.draft_id = %s
                    ORDER BY pi.severity DESC, s.scene_number
                """, (draft_id,))
                
                issues = cursor.fetchall()
                
                for issue in issues:
                    issue_id, scene_id, issue_type, description, severity, suggested_fix, scene_number = issue
                    
                    scenes_data['issues'].append({
                        'id': issue_id,
                        'affected_scene_id': scene_id,
                        'scene_number': scene_number,
                        'issue_type': issue_type,
                        'description': description,
                        'severity': severity,
                        'suggested_fix': suggested_fix
                    })
            
            self.db_pool.putconn(conn)
            
            logger.debug(f"Retrieved {len(scenes_data['scenes'])} scenes and {len(scenes_data['issues'])} issues for enhancement")
            return scenes_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve scenes and issues for draft {draft_id}: {e}")
            if 'conn' in locals():
                self.db_pool.putconn(conn)
            raise
    
    def _get_enhancement_context(self, draft_id: str) -> Dict[str, Any]:
        """
        Get additional context data needed for enhancement.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Context data for enhancement
        """
        try:
            conn = self.db_pool.getconn()
            context = {
                'character_reports': {},
                'narrative_overview': {},
                'style_guidance': ''
            }
            
            with conn.cursor() as cursor:
                # Get analysis reports for context
                cursor.execute("""
                    SELECT report_type, report_subject, content_json
                    FROM analysis_reports
                    WHERE draft_id = %s
                """, (draft_id,))
                
                reports = cursor.fetchall()
                
                for report_type, subject, content in reports:
                    try:
                        content_data = json.loads(content) if content else {}
                        
                        if report_type == 'CHARACTER_ARC':
                            context['character_reports'][subject] = content_data
                        elif report_type == 'NARRATIVE_OVERVIEW':
                            context['narrative_overview'] = content_data
                        
                    except (json.JSONDecodeError, TypeError):
                        continue
                
                # Extract style guidance from character reports
                if context['character_reports']:
                    style_elements = []
                    for char_data in context['character_reports'].values():
                        if 'narrative_voice' in char_data:
                            style_elements.append(char_data['narrative_voice'])
                    
                    context['style_guidance'] = '; '.join(style_elements[:3])  # Limit to top 3
            
            self.db_pool.putconn(conn)
            return context
            
        except Exception as e:
            logger.error(f"Failed to get enhancement context for draft {draft_id}: {e}")
            if 'conn' in locals():
                self.db_pool.putconn(conn)
            return {'character_reports': {}, 'narrative_overview': {}, 'style_guidance': ''}
    
    def _needs_enhancement(self, scene: Dict[str, Any]) -> bool:
        """
        Determine if a scene needs enhancement even without explicit issues.
        
        Args:
            scene: Scene data
            
        Returns:
            Whether scene needs enhancement
        """
        # Check if scene is already enhanced
        if scene.get('enhanced_content'):
            return False
        
        # Check content length - very short scenes might need expansion
        original_content = scene.get('original_content', '')
        if len(original_content.split()) < 100:  # Less than 100 words
            return True
        
        # Check for incomplete analysis
        analysis = scene.get('analysis', {})
        if not analysis.get('character_development') or not analysis.get('plot_function'):
            return True
        
        # Check for weak dialogue or description indicators
        content_lower = original_content.lower()
        dialogue_count = content_lower.count('"')
        if dialogue_count < 2 and len(original_content.split()) > 200:  # Long scene with little dialogue
            return True
        
        return False
    
    def _enhance_scene(self, scene: Dict[str, Any], issues: List[Dict[str, Any]], 
                      context: Dict[str, Any]) -> Optional[str]:
        """
        Enhance a single scene using AI processing.
        
        Args:
            scene: Scene data
            issues: List of issues affecting this scene
            context: Enhancement context data
            
        Returns:
            Enhanced scene content or None if enhancement failed
        """
        try:
            # Prepare issue descriptions
            issue_descriptions = []
            for issue in issues:
                issue_desc = f"- {issue['issue_type']}: {issue['description']}"
                if issue['suggested_fix']:
                    issue_desc += f" (Suggested fix: {issue['suggested_fix']})"
                issue_descriptions.append(issue_desc)
            
            # Prepare character context
            scene_characters = scene.get('characters', [])
            character_info = []
            
            for character in scene_characters[:3]:  # Limit to top 3 characters
                if character in context['character_reports']:
                    char_data = context['character_reports'][character]
                    char_info = f"{character}: "
                    
                    # Add key character traits
                    if 'personality_profile' in char_data:
                        traits = char_data['personality_profile'].get('core_traits', [])
                        char_info += f"Traits: {', '.join(traits[:3])}"
                    
                    # Add motivations
                    if 'motivations' in char_data:
                        primary_motivation = char_data['motivations'].get('primary', '')
                        if primary_motivation:
                            char_info += f"; Motivation: {primary_motivation}"
                    
                    character_info.append(char_info)
            
            # Prepare plot context
            plot_context = f"Scene {scene['scene_number']}: {scene['title']}"
            if scene['analysis'].get('plot_function'):
                plot_context += f"\nPlot function: {scene['analysis']['plot_function']}"
            
            if context['narrative_overview']:
                overview = context['narrative_overview']
                if 'narrative_complexity' in overview:
                    plot_context += f"\nStory complexity: {overview['narrative_complexity']}"
            
            # Generate enhancement prompt
            prompt = self.prompt_template.get_enhancement_prompt().format(
                original_scene=scene['original_content'],
                scene_issues='\n'.join(issue_descriptions) if issue_descriptions else 'No specific issues identified, general enhancement requested',
                character_information='\n'.join(character_info) if character_info else 'Character information not available',
                plot_context=plot_context
            )
            
            # Add style guidance if available
            if context.get('style_guidance'):
                prompt += f"\n\nSTYLE GUIDANCE: {context['style_guidance']}"
            
            # Add chaptering guidance for enhancement
            chaptering_guidance = self._get_chaptering_guidance(scene, context)
            if chaptering_guidance:
                prompt += f"\n\nCHAPTERING GUIDANCE: {chaptering_guidance}"
            
            # Generate enhanced scene
            self.generation_engine.request.prompt = prompt
            self.generation_engine.request.instruction = f"Enhance scene {scene['scene_number']} while maintaining the author's voice and addressing identified issues."
            
            response = self.generation_engine.generate(skip_quota=True)
            
            if response.success:
                enhanced_text = response.text.strip()
                
                # Validate enhancement
                if self._validate_enhancement(scene['original_content'], enhanced_text):
                    return enhanced_text
                else:
                    logger.warning(f"Enhancement validation failed for scene {scene['scene_number']}")
                    return scene['original_content']  # Fallback to original
            else:
                logger.error(f"AI generation failed for scene {scene['scene_number']}: {response.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Error enhancing scene {scene['scene_number']}: {e}")
            return None
    
    def _get_chaptering_guidance(self, scene: Dict[str, Any], context: Dict[str, Any]) -> str:
        """
        Generate chaptering guidance for scene enhancement.
        
        Args:
            scene: Scene data
            context: Enhancement context including chaptering parameters
            
        Returns:
            Chaptering guidance string
        """
        chaptering_mode = context.get('chaptering_mode', 'flexible')
        target_length = context.get('target_chapter_length', 2500)
        scene_number = scene.get('scene_number', 0)
        
        guidance_parts = []
        
        # Mode-specific guidance
        if chaptering_mode == 'constrained':
            guidance_parts.append(f"This novel will use a constrained chaptering approach with target chapters of {target_length} words.")
            guidance_parts.append("Ensure scene transitions and pacing support clear chapter boundaries.")
        else:
            guidance_parts.append(f"This novel will use flexible chaptering with approximate target chapters of {target_length} words.")
            guidance_parts.append("Focus on natural narrative flow that can adapt to organic chapter breaks.")
        
        # Scene position guidance
        if scene_number <= 3:
            guidance_parts.append("This is an early scene - ensure strong character establishment and narrative hooks for chapter engagement.")
        elif scene_number % 5 == 0:  # Every 5th scene might be a chapter break
            guidance_parts.append("This scene may serve as a chapter transition point - consider enhancing emotional beats and narrative momentum.")
        
        # Length-based guidance
        original_length = len(scene.get('original_content', '').split())
        if original_length < target_length // 4:  # Less than 1/4 of target chapter length
            guidance_parts.append("This scene is relatively short - consider expanding with additional character development or atmospheric detail to support chapter structure.")
        elif original_length > target_length // 2:  # More than 1/2 of target chapter length
            guidance_parts.append("This scene is substantial - ensure internal pacing and structure that could anchor or complement a chapter.")
        
        return ' '.join(guidance_parts) if guidance_parts else ''

    def _validate_enhancement(self, original: str, enhanced: str) -> bool:
        """
        Validate that the enhancement is appropriate.
        
        Args:
            original: Original scene content
            enhanced: Enhanced scene content
            
        Returns:
            Whether enhancement is valid
        """
        # Basic length check - enhancement should not be drastically shorter
        if len(enhanced) < len(original) * 0.7:
            return False
        
        # Check for excessive length increase
        if len(enhanced) > len(original) * 3:
            return False
        
        # Check that enhancement contains meaningful content
        if len(enhanced.strip()) < 50:
            return False
        
        # Check for proper narrative structure (has some dialogue or action)
        has_dialogue = '"' in enhanced or "'" in enhanced
        has_action = any(word in enhanced.lower() for word in ['walked', 'said', 'looked', 'moved', 'turned'])
        
        if not (has_dialogue or has_action):
            return False
        
        return True
    
    def _update_scene_enhancement(self, scene_id: int, enhanced_content: str) -> None:
        """
        Update the scene with enhanced content.
        
        Args:
            scene_id: Scene database ID
            enhanced_content: Enhanced scene content
        """
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE scenes 
                    SET enhanced_content = %s
                    WHERE id = %s
                """, (enhanced_content, scene_id))
                
                conn.commit()
            
            self.db_pool.putconn(conn)
            
        except Exception as e:
            logger.error(f"Failed to update scene enhancement for scene {scene_id}: {e}")
            if 'conn' in locals():
                conn.rollback()
                self.db_pool.putconn(conn)
            raise
    
    def _generate_final_manuscript(self, draft_id: str, scenes: List[Dict[str, Any]]) -> Optional[str]:
        """
        Generate the final manuscript by combining enhanced scenes.
        
        Args:
            draft_id: UUID of the draft
            scenes: List of scene data
            
        Returns:
            Final manuscript text or None if generation failed
        """
        try:
            manuscript_parts = []
            
            for scene in sorted(scenes, key=lambda x: x['scene_number']):
                # Use enhanced content if available, otherwise use original
                scene_content = scene.get('enhanced_content') or scene.get('original_content', '')
                
                if scene_content.strip():
                    # Add scene break formatting
                    scene_header = f"\n\n=== {scene['title']} ===\n\n"
                    manuscript_parts.append(scene_header + scene_content)
            
            if not manuscript_parts:
                logger.warning(f"No content found to generate manuscript for draft {draft_id}")
                return None
            
            # Combine all scenes
            full_manuscript = '\n\n'.join(manuscript_parts)
            
            # Clean up formatting
            full_manuscript = self._clean_manuscript_formatting(full_manuscript)
            
            logger.info(f"Generated final manuscript for draft {draft_id}: {len(full_manuscript.split())} words")
            return full_manuscript
            
        except Exception as e:
            logger.error(f"Error generating final manuscript for draft {draft_id}: {e}")
            return None
    
    def _clean_manuscript_formatting(self, manuscript: str) -> str:
        """
        Clean and standardize manuscript formatting.
        
        Args:
            manuscript: Raw manuscript text
            
        Returns:
            Cleaned manuscript text
        """
        try:
            # Remove excessive whitespace
            manuscript = re.sub(r'\n{4,}', '\n\n\n', manuscript)  # Max 3 consecutive newlines
            manuscript = re.sub(r' {2,}', ' ', manuscript)  # Remove multiple spaces
            
            # Standardize paragraph breaks
            manuscript = re.sub(r'\n\s*\n', '\n\n', manuscript)
            
            # Clean up dialogue formatting
            manuscript = re.sub(r'"\s*\n\s*"', '" "', manuscript)  # Fix broken dialogue
            
            # Remove trailing whitespace from lines
            lines = [line.rstrip() for line in manuscript.split('\n')]
            manuscript = '\n'.join(lines)
            
            # Ensure manuscript starts and ends cleanly
            manuscript = manuscript.strip()
            
            return manuscript
            
        except Exception as e:
            logger.warning(f"Error cleaning manuscript formatting: {e}")
            return manuscript  # Return original if cleaning fails
    
    def _store_final_manuscript(self, draft_id: str, manuscript_content: str) -> bool:
        """
        Store the final manuscript in the database.
        
        Args:
            draft_id: UUID of the draft
            manuscript_content: Final manuscript content
            
        Returns:
            Success status
        """
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                # Calculate word count
                word_count = len(manuscript_content.split())
                
                # Generate processing summary
                processing_summary = f"Enhanced manuscript generated from {word_count} words of content on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                # Clear any existing final manuscript for this draft
                cursor.execute("DELETE FROM final_manuscripts WHERE draft_id = %s", (draft_id,))
                
                # Insert new final manuscript
                cursor.execute("""
                    INSERT INTO final_manuscripts (
                        draft_id, final_content, word_count, 
                        generated_at, generated_by, processing_summary
                    )
                    VALUES (%s, %s, %s, NOW(), 1, %s)
                """, (draft_id, manuscript_content, word_count, processing_summary))
                
                conn.commit()
            
            self.db_pool.putconn(conn)
            
            logger.info(f"Stored final manuscript for draft {draft_id}: {word_count} words")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store final manuscript for draft {draft_id}: {e}")
            if 'conn' in locals():
                conn.rollback()
                self.db_pool.putconn(conn)
            return False
    
    def get_enhancement_statistics(self, draft_id: str) -> Dict[str, Any]:
        """
        Get statistics about the enhancement process.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Enhancement statistics
        """
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                # Get scene enhancement statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_scenes,
                        COUNT(CASE WHEN enhanced_content IS NOT NULL THEN 1 END) as enhanced_scenes,
                        AVG(LENGTH(original_content)) as avg_original_length,
                        AVG(LENGTH(enhanced_content)) as avg_enhanced_length
                    FROM scenes
                    WHERE draft_id = %s
                """, (draft_id,))
                
                result = cursor.fetchone()
                
                if result:
                    total_scenes, enhanced_scenes, avg_original, avg_enhanced = result
                    
                    stats = {
                        'total_scenes': total_scenes,
                        'enhanced_scenes': enhanced_scenes,
                        'enhancement_percentage': (enhanced_scenes / total_scenes * 100) if total_scenes > 0 else 0,
                        'avg_original_length': int(avg_original) if avg_original else 0,
                        'avg_enhanced_length': int(avg_enhanced) if avg_enhanced else 0,
                        'avg_enhancement_ratio': (avg_enhanced / avg_original) if avg_original and avg_enhanced else 1.0
                    }
                else:
                    stats = {
                        'total_scenes': 0,
                        'enhanced_scenes': 0,
                        'enhancement_percentage': 0,
                        'avg_original_length': 0,
                        'avg_enhanced_length': 0,
                        'avg_enhancement_ratio': 1.0
                    }
                
                # Get final manuscript statistics
                cursor.execute("""
                    SELECT word_count, generated_at
                    FROM final_manuscripts
                    WHERE draft_id = %s
                    ORDER BY generated_at DESC
                    LIMIT 1
                """, (draft_id,))
                
                manuscript_result = cursor.fetchone()
                
                if manuscript_result:
                    word_count, generated_at = manuscript_result
                    stats['final_manuscript'] = {
                        'word_count': word_count,
                        'generated_at': generated_at.isoformat() if generated_at else None
                    }
                else:
                    stats['final_manuscript'] = None
            
            self.db_pool.putconn(conn)
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get enhancement statistics for draft {draft_id}: {e}")
            if 'conn' in locals():
                self.db_pool.putconn(conn)
            return {'error': str(e)}
    
    def reprocess_scene_enhancements(self, draft_id: str, scene_numbers: List[int] = None) -> Dict[str, Any]:
        """
        Reprocess enhancements for specific scenes or all scenes.
        
        Args:
            draft_id: UUID of the draft
            scene_numbers: Optional list of specific scene numbers to reprocess
            
        Returns:
            Reprocessing results
        """
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                # Clear existing enhanced content for specified scenes
                if scene_numbers:
                    placeholders = ','.join(['%s'] * len(scene_numbers))
                    cursor.execute(f"""
                        UPDATE scenes 
                        SET enhanced_content = NULL 
                        WHERE draft_id = %s AND scene_number IN ({placeholders})
                    """, [draft_id] + scene_numbers)
                else:
                    cursor.execute("""
                        UPDATE scenes 
                        SET enhanced_content = NULL 
                        WHERE draft_id = %s
                    """, (draft_id,))
                
                cleared_count = cursor.rowcount
                conn.commit()
            
            self.db_pool.putconn(conn)
            
            logger.info(f"Cleared {cleared_count} scene enhancements for reprocessing")
            
            # Re-run enhancement
            result = self.run(draft_id)
            result['reprocessed'] = True
            result['cleared_enhancements'] = cleared_count
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to reprocess enhancements for draft {draft_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'draft_id': draft_id
            }
"""
Stage 4A: Scene-by-Scene Analysis
Performs detailed analysis of individual scenes for plot, character, and thematic elements.
"""

import json
import logging
from typing import Dict, Any, List, Tuple
from models.request import BaseGenerationRequest
from ..prompt_template import DeconstructorPrompts
from utils.database_utils import utf8_database_connection, clean_text_for_database, ensure_utf8_json

logger = logging.getLogger(__name__)

class SceneBySceneAnalysisStage:
    """
    Stage 4A of the deconstruction pipeline.
    Analyzes each scene individually for literary elements and plot significance.
    """
    
    def __init__(self, db_pool, generation_engine):
        """
        Initialize the scene analysis stage.
        
        Args:
            db_pool: Database connection pool
            generation_engine: AI generation engine
        """
        self.db_pool = db_pool
        self.generation_engine = generation_engine
        self.prompt_template = DeconstructorPrompts()
    
    def run(self, draft_id: str, chaptering_mode: str = 'flexible', target_chapter_length: int = 2500) -> Dict[str, Any]:
        """
        Execute Stage 4A: Scene-by-scene analysis.
        
        Args:
            draft_id: UUID of the draft
            chaptering_mode: Chaptering approach ('flexible' or 'constrained')
            target_chapter_length: Target word count per chapter
            
        Returns:
            Stage execution results
        """
        logger.info(f"Starting Stage 4A scene analysis for draft {draft_id} (chaptering_mode: {chaptering_mode}, target_length: {target_chapter_length})")
        
        try:
            # Get all scenes for this draft
            scenes = self._get_draft_scenes(draft_id)
            
            if not scenes:
                logger.warning(f"No scenes found for draft {draft_id}")
                return {
                    'success': True,
                    'scenes_analyzed': 0,
                    'message': 'No scenes to analyze'
                }
            
            # Analyze each scene
            analyzed_scenes = 0
            failed_analyses = []
            
            for scene_id, scene_number, title, setting, characters, content in scenes:
                try:
                    analysis_data = self._analyze_scene(
                        scene_number, title, setting, characters, content
                    )
                    
                    if analysis_data:
                        self._update_scene_analysis(scene_id, analysis_data)
                        analyzed_scenes += 1
                        logger.debug(f"Analyzed scene {scene_number} for draft {draft_id}")
                    else:
                        failed_analyses.append(scene_number)
                        
                except Exception as e:
                    logger.error(f"Failed to analyze scene {scene_number}: {e}")
                    failed_analyses.append(scene_number)
            
            result = {
                'success': True,
                'total_scenes': len(scenes),
                'scenes_analyzed': analyzed_scenes,
                'failed_analyses': len(failed_analyses),
                'failed_scene_numbers': failed_analyses if failed_analyses else None,
                'chaptering_mode': chaptering_mode,
                'target_chapter_length': target_chapter_length
            }
            
            logger.info(f"Stage 4A completed for draft {draft_id}: {analyzed_scenes}/{len(scenes)} scenes analyzed")
            return result
            
        except Exception as e:
            logger.error(f"Stage 4A failed for draft {draft_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'draft_id': draft_id
            }
    
    def _get_draft_scenes(self, draft_id: str) -> List[Tuple]:
        """
        Retrieve all scenes for a draft from the database with UTF-8 safety.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            List of scene tuples
        """
        try:
            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, scene_number, title, setting, characters, original_content
                    FROM scenes 
                    WHERE draft_id = %s
                    ORDER BY scene_number
                """, (draft_id,))
                
                scenes = cursor.fetchall()
            
            logger.debug(f"Retrieved {len(scenes)} scenes for analysis in draft {draft_id} (UTF-8 safe)")
            return scenes
            
        except Exception as e:
            logger.error(f"Failed to retrieve scenes for draft {draft_id}: {e}")
            raise
    
    def _analyze_scene(self, scene_number: int, title: str, setting: str, 
                      characters: str, content: str) -> Dict[str, Any]:
        """
        Analyze a single scene using AI.
        
        Args:
            scene_number: Scene number
            title: Scene title
            setting: Scene setting
            characters: Characters JSON string
            content: Scene content
            
        Returns:
            Analysis data dictionary
        """
        try:
            # Parse characters if it's a JSON string
            try:
                characters_list = json.loads(characters) if characters else []
            except (json.JSONDecodeError, TypeError):
                characters_list = []
            
            # Prepare the analysis prompt
            prompt = self.prompt_template.get_scene_analysis_prompt().format(
                scene_title=title,
                scene_setting=setting,
                scene_characters=characters_list,
                scene_content=content
            )
            
            # Update the generation request
            self.generation_engine.request.prompt = prompt
            self.generation_engine.request.instruction = "Provide a comprehensive literary analysis of this scene."
            
            # Generate analysis
            response = self.generation_engine.generate(skip_quota=True)
            
            if not response.success:
                logger.error(f"AI generation failed for scene {scene_number}: {response.error_message}")
                return {}
            
            # Parse the JSON response
            try:
                analysis_data = json.loads(response.text.strip())
                
                # Validate analysis structure
                validated_analysis = self._validate_analysis_data(analysis_data)
                
                return validated_analysis
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse scene analysis JSON for scene {scene_number}: {e}")
                logger.error(f"Raw response: {response.text[:500]}...")
                
                # Return basic analysis structure
                return self._create_fallback_analysis(content)
                
        except Exception as e:
            logger.error(f"Error analyzing scene {scene_number}: {e}")
            return {}
    
    def _validate_analysis_data(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and structure the analysis data.
        
        Args:
            analysis_data: Raw analysis from AI
            
        Returns:
            Validated analysis dictionary
        """
        validated = {
            'plot_function': analysis_data.get('plot_function', ''),
            'character_development': analysis_data.get('character_development', {}),
            'conflicts': analysis_data.get('conflicts', []),
            'themes': analysis_data.get('themes', []),
            'foreshadowing': analysis_data.get('foreshadowing', []),
            'world_building': analysis_data.get('world_building', ''),
            'dialogue_analysis': analysis_data.get('dialogue_analysis', ''),
            'pacing_notes': analysis_data.get('pacing_notes', ''),
            'overall_significance': analysis_data.get('overall_significance', '')
        }
        
        # Ensure lists are actually lists
        for key in ['conflicts', 'themes', 'foreshadowing']:
            if not isinstance(validated[key], list):
                validated[key] = []
        
        # Ensure character_development is a dict
        if not isinstance(validated['character_development'], dict):
            validated['character_development'] = {}
        
        return validated
    
    def _create_fallback_analysis(self, content: str) -> Dict[str, Any]:
        """
        Create a basic analysis structure when AI parsing fails.
        
        Args:
            content: Scene content
            
        Returns:
            Basic analysis dictionary
        """
        return {
            'plot_function': 'Analysis failed - manual review required',
            'character_development': {},
            'conflicts': [],
            'themes': [],
            'foreshadowing': [],
            'world_building': f'Scene content length: {len(content)} characters',
            'dialogue_analysis': 'Analysis incomplete',
            'pacing_notes': 'Requires manual analysis',
            'overall_significance': 'Unable to determine automatically'
        }
    
    def _update_scene_analysis(self, scene_id: int, analysis_data: Dict[str, Any]) -> None:
        """
        Update the scene with analysis data using UTF-8 safety.
        
        Args:
            scene_id: Scene database ID
            analysis_data: Analysis results
        """
        try:
            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()
                
                # Ensure UTF-8 safe JSON encoding
                analysis_json = ensure_utf8_json(analysis_data)
                
                cursor.execute("""
                    UPDATE scenes 
                    SET analysis_json = %s
                    WHERE id = %s
                """, (analysis_json, scene_id))
                
                conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to update scene analysis for scene {scene_id}: {e}")
            raise
    
    def get_analysis_statistics(self, draft_id: str) -> Dict[str, Any]:
        """
        Get statistics about scene analyses.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Analysis statistics
        """
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                # Get basic counts
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_scenes,
                        COUNT(CASE WHEN analysis_json IS NOT NULL THEN 1 END) as analyzed_scenes
                    FROM scenes 
                    WHERE draft_id = %s
                """, (draft_id,))
                
                result = cursor.fetchone()
                total_scenes = result[0] if result else 0
                analyzed_scenes = result[1] if result else 0
                
                # Get theme and conflict statistics
                cursor.execute("""
                    SELECT analysis_json 
                    FROM scenes 
                    WHERE draft_id = %s AND analysis_json IS NOT NULL
                """, (draft_id,))
                
                analyses = cursor.fetchall()
                
                all_themes = []
                all_conflicts = []
                character_mentions = {}
                
                for analysis_row in analyses:
                    try:
                        analysis = json.loads(analysis_row[0])
                        
                        # Collect themes
                        themes = analysis.get('themes', [])
                        all_themes.extend(themes)
                        
                        # Collect conflicts
                        conflicts = analysis.get('conflicts', [])
                        all_conflicts.extend(conflicts)
                        
                        # Count character mentions
                        char_dev = analysis.get('character_development', {})
                        for char_name in char_dev.keys():
                            character_mentions[char_name] = character_mentions.get(char_name, 0) + 1
                            
                    except (json.JSONDecodeError, TypeError):
                        continue
                
                # Count frequencies
                theme_counts = {}
                for theme in all_themes:
                    theme_counts[theme] = theme_counts.get(theme, 0) + 1
                
                conflict_counts = {}
                for conflict in all_conflicts:
                    conflict_counts[conflict] = conflict_counts.get(conflict, 0) + 1
                
                stats = {
                    'total_scenes': total_scenes,
                    'analyzed_scenes': analyzed_scenes,
                    'unanalyzed_scenes': total_scenes - analyzed_scenes,
                    'analysis_percentage': (analyzed_scenes / total_scenes * 100) if total_scenes > 0 else 0,
                    'unique_themes': len(theme_counts),
                    'most_common_themes': sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:10],
                    'unique_conflicts': len(conflict_counts),
                    'most_common_conflicts': sorted(conflict_counts.items(), key=lambda x: x[1], reverse=True)[:10],
                    'characters_with_development': len(character_mentions),
                    'most_developed_characters': sorted(character_mentions.items(), key=lambda x: x[1], reverse=True)[:10]
                }
            
            self.db_pool.putconn(conn)
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get analysis statistics for draft {draft_id}: {e}")
            if 'conn' in locals():
                self.db_pool.putconn(conn)
            return {'error': str(e)}
    
    def reanalyze_scenes(self, draft_id: str, scene_numbers: List[int] = None) -> Dict[str, Any]:
        """
        Re-analyze specific scenes or all scenes.
        
        Args:
            draft_id: UUID of the draft
            scene_numbers: Optional list of specific scene numbers to re-analyze
            
        Returns:
            Re-analysis results
        """
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                # Clear existing analyses for specified scenes
                if scene_numbers:
                    placeholders = ','.join(['%s'] * len(scene_numbers))
                    cursor.execute(f"""
                        UPDATE scenes 
                        SET analysis_json = NULL 
                        WHERE draft_id = %s AND scene_number IN ({placeholders})
                    """, [draft_id] + scene_numbers)
                else:
                    cursor.execute("""
                        UPDATE scenes 
                        SET analysis_json = NULL 
                        WHERE draft_id = %s
                    """, (draft_id,))
                
                cleared_count = cursor.rowcount
                conn.commit()
            
            self.db_pool.putconn(conn)
            
            logger.info(f"Cleared {cleared_count} scene analyses for re-analysis")
            
            # Re-run analysis
            result = self.run(draft_id)
            result['reanalyzed'] = True
            result['cleared_analyses'] = cleared_count
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to reanalyze scenes for draft {draft_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'draft_id': draft_id
            }
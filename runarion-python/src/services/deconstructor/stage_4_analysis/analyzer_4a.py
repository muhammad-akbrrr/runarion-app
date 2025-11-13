"""
Stage 4A: Scene-by-Scene Analysis
Performs detailed analysis of individual scenes for plot, character, and thematic elements.
"""

import json
import logging
from typing import Dict, Any, List, Tuple
from ..prompt_template import DeconstructorPrompts
from utils.database_utils import ensure_utf8_json
from utils.json_response_parser import parse_scene_analysis_response
from ..base_stage import BasePipelineStage, PipelineStageResult, PipelineStageContext

logger = logging.getLogger(__name__)

class SceneBySceneAnalysisStage(BasePipelineStage):
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
        super().__init__(db_pool, "SceneBySceneAnalysisStage", generation_engine)
        self.prompt_template = DeconstructorPrompts()
    
    def _execute_stage(self, context: PipelineStageContext) -> PipelineStageResult:
        """
        Execute Stage 4A: Scene-by-scene analysis.
        
        Args:
            context: Stage execution context containing draft_id
            
        Returns:
            PipelineStageResult with stage execution results
        """
        draft_id = context.draft_id
        
        # Get chaptering parameters from draft metadata
        draft_metadata = self.get_draft_metadata(draft_id)
        chaptering_mode = draft_metadata.get('chaptering_mode', 'flexible')
        target_length = draft_metadata.get('target_chapter_length', 2500)
        
        try:
            # Get all scenes for this draft
            scenes = self._get_draft_scenes(context)
            
            if not scenes:
                return PipelineStageResult.success_result(
                    self.stage_name,
                    total_scenes=0,
                    scenes_analyzed=0,
                    failed_analyses=0,
                    message='No scenes to analyze'
                )
            
            analyzed_scenes = 0
            failed_analyses = []
            
            for scene in scenes:
                scene_id, scene_number, title, setting, characters, content = scene
                
                try:
                    # Analyze this scene
                    analysis_result = self._analyze_single_scene(scene_id, scene_number, title, setting, characters, content)
                    
                    if analysis_result:
                        # Update scene with analysis
                        self._update_scene_analysis(context, scene_id, analysis_result)
                        analyzed_scenes += 1
                        self.logger.debug(f"Analyzed scene {scene_number} successfully")
                    else:
                        self.logger.warning(f"Scene {scene_number} analysis returned empty result")
                        failed_analyses.append(scene_number)
                        
                except Exception as e:
                    self.logger.error(f"Failed to analyze scene {scene_number}: {e}")
                    failed_analyses.append(scene_number)
            
            # Update draft graph metadata after successful analysis
            if analyzed_scenes > 0:
                self._update_draft_graph_metadata(context)
            
            return PipelineStageResult.success_result(
                self.stage_name,
                total_scenes=len(scenes),
                scenes_analyzed=analyzed_scenes,
                failed_analyses=len(failed_analyses),
                failed_scene_numbers=failed_analyses if failed_analyses else None,
                chaptering_mode=chaptering_mode,
                target_chapter_length=target_length
            )
            
        except Exception as e:
            return PipelineStageResult.error_result(
                self.stage_name,
                error=str(e),
                draft_id=draft_id
            )
    
    def run(self, draft_id: str, chaptering_mode: str = 'flexible', target_chapter_length: int = 2500) -> Dict[str, Any]:
        """
        Execute Stage 4A with legacy interface (backward compatibility).
        
        Args:
            draft_id: UUID of the draft
            chaptering_mode: Chaptering approach (backward compatibility)
            target_chapter_length: Target word count (backward compatibility)
            
        Returns:
            Stage execution results
        """
        return super().run(draft_id)
    
    def _get_draft_scenes(self, context: PipelineStageContext) -> List[Tuple]:
        """
        Retrieve all scenes for a draft from the database with UTF-8 safety.
        
        Args:
            context: Stage execution context
            
        Returns:
            List of scene tuples
        """
        draft_id = context.draft_id
        
        try:
            db_connection = self.get_database_connection(context)
            with db_connection as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, scene_number, title, setting, characters, original_content
                    FROM scenes 
                    WHERE draft_id = %s
                    ORDER BY scene_number
                """, (draft_id,))
                
                scenes = cursor.fetchall()
            
            self.logger.debug(f"Retrieved {len(scenes)} scenes for analysis in draft {draft_id} (UTF-8 safe)")
            return scenes
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve scenes for draft {draft_id}: {e}")
            raise
    
    def _analyze_single_scene(self, scene_id: int, scene_number: int, title: str, setting: str,
                             characters: str, content: str) -> Dict[str, Any]:
        """
        Analyze a single scene using AI.

        Args:
            scene_id: Scene ID
            scene_number: Scene number
            title: Scene title
            setting: Scene setting
            characters: Characters JSON string
            content: Scene content

        Returns:
            Analysis data dictionary
        """
        try:
            # Validate content length before processing
            # Reduced from 200 to 150 chars to align with Stage 3 hydration threshold
            if not content or len(content.strip()) < 150:
                self.logger.warning(
                    f"Scene {scene_number} has suspiciously short content ({len(content) if content else 0} chars) - "
                    f"may be truncated. Analysis quality may be affected."
                )
                # Still attempt analysis, but log the issue
            elif content.endswith('...') and len(content) < 500:
                self.logger.warning(
                    f"Scene {scene_number} appears truncated (ends with '...', length {len(content)} chars). "
                    f"This indicates Stage 3 hydration failure."
                )

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
            
            # Set appropriate token limit for scene analysis (focused analysis, not full content)
            self.generation_engine.request.generation_config.max_output_tokens = 2000
            
            # Generate analysis
            response = self.generation_engine.generate(skip_quota=True)

            # Check if response was truncated due to token limit
            if response.success and hasattr(response, 'metadata') and response.metadata.finish_reason == 'length':
                current_limit = self.generation_engine.request.generation_config.max_output_tokens
                new_limit = int(current_limit * 1.5)  # Increase by 50%
                self.logger.warning(
                    f"Stage 4A scene {scene_number} analysis truncated (finish_reason='length'). "
                    f"Tokens: {response.metadata.output_tokens}. "
                    f"Increasing max_output_tokens from {current_limit} to {new_limit} and retrying..."
                )
                self.generation_engine.request.generation_config.max_output_tokens = new_limit
                response = self.generation_engine.generate(skip_quota=True)

            if not response.success:
                self.logger.error(f"AI generation failed for scene {scene_number}: {response.error_message}")
                return {}
            
            # Parse the JSON response using unified parser
            try:
                validated_analysis = parse_scene_analysis_response(response)
                return validated_analysis
                
            except Exception as e:
                self.logger.error(f"Failed to parse scene analysis JSON for scene {scene_number}: {e}")
                if hasattr(response, 'text'):
                    self.logger.error(f"Raw response: {str(response.text)[:500]}...")
                
                # Return basic analysis structure
                return self._create_fallback_analysis(content)
                
        except Exception as e:
            self.logger.error(f"Error analyzing scene {scene_number}: {e}")
            return {}
    
    
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
    
    def _update_scene_analysis(self, context: PipelineStageContext, scene_id: int, analysis_data: Dict[str, Any]) -> None:
        """
        Update the scene with analysis data and graph flags using UTF-8 safety.
        
        Args:
            context: Stage execution context
            scene_id: Scene database ID
            analysis_data: Analysis results
        """
        try:
            db_connection = self.get_database_connection(context)
            with db_connection as conn:
                cursor = conn.cursor()
                
                # Ensure UTF-8 safe JSON encoding
                analysis_json = ensure_utf8_json(analysis_data)
                
                cursor.execute("""
                    UPDATE scenes 
                    SET analysis_json = %s,
                        graph_analyzed = true,
                        graph_last_updated = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (analysis_json, scene_id))
                
                conn.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to update scene analysis for scene {scene_id}: {e}")
            raise
    
    def _update_draft_graph_metadata(self, context: PipelineStageContext) -> None:
        """
        Update draft-level graph metadata flags and prepare for Stage 4B.
        
        Args:
            context: Stage execution context
        """
        try:
            draft_id = context.draft_id
            metadata_updates = {
                'graph_initialized': True,
                'stage_4a_completed': True,
                'ready_for_graph_analysis': True
            }
            self.update_draft_metadata(draft_id, metadata_updates)
            
            # Also update the graph timestamp in the drafts table
            db_connection = self.get_database_connection(context)
            with db_connection as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE drafts 
                    SET graph_last_updated = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (draft_id,))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to update draft graph metadata: {e}")
            # Don't raise here as it's not critical to stage success
    
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
            self.logger.error(f"Failed to get analysis statistics for draft {draft_id}: {e}")
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
            self.logger.error(f"Failed to reanalyze scenes for draft {draft_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'draft_id': draft_id
            }

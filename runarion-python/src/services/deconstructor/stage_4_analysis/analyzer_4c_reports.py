"""
Stage 4C: Comprehensive Reporting
Generates detailed analysis reports for major story elements.
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional
from collections import Counter
from ulid import ULID
from ..prompt_template import DeconstructorPrompts
from utils.database_utils import clean_text_for_database, ensure_utf8_json
from utils.llm_retry import call_llm_with_retry
from ..base_stage import BasePipelineStage, PipelineStageResult, PipelineStageContext
from services.graph_database_service import GraphDatabaseService, GraphDatabaseNotAvailableError

logger = logging.getLogger(__name__)

class ComprehensiveReportingStage(BasePipelineStage):
    """
    Stage 4C: Generates comprehensive analysis reports.
    """
    
    def __init__(self, db_pool, generation_engine):
        """
        Initialize the comprehensive reporting stage.
        
        Args:
            db_pool: Database connection pool
            generation_engine: AI generation engine
        """
        super().__init__(db_pool, "ComprehensiveReportingStage", generation_engine)
        self.prompt_template = DeconstructorPrompts()
        self.age_enabled = os.getenv('AGE_ENABLED', 'true').lower() == 'true'
        
        # Initialize graph service if AGE is enabled
        if self.age_enabled:
            try:
                self.graph_service = GraphDatabaseService(db_pool)
            except GraphDatabaseNotAvailableError as e:
                logger.warning(f"AGE not available, disabling graph features: {e}")
                self.graph_service = None
                self.age_enabled = False
        else:
            self.graph_service = None
    
    def _execute_stage(self, context: PipelineStageContext) -> PipelineStageResult:
        """
        Execute Stage 4C: Comprehensive reporting.
        
        Args:
            context: Stage execution context containing draft_id
            
        Returns:
            PipelineStageResult with stage execution results
        """
        draft_id = context.draft_id
        
        # Get chaptering parameters from draft metadata
        draft_metadata = self.get_draft_metadata(draft_id)
        chaptering_mode = draft_metadata.get('chaptering_mode', 'flexible')
        target_chapter_length = draft_metadata.get('target_chapter_length', 2500)
        
        self.logger.info(f"Starting Stage 4C comprehensive reporting for draft {draft_id} (chaptering_mode: {chaptering_mode}, target_length: {target_chapter_length})")
        
        try:
            scenes_data = self._get_scenes_with_analysis(context)
            
            if not scenes_data:
                return PipelineStageResult.success_result(
                    self.stage_name,
                    reports_generated=0,
                    message='No analyzed scenes to report on'
                )
            
            # Get graph data if available
            graph_data = self._get_graph_data(context)
            
            # Identify major elements using both scene and graph data
            major_characters = self._identify_major_characters(scenes_data, graph_data)
            major_themes = self._identify_major_themes(scenes_data)
            major_settings = self._identify_major_settings(scenes_data)
            plot_threads = self._identify_plot_threads(scenes_data)
            
            reports_generated = 0
            
            # Generate character reports with graph relationships
            for character_name in major_characters:
                try:
                    character_data = self._extract_character_data(character_name, scenes_data, graph_data)
                    report = self._generate_character_report(character_name, character_data)
                    
                    if report:
                        self._store_analysis_report(context, 'CHARACTER_ARC', character_name, report)
                        reports_generated += 1
                        
                except Exception as e:
                    self.logger.error(f"Failed to generate character report for {character_name}: {e}")
            
            # Generate theme reports
            for theme in major_themes[:5]:  # Limit to top 5 themes
                try:
                    theme_data = self._extract_theme_data(theme, scenes_data)
                    report = self._generate_theme_report(theme, theme_data)
                    
                    if report:
                        self._store_analysis_report(context, 'THEME_ANALYSIS', theme, report)
                        reports_generated += 1
                        
                except Exception as e:
                    self.logger.error(f"Failed to generate theme report for {theme}: {e}")
            
            # Generate setting reports
            for setting in major_settings[:5]:  # Limit to top 5 settings
                try:
                    setting_data = self._extract_setting_data(setting, scenes_data)
                    report = self._generate_setting_report(setting, setting_data)
                    
                    if report:
                        self._store_analysis_report(context, 'SETTING_ANALYSIS', setting, report)
                        reports_generated += 1
                        
                except Exception as e:
                    self.logger.error(f"Failed to generate setting report for {setting}: {e}")
            
            # Generate plot thread reports
            for i, plot_thread in enumerate(plot_threads[:3]):  # Limit to top 3 plot threads
                try:
                    report = self._generate_plot_thread_report(plot_thread, scenes_data)
                    
                    if report:
                        thread_name = f"plot_thread_{i+1}"
                        self._store_analysis_report(context, 'PLOT_THREAD', thread_name, report)
                        reports_generated += 1
                        
                except Exception as e:
                    self.logger.error(f"Failed to generate plot thread report {i+1}: {e}")
            
            # Generate relationship analysis using graph data
            if graph_data and graph_data.get('relationships'):
                try:
                    relationship_report = self._generate_relationship_report(graph_data, scenes_data)
                    if relationship_report:
                        self._store_analysis_report(context, 'RELATIONSHIP_ANALYSIS', 'character_relationships', relationship_report)
                        reports_generated += 1
                        
                except Exception as e:
                    self.logger.error(f"Failed to generate relationship report: {e}")
            
            # Generate comprehensive narrative overview
            try:
                narrative_report = self._generate_narrative_report(
                    scenes_data, major_characters, major_themes, 
                    major_settings, plot_threads, graph_data
                )
                if narrative_report:
                    self._store_analysis_report(context, 'NARRATIVE_OVERVIEW', 'story_overview', narrative_report)
                    reports_generated += 1
                    
            except Exception as e:
                self.logger.error(f"Failed to generate narrative report: {e}")
            
            self.logger.info(f"Stage 4C completed for draft {draft_id}: {reports_generated} reports generated")
            
            return PipelineStageResult.success_result(
                self.stage_name,
                scenes_analyzed=len(scenes_data),
                major_characters=len(major_characters),
                major_themes=len(major_themes),
                major_settings=len(major_settings),
                plot_threads=len(plot_threads),
                graph_data_available=bool(graph_data),
                reports_generated=reports_generated,
                chaptering_mode=chaptering_mode,
                target_chapter_length=target_chapter_length
            )
            
        except Exception as e:
            return PipelineStageResult.error_result(
                self.stage_name,
                error=str(e),
                draft_id=draft_id
            )
    
    def run(self, draft_id: str, chaptering_mode: str = 'flexible', target_chapter_length: int = 2500) -> Dict[str, Any]:
        """
        Execute Stage 4C with legacy interface (backward compatibility).
        
        Args:
            draft_id: UUID of the draft
            chaptering_mode: Chaptering approach (backward compatibility)
            target_chapter_length: Target word count (backward compatibility)
            
        Returns:
            Stage execution results
        """
        return super().run(draft_id)
    
    def _update_chaptering_metadata(self, draft_id: str, chaptering_mode: str, target_chapter_length: int) -> None:
        """
        Update draft metadata with chaptering parameters for downstream stages.
        
        Args:
            draft_id: UUID of the draft
            chaptering_mode: Chaptering approach
            target_chapter_length: Target word count per chapter
        """
        try:
            # Use base class method for standardized metadata update
            metadata_updates = {
                'chaptering_mode': chaptering_mode,
                'target_chapter_length': target_chapter_length,
                'stage_4c_completed': True
            }
            self.update_draft_metadata(draft_id, metadata_updates)
            self.logger.debug(f"Updated chaptering metadata for draft {draft_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to update chaptering metadata for draft {draft_id}: {e}")
            raise

    def _get_scenes_with_analysis(self, context: PipelineStageContext) -> List[Dict[str, Any]]:
        """Retrieve scenes with their analysis data using UTF-8 safety."""
        draft_id = context.draft_id
        
        try:
            db_connection = self.get_database_connection(context)
            with db_connection as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, scene_number, title, setting, characters, 
                           original_content, analysis_json
                    FROM scenes 
                    WHERE draft_id = %s AND analysis_json IS NOT NULL
                    ORDER BY scene_number
                """, (draft_id,))
                
                scenes = cursor.fetchall()
            
            scenes_data = []
            for scene in scenes:
                scene_id, scene_number, title, setting, characters, content, analysis_json = scene
                
                try:
                    analysis = json.loads(analysis_json) if analysis_json else {}
                    characters_list = json.loads(characters) if characters else []
                except (json.JSONDecodeError, TypeError):
                    analysis = {}
                    characters_list = []
                
                scenes_data.append({
                    'id': scene_id,
                    'scene_number': scene_number,
                    'title': title,
                    'setting': setting,
                    'characters': characters_list,
                    'content': content,
                    'analysis': analysis
                })
            
            self.logger.debug(f"Retrieved {len(scenes_data)} scenes with analysis for draft {draft_id} (UTF-8 safe)")
            return scenes_data
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve scenes with analysis: {e}")
            return []
    
    def _get_graph_data(self, context: PipelineStageContext) -> Optional[Dict[str, Any]]:
        """Retrieve graph data from AGE database using GraphDatabaseService."""
        draft_id = context.draft_id
        
        if not self.age_enabled or not self.graph_service:
            self.logger.debug("AGE disabled or graph service not available")
            return None
            
        try:
            # Use GraphDatabaseService methods for all graph operations
            characters = self.graph_service.get_character_vertices(draft_id)
            locations = self.graph_service.get_location_vertices(draft_id)
            relationships = self.graph_service.get_draft_relationships(draft_id)
            statistics = self.graph_service.get_graph_statistics(draft_id)
            
            # Validate that we have meaningful data
            if not characters and not locations and not relationships:
                self.logger.warning(f"No graph data found for draft {draft_id}")
                return None
            
            graph_data = {
                'characters': characters or [],
                'locations': locations or [],
                'relationships': relationships or [],
                'entities_count': statistics.get('total_entities', 0),
                'relationships_count': statistics.get('total_relationships', 0),
                'entity_breakdown': statistics.get('entity_breakdown', {}),
                'relationship_types': statistics.get('relationship_types', [])
            }
            
            self.logger.debug(f"Retrieved graph data for draft {draft_id}: {graph_data['entities_count']} entities, {graph_data['relationships_count']} relationships")
            return graph_data
                
        except GraphDatabaseNotAvailableError as e:
            self.logger.warning(f"AGE not available for graph data retrieval: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to retrieve graph data: {e}")
            return None
    
    def _identify_major_characters(self, scenes_data: List[Dict[str, Any]], 
                                  graph_data: Optional[Dict[str, Any]] = None) -> List[str]:
        """Identify major characters based on appearances and graph centrality."""
        character_counter = Counter()
        
        # Count scene appearances
        for scene in scenes_data:
            for character in scene.get('characters', []):
                character_counter[character] += 1
            
            # Count mentions in analysis
            analysis = scene.get('analysis', {})
            char_dev = analysis.get('character_development', {})
            for character in char_dev.keys():
                character_counter[character] += 1
        
        # Boost characters with graph relationships (centrality)
        if graph_data and graph_data.get('relationships'):
            relationship_counter = Counter()
            for rel in graph_data['relationships']:
                relationship_counter[rel['source']] += 1
                relationship_counter[rel['target']] += 1
            
            # Add relationship weight to character importance
            for char, rel_count in relationship_counter.items():
                character_counter[char] += rel_count * 0.5  # Weight relationships
        
        # Dynamic threshold based on story length
        total_scenes = len(scenes_data)
        min_appearances = max(2, total_scenes // 10)  # At least 10% of scenes
        
        return [char for char, count in character_counter.most_common(15) if count >= min_appearances]
    
    def _identify_major_themes(self, scenes_data: List[Dict[str, Any]]) -> List[str]:
        """Identify major themes based on frequency."""
        theme_counter = Counter()
        
        for scene in scenes_data:
            analysis = scene.get('analysis', {})
            themes = analysis.get('themes', [])
            
            for theme in themes:
                if isinstance(theme, str) and len(theme.strip()) > 0:
                    theme_counter[theme.strip()] += 1
        
        return [theme for theme, count in theme_counter.most_common(10) if count >= 2]
    
    def _identify_major_settings(self, scenes_data: List[Dict[str, Any]]) -> List[str]:
        """Identify major settings based on frequency and importance."""
        setting_counter = Counter()
        
        for scene in scenes_data:
            setting = scene.get('setting', '').strip()
            if setting and setting.lower() not in ['unknown location', 'unknown', '']:
                setting_counter[setting] += 1
        
        # Return settings appearing in multiple scenes
        return [setting for setting, count in setting_counter.most_common(10) if count >= 2]
    
    def _identify_plot_threads(self, scenes_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify major plot threads based on conflicts and themes."""
        plot_threads = []
        
        # Group conflicts by type
        conflict_groups = {}
        for scene in scenes_data:
            analysis = scene.get('analysis', {})
            conflicts = analysis.get('conflicts', [])
            
            for conflict in conflicts:
                if isinstance(conflict, str) and len(conflict.strip()) > 10:
                    # Simple categorization
                    conflict_key = conflict[:30].strip()  # Use first 30 chars as key
                    if conflict_key not in conflict_groups:
                        conflict_groups[conflict_key] = {
                            'description': conflict,
                            'scenes': [],
                            'frequency': 0
                        }
                    conflict_groups[conflict_key]['scenes'].append(scene['scene_number'])
                    conflict_groups[conflict_key]['frequency'] += 1
        
        # Convert to plot threads
        for conflict_key, data in conflict_groups.items():
            if data['frequency'] >= 2:  # Appears in multiple scenes
                plot_threads.append({
                    'thread_key': conflict_key,
                    'description': data['description'],
                    'scenes': data['scenes'],
                    'frequency': data['frequency'],
                    'thread_type': 'conflict'
                })
        
        # Sort by frequency and return top threads
        plot_threads.sort(key=lambda x: x['frequency'], reverse=True)
        return plot_threads[:5]
    
    def _extract_character_data(self, character_name: str, scenes_data: List[Dict[str, Any]], 
                               graph_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Extract all data related to a specific character."""
        character_scenes = []
        character_development = []
        
        for scene in scenes_data:
            if character_name in scene.get('characters', []):
                character_scenes.append({
                    'scene_number': scene['scene_number'],
                    'title': scene['title'],
                    'content_excerpt': scene['content'][:300] + '...' if len(scene['content']) > 300 else scene['content']
                })
            
            analysis = scene.get('analysis', {})
            char_dev = analysis.get('character_development', {})
            if character_name in char_dev:
                character_development.append({
                    'scene_number': scene['scene_number'],
                    'development': char_dev[character_name]
                })
        
        # Add graph relationship data
        relationships = []
        if graph_data and graph_data.get('relationships'):
            for rel in graph_data['relationships']:
                if rel['source'] == character_name or rel['target'] == character_name:
                    relationships.append({
                        'other_character': rel['target'] if rel['source'] == character_name else rel['source'],
                        'relationship_type': rel['relationship_type'],
                        'properties': rel.get('properties', {})
                    })
        
        return {
            'character_name': character_name,
            'scene_appearances': character_scenes,
            'character_development': character_development,
            'relationships': relationships,
            'total_scenes': len(character_scenes),
            'relationship_count': len(relationships)
        }
    
    def _generate_character_report(self, character_name: str, character_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a character analysis report using AI."""
        try:
            scenes_info = []
            for scene in character_data['scene_appearances']:
                scenes_info.append(f"Scene {scene['scene_number']}: {scene['title']} - {scene['content_excerpt']}")
            
            relationships_info = []
            for dev in character_data['character_development']:
                relationships_info.append(f"Scene {dev['scene_number']}: {dev['development']}")
            
            prompt = self.prompt_template.get_character_report_prompt().format(
                character_name=character_name,
                character_scenes='\n'.join(scenes_info),
                character_relationships='\n'.join(relationships_info)
            )
            
            self.generation_engine.request.prompt = prompt
            self.generation_engine.request.instruction = f"Generate a comprehensive character analysis report for {character_name}."

            # Set provider-aware token limit for report JSON
            self.generation_engine.request.generation_config.max_output_tokens = self._get_output_budget("json_analytical")

            # Enable JSON mode for Gemini structured output
            self.generation_engine.request.generation_config.response_mime_type = "application/json"

            try:
                # Generate report (with transient-error retry)
                response = call_llm_with_retry(
                    lambda: self.generation_engine.generate(skip_quota=True)
                )

                # Check if response was truncated due to token limit
                if response.success and hasattr(response, 'metadata') and response.metadata.finish_reason == 'length':
                    current_limit = self.generation_engine.request.generation_config.max_output_tokens
                    new_limit = int(current_limit * 1.5)  # Increase by 50%
                    self.logger.warning(
                        f"Stage 4C character report for '{character_name}' truncated (finish_reason='length'). "
                        f"Tokens: {response.metadata.output_tokens}. "
                        f"Increasing max_output_tokens from {current_limit} to {new_limit} and retrying..."
                    )
                    self.generation_engine.request.generation_config.max_output_tokens = new_limit
                    response = call_llm_with_retry(
                        lambda: self.generation_engine.generate(skip_quota=True)
                    )
            finally:
                # Reset to avoid leaking into subsequent plain-text stages
                self.generation_engine.request.generation_config.response_mime_type = None

            if not response.success:
                return self._create_fallback_character_report(character_name, character_data)
            
            try:
                # Use the robust JSON parser that handles markdown code blocks
                from utils.json_response_parser import JSONResponseParser
                parsed_data, _ = JSONResponseParser.parse_response(response, "dict", {})
                return parsed_data
            except Exception as parse_error:
                self.logger.warning(f"Could not parse character report response: {parse_error}")
                return self._create_fallback_character_report(character_name, character_data)
                
        except Exception as e:
            self.logger.error(f"Error generating character report for {character_name}: {e}")
            return None
    
    def _create_fallback_theme_report(self, theme: str, theme_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a basic theme report when AI generation fails."""
        return {
            'theme_name': theme,
            'significance': f'Theme appears in {theme_data["frequency"]} scenes',
            'thematic_analysis': 'Requires manual analysis',
            'symbolic_meaning': 'To be determined',
            'narrative_function': f'Recurring theme with {theme_data["frequency"]} appearances',
            'analysis_status': 'incomplete'
        }
    
    def _create_fallback_setting_report(self, setting: str, setting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a basic setting report when AI generation fails."""
        return {
            'setting_name': setting,
            'atmosphere': 'To be analyzed',
            'significance': f'Setting used in {setting_data["frequency"]} scenes',
            'characters_present': setting_data['characters_present'],
            'narrative_function': f'Location with {setting_data["frequency"]} scene appearances',
            'analysis_status': 'incomplete'
        }
    
    def _create_fallback_plot_thread_report(self, plot_thread: Dict[str, Any]) -> Dict[str, Any]:
        """Create a basic plot thread report when AI generation fails."""
        return {
            'plot_thread': plot_thread['description'][:100],
            'thread_type': plot_thread.get('thread_type', 'unknown'),
            'frequency': plot_thread['frequency'],
            'affected_scenes': plot_thread['scenes'],
            'resolution_status': 'To be analyzed',
            'narrative_importance': f'Thread appears in {plot_thread["frequency"]} scenes',
            'analysis_status': 'incomplete',
            'thread_metadata': plot_thread
        }
    
    def _create_fallback_character_report(self, character_name: str, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a basic character report when AI generation fails."""
        return {
            'character_name': character_name,
            'character_arc': f'{character_name} appears in {character_data["total_scenes"]} scenes.',
            'personality_profile': {
                'core_traits': ['requires_analysis'],
                'strengths': ['to_be_determined'],
                'weaknesses': ['to_be_determined']
            },
            'narrative_role': f'Character with {character_data["total_scenes"]} scene appearances',
            'significance_rating': min(10, character_data["total_scenes"]),
            'relationship_count': character_data.get('relationship_count', 0),
            'analysis_status': 'incomplete'
        }
    
    def _extract_theme_data(self, theme: str, scenes_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract all data related to a specific theme."""
        theme_scenes = []
        
        for scene in scenes_data:
            analysis = scene.get('analysis', {})
            themes = analysis.get('themes', [])
            
            if theme in themes:
                theme_scenes.append({
                    'scene_number': scene['scene_number'],
                    'title': scene['title'],
                    'setting': scene['setting'],
                    'theme_context': analysis.get('world_building', '')[:200]
                })
        
        return {
            'theme_name': theme,
            'appearances': theme_scenes,
            'frequency': len(theme_scenes)
        }
    
    def _extract_setting_data(self, setting: str, scenes_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract all data related to a specific setting."""
        setting_scenes = []
        characters_in_setting = set()
        
        for scene in scenes_data:
            if scene.get('setting') == setting:
                setting_scenes.append({
                    'scene_number': scene['scene_number'],
                    'title': scene['title'],
                    'characters': scene.get('characters', []),
                    'summary': scene.get('summary', '')[:200]
                })
                characters_in_setting.update(scene.get('characters', []))
        
        return {
            'setting_name': setting,
            'scenes': setting_scenes,
            'characters_present': list(characters_in_setting),
            'frequency': len(setting_scenes)
        }
    
    def _generate_theme_report(self, theme: str, theme_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a theme analysis report using AI."""
        try:
            scenes_info = []
            for scene in theme_data['appearances']:
                scenes_info.append(f"Scene {scene['scene_number']}: {scene['title']} - {scene['theme_context']}")
            
            prompt = self.prompt_template.get_theme_analysis_prompt().format(
                theme_name=theme,
                theme_scenes='\n'.join(scenes_info),
                frequency=theme_data['frequency']
            )
            
            self.generation_engine.request.prompt = prompt
            self.generation_engine.request.instruction = f"Generate a comprehensive theme analysis report for {theme}."

            # Set provider-aware token limit for report JSON
            self.generation_engine.request.generation_config.max_output_tokens = self._get_output_budget("json_analytical")

            # Enable JSON mode for Gemini structured output
            self.generation_engine.request.generation_config.response_mime_type = "application/json"

            try:
                # Generate report (with transient-error retry)
                response = call_llm_with_retry(
                    lambda: self.generation_engine.generate(skip_quota=True)
                )

                # Check if response was truncated due to token limit
                if response.success and hasattr(response, 'metadata') and response.metadata.finish_reason == 'length':
                    current_limit = self.generation_engine.request.generation_config.max_output_tokens
                    new_limit = int(current_limit * 1.5)  # Increase by 50%
                    self.logger.warning(
                        f"Stage 4C theme report for '{theme}' truncated (finish_reason='length'). "
                        f"Tokens: {response.metadata.output_tokens}. "
                        f"Increasing max_output_tokens from {current_limit} to {new_limit} and retrying..."
                    )
                    self.generation_engine.request.generation_config.max_output_tokens = new_limit
                    response = call_llm_with_retry(
                        lambda: self.generation_engine.generate(skip_quota=True)
                    )
            finally:
                # Reset to avoid leaking into subsequent plain-text stages
                self.generation_engine.request.generation_config.response_mime_type = None

            if not response.success:
                return self._create_fallback_theme_report(theme, theme_data)
            
            try:
                # Use the robust JSON parser that handles markdown code blocks
                from utils.json_response_parser import JSONResponseParser
                parsed_data, _ = JSONResponseParser.parse_response(response, "dict", {})
                return parsed_data
            except Exception as parse_error:
                self.logger.warning(f"Could not parse theme report response: {parse_error}")
                return self._create_fallback_theme_report(theme, theme_data)
                
        except Exception as e:
            self.logger.error(f"Error generating theme report for {theme}: {e}")
            return None
    
    def _generate_setting_report(self, setting: str, setting_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a setting analysis report using AI."""
        try:
            scenes_info = []
            for scene in setting_data['scenes']:
                characters_str = ', '.join(scene['characters']) if scene['characters'] else 'No characters'
                scenes_info.append(f"Scene {scene['scene_number']}: {scene['title']} - Characters: {characters_str}")
            
            prompt = self.prompt_template.get_setting_analysis_prompt().format(
                setting_name=setting,
                setting_scenes='\n'.join(scenes_info),
                characters_present=', '.join(setting_data['characters_present'])
            )
            
            self.generation_engine.request.prompt = prompt
            self.generation_engine.request.instruction = f"Generate a comprehensive setting analysis report for {setting}."

            # Set provider-aware token limit for report JSON
            self.generation_engine.request.generation_config.max_output_tokens = self._get_output_budget("json_analytical")

            # Enable JSON mode for Gemini structured output
            self.generation_engine.request.generation_config.response_mime_type = "application/json"

            try:
                # Generate report (with transient-error retry)
                response = call_llm_with_retry(
                    lambda: self.generation_engine.generate(skip_quota=True)
                )

                # Check if response was truncated due to token limit
                if response.success and hasattr(response, 'metadata') and response.metadata.finish_reason == 'length':
                    current_limit = self.generation_engine.request.generation_config.max_output_tokens
                    new_limit = int(current_limit * 1.5)  # Increase by 50%
                    self.logger.warning(
                        f"Stage 4C setting report for '{setting}' truncated (finish_reason='length'). "
                        f"Tokens: {response.metadata.output_tokens}. "
                        f"Increasing max_output_tokens from {current_limit} to {new_limit} and retrying..."
                    )
                    self.generation_engine.request.generation_config.max_output_tokens = new_limit
                    response = call_llm_with_retry(
                        lambda: self.generation_engine.generate(skip_quota=True)
                    )
            finally:
                # Reset to avoid leaking into subsequent plain-text stages
                self.generation_engine.request.generation_config.response_mime_type = None

            if not response.success:
                return self._create_fallback_setting_report(setting, setting_data)
            
            try:
                # Use the robust JSON parser that handles markdown code blocks
                from utils.json_response_parser import JSONResponseParser
                parsed_data, _ = JSONResponseParser.parse_response(response, "dict", {})
                return parsed_data
            except Exception as parse_error:
                self.logger.warning(f"Could not parse setting report response: {parse_error}")
                return self._create_fallback_setting_report(setting, setting_data)
                
        except Exception as e:
            self.logger.error(f"Error generating setting report for {setting}: {e}")
            return None
    
    def _generate_plot_thread_report(self, plot_thread: Dict[str, Any], scenes_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate a plot thread analysis report using AI."""
        try:
            # Get detailed scene information for this plot thread
            thread_scenes = [scene for scene in scenes_data if scene['scene_number'] in plot_thread['scenes']]
            scenes_info = []
            
            for scene in thread_scenes:
                scenes_info.append(f"Scene {scene['scene_number']}: {scene['title']} - {scene.get('summary', '')[:150]}")
            
            prompt = self.prompt_template.get_individual_plot_thread_prompt().format(
                plot_description=plot_thread['description'],
                affected_scenes='\n'.join(scenes_info),
                thread_frequency=plot_thread['frequency']
            )
            
            self.generation_engine.request.prompt = prompt
            self.generation_engine.request.instruction = "Generate a comprehensive plot thread analysis report."

            # Set provider-aware token limit for report JSON
            self.generation_engine.request.generation_config.max_output_tokens = self._get_output_budget("json_analytical")

            # Enable JSON mode for Gemini structured output
            self.generation_engine.request.generation_config.response_mime_type = "application/json"

            try:
                # Generate report (with transient-error retry)
                response = call_llm_with_retry(
                    lambda: self.generation_engine.generate(skip_quota=True)
                )

                # Check if response was truncated due to token limit
                if response.success and hasattr(response, 'metadata') and response.metadata.finish_reason == 'length':
                    current_limit = self.generation_engine.request.generation_config.max_output_tokens
                    new_limit = int(current_limit * 1.5)  # Increase by 50%
                    self.logger.warning(
                        f"Stage 4C plot thread report truncated (finish_reason='length'). "
                        f"Tokens: {response.metadata.output_tokens}. "
                        f"Increasing max_output_tokens from {current_limit} to {new_limit} and retrying..."
                    )
                    self.generation_engine.request.generation_config.max_output_tokens = new_limit
                    response = call_llm_with_retry(
                        lambda: self.generation_engine.generate(skip_quota=True)
                    )
            finally:
                # Reset to avoid leaking into subsequent plain-text stages
                self.generation_engine.request.generation_config.response_mime_type = None

            if not response.success:
                return self._create_fallback_plot_thread_report(plot_thread)
            
            try:
                # Use the robust JSON parser that handles markdown code blocks
                from utils.json_response_parser import JSONResponseParser
                report_data, _ = JSONResponseParser.parse_response(response, "dict", {})
                report_data['thread_metadata'] = plot_thread
                return report_data
            except Exception as parse_error:
                self.logger.warning(f"Could not parse plot thread report response: {parse_error}")
                return self._create_fallback_plot_thread_report(plot_thread)
                
        except Exception as e:
            self.logger.error(f"Error generating plot thread report: {e}")
            return None
    
    def _generate_relationship_report(self, graph_data: Dict[str, Any], scenes_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate a character relationship analysis report using graph data."""
        try:
            relationships = graph_data.get('relationships', [])
            
            if not relationships:
                self.logger.warning("No relationships found in graph data for relationship report")
                return {
                    'total_relationships': 0,
                    'relationship_types': {},
                    'most_connected_characters': [],
                    'network_density': 0.0,
                    'analysis_summary': "No relationships found in graph data"
                }
            
            # Group relationships by type
            relationship_types = Counter()
            character_connections = {}
            
            for rel in relationships:
                # Validate relationship structure
                if not isinstance(rel, dict) or 'relationship_type' not in rel or 'source' not in rel or 'target' not in rel:
                    self.logger.warning(f"Invalid relationship structure: {rel}")
                    continue
                    
                rel_type = rel['relationship_type']
                relationship_types[rel_type] += 1
                
                source = rel['source']
                target = rel['target']
                
                if source not in character_connections:
                    character_connections[source] = []
                if target not in character_connections:
                    character_connections[target] = []
                
                character_connections[source].append({'character': target, 'relationship': rel_type})
                character_connections[target].append({'character': source, 'relationship': rel_type})
            
            # Find most connected characters
            most_connected = sorted(character_connections.items(), key=lambda x: len(x[1]), reverse=True)[:5]
            
            return {
                'total_relationships': len(relationships),
                'relationship_types': dict(relationship_types.most_common()),
                'most_connected_characters': [
                    {
                        'character': char,
                        'connection_count': len(connections),
                        'connections': connections[:5]  # Limit to top 5 connections
                    }
                    for char, connections in most_connected
                ],
                'network_density': len(relationships) / max(1, len(character_connections)),
                'analysis_summary': f"Network contains {len(character_connections)} characters with {len(relationships)} relationships"
            }
            
        except Exception as e:
            self.logger.error(f"Error generating relationship report: {e}")
            return None
    
    def _generate_narrative_report(self, scenes_data: List[Dict[str, Any]], 
                                 major_characters: List[str], major_themes: List[str],
                                 major_settings: List[str], plot_threads: List[Dict[str, Any]],
                                 graph_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate an overall narrative analysis report."""
        total_scenes = len(scenes_data)
        total_content_length = sum(len(scene.get('content', '')) for scene in scenes_data)
        
        all_conflicts = []
        all_settings = set()
        
        for scene in scenes_data:
            analysis = scene.get('analysis', {})
            conflicts = analysis.get('conflicts', [])
            all_conflicts.extend(conflicts)
            
            setting = scene.get('setting', '')
            if setting:
                all_settings.add(setting)
        
        # Enhanced narrative overview with graph insights
        graph_insights = {}
        if graph_data:
            graph_insights = {
                'graph_entities': graph_data.get('entities_count', 0),
                'graph_relationships': graph_data.get('relationships_count', 0),
                'relationship_density': graph_data.get('relationships_count', 0) / max(1, graph_data.get('entities_count', 1))
            }
        
        return {
            'narrative_overview': {
                'total_scenes': total_scenes,
                'total_length': total_content_length,
                'major_characters': len(major_characters),
                'major_themes': len(major_themes),
                'major_settings': len(major_settings),
                'plot_threads': len(plot_threads),
                'unique_settings': len(all_settings),
                **graph_insights
            },
            'characters': major_characters,
            'themes': major_themes,
            'settings': major_settings,
            'plot_threads': [thread['description'][:100] for thread in plot_threads],
            'narrative_complexity': self._assess_complexity(
                total_scenes, len(major_characters), len(major_themes), 
                len(major_settings), len(plot_threads)
            )
        }
    
    def _assess_complexity(self, scenes: int, characters: int, themes: int, 
                          settings: int = 0, plot_threads: int = 0) -> str:
        """Assess narrative complexity with enhanced metrics."""
        score = (scenes * 0.5) + (characters * 2) + (themes * 1.5) + (settings * 1.2) + (plot_threads * 2.5)
        
        if score < 25:
            return 'simple'
        elif score < 60:
            return 'moderate'
        elif score < 100:
            return 'complex'
        else:
            return 'highly_complex'
    
    def _store_analysis_report(self, context: PipelineStageContext, report_type: str, report_subject: str, 
                             report_content: Dict[str, Any]) -> None:
        """Store an analysis report in the database with UTF-8 safety and dynamic values."""
        draft_id = context.draft_id
        
        try:
            db_connection = self.get_database_connection(context)
            with db_connection as conn:
                cursor = conn.cursor()
                
                # Ensure UTF-8 safe JSON encoding and text cleaning
                safe_subject = clean_text_for_database(report_subject)
                content_json = ensure_utf8_json(report_content)
                
                # Get dynamic values from context
                user_id = context.get_user_id(self.db_pool)
                report_id = str(ULID())
                
                cursor.execute("""
                    INSERT INTO analysis_reports (id, draft_id, report_type, report_subject, content_json, generated_at, generated_by)
                    VALUES (%s, %s, %s, %s, %s, NOW(), %s)
                    ON CONFLICT (draft_id, report_type, report_subject) DO UPDATE SET
                    content_json = EXCLUDED.content_json,
                    generated_at = NOW(),
                    generated_by = EXCLUDED.generated_by
                """, (report_id, draft_id, report_type, safe_subject, content_json, user_id))
                
                conn.commit()
                self.logger.debug(f"Stored analysis report {report_type}:{safe_subject} for draft {draft_id} (user_id: {user_id}, UTF-8 safe)")
            
        except Exception as e:
            self.logger.error(f"Failed to store analysis report: {e}")
            raise

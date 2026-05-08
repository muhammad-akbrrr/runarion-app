"""
Stage 5: Coherence Check
Analyzes story for plot holes, inconsistencies, and narrative coherence issues.
"""

import json
import logging
from typing import Dict, Any, List
from collections import defaultdict
from .prompt_template import DeconstructorPrompts
from .base_stage import BasePipelineStage, PipelineStageResult, PipelineStageContext
from src.utils.llm_retry import call_llm_with_retry

logger = logging.getLogger(__name__)

class CoherenceCheckStage(BasePipelineStage):
    """
    Stage 5 of the deconstruction pipeline.
    Performs comprehensive coherence analysis to identify plot issues and inconsistencies.
    """
    
    def __init__(self, db_pool, generation_engine):
        """
        Initialize the coherence check stage.
        
        Args:
            db_pool: Database connection pool
            generation_engine: AI generation engine
        """
        super().__init__(db_pool, "CoherenceCheckStage", generation_engine)
        self.prompt_template = DeconstructorPrompts()
    
    def _execute_stage(self, context: PipelineStageContext) -> PipelineStageResult:
        """
        Execute Stage 5: Coherence check analysis.
        
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
        
        try:
            # Get all analysis data needed for coherence check
            analysis_data = self._get_analysis_data(context)
            
            if not analysis_data['scenes']:
                return PipelineStageResult.success_result(
                    self.stage_name,
                    issues_found=0,
                    scenes_analyzed=0,
                    message='No scenes to analyze for coherence'
                )
            
            # Perform different types of coherence analysis
            all_issues = []
            
            # Timeline consistency check
            timeline_issues = self._check_timeline_consistency(analysis_data)
            all_issues.extend(timeline_issues)
            
            # Character consistency check
            character_issues = self._check_character_consistency(analysis_data)
            all_issues.extend(character_issues)
            
            # Plot logic check
            plot_issues = self._check_plot_logic(analysis_data)
            all_issues.extend(plot_issues)
            
            # Cause and effect analysis
            causality_issues = self._check_causality(analysis_data)
            all_issues.extend(causality_issues)
            
            # Store all identified issues in database
            issues_stored = self._store_plot_issues(context, all_issues)
            
            return PipelineStageResult.success_result(
                self.stage_name,
                scenes_analyzed=len(analysis_data['scenes']),
                issues_found=len(all_issues),
                issues_stored=issues_stored,
                issue_breakdown={
                    'timeline': len(timeline_issues),
                    'character': len(character_issues),
                    'plot': len(plot_issues),
                    'causality': len(causality_issues)
                },
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
        Execute Stage 5 with legacy interface (backward compatibility).
        
        Args:
            draft_id: UUID of the draft
            chaptering_mode: Chaptering approach (backward compatibility)
            target_chapter_length: Target word count (backward compatibility)
            
        Returns:
            Stage execution results
        """
        return super().run(draft_id)
    
    def _get_analysis_data(self, context: PipelineStageContext) -> Dict[str, Any]:
        """
        Retrieve all necessary analysis data for coherence checking.
        
        Args:
            context: Stage execution context
            
        Returns:
            Comprehensive analysis data
        """
        draft_id = context.draft_id
        
        try:
            analysis_data = {
                'scenes': [],
                'characters': [],
                'analysis_reports': [],
                'graph_relationships': []
            }
            
            db_connection = self.get_database_connection(context)
            with db_connection as conn:
                cursor = conn.cursor()
                # Get scenes with analysis data
                cursor.execute("""
                    SELECT id, scene_number, title, setting, characters, 
                           original_content, analysis_json
                    FROM scenes 
                    WHERE draft_id = %s
                    ORDER BY scene_number
                """, (draft_id,))
                
                scenes_raw = cursor.fetchall()
                
                for scene in scenes_raw:
                    scene_id, scene_number, title, setting, characters, content, analysis_json = scene

                    # Validate content length
                    # Reduced from 200 to 150 chars to align with Stage 3 hydration threshold
                    if not content or len(content.strip()) < 150:
                        self.logger.warning(
                            f"Scene {scene_number} has suspiciously short content ({len(content) if content else 0} chars) - "
                            f"may be truncated. Coherence analysis may be affected."
                        )
                    elif content.endswith('...') and len(content) < 500:
                        self.logger.warning(
                            f"Scene {scene_number} appears truncated (ends with '...', length {len(content)} chars). "
                            f"This indicates Stage 3 hydration failure."
                        )

                    try:
                        analysis = json.loads(analysis_json) if analysis_json else {}
                        characters_list = json.loads(characters) if characters else []
                    except (json.JSONDecodeError, TypeError):
                        analysis = {}
                        characters_list = []

                    analysis_data['scenes'].append({
                        'id': scene_id,
                        'scene_number': scene_number,
                        'title': title,
                        'setting': setting,
                        'characters': characters_list,
                        'content': content,
                        'analysis': analysis
                    })
                
                # Get analysis reports for character and narrative context
                cursor.execute("""
                    SELECT report_type, report_subject, content_json
                    FROM analysis_reports
                    WHERE draft_id = %s
                """, (draft_id,))
                
                reports = cursor.fetchall()
                for report_type, subject, content in reports:
                    try:
                        content_data = json.loads(content) if content else {}
                        analysis_data['analysis_reports'].append({
                            'type': report_type,
                            'subject': subject,
                            'content': content_data
                        })
                    except (json.JSONDecodeError, TypeError):
                        continue
                
                # Note: Graph relationships are now handled by Apache AGE integration
                # Legacy relational table 'novel_graph_edges' has been removed
                self.logger.debug("Graph relationship data handled by AGE integration in other pipeline stages")
            
            # Extract unique characters for consistency tracking
            all_characters = set()
            for scene in analysis_data['scenes']:
                all_characters.update(scene['characters'])
                char_dev = scene['analysis'].get('character_development', {})
                all_characters.update(char_dev.keys())
            
            analysis_data['characters'] = list(all_characters)
            
            self.logger.debug(f"Retrieved analysis data: {len(analysis_data['scenes'])} scenes, {len(analysis_data['characters'])} characters")
            return analysis_data
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve analysis data for draft {draft_id}: {e}")
            raise
    
    def _check_timeline_consistency(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for timeline inconsistencies and temporal logic issues.
        
        Args:
            analysis_data: Complete analysis data
            
        Returns:
            List of timeline issues
        """
        issues = []
        scenes = analysis_data['scenes']
        
        try:
            # Look for explicit time references and inconsistencies
            time_references = []
            for scene in scenes:
                content = scene['content'].lower()
                analysis = scene['analysis']
                
                # Check for time contradictions in narrative
                if any(phrase in content for phrase in ['yesterday', 'tomorrow', 'last week', 'next month']):
                    time_references.append({
                        'scene': scene['scene_number'],
                        'content_snippet': content[:200]
                    })
                
                # Check for impossible time sequences in world building
                world_building = analysis.get('world_building', '').lower()
                if 'time' in world_building or 'when' in world_building:
                    # Look for potential time inconsistencies
                    if len(time_references) >= 2:
                        issues.append({
                            'issue_type': 'TIMELINE_INCONSISTENCY',
                            'affected_scenes': [scene['scene_number']],
                            'description': f"Potential timeline inconsistency in scene {scene['scene_number']}: {scene['title']}",
                            'severity': 'medium',
                            'suggested_fix': 'Review temporal references and ensure chronological consistency'
                        })
            
            # Check for character knowledge inconsistencies across time
            character_knowledge = defaultdict(list)
            for scene in scenes:
                char_dev = scene['analysis'].get('character_development', {})
                for char, development in char_dev.items():
                    if isinstance(development, str) and 'knows' in development.lower():
                        character_knowledge[char].append({
                            'scene': scene['scene_number'],
                            'knowledge': development
                        })
            
            # Identify potential knowledge inconsistencies
            for character, knowledge_list in character_knowledge.items():
                if len(knowledge_list) > 1:
                    # Simple heuristic: if knowledge seems contradictory
                    knowledge_texts = [k['knowledge'].lower() for k in knowledge_list]
                    if any('not' in text and 'know' in text for text in knowledge_texts):
                        affected_scenes = [k['scene'] for k in knowledge_list]
                        issues.append({
                            'issue_type': 'CHARACTER_KNOWLEDGE',
                            'affected_scenes': affected_scenes,
                            'description': f"Character {character} has inconsistent knowledge across scenes {affected_scenes}",
                            'severity': 'medium',
                            'suggested_fix': f'Review {character}\'s knowledge progression and ensure logical consistency'
                        })
            
        except Exception as e:
            self.logger.warning(f"Error checking timeline consistency: {e}")
        
        return issues
    
    def _check_character_consistency(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for character behavior and trait inconsistencies.
        
        Args:
            analysis_data: Complete analysis data
            
        Returns:
            List of character consistency issues
        """
        issues = []
        scenes = analysis_data['scenes']
        
        try:
            # Track character traits and behaviors across scenes
            character_traits = defaultdict(list)
            character_behaviors = defaultdict(list)
            
            for scene in scenes:
                char_dev = scene['analysis'].get('character_development', {})
                
                for character, development in char_dev.items():
                    if isinstance(development, str):
                        development_lower = development.lower()
                        
                        # Track behavioral patterns
                        behavior_keywords = ['acts', 'behaves', 'reacts', 'responds', 'decides']
                        if any(keyword in development_lower for keyword in behavior_keywords):
                            character_behaviors[character].append({
                                'scene': scene['scene_number'],
                                'behavior': development,
                                'scene_title': scene['title']
                            })
                        
                        # Track personality traits
                        trait_keywords = ['is', 'becomes', 'shows', 'demonstrates', 'appears']
                        if any(keyword in development_lower for keyword in trait_keywords):
                            character_traits[character].append({
                                'scene': scene['scene_number'],
                                'trait': development,
                                'scene_title': scene['title']
                            })
            
            # Analyze character reports for established traits
            character_reports = {}
            for report in analysis_data['analysis_reports']:
                if report['type'] == 'CHARACTER_ARC':
                    character_reports[report['subject']] = report['content']
            
            # Check for trait contradictions
            for character, traits in character_traits.items():
                if len(traits) > 2:  # Need multiple data points
                    trait_texts = [t['trait'].lower() for t in traits]
                    
                    # Simple contradiction detection
                    contradictory_pairs = [
                        ('brave', 'coward'), ('kind', 'cruel'), ('honest', 'lying'),
                        ('smart', 'stupid'), ('calm', 'angry'), ('confident', 'insecure')
                    ]
                    
                    for positive, negative in contradictory_pairs:
                        has_positive = any(positive in text for text in trait_texts)
                        has_negative = any(negative in text for text in trait_texts)
                        
                        if has_positive and has_negative:
                            affected_scenes = [t['scene'] for t in traits]
                            issues.append({
                                'issue_type': 'CHARACTER_INCONSISTENCY',
                                'affected_scenes': affected_scenes,
                                'description': f"Character {character} shows contradictory traits: {positive} vs {negative}",
                                'severity': 'high',
                                'suggested_fix': f'Resolve character trait contradiction for {character} - ensure consistent personality or show clear character development'
                            })
            
            # Check for unmotivated character actions
            for character, behaviors in character_behaviors.items():
                if len(behaviors) >= 2:
                    # Look for character reports to validate motivations
                    if character in character_reports:
                        char_data = character_reports[character]
                        motivations = char_data.get('motivations', {})
                        
                        if not motivations or not motivations.get('primary'):
                            affected_scenes = [b['scene'] for b in behaviors]
                            issues.append({
                                'issue_type': 'UNCLEAR_MOTIVATION',
                                'affected_scenes': affected_scenes,
                                'description': f"Character {character} lacks clear motivation for actions across multiple scenes",
                                'severity': 'medium',
                                'suggested_fix': f'Establish clearer motivations for {character}\'s actions and decisions'
                            })
            
        except Exception as e:
            self.logger.warning(f"Error checking character consistency: {e}")
        
        return issues
    
    def _check_plot_logic(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for plot holes and logical inconsistencies.
        
        Args:
            analysis_data: Complete analysis data
            
        Returns:
            List of plot logic issues
        """
        issues = []
        scenes = analysis_data['scenes']
        
        try:
            # Track plot threads and their resolution
            plot_elements = defaultdict(list)
            
            for scene in scenes:
                analysis = scene['analysis']
                
                # Collect conflicts and plot elements
                conflicts = analysis.get('conflicts', [])
                for conflict in conflicts:
                    if isinstance(conflict, str) and len(conflict.strip()) > 10:
                        plot_elements['conflicts'].append({
                            'scene': scene['scene_number'],
                            'element': conflict,
                            'scene_title': scene['title']
                        })
                
                # Collect foreshadowing elements
                foreshadowing = analysis.get('foreshadowing', [])
                for element in foreshadowing:
                    if isinstance(element, str) and len(element.strip()) > 10:
                        plot_elements['foreshadowing'].append({
                            'scene': scene['scene_number'],
                            'element': element,
                            'scene_title': scene['title']
                        })
            
            # Check for unresolved conflicts
            conflicts = plot_elements.get('conflicts', [])
            if len(conflicts) > 1:
                # Group similar conflicts
                conflict_groups = {}
                for conflict_data in conflicts:
                    conflict_key = conflict_data['element'][:30].strip()  # Group by first 30 chars
                    if conflict_key not in conflict_groups:
                        conflict_groups[conflict_key] = []
                    conflict_groups[conflict_key].append(conflict_data)
                
                # Check for conflicts that appear only once (potentially unresolved)
                for conflict_key, conflict_list in conflict_groups.items():
                    if len(conflict_list) == 1:
                        conflict_data = conflict_list[0]
                        issues.append({
                            'issue_type': 'UNRESOLVED_CONFLICT',
                            'affected_scenes': [conflict_data['scene']],
                            'description': f"Potential unresolved conflict in scene {conflict_data['scene']}: {conflict_data['element'][:100]}",
                            'severity': 'medium',
                            'suggested_fix': 'Ensure this conflict is properly resolved or remove if not central to the plot'
                        })
            
            # Check for unfulfilled foreshadowing
            foreshadowing_elements = plot_elements.get('foreshadowing', [])
            if foreshadowing_elements:
                # Simple check: foreshadowing in early scenes should have payoff in later scenes
                early_foreshadowing = [f for f in foreshadowing_elements if f['scene'] <= len(scenes) // 2]
                
                for foreshadow in early_foreshadowing:
                    # Check if similar themes appear in later scenes
                    payoff_found = False
                    foreshadow_keywords = foreshadow['element'].lower().split()[:3]  # First 3 words
                    
                    for scene in scenes[foreshadow['scene']:]:  # Check later scenes
                        scene_content = scene['content'].lower()
                        analysis_content = str(scene['analysis']).lower()
                        
                        if any(keyword in scene_content or keyword in analysis_content for keyword in foreshadow_keywords):
                            payoff_found = True
                            break
                    
                    if not payoff_found:
                        issues.append({
                            'issue_type': 'UNFULFILLED_FORESHADOWING',
                            'affected_scenes': [foreshadow['scene']],
                            'description': f"Foreshadowing in scene {foreshadow['scene']} may lack payoff: {foreshadow['element'][:100]}",
                            'severity': 'low',
                            'suggested_fix': 'Ensure foreshadowing elements have appropriate payoff in later scenes'
                        })
            
            # Check for logical plot progression using AI analysis
            if len(scenes) > 2:
                story_summary = self._create_story_summary(scenes)
                ai_issues = self._ai_plot_analysis(story_summary, scenes)
                issues.extend(ai_issues)
            
        except Exception as e:
            self.logger.warning(f"Error checking plot logic: {e}")
        
        return issues
    
    def _check_causality(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check cause and effect relationships in the narrative.
        
        Args:
            analysis_data: Complete analysis data
            
        Returns:
            List of causality issues
        """
        issues = []
        scenes = analysis_data['scenes']
        
        try:
            # Track major events and their consequences
            major_events = []
            
            for scene in scenes:
                analysis = scene['analysis']
                plot_function = analysis.get('plot_function', '').lower()
                
                # Identify scenes with major plot impact
                impact_keywords = ['turns', 'changes', 'decides', 'reveals', 'discovers', 'dies', 'arrives', 'leaves']
                if any(keyword in plot_function for keyword in impact_keywords):
                    major_events.append({
                        'scene': scene['scene_number'],
                        'event': plot_function,
                        'scene_title': scene['title']
                    })
            
            # Check for events without clear consequences
            for i, event in enumerate(major_events):
                if i < len(major_events) - 1:  # Not the last event
                    next_scenes = scenes[event['scene']:][:3]  # Check next 3 scenes
                    
                    consequence_found = False
                    for next_scene in next_scenes:
                        next_analysis = next_scene['analysis'].get('plot_function', '').lower()
                        
                        # Simple keyword matching for consequences
                        consequence_keywords = ['because', 'due to', 'result', 'consequence', 'therefore']
                        if any(keyword in next_analysis for keyword in consequence_keywords):
                            consequence_found = True
                            break
                    
                    if not consequence_found:
                        issues.append({
                            'issue_type': 'MISSING_CONSEQUENCES',
                            'affected_scenes': [event['scene']],
                            'description': f"Major event in scene {event['scene']} may lack clear consequences: {event['event'][:100]}",
                            'severity': 'medium',
                            'suggested_fix': 'Show the consequences or impact of this event in subsequent scenes'
                        })
            
        except Exception as e:
            self.logger.warning(f"Error checking causality: {e}")
        
        return issues
    
    def _create_story_summary(self, scenes: List[Dict[str, Any]]) -> str:
        """
        Create a concise story summary for AI analysis.
        
        Args:
            scenes: List of scene data
            
        Returns:
            Story summary string
        """
        summary_parts = []
        
        for scene in scenes[:10]:  # Limit to first 10 scenes for summary
            scene_summary = f"Scene {scene['scene_number']}: {scene['title']}"
            if scene['analysis'].get('plot_function'):
                scene_summary += f" - {scene['analysis']['plot_function'][:100]}"
            summary_parts.append(scene_summary)
        
        return '\n'.join(summary_parts)
    
    def _ai_plot_analysis(self, story_summary: str, scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Use AI to analyze plot coherence and identify issues.
        
        Args:
            story_summary: Summary of the story
            scenes: List of scene data
            
        Returns:
            List of AI-identified issues
        """
        issues = []
        
        try:
            # Prepare character information
            all_characters = set()
            for scene in scenes:
                all_characters.update(scene['characters'])
                char_dev = scene['analysis'].get('character_development', {})
                all_characters.update(char_dev.keys())
            
            character_data = ', '.join(list(all_characters)[:10])  # Limit to top 10 characters
            
            # Create scene sequence summary
            scene_sequence = []
            for scene in scenes:
                sequence_item = f"Scene {scene['scene_number']}: {scene['title']} (Setting: {scene['setting']})"
                scene_sequence.append(sequence_item)
            
            # Generate coherence analysis prompt
            prompt = self.prompt_template.get_coherence_check_prompt().format(
                story_summary=story_summary,
                character_data=character_data,
                scene_sequence='\n'.join(scene_sequence[:15])  # Limit to first 15 scenes
            )
            
            # Generate AI analysis
            self.generation_engine.request.prompt = prompt
            self.generation_engine.request.instruction = "Analyze the story for plot holes, inconsistencies, and coherence issues."

            # Set provider-aware token limit for coherence analysis JSON
            self.generation_engine.request.generation_config.max_output_tokens = self._get_output_budget("json_analytical")

            # Enable JSON mode for Gemini structured output
            self.generation_engine.request.generation_config.response_mime_type = "application/json"

            try:
                # Generate coherence analysis (with transient-error retry)
                response = call_llm_with_retry(
                    lambda: self.generation_engine.generate(skip_quota=True)
                )

                # Check if response was truncated due to token limit
                if response.success and hasattr(response, 'metadata') and response.metadata.finish_reason == 'length':
                    current_limit = self.generation_engine.request.generation_config.max_output_tokens
                    new_limit = int(current_limit * 1.5)  # Increase by 50%
                    self.logger.warning(
                        f"Stage 5 coherence analysis truncated (finish_reason='length'). "
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

            if response.success:
                try:
                    # Use the robust JSON parser that handles markdown code blocks
                    from src.utils.json_response_parser import JSONResponseParser
                    analysis_result, _ = JSONResponseParser.parse_response(response, "dict", {})
                    
                    # Convert AI analysis to our issue format
                    for category in ['timeline_issues', 'character_issues', 'plot_issues']:
                        ai_issues = analysis_result.get(category, [])
                        if isinstance(ai_issues, list):
                            for ai_issue in ai_issues:
                                if isinstance(ai_issue, dict):
                                    issues.append({
                                        'issue_type': ai_issue.get('issue_type', 'AI_IDENTIFIED'),
                                        'affected_scenes': ai_issue.get('affected_scenes', []),
                                        'description': ai_issue.get('description', 'AI identified issue'),
                                        'severity': ai_issue.get('severity', 'medium'),
                                        'suggested_fix': ai_issue.get('suggested_fix', 'Review and address this issue')
                                    })
                    
                except Exception as parse_error:
                    self.logger.warning(f"Could not parse AI coherence analysis response: {parse_error}")
                    if hasattr(response, 'text'):
                        self.logger.debug(f"Raw response text: {response.text[:500]}...")
                    
        except Exception as e:
            self.logger.warning(f"Error in AI plot analysis: {e}")
        
        return issues
    
    def _store_plot_issues(self, context: PipelineStageContext, issues: List[Dict[str, Any]]) -> int:
        """
        Store identified plot issues in the database.
        
        Args:
            context: Stage execution context
            issues: List of identified issues
            
        Returns:
            Number of issues stored
        """
        draft_id = context.draft_id
        
        if not issues:
            return 0
        
        try:
            issues_stored = 0
            
            db_connection = self.get_database_connection(context)
            with db_connection as conn:
                cursor = conn.cursor()
                # Clear existing issues for this draft
                cursor.execute("DELETE FROM plot_issues WHERE draft_id = %s", (draft_id,))
                
                # Prepare bulk insert data
                issue_data = []
                for issue in issues:
                    # Get the first affected scene (required by schema)
                    affected_scenes = issue.get('affected_scenes', [])
                    if not affected_scenes:
                        continue
                    
                    primary_scene = affected_scenes[0]
                    
                    # Get the actual scene ID from scene number
                    cursor.execute("""
                        SELECT id FROM scenes 
                        WHERE draft_id = %s AND scene_number = %s
                        LIMIT 1
                    """, (draft_id, primary_scene))
                    
                    scene_result = cursor.fetchone()
                    if not scene_result:
                        continue
                    
                    scene_id = scene_result[0]
                    
                    issue_data.append((
                        draft_id,
                        scene_id,
                        issue.get('issue_type', 'UNKNOWN'),
                        issue.get('description', 'No description'),
                        issue.get('severity', 'medium'),
                        issue.get('suggested_fix', 'No suggestion provided')
                    ))
                
                # Bulk insert issues
                if issue_data:
                    cursor.executemany("""
                        INSERT INTO plot_issues (
                            draft_id, affected_scene_id, issue_type, 
                            description, severity, suggested_fix
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, issue_data)
                    
                    issues_stored = cursor.rowcount
                    conn.commit()
            
            self.logger.info(f"Stored {issues_stored} plot issues for draft {draft_id}")
            return issues_stored
            
        except Exception as e:
            self.logger.error(f"Failed to store plot issues for draft {draft_id}: {e}")
            raise
    
    def get_coherence_statistics(self, draft_id: str) -> Dict[str, Any]:
        """
        Get statistics about coherence analysis results.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Coherence statistics
        """
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                # Get issue counts by type and severity
                cursor.execute("""
                    SELECT issue_type, severity, COUNT(*) as count
                    FROM plot_issues
                    WHERE draft_id = %s
                    GROUP BY issue_type, severity
                    ORDER BY count DESC
                """, (draft_id,))
                
                issue_breakdown = cursor.fetchall()
                
                # Get total counts
                cursor.execute("""
                    SELECT COUNT(*) as total_issues,
                           COUNT(CASE WHEN severity = 'high' THEN 1 END) as high_severity,
                           COUNT(CASE WHEN severity = 'medium' THEN 1 END) as medium_severity,
                           COUNT(CASE WHEN severity = 'low' THEN 1 END) as low_severity
                    FROM plot_issues
                    WHERE draft_id = %s
                """, (draft_id,))
                
                totals = cursor.fetchone()
                
                stats = {
                    'total_issues': totals[0] if totals else 0,
                    'severity_breakdown': {
                        'high': totals[1] if totals else 0,
                        'medium': totals[2] if totals else 0,
                        'low': totals[3] if totals else 0
                    },
                    'issue_types': {}
                }
                
                # Organize issue breakdown
                for issue_type, severity, count in issue_breakdown:
                    if issue_type not in stats['issue_types']:
                        stats['issue_types'][issue_type] = {}
                    stats['issue_types'][issue_type][severity] = count
            
            self.db_pool.putconn(conn)
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get coherence statistics for draft {draft_id}: {e}")
            return {'error': str(e)}

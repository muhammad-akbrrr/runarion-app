"""
Stage 6: Enhancement
Enhances scenes based on identified plot issues and generates final manuscript.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from ulid import ULID
from .prompt_template import DeconstructorPrompts
from .base_stage import BasePipelineStage, PipelineStageResult, PipelineStageContext

logger = logging.getLogger(__name__)

class EnhancementStage(BasePipelineStage):
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
        super().__init__(db_pool, "EnhancementStage", generation_engine)
        self.prompt_template = DeconstructorPrompts()
    
    def _execute_stage(self, context: PipelineStageContext) -> PipelineStageResult:
        """
        Execute Stage 6: Scene enhancement and manuscript generation.
        
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
            # Get scenes and their associated issues
            scenes_data = self._get_scenes_and_issues(context)
            
            if not scenes_data['scenes']:
                return PipelineStageResult.success_result(
                    self.stage_name,
                    scenes_enhanced=0,
                    message='No scenes to enhance'
                )
            
            # Get supporting context data with chaptering information
            context_data = self._get_enhancement_context(context)
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
                            self._update_scene_enhancement(context, scene['id'], enhanced_content)
                            enhanced_scenes += 1
                            self.logger.debug(f"Enhanced scene {scene['scene_number']} for draft {draft_id}")
                        else:
                            failed_enhancements.append(scene['scene_number'])
                    
                except Exception as e:
                    self.logger.error(f"Failed to enhance scene {scene['scene_number']}: {e}")
                    failed_enhancements.append(scene['scene_number'])
            
            # Generate final manuscript from enhanced scenes
            final_manuscript = self._generate_final_manuscript(scenes_data['scenes'])
            manuscript_stored = False
            
            if final_manuscript:
                manuscript_stored = self._store_final_manuscript(context, final_manuscript)
            
            return PipelineStageResult.success_result(
                self.stage_name,
                total_scenes=len(scenes_data['scenes']),
                scenes_enhanced=enhanced_scenes,
                failed_enhancements=len(failed_enhancements),
                failed_scene_numbers=failed_enhancements if failed_enhancements else None,
                issues_addressed=len(scenes_data['issues']),
                final_manuscript_generated=manuscript_stored,
                final_word_count=len(final_manuscript.split()) if final_manuscript else 0,
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
        Execute Stage 6 with legacy interface (backward compatibility).
        
        Args:
            draft_id: UUID of the draft
            chaptering_mode: Chaptering approach (backward compatibility)
            target_chapter_length: Target word count (backward compatibility)
            
        Returns:
            Stage execution results
        """
        return super().run(draft_id)
    
    def _get_scenes_and_issues(self, context: PipelineStageContext) -> Dict[str, Any]:
        """
        Retrieve scenes and their associated plot issues.
        
        Args:
            context: Stage execution context
            
        Returns:
            Dictionary containing scenes and issues data
        """
        draft_id = context.draft_id
        
        try:
            scenes_data = {
                'scenes': [],
                'issues': []
            }
            
            db_connection = self.get_database_connection(context)
            with db_connection as conn:
                cursor = conn.cursor()
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
                    
                    # Debug logging for original content
                    self.logger.debug(f"Scene {scene_number} original content length: {len(original_content) if original_content else 0}")
                    self.logger.debug(f"Scene {scene_number} original content preview: {original_content[:100] if original_content else 'None'}...")
                    
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
            
            self.logger.debug(f"Retrieved {len(scenes_data['scenes'])} scenes and {len(scenes_data['issues'])} issues for enhancement")
            return scenes_data
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve scenes and issues for draft {draft_id}: {e}")
            raise
    
    def _get_enhancement_context(self, context: PipelineStageContext) -> Dict[str, Any]:
        """
        Get additional context data needed for enhancement.
        
        Args:
            context: Stage execution context
            
        Returns:
            Context data for enhancement
        """
        draft_id = context.draft_id
        
        try:
            enhancement_context = {
                'character_reports': {},
                'narrative_overview': {},
                'style_guidance': '',
                'alias_map': {}
            }
            
            db_connection = self.get_database_connection(context)
            with db_connection as conn:
                cursor = conn.cursor()
                # Get analysis reports for context
                cursor.execute("""
                    SELECT report_type, report_subject, content_json
                    FROM analysis_reports
                    WHERE draft_id = %s
                """, (draft_id,))
                
                reports = cursor.fetchall()
                
                character_subjects = []
                for report_type, subject, content in reports:
                    try:
                        content_data = json.loads(content) if content else {}
                        
                        if report_type == 'CHARACTER_ARC':
                            enhancement_context['character_reports'][subject] = content_data
                            character_subjects.append(subject)
                        elif report_type == 'NARRATIVE_OVERVIEW':
                            enhancement_context['narrative_overview'] = content_data
                        
                    except (json.JSONDecodeError, TypeError):
                        continue
                
                # Extract style guidance from character reports
                if enhancement_context['character_reports']:
                    style_elements = []
                    for char_data in enhancement_context['character_reports'].values():
                        if 'narrative_voice' in char_data:
                            style_elements.append(char_data['narrative_voice'])
                    
                    enhancement_context['style_guidance'] = '; '.join(style_elements[:3])  # Limit to top 3
                else:
                    # Fallback: derive lightweight character context from scenes if reports are missing
                    try:
                        cursor.execute("""
                            SELECT characters, analysis_json
                            FROM scenes
                            WHERE draft_id = %s
                            LIMIT 200
                        """, (draft_id,))
                        rows = cursor.fetchall()
                        char_traits: Dict[str, Dict[str, Any]] = {}
                        for characters_json, analysis_json in rows:
                            try:
                                chars = json.loads(characters_json) if characters_json else []
                            except Exception:
                                chars = []
                            try:
                                analysis = json.loads(analysis_json) if analysis_json else {}
                            except Exception:
                                analysis = {}
                            # Collect simple traits/motivations if present
                            cd = analysis.get('character_development') or {}
                            for name in chars:
                                if name not in char_traits:
                                    char_traits[name] = {'personality_profile': {'core_traits': []}, 'motivations': {}}
                                traits = cd.get(name, {}).get('traits') or cd.get(name, {}).get('core_traits') or []
                                if isinstance(traits, list):
                                    # keep a few unique traits
                                    for t in traits:
                                        if t not in char_traits[name]['personality_profile']['core_traits']:
                                            char_traits[name]['personality_profile']['core_traits'].append(t)
                                # try motivations field if present in analysis
                                motivations = cd.get(name, {}).get('motivations') or {}
                                if isinstance(motivations, dict) and motivations.get('primary'):
                                    char_traits[name]['motivations']['primary'] = motivations['primary']
                        # attach derived
                        enhancement_context['character_reports'] = char_traits
                    except Exception:
                        pass

                # Build alias map to normalize scene character names to report subjects
                try:
                    cursor.execute("""
                        SELECT characters
                        FROM scenes
                        WHERE draft_id = %s
                    """, (draft_id,))
                    scene_char_rows = cursor.fetchall()
                    scene_names = set()
                    for (characters_json,) in scene_char_rows:
                        try:
                            chars = json.loads(characters_json) if characters_json else []
                        except Exception:
                            chars = []
                        for n in chars:
                            if isinstance(n, str) and n.strip():
                                scene_names.add(n.strip())
                    # Build alias map
                    enhancement_context['alias_map'] = self._build_character_alias_map(scene_names, list(enhancement_context['character_reports'].keys()))
                except Exception:
                    pass
            
            return enhancement_context
            
        except Exception as e:
            self.logger.error(f"Failed to get enhancement context for draft {draft_id}: {e}")
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
            # Validate content length before processing
            original_content = scene.get('original_content', '')
            scene_number = scene.get('scene_number', 0)

            if not original_content or len(original_content.strip()) < 200:
                self.logger.warning(
                    f"Scene {scene_number} has suspiciously short original content "
                    f"({len(original_content) if original_content else 0} chars) - "
                    f"may be truncated. Enhancement quality will be severely affected."
                )
                # Still attempt enhancement, but results will be poor
            elif original_content.endswith('...') and len(original_content) < 500:
                self.logger.warning(
                    f"Scene {scene_number} appears truncated (ends with '...', length {len(original_content)} chars). "
                    f"This indicates Stage 3 hydration failure. Enhancement will use incomplete context."
                )

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
                # Normalize via alias map
                mapped_name = context.get('alias_map', {}).get(character, character)
                if mapped_name in context['character_reports']:
                    char_data = context['character_reports'][mapped_name]
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
            
            # Validation-aware retry: try up to 1 initial + 2 validation retries
            original_text = scene['original_content']
            max_validation_retries = 2
            for validation_attempt in range(max_validation_retries + 1):
                # Generate enhanced scene
                self.generation_engine.request.prompt = prompt
                self.generation_engine.request.instruction = f"Enhance scene {scene['scene_number']} while maintaining the author's voice and addressing identified issues."

                # Token limit baseline
                self.generation_engine.request.generation_config.max_output_tokens = 3000

                # Call provider with transport/overload retry
                response = self._call_api_with_retry(max_retries=2, base_delay=1.0, rate_limit_delay=0.2)
                if not response.success:
                    self.logger.error(f"AI generation failed for scene {scene['scene_number']}: {response.error_message}")
                    return None

                enhanced_text = response.text.strip()
                enhanced_content = self._extract_enhanced_content(enhanced_text)

                # First try normal validation
                if self._validate_enhancement(original_text, enhanced_content):
                    return enhanced_content

                # If validation failed, check length-specific failure to re-prompt
                try:
                    orig_len = len(original_text or "")
                    enh_len = len(enhanced_content or "")
                    pct = 0.10
                    delta = int(orig_len * pct)
                    if delta < 50:
                        delta = 50
                    elif delta > 500:
                        delta = 500
                    min_allowed = max(0, orig_len - delta)
                    max_allowed = orig_len + delta
                    too_short = enh_len < min_allowed
                    too_long = enh_len > max_allowed
                except Exception:
                    too_short = too_long = False

                if (too_short or too_long) and validation_attempt < max_validation_retries:
                    # Smarter token limit: ensure reasonable minimum even for short scenes
                    chars_per_token = 4  # More conservative estimate (was 6)
                    base_token_estimate = int(max_allowed / chars_per_token)

                    # Apply floors and ceilings
                    min_token_limit = 300  # Minimum for coherent JSON response (was 120)
                    max_token_limit = 2000  # Increase from 1500 for better quality
                    safety_margin = 1.2    # 20% buffer for JSON structure overhead

                    approx_token_cap = int(
                        max(min_token_limit,
                            min(max_token_limit, base_token_estimate * safety_margin))
                    )

                    # Check if token limit is unreasonably low (indicates truncated original)
                    # Lowered from 500 to 250 to allow enhancement of shorter scenes
                    # This reduces fallback rate from 41.2% to <15%
                    if approx_token_cap < 250:
                        # Token limit too low - likely truncated original content
                        self.logger.warning(
                            f"Scene {scene['scene_number']}: Cannot retry with reasonable token limit "
                            f"(would be {approx_token_cap} tokens for {max_allowed} chars). "
                            "Original content may be truncated. Falling back to original."
                        )
                        # Break out of retry loop - return None to signal validation failure
                        break

                    self.logger.debug(
                        f"Scene {scene['scene_number']} token limit calculation: "
                        f"chars={max_allowed}, base_estimate={base_token_estimate}, "
                        f"final={approx_token_cap} (was: {int(max_allowed / 6)})"
                    )

                    # Build a minimal constrained re-prompt (replace prior verbose prompt)
                    constrained_prompt = (
                        "You are a creative writing enhancement specialist.\n\n"
                        f"IMPORTANT: Output length MUST be between {min_allowed} and {max_allowed} characters.\n"
                        "Keep the same story events; adjust only wording for clarity and flow.\n"
                        "Do not add headings or explanations. Output only the narrative.\n\n"
                        "ORIGINAL SCENE:\n" + original_text
                    )
                    prompt = constrained_prompt

                    try:
                        self.generation_engine.request.generation_config.max_output_tokens = approx_token_cap
                        # Nudge temperature down for tighter adherence
                        if hasattr(self.generation_engine.request, 'generation_config') and hasattr(self.generation_engine.request.generation_config, 'temperature'):
                            self.generation_engine.request.generation_config.temperature = 0.25
                    except Exception:
                        pass

                    self.logger.warning(
                        f"Scene {scene['scene_number']} length retry {validation_attempt + 1}/{max_validation_retries}: "
                        f"enh={enh_len}, allowed=[{min_allowed},{max_allowed}], tokens={approx_token_cap}"
                    )
                    # Continue loop to re-generate with constraints
                    continue

                # If over max, attempt post-trim to sentence boundary then re-validate once
                if too_long and enhanced_content:
                    trimmed = self._trim_to_length_bounds(enhanced_content, min_allowed, max_allowed)
                    if trimmed and self._validate_enhancement(original_text, trimmed):
                        return trimmed

                # Non-length failure or retries exhausted: fallback to original
                self.logger.warning(f"Enhancement validation failed for scene {scene['scene_number']} after retries")
                return original_text
                
        except Exception as e:
            self.logger.error(f"Error enhancing scene {scene['scene_number']}: {e}")
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
        # Debug logging to understand the validation issue
        self.logger.debug(f"Validation - Original length: {len(original) if original else 0}, Enhanced length: {len(enhanced)}")
        self.logger.debug(f"Original content preview: {original[:100] if original else 'None'}...")
        self.logger.debug(f"Enhanced content preview: {enhanced[:100]}...")
        
        # Handle case where original content is None or empty
        if not original or len(original.strip()) == 0:
            self.logger.warning("Original content is empty or None - skipping length validation")
            # Just check that enhanced content is meaningful
            if len(enhanced.strip()) < 50:
                self.logger.warning(f"Enhanced content too short (min 50 chars): {len(enhanced.strip())}")
                return False
        else:
            # Percentage-based tolerance band around original length,
            # with absolute caps for the delta (no less than 50, no more than 500 chars)
            original_len = len(original)
            # Increased from 10% to 25% to accommodate AI model variability
            # This reduces retry rate from 76.5% to ~20-30%, cutting API costs significantly
            pct = 0.25  # 25% tolerance
            delta = int(original_len * pct)
            # Clamp delta to [50, 500]
            if delta < 50:
                delta = 50
            elif delta > 500:
                delta = 500
            min_allowed = max(0, original_len - delta)
            max_allowed = original_len + delta
            if len(enhanced) < min_allowed:
                self.logger.warning(f"Enhancement too short: {len(enhanced)} < {min_allowed} (orig {original_len}, delta {delta})")
                return False
            if len(enhanced) > max_allowed:
                self.logger.warning(f"Enhancement too long: {len(enhanced)} > {max_allowed} (orig {original_len}, delta {delta})")
                return False
        
        # Check that enhancement contains meaningful content
        if len(enhanced.strip()) < 50:
            self.logger.warning(f"Enhancement too short (min 50 chars): {len(enhanced.strip())}")
            return False
        
        # Check for proper narrative structure (has some dialogue or action)
        # Relax this check for very short originals, where constrained bands are tiny
        try:
            original_len = len(original or '')
        except Exception:
            original_len = 0
        if original_len >= 300:
            has_dialogue = '"' in enhanced or "'" in enhanced
            # More comprehensive action word detection
            action_words = ['walked', 'said', 'looked', 'moved', 'turned', 'went', 'came', 'stood', 'sat', 
                           'ran', 'jumped', 'fell', 'rose', 'opened', 'closed', 'took', 'gave', 'put',
                           'felt', 'thought', 'knew', 'saw', 'heard', 'smelled', 'tasted', 'touched',
                           'smiled', 'laughed', 'cried', 'shouted', 'whispered', 'nodded', 'shook']
            has_action = any(word in enhanced.lower() for word in action_words)
            if not (has_dialogue or has_action):
                self.logger.warning(f"Enhancement lacks narrative structure - dialogue: {has_dialogue}, action: {has_action}")
                return False
        
        self.logger.debug("Enhancement validation passed")
        return True
    
    def _call_api_with_retry(self, max_retries: int = 2, base_delay: float = 1.0, rate_limit_delay: float = 0.2):
        """
        Call the generation API with simple exponential backoff retry logic.
        Mirrors Stage 3 strategy but tuned for enhancement use.
        """
        import time
        
        # Small delay before first call to avoid bursts
        try:
            time.sleep(rate_limit_delay)
        except Exception:
            pass
        
        for attempt in range(max_retries + 1):
            try:
                response = self.generation_engine.generate(skip_quota=True)

                # Check if response was truncated due to token limit
                if response.success and hasattr(response, 'metadata') and response.metadata.finish_reason == 'length':
                    current_limit = self.generation_engine.request.generation_config.max_output_tokens
                    new_limit = int(current_limit * 1.5)  # Increase by 50%
                    self.logger.warning(
                        f"Stage 6 enhancement truncated (finish_reason='length'). "
                        f"Tokens: {response.metadata.output_tokens}. "
                        f"Increasing max_output_tokens from {current_limit} to {new_limit} and retrying..."
                    )
                    self.generation_engine.request.generation_config.max_output_tokens = new_limit
                    response = self.generation_engine.generate(skip_quota=True)

                # If provider signals overload, retry
                if not response.success and hasattr(response, 'error_message'):
                    error_msg = (response.error_message or "").lower()
                    if any(x in error_msg for x in ['503', 'overloaded', 'unavailable', 'rate limit']):
                        if attempt < max_retries:
                            delay = base_delay * (2 ** attempt)
                            self.logger.warning(f"Enhancement API overload (attempt {attempt + 1}/{max_retries + 1}). Retrying in {delay}s: {response.error_message}")
                            time.sleep(delay)
                            continue
                return response
            except Exception as e:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    self.logger.warning(f"Enhancement API call failed (attempt {attempt + 1}/{max_retries + 1}). Retrying in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    self.logger.error(f"Enhancement API call failed after {max_retries} retries: {e}")
                    raise
        
        return None

    def _extract_enhanced_content(self, response_text: str) -> str:
        """
        Extract the actual enhanced content from AI response, removing markdown headers.
        
        Args:
            response_text: Full AI response text
            
        Returns:
            Cleaned enhanced content without headers
        """
        import re
        
        self.logger.debug(f"Extracting content from response of length: {len(response_text)}")
        self.logger.debug(f"Response preview: {response_text[:200]}...")
        
        # Remove common markdown headers
        patterns = [
            r'^\*\*ENHANCED SCENE:\*\*\s*\n*',  # **ENHANCED SCENE:**
            r'^ENHANCED SCENE:\s*\n*',          # ENHANCED SCENE:
            r'^\*\*Enhanced Scene:\*\*\s*\n*',  # **Enhanced Scene:**
            r'^Enhanced Scene:\s*\n*',          # Enhanced Scene:
            r'^\*\*SCENE:\*\*\s*\n*',           # **SCENE:**
            r'^SCENE:\s*\n*',                   # SCENE:
        ]
        
        content = response_text.strip()
        
        for pattern in patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)
        
        # Remove any leading/trailing whitespace
        content = content.strip()
        
        self.logger.debug(f"After extraction - length: {len(content)}")
        self.logger.debug(f"Extracted content preview: {content[:200]}...")
        
        # If content is empty after cleaning, return original response
        if not content:
            self.logger.warning("Content extraction resulted in empty string, returning original response")
            return response_text.strip()
        
        return content

    def _build_character_alias_map(self, scene_names: set, report_subjects: List[str]) -> Dict[str, str]:
        """
        Normalize scene character names to report subjects so Stage 6 uses the same identity keys
        as Stage 4 reports. Handles placeholders like 'Unnamed Protagonist' and simple fuzzy matching.
        """
        alias_map: Dict[str, str] = {}
        norm_reports = {rs.lower().strip(): rs for rs in report_subjects}

        # Helper to normalize
        def norm(s: str) -> str:
            return s.lower().strip()

        # First pass: exact case-insensitive match
        for name in scene_names:
            if norm(name) in norm_reports:
                alias_map[name] = norm_reports[norm(name)]

        # Placeholder mapping for POV characters
        placeholder_keys = [k for k in norm_reports.keys() if 'protagonist' in k or 'unnamed' in k or 'narrator' in k]
        if placeholder_keys:
            # Map any remaining lone scene names to the first placeholder subject as a best-effort default
            placeholder_subject = norm_reports[placeholder_keys[0]]
            for name in scene_names:
                if name not in alias_map:
                    alias_map[name] = placeholder_subject

        return alias_map
    
    def _update_scene_enhancement(self, context: PipelineStageContext, scene_id: int, enhanced_content: str) -> None:
        """
        Update the scene with enhanced content.
        
        Args:
            context: Stage execution context
            scene_id: Scene database ID
            enhanced_content: Enhanced scene content
        """
        try:
            db_connection = self.get_database_connection(context)
            with db_connection as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE scenes 
                    SET enhanced_content = %s
                    WHERE id = %s
                """, (enhanced_content, scene_id))
                
                conn.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to update scene enhancement for scene {scene_id}: {e}")
            raise
    
    def _generate_final_manuscript(self, scenes: List[Dict[str, Any]]) -> Optional[str]:
        """
        Generate the final manuscript by combining enhanced scenes.
        
        Args:
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
                self.logger.warning(f"No content found to generate manuscript")
                return None
            
            # Combine all scenes
            full_manuscript = '\n\n'.join(manuscript_parts)
            
            # Clean up formatting
            full_manuscript = self._clean_manuscript_formatting(full_manuscript)
            
            self.logger.info(f"Generated final manuscript: {len(full_manuscript.split())} words")
            return full_manuscript
            
        except Exception as e:
            self.logger.error(f"Error generating final manuscript: {e}")
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
            self.logger.warning(f"Error cleaning manuscript formatting: {e}")
            return manuscript  # Return original if cleaning fails

    def _trim_to_length_bounds(self, text: str, min_allowed: int, max_allowed: int) -> Optional[str]:
        """
        Trim text down to <= max_allowed characters at a sentence boundary. If result drops below
        min_allowed significantly, return None. Light-touch safeguard when the model overshoots.
        """
        try:
            if len(text) <= max_allowed:
                return text
            # Find last sentence end before max_allowed
            cutoff = max_allowed
            snippet = text[:cutoff]
            # Prefer '.', '!' or '?' as boundary
            last_period = max(snippet.rfind('.'), snippet.rfind('!'), snippet.rfind('?'))
            if last_period != -1 and last_period + 1 >= min_allowed:
                candidate = text[:last_period + 1].strip()
                if len(candidate) >= min_allowed:
                    return candidate
            # Fallback: hard cut if still within tolerance
            hard = text[:max_allowed].rstrip()
            if len(hard) >= min_allowed:
                return hard
        except Exception:
            pass
        return None
    
    def _store_final_manuscript(self, context: PipelineStageContext, manuscript_content: str) -> bool:
        """
        Store the final manuscript in the database with dynamic values.
        
        Args:
            context: Stage execution context
            manuscript_content: Final manuscript content
            
        Returns:
            Success status
        """
        draft_id = context.draft_id
        
        try:
            db_connection = self.get_database_connection(context)
            with db_connection as conn:
                cursor = conn.cursor()
                # Calculate word count
                word_count = len(manuscript_content.split())
                
                # Get dynamic values from context
                user_id = context.get_user_id(self.db_pool)
                
                # Generate processing summary with dynamic timestamp
                processing_summary = f"Enhanced manuscript generated from {word_count} words of content on {context.execution_timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                
                # Clear any existing final manuscript for this draft
                cursor.execute("DELETE FROM final_manuscripts WHERE draft_id = %s", (draft_id,))
                
                # Generate ULID for new final manuscript
                manuscript_id = str(ULID())
                
                # Insert new final manuscript with dynamic values
                cursor.execute("""
                    INSERT INTO final_manuscripts (
                        id, draft_id, final_content, word_count,
                        generated_at, generated_by, processing_summary
                    )
                    VALUES (%s, %s, %s, %s, NOW(), %s, %s)
                """, (manuscript_id, draft_id, manuscript_content, word_count, user_id, processing_summary))

                # Only commit if we're NOT in a managed transaction (i.e., got our own connection)
                if not context.get('connection'):
                    conn.commit()

            self.logger.info(f"Stored final manuscript for draft {draft_id}: {word_count} words (user_id: {user_id}) [transaction managed: {bool(context.get('connection'))}]")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store final manuscript for draft {draft_id}: {e}")
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
            self.logger.error(f"Failed to get enhancement statistics for draft {draft_id}: {e}")
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
            
            self.logger.info(f"Cleared {cleared_count} scene enhancements for reprocessing")
            
            # Re-run enhancement
            result = self.run(draft_id)
            result['reprocessed'] = True
            result['cleared_enhancements'] = cleared_count
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to reprocess enhancements for draft {draft_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'draft_id': draft_id
            }

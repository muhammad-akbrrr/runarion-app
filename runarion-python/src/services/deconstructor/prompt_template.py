"""
Prompt templates for the novel deconstructor pipeline.
Contains specialized prompts for each stage of analysis.
"""

class DeconstructorPrompts:
    """
    Collection of prompt templates for novel analysis stages.
    """
    
    @staticmethod
    def get_text_cleaning_prompt() -> str:
        """Prompt for Stage 2: Text Cleaning"""
        return """You are a text cleaning specialist for novel analysis. Your task is to clean and normalize raw text extracted from documents while preserving all narrative content and structure.

CRITICAL REQUIREMENTS:
1. PRESERVE ALL CONTENT - Do not summarize, omit, or truncate any text
2. Maintain the original text length - cleaned text should be similar length to original
3. Clean and improve the text while keeping every narrative element

CLEANING INSTRUCTIONS:
1. Remove OCR artifacts, duplicate characters, and formatting errors
2. Fix spacing issues and line breaks
3. Correct obvious typos and encoding problems
4. Preserve dialogue formatting and paragraph structure
5. Maintain chapter/section breaks
6. Improve sentence structure and flow
7. Enhance readability while preserving the original tone and style

INPUT TEXT:
{text_chunk}

OUTPUT FORMAT:
Return only the cleaned text without any additional commentary or formatting markers.

CLEANED TEXT:"""

    @staticmethod
    def get_scene_detection_prompt() -> str:
        """Prompt for Stage 3: Scene Detection"""
        return """You are an expert literary analyst specializing in scene boundary detection for novels. Analyze the provided text and identify distinct scenes based on changes in time, location, characters, or narrative focus.

CRITICAL REQUIREMENT: Extract between 8 and 20 scenes from the text. This is mandatory.

SCENE CRITERIA:
- Change in time (hours, days, weeks)
- Change in location or setting
- Change in point of view character
- Significant shift in action or focus
- Chapter or section breaks

SCENE COUNT VALIDATION:
- MINIMUM: 8 scenes (look for subtle transitions if needed)
- MAXIMUM: 20 scenes (combine minor transitions if needed)
- OPTIMAL: 12-16 scenes for most text chunks

ANALYSIS TEXT:
{text_content}

For each scene identified, provide:
1. Scene number (sequential)
2. Title (2-4 words, descriptive)
3. Setting (location and time period)
4. Main characters present
5. Brief summary (1-2 sentences)
6. Start and end markers in the text

OUTPUT FORMAT (JSON):
[
  {{
    "scene_number": 1,
    "title": "Opening at Market",
    "setting": "Village marketplace, morning",
    "characters": ["protagonist", "merchant"],
    "summary": "Protagonist visits the market and encounters the mysterious merchant.",
    "start_marker": "The sun was barely...",
    "end_marker": "...walked away troubled.",
    "content": "Full scene text here..."
  }}
]

REMINDER: You must extract between 8 and 20 scenes. Count your scenes before responding.

SCENES:"""

    @staticmethod
    def get_scene_analysis_prompt() -> str:
        """Prompt for Stage 4A: Detailed Scene Analysis"""
        return """You are a literary analysis expert specializing in deep scene examination. Analyze the provided scene for plot elements, character development, themes, and narrative techniques.

SCENE TO ANALYZE:
Title: {scene_title}
Setting: {scene_setting}
Characters: {scene_characters}

SCENE CONTENT:
{scene_content}

ANALYSIS AREAS:
1. Plot Function: How does this scene advance the overall story?
2. Character Development: What do we learn about characters?
3. Conflict: What tensions or conflicts are present?
4. Themes: What thematic elements emerge?
5. Foreshadowing: Any hints about future events?
6. World Building: Setting details and atmosphere
7. Dialogue Quality: Character voice and subtext
8. Pacing: Scene rhythm and flow

OUTPUT FORMAT (JSON):
{{
  "plot_function": "Detailed analysis of plot advancement",
  "character_development": {{
    "character_name": "What we learn about this character",
    "another_character": "Development details"
  }},
  "conflicts": ["List of conflicts present"],
  "themes": ["Thematic elements identified"],
  "foreshadowing": ["Future hints discovered"],
  "world_building": "Setting and atmosphere details",
  "dialogue_analysis": "Quality and character voice assessment",
  "pacing_notes": "Rhythm and flow observations",
  "overall_significance": "Scene's importance to the story"
}}

ANALYSIS:"""

    @staticmethod
    def get_graph_analysis_prompt() -> str:
        """Prompt for Stage 4B: Graph Relationship Analysis"""
        return """You are a narrative relationship specialist. Extract and analyze all character relationships, locations, and objects from the provided scene to build a knowledge graph.

PROGRESSIVE STORY CONTEXT:
{progressive_summary}

CURRENT SCENE:
{scene_content}

EXTRACTION REQUIREMENTS:

CHARACTERS:
- Identify all named characters and significant unnamed characters
- Note character traits, roles, and development
- Track emotional states and motivations

RELATIONSHIPS:
- Character interactions (speaks to, fights with, helps, etc.)
- Family/romantic/friendship connections
- Power dynamics and hierarchies

LOCATIONS:
- Specific places mentioned
- Geographic relationships between locations
- Setting atmosphere and significance

OBJECTS/ITEMS:
- Important items mentioned
- Who owns/uses/finds/loses items
- Symbolic or plot-significant objects

OUTPUT FORMAT (JSON):
{{
  "characters": [
    {{
      "name": "Character Name",
      "type": "CHARACTER",
      "traits": ["brave", "intelligent"],
      "role": "protagonist",
      "emotional_state": "determined"
    }}
  ],
  "locations": [
    {{
      "name": "Location Name",
      "type": "LOCATION",
      "description": "Physical description",
      "atmosphere": "mood/feeling"
    }}
  ],
  "objects": [
    {{
      "name": "Object Name",
      "type": "ITEM",
      "description": "Physical description",
      "significance": "plot importance"
    }}
  ],
  "relationships": [
    {{
      "source": "Character A",
      "target": "Character B",
      "relationship": "INTERACTS_WITH",
      "context": "How they interact",
      "emotional_tone": "friendly/hostile/neutral"
    }}
  ]
}}

GRAPH DATA:"""

    @staticmethod
    def get_character_report_prompt() -> str:
        """Prompt for Stage 4C: Character Analysis Reports"""
        return """You are a character analysis expert. Create a comprehensive character profile based on all available scene data and relationship information.

CHARACTER TO ANALYZE: {character_name}

SCENE APPEARANCES:
{character_scenes}

RELATIONSHIP DATA:
{character_relationships}

ANALYSIS REQUIREMENTS:
1. Character Arc: How does the character change?
2. Personality Profile: Core traits and characteristics
3. Motivations: What drives this character?
4. Relationships: Key connections with others
5. Role in Story: Function in the narrative
6. Development Potential: Areas for growth
7. Conflicts: Internal and external struggles

OUTPUT FORMAT (JSON):
{{
  "character_name": "{character_name}",
  "character_arc": "Detailed progression through story",
  "personality_profile": {{
    "core_traits": ["trait1", "trait2"],
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "quirks": ["unique characteristics"]
  }},
  "motivations": {{
    "primary": "Main driving force",
    "secondary": ["Other motivating factors"]
  }},
  "key_relationships": [
    {{
      "character": "Other Character",
      "relationship_type": "friend/enemy/family",
      "dynamics": "How they interact"
    }}
  ],
  "narrative_role": "Function in the story",
  "development_potential": "Growth opportunities",
  "conflicts": {{
    "internal": ["Internal struggles"],
    "external": ["External challenges"]
  }},
  "significance_rating": "1-10 scale",
  "recommendations": ["Suggestions for character development"]
}}

CHARACTER ANALYSIS:"""

    @staticmethod
    def get_coherence_check_prompt() -> str:
        """Prompt for Stage 5: Plot Coherence Analysis"""
        return """You are a plot consistency expert. Analyze the provided story data for plot holes, inconsistencies, and narrative issues.

STORY DATA:
{story_summary}

CHARACTER INFORMATION:
{character_data}

SCENE PROGRESSION:
{scene_sequence}

ANALYSIS AREAS:
1. Timeline Consistency: Check for temporal contradictions
2. Character Consistency: Verify character behavior matches established traits
3. Plot Logic: Identify unexplained events or impossible situations
4. Cause and Effect: Ensure proper narrative flow
5. Character Motivation: Verify actions align with established motivations
6. World Building: Check for setting/rule contradictions

SPECIFIC CHECKS:
- Do character personalities remain consistent?
- Are there unexplained character knowledge gaps?
- Do events follow logical progression?
- Are there missing emotional reactions?
- Do consequences match actions?
- Are plot threads properly resolved?

OUTPUT FORMAT (JSON):
{{
  "timeline_issues": [
    {{
      "issue_type": "INCONSISTENCY",
      "description": "Detailed description of the problem",
      "affected_scenes": [1, 5, 8],
      "severity": "low/medium/high",
      "suggested_fix": "How to resolve this issue"
    }}
  ],
  "character_issues": [
    {{
      "issue_type": "PLOT_HOLE",
      "character": "Character Name",
      "description": "Character consistency problem",
      "affected_scenes": [3, 7],
      "severity": "medium",
      "suggested_fix": "Resolution suggestion"
    }}
  ],
  "plot_issues": [
    {{
      "issue_type": "PLOT_HOLE",
      "description": "Logic gap or unexplained event",
      "affected_scenes": [4],
      "severity": "high",
      "suggested_fix": "How to fill the plot hole"
    }}
  ],
  "overall_coherence_score": "1-10 rating",
  "priority_fixes": ["Most important issues to address"]
}}

COHERENCE ANALYSIS:"""

    @staticmethod
    def get_enhancement_prompt() -> str:
        """Prompt for Stage 6: Scene Enhancement"""
        return """You are a creative writing enhancement specialist. Improve the provided scene by addressing identified issues while maintaining the author's voice and story integrity.

ORIGINAL SCENE:
{original_scene}

IDENTIFIED ISSUES:
{scene_issues}

CHARACTER CONTEXT:
{character_information}

PLOT CONTEXT:
{plot_context}

ENHANCEMENT GUIDELINES:
1. Maintain the author's writing style and voice
2. Address all identified plot/character issues
3. Enhance dialogue and character development
4. Improve pacing and narrative flow
5. Add sensory details and atmosphere
6. Strengthen emotional impact
7. Ensure consistency with established story elements

SPECIFIC IMPROVEMENTS:
- Fill any plot holes identified
- Enhance character motivations
- Improve dialogue authenticity
- Add missing emotional reactions
- Strengthen scene transitions
- Enrich setting descriptions

OUTPUT FORMAT:
Provide the enhanced scene as a complete, polished narrative passage. Maintain the same basic structure and events while improving quality and addressing issues.

ENHANCED SCENE:"""

    @staticmethod
    def get_chaptering_prompt() -> str:
        """Prompt for Stage 7: Chapter Organization"""
        return """You are a book structure specialist. Organize the provided manuscript into well-structured chapters with compelling titles and smooth transitions.

MANUSCRIPT TEXT:
{manuscript_text}

SCENE BREAKDOWN:
{scene_information}

CHAPTERING REQUIREMENTS:
1. Create logical chapter breaks based on:
   - Natural story beats
   - Scene groupings
   - Pacing considerations
   - Cliffhangers and hooks
2. Ensure each chapter has:
   - Clear beginning, middle, end
   - Consistent length (adjust as needed)
   - Compelling chapter titles
   - Smooth transitions

TARGET CHAPTER LENGTH: {target_length} words (flexible)
CHAPTERING MODE: {chaptering_mode}

OUTPUT FORMAT (JSON):
{{
  "chapters": [
    {{
      "chapter_number": 1,
      "title": "Compelling Chapter Title",
      "content": "Full chapter text with proper formatting",
      "word_count": 2500,
      "summary": "Brief chapter summary",
      "key_events": ["Major events in this chapter"],
      "cliffhanger": "Yes/No - does it end with suspense?"
    }}
  ],
  "total_word_count": 75000,
  "chapter_count": 30,
  "structure_notes": "Overall organization strategy used"
}}

CHAPTER STRUCTURE:"""

    @staticmethod
    def get_plot_thread_analysis_prompt() -> str:
        """Prompt for analyzing plot threads across scenes"""
        return """You are a plot structure analyst. Identify and track major plot threads throughout the story.

STORY SCENES:
{all_scenes}

ANALYSIS REQUIREMENTS:
1. Identify major plot threads (main plot, subplots)
2. Track thread progression through scenes
3. Note thread interactions and convergences
4. Identify incomplete or abandoned threads
5. Assess thread resolution quality

OUTPUT FORMAT (JSON):
{{
  "plot_threads": [
    {{
      "thread_id": "main_quest",
      "title": "The Hero's Journey",
      "type": "main_plot",
      "scenes": [1, 3, 5, 8, 12],
      "status": "resolved/ongoing/abandoned",
      "resolution_quality": "satisfying/weak/incomplete"
    }}
  ],
  "thread_interactions": [
    {{
      "threads": ["main_quest", "romance_subplot"],
      "interaction_type": "convergence/conflict/support",
      "scene": 8
    }}
  ],
  "recommendations": ["Suggestions for plot thread improvements"]
}}

PLOT ANALYSIS:"""

    @staticmethod
    def get_theme_analysis_prompt() -> str:
        """Prompt for Stage 4C: Theme Analysis Reports"""
        return """You are a literary theme analysis expert. Create a comprehensive thematic analysis based on the theme's appearances throughout the story.

THEME TO ANALYZE: {theme_name}

THEME APPEARANCES:
{theme_scenes}

FREQUENCY: {frequency} scenes

ANALYSIS REQUIREMENTS:
1. Thematic Significance: What does this theme represent?
2. Symbolic Meaning: How is the theme symbolized in the narrative?
3. Character Connection: Which characters embody or challenge this theme?
4. Narrative Function: How does this theme drive the plot?
5. Evolution: How does the theme develop throughout the story?
6. Literary Techniques: How is the theme conveyed (metaphor, symbolism, etc.)?

Provide your analysis in JSON format:
{{
  "theme_name": "{theme_name}",
  "significance": "Overall importance and meaning",
  "symbolic_meaning": "What the theme symbolizes",
  "character_connections": ["Character names who relate to this theme"],
  "narrative_function": "How it drives the story",
  "evolution": "How it changes throughout the narrative",
  "literary_techniques": ["Techniques used to convey the theme"],
  "thematic_statement": "Central message or insight"
}}

THEME ANALYSIS:"""

    @staticmethod
    def get_setting_analysis_prompt() -> str:
        """Prompt for Stage 4C: Setting Analysis Reports"""
        return """You are a setting and world-building analysis expert. Create a comprehensive analysis of how this setting functions in the narrative.

SETTING TO ANALYZE: {setting_name}

SETTING SCENES:
{setting_scenes}

CHARACTERS PRESENT: {characters_present}

ANALYSIS REQUIREMENTS:
1. Atmosphere: What mood or feeling does this setting create?
2. Symbolic Function: What does this place represent thematically?
3. Character Relationships: How do characters interact with this space?
4. Plot Function: How does this setting advance the story?
5. World-building: What does this reveal about the story's world?
6. Sensory Details: How is the setting described to the reader?

Provide your analysis in JSON format:
{{
  "setting_name": "{setting_name}",
  "atmosphere": "Mood and emotional tone",
  "symbolic_function": "What the setting represents",
  "character_interactions": "How characters relate to this space",
  "plot_function": "How it advances the story",
  "world_building_significance": "What it reveals about the world",
  "sensory_descriptions": ["Key sensory details"],
  "narrative_importance": "Overall significance to the story"
}}

SETTING ANALYSIS:"""

    @staticmethod
    def get_individual_plot_thread_prompt() -> str:
        """Prompt for Stage 4C: Individual Plot Thread Analysis"""
        return """You are a plot structure analysis expert. Analyze this specific recurring plot element and its development throughout the narrative.

PLOT THREAD DESCRIPTION: {plot_description}

AFFECTED SCENES:
{affected_scenes}

FREQUENCY: {thread_frequency} scenes

ANALYSIS REQUIREMENTS:
1. Thread Type: Is this a conflict, mystery, relationship arc, or other type?
2. Character Involvement: Which characters are central to this thread?
3. Development: How does this thread evolve across scenes?
4. Resolution Status: Is this thread resolved, ongoing, or abandoned?
5. Narrative Importance: How critical is this to the overall story?
6. Interconnections: How does this connect to other plot elements?

Provide your analysis in JSON format:
{{
  "thread_type": "Type of plot thread (conflict/mystery/relationship/etc.)",
  "central_characters": ["Characters involved in this thread"],
  "development_arc": "How the thread progresses",
  "resolution_status": "resolved/ongoing/abandoned/unclear",
  "narrative_importance": "high/medium/low",
  "interconnections": ["Other plot elements this connects to"],
  "turning_points": ["Key moments in this thread's development"],
  "thematic_significance": "What themes this thread explores"
}}

PLOT THREAD ANALYSIS:"""
"""
In-memory story context for the novel writer pipeline.
Aggregates Phase 1 (deconstructor) and Phase 2 (style analyzer) outputs
into a unified data structure for prose generation.

Rebuilt from database tables each pipeline run - not persisted.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class CharacterProfile:
    """Merged character profile from analysis reports, graph data, and scene analysis."""
    name: str
    traits: List[str] = field(default_factory=list)
    role: str = ""
    arc_summary: str = ""
    motivations: Dict[str, Any] = field(default_factory=dict)
    relationships: List[Dict[str, str]] = field(default_factory=list)
    first_appearance_scene: int = 0
    scenes_present: List[int] = field(default_factory=list)
    graph_properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LocationProfile:
    """Merged location profile from analysis reports and graph data."""
    name: str
    description: str = ""
    atmosphere: str = ""
    significance: str = ""
    scenes_present: List[int] = field(default_factory=list)
    graph_properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedChapter:
    """Holds a generated chapter's content and metadata during pipeline execution."""
    chapter_number: int
    title: str
    content: str
    word_count: int
    summary: str = ""
    source_scenes: List[int] = field(default_factory=list)


class StoryContext:
    """
    Central data structure aggregating all inputs for novel generation.

    Built in Stage 1 (EntityProfilingStage) from:
    - scenes table (deconstructor)
    - chapters table (deconstructor)
    - analysis_reports table (deconstructor)
    - plot_issues table (deconstructor)
    - author_styles table (style_analyzer)
    - Apache AGE graph (character/location/relationship vertices)

    Consumed by Stages 2-5 for generation, assessment, and assembly.
    """

    def __init__(self):
        # From deconstructor - scenes and chapters
        self.scenes: List[Dict[str, Any]] = []
        self.chapters: List[Dict[str, Any]] = []

        # Merged entity profiles
        self.character_profiles: Dict[str, CharacterProfile] = {}
        self.location_profiles: Dict[str, LocationProfile] = {}

        # From graph database
        self.relationships: List[Dict[str, Any]] = []

        # From analysis reports
        self.themes: List[Dict[str, Any]] = []
        self.plot_threads: List[Dict[str, Any]] = []
        self.narrative_overview: Dict[str, Any] = {}
        self.plot_issues: List[Dict[str, Any]] = []

        # From style analyzer (optional)
        self.author_style = None  # AuthorStyle Pydantic model or None
        self.writing_perspective: str = "third_person_limited"

        # Built during Stage 2 (Prose Generation)
        self.generated_chapters: Dict[int, GeneratedChapter] = {}

    def get_chapter_context(self, chapter_number: int) -> Dict[str, Any]:
        """
        Get all context needed for generating a specific chapter.

        Returns a dict with scenes, character profiles, location profiles,
        previous chapter summaries, active plot threads, and chapter position info.
        """
        if not self.chapters:
            return {}

        chapter_idx = chapter_number - 1
        if chapter_idx < 0 or chapter_idx >= len(self.chapters):
            return {}

        chapter = self.chapters[chapter_idx]
        start_scene = chapter.get('start_scene', 1)
        end_scene = chapter.get('end_scene', start_scene)

        # Scenes for this chapter
        chapter_scenes = [
            s for s in self.scenes
            if start_scene <= s.get('scene_number', 0) <= end_scene
        ]

        # Characters appearing in these scenes
        chapter_character_names = set()
        for scene in chapter_scenes:
            chars = scene.get('characters', [])
            if isinstance(chars, list):
                chapter_character_names.update(chars)
            elif isinstance(chars, str):
                chapter_character_names.add(chars)

        chapter_characters = {
            name: self.character_profiles[name]
            for name in chapter_character_names
            if name in self.character_profiles
        }

        # Locations mentioned in these scenes
        chapter_location_names = set()
        for scene in chapter_scenes:
            setting = scene.get('setting', '')
            if setting:
                chapter_location_names.add(setting)

        chapter_locations = {
            name: self.location_profiles[name]
            for name in chapter_location_names
            if name in self.location_profiles
        }

        # Previous chapter summaries for continuity (last 3)
        prev_summaries = []
        for prev_num in sorted(self.generated_chapters.keys()):
            if prev_num < chapter_number:
                gc = self.generated_chapters[prev_num]
                prev_summaries.append({
                    'chapter': prev_num,
                    'title': gc.title,
                    'summary': gc.summary
                })
        prev_summaries = prev_summaries[-3:]

        # Active plot threads in scene range
        active_threads = self._get_active_threads(start_scene, end_scene)

        return {
            'chapter': chapter,
            'scenes': chapter_scenes,
            'characters': chapter_characters,
            'locations': chapter_locations,
            'previous_summaries': prev_summaries,
            'active_plot_threads': active_threads,
            'chapter_position': {
                'is_first': chapter_number == 1,
                'is_last': chapter_number == len(self.chapters),
                'current': chapter_number,
                'total_chapters': len(self.chapters)
            }
        }

    def _get_active_threads(self, start_scene: int, end_scene: int) -> List[Dict[str, Any]]:
        """Get plot threads active in the given scene range."""
        active = []
        for thread in self.plot_threads:
            content = thread.get('content_json', {})
            if isinstance(content, str):
                import json
                try:
                    content = json.loads(content)
                except (json.JSONDecodeError, TypeError):
                    content = {}
            # Include thread if it mentions scenes in our range or has no scene data
            thread_scenes = content.get('scenes', [])
            if not thread_scenes or any(start_scene <= s <= end_scene for s in thread_scenes):
                active.append(thread)
        return active

    def get_all_character_names(self) -> List[str]:
        """Get all character names from profiles."""
        return list(self.character_profiles.keys())

    def get_all_location_names(self) -> List[str]:
        """Get all location names from profiles."""
        return list(self.location_profiles.keys())

    def get_total_scene_count(self) -> int:
        """Get total number of scenes."""
        return len(self.scenes)

    def get_total_chapter_count(self) -> int:
        """Get total number of chapters."""
        return len(self.chapters)

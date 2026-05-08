"""
Stage 1: Entity Profiling for the novel writer pipeline.
Loads all Phase 1 (deconstructor) and Phase 2 (style analyzer) outputs
into a StoryContext object. Pure data aggregation - zero LLM calls.
"""

import json
import logging
from typing import Dict, Any, List, Optional

from .base_stage import BasePipelineStage, PipelineStageContext, PipelineStageResult
from .rewrite_policy import compile_rewrite_policy
from .story_context import StoryContext, CharacterProfile, LocationProfile

logger = logging.getLogger(__name__)


class EntityProfilingStage(BasePipelineStage):
    """
    Stage 1: Load all input data and build entity profiles.

    Reads from:
    - scenes table (deconstructor)
    - chapters table (deconstructor)
    - analysis_reports table (deconstructor)
    - plot_issues table (deconstructor)
    - author_styles table (style analyzer)
    - Apache AGE graph (characters, locations, relationships)

    Produces: StoryContext stored in context.metadata['story_context']
    """

    def __init__(self, db_pool, generation_engine=None, graph_service=None):
        super().__init__(db_pool, "EntityProfilingStage", generation_engine)
        self.graph_service = graph_service
        self._author_styles_supports_v2_schema: Optional[bool] = None

    def _supports_author_style_v2_schema(self) -> bool:
        if self._author_styles_supports_v2_schema is not None:
            return self._author_styles_supports_v2_schema

        try:
            from src.utils.database_utils import utf8_database_connection

            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'author_styles'
                      AND column_name IN ('schema_version', 'adaptation_json')
                    """
                )
                columns = {row[0] for row in cursor.fetchall()}
                self._author_styles_supports_v2_schema = {
                    'schema_version',
                    'adaptation_json',
                }.issubset(columns)
        except Exception as e:
            self.logger.warning(
                f"Failed to inspect author_styles schema; assuming legacy layout: {e}"
            )
            self._author_styles_supports_v2_schema = False

        return self._author_styles_supports_v2_schema

    def _execute_stage(self, context: PipelineStageContext) -> PipelineStageResult:
        draft_id = context.draft_id
        workspace_id = context.get_workspace_id(self.db_pool)
        author_style_name = context.config.get('author_style_name')
        writing_perspective = context.config.get('writing_perspective', 'third_person_limited')
        rewrite_policy = context.config.get('rewrite_policy', {})

        story_context = StoryContext()
        story_context.writing_perspective = writing_perspective
        story_context.rewrite_policy = rewrite_policy
        conn = context.get('connection')

        try:
            # Use pipeline connection if available, otherwise get from pool
            if conn:
                cursor = conn.cursor()
                self._load_all_data(cursor, draft_id, workspace_id, author_style_name, story_context)
                cursor.close()
            else:
                from src.utils.database_utils import utf8_database_connection
                with utf8_database_connection(self.db_pool) as db_conn:
                    cursor = db_conn.cursor()
                    self._load_all_data(cursor, draft_id, workspace_id, author_style_name, story_context)
                    cursor.close()

            # Load graph data (uses its own connection management)
            self._load_graph_data(draft_id, story_context)

            # Merge entity profiles from multiple sources
            self._merge_character_profiles(story_context)
            self._merge_location_profiles(story_context)

            # Validate minimum requirements
            if not story_context.scenes:
                return PipelineStageResult.error_result(
                    self.stage_name,
                    error=f"No scenes found for draft {draft_id}. Deconstructor must complete first."
                )

            if not story_context.chapters:
                return PipelineStageResult.error_result(
                    self.stage_name,
                    error=f"No chapters found for draft {draft_id}. Deconstructor chaptering must complete first."
                )

            if story_context.author_style is None:
                self.logger.warning(
                    f"No author style found for workspace {workspace_id}. "
                    "Generation will proceed without style guidance."
                )

            story_context.compiled_rewrite_policy = compile_rewrite_policy(
                rewrite_policy,
                story_context.author_style,
            )

            # Store in context for downstream stages
            context.set('story_context', story_context)

            return PipelineStageResult.success_result(
                self.stage_name,
                scenes_loaded=len(story_context.scenes),
                chapters_loaded=len(story_context.chapters),
                characters_profiled=len(story_context.character_profiles),
                locations_profiled=len(story_context.location_profiles),
                relationships_loaded=len(story_context.relationships),
                themes_loaded=len(story_context.themes),
                plot_threads_loaded=len(story_context.plot_threads),
                plot_issues_loaded=len(story_context.plot_issues),
                has_author_style=story_context.author_style is not None,
                has_narrative_overview=bool(story_context.narrative_overview),
            )

        except Exception as e:
            self.logger.error(f"Entity profiling failed for draft {draft_id}: {e}")
            return PipelineStageResult.error_result(
                self.stage_name,
                error=str(e)
            )

    def _load_all_data(self, cursor, draft_id: str, workspace_id: str,
                       author_style_name: Optional[str], story_context: StoryContext) -> None:
        """Load all relational data from DB into story_context."""
        self._load_scenes(cursor, draft_id, story_context)
        self._load_chapters(cursor, draft_id, story_context)
        self._load_analysis_reports(cursor, draft_id, story_context)
        self._load_plot_issues(cursor, draft_id, story_context)
        self._load_author_style(cursor, workspace_id, author_style_name, story_context)

    def _load_scenes(self, cursor, draft_id: str, story_context: StoryContext) -> None:
        """Load all scenes for the draft."""
        cursor.execute("""
            SELECT id, scene_number, title, summary, setting, characters,
                   original_content, analysis_json, enhanced_content
            FROM scenes
            WHERE draft_id = %s
            ORDER BY scene_number
        """, (draft_id,))

        for row in cursor.fetchall():
            scene = {
                'id': row[0],
                'scene_number': row[1],
                'title': row[2],
                'summary': row[3],
                'setting': row[4],
                'characters': self._parse_json_field(row[5], default=[]),
                'original_content': row[6],
                'analysis_json': self._parse_json_field(row[7], default={}),
                'enhanced_content': row[8],
            }
            story_context.scenes.append(scene)

        self.logger.info(f"Loaded {len(story_context.scenes)} scenes for draft {draft_id}")

    def _load_chapters(self, cursor, draft_id: str, story_context: StoryContext) -> None:
        """Load chapter structure from deconstructor."""
        cursor.execute("""
            SELECT id, chapter_number, title, word_count,
                   start_scene, end_scene, scene_count, scene_titles
            FROM chapters
            WHERE draft_id = %s
            ORDER BY chapter_number
        """, (draft_id,))

        for row in cursor.fetchall():
            chapter = {
                'id': row[0],
                'chapter_number': row[1],
                'title': row[2],
                'word_count': row[3],
                'start_scene': row[4],
                'end_scene': row[5],
                'scene_count': row[6],
                'scene_titles': self._parse_json_field(row[7], default=[]),
            }
            story_context.chapters.append(chapter)

        self.logger.info(f"Loaded {len(story_context.chapters)} chapters for draft {draft_id}")

    def _load_analysis_reports(self, cursor, draft_id: str, story_context: StoryContext) -> None:
        """Load analysis reports and categorize by type."""
        cursor.execute("""
            SELECT id, report_type, report_subject, content_json
            FROM analysis_reports
            WHERE draft_id = %s
        """, (draft_id,))

        character_reports = []
        theme_reports = []
        setting_reports = []
        plot_thread_reports = []
        narrative_overview = {}

        for row in cursor.fetchall():
            report = {
                'id': row[0],
                'report_type': row[1],
                'report_subject': row[2],
                'content_json': self._parse_json_field(row[3], default={}),
            }

            report_type = row[1]
            if report_type == 'CHARACTER_ARC':
                character_reports.append(report)
            elif report_type == 'THEME_ANALYSIS':
                theme_reports.append(report)
            elif report_type == 'SETTING_ANALYSIS':
                setting_reports.append(report)
            elif report_type == 'PLOT_THREAD':
                plot_thread_reports.append(report)
            elif report_type == 'NARRATIVE_OVERVIEW':
                narrative_overview = report.get('content_json', {})

        # Store categorized reports
        story_context.themes = theme_reports
        story_context.plot_threads = plot_thread_reports
        story_context.narrative_overview = narrative_overview

        # Character and setting reports stored temporarily for merging
        story_context._raw_character_reports = character_reports
        story_context._raw_setting_reports = setting_reports

        total = len(character_reports) + len(theme_reports) + len(setting_reports) + len(plot_thread_reports)
        self.logger.info(
            f"Loaded {total} analysis reports for draft {draft_id}: "
            f"{len(character_reports)} character, {len(theme_reports)} theme, "
            f"{len(setting_reports)} setting, {len(plot_thread_reports)} plot thread"
        )

    def _load_plot_issues(self, cursor, draft_id: str, story_context: StoryContext) -> None:
        """Load plot issues identified by the deconstructor."""
        cursor.execute("""
            SELECT id, affected_scene_id, issue_type, description, severity, suggested_fix
            FROM plot_issues
            WHERE draft_id = %s
        """, (draft_id,))

        for row in cursor.fetchall():
            issue = {
                'id': row[0],
                'affected_scene_id': row[1],
                'issue_type': row[2],
                'description': row[3],
                'severity': row[4],
                'suggested_fix': row[5],
            }
            story_context.plot_issues.append(issue)

        self.logger.info(f"Loaded {len(story_context.plot_issues)} plot issues for draft {draft_id}")

    def _load_author_style(self, cursor, workspace_id: str,
                           author_style_name: Optional[str], story_context: StoryContext) -> None:
        """Load author style profile from style analyzer."""
        try:
            legacy_schema = not self._supports_author_style_v2_schema()

            if not legacy_schema:
                if author_style_name:
                    cursor.execute("""
                        SELECT schema_version, techniques_json, examples_json, adaptation_json
                        FROM author_styles
                        WHERE workspace_id = %s AND author_name = %s
                          AND status = 'profiling_completed' AND schema_version = 2
                        ORDER BY updated_at DESC
                        LIMIT 1
                    """, (workspace_id, author_style_name))
                else:
                    cursor.execute("""
                        SELECT schema_version, techniques_json, examples_json, adaptation_json
                        FROM author_styles
                        WHERE workspace_id = %s AND status = 'profiling_completed' AND schema_version = 2
                        ORDER BY updated_at DESC
                        LIMIT 1
                    """, (workspace_id,))
            else:
                if author_style_name:
                    cursor.execute("""
                        SELECT techniques_json, examples_json
                        FROM author_styles
                        WHERE workspace_id = %s AND author_name = %s
                          AND status = 'profiling_completed'
                        ORDER BY updated_at DESC
                        LIMIT 1
                    """, (workspace_id, author_style_name))
                else:
                    cursor.execute("""
                        SELECT techniques_json, examples_json
                        FROM author_styles
                        WHERE workspace_id = %s AND status = 'profiling_completed'
                        ORDER BY updated_at DESC
                        LIMIT 1
                    """, (workspace_id,))

            row = cursor.fetchone()
            if row:
                if legacy_schema:
                    schema_version = 2
                    techniques_json = self._parse_json_field(row[0], default={})
                    examples_json = self._parse_json_field(row[1], default={})
                    adaptation_json = {}
                else:
                    schema_version = int(row[0] or 0)
                    if schema_version != 2:
                        self.logger.warning(
                            f"Author style schema_version={schema_version} is incompatible; re-profiling required."
                        )
                        return
                    techniques_json = self._parse_json_field(row[1], default={})
                    examples_json = self._parse_json_field(row[2], default={})
                    adaptation_json = self._parse_json_field(row[3], default={})

                from src.models.style_analyzer.author_style import AuthorStyle
                story_context.author_style = AuthorStyle(
                    schema_version=schema_version,
                    techniques=techniques_json,
                    examples=examples_json,
                    adaptation=adaptation_json,
                )
                self.logger.info(f"Loaded author style for workspace {workspace_id}")
            else:
                self.logger.warning(f"No completed author style found for workspace {workspace_id}")

        except Exception as e:
            self.logger.warning(f"Failed to load author style: {e}. Continuing without style.")

    def _load_graph_data(self, draft_id: str, story_context: StoryContext) -> None:
        """Load graph data from Apache AGE (graceful degradation)."""
        if not self.graph_service:
            self.logger.info("Graph service not available, skipping graph data loading")
            return

        try:
            # Load character vertices
            characters = self.graph_service.get_character_vertices(draft_id)
            story_context._raw_graph_characters = characters
            self.logger.info(f"Loaded {len(characters)} character vertices from graph")

            # Load location vertices
            locations = self.graph_service.get_location_vertices(draft_id)
            story_context._raw_graph_locations = locations
            self.logger.info(f"Loaded {len(locations)} location vertices from graph")

            # Load relationships
            relationships = self.graph_service.get_draft_relationships(draft_id)
            story_context.relationships = relationships
            self.logger.info(f"Loaded {len(relationships)} relationships from graph")

        except Exception as e:
            self.logger.warning(f"Failed to load graph data: {e}. Continuing without graph data.")
            story_context._raw_graph_characters = []
            story_context._raw_graph_locations = []

    def _merge_character_profiles(self, story_context: StoryContext) -> None:
        """Merge character data from analysis reports, graph, and scene data."""
        profiles = {}

        # From analysis reports (CHARACTER_ARC)
        for report in getattr(story_context, '_raw_character_reports', []):
            name = report.get('report_subject', '')
            if not name:
                continue
            content = report.get('content_json', {})
            profiles[name] = CharacterProfile(
                name=name,
                traits=content.get('traits', []),
                role=content.get('role', ''),
                arc_summary=content.get('arc_summary', content.get('summary', '')),
                motivations=content.get('motivations', {}),
            )

        # From graph vertices (merge or create)
        for vertex in getattr(story_context, '_raw_graph_characters', []):
            name = vertex.get('name', '')
            if not name:
                continue
            props = vertex.get('properties', {})
            if isinstance(props, str):
                try:
                    props = json.loads(props)
                except (json.JSONDecodeError, TypeError):
                    props = {}

            if name in profiles:
                profiles[name].graph_properties = props
            else:
                profiles[name] = CharacterProfile(
                    name=name,
                    graph_properties=props,
                )

        # From scene character lists (track appearances)
        for scene in story_context.scenes:
            scene_num = scene.get('scene_number', 0)
            characters = scene.get('characters', [])
            if isinstance(characters, str):
                characters = [characters]

            for char_name in characters:
                if not char_name:
                    continue
                if char_name in profiles:
                    profiles[char_name].scenes_present.append(scene_num)
                    if not profiles[char_name].first_appearance_scene:
                        profiles[char_name].first_appearance_scene = scene_num
                else:
                    profiles[char_name] = CharacterProfile(
                        name=char_name,
                        first_appearance_scene=scene_num,
                        scenes_present=[scene_num],
                    )

        # Add relationship data
        for rel in story_context.relationships:
            source = rel.get('source', '')
            target = rel.get('target', '')
            rel_type = rel.get('relationship_type', '')

            if source in profiles:
                profiles[source].relationships.append({
                    'target': target,
                    'type': rel_type,
                    'properties': rel.get('properties', {}),
                })

        story_context.character_profiles = profiles

        # Clean up temporary attributes
        for attr in ('_raw_character_reports', '_raw_graph_characters'):
            if hasattr(story_context, attr):
                delattr(story_context, attr)

    def _merge_location_profiles(self, story_context: StoryContext) -> None:
        """Merge location data from analysis reports, graph, and scene data."""
        profiles = {}

        # From analysis reports (SETTING_ANALYSIS)
        for report in getattr(story_context, '_raw_setting_reports', []):
            name = report.get('report_subject', '')
            if not name:
                continue
            content = report.get('content_json', {})
            profiles[name] = LocationProfile(
                name=name,
                description=content.get('description', ''),
                atmosphere=content.get('atmosphere', ''),
                significance=content.get('significance', ''),
            )

        # From graph vertices
        for vertex in getattr(story_context, '_raw_graph_locations', []):
            name = vertex.get('name', '')
            if not name:
                continue
            props = vertex.get('properties', {})
            if isinstance(props, str):
                try:
                    props = json.loads(props)
                except (json.JSONDecodeError, TypeError):
                    props = {}

            if name in profiles:
                profiles[name].graph_properties = props
            else:
                profiles[name] = LocationProfile(
                    name=name,
                    graph_properties=props,
                )

        # From scene settings (track appearances)
        for scene in story_context.scenes:
            scene_num = scene.get('scene_number', 0)
            setting = scene.get('setting', '')
            if setting:
                if setting in profiles:
                    profiles[setting].scenes_present.append(scene_num)
                else:
                    profiles[setting] = LocationProfile(
                        name=setting,
                        scenes_present=[scene_num],
                    )

        story_context.location_profiles = profiles

        # Clean up temporary attributes
        for attr in ('_raw_setting_reports', '_raw_graph_locations'):
            if hasattr(story_context, attr):
                delattr(story_context, attr)

    def _parse_json_field(self, value, default=None):
        """Safely parse a JSON field that may be a string, dict, list, or None."""
        if value is None:
            return default
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return default
        return default

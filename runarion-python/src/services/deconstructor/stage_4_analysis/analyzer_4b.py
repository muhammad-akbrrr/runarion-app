"""
Stage 4B: Progressive Graph Analysis
Builds knowledge graph using Apache AGE to map character relationships and story elements.
"""

import json
import logging
import os
from typing import Dict, Any, List, Tuple, Optional
from ..prompt_template import DeconstructorPrompts
from utils.database_utils import utf8_database_connection, clean_text_for_database, ensure_utf8_json

logger = logging.getLogger(__name__)

class ProgressiveGraphAnalysisStage:
    """
    Stage 4B of the deconstruction pipeline.
    Builds progressive knowledge graph using Apache AGE for relationship analysis.
    """
    
    def __init__(self, db_pool, generation_engine):
        """
        Initialize the graph analysis stage.
        
        Args:
            db_pool: Database connection pool
            generation_engine: AI generation engine
        """
        self.db_pool = db_pool
        self.generation_engine = generation_engine
        self.prompt_template = DeconstructorPrompts()
        self.age_enabled = os.getenv('AGE_ENABLED', 'true').lower() == 'true'
        self.graph_name = os.getenv('AGE_GRAPH_NAME', 'novel_pipeline_graph')
    
    def run(self, draft_id: str, chaptering_mode: str = 'flexible', target_chapter_length: int = 2500) -> Dict[str, Any]:
        """
        Execute Stage 4B: Progressive graph analysis.
        
        Args:
            draft_id: UUID of the draft
            chaptering_mode: Chaptering approach ('flexible' or 'constrained')
            target_chapter_length: Target word count per chapter
            
        Returns:
            Stage execution results
        """
        logger.info(f"Starting Stage 4B graph analysis for draft {draft_id} (chaptering_mode: {chaptering_mode}, target_length: {target_chapter_length})")
        
        # Store chaptering parameters for later stages
        self._store_chaptering_metadata(draft_id, chaptering_mode, target_chapter_length)
        
        try:
            # Check if AGE is available
            if not self.age_enabled:
                logger.warning("Apache AGE disabled, using fallback storage")
                return self._run_fallback_analysis(draft_id)
            
            # Get scenes for processing
            scenes = self._get_draft_scenes(draft_id)
            
            if not scenes:
                logger.warning(f"No scenes found for draft {draft_id}")
                return {
                    'success': True,
                    'entities_created': 0,
                    'relationships_created': 0,
                    'message': 'No scenes to analyze'
                }
            
            # Initialize progressive summary
            progressive_summary = ""
            total_entities = 0
            total_relationships = 0
            
            # Process scenes in batches
            batch_size = 5
            scene_batches = [scenes[i:i + batch_size] for i in range(0, len(scenes), batch_size)]
            
            for batch_num, scene_batch in enumerate(scene_batches):
                logger.info(f"Processing scene batch {batch_num + 1}/{len(scene_batches)} for draft {draft_id}")
                
                # Analyze batch and extract entities/relationships
                batch_data = self._analyze_scene_batch(scene_batch, progressive_summary)
                
                if batch_data:
                    # Store entities and relationships in graph
                    entities_created, relationships_created = self._store_graph_data(
                        draft_id, batch_data
                    )
                    
                    total_entities += entities_created
                    total_relationships += relationships_created
                    
                    # Update progressive summary
                    progressive_summary = self._update_progressive_summary(
                        progressive_summary, scene_batch, batch_data
                    )
            
            result = {
                'success': True,
                'scenes_processed': len(scenes),
                'entities_created': total_entities,
                'relationships_created': total_relationships,
                'batches_processed': len(scene_batches),
                'chaptering_mode': chaptering_mode,
                'target_chapter_length': target_chapter_length
            }
            
            logger.info(f"Stage 4B completed for draft {draft_id}: {total_entities} entities, {total_relationships} relationships")
            return result
            
        except Exception as e:
            logger.error(f"Stage 4B failed for draft {draft_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'draft_id': draft_id
            }
    
    def _run_fallback_analysis(self, draft_id: str) -> Dict[str, Any]:
        """
        Run analysis without Apache AGE using relational tables.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Fallback analysis results
        """
        logger.info(f"Running fallback graph analysis for draft {draft_id}")
        
        try:
            scenes = self._get_draft_scenes(draft_id)
            
            if not scenes:
                return {
                    'success': True,
                    'entities_created': 0,
                    'relationships_created': 0,
                    'message': 'No scenes to analyze'
                }
            
            # Use relational tables to store graph-like data
            entities_created = 0
            relationships_created = 0
            
            for scene in scenes:
                scene_id, scene_number, title, setting, characters, content, analysis = scene
                
                # Extract basic entities from scene metadata
                try:
                    char_list = json.loads(characters) if characters else []
                    for char in char_list:
                        self._store_fallback_entity(draft_id, char, 'CHARACTER', scene_id)
                        entities_created += 1
                    
                    # Store setting as location
                    if setting:
                        self._store_fallback_entity(draft_id, setting, 'LOCATION', scene_id)
                        entities_created += 1
                        
                except Exception as e:
                    logger.warning(f"Error processing scene {scene_number}: {e}")
            
            return {
                'success': True,
                'scenes_processed': len(scenes),
                'entities_created': entities_created,
                'relationships_created': relationships_created,
                'mode': 'fallback'
            }
            
        except Exception as e:
            logger.error(f"Fallback analysis failed for draft {draft_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'draft_id': draft_id
            }
    
    def _store_chaptering_metadata(self, draft_id: str, chaptering_mode: str, target_chapter_length: int) -> None:
        """
        Store chaptering parameters in draft metadata for later stages.
        
        Args:
            draft_id: UUID of the draft
            chaptering_mode: Chaptering approach
            target_chapter_length: Target word count per chapter
        """
        try:
            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()
                
                # Get current metadata
                cursor.execute("SELECT metadata FROM drafts WHERE id = %s", (draft_id,))
                result = cursor.fetchone()
                
                current_metadata = {}
                if result and result[0]:
                    try:
                        current_metadata = json.loads(result[0])
                    except json.JSONDecodeError:
                        current_metadata = {}
                
                # Update with chaptering parameters
                current_metadata.update({
                    'chaptering_mode': chaptering_mode,
                    'target_chapter_length': target_chapter_length,
                    'stage_4b_completed': True
                })
                
                # Store updated metadata
                metadata_json = ensure_utf8_json(current_metadata)
                cursor.execute(
                    "UPDATE drafts SET metadata = %s WHERE id = %s",
                    (metadata_json, draft_id)
                )
                
                conn.commit()
                logger.debug(f"Stored chaptering metadata for draft {draft_id}")
                
        except Exception as e:
            logger.error(f"Failed to store chaptering metadata for draft {draft_id}: {e}")
            raise

    def _get_draft_scenes(self, draft_id: str) -> List[Tuple]:
        """
        Retrieve scenes for graph analysis with UTF-8 safety.
        """
        try:
            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, scene_number, title, setting, characters, 
                           original_content, analysis_json
                    FROM scenes 
                    WHERE draft_id = %s
                    ORDER BY scene_number
                """, (draft_id,))
                
                scenes = cursor.fetchall()
            
            logger.debug(f"Retrieved {len(scenes)} scenes for graph analysis in draft {draft_id} (UTF-8 safe)")
            return scenes
            
        except Exception as e:
            logger.error(f"Failed to retrieve scenes for draft {draft_id}: {e}")
            raise
    
    def _analyze_scene_batch(self, scene_batch: List[Tuple], progressive_summary: str) -> Optional[Dict[str, Any]]:
        """
        Analyze a batch of scenes for entities and relationships.
        """
        try:
            # Combine scene content for batch analysis
            batch_content = ""
            for scene in scene_batch:
                scene_id, scene_number, title, setting, characters, content, analysis = scene
                batch_content += f"\n\n--- Scene {scene_number}: {title} ---\n{content}"
            
            # Prepare the graph analysis prompt
            prompt = self.prompt_template.get_graph_analysis_prompt().format(
                progressive_summary=progressive_summary,
                scene_content=batch_content
            )
            
            # Update the generation request
            self.generation_engine.request.prompt = prompt
            self.generation_engine.request.instruction = "Extract entities and relationships for graph database storage."
            
            # Generate graph analysis
            response = self.generation_engine.generate(skip_quota=True)
            
            if not response.success:
                logger.error(f"AI generation failed for scene batch: {response.error_message}")
                return None
            
            # Parse the JSON response
            try:
                graph_data = json.loads(response.text.strip())
                return self._validate_graph_data(graph_data)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse graph analysis JSON: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error analyzing scene batch: {e}")
            return None
    
    def _validate_graph_data(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and structure the graph data.
        """
        validated = {
            'characters': [],
            'locations': [],
            'objects': [],
            'relationships': []
        }
        
        # Validate characters
        for char in graph_data.get('characters', []):
            if isinstance(char, dict) and char.get('name'):
                validated_char = {
                    'name': char['name'],
                    'type': 'CHARACTER',
                    'traits': char.get('traits', []),
                    'role': char.get('role', ''),
                    'emotional_state': char.get('emotional_state', '')
                }
                validated['characters'].append(validated_char)
        
        # Validate locations
        for loc in graph_data.get('locations', []):
            if isinstance(loc, dict) and loc.get('name'):
                validated_loc = {
                    'name': loc['name'],
                    'type': 'LOCATION',
                    'description': loc.get('description', ''),
                    'atmosphere': loc.get('atmosphere', '')
                }
                validated['locations'].append(validated_loc)
        
        # Validate objects
        for obj in graph_data.get('objects', []):
            if isinstance(obj, dict) and obj.get('name'):
                validated_obj = {
                    'name': obj['name'],
                    'type': 'ITEM',
                    'description': obj.get('description', ''),
                    'significance': obj.get('significance', '')
                }
                validated['objects'].append(validated_obj)
        
        # Validate relationships
        for rel in graph_data.get('relationships', []):
            if isinstance(rel, dict) and rel.get('source') and rel.get('target'):
                validated_rel = {
                    'source': rel['source'],
                    'target': rel['target'],
                    'relationship': rel.get('relationship', 'RELATES_TO'),
                    'context': rel.get('context', ''),
                    'emotional_tone': rel.get('emotional_tone', 'neutral')
                }
                validated['relationships'].append(validated_rel)
        
        return validated
    
    def _store_graph_data(self, draft_id: str, graph_data: Dict[str, Any]) -> Tuple[int, int]:
        """
        Store entities and relationships in Apache AGE graph database.
        """
        if not self.age_enabled:
            return self._store_fallback_graph_data(draft_id, graph_data)
        
        try:
            conn = self.db_pool.getconn()
            entities_created = 0
            relationships_created = 0
            
            with conn.cursor() as cursor:
                # Set search path for AGE
                cursor.execute("SET search_path = ag_catalog, public")
                
                # Create vertices for each entity type
                for entity_type, entities in [
                    ('Character', graph_data.get('characters', [])),
                    ('Location', graph_data.get('locations', [])),
                    ('Item', graph_data.get('objects', []))
                ]:
                    for entity in entities:
                        try:
                            properties = {k: v for k, v in entity.items() if k != 'name' and k != 'type'}
                            cursor.execute("""
                                SELECT upsert_novel_vertex(%s, %s, %s, %s)
                            """, (
                                draft_id,
                                entity['name'],
                                entity_type,
                                json.dumps(properties)
                            ))
                            entities_created += 1
                        except Exception as e:
                            logger.error(f"Failed to create {entity_type} vertex {entity['name']}: {e}")
                
                # Create relationships
                for relationship in graph_data.get('relationships', []):
                    try:
                        source_label = self._determine_entity_label(relationship['source'], graph_data)
                        target_label = self._determine_entity_label(relationship['target'], graph_data)
                        
                        relationship_props = {
                            'context': relationship.get('context', ''),
                            'emotional_tone': relationship.get('emotional_tone', 'neutral')
                        }
                        
                        cursor.execute("""
                            SELECT create_novel_relationship(%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            draft_id,
                            relationship['source'],
                            source_label,
                            relationship['target'],
                            target_label,
                            relationship['relationship'],
                            json.dumps(relationship_props)
                        ))
                        relationships_created += 1
                    except Exception as e:
                        logger.error(f"Failed to create relationship: {e}")
                
                conn.commit()
            
            self.db_pool.putconn(conn)
            return entities_created, relationships_created
            
        except Exception as e:
            logger.error(f"Failed to store graph data: {e}")
            if 'conn' in locals():
                conn.rollback()
                self.db_pool.putconn(conn)
            return 0, 0
    
    def _store_fallback_graph_data(self, draft_id: str, graph_data: Dict[str, Any]) -> Tuple[int, int]:
        """
        Store graph data using relational tables when AGE is unavailable.
        """
        try:
            conn = self.db_pool.getconn()
            entities_created = 0
            relationships_created = 0
            
            with conn.cursor() as cursor:
                # Store entities in novel_graph_vertex table
                for entity_type, entities in [
                    ('character', graph_data.get('characters', [])),
                    ('location', graph_data.get('locations', [])),
                    ('item', graph_data.get('objects', []))
                ]:
                    for entity in entities:
                        try:
                            properties = {k: v for k, v in entity.items() if k != 'name' and k != 'type'}
                            cursor.execute("""
                                INSERT INTO novel_graph_vertices (draft_id, entity_type, name, properties)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT (draft_id, entity_type, name) DO UPDATE SET
                                properties = EXCLUDED.properties
                            """, (draft_id, entity_type, entity['name'], json.dumps(properties)))
                            entities_created += 1
                        except Exception as e:
                            logger.error(f"Failed to store {entity_type} entity: {e}")
                
                # Store relationships in novel_graph_edges table
                for relationship in graph_data.get('relationships', []):
                    try:
                        cursor.execute("""
                            INSERT INTO novel_graph_edges (draft_id, source_name, target_name, 
                                                         relationship_type, properties)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            draft_id,
                            relationship['source'],
                            relationship['target'],
                            relationship['relationship'],
                            json.dumps({
                                'context': relationship.get('context', ''),
                                'emotional_tone': relationship.get('emotional_tone', 'neutral')
                            })
                        ))
                        relationships_created += 1
                    except Exception as e:
                        logger.error(f"Failed to store relationship: {e}")
                
                conn.commit()
            
            self.db_pool.putconn(conn)
            return entities_created, relationships_created
            
        except Exception as e:
            logger.error(f"Failed to store fallback graph data: {e}")
            if 'conn' in locals():
                conn.rollback()
                self.db_pool.putconn(conn)
            return 0, 0
    
    def _store_fallback_entity(self, draft_id: str, entity_name: str, entity_type: str, scene_id: int) -> None:
        """
        Store a single entity in fallback mode.
        """
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO novel_graph_vertices (draft_id, entity_type, name, properties)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (draft_id, entity_type, name) DO NOTHING
                """, (draft_id, entity_type.lower(), entity_name, json.dumps({'scene_id': scene_id})))
                
                conn.commit()
            
            self.db_pool.putconn(conn)
            
        except Exception as e:
            logger.error(f"Failed to store fallback entity {entity_name}: {e}")
            if 'conn' in locals():
                self.db_pool.putconn(conn)
    
    def _determine_entity_label(self, entity_name: str, graph_data: Dict[str, Any]) -> str:
        """
        Determine the AGE label for an entity based on graph data.
        """
        # Check characters
        for char in graph_data.get('characters', []):
            if char.get('name') == entity_name:
                return 'Character'
        
        # Check locations
        for loc in graph_data.get('locations', []):
            if loc.get('name') == entity_name:
                return 'Location'
        
        # Check objects
        for obj in graph_data.get('objects', []):
            if obj.get('name') == entity_name:
                return 'Item'
        
        # Default to Character if unknown
        return 'Character'
    
    def _update_progressive_summary(self, current_summary: str, scene_batch: List[Tuple], 
                                   graph_data: Dict[str, Any]) -> str:
        """
        Update the progressive summary with new information.
        """
        # Extract key information from the batch
        new_characters = [char['name'] for char in graph_data.get('characters', [])]
        new_locations = [loc['name'] for loc in graph_data.get('locations', [])]
        scene_numbers = [scene[1] for scene in scene_batch]  # scene_number is index 1
        
        # Create summary update
        summary_update = f"\n\nScenes {min(scene_numbers)}-{max(scene_numbers)}: "
        
        if new_characters:
            summary_update += f"Characters: {', '.join(new_characters[:5])}. "
        
        if new_locations:
            summary_update += f"Locations: {', '.join(new_locations[:3])}. "
        
        # Append to current summary (keep it manageable)
        updated_summary = current_summary + summary_update
        
        # Truncate if too long (keep last 2000 characters)
        if len(updated_summary) > 2000:
            updated_summary = "..." + updated_summary[-1997:]
        
        return updated_summary
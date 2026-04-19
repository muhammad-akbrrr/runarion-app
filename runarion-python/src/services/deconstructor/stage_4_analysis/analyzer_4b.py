"""
Stage 4B: Progressive Graph Analysis
Builds knowledge graph using Apache AGE to map character relationships and story elements.
"""

import json
import logging
import os
from typing import Dict, Any, List, Tuple, Optional
from ..prompt_template import DeconstructorPrompts
from utils.json_response_parser import parse_graph_analysis_response
from utils.llm_retry import call_llm_with_retry
from ..base_stage import BasePipelineStage, PipelineStageResult, PipelineStageContext
from services.graph_database_service import GraphDatabaseService, GraphDatabaseNotAvailableError

logger = logging.getLogger(__name__)

class ProgressiveGraphAnalysisStage(BasePipelineStage):
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
        super().__init__(db_pool, "ProgressiveGraphAnalysisStage", generation_engine)
        self.prompt_template = DeconstructorPrompts()
        self.graph_service = GraphDatabaseService(db_pool)
    
    def _execute_stage(self, context: PipelineStageContext) -> PipelineStageResult:
        """
        Execute Stage 4B: Progressive graph analysis.
        
        Args:
            context: Stage execution context containing draft_id
            
        Returns:
            PipelineStageResult with stage execution results
        """
        draft_id = context.draft_id
        
        # Get chaptering parameters from draft metadata, or use defaults
        draft_metadata = self.get_draft_metadata(draft_id)
        chaptering_mode = draft_metadata.get('chaptering_mode', 'flexible')
        target_chapter_length = draft_metadata.get('target_chapter_length', 2500)
        
        # Store chaptering parameters for later stages if not already set
        if not draft_metadata.get('chaptering_mode'):
            self._store_chaptering_metadata(draft_id, chaptering_mode, target_chapter_length)
        
        try:
            # Log current graph service status
            service_status = self.graph_service.get_status()
            self.logger.info(f"Graph service status: {service_status}")
            
            # Get scenes for processing
            scenes = self._get_draft_scenes(context)
            
            if not scenes:
                return PipelineStageResult.success_result(
                    self.stage_name,
                    entities_created=0,
                    relationships_created=0,
                    message='No scenes to analyze'
                )
            
            # Initialize progressive summary
            progressive_summary = ""
            total_entities = 0
            total_relationships = 0
            
            # Process scenes in batches
            batch_size = 5
            scene_batches = [scenes[i:i + batch_size] for i in range(0, len(scenes), batch_size)]
            
            for batch_num, scene_batch in enumerate(scene_batches):
                self.logger.info(f"Processing scene batch {batch_num + 1}/{len(scene_batches)} for draft {draft_id}")
                
                # Analyze batch and extract entities/relationships
                batch_data = self._analyze_scene_batch(scene_batch, progressive_summary)
                
                if batch_data:
                    # Store entities and relationships in graph
                    entities_created, relationships_created = self._store_graph_data(
                        context, batch_data
                    )
                    
                    total_entities += entities_created
                    total_relationships += relationships_created
                    
                    # Update progressive summary
                    progressive_summary = self._update_progressive_summary(
                        progressive_summary, scene_batch, batch_data
                    )
            
            return PipelineStageResult.success_result(
                self.stage_name,
                scenes_processed=len(scenes),
                entities_created=total_entities,
                relationships_created=total_relationships,
                batches_processed=len(scene_batches),
                chaptering_mode=chaptering_mode,
                target_chapter_length=target_chapter_length,
                graph_service_status=service_status
            )
            
        except Exception as e:
            return PipelineStageResult.error_result(
                self.stage_name,
                error=str(e),
                draft_id=draft_id
            )
    
    def run(self, draft_id: str, chaptering_mode: str = 'flexible', target_chapter_length: int = 2500) -> Dict[str, Any]:
        """
        Execute Stage 4B: Progressive graph analysis with backward compatibility.
        
        Args:
            draft_id: UUID of the draft
            chaptering_mode: Chaptering approach (backward compatibility)
            target_chapter_length: Target word count (backward compatibility)
            
        Returns:
            Stage execution results
        """
        return super().run(draft_id)
    
    
    def _store_chaptering_metadata(self, draft_id: str, chaptering_mode: str, target_chapter_length: int) -> None:
        """
        Store chaptering parameters in draft metadata for later stages.
        
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
                'stage_4b_completed': True
            }
            self.update_draft_metadata(draft_id, metadata_updates)
            self.logger.debug(f"Stored chaptering metadata for draft {draft_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to store chaptering metadata for draft {draft_id}: {e}")
            raise

    def _get_draft_scenes(self, context: PipelineStageContext) -> List[Tuple]:
        """
        Retrieve scenes for graph analysis with UTF-8 safety.
        """
        draft_id = context.draft_id
        
        try:
            db_connection = self.get_database_connection(context)
            with db_connection as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, scene_number, title, setting, characters, 
                           original_content, analysis_json
                    FROM scenes 
                    WHERE draft_id = %s
                    ORDER BY scene_number
                """, (draft_id,))
                
                scenes = cursor.fetchall()
            
            self.logger.debug(f"Retrieved {len(scenes)} scenes for graph analysis in draft {draft_id} (UTF-8 safe)")
            return scenes
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve scenes for draft {draft_id}: {e}")
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
            
            # Set provider-aware token limit for graph analysis JSON
            self.generation_engine.request.generation_config.max_output_tokens = self._get_output_budget("json_analytical")

            # Enable JSON mode for Gemini structured output
            self.generation_engine.request.generation_config.response_mime_type = "application/json"

            try:
                # Generate graph analysis (with transient-error retry)
                response = call_llm_with_retry(
                    lambda: self.generation_engine.generate(skip_quota=True)
                )

                # Check if response was truncated due to token limit
                if response.success and hasattr(response, 'metadata') and response.metadata.finish_reason == 'length':
                    current_limit = self.generation_engine.request.generation_config.max_output_tokens
                    new_limit = int(current_limit * 1.5)  # Increase by 50%
                    self.logger.warning(
                        f"Stage 4B graph analysis truncated (finish_reason='length'). "
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
                self.logger.error(f"AI generation failed for scene batch: {response.error_message}")
                return None
            
            # Parse the JSON response using unified parser
            try:
                graph_data = parse_graph_analysis_response(response)
                return graph_data
                
            except Exception as e:
                self.logger.error(f"Failed to parse graph analysis JSON: {e}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error analyzing scene batch: {e}")
            return None
    
    
    def _store_graph_data(self, context: PipelineStageContext, graph_data: Dict[str, Any]) -> Tuple[int, int]:
        """
        Store entities and relationships using Apache AGE (AGE-first architecture).
        """
        draft_id = context.draft_id
        entities_created = 0
        relationships_created = 0
        created_entities = set()  # Track successfully created entities
        
        try:
            # Create vertices for each entity type
            for entity_type, entities in [
                ('Character', graph_data.get('characters', [])),
                ('Location', graph_data.get('locations', [])),
                ('Item', graph_data.get('objects', []))
            ]:
                for entity in entities:
                    try:
                        # Validate entity name is present and non-empty
                        entity_name = entity.get('name', '').strip()
                        if not entity_name or len(entity_name) < 1:
                            self.logger.warning(f"Skipping {entity_type} entity with empty/invalid name: {entity}")
                            continue

                        # Allow entities with special characters like "V.S." or "Unnamed Baby"
                        # Only filter out truly problematic names (e.g., only punctuation)
                        import re
                        if not re.search(r'[a-zA-Z0-9]', entity_name):
                            self.logger.warning(f"Skipping {entity_type} entity with no alphanumeric characters: '{entity_name}'")
                            continue

                        # Extract properties (excluding name and type)
                        properties = {k: v for k, v in entity.items() if k not in ['name', 'type']}

                        # Create vertex using AGE graph database
                        vertex_id = self.graph_service.create_vertex(
                            draft_id=draft_id,
                            entity_name=entity_name,
                            entity_type=entity_type,
                            properties=properties
                        )

                        if vertex_id:
                            entities_created += 1
                            created_entities.add(entity_name)  # Track successful creation
                            self.logger.debug(f"Created AGE vertex {vertex_id}: {entity_name} ({entity_type})")
                        else:
                            self.logger.warning(f"Failed to create {entity_type} vertex '{entity_name}': No vertex ID returned")

                    except GraphDatabaseNotAvailableError as e:
                        self.logger.error(f"AGE graph database not available: {e}")
                        raise
                    except Exception as e:
                        self.logger.error(f"Failed to create {entity_type} vertex '{entity.get('name', 'UNKNOWN')}': {e}")
                        # Continue with other entities instead of failing completely
            
            # Create relationships only for entities that were successfully created
            for relationship in graph_data.get('relationships', []):
                try:
                    source_name = relationship['source']
                    target_name = relationship['target']
                    rel_type = relationship['relationship']
                    
                    # Validate that both entities exist before creating relationship
                    if source_name not in created_entities:
                        self.logger.warning(f"Skipping relationship: source entity '{source_name}' was not created")
                        continue
                    if target_name not in created_entities:
                        self.logger.warning(f"Skipping relationship: target entity '{target_name}' was not created")
                        continue
                    
                    # Build relationship properties
                    rel_props = {
                        'context': relationship.get('context', ''),
                        'emotional_tone': relationship.get('emotional_tone', 'neutral')
                    }
                    
                    # Create relationship using AGE graph database
                    edge_id = self.graph_service.create_relationship(
                        draft_id=draft_id,
                        source_name=source_name,
                        target_name=target_name,
                        relationship_type=rel_type,
                        properties=rel_props
                    )
                    
                    if edge_id:
                        relationships_created += 1
                        self.logger.debug(f"Created AGE relationship {edge_id}: {source_name} -{rel_type}-> {target_name}")
                    else:
                        self.logger.warning(f"Failed to create relationship {source_name} -{rel_type}-> {target_name}: No edge ID returned")
                        
                except GraphDatabaseNotAvailableError as e:
                    self.logger.error(f"AGE graph database not available: {e}")
                    raise
                except Exception as e:
                    self.logger.error(f"Failed to create relationship {source_name} -{rel_type}-> {target_name}: {e}")
                    # Continue with other relationships instead of failing completely
            
            # Log the results
            self.logger.info(f"AGE graph data stored: {entities_created} entities, {relationships_created} relationships")
            
            return entities_created, relationships_created
            
        except GraphDatabaseNotAvailableError:
            raise  # Re-raise to fail the entire stage
        except Exception as e:
            self.logger.error(f"Failed to store graph data: {e}")
            raise GraphDatabaseNotAvailableError(f"Graph operations failed: {e}") from e
    
    
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

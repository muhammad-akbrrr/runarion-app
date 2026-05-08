"""
Records API - Flask blueprint for records system CRUD operations
"""

from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

records = Blueprint('records', __name__)


def get_records_manager():
    """Get RecordsManager instance from app config."""
    from flask import current_app
    from src.services.records_manager import RecordsManager
    db_pool = current_app.config.get('CONNECTION_POOL')
    if not db_pool:
        raise RuntimeError("Database connection pool not available")
    return RecordsManager(db_pool)


@records.route('/records/entity', methods=['POST'])
def create_entity():
    """Create a new entity (character, location, item, or custom type)."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        entity_name = data.get('name')
        entity_type = data.get('type')
        properties = data.get('properties', {})
        vertex_label = data.get('vertex_label')  # Optional, defaults to capitalized entity_type
        
        if not project_id or not entity_name or not entity_type:
            return jsonify({
                'error': 'Missing required fields: project_id, name, type'
            }), 400
        
        records_manager = get_records_manager()
        vertex_id = records_manager.create_entity(
            project_id=project_id,
            entity_name=entity_name,
            entity_type=entity_type,
            properties=properties,
            vertex_label=vertex_label
        )
        
        if vertex_id:
            return jsonify({
                'success': True,
                'vertex_id': str(vertex_id),  # Convert to string to avoid JS precision loss
                'entity': {
                    'vertex_id': str(vertex_id),  # Convert to string to avoid JS precision loss
                    'name': entity_name,
                    'type': entity_type,
                    'properties': properties
                }
            }), 201
        else:
            return jsonify({'error': 'Failed to create entity'}), 500
            
    except Exception as e:
        logger.error(f"Error creating entity: {e}")
        return jsonify({'error': str(e)}), 500


@records.route('/records/categories', methods=['GET'])
def list_categories():
    """List all categories for a project."""
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        records_manager = get_records_manager()
        entities = records_manager.get_project_entities(project_id=project_id)
        
        # Extract unique categories, excluding internal ones
        categories = set()
        for entity in entities:
            entity_type = entity.get('type', '')
            if entity_type and not entity_type.startswith('_'):
                categories.add(entity_type)
        
        return jsonify({
            'success': True,
            'categories': sorted(list(categories)),
            'count': len(categories)
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing categories: {e}")
        return jsonify({'error': str(e)}), 500


@records.route('/records/entities', methods=['GET'])
def list_entities_query():
    """List entities for a project (query param version)."""
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
            
        category = request.args.get('category')  # Optional filter
        
        records_manager = get_records_manager()
        entities = records_manager.get_project_entities(
            project_id=project_id,
            entity_type=category
        )
        
        # Filter out internal types
        filtered = [e for e in entities
                   if not e.get('type', '').startswith('_')]
        
        return jsonify({
            'success': True,
            'entities': filtered,
            'count': len(filtered)
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing entities: {e}")
        return jsonify({'error': str(e)}), 500


@records.route('/records/entities/<project_id>', methods=['GET'])
def list_entities(project_id: str):
    """List all entities for a project."""
    try:
        entity_type = request.args.get('type')  # Optional filter
        
        records_manager = get_records_manager()
        entities = records_manager.get_project_entities(
            project_id=project_id,
            entity_type=entity_type
        )
        
        return jsonify({
            'success': True,
            'entities': entities,
            'count': len(entities)
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing entities: {e}")
        return jsonify({'error': str(e)}), 500


@records.route('/records/entity/<vertex_id>', methods=['GET'])
def get_entity(vertex_id):
    """Get a single entity by vertex ID."""
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({'error': 'project_id parameter required'}), 400
        
        records_manager = get_records_manager()
        entities = records_manager.get_project_entities(project_id=project_id)
        
        # Find the entity with matching vertex_id (compare as strings to handle large IDs)
        target_id = str(vertex_id)
        entity = next((e for e in entities if str(e.get('vertex_id')) == target_id), None)
        
        if entity:
            logger.info(f"Found entity {entity.get('name')} with properties keys: {list(entity.get('properties', {}).keys())}")
            return jsonify({
                'success': True,
                'entity': entity
            }), 200
        else:
            logger.warning(f"Entity not found: vertex_id={vertex_id}, project_id={project_id}")
            return jsonify({'error': 'Entity not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting entity: {e}")
        return jsonify({'error': str(e)}), 500


@records.route('/records/entity/<int:vertex_id>', methods=['PUT'])
def update_entity(vertex_id: int):
    """Update an entity."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        entity_name = data.get('name')
        properties = data.get('properties')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        if entity_name is None and properties is None:
            return jsonify({'error': 'At least one field (name or properties) must be provided'}), 400
        
        records_manager = get_records_manager()
        success = records_manager.update_entity(
            project_id=project_id,
            vertex_id=vertex_id,
            entity_name=entity_name,
            properties=properties
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Entity updated successfully'
            }), 200
        else:
            return jsonify({'error': 'Failed to update entity'}), 500
            
    except Exception as e:
        logger.error(f"Error updating entity: {e}")
        return jsonify({'error': str(e)}), 500


@records.route('/records/entity/<int:vertex_id>', methods=['DELETE'])
def delete_entity(vertex_id: int):
    """Delete an entity."""
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({'error': 'project_id parameter required'}), 400
        
        records_manager = get_records_manager()
        success = records_manager.delete_entity(
            project_id=project_id,
            vertex_id=vertex_id
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Entity deleted successfully'
            }), 200
        else:
            return jsonify({'error': 'Failed to delete entity'}), 500
            
    except Exception as e:
        logger.error(f"Error deleting entity: {e}")
        return jsonify({'error': str(e)}), 500


@records.route('/records/relationship', methods=['POST'])
def create_relationship():
    """Create a relationship between two entities."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        source_id = data.get('source_id') or data.get('source')  # Support both ID and name
        target_id = data.get('target_id') or data.get('target')  # Support both ID and name
        relationship_type = data.get('type')
        properties = data.get('properties', {})
        edge_label = data.get('edge_label')  # Optional
        
        if not all([project_id, source_id, target_id, relationship_type]):
            return jsonify({
                'error': 'Missing required fields: project_id, source_id (or source), target_id (or target), type'
            }), 400
        
        records_manager = get_records_manager()
        
        # If source_id/target_id are integers, use them directly; otherwise treat as names
        try:
            source_vertex_id = int(source_id) if isinstance(source_id, (int, str)) and str(source_id).isdigit() else None
            target_vertex_id = int(target_id) if isinstance(target_id, (int, str)) and str(target_id).isdigit() else None
        except (ValueError, TypeError):
            source_vertex_id = None
            target_vertex_id = None
        
        if source_vertex_id and target_vertex_id:
            # Use vertex IDs directly
            edge_id = records_manager.create_relationship_by_ids(
                project_id=project_id,
                source_vertex_id=source_vertex_id,
                target_vertex_id=target_vertex_id,
                relationship_type=relationship_type,
                properties=properties,
                edge_label=edge_label
            )
        else:
            # Fall back to name-based lookup
            edge_id = records_manager.create_relationship(
                project_id=project_id,
                source_name=str(source_id),
                target_name=str(target_id),
                relationship_type=relationship_type,
                properties=properties,
                edge_label=edge_label
            )
        
        if edge_id:
            return jsonify({
                'success': True,
                'edge_id': str(edge_id),  # Convert to string to avoid JS precision loss
                'relationship': {
                    'edge_id': str(edge_id),  # Convert to string to avoid JS precision loss
                    'source_id': source_vertex_id if source_vertex_id else None,
                    'target_id': target_vertex_id if target_vertex_id else None,
                    'source': source_name if not source_vertex_id else None,
                    'target': target_name if not target_vertex_id else None,
                    'type': relationship_type,
                    'properties': properties
                }
            }), 201
        else:
            logger.error(f"Failed to create relationship - edge_id is None. source_id={source_id}, target_id={target_id}, type={relationship_type}")
            return jsonify({
                'error': 'Failed to create relationship',
                'details': 'The relationship creation returned None. Check logs for details.'
            }), 500
            
    except Exception as e:
        logger.error(f"Error creating relationship: {e}")
        return jsonify({'error': str(e)}), 500


@records.route('/records/relationships/<project_id>', methods=['GET'])
def list_relationships(project_id: str):
    """List all relationships for a project."""
    try:
        relationship_type = request.args.get('type')  # Optional filter
        
        records_manager = get_records_manager()
        relationships = records_manager.get_project_relationships(
            project_id=project_id,
            relationship_type=relationship_type
        )
        
        return jsonify({
            'success': True,
            'relationships': relationships,
            'count': len(relationships)
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing relationships: {e}")
        return jsonify({'error': str(e)}), 500


@records.route('/records/relationship/<int:edge_id>', methods=['PUT'])
def update_relationship(edge_id: int):
    """Update a relationship."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        relationship_type = data.get('type')
        properties = data.get('properties')
        edge_label = data.get('edge_label')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        if relationship_type is None and properties is None:
            return jsonify({'error': 'At least one field (type or properties) must be provided'}), 400
        
        records_manager = get_records_manager()
        success = records_manager.update_relationship(
            project_id=project_id,
            edge_id=edge_id,
            relationship_type=relationship_type,
            properties=properties,
            edge_label=edge_label
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Relationship updated successfully'
            }), 200
        else:
            return jsonify({'error': 'Failed to update relationship'}), 500
            
    except Exception as e:
        logger.error(f"Error updating relationship: {e}")
        return jsonify({'error': str(e)}), 500


@records.route('/records/relationship/<int:edge_id>', methods=['DELETE'])
def delete_relationship(edge_id: int):
    """Delete a relationship."""
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({'error': 'project_id parameter required'}), 400
        
        records_manager = get_records_manager()
        success = records_manager.delete_relationship(
            project_id=project_id,
            edge_id=edge_id
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Relationship deleted successfully'
            }), 200
        else:
            return jsonify({'error': 'Failed to delete relationship'}), 500
            
    except Exception as e:
        logger.error(f"Error deleting relationship: {e}")
        return jsonify({'error': str(e)}), 500


@records.route('/records/entity-type', methods=['POST'])
def create_entity_type():
    """Create a custom entity type (vertex label in AGE)."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        vertex_label = data.get('vertex_label')
        
        if not vertex_label:
            return jsonify({'error': 'vertex_label required'}), 400
        
        records_manager = get_records_manager()
        success = records_manager.create_vertex_label(vertex_label)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Entity type {vertex_label} created successfully'
            }), 201
        else:
            return jsonify({'error': 'Failed to create entity type'}), 500
            
    except Exception as e:
        logger.error(f"Error creating entity type: {e}")
        return jsonify({'error': str(e)}), 500


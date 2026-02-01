"""
Auditor API - Flask blueprint for manuscript analysis and summarization
"""

from flask import Blueprint, request, jsonify, current_app
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

auditor = Blueprint('auditor', __name__)


def get_auditor_service():
    """Get AuditorService instance from app config."""
    from flask import current_app
    from services.auditor_service import AuditorService
    db_pool = current_app.config.get('CONNECTION_POOL')
    if not db_pool:
        raise RuntimeError("Database connection pool not available")
    return AuditorService(db_pool)


@auditor.route('/auditor/summarize', methods=['POST'])
def summarize():
    """
    Summarize manuscript chapters and create Record Keeper entries.
    
    Request body:
    {
        "project_id": "project_uuid",
        "enable_record_keeper": true/false,  // Optional, defaults to true
        "category": "character" | "location" | "item" | "theme" | "plot_point" | "all_categories" | custom,
        "mode": "all" | "focused",  // Required only if category is selected (not "all_categories")
        "entity_ids": [1, 2, 3],  // Optional, for focused mode
        "chapter_orders": [0, 1, 2],  // Optional, if None uses all chapters
        "model": "gemini-2.5-flash",
        "provider": "gemini"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        workspace_id = data.get('workspace_id')  # Used for Laravel endpoint (primary method)
        enable_record_keeper = data.get('enable_record_keeper', True)
        category = data.get('category')
        mode = data.get('mode', 'all')
        entity_ids = data.get('entity_ids')
        chapter_orders = data.get('chapter_orders')  # None = all chapters
        model = data.get('model', 'gemini-2.5-flash')
        provider = data.get('provider', 'gemini')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        # Validate that at least one option is enabled
        if not enable_record_keeper and not category:
            return jsonify({'error': 'At least one of Record Keeper or Category must be enabled'}), 400
        
        auditor_service = get_auditor_service()
        
        # Get all chapters (Laravel endpoint is primary when workspace_id available)
        all_chapters = auditor_service.get_chapters(project_id, workspace_id)
        
        if not all_chapters:
            logger.warning(f"No chapters found for project {project_id}")
            return jsonify({'error': 'No chapters found for this project'}), 404
        
        logger.info(f"Found {len(all_chapters)} chapters for project {project_id}")
        
        # Filter chapters if specific ones requested
        chapters_to_process = all_chapters
        if chapter_orders is not None:
            chapters_to_process = [
                ch for ch in all_chapters 
                if ch.get('order') in chapter_orders
            ]
        
        if not chapters_to_process:
            return jsonify({'error': 'No chapters match the specified orders'}), 400
        
        results = {
            'record_keeper_entries_created': 0,
            'record_keeper_entries_updated': 0,
            'entities_processed': 0,  # Total entities analyzed
            'entities_updated': 0,    # Entities that got summaries
            'chapters_processed': 0,
            'errors': []
        }
        
        # Create Record Keeper entries if enabled
        if enable_record_keeper:
            logger.info(f"Creating Record Keeper entries for {len(chapters_to_process)} chapters")
            for chapter in chapters_to_process:
                chapter_order = chapter.get('order', 'unknown')
                chapter_name = chapter.get('chapter_name', f"Chapter {chapter_order}")
                chapter_content = chapter.get('content', '')
                logger.debug(f"Processing chapter {chapter_order}: {chapter_name} ({len(chapter_content) if chapter_content else 0} chars)")
                try:
                    # Analyze chapter for Record Keeper
                    record_keeper_data = auditor_service.summarize_chapter_for_record_keeper(
                        project_id=project_id,
                        chapter=chapter,
                        model=model,
                        provider=provider,
                        workspace_id=workspace_id
                    )
                    
                    if record_keeper_data:
                        # Check if entry exists
                        existing = auditor_service._find_record_keeper_entry(
                            project_id, 
                            record_keeper_data.get('chapter_number')
                        )
                        
                        vertex_id = auditor_service.create_or_update_record_keeper_entry(
                            project_id=project_id,
                            record_keeper_data=record_keeper_data
                        )
                        
                        if vertex_id:
                            if existing:
                                results['record_keeper_entries_updated'] += 1
                            else:
                                results['record_keeper_entries_created'] += 1
                            results['chapters_processed'] += 1
                            logger.info(f"Successfully created/updated Record Keeper entry for chapter {record_keeper_data.get('chapter_number', chapter_order)} (vertex_id: {vertex_id})")
                            
                            # Update scan metadata to track record keeper summarization
                            content_hash = auditor_service._compute_content_hash(chapter_content)
                            auditor_service._update_scan_metadata(
                                project_id=project_id,
                                chapter_order=chapter_order if isinstance(chapter_order, int) else int(chapter_order) if str(chapter_order).isdigit() else 0,
                                content_hash=content_hash,
                                scan_type='record_keeper'
                            )
                        else:
                            error_msg = f"Failed to create Record Keeper entry for chapter {record_keeper_data.get('chapter_number', chapter.get('order', 'unknown'))}"
                            logger.error(error_msg)
                            results['errors'].append(error_msg)
                    else:
                        error_msg = f"Failed to analyze chapter {chapter_order} - likely no content or content too short"
                        logger.warning(error_msg)
                        results['errors'].append(error_msg)
                        
                except Exception as e:
                    logger.error(f"Error processing chapter {chapter_order}: {e}", exc_info=True)
                    results['errors'].append(f"Error processing chapter {chapter_order}: {str(e)}")
        
        # Process category summaries if category is provided
        if category:
            if category == "all_categories":
                # Process all categories sequentially
                logger.info("Processing all categories for entity summarization")
                
                # Get all collection types (excluding Record Keeper)
                collection_types = auditor_service.get_collection_types(project_id)
                all_types = collection_types.get('system', []) + collection_types.get('custom', [])
                categories_to_process = [t['name'] for t in all_types if t['name'].lower() != 'record keeper']
                
                for cat_name in categories_to_process:
                    logger.info(f"Processing entity summaries for category '{cat_name}'")
                    try:
                        cat_results = auditor_service.summarize_entities_by_category(
                            project_id=project_id,
                            workspace_id=workspace_id,
                            category=cat_name,
                            mode='all',
                            entity_ids=None,
                            chapter_orders=chapter_orders,
                            model=model,
                            provider=provider
                        )
                        
                        if 'error' not in cat_results:
                            results['entities_processed'] += cat_results.get('entities_processed', 0)
                            results['entities_updated'] += cat_results.get('entities_updated', 0)
                            if cat_results.get('errors'):
                                results['errors'].extend(cat_results['errors'])
                        else:
                            logger.warning(f"Category {cat_name}: {cat_results.get('error')}")
                            
                    except Exception as e:
                        logger.error(f"Error processing category {cat_name}: {e}")
                        results['errors'].append(f"Error processing {cat_name}: {str(e)}")
            else:
                # Process single category
                logger.info(f"Processing entity summaries for category '{category}'")
                
                cat_results = auditor_service.summarize_entities_by_category(
                    project_id=project_id,
                    workspace_id=workspace_id,
                    category=category,
                    mode=mode,
                    entity_ids=entity_ids,
                    chapter_orders=chapter_orders,
                    model=model,
                    provider=provider
                )
                
                if 'error' not in cat_results:
                    results['entities_processed'] = cat_results.get('entities_processed', 0)
                    results['entities_updated'] = cat_results.get('entities_updated', 0)
                    if cat_results.get('errors'):
                        results['errors'].extend(cat_results['errors'])
                else:
                    error_msg = f"Category summarization failed: {cat_results.get('error')}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
        
        return jsonify({
            'success': True,
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error in summarize endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/extract', methods=['POST'])
def extract_entities():
    """
    Extract entities from manuscript for specified categories.
    
    Request body:
    {
        "project_id": "project_uuid",
        "workspace_id": "workspace_uuid",  // Required for content retrieval
        "categories": ["character", "location"] or ["all_categories"],
        "chapter_orders": [0, 1, 2],  // Optional, if None uses all chapters
        "scan_mode": "incremental" | "full" | "new_only",  // Optional, defaults to "incremental"
        "model": "gemini-2.5-flash",
        "provider": "gemini"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        workspace_id = data.get('workspace_id')
        categories = data.get('categories', [])
        chapter_orders = data.get('chapter_orders')  # None = all chapters
        scan_mode = data.get('scan_mode', 'incremental')  # incremental, full, or new_only
        model = data.get('model', 'gemini-2.5-flash')
        provider = data.get('provider', 'gemini')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        if not workspace_id:
            return jsonify({'error': 'workspace_id required for content retrieval'}), 400
        
        if not categories:
            return jsonify({'error': 'categories required (use ["all_categories"] for all)'}), 400
        
        if scan_mode not in ['incremental', 'full', 'new_only']:
            return jsonify({'error': 'scan_mode must be "incremental", "full", or "new_only"'}), 400
        
        logger.info(f"Entity extraction request: project={project_id}, categories={categories}, chapters={chapter_orders}, mode={scan_mode}, model={model}")
        
        auditor_service = get_auditor_service()
        
        # Extract entities
        results = auditor_service.extract_entities(
            project_id=project_id,
            workspace_id=workspace_id,
            categories=categories,
            chapter_orders=chapter_orders,
            model=model,
            provider=provider,
            scan_mode=scan_mode
        )
        
        if 'error' in results:
            logger.error(f"Entity extraction failed: {results['error']}")
            # Return the message if it's just "no chapters to process"
            if 'All chapters are up-to-date' in results.get('message', ''):
                return jsonify({
                    'success': True,
                    'message': results['message'],
                    'scan_info': results.get('scan_info', {})
                }), 200
            return jsonify({'error': results['error']}), 400
        
        logger.info(f"Entity extraction complete: created={results.get('entities_created', 0)}, updated={results.get('entities_updated', 0)}")
        
        return jsonify({
            'success': True,
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error in extract endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/scan-status', methods=['GET'])
def get_scan_status():
    """
    Get scan status for all chapters in a project.
    Shows which chapters have been scanned, which have changes, etc.
    
    Query params:
        project_id: Project UUID (required)
    """
    try:
        project_id = request.args.get('project_id')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        auditor_service = get_auditor_service()
        status = auditor_service.get_scan_status(project_id)
        
        if 'error' in status:
            return jsonify({'error': status['error']}), 400
        
        return jsonify({
            'success': True,
            'scan_status': status
        }), 200
        
    except Exception as e:
        logger.error(f"Error in scan-status endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/check-consistency/records', methods=['POST'])
def check_record_consistency():
    """
    Check consistency between database records and story content.
    
    Request body:
    {
        "project_id": "project_uuid",
        "workspace_id": "workspace_uuid",
        "categories": ["character", "location"],  // Optional, null = all
        "model": "gemini-2.5-flash",
        "provider": "gemini"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        workspace_id = data.get('workspace_id')
        categories = data.get('categories')  # None = all
        model = data.get('model', 'gemini-2.5-flash')
        provider = data.get('provider', 'gemini')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        if not workspace_id:
            return jsonify({'error': 'workspace_id required'}), 400
        
        logger.info(f"Record consistency check: project={project_id}, categories={categories}")
        
        auditor_service = get_auditor_service()
        
        results = auditor_service.check_record_consistency(
            project_id=project_id,
            workspace_id=workspace_id,
            categories=categories,
            model=model,
            provider=provider
        )
        
        if 'error' in results:
            return jsonify({'error': results['error']}), 400
        
        return jsonify({
            'success': True,
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error in check-consistency/records endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/check-consistency/story', methods=['POST'])
def check_story_consistency():
    """
    Check story itself for internal consistency issues (plot holes, timeline, etc.)
    
    Request body:
    {
        "project_id": "project_uuid",
        "workspace_id": "workspace_uuid",
        "check_types": ["plot_holes", "timeline", "character", "continuity"],  // Optional, null = all
        "chapter_orders": [0, 1, 2],  // Optional, null = all chapters
        "model": "gemini-2.5-flash",
        "provider": "gemini"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        workspace_id = data.get('workspace_id')
        check_types = data.get('check_types')  # None = all
        chapter_orders = data.get('chapter_orders')  # None = all chapters
        model = data.get('model', 'gemini-2.5-flash')
        provider = data.get('provider', 'gemini')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        if not workspace_id:
            return jsonify({'error': 'workspace_id required'}), 400
        
        logger.info(f"Story consistency check: project={project_id}, check_types={check_types}, chapters={chapter_orders}")
        
        auditor_service = get_auditor_service()
        
        results = auditor_service.check_story_consistency(
            project_id=project_id,
            workspace_id=workspace_id,
            check_types=check_types,
            model=model,
            provider=provider,
            chapter_orders=chapter_orders
        )
        
        if 'error' in results:
            return jsonify({'error': results['error']}), 400
        
        return jsonify({
            'success': True,
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error in check-consistency/story endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/find-duplicates', methods=['POST'])
def find_duplicates():
    """
    Find potential duplicate entities that could be merged.
    
    Request body:
    {
        "project_id": "project_uuid",
        "workspace_id": "workspace_uuid",  // Optional, for story context
        "scope": "all" | "category" | "entity",  // Optional, defaults to "all"
        "categories": ["character", "location"],  // Optional, null = all
        "entity_ids": ["vertex_id1", "vertex_id2"],  // Optional, for entity scope
        "model": "gemini-2.5-flash",
        "provider": "gemini"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        workspace_id = data.get('workspace_id')
        scope = data.get('scope', 'all')
        categories = data.get('categories')  # None = all
        entity_ids = data.get('entity_ids')  # For specific entity scope
        model = data.get('model', 'gemini-2.5-flash')
        provider = data.get('provider', 'gemini')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        logger.info(f"Find duplicates: project={project_id}, scope={scope}, categories={categories}, entity_ids={entity_ids}")
        
        auditor_service = get_auditor_service()
        
        results = auditor_service.find_duplicate_entities(
            project_id=project_id,
            workspace_id=workspace_id,
            scope=scope,
            categories=categories,
            entity_ids=entity_ids,
            model=model,
            provider=provider
        )
        
        if 'error' in results:
            return jsonify({'error': results['error']}), 400
        
        return jsonify({
            'success': True,
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error in find-duplicates endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/merge-entities', methods=['POST'])
def merge_entities():
    """
    Merge two entities into one.
    
    Request body:
    {
        "project_id": "project_uuid",
        "source_vertex_id": "123",  // Entity to merge FROM (will be deleted)
        "target_vertex_id": "456",  // Entity to merge INTO (will be kept)
        "merge_strategy": "combine" | "prefer_source" | "prefer_target"  // Optional, defaults to "combine"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        source_vertex_id = data.get('source_vertex_id')
        target_vertex_id = data.get('target_vertex_id')
        merge_strategy = data.get('merge_strategy', 'combine')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        if not source_vertex_id:
            return jsonify({'error': 'source_vertex_id required'}), 400
        
        if not target_vertex_id:
            return jsonify({'error': 'target_vertex_id required'}), 400
        
        if source_vertex_id == target_vertex_id:
            return jsonify({'error': 'Cannot merge entity into itself'}), 400
        
        if merge_strategy not in ['combine', 'prefer_source', 'prefer_target']:
            return jsonify({'error': 'merge_strategy must be "combine", "prefer_source", or "prefer_target"'}), 400
        
        logger.info(f"Merge entities: project={project_id}, source={source_vertex_id}, target={target_vertex_id}, strategy={merge_strategy}")
        
        auditor_service = get_auditor_service()
        
        results = auditor_service.merge_entities(
            project_id=project_id,
            source_vertex_id=source_vertex_id,
            target_vertex_id=target_vertex_id,
            merge_strategy=merge_strategy
        )
        
        if 'error' in results:
            return jsonify({'error': results['error']}), 400
        
        return jsonify({
            'success': True,
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error in merge-entities endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/refresh-properties', methods=['POST'])
def refresh_entity_properties():
    """
    Refresh a single entity's properties to reflect current story state.
    
    This is arc-aware: it understands that characters change over time
    and updates properties to where they are NOW in the narrative.
    
    Request body:
    {
        "project_id": "project_uuid",
        "workspace_id": "workspace_uuid",
        "vertex_id": "entity_vertex_id",
        "model": "gemini-2.5-flash",
        "provider": "gemini"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        workspace_id = data.get('workspace_id')
        vertex_id = data.get('vertex_id')
        model = data.get('model', 'gemini-2.5-flash')
        provider = data.get('provider', 'gemini')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        if not workspace_id:
            return jsonify({'error': 'workspace_id required'}), 400
        
        if not vertex_id:
            return jsonify({'error': 'vertex_id required'}), 400
        
        logger.info(f"Refresh properties: project={project_id}, entity={vertex_id}")
        
        auditor_service = get_auditor_service()
        
        results = auditor_service.refresh_entity_properties(
            project_id=project_id,
            workspace_id=workspace_id,
            vertex_id=str(vertex_id),
            model=model,
            provider=provider
        )
        
        if 'error' in results:
            return jsonify({'error': results['error']}), 400
        
        return jsonify({
            'success': True,
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error in refresh-properties endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/refresh-all-properties', methods=['POST'])
def refresh_all_properties():
    """
    Refresh all entities' properties (or filtered by category) to current story state.
    
    Request body:
    {
        "project_id": "project_uuid",
        "workspace_id": "workspace_uuid",
        "categories": ["character", "location"],  // Optional, null = all
        "model": "gemini-2.5-flash",
        "provider": "gemini"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        workspace_id = data.get('workspace_id')
        categories = data.get('categories')  # None = all categories
        entity_ids = data.get('entity_ids')  # None = all entities in selected categories
        model = data.get('model', 'gemini-2.5-flash')
        provider = data.get('provider', 'gemini')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        if not workspace_id:
            return jsonify({'error': 'workspace_id required'}), 400
        
        logger.info(f"Refresh all properties: project={project_id}, categories={categories}, entity_ids={entity_ids}")
        
        auditor_service = get_auditor_service()
        
        results = auditor_service.refresh_all_entities_properties(
            project_id=project_id,
            workspace_id=workspace_id,
            categories=categories,
            entity_ids=entity_ids,
            model=model,
            provider=provider
        )
        
        if 'error' in results:
            return jsonify({'error': results['error']}), 400
        
        return jsonify({
            'success': True,
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error in refresh-all-properties endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/apply-fix', methods=['POST'])
def apply_consistency_fix():
    """
    Apply a fix from consistency check results.
    
    Request body:
    {
        "project_id": "project_uuid",
        "workspace_id": "workspace_uuid",
        "entity_name": "Yurak",
        "entity_type": "character",  // Optional
        "issue_type": "contradiction" | "outdated" | "missing_update",
        "field": "emotional_state",  // Optional - the specific field to update
        "suggestion": "Update the trait to reflect...",
        "model": "gemini-2.5-flash",
        "provider": "gemini"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        workspace_id = data.get('workspace_id')
        entity_name = data.get('entity_name')
        entity_type = data.get('entity_type')
        issue_type = data.get('issue_type')
        field = data.get('field')
        suggestion = data.get('suggestion')
        model = data.get('model', 'gemini-2.5-flash')
        provider = data.get('provider', 'gemini')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        if not entity_name:
            return jsonify({'error': 'entity_name required'}), 400
        
        if not suggestion:
            return jsonify({'error': 'suggestion required'}), 400
        
        logger.info(f"Apply fix: project={project_id}, entity={entity_name}, issue={issue_type}, field={field}")
        
        auditor_service = get_auditor_service()
        
        results = auditor_service.apply_consistency_fix(
            project_id=project_id,
            workspace_id=workspace_id,
            entity_name=entity_name,
            entity_type=entity_type,
            issue_type=issue_type,
            field=field,
            suggestion=suggestion,
            model=model,
            provider=provider
        )
        
        if 'error' in results:
            return jsonify({'error': results['error']}), 400
        
        return jsonify({
            'success': True,
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error in apply-fix endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/fix-story-text', methods=['POST'])
def fix_story_text():
    """
    Generate a fix for story text (not entity properties).
    This finds the problematic text and generates a revised version.
    
    Request body:
    {
        "project_id": "project_uuid",
        "workspace_id": "workspace_uuid",
        "issue_type": "character" | "plot_holes" | "timeline" | "continuity",
        "title": "Issue title",
        "description": "Detailed description",
        "evidence": "Quote from the text",
        "location": "Chapter 1",
        "suggestion": "How to fix it",
        "model": "gemini-2.5-flash",
        "provider": "gemini"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        workspace_id = data.get('workspace_id')
        issue_type = data.get('issue_type')
        title = data.get('title')
        description = data.get('description', '')
        evidence = data.get('evidence', '')
        location = data.get('location', '')
        suggestion = data.get('suggestion', '')
        model = data.get('model', 'gemini-2.5-flash')
        provider = data.get('provider', 'gemini')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        if not title:
            return jsonify({'error': 'title required'}), 400
        
        logger.info(f"Fix story text: project={project_id}, issue={issue_type}, title={title}")
        
        auditor_service = get_auditor_service()
        
        results = auditor_service.fix_story_text(
            project_id=project_id,
            workspace_id=workspace_id,
            issue_type=issue_type,
            title=title,
            description=description,
            evidence=evidence,
            location=location,
            suggestion=suggestion,
            model=model,
            provider=provider
        )
        
        if 'error' in results:
            return jsonify({'error': results['error']}), 400
        
        return jsonify({
            'success': True,
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error in fix-story-text endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/batch-fix-story-text', methods=['POST'])
def batch_fix_story_text():
    """
    Generate fixes for multiple story issues against the same content snapshot.
    This ensures all fixes are compatible and can be applied together without conflicts.

    Request body:
    {
        "project_id": "project_uuid",
        "workspace_id": "workspace_uuid",
        "issues": [
            {
                "issue_type": "timeline",
                "title": "Issue title",
                "description": "Description",
                "evidence": "Quote from text",
                "location": "Chapter 1",
                "suggestion": "How to fix"
            },
            ...
        ],
        "model": "gemini-2.5-flash",
        "provider": "gemini"
    }

    Response:
    {
        "success": true,
        "results": {
            "fixes": [
                {
                    "issue_index": 0,
                    "old_text": "...",
                    "new_text": "...",
                    "explanation": "...",
                    "chapter_order": 1,
                    "chapter_name": "Chapter 1",
                    "position": 234
                },
                ...
            ],
            "content_hash": "abc123",
            "errors": []
        }
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        project_id = data.get('project_id')
        workspace_id = data.get('workspace_id')
        issues = data.get('issues', [])
        model = data.get('model', 'gemini-2.5-flash')
        provider = data.get('provider', 'gemini')

        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400

        if not issues:
            return jsonify({'error': 'issues array is required'}), 400

        auditor_service = get_auditor_service()
        results = auditor_service.batch_fix_story_text(
            project_id=project_id,
            workspace_id=workspace_id,
            issues=issues,
            model=model,
            provider=provider
        )

        if 'error' in results and not results.get('fixes'):
            return jsonify({'success': False, 'error': results['error']}), 400

        return jsonify({
            'success': True,
            'results': results
        }), 200

    except Exception as e:
        logger.error(f"Error in batch-fix-story-text endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# =============================================================================
# SENTIMENT ANALYZER ENDPOINTS
# =============================================================================

def get_sentiment_service():
    """Get SentimentAnalyzerService instance from app config."""
    from flask import current_app
    from services.sentiment_analyzer_service import SentimentAnalyzerService
    db_pool = current_app.config.get('CONNECTION_POOL')
    if not db_pool:
        raise RuntimeError("Database connection pool not available")
    return SentimentAnalyzerService(db_pool)


@auditor.route('/auditor/extract-relationships', methods=['POST'])
def extract_relationships():
    """
    Extract character relationships from manuscript with sentiment analysis.
    
    Request body:
    {
        "project_id": "project_uuid",
        "workspace_id": "workspace_uuid",
        "character_ids": [123, 456],  // Optional - vertex IDs to focus on (null = all)
        "chapter_orders": [0, 1, 2],  // Optional - chapters to analyze (null = all)
        "model": "gemini-2.5-flash",
        "provider": "gemini"
    }
    
    Returns:
    {
        "success": true,
        "relationships": [
            {
                "source": "Alice",
                "target": "Bob",
                "relationship_type": "RIVALS",
                "emotional_tone": "hostile",
                "sentiment_score": -45,
                "sentiment_reasons": ["Base tone: hostile (-70)", "Context: \"rivalry\" (-10)", ...],
                "context": "Alice and Bob have been rivals since...",
                "text_evidence": [{"quote": "...", "location": "Chapter 3"}],
                "edge_id": "123456789"
            }
        ],
        "total_extracted": 5,
        "stored_in_graph": 5,
        "chapters_analyzed": 3
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        workspace_id = data.get('workspace_id')
        character_ids = data.get('character_ids')  # Optional list of vertex IDs
        chapter_orders = data.get('chapter_orders')  # Optional list
        model = data.get('model', 'gemini-2.5-flash')
        provider = data.get('provider', 'gemini')
        focus_mode = data.get('focus_mode', 'all')  # 'all', 'selected', or '1-to-1'
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        # Validate 1-to-1 mode requires exactly 2 characters
        if focus_mode == '1-to-1':
            if not character_ids or len(character_ids) != 2:
                return jsonify({'error': '1-to-1 mode requires exactly 2 character IDs'}), 400
        
        logger.info(f"Extract relationships: project={project_id}, characters={character_ids}, chapters={chapter_orders}, focus_mode={focus_mode}")
        
        sentiment_service = get_sentiment_service()
        
        results = sentiment_service.extract_relationships(
            project_id=project_id,
            workspace_id=workspace_id,
            character_ids=character_ids,
            chapter_orders=chapter_orders,
            model=model,
            provider=provider,
            focus_mode=focus_mode
        )
        
        if 'error' in results:
            return jsonify({'error': results['error']}), 400
        
        return jsonify(results), 200
        
    except Exception as e:
        logger.error(f"Error in extract-relationships endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/extract-relationships-v2', methods=['POST'])
def extract_relationships_v2():
    """
    V2 Relationship Extraction: Chapter-based analysis (simpler, more reliable).
    
    Instead of extracting micro-interactions, analyzes how each character
    engages with others chapter-by-chapter, then synthesizes overall relationships.
    
    Request body:
    {
        "project_id": "project_uuid",
        "workspace_id": "workspace_uuid",
        "character_ids": [123, 456],  // Optional - vertex IDs to focus on
        "chapter_orders": [0, 1, 2],  // Optional - chapters to analyze
        "model": "gemini-2.5-flash",
        "provider": "gemini",
        "focus_mode": "all" | "selected" | "1-to-1"
    }
    
    Returns:
    {
        "success": true,
        "relationships": [
            {
                "source": "Alice",
                "target": "Bob",
                "chapter_analyses": [
                    {
                        "chapter_number": 1,
                        "chapter_name": "Chapter 1",
                        "sentiment_score": 35,
                        "relationship_type": "ALLY",
                        "emotional_tone": "cautious",
                        "summary": "Alice views Bob with cautious respect...",
                        "key_moment": "\"I trust you, for now,\" Alice said."
                    },
                    ...
                ],
                "overall": {
                    "overall_sentiment": 42,
                    "relationship_type": "ALLY",
                    "emotional_tone": "growing trust",
                    "summary": "Their alliance deepens through shared challenges.",
                    "progression": "Started wary, now genuine allies."
                }
            }
        ],
        "total_pairs": 4,
        "successful_pairs": 4,
        "chapters_analyzed": 3,
        "mode": "1-to-1"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        workspace_id = data.get('workspace_id')
        character_ids = data.get('character_ids')
        chapter_orders = data.get('chapter_orders')
        model = data.get('model', 'gemini-2.5-flash')
        provider = data.get('provider', 'gemini')
        focus_mode = data.get('focus_mode', 'all')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        # Validate 1-to-1 mode
        if focus_mode == '1-to-1':
            if not character_ids or len(character_ids) != 2:
                return jsonify({'error': '1-to-1 mode requires exactly 2 character IDs'}), 400
        
        logger.info(f"Extract relationships V2: project={project_id}, focus_mode={focus_mode}, characters={character_ids}, chapter_orders={chapter_orders}")
        
        sentiment_service = get_sentiment_service()
        
        results = sentiment_service.extract_relationships_v2(
            project_id=project_id,
            workspace_id=workspace_id,
            character_ids=character_ids,
            chapter_orders=chapter_orders,
            model=model,
            provider=provider,
            focus_mode=focus_mode
        )
        
        if 'error' in results:
            return jsonify({'error': results['error']}), 400
        
        return jsonify(results), 200
        
    except Exception as e:
        logger.error(f"Error in extract-relationships-v2 endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/relationship/<int:edge_id>/chapter-analyses', methods=['PUT'])
def update_chapter_analyses(edge_id: int):
    """
    Update chapter analyses for a relationship (edit/add/delete individual chapters).
    
    Request body:
    {
        "project_id": "project_uuid",
        "chapter_analyses": [...],  // Full array of chapter analyses
        "recalculate_overall": true  // Whether to recalculate overall sentiment
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        chapter_analyses = data.get('chapter_analyses', [])
        recalculate_overall = data.get('recalculate_overall', True)
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        from services.records_manager import RecordsManager
        from flask import current_app
        
        db_pool = current_app.config.get('CONNECTION_POOL')
        if not db_pool:
            return jsonify({'error': 'Database connection pool not available'}), 500
        
        records_manager = RecordsManager(db_pool)
        
        # Get existing relationship properties
        relationships = records_manager.get_project_relationships(project_id)
        target_rel = None
        for rel in relationships:
            if str(rel.get('edge_id')) == str(edge_id):
                target_rel = rel
                break
        
        if not target_rel:
            return jsonify({'error': f'Relationship {edge_id} not found'}), 404
        
        current_props = target_rel.get('properties', {})
        
        # Update chapter_analyses
        import json
        current_props['chapter_analyses'] = json.dumps(chapter_analyses)
        
        # Optionally recalculate overall sentiment
        if recalculate_overall and chapter_analyses:
            total_score = sum(ch.get('sentiment_score', 0) for ch in chapter_analyses)
            avg_score = total_score // len(chapter_analyses) if chapter_analyses else 0
            current_props['sentiment_score'] = avg_score
            
            # Use the most recent chapter's tone/type as the overall
            if chapter_analyses:
                latest = chapter_analyses[-1]
                current_props['emotional_tone'] = latest.get('emotional_tone', current_props.get('emotional_tone', 'neutral'))
        
        current_props['last_updated'] = __import__('datetime').datetime.utcnow().isoformat()
        
        # Update the relationship
        success = records_manager.update_relationship(
            project_id=project_id,
            edge_id=edge_id,
            properties=current_props
        )
        
        if success:
            logger.info(f"Updated chapter analyses for edge {edge_id}: {len(chapter_analyses)} chapters")
            return jsonify({
                'success': True,
                'edge_id': str(edge_id),
                'chapter_count': len(chapter_analyses),
                'new_sentiment': current_props.get('sentiment_score')
            }), 200
        else:
            return jsonify({'error': 'Failed to update relationship'}), 500
        
    except Exception as e:
        logger.error(f"Error updating chapter analyses: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/emotional-tones/<project_id>', methods=['GET'])
def get_emotional_tones(project_id: str):
    """
    Get all emotional tones for a project (base + custom).
    """
    try:
        from services.records_manager import RecordsManager
        from flask import current_app
        
        db_pool = current_app.config.get('CONNECTION_POOL')
        if not db_pool:
            return jsonify({'error': 'Database connection pool not available'}), 500
        
        records_manager = RecordsManager(db_pool)
        
        # Base emotional tones (always available)
        base_tones = [
            {'id': 'warm', 'name': 'Warm', 'is_base': True},
            {'id': 'cold', 'name': 'Cold', 'is_base': True},
            {'id': 'neutral', 'name': 'Neutral', 'is_base': True},
            {'id': 'hostile', 'name': 'Hostile', 'is_base': True},
            {'id': 'friendly', 'name': 'Friendly', 'is_base': True},
            {'id': 'professional', 'name': 'Professional', 'is_base': True},
            {'id': 'romantic', 'name': 'Romantic', 'is_base': True},
            {'id': 'familial', 'name': 'Familial', 'is_base': True},
            {'id': 'protective', 'name': 'Protective', 'is_base': True},
            {'id': 'suspicious', 'name': 'Suspicious', 'is_base': True},
            {'id': 'playful', 'name': 'Playful', 'is_base': True},
            {'id': 'tense', 'name': 'Tense', 'is_base': True},
        ]
        
        # Get custom tones from database
        custom_tones = records_manager.get_custom_emotional_tones(project_id)
        
        return jsonify({
            'success': True,
            'base_tones': base_tones,
            'custom_tones': custom_tones,
            'all_tones': base_tones + custom_tones
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting emotional tones: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/emotional-tones/<project_id>', methods=['POST'])
def create_emotional_tone(project_id: str):
    """
    Create a custom emotional tone.
    
    Request body:
    {
        "name": "Brotherly",
        "description": "A warm, protective sibling-like bond"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        name = data.get('name', '').strip()
        description = data.get('description', '')
        
        if not name:
            return jsonify({'error': 'Tone name required'}), 400
        
        from services.records_manager import RecordsManager
        from flask import current_app
        
        db_pool = current_app.config.get('CONNECTION_POOL')
        if not db_pool:
            return jsonify({'error': 'Database connection pool not available'}), 500
        
        records_manager = RecordsManager(db_pool)
        
        tone_id = records_manager.create_custom_emotional_tone(
            project_id=project_id,
            name=name,
            description=description
        )
        
        if tone_id:
            return jsonify({
                'success': True,
                'tone': {
                    'id': tone_id,
                    'name': name,
                    'description': description,
                    'is_base': False
                }
            }), 201
        else:
            return jsonify({'error': 'Failed to create tone'}), 500
        
    except Exception as e:
        logger.error(f"Error creating emotional tone: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/emotional-tones/<project_id>/<tone_id>', methods=['DELETE'])
def delete_emotional_tone(project_id: str, tone_id: str):
    """
    Delete a custom emotional tone (cannot delete base tones).
    """
    try:
        from services.records_manager import RecordsManager
        from flask import current_app
        
        db_pool = current_app.config.get('CONNECTION_POOL')
        if not db_pool:
            return jsonify({'error': 'Database connection pool not available'}), 500
        
        records_manager = RecordsManager(db_pool)
        
        success = records_manager.delete_custom_emotional_tone(
            project_id=project_id,
            tone_id=tone_id
        )
        
        if success:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Failed to delete tone (may be a base tone)'}), 400
        
    except Exception as e:
        logger.error(f"Error deleting emotional tone: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/scan-relationship-changes', methods=['POST'])
def scan_relationship_changes():
    """
    Scan for relationship changes between stored state and current manuscript.
    
    Request body:
    {
        "project_id": "project_uuid",
        "workspace_id": "workspace_uuid",
        "model": "gemini-2.5-flash",
        "provider": "gemini"
    }
    
    Returns:
    {
        "success": true,
        "changes": {
            "new_relationships": [...],
            "modified_relationships": [...],
            "potentially_removed": [...],
            "unchanged": [...]
        },
        "summary": {
            "new_count": 2,
            "modified_count": 1,
            "removed_count": 0,
            "unchanged_count": 5
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        workspace_id = data.get('workspace_id')
        model = data.get('model', 'gemini-2.5-flash')
        provider = data.get('provider', 'gemini')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        logger.info(f"Scan relationship changes: project={project_id}")
        
        sentiment_service = get_sentiment_service()
        
        results = sentiment_service.scan_relationship_changes(
            project_id=project_id,
            workspace_id=workspace_id,
            model=model,
            provider=provider
        )
        
        if 'error' in results:
            return jsonify({'error': results['error']}), 400
        
        return jsonify(results), 200
        
    except Exception as e:
        logger.error(f"Error in scan-relationship-changes endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/apply-relationship-changes', methods=['POST'])
def apply_relationship_changes():
    """
    Apply selected relationship changes to the database.
    
    Request body:
    {
        "project_id": "project_uuid",
        "changes": [
            {
                "action": "update" | "create" | "delete",
                "edge_id": "123456789",  // For update/delete
                "source": "Alice",
                "target": "Bob",
                "relationship_type": "RIVALS",
                "new_emotional_tone": "hostile",
                "new_sentiment_score": -45,
                "new_context": "..."
            }
        ]
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        changes = data.get('changes', [])
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        if not changes:
            return jsonify({'error': 'No changes provided'}), 400
        
        logger.info(f"Apply relationship changes: project={project_id}, count={len(changes)}")
        
        sentiment_service = get_sentiment_service()
        
        results = sentiment_service.apply_relationship_changes(
            project_id=project_id,
            changes_to_apply=changes
        )
        
        return jsonify(results), 200
        
    except Exception as e:
        logger.error(f"Error in apply-relationship-changes endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/interactions', methods=['GET'])
def get_interactions():
    """
    Get all interaction records for a project.
    
    Query params:
        project_id: Required - Project UUID
        source_character: Optional - Filter by source character name
        target_character: Optional - Filter by target character name (requires source_character)
    
    Returns:
    {
        "success": true,
        "interactions": [
            {
                "vertex_id": 123456789,
                "source_character": "Alice",
                "target_character": "Bob",
                "chapter_number": 1,
                "chapter_name": "Chapter 1",
                "interaction_type": "ARGUES_WITH",
                "emotional_tone": "hostile",
                "sentiment_modifier": -25,
                "context": "...",
                "text_evidence": "..."
            }
        ],
        "count": 15
    }
    """
    try:
        project_id = request.args.get('project_id')
        source_character = request.args.get('source_character')
        target_character = request.args.get('target_character')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        from services.records_manager import RecordsManager
        from flask import current_app
        
        db_pool = current_app.config.get('CONNECTION_POOL')
        if not db_pool:
            return jsonify({'error': 'Database connection pool not available'}), 500
        
        records_manager = RecordsManager(db_pool)
        
        if source_character:
            interactions = records_manager.get_interactions_for_characters(
                project_id=project_id,
                source_character=source_character,
                target_character=target_character
            )
        else:
            interactions = records_manager.get_all_interactions_for_project(project_id)
        
        return jsonify({
            'success': True,
            'interactions': interactions,
            'count': len(interactions)
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get-interactions endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/interactions/delete-all', methods=['DELETE'])
def delete_all_interactions():
    """
    Delete ALL interactions for a project.
    
    Query params:
        project_id: Required - Project UUID
    
    Returns:
    {
        "success": true,
        "deleted_count": 42
    }
    """
    try:
        from services.records_manager import RecordsManager
        
        project_id = request.args.get('project_id')
        
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        
        db_pool = current_app.config.get('CONNECTION_POOL')
        if not db_pool:
            return jsonify({'error': 'Database connection pool not available'}), 500
        
        records_manager = RecordsManager(db_pool)
        deleted_count = records_manager.delete_all_interactions(project_id)
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count
        }), 200
        
    except Exception as e:
        logger.error(f"Error in delete-all-interactions endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/interactions/<vertex_id>', methods=['DELETE'])
def delete_interaction(vertex_id):
    """
    Delete a single interaction by vertex ID.
    
    Path params:
        vertex_id: Interaction vertex ID
        
    Query params:
        project_id: Required - Project UUID
    
    Returns:
        {"success": true} or {"error": "message"}
    """
    try:
        project_id = request.args.get('project_id')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        from services.records_manager import RecordsManager
        from flask import current_app
        
        db_pool = current_app.config.get('CONNECTION_POOL')
        if not db_pool:
            return jsonify({'error': 'Database connection pool not available'}), 500
        
        records_manager = RecordsManager(db_pool)
        
        success = records_manager.delete_interaction(project_id, int(vertex_id))
        
        if success:
            return jsonify({'success': True, 'deleted_vertex_id': vertex_id}), 200
        else:
            return jsonify({'error': 'Failed to delete interaction'}), 500
        
    except Exception as e:
        logger.error(f"Error in delete-interaction endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/interactions/<vertex_id>', methods=['PUT'])
def update_interaction(vertex_id):
    """
    Update a single interaction by vertex ID.
    
    Path params:
        vertex_id: Interaction vertex ID
        
    Body:
        project_id: Required - Project UUID
        interaction_type: Optional - New interaction type
        emotional_tone: Optional - New emotional tone
        sentiment_modifier: Optional - New sentiment modifier
        context: Optional - New context
        text_evidence: Optional - New text evidence
    
    Returns:
        {"success": true, "interaction": {...}} or {"error": "message"}
    """
    try:
        data = request.get_json() or {}
        project_id = data.get('project_id')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        from services.records_manager import RecordsManager
        from flask import current_app
        
        db_pool = current_app.config.get('CONNECTION_POOL')
        if not db_pool:
            return jsonify({'error': 'Database connection pool not available'}), 500
        
        records_manager = RecordsManager(db_pool)
        
        # Build properties to update
        update_props = {}
        if 'interaction_type' in data:
            update_props['interaction_type'] = data['interaction_type']
        if 'emotional_tone' in data:
            update_props['emotional_tone'] = data['emotional_tone']
        if 'sentiment_modifier' in data:
            update_props['sentiment_modifier'] = data['sentiment_modifier']
        if 'context' in data:
            update_props['context'] = data['context']
        if 'text_evidence' in data:
            update_props['text_evidence'] = data['text_evidence']
        
        if not update_props:
            return jsonify({'error': 'No properties to update'}), 400
        
        # Update the interaction vertex
        success = records_manager.update_entity(
            project_id=project_id,
            vertex_id=int(vertex_id),
            properties=update_props
        )
        
        if success:
            return jsonify({'success': True, 'updated_vertex_id': vertex_id}), 200
        else:
            return jsonify({'error': 'Failed to update interaction'}), 500
        
    except Exception as e:
        logger.error(f"Error in update-interaction endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/interactions/create', methods=['POST'])
def create_interaction_endpoint():
    """
    Create a new interaction manually.
    
    Body:
        project_id: Required - Project UUID
        source_character: Required - Source character name
        target_character: Required - Target character name
        chapter_number: Required - Chapter number (0-indexed)
        chapter_name: Optional - Chapter name
        interaction_type: Required - Interaction type (e.g., SAVES, THREATENS)
        emotional_tone: Required - Emotional tone (e.g., hostile, friendly)
        sentiment_modifier: Optional - Sentiment modifier (-100 to +100)
        context: Optional - Context description
        text_evidence: Optional - Text evidence/quote
    
    Returns:
        {"success": true, "interaction": {...}} or {"error": "message"}
    """
    try:
        data = request.get_json() or {}
        
        # Validate required fields
        required = ['project_id', 'source_character', 'target_character', 'chapter_number', 'interaction_type', 'emotional_tone']
        missing = [f for f in required if not data.get(f) and data.get(f) != 0]
        if missing:
            return jsonify({'error': f'Missing required fields: {missing}'}), 400
        
        from services.records_manager import RecordsManager
        from services.sentiment_analyzer_service import SentimentAnalyzerService
        from flask import current_app
        
        db_pool = current_app.config.get('CONNECTION_POOL')
        if not db_pool:
            return jsonify({'error': 'Database connection pool not available'}), 500
        
        records_manager = RecordsManager(db_pool)
        sentiment_service = SentimentAnalyzerService(db_pool)
        
        # Calculate sentiment if not provided
        sentiment_modifier = data.get('sentiment_modifier')
        if sentiment_modifier is None:
            sentiment_modifier, _ = sentiment_service.calculate_sentiment_score(
                emotional_tone=data['emotional_tone'],
                context=data.get('context', ''),
                relationship_type=data['interaction_type']
            )
        
        # Create the interaction
        vertex_id = records_manager.create_interaction(
            project_id=data['project_id'],
            source_character=data['source_character'],
            target_character=data['target_character'],
            chapter_number=data['chapter_number'],
            chapter_name=data.get('chapter_name', f"Chapter {data['chapter_number'] + 1}"),
            interaction_type=data['interaction_type'],
            emotional_tone=data['emotional_tone'],
            sentiment_modifier=sentiment_modifier,
            context=data.get('context', ''),
            text_evidence=data.get('text_evidence', ''),
            properties={}
        )
        
        if vertex_id:
            return jsonify({
                'success': True,
                'interaction': {
                    'vertex_id': vertex_id,
                    'source_character': data['source_character'],
                    'target_character': data['target_character'],
                    'chapter_number': data['chapter_number'],
                    'interaction_type': data['interaction_type'],
                    'emotional_tone': data['emotional_tone'],
                    'sentiment_modifier': sentiment_modifier,
                    'context': data.get('context', ''),
                    'text_evidence': data.get('text_evidence', '')
                }
            }), 201
        else:
            return jsonify({'error': 'Failed to create interaction'}), 500
        
    except Exception as e:
        logger.error(f"Error in create-interaction endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/interactions/aggregate', methods=['GET'])
def aggregate_interactions():
    """
    Aggregate interactions between two characters into a relationship summary.
    
    Query params:
        project_id: Required - Project UUID
        source_character: Required - First character name
        target_character: Required - Second character name
    
    Returns:
    {
        "success": true,
        "relationship": {
            "source": "Alice",
            "target": "Bob",
            "sentiment_score": -45,
            "interaction_count": 5,
            "dominant_tone": "hostile",
            "tone_breakdown": {"hostile": 3, "cold": 2},
            "interactions": [...]
        }
    }
    """
    try:
        project_id = request.args.get('project_id')
        source_character = request.args.get('source_character')
        target_character = request.args.get('target_character')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        if not source_character or not target_character:
            return jsonify({'error': 'source_character and target_character required'}), 400
        
        from services.records_manager import RecordsManager
        from flask import current_app
        
        db_pool = current_app.config.get('CONNECTION_POOL')
        if not db_pool:
            return jsonify({'error': 'Database connection pool not available'}), 500
        
        records_manager = RecordsManager(db_pool)
        
        aggregated = records_manager.aggregate_relationship_from_interactions(
            project_id=project_id,
            source_character=source_character,
            target_character=target_character
        )
        
        return jsonify({
            'success': True,
            'relationship': aggregated
        }), 200
        
    except Exception as e:
        logger.error(f"Error in aggregate-interactions endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/relationships/synthesize', methods=['POST'])
def synthesize_relationship():
    """
    Synthesize a holistic relationship summary from interactions using AI.
    
    This asks AI to analyze all interactions between two characters and provide
    a meaningful summary of how the source character perceives the target.
    
    Body:
        project_id: Required - Project UUID
        workspace_id: Required - Workspace UUID
        source_character: Required - Source character name
        target_character: Required - Target character name
        model: Optional - AI model to use (default: gemini-2.5-flash)
        provider: Optional - AI provider (default: gemini)
    
    Returns:
        {
            "success": true,
            "synthesis": {
                "overall_sentiment_score": -100 to +100,
                "relationship_summary": "Description of how source views target",
                "key_dynamics": ["dynamic 1", "dynamic 2"],
                "emotional_foundation": "core emotion driving the relationship"
            }
        }
    """
    try:
        data = request.get_json() or {}
        project_id = data.get('project_id')
        workspace_id = data.get('workspace_id')
        source_character = data.get('source_character')
        target_character = data.get('target_character')
        model = data.get('model', 'gemini-2.5-flash')
        provider = data.get('provider', 'gemini')
        
        if not project_id or not workspace_id:
            return jsonify({'error': 'project_id and workspace_id required'}), 400
        
        if not source_character or not target_character:
            return jsonify({'error': 'source_character and target_character required'}), 400
        
        from services.sentiment_analyzer_service import SentimentAnalyzerService
        from services.records_manager import RecordsManager
        from flask import current_app
        
        db_pool = current_app.config.get('CONNECTION_POOL')
        if not db_pool:
            return jsonify({'error': 'Database connection pool not available'}), 500
        
        # Get interactions for this character pair
        records_manager = RecordsManager(db_pool)
        interactions = records_manager.get_interactions_for_characters(
            project_id=project_id,
            source_character=source_character,
            target_character=target_character
        )
        
        # Filter to only interactions where source acts toward target (directional)
        directional_interactions = [
            i for i in interactions 
            if i.get('source_character', '').lower().strip() == source_character.lower().strip()
        ]
        
        # Synthesize using AI
        sentiment_service = SentimentAnalyzerService(db_pool)
        synthesis = sentiment_service.synthesize_relationship(
            project_id=project_id,
            workspace_id=workspace_id,
            source_character=source_character,
            target_character=target_character,
            interactions=directional_interactions,
            model=model,
            provider=provider
        )
        
        return jsonify({
            'success': True,
            'synthesis': synthesis,
            'interactions_analyzed': len(directional_interactions)
        }), 200
        
    except Exception as e:
        logger.error(f"Error in synthesize-relationship endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auditor.route('/auditor/relationships/recalculate', methods=['POST'])
def recalculate_relationship_sentiment():
    """
    Recalculate the sentiment score for a relationship from its interactions.
    
    This recalculates and updates the relationship edge in the database
    based on current interaction data.
    
    Body:
        project_id: Required - Project UUID  
        source_character: Required - Source character name
        target_character: Required - Target character name
    
    Returns:
        {"success": true, "new_sentiment_score": X, "interaction_count": Y}
    """
    try:
        data = request.get_json() or {}
        project_id = data.get('project_id')
        source_character = data.get('source_character')
        target_character = data.get('target_character')
        
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400
        
        if not source_character or not target_character:
            return jsonify({'error': 'source_character and target_character required'}), 400
        
        from services.records_manager import RecordsManager
        from flask import current_app
        from datetime import datetime
        
        db_pool = current_app.config.get('CONNECTION_POOL')
        if not db_pool:
            return jsonify({'error': 'Database connection pool not available'}), 500
        
        records_manager = RecordsManager(db_pool)
        
        # Get all interactions for this pair
        interactions = records_manager.get_interactions_for_characters(
            project_id=project_id,
            source_character=source_character,
            target_character=target_character
        )
        
        # Filter to directional interactions (source -> target only)
        directional_interactions = [
            i for i in interactions 
            if i.get('source_character', '').lower().strip() == source_character.lower().strip()
        ]
        
        if not directional_interactions:
            return jsonify({
                'success': True,
                'new_sentiment_score': 0,
                'interaction_count': 0,
                'message': 'No directional interactions found for this pair'
            }), 200
        
        # Calculate new sentiment with weighted clamping
        raw_total = sum(i.get('sentiment_modifier', 0) for i in directional_interactions)
        interaction_count = len(directional_interactions)
        
        # Apply weighted clamping based on interaction count
        if interaction_count == 1:
            new_sentiment = max(-60, min(60, raw_total))
        elif interaction_count <= 3:
            new_sentiment = max(-80, min(80, raw_total))
        else:
            new_sentiment = max(-100, min(100, raw_total))
        
        # Find dominant tone
        tone_counts = {}
        for i in directional_interactions:
            tone = i.get('emotional_tone', 'neutral')
            tone_counts[tone] = tone_counts.get(tone, 0) + 1
        dominant_tone = max(tone_counts, key=tone_counts.get) if tone_counts else 'neutral'
        
        # Update relationship edge in database
        try:
            records_manager.upsert_relationship(
                project_id=project_id,
                source_name=source_character,
                target_name=target_character,
                relationship_type='INTERACTS_WITH',  # Will use existing type if present
                properties={
                    'sentiment_score': new_sentiment,
                    'raw_sentiment_total': raw_total,
                    'emotional_tone': dominant_tone,
                    'interaction_count': interaction_count,
                    'recalculated_at': datetime.utcnow().isoformat(),
                    'directional': True
                }
            )
        except Exception as e:
            logger.warning(f"Could not update relationship edge: {e}")
        
        return jsonify({
            'success': True,
            'new_sentiment_score': new_sentiment,
            'raw_sentiment_total': raw_total,
            'interaction_count': interaction_count,
            'dominant_tone': dominant_tone
        }), 200
        
    except Exception as e:
        logger.error(f"Error in recalculate-sentiment endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


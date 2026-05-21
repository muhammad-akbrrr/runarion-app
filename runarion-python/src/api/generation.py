from flask import Blueprint, request, jsonify, current_app, Response, stream_with_context
import json
import traceback
from pydantic import ValidationError
from src.models.request import BaseGenerationRequest
from src.services.generation_engine import GenerationEngine
from src.services.usecase_handler.mock_handler import MockHandler
from src.services.usecase_handler.story_handler import StoryHandler
from src.services.usecase_handler.graph_layout_handler import GraphLayoutHandler
from src.services.conversation_manager import ConversationManager
from src.models.response import BaseGenerationResponse
from src.models.story_generation.prompt_config import PromptConfig

generate = Blueprint("generate", __name__)

USECASE_MAP = {
    "mock" : MockHandler(),
    "story": StoryHandler(),
    "graph-layout": GraphLayoutHandler(),  # Bypasses conversation history for fresh graph generation
    # "summarizer": SummarizerHandler(),
}


@generate.route("/conversation/sync", methods=["POST"])
def sync_conversation_route():
    """
    Sync conversation history from current project content.
    
    This rebuilds conversation from the actual content in project_content table,
    ensuring conversation matches editor state. Call this when:
    - User deletes content from editor
    - User clears a chapter
    - Before generation to ensure accuracy
    
    Request body:
        project_id: ULID of the project
        
    Returns:
        200: {"success": true, "message": "..."}
        400: {"error": "..."}
        500: {"error": "..."}
    """
    json_data = request.get_json()
    project_id = json_data.get("project_id")
    
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400
    
    db_pool = current_app.config.get('CONNECTION_POOL')
    if not db_pool:
        return jsonify({"error": "Database connection pool not available"}), 500
    
    try:
        conversation_manager = ConversationManager(db_pool)
        success = conversation_manager.sync_from_content(project_id)
        
        if success:
            return jsonify({"success": True, "message": f"Conversation history synced for project {project_id}"}), 200
        else:
            return jsonify({"error": "Failed to sync conversation history"}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error syncing conversation: {e}")
        return jsonify({"error": str(e)}), 500


@generate.route("/conversation/clear", methods=["POST"])
def clear_conversation_route():
    """
    Clear all conversation history for a project.
    
    Request body:
        project_id: ULID of the project
        
    Returns:
        200: {"success": true, "message": "..."}
        400: {"error": "..."}
        500: {"error": "..."}
    """
    json_data = request.get_json()
    project_id = json_data.get("project_id")
    
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400
    
    db_pool = current_app.config.get('CONNECTION_POOL')
    if not db_pool:
        return jsonify({"error": "Database connection pool not available"}), 500
    
    try:
        conversation_manager = ConversationManager(db_pool)
        success = conversation_manager.clear_history(project_id)
        
        if success:
            return jsonify({"success": True, "message": f"Conversation history cleared for project {project_id}"}), 200
        else:
            return jsonify({"error": "Failed to clear conversation history"}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error clearing conversation: {e}")
        return jsonify({"error": str(e)}), 500

@generate.route("/generate", methods=["POST"])
def generate_text_route():
    json_data = request.get_json()
    usecase = json_data.get("usecase", "mock")

    handler = USECASE_MAP.get(usecase)
    if not handler:
        return jsonify({"error": f"Unsupported usecase '{usecase}'."}), 400

    try:
        req_obj = handler.build_request(json_data)
        engine = GenerationEngine(req_obj)
        response = engine.generate()
        return jsonify(response.model_dump()), 200
    except Exception as e:
        current_app.logger.error(f"Generation error: {type(e).__name__} - {e}")
        return jsonify({"error": "Failed to generate text.", "message": str(e)}), 500

@generate.route("/stream", methods=["POST"])
def stream_text_route():
    json_data = request.get_json()
    
    # Validate that stream is set to True
    if not json_data.get("stream", False):
        return {"error": "Stream parameter must be set to true for this endpoint"}, 400
    
    # Force stream to be True
    json_data["stream"] = True
    
    if "generation_config" in json_data:
        json_data["generation_config"]["stream"] = True
    else:
        json_data["generation_config"] = {"stream": True}
    
    usecase = json_data.get("usecase", "mock")
    
    handler = USECASE_MAP.get(usecase)
    if not handler:
        return jsonify({"error": f"Unsupported usecase '{usecase}'."}), 400
    
    try:
        req_obj = handler.build_request(json_data)
        current_app.logger.info(f"Built streaming request object: {req_obj}")
                
        if not req_obj.generation_config.stream:
            current_app.logger.warning("Stream flag was not properly set in request object, forcing it now")
            req_obj.generation_config.stream = True

        # Handle conversation history for story usecase with Gemini provider
        conversation_manager = None
        project_id = None
        chapter_order = None
        
        # Only use conversation history for story usecase with Gemini provider
        use_conversation_history = (
            usecase == "story" and 
            req_obj.caller.project_id and 
            req_obj.provider.lower() == "gemini"
        )
        
        # Handle conversation history with graceful fallback on errors
        conversation_manager = None
        project_id = None
        chapter_order = None
        
        if use_conversation_history:
            project_id = req_obj.caller.project_id
            db_pool = current_app.config.get('CONNECTION_POOL')
            
            if db_pool:
                try:
                    conversation_manager = ConversationManager(db_pool)
                    
                    # Extract chapter_order from request if available
                    chapter_order = json_data.get("chapter_order")
                    
                    # CRITICAL FIX: Sync conversation from current project content FIRST
                    # This ensures deleted content in editor is removed from conversation history
                    try:
                        conversation_manager.sync_from_content(project_id)
                        current_app.logger.info(f"Synced conversation history from project content for {project_id}")
                    except Exception as e:
                        current_app.logger.warning(f"Failed to sync conversation for project {project_id}: {e}. Using existing history.")
                    
                    # Initialize conversation if needed (non-blocking)
                    try:
                        prompt_config_data = json_data.get("prompt_config", {})
                        prompt_config = PromptConfig(**prompt_config_data) if prompt_config_data else None
                        
                        conversation_manager.initialize_conversation(
                            project_id=project_id,
                            prompt_config=prompt_config,
                            initial_prompt=req_obj.prompt,
                            chapter_order=chapter_order
                        )
                    except Exception as e:
                        current_app.logger.warning(f"Failed to initialize conversation for project {project_id}: {e}. Continuing with existing history.")
                    
                    # Load conversation history (non-blocking)
                    messages = []
                    try:
                        messages = conversation_manager.load_history(project_id)
                    except Exception as e:
                        current_app.logger.warning(f"Failed to load conversation history for project {project_id}: {e}. Using prompt-only mode.")
                        messages = []
                    
                    # Append current user prompt as new message (only if not already there)
                    user_prompt = req_obj.prompt or ""
                    if user_prompt and conversation_manager:
                        try:
                            # Check if the last message is already this prompt to avoid duplicates
                            should_append = True
                            if messages:
                                last_msg = messages[-1]
                                if last_msg.get('role') == 'user' and last_msg.get('content') == user_prompt:
                                    should_append = False
                                    current_app.logger.info(f"Skipping duplicate user prompt for project {project_id}")
                            
                            if should_append:
                                conversation_manager.append_message(
                                    project_id=project_id,
                                    role="user",
                                    content=user_prompt,
                                    chapter_order=chapter_order
                                )
                                # Reload to get updated history
                                messages = conversation_manager.load_history(project_id)
                        except Exception as e:
                            current_app.logger.warning(f"Failed to append message for project {project_id}: {e}. Using current history.")
                            # Continue with existing messages if append fails
                    
                    # Convert to Gemini format and set on provider (non-blocking)
                    if messages:
                        try:
                            gemini_messages = conversation_manager.to_gemini_format(messages)
                            
                            # Create engine first to get provider instance
                            engine = GenerationEngine(req_obj)
                            
                            # Set conversation history on provider (only GeminiProvider has this method)
                            if hasattr(engine.provider_instance, 'set_conversation_history') and gemini_messages:
                                engine.provider_instance.set_conversation_history(gemini_messages)
                                current_app.logger.info(f"Set conversation history for project {project_id} with {len(gemini_messages)} messages")
                            else:
                                # No history or provider doesn't support it, use standard flow
                                current_app.logger.info(f"No conversation history to set for project {project_id}, using prompt-only mode")
                        except Exception as e:
                            current_app.logger.warning(f"Failed to set conversation history for project {project_id}: {e}. Falling back to prompt-only mode.")
                            engine = GenerationEngine(req_obj)
                    else:
                        # No messages, use standard prompt-only flow
                        current_app.logger.info(f"No conversation history found for project {project_id}, using prompt-only mode")
                        engine = GenerationEngine(req_obj)
                        
                except Exception as e:
                    current_app.logger.error(f"Conversation history setup failed for project {project_id}: {e}. Using standard flow.")
                    engine = GenerationEngine(req_obj)
            else:
                current_app.logger.warning("Database connection pool not available, skipping conversation history")
                engine = GenerationEngine(req_obj)
        else:
            # Non-story usecase, non-Gemini provider, or no project_id - use standard flow
            engine = GenerationEngine(req_obj)

        # Return a streaming response with conversation manager for saving response
        return Response(
            stream_with_context(stream_generator(engine, conversation_manager, project_id, chapter_order)),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive',
            }
        )

    except ValidationError as e:
        current_app.logger.error(f"Validation error: {e}")
        return {"error": "Invalid request data", "details": e.errors()}, 400

@generate.route("/rewrite-selection", methods=["POST"])
def rewrite_selection_route():
    """
    Rewrite selected text with context awareness.
    
    Actions:
    - rewrite: Improve the writing quality while preserving meaning
    - humanize: Make the text sound more natural and human-written
    - custom: Apply a custom instruction to transform the text
    
    Request body:
        project_id: ULID of the project
        workspace_id: ULID of the workspace
        selected_text: The text to rewrite
        context_before: Text that comes before the selection (for flow)
        context_after: Text that comes after the selection (for flow)
        action: "rewrite" | "humanize" | "custom"
        custom_instruction: Custom instruction (only for "custom" action)
        model: AI model to use (default: gemini-2.5-flash)
        provider: AI provider (default: gemini)
        
    Returns:
        200: {"success": true, "new_text": "..."}
        400: {"error": "..."}
        500: {"error": "..."}
    """
    json_data = request.get_json()
    
    selected_text = json_data.get("selected_text", "")
    context_before = json_data.get("context_before", "")
    context_after = json_data.get("context_after", "")
    action = json_data.get("action", "rewrite")
    custom_instruction = json_data.get("custom_instruction", "")
    model = json_data.get("model", "gemini-2.5-flash")
    provider = json_data.get("provider", "gemini")
    project_id = json_data.get("project_id")
    workspace_id = json_data.get("workspace_id")
    
    if not selected_text:
        return jsonify({"error": "selected_text is required"}), 400
    
    if action not in ["rewrite", "humanize", "custom"]:
        return jsonify({"error": f"Invalid action: {action}"}), 400
    
    if action == "custom" and not custom_instruction:
        return jsonify({"error": "custom_instruction is required for custom action"}), 400
    
    try:
        # Build the prompt based on action
        if action == "rewrite":
            instruction = """Rewrite the selected text to improve clarity, flow, and style while preserving the original meaning and tone. Make it more engaging and polished."""
        elif action == "humanize":
            instruction = """Rewrite the selected text to sound more natural, conversational, and human-written. Remove any robotic or AI-like patterns. Add personality and authentic voice while maintaining the meaning."""
        else:  # custom
            instruction = custom_instruction
        
        prompt = f"""You are an expert editor helping to refine a piece of writing.

CONTEXT BEFORE THE SELECTION:
---
{context_before[-500:] if context_before else "(Beginning of document)"}
---

SELECTED TEXT TO REWRITE:
---
{selected_text}
---

CONTEXT AFTER THE SELECTION:
---
{context_after[:500] if context_after else "(End of document)"}
---

INSTRUCTION: {instruction}

IMPORTANT RULES:
1. ONLY output the rewritten text - no explanations, no quotes, no markdown formatting
2. The rewritten text must flow naturally with the context before and after
3. Maintain the same approximate length (within 20% of original)
4. Preserve any proper nouns, character names, and specific terminology
5. Keep the same tense and perspective as the original
6. Do not add new information or change the core meaning

Rewritten text:"""

        # Build the request for generation
        from src.models.request import BaseGenerationRequest, GenerationConfig
        from src.models.quota import QuotaCaller
        
        # Create a caller for the request
        caller = QuotaCaller.from_request_data(
            user_id=1,  # Default user ID (will use default API keys)
            workspace_id=workspace_id or "system",
            project_id=project_id or "system",
            session_id="rewrite-selection",
            api_keys={}  # Will use default API keys from environment
        )
        
        req_obj = BaseGenerationRequest(
            usecase="novel_pipeline",
            provider=provider,
            model=model,
            prompt=prompt,
            generation_config=GenerationConfig(
                max_output_tokens=2000,
                temperature=0.7,
                stream=False
            ),
            caller=caller
        )
        
        engine = GenerationEngine(req_obj)
        response = engine.generate(skip_quota=True)
        
        if not response or not response.text:
            return jsonify({"error": "Failed to generate rewrite"}), 500
        
        # Clean up the response - remove any accidental quotes or formatting
        new_text = response.text.strip()
        
        # Remove surrounding quotes if present
        if (new_text.startswith('"') and new_text.endswith('"')) or \
           (new_text.startswith("'") and new_text.endswith("'")):
            new_text = new_text[1:-1]
        
        current_app.logger.info(f"Rewrite successful: {len(selected_text)} chars -> {len(new_text)} chars")
        
        return jsonify({
            "success": True,
            "new_text": new_text,
            "action": action
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Rewrite error: {type(e).__name__} - {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Failed to rewrite text: {str(e)}"}), 500


@generate.route("/enhance-text", methods=["POST"])
def enhance_text_route():
    """
    Enhance text using AI with context-aware prompts based on enhancement mode.
    
    Enhancement modes:
    - story_text: Enhance story content to be more vivid and engaging
    - chat_message: Improve message clarity and structure
    - property: Enhance property descriptions to be more detailed
    - custom_instruction: Refine instructions to be clearer and actionable
    - entity_name: Improve entity names to be more evocative
    - chapter_name: Enhance chapter titles to be more compelling
    - description: Enhance descriptions to be more vivid
    - summary: Improve summaries to be more comprehensive
    
    Request body:
        text: The text to enhance
        enhancement_mode: One of the modes above
        model: AI model to use (default: gemini-2.5-flash)
        provider: AI provider (default: gemini)
        project_id: Optional project ID for context
        workspace_id: Optional workspace ID
        chapter_content: Optional chapter content (for chapter_name mode)
        
    Returns:
        200: {"success": true, "enhanced_text": "..."}
        400: {"error": "..."}
        500: {"error": "..."}
    """
    json_data = request.get_json()
    
    if not json_data:
        return jsonify({"error": "Request body is required"}), 400
    
    # Safely get text and handle None values
    text = json_data.get("text") or ""
    if isinstance(text, str):
        text = text.strip()
    else:
        text = ""
    
    enhancement_mode = json_data.get("enhancement_mode", "description")
    model = json_data.get("model", "gemini-2.5-flash")
    provider = json_data.get("provider", "gemini")
    project_id = json_data.get("project_id")
    workspace_id = json_data.get("workspace_id")
    
    # Safely get chapter_content and handle None values
    chapter_content = json_data.get("chapter_content") or ""
    if isinstance(chapter_content, str):
        chapter_content = chapter_content.strip()
    else:
        chapter_content = ""
    
    if not text:
        return jsonify({"error": "text is required"}), 400
    
    valid_modes = [
        "story_text", "chat_message", "property", "custom_instruction",
        "entity_name", "chapter_name", "description", "summary"
    ]
    if enhancement_mode not in valid_modes:
        return jsonify({"error": f"Invalid enhancement_mode. Must be one of: {', '.join(valid_modes)}"}), 400
    
    try:
        # Build context-aware prompts based on mode
        mode_prompts = {
            "story_text": """Enhance this story text to be more vivid, engaging, and polished while maintaining the author's voice and style. Improve clarity, flow, and emotional impact. Make it more immersive and compelling without changing the core meaning or plot.""",
            
            "chat_message": """Improve this message to be clearer, more helpful, and better structured. Make it more concise if it's too wordy, or more detailed if it's too brief. Ensure it communicates the intent effectively and professionally.""",
            
            "property": """Enhance this description to be more detailed, vivid, and informative. Add relevant details that would be useful for world-building or character development. Make it more engaging while keeping it accurate and relevant.""",
            
            "custom_instruction": """Refine this instruction to be clearer, more specific, and actionable. Make it easier to understand and follow. Ensure it precisely communicates what needs to be done without ambiguity.""",
            
            "entity_name": """Improve this entity name to be more evocative, memorable, and fitting for a fantasy/sci-fi story. Make it sound more unique and interesting while keeping it pronounceable and appropriate to the genre.""",
            
            "chapter_name": """Enhance this chapter title to be more compelling, intriguing, and memorable. Make it hint at the chapter's content in an engaging way. Keep it concise but impactful. The title should reflect the themes, events, or emotional tone of the chapter content provided.""",
            
            "description": """Enhance this description to be more vivid, detailed, and engaging. Add sensory details and make it more immersive. Improve clarity and flow while keeping it relevant and accurate.""",
            
            "summary": """Improve this summary to be more comprehensive, clear, and well-structured. Ensure it captures all key points effectively. Make it more engaging while maintaining accuracy and completeness."""
        }
        
        instruction = mode_prompts.get(enhancement_mode, mode_prompts["description"])
        
        # Add chapter content context for chapter_name mode
        chapter_context = ""
        if enhancement_mode == "chapter_name" and chapter_content:
            # Limit chapter content to first 5000 chars to avoid token limits
            chapter_preview = chapter_content[:5000]
            chapter_context = f"""

CHAPTER CONTENT (for context):
---
{chapter_preview}
---
"""
        
        prompt = f"""You are an expert writing assistant helping to enhance text.

TEXT TO ENHANCE:
---
{text}
---{chapter_context}
INSTRUCTION: {instruction}

IMPORTANT RULES:
1. ONLY output the enhanced text - no explanations, no quotes, no markdown formatting, no prefixes
2. Maintain the same approximate length (within 30% of original) unless the mode specifically requires expansion
3. Preserve any proper nouns, character names, and specific terminology
4. Keep the same tense and perspective as the original
5. Do not add information that contradicts or significantly changes the original meaning
6. The output should be ready to use directly - no "Here's the enhanced version:" or similar prefixes

Enhanced text:"""

        # Build the request for generation
        from src.models.request import BaseGenerationRequest, GenerationConfig
        from src.models.quota import QuotaCaller
        
        # Create a caller for the request
        caller = QuotaCaller.from_request_data(
            user_id=1,  # Default user ID (will use default API keys)
            workspace_id=workspace_id or "system",
            project_id=project_id or "system",
            session_id="enhance-text",
            api_keys={}  # Will use default API keys from environment
        )
        
        req_obj = BaseGenerationRequest(
            usecase="novel_pipeline",
            provider=provider,
            model=model,
            prompt=prompt,
            generation_config=GenerationConfig(
                max_output_tokens=2000,
                temperature=0.7,
                stream=False
            ),
            caller=caller
        )
        
        engine = GenerationEngine(req_obj)
        response = engine.generate(skip_quota=True)
        
        if not response or not response.text:
            return jsonify({"error": "Failed to generate enhancement"}), 500
        
        # Clean up the response - remove any accidental quotes or formatting
        enhanced_text = response.text.strip()
        
        # Remove common prefixes that models sometimes add
        prefixes_to_remove = [
            "Here's the enhanced text:",
            "Enhanced text:",
            "Here's the improved version:",
            "Improved version:",
            "Here's the refined text:",
            "Refined text:",
        ]
        for prefix in prefixes_to_remove:
            if enhanced_text.startswith(prefix):
                enhanced_text = enhanced_text[len(prefix):].strip()
        
        # Remove quotes if the entire response is wrapped in them
        if (enhanced_text.startswith('"') and enhanced_text.endswith('"')) or \
           (enhanced_text.startswith("'") and enhanced_text.endswith("'")):
            enhanced_text = enhanced_text[1:-1].strip()
        
        return jsonify({
            "success": True,
            "enhanced_text": enhanced_text
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in enhance-text: {type(e).__name__} - {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


def stream_generator(engine, conversation_manager=None, project_id=None, chapter_order=None):
    """
    Generator function that yields SSE formatted chunks from the streaming engine.
    Also saves conversation history after streaming completes.
    
    Args:
        engine: GenerationEngine instance
        conversation_manager: Optional ConversationManager for saving history
        project_id: Optional project ID for conversation history
        chapter_order: Optional chapter order for conversation history
    """
    generated_text = ""
    
    try:
        # Send initial message
        yield 'data: {"status": "started"}\n\n'
        
        # Stream the chunks
        for chunk in engine.stream():
            if chunk:
                if chunk.startswith("Error:"):
                    # If the chunk is an error message, send an error event
                    error_msg = {"error": chunk[7:], "status": "error"}
                    yield f'data: {json.dumps(error_msg)}\n\n'
                    break
                else:
                    # Otherwise, send the chunk and accumulate text
                    generated_text += chunk
                    yield f'data: {json.dumps({"chunk": chunk})}\n\n'
        
        # Save assistant response to conversation history if manager is available
        if conversation_manager and project_id and generated_text:
            try:
                conversation_manager.append_message(
                    project_id=project_id,
                    role="assistant",
                    content=generated_text,
                    chapter_order=chapter_order
                )
                current_app.logger.info(f"Saved assistant response to conversation history for project {project_id}")
            except Exception as e:
                current_app.logger.error(f"Failed to save conversation history: {e}")
                
        # Send completion message
        yield 'data: [DONE]\n\n'
        
    except Exception as e:
        current_app.logger.error(f"Stream generator error: {type(e).__name__} - {e}")
        current_app.logger.error(traceback.format_exc())
        error_msg = {"error": str(e), "status": "error"}
        yield f'data: {json.dumps(error_msg)}\n\n'
        yield 'data: [DONE]\n\n'

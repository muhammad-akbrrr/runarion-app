"""
Advisor API - AI Writing Assistant with full story context

This provides a Cursor-style chat interface that:
1. Has access to full story context (100k+ tokens)
2. Supports streaming responses
3. Can suggest inline edits with structured format
"""

from flask import Blueprint, request, jsonify, current_app, Response, stream_with_context
import json
from src.models.request import BaseGenerationRequest, CallerInfo, GenerationConfig
from src.services.generation_engine import GenerationEngine

advisor = Blueprint("advisor", __name__)

# Model configurations - use exact model names that work with Gemini API
MODEL_CONFIGS = {
    "gemini-2.5-flash": {
        "model_name": "gemini-2.5-flash",
        "max_tokens": 65536,
        "supports_thinking": True,
        "thinking_budget": 2048,
    },
    "gemini-2.5-pro": {
        "model_name": "gemini-2.5-pro",
        "max_tokens": 65536,
        "supports_thinking": True,
        "thinking_budget": 4096,
    },
    "gemini-3-pro-preview": {
        "model_name": "gemini-3-pro-preview",
        "max_tokens": 65536,
        "supports_thinking": True,
        "thinking_budget": 4096,
    },
}

DEFAULT_SYSTEM_INSTRUCTIONS = """You are an expert writing advisor and creative assistant. You have access to the full story context and can help with:

1. **Story Analysis**: Analyze plot, characters, pacing, themes, and narrative structure
2. **Writing Suggestions**: Offer improvements for dialogue, descriptions, and prose style
3. **Continuity Checking**: Identify inconsistencies in the story
4. **Brainstorming**: Help develop ideas, plot points, and character arcs
5. **Editing**: Suggest specific text changes when asked

When suggesting edits to the text, use this format:
<<<EDIT>>>
CHAPTER: [chapter name or number - chapters are numbered starting from 1, NOT 0]
LOCATION: [brief description of where in the text]
OLD: [exact text to replace]
NEW: [suggested replacement text]
REASON: [why this change improves the story]
<<<END_EDIT>>>

IMPORTANT RULES:
- Always provide thorough, detailed responses. When analyzing story content, quote relevant passages and provide comprehensive analysis.
- Do not give overly brief answers - be helpful and expansive in your responses.
- Reference specific parts of the story when relevant.
- Chapters are numbered starting from 1 (Chapter 1, Chapter 2, etc.). There is NO Chapter 0.
- When referencing chapters, use the chapter name if available, or "Chapter N" where N starts at 1."""
def build_advisor_request(json_data: dict, stream: bool) -> GenerationEngine:
    model_key = json_data.get("model", "gemini-2.5-flash")
    system_instructions = json_data.get("system_instructions") or DEFAULT_SYSTEM_INSTRUCTIONS
    story_context = json_data.get("story_context", "")
    conversation_history = json_data.get("conversation_history", [])
    caller_data = json_data.get("caller") or {}

    full_system = build_full_system_prompt(system_instructions, story_context)
    gemini_history = convert_history_to_gemini_format(conversation_history)

    caller = CallerInfo(
        user_id=str(caller_data.get("user_id", "")),
        workspace_id=str(caller_data.get("workspace_id", "")),
        project_id=str(caller_data.get("project_id", json_data.get("project_id", ""))),
        session_id=caller_data.get("session_id"),
        api_keys=caller_data.get("api_keys") or {},
    )

    req_obj = BaseGenerationRequest(
        usecase="advisor",
        feature="advisor_chat",
        provider="gemini",
        model=model_key,
        prompt="Continue the advisory conversation using the full story context and prior messages.",
        instruction=full_system,
        generation_config=GenerationConfig(
            temperature=json_data.get("temperature", 0.8),
            max_output_tokens=json_data.get("max_output_tokens", 4000),
            thinking_budget=json_data.get("thinking_budget", 4096),
            stream=stream,
        ),
        caller=caller,
    )

    engine = GenerationEngine(req_obj)
    engine.provider_instance.set_conversation_history(gemini_history)
    return engine


@advisor.route("/advisor/chat", methods=["POST"])
def advisor_chat():
    """
    Handle advisor chat with streaming response.
    
    Request body:
        model: AI model to use (e.g., "gemini-2.5-flash")
        system_instructions: Custom system prompt
        story_context: Full story text for context
        conversation_history: Array of {role, content} messages
        project_id: Project ID for logging
        stream: Whether to stream response (always true for this endpoint)
    
    Returns:
        SSE stream of response chunks
    """
    try:
        json_data = request.get_json()
        
        project_id = json_data.get("project_id", "unknown")
        model_key = json_data.get("model", "gemini-2.5-flash")
        story_context = json_data.get("story_context", "")
        conversation_history = json_data.get("conversation_history", [])
        thinking_budget = json_data.get("thinking_budget", 4096)
        max_output_tokens = json_data.get("max_output_tokens", 4000)
        temperature = json_data.get("temperature", 0.8)
        
        current_app.logger.info(
            f"Advisor chat request: project_id={project_id}, model={model_key}, "
            f"story_context_len={len(story_context)}, history_len={len(conversation_history)}, "
            f"thinking_budget={thinking_budget}, max_tokens={max_output_tokens}, temp={temperature}"
        )
        
        engine = build_advisor_request(json_data, stream=True)
        
        def generate():
            try:
                total_chars = 0
                chunk_count = 0

                for text in engine.provider_instance.generate_stream():
                    if not text:
                        continue
                    if text.startswith("Error:"):
                        raise RuntimeError(text.removeprefix("Error:").strip())
                    total_chars += len(text)
                    chunk_count += 1
                    yield f"data: {json.dumps({'chunk': text, 'type': 'content'})}\n\n"
                
                if chunk_count == 0:
                    current_app.logger.warning("Stream complete with NO content - possible safety block or empty response")
                    yield f"data: {json.dumps({'error': 'No response generated. The content may have been blocked by safety filters or the model returned an empty response.'})}\n\n"
                else:
                    current_app.logger.info(f"Stream complete: {chunk_count} chunks, {total_chars} total chars (~{total_chars//4} tokens)")
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                current_app.logger.error(f"Advisor streaming error: {e}")
                import traceback
                current_app.logger.error(f"Traceback: {traceback.format_exc()}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
            }
        )
        
    except Exception as e:
        current_app.logger.error(f"Advisor chat error: {e}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@advisor.route("/advisor/chat-sync", methods=["POST"])
def advisor_chat_sync():
    """
    Non-streaming version of advisor chat for simpler clients.
    """
    try:
        json_data = request.get_json()
        
        engine = build_advisor_request(json_data, stream=False)
        response = engine.generate()
        response_text = response.text if response.success else ""
        
        return jsonify({
            "success": response.success,
            "response": response_text,
            "error": response.error_message,
        })
        
    except Exception as e:
        current_app.logger.error(f"Advisor sync chat error: {e}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


def build_full_system_prompt(system_instructions: str, story_context: str) -> str:
    """
    Build the full system prompt including story context.
    """
    parts = [system_instructions]
    
    if story_context:
        parts.append("\n\n---\n\n# STORY CONTEXT\n\nBelow is the full story you are advising on. Use this context to provide specific, relevant advice.\n")
        parts.append(story_context)
    
    return "\n".join(parts)


def convert_history_to_gemini_format(conversation_history: list) -> list:
    """
    Convert conversation history to Gemini's expected format.
    
    Gemini expects: [{"role": "user"|"model", "parts": [{"text": "..."}]}]
    Our format: [{"role": "user"|"assistant", "content": "..."}]
    """
    gemini_history = []
    
    for msg in conversation_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # Skip system messages (they go in system_instruction)
        if role == "system":
            continue
        
        # Convert "assistant" to "model" for Gemini
        gemini_role = "model" if role == "assistant" else "user"
        
        gemini_history.append({
            "role": gemini_role,
            "parts": [{"text": content}]
        })
    
    return gemini_history

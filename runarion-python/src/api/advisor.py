"""
Advisor API - AI Writing Assistant with full story context

This provides a Cursor-style chat interface that:
1. Has access to full story context (100k+ tokens)
2. Supports streaming responses
3. Can suggest inline edits with structured format
"""

from flask import Blueprint, request, jsonify, current_app, Response, stream_with_context
import json
import os
from google import genai
from google.genai.types import GenerateContentConfig, SafetySetting, HarmCategory, HarmBlockThreshold, ThinkingConfig

advisor = Blueprint("advisor", __name__)

# Model configurations - use exact model names that work with Gemini API
MODEL_CONFIGS = {
    "gemini-2.0-flash": {
        "model_name": "gemini-2.0-flash",
        "max_tokens": 8192,
        "supports_thinking": False,
    },
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

# Safety settings - BLOCK_NONE for creative writing
SAFETY_SETTINGS = [
    SafetySetting(category=HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=HarmBlockThreshold.BLOCK_NONE),
    SafetySetting(category=HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=HarmBlockThreshold.BLOCK_NONE),
    SafetySetting(category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=HarmBlockThreshold.BLOCK_NONE),
    SafetySetting(category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=HarmBlockThreshold.BLOCK_NONE),
    SafetySetting(category=HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY, threshold=HarmBlockThreshold.BLOCK_NONE),
]

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


def get_gemini_client():
    """Get or create a Gemini client."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    return genai.Client(api_key=api_key)


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
        
        model_key = json_data.get("model", "gemini-2.5-flash")
        system_instructions = json_data.get("system_instructions") or DEFAULT_SYSTEM_INSTRUCTIONS
        story_context = json_data.get("story_context", "")
        conversation_history = json_data.get("conversation_history", [])
        project_id = json_data.get("project_id", "unknown")
        
        # Generation settings from request
        thinking_budget = json_data.get("thinking_budget", 4096)
        max_output_tokens = json_data.get("max_output_tokens", 4000)  # Increased default for detailed responses
        temperature = json_data.get("temperature", 0.8)
        
        current_app.logger.info(f"Advisor chat request: model={model_key}, story_context_len={len(story_context)}, history_len={len(conversation_history)}, thinking_budget={thinking_budget}, max_tokens={max_output_tokens}, temp={temperature}")
        
        # Get model config
        model_config = MODEL_CONFIGS.get(model_key, MODEL_CONFIGS["gemini-2.5-flash"])
        
        # Build the full prompt with story context
        full_system = build_full_system_prompt(system_instructions, story_context)
        
        # Convert conversation history to Gemini format
        gemini_history = convert_history_to_gemini_format(conversation_history)
        
        def generate():
            try:
                client = get_gemini_client()
                
                # Build thinking config if supported
                thinking_cfg = None
                actual_max_tokens = max_output_tokens
                
                if model_config.get("supports_thinking") and thinking_budget > 0:
                    thinking_cfg = ThinkingConfig(
                        thinking_budget=thinking_budget,
                        include_thoughts=False
                    )
                    # Add thinking budget to max tokens so model has room for both
                    actual_max_tokens = thinking_budget + max_output_tokens
                
                current_app.logger.info(f"Generation config: thinking_budget={thinking_budget}, max_output={max_output_tokens}, actual_max={actual_max_tokens}, temp={temperature}")
                
                # Build generation config
                gen_config = GenerateContentConfig(
                    system_instruction=full_system,
                    temperature=temperature,
                    max_output_tokens=actual_max_tokens,
                    safety_settings=SAFETY_SETTINGS,
                    thinking_config=thinking_cfg,
                )
                
                # Stream the response
                current_app.logger.info(f"Starting Gemini streaming with model: {model_config['model_name']}")
                
                stream = client.models.generate_content_stream(
                    model=model_config["model_name"],
                    contents=gemini_history,
                    config=gen_config,
                )
                
                total_chars = 0
                chunk_count = 0
                
                for chunk in stream:
                    try:
                        text = None
                        
                        # Method 1: Try direct text access (works for most models)
                        try:
                            if hasattr(chunk, 'text') and chunk.text:
                                text = chunk.text
                        except Exception as text_err:
                            current_app.logger.debug(f"Direct text access failed: {text_err}")
                        
                        # Method 2: Extract from candidates/parts (more reliable)
                        if not text and hasattr(chunk, 'candidates') and chunk.candidates:
                            for cand in chunk.candidates:
                                # Check for finish reason that might indicate blocked content
                                if hasattr(cand, 'finish_reason') and cand.finish_reason:
                                    current_app.logger.debug(f"Candidate finish_reason: {cand.finish_reason}")
                                
                                if hasattr(cand, 'content') and cand.content:
                                    if hasattr(cand.content, 'parts') and cand.content.parts:
                                        for part in cand.content.parts:
                                            # Skip thinking parts
                                            is_thought = getattr(part, 'thought', False)
                                            if is_thought:
                                                continue
                                            
                                            part_text = getattr(part, 'text', None)
                                            if part_text:
                                                text = part_text
                                                break
                                    if text:
                                        break
                        
                        if text:
                            total_chars += len(text)
                            chunk_count += 1
                            yield f"data: {json.dumps({'chunk': text, 'type': 'content'})}\n\n"
                        else:
                            # Log chunk structure for debugging empty responses
                            if chunk_count == 0:
                                current_app.logger.debug(f"Empty chunk received. Chunk type: {type(chunk)}, attrs: {dir(chunk)}")
                                if hasattr(chunk, 'candidates'):
                                    for i, cand in enumerate(chunk.candidates):
                                        current_app.logger.debug(f"Candidate {i}: finish_reason={getattr(cand, 'finish_reason', None)}, safety_ratings={getattr(cand, 'safety_ratings', None)}")
                                        
                    except Exception as chunk_err:
                        current_app.logger.warning(f"Chunk processing error: {chunk_err}")
                        import traceback
                        current_app.logger.debug(f"Chunk error traceback: {traceback.format_exc()}")
                        continue
                
                if chunk_count == 0:
                    current_app.logger.warning(f"Stream complete with NO content - possible safety block or empty response")
                    yield f"data: {json.dumps({'error': 'No response generated. The content may have been blocked by safety filters or the model returned an empty response.'})}\n\n"
                else:
                    current_app.logger.info(f"Stream complete: {chunk_count} chunks, {total_chars} total chars (~{total_chars//4} tokens)")
                yield f"data: [DONE]\n\n"
                
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
        
        model_key = json_data.get("model", "gemini-2.5-flash")
        system_instructions = json_data.get("system_instructions") or DEFAULT_SYSTEM_INSTRUCTIONS
        story_context = json_data.get("story_context", "")
        conversation_history = json_data.get("conversation_history", [])
        
        model_config = MODEL_CONFIGS.get(model_key, MODEL_CONFIGS["gemini-2.5-flash"])
        
        full_system = build_full_system_prompt(system_instructions, story_context)
        gemini_history = convert_history_to_gemini_format(conversation_history)
        
        client = get_gemini_client()
        
        # Build thinking config if supported
        thinking_config = None
        max_tokens = model_config["max_tokens"]
        
        if model_config.get("supports_thinking"):
            thinking_budget = model_config.get("thinking_budget", 2048)
            thinking_config = ThinkingConfig(
                thinking_budget=thinking_budget,
                include_thoughts=False
            )
            max_tokens = thinking_budget + model_config["max_tokens"]
        
        gen_config = GenerateContentConfig(
            system_instruction=full_system,
            temperature=0.8,
            max_output_tokens=max_tokens,
            safety_settings=SAFETY_SETTINGS,
            thinking_config=thinking_config,
        )
        
        response = client.models.generate_content(
            model=model_config["model_name"],
            contents=gemini_history,
            config=gen_config,
        )
        
        # Extract text from response
        response_text = ""
        if response.candidates:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                response_text = "".join(
                    part.text for part in candidate.content.parts 
                    if hasattr(part, "text") and part.text and not getattr(part, 'thought', False)
                )
        
        return jsonify({
            "success": True,
            "response": response_text,
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

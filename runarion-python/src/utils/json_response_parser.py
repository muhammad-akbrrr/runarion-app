"""
Unified JSON Response Parser for AI Generation Outputs
Handles various AI response formats consistently across all pipeline stages.
"""

import json
import re
import logging
from typing import Any, Dict, List, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)

class ResponseFormat(Enum):
    """Enumeration of possible AI response formats."""
    PLAIN_JSON = "plain_json"
    MARKDOWN_WRAPPED = "markdown_wrapped"
    MALFORMED_JSON = "malformed_json"
    EMPTY_RESPONSE = "empty_response"
    NON_JSON = "non_json"

class JSONResponseParser:
    """
    Unified parser for AI-generated JSON responses.
    Handles multiple response formats and provides consistent error handling.
    """
    
    # Common markdown wrappers
    MARKDOWN_JSON_PATTERNS = [
        (r'```json\s*(.*?)\s*```', re.DOTALL | re.IGNORECASE),
        (r'```\s*(.*?)\s*```', re.DOTALL | re.IGNORECASE),
        (r'`(.*?)`', re.DOTALL | re.IGNORECASE),
    ]
    
    # Common JSON repair patterns
    JSON_REPAIR_PATTERNS = [
        # Fix trailing commas
        (r',(\s*[}\]])', r'\1'),
        # Fix unquoted keys
        (r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":'),
        # Fix single quotes
        (r"'([^']*)'", r'"\1"'),
    ]
    
    @classmethod
    def parse_response(cls, response: Any, expected_type: str = "dict", 
                      fallback_value: Optional[Any] = None) -> tuple[Any, ResponseFormat]:
        """
        Parse AI response into JSON data with comprehensive error handling.
        
        Args:
            response: AI response object or string
            expected_type: Expected JSON type ("dict", "list", "any")
            fallback_value: Value to return if parsing fails completely
            
        Returns:
            tuple: (parsed_data, response_format)
        """
        if fallback_value is None:
            fallback_value = {} if expected_type == "dict" else []
            
        # Extract response text
        response_text = cls._extract_response_text(response)
        
        if not response_text:
            logger.warning("Empty or None response received")
            return fallback_value, ResponseFormat.EMPTY_RESPONSE
        
        # Try parsing as plain JSON first
        parsed_data, format_type = cls._parse_plain_json(response_text, expected_type)
        if parsed_data is not None:
            return parsed_data, format_type
        
        # Try extracting from markdown wrappers
        parsed_data, format_type = cls._parse_markdown_wrapped(response_text, expected_type)
        if parsed_data is not None:
            return parsed_data, format_type
        
        # Try repairing malformed JSON
        parsed_data, format_type = cls._parse_malformed_json(response_text, expected_type)
        if parsed_data is not None:
            return parsed_data, format_type

        # Fallback: try to extract the largest plausible JSON substring
        substring_parsed = cls._parse_by_substring_extraction(response_text, expected_type)
        if substring_parsed[0] is not None:
            return substring_parsed
        
        logger.error(f"Failed to parse JSON from response (full): {response_text}")
        return fallback_value, ResponseFormat.NON_JSON
    
    @classmethod
    def _extract_response_text(cls, response: Any) -> str:
        """Extract text content from various response types."""
        if response is None:
            return ""
        
        if isinstance(response, str):
            return response.strip()
        
        # Handle response objects with text attribute
        if hasattr(response, 'text'):
            text = response.text
            if isinstance(text, str):
                return text.strip()
            elif isinstance(text, (dict, list)):
                # Already parsed, convert back to JSON string for consistency
                return json.dumps(text, ensure_ascii=False)
        
        # Handle response objects with content attribute
        if hasattr(response, 'content'):
            content = response.content
            if isinstance(content, str):
                return content.strip()
        
        # Handle dict-like response objects
        if isinstance(response, dict):
            return json.dumps(response, ensure_ascii=False)
        
        # Handle list-like response objects  
        if isinstance(response, list):
            return json.dumps(response, ensure_ascii=False)
        
        # Try converting to string as last resort
        try:
            return str(response).strip()
        except Exception as e:
            logger.error(f"Failed to extract text from response: {e}")
            return ""
    
    @classmethod
    def _parse_plain_json(cls, text: str, expected_type: str) -> tuple[Optional[Any], ResponseFormat]:
        """Try parsing as plain JSON."""
        try:
            parsed = json.loads(text)
            if cls._validate_json_type(parsed, expected_type):
                logger.debug("Successfully parsed as plain JSON")
                return parsed, ResponseFormat.PLAIN_JSON
        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.debug(f"Plain JSON parsing failed: {e}")
        
        return None, ResponseFormat.PLAIN_JSON
    
    @classmethod
    def _parse_markdown_wrapped(cls, text: str, expected_type: str) -> tuple[Optional[Any], ResponseFormat]:
        """Try extracting JSON from markdown code blocks."""
        for pattern, flags in cls.MARKDOWN_JSON_PATTERNS:
            try:
                matches = re.findall(pattern, text, flags)
                if matches:
                    # Try each match until one parses successfully
                    for match in matches:
                        try:
                            parsed = json.loads(match.strip())
                            if cls._validate_json_type(parsed, expected_type):
                                logger.debug("Successfully parsed markdown-wrapped JSON")
                                return parsed, ResponseFormat.MARKDOWN_WRAPPED
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.debug(f"Markdown parsing failed: {e}")
                continue
        
        return None, ResponseFormat.MARKDOWN_WRAPPED
    
    @classmethod
    def _parse_malformed_json(cls, text: str, expected_type: str) -> tuple[Optional[Any], ResponseFormat]:
        """Try repairing and parsing malformed JSON."""
        repaired_text = text
        
        # Apply repair patterns
        for pattern, replacement in cls.JSON_REPAIR_PATTERNS:
            try:
                repaired_text = re.sub(pattern, replacement, repaired_text)
            except Exception as e:
                logger.debug(f"JSON repair pattern failed: {e}")
                continue
        
        # Try parsing repaired text
        try:
            parsed = json.loads(repaired_text)
            if cls._validate_json_type(parsed, expected_type):
                logger.debug("Successfully parsed repaired JSON")
                return parsed, ResponseFormat.MALFORMED_JSON
        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.debug(f"Malformed JSON parsing failed: {e}")
        
        return None, ResponseFormat.MALFORMED_JSON
    
    @classmethod
    def _is_likely_truncated_json(cls, json_text: str) -> bool:
        """
        Check if JSON text appears to be truncated due to token limits.
        
        Args:
            json_text: JSON text to check
            
        Returns:
            True if the JSON appears to be truncated
        """
        json_text = json_text.strip()

        # Check bracket/brace balance only (be less aggressive to avoid false positives)
        open_braces = json_text.count('{')
        close_braces = json_text.count('}')
        open_brackets = json_text.count('[')
        close_brackets = json_text.count(']')
        
        if open_braces != close_braces or open_brackets != close_brackets:
            return True
            
        return False

    @classmethod
    def _parse_by_substring_extraction(cls, text: str, expected_type: str) -> tuple[Optional[Any], ResponseFormat]:
        """As a last resort, extract the largest JSON substring and attempt to parse it.

        This handles responses where the model adds prose around JSON or uses unconventional wrappers.
        """
        try:
            # Try object-first extraction
            obj_result = cls._extract_between_matching_delimiters(text, '{', '}')
            if obj_result:
                try:
                    parsed = json.loads(obj_result)
                    if cls._validate_json_type(parsed, expected_type):
                        logger.debug("Parsed JSON via object-substring extraction")
                        return parsed, ResponseFormat.MALFORMED_JSON
                except json.JSONDecodeError:
                    pass

            # Then try array extraction
            arr_result = cls._extract_between_matching_delimiters(text, '[', ']')
            if arr_result:
                try:
                    parsed = json.loads(arr_result)
                    if cls._validate_json_type(parsed, expected_type):
                        logger.debug("Parsed JSON via array-substring extraction")
                        return parsed, ResponseFormat.MALFORMED_JSON
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.debug(f"Substring extraction parsing failed: {e}")

        return None, ResponseFormat.NON_JSON

    @staticmethod
    def _extract_between_matching_delimiters(text: str, open_char: str, close_char: str) -> Optional[str]:
        """Extract the largest balanced substring between matching delimiters.

        Uses a stack to find the earliest opening and the last matching closing delimiter,
        ensuring balanced braces/brackets even with nested structures.
        """
        start_index = None
        stack = []
        best_span = None

        for idx, ch in enumerate(text):
            if ch == open_char:
                if start_index is None:
                    start_index = idx
                stack.append(ch)
            elif ch == close_char and stack:
                stack.pop()
                if not stack and start_index is not None:
                    best_span = (start_index, idx)
                    # keep searching; we want the last complete top-level block
        if best_span:
            s, e = best_span
            return text[s:e+1].strip()
        return None
    
    @classmethod
    def _validate_json_type(cls, parsed_data: Any, expected_type: str) -> bool:
        """Validate that parsed data matches expected type."""
        if expected_type == "any":
            return True
        elif expected_type == "dict":
            return isinstance(parsed_data, dict)
        elif expected_type == "list":
            return isinstance(parsed_data, list)
        else:
            logger.warning(f"Unknown expected type: {expected_type}")
            return True
    
    @classmethod
    def validate_scene_data(cls, scenes_data: Any, min_scenes: int = 8, max_scenes: int = 20, 
                           context: Any = None) -> List[Dict[str, Any]]:
        """
        Validate and clean scene detection data specifically.
        
        Args:
            scenes_data: Parsed scenes data
            min_scenes: Minimum required scenes (overridden by context if provided)
            max_scenes: Maximum allowed scenes (overridden by context if provided)
            context: Optional execution context with dynamic configuration
            
        Returns:
            List of validated scene dictionaries
        """
        if not isinstance(scenes_data, list):
            logger.error(f"Expected scenes data to be a list, got {type(scenes_data)}")
            return []
        
        # Override min/max from context configuration if provided
        if context and hasattr(context, 'config') and context.config:
            config = context.config
            min_scenes = config.get('min_scenes', min_scenes)
            max_scenes = config.get('max_scenes', max_scenes)
        
        validated_scenes = []
        
        for i, scene in enumerate(scenes_data):
            if not isinstance(scene, dict):
                logger.warning(f"Scene {i + 1} is not a dictionary, skipping")
                continue
            
            # Ensure required fields exist
            required_fields = ['title', 'setting', 'characters', 'summary']
            scene_dict = {
                'scene_number': scene.get('scene_number', i + 1),
                'title': scene.get('title', f'Scene {i + 1}'),
                'setting': scene.get('setting', 'Unknown location'),
                'characters': scene.get('characters', []),
                'summary': scene.get('summary', ''),
                'content': scene.get('content', ''),
                'start_marker': scene.get('start_marker', ''),
                'end_marker': scene.get('end_marker', '')
            }
            
            # Validate content length (minimum 20 characters)
            if len(scene_dict['content'].strip()) >= 20:
                validated_scenes.append(scene_dict)
            else:
                logger.warning(f"Scene {i + 1} has insufficient content, skipping")
        
        # Validate scene count
        scene_count = len(validated_scenes)
        if scene_count < min_scenes:
            logger.warning(f"Scene count ({scene_count}) below minimum ({min_scenes})")
        elif scene_count > max_scenes:
            logger.warning(f"Scene count ({scene_count}) above maximum ({max_scenes})")
        
        return validated_scenes
    
    @classmethod
    def validate_analysis_data(cls, analysis_data: Any, context: Any = None) -> Dict[str, Any]:
        """
        Validate and clean scene analysis data.
        
        Args:
            analysis_data: Parsed analysis data
            
        Returns:
            Validated analysis dictionary
        """
        if not isinstance(analysis_data, dict):
            logger.warning(f"Expected analysis data to be a dict, got {type(analysis_data)}")
            analysis_data = {}
        
        validated = {
            'plot_function': analysis_data.get('plot_function', ''),
            'character_development': analysis_data.get('character_development', {}),
            'conflicts': analysis_data.get('conflicts', []),
            'themes': analysis_data.get('themes', []),
            'foreshadowing': analysis_data.get('foreshadowing', []),
            'world_building': analysis_data.get('world_building', ''),
            'dialogue_analysis': analysis_data.get('dialogue_analysis', ''),
            'pacing_notes': analysis_data.get('pacing_notes', ''),
            'overall_significance': analysis_data.get('overall_significance', '')
        }
        
        # Ensure lists are actually lists
        for key in ['conflicts', 'themes', 'foreshadowing']:
            if not isinstance(validated[key], list):
                logger.warning(f"Converting {key} from {type(validated[key])} to list")
                validated[key] = []
        
        # Ensure character_development is a dict
        if not isinstance(validated['character_development'], dict):
            logger.warning(f"Converting character_development from {type(validated['character_development'])} to dict")
            validated['character_development'] = {}
        
        return validated
    
    @classmethod
    def validate_graph_data(cls, graph_data: Any, context: Any = None) -> Dict[str, Any]:
        """
        Validate and clean graph analysis data.
        
        Args:
            graph_data: Parsed graph data
            
        Returns:
            Validated graph dictionary
        """
        if not isinstance(graph_data, dict):
            logger.warning(f"Expected graph data to be a dict, got {type(graph_data)}")
            graph_data = {}
        
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
                    'name': str(char['name']),
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
                    'name': str(loc['name']),
                    'type': 'LOCATION',
                    'description': loc.get('description', ''),
                    'atmosphere': loc.get('atmosphere', '')
                }
                validated['locations'].append(validated_loc)
        
        # Validate objects/items
        for obj in graph_data.get('objects', []):
            if isinstance(obj, dict) and obj.get('name'):
                validated_obj = {
                    'name': str(obj['name']),
                    'type': 'ITEM',
                    'description': obj.get('description', ''),
                    'significance': obj.get('significance', '')
                }
                validated['objects'].append(validated_obj)
        
        # Validate relationships
        for rel in graph_data.get('relationships', []):
            if isinstance(rel, dict) and rel.get('source') and rel.get('target'):
                validated_rel = {
                    'source': str(rel['source']),
                    'target': str(rel['target']),
                    'relationship': rel.get('relationship', 'RELATES_TO'),
                    'context': rel.get('context', ''),
                    'emotional_tone': rel.get('emotional_tone', 'neutral')
                }
                validated['relationships'].append(validated_rel)
        
        return validated

# Convenience functions for backward compatibility
def parse_scene_detection_response(response: Any, context: Any = None) -> List[Dict[str, Any]]:
    """Parse scene detection AI response."""
    parsed_data, _ = JSONResponseParser.parse_response(response, "list", [])
    return JSONResponseParser.validate_scene_data(parsed_data, context=context)

def parse_scene_analysis_response(response: Any, context: Any = None) -> Dict[str, Any]:
    """Parse scene analysis AI response."""
    parsed_data, _ = JSONResponseParser.parse_response(response, "dict", {})
    return JSONResponseParser.validate_analysis_data(parsed_data, context=context)

def parse_graph_analysis_response(response: Any, context: Any = None) -> Dict[str, Any]:
    """Parse graph analysis AI response."""
    parsed_data, _ = JSONResponseParser.parse_response(response, "dict", {})
    return JSONResponseParser.validate_graph_data(parsed_data, context=context)

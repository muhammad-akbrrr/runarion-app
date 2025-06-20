from typing import Literal, TypedDict

from models.request import BaseGenerationRequest, CallerInfo, GenerationConfig
from services.usecase_handler.base_handler import UseCaseHandler

# Prompt template for obtaining raw author style
TEMPLATE_AUTHOR_STYLE = """
{introduction}
For each aspect:
1. Explain their techniques and patterns
2. {instruction_for_example}

DIALOGUE
- How do they write conversations?
- How do they handle character voices?
- How do they balance dialogue with action/thoughts?
[{instruction_for_example}]

ACTION & COMBAT
- How do they write fight scenes?
- How do they handle action sequences?
- How do they maintain tension?
[{instruction_for_example}]

WORLDBUILDING
- How do they reveal world information?
- How do they handle exposition?
- How do they weave in history/magic?
[{instruction_for_example}]

DESCRIPTIONS
- How do they describe characters?
- How do they paint scenes?
- How do they establish atmosphere?
[{instruction_for_example}]

LITERARY TECHNIQUES
- What devices do they favor?
- How do they craft metaphors/similes?
- What word patterns do they use?
[{instruction_for_example}]

SCENE STRUCTURE
- How do they pace scenes?
- How do they handle transitions?
- How do they build/release tension?
[{instruction_for_example}]

NARRATIVE VOICE
- What's their prose style?
- What sentence patterns do they use?
- How do they control tone?
[{instruction_for_example}]
"""

# Prompt template for obtaining raw partial author style from a single passage
PARTIAL_AUTHOR_STYLE = TEMPLATE_AUTHOR_STYLE.format(
    introduction="The TEXT is a passage of an author's work. Based on the TEXT, analyze the author's style!",
    instruction_for_example="Show relevant examples from the TEXT",
)

# Prompt template for obtaining raw combined author style from multiple partial author styles
COMBINED_AUTHOR_STYLE = TEMPLATE_AUTHOR_STYLE.format(
    introduction="The TEXT contains multiple style analyses. Each analysis examines the same aspects from the same author, but from different PASSAGEs and FILEs. Based on the TEXT, analyze the author's overall style on the same aspects!",
    instruction_for_example="Show relevant examples from different PASSAGEs and FILEs in the TEXT",
)

# Prompt template for obtaining structured author style from raw combined author style
STRUCTURED_AUTHOR_STYLE = """
The TEXT contains unstructured analyses of an author's style. Based on the TEXT, extract structured information. Return a JSON object with the following structure:

{
  "techniques": {
    "dialogue": {
      "conversation_style": "how they write conversations",
      "character_voices": "how they handle different voices",
      "dialogue_balance": "how they balance dialogue with action/thoughts"
    },
    "action": {
      "fight_scenes": "how they write fights",
      "action_sequences": "how they handle action",
      "tension": "how they maintain tension"
    },
    "worldbuilding": {
      "world_reveals": "how they reveal world info",
      "exposition": "how they handle exposition",
      "history_magic": "how they weave in history/magic"
    },
    "descriptions": {
      "character_descriptions": "how they describe characters",
      "scene_painting": "how they paint scenes",
      "atmosphere": "how they establish atmosphere"
    },
    "literary": {
      "devices": "literary devices they favor",
      "metaphors": "how they craft metaphors",
      "word_patterns": "their word patterns",
      "scene_structure": "how they structure scenes",
      "transitions": "how they handle transitions",
      "pacing": "how they control pacing"
    }
  },
  "examples": {
    "dialogue": [list of quoted dialogue examples],
    "action": [list of action sequence examples],
    "worldbuilding": [list of worldbuilding examples],
    "descriptions": [list of descriptive examples],
    "literary": [list of literary technique examples]
  }
}

Extract ALL examples you can find, regardless of formatting. Look for:
- Quoted text
- Examples after "Example:" or similar markers
- Descriptive explanations of techniques
- Any text that demonstrates the technique being discussed
"""

INPUT_CONTENT = """
The TEXT:
{text}
"""


class AuthorStyleRequest(TypedDict):
    mode: Literal["partial", "combined", "structured"]
    provider: str | None
    model: str | None
    text: str
    generation_config: GenerationConfig
    caller: CallerInfo


class AuthorStyleHandler(UseCaseHandler):
    """
    A handler class to prepare generation requests for author style analysis.
    """

    def build_request(self, raw_json: AuthorStyleRequest) -> BaseGenerationRequest:
        instructions = {
            "partial": PARTIAL_AUTHOR_STYLE,
            "combined": COMBINED_AUTHOR_STYLE,
            "structured": STRUCTURED_AUTHOR_STYLE,
        }
        instruction = instructions[raw_json["mode"]]

        prompt = INPUT_CONTENT.format(text=raw_json["text"])

        return BaseGenerationRequest(
            provider=raw_json.get("provider") or "openai",
            model=raw_json.get("model"),
            prompt=prompt,
            instruction=instruction,
            generation_config=raw_json["generation_config"],
            caller=raw_json["caller"],
        )

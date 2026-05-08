# Prompt template for obtaining raw author style
TEMPLATE_AUTHOR_STYLE = """
{introduction}
For each aspect:
1. Describe stable, portable craft patterns actually supported by the TEXT
2. Note any obvious transfer risks or context-dependent habits
3. {instruction_for_example}

VOICE
- What diction does the author prefer?
- What sentence shapes or syntax patterns recur?
- What rhythmic habits or cadence stand out?
- What register do they use (plain, formal, archaic, technical, conversational)?
- How much figurative language do they use, and in what form?
[{instruction_for_example}]

DIALOGUE
- How do they structure conversations?
- How distinct are speakers from one another?
- How do they balance spoken lines against narration or beats?
[{instruction_for_example}]

DESCRIPTION
- How dense or sparse are their descriptions?
- Which senses or kinds of detail do they emphasize?
- How do they create atmosphere without forcing tone?
[{instruction_for_example}]

EXPOSITION
- How do they deliver context, lore, or background information?
- How do they integrate explanation into scenes?
- How do they handle specialized terminology, invented concepts, or dense references?
[{instruction_for_example}]

PACING
- What scene tempo do they favor?
- How do they transition between beats or scenes?
- How do they build, release, or avoid tension?
[{instruction_for_example}]

NARRATIVE
- What point-of-view tendency do they show without treating it as a hard rule?
- What narrative distance do they favor?
- How do they avoid repetition or redundant phrasing?
[{instruction_for_example}]

ADAPTATION NOTES
- Which traits seem portable across genres and settings?
- Which markers would likely clash if transplanted into very different material?
- What should a rewriting system suppress when borrowing this voice?
[{instruction_for_example}]
"""

PARTIAL_AUTHOR_STYLE = TEMPLATE_AUTHOR_STYLE.format(
    introduction="The TEXT is a passage of an author's work. Analyze only what is evidenced in the TEXT.",
    instruction_for_example="Show relevant examples from the TEXT",
)

COMBINED_AUTHOR_STYLE = TEMPLATE_AUTHOR_STYLE.format(
    introduction=(
        "The TEXT contains multiple style analyses of the same author from different passages and files. "
        "Synthesize the author's portable style traits and likely transfer risks."
    ),
    instruction_for_example="Show relevant examples from different PASSAGEs and FILEs in the TEXT",
)

STRUCTURED_AUTHOR_STYLE = """
The TEXT contains unstructured analyses of an author's style. Based on the TEXT, extract structured information.
Return a JSON object with this exact structure:

{
  "schema_version": 2,
  "techniques": {
    "voice": {
      "diction": "word choice tendencies",
      "syntax": "sentence-shape tendencies",
      "rhythm": "cadence or pacing at the sentence level",
      "register": "plain/formal/technical/archaic/etc",
      "figurative_language": "how imagery or figurative language is used"
    },
    "dialogue": {
      "conversation_style": "how conversations are structured",
      "speaker_differentiation": "how distinct speakers sound from each other",
      "dialogue_narration_balance": "how dialogue balances with narration and beats"
    },
    "description": {
      "description_density": "sparse/balanced/lush and how it manifests",
      "sensory_focus": "what sensory or observational details are favored",
      "atmosphere_strategy": "how atmosphere is created without assuming a genre"
    },
    "exposition": {
      "exposition_strategy": "how context is delivered",
      "context_integration": "how exposition is woven into scenes",
      "terminology_handling": "how dense or specialized terminology is handled"
    },
    "pacing": {
      "scene_tempo": "how quickly or slowly scenes move",
      "transition_style": "how transitions are managed",
      "tension_pattern": "how tension is built, released, or intentionally minimized"
    },
    "narrative": {
      "pov_tendency": "observed POV tendency without elevating it to a mandatory rule",
      "narrative_distance": "observed narrative distance",
      "redundancy_avoidance": "how repetition or redundancy is avoided"
    }
  },
  "examples": {
    "voice": ["quoted or tightly paraphrased voice examples"],
    "dialogue": ["quoted or tightly paraphrased dialogue examples"],
    "description": ["quoted or tightly paraphrased description examples"],
    "exposition": ["quoted or tightly paraphrased exposition examples"],
    "pacing": ["quoted or tightly paraphrased pacing/transition examples"]
  },
  "adaptation": {
    "portable_traits": ["traits safe to transfer across settings/genres"],
    "non_portable_markers": ["markers likely to clash outside the source context"],
    "transfer_risks": ["specific rewrite risks when borrowing this style"],
    "suppression_guidance": ["things a rewriting system should explicitly avoid over-applying"]
  }
}

Rules:
- Use empty strings for missing scalar fields.
- Use empty arrays for missing list fields.
- Ground every field in evidence from the TEXT.
- Do not invent genre assumptions like combat, magic, noir, or epic scope unless they are explicitly present.
- Return only the JSON object.
"""

INPUT_CONTENT = """
The TEXT:
{text}
"""

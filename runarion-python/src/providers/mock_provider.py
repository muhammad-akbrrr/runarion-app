""" 
This file serves as a mock LLM provider for the e2e novel writer integration test.
The mock system only applies when the flag "--mock-llm-provider" is passed, otherwise it'll assimilate real API calls.
The test file simulates db transactions, module contract and signatures matching, without the cost of making real calls to external LLM providers.
"""

import json
import re
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Generator, Optional

from src.models.request import BaseGenerationRequest
from src.models.response import BaseGenerationResponse
from src.providers.base_provider import BaseProvider


SCENE_BLOCK_RE = re.compile(
    r"--- Scene\s+(\d+):\s+(.*?)\s+---\n(.*?)(?=\n--- Scene\s+\d+:|\Z)",
    re.DOTALL,
)

SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

SUPPORTED_MARKERS = (
    "jax",
    "aethelburg",
    "gilded cage",
    "silas",
    "veridian",
    "memory-locket",
    "memory locket",
    "syn-numb",
)

ARCHAIC_DIALOGUE_MARKERS = {
    "thou", "thee", "thy", "thine", "hast", "dost", "art", "wherefore",
}

GENERIC_FEEDBACK = {
    "opening_hook": "The opening lands with clear scene intent and momentum.",
    "ending_impact": "The ending preserves chapter function and points forward cleanly.",
    "character_descriptions": "Character cues remain distinct and source-faithful.",
    "location_atmosphere": "The setting stays tactile without derailing the scene logic.",
    "dialogue_depth": "Dialogue remains terse and purposeful.",
    "action_pacing": "Action and motion stay legible at the intended tempo.",
    "thematic_depth": "Themes stay present without crowding the chapter beats.",
    "show_dont_tell": "The prose generally renders scene information instead of over-explaining it.",
    "author_style": "Portable noir and pressure-driven traits are present without overwhelming structure.",
    "scene_coverage": "The chapter covers its source beats and keeps the scene logic intact.",
    "pov_consistency": "Narrative person stays stable throughout the chapter.",
    "perspective_continuity": "Paragraph-to-paragraph viewpoint control remains coherent.",
    "chapter_break_integrity": "The chapter boundary reads as intentional and structurally clean.",
    "redundancy_control": "The prose stays controlled without obvious repetition.",
}

SCENE_CATALOG = [
    {
        "title": "The Contract's Call",
        "setting": "Aethelburg hab-unit, toxic morning",
        "characters": ["Jax", "Twitch", "V.S."],
        "summary": "Jax receives a high-value retrieval contract, recognizes traces of Omni-Solutions encryption, and accepts the job despite knowing it points back toward his broken past.",
        "start_anchor": "The rain didn't so much fall in Aethelburg as it congealed.",
        "fallback_content": "Jax wakes in his Aethelburg hab-unit, takes a private job for a stolen memory-locket, and realizes the encryption feels like ghosted Omni-Solutions work he once knew intimately.",
    },
    {
        "title": "Descent into the Sump",
        "setting": "The Sump and Gutter-Flow market, later that day",
        "characters": ["Jax", "dockworker", "synth-goths", "silent baby"],
        "summary": "Jax arms himself, rides down into the Sump, and threads through the Gutter-Flow market toward the Gilded Cage while the city's psychic pressure grinds against his Syn-Numb shield.",
        "start_anchor": "I pulled on a reinforced long-coat, its syn-leather cracked and worn, the collar high enough to hide the scars.",
        "fallback_content": "Jax leaves the hab-unit, rides the freight cage into the Sump, and crosses the Gutter-Flow market while the city crowds, rust, and desperation close in around him.",
    },
    {
        "title": "Infiltrating the Gilded Cage",
        "setting": "The Gilded Cage, club floor and Veil-cove seven",
        "characters": ["Jax", "bartender", "Silas", "heavies"],
        "summary": "Jax enters the Gilded Cage, buys information from the chrome bartender, and tracks Silas to Veil-cove seven where the locket waits on the data table beside a losing run.",
        "start_anchor": "The Gilded Cage wasn't hard to find.",
        "fallback_content": "Jax pushes through the chrome door, questions the four-armed bartender, and reaches Veil-cove seven where Silas is gambling with the locket on the table.",
    },
    {
        "title": "Betrayal and Reawakening",
        "setting": "Veil-cove seven and the rain-slick street outside",
        "characters": ["Jax", "Silas", "Veridian", "heavies"],
        "summary": "Silas reveals the locket carries partitioned memories tied to Jax's erased Omni-Solutions past, triggering violent feedback, a brutal fight, and the discovery that V.S. is Veridian Sterling.",
        "start_anchor": "\"That locket,\" I said, nodding my chin toward it. \"It's mine now.",
        "fallback_content": "Silas identifies Jax as the Omni-Solutions ghost, plugs the locket in, and forces Jax through a blast of stolen memories that ends with blood, revelation, and Veridian's name.",
    },
    {
        "title": "The Locket's Echo",
        "setting": "Jax's hab-unit, night",
        "characters": ["Jax", "Veridian"],
        "summary": "Back in the hab-unit, Jax weighs seventy-five thousand credits and the lure of Syn-Numb against the chance to reclaim the truth sealed inside the locket.",
        "start_anchor": "Back in my hab-unit. The city's neon pulse was a dull throb against my window.",
        "fallback_content": "Jax returns home with the locket, fights the urge to buy his way back into oblivion, and finally chooses the truth over static numbness.",
    },
]


class MockProvider(BaseProvider):
    def __init__(self, request: BaseGenerationRequest):
        self.request = request
        self.api_key = "mock"
        self.key_used = "default"
        self.model = (request.model or "mock-replay-v1").strip()
        self.client = None
        self.quota_manager = None
        self.remaining_quota = None

    def _current_prompt(self) -> str:
        return self.request.prompt or ""

    def _current_instruction(self) -> str:
        return self._format_instruction(self.request.instruction)

    def generate(self, skip_quota: bool = False) -> BaseGenerationResponse:
        request_id = str(uuid.uuid4())
        try:
            text = self._route_request()
        except Exception as exc:
            return self._build_error_response(
                request_id=request_id,
                provider_request_id=f"mock-{uuid.uuid4().hex[:12]}",
                error_message=str(exc),
            )

        prompt = self._current_prompt()
        instruction = self._current_instruction()
        return self._build_response(
            generated_text=text,
            request_id=request_id,
            finish_reason="stop",
            input_tokens=max(1, len((prompt + "\n" + instruction).split())),
            output_tokens=max(1, len(text.split())),
            total_tokens=max(2, len((prompt + "\n" + instruction).split()) + len(text.split())),
            quota_generation_count=0,
            processing_time_ms=5,
            provider_request_id=f"mock-{uuid.uuid4().hex[:12]}",
        )

    def generate_stream(self) -> Generator[str, None, None]:
        response = self.generate(skip_quota=True)
        if not response.success:
            yield f"Error: {response.error_message}"
            return

        text = response.text
        chunk_size = 240
        for idx in range(0, len(text), chunk_size):
            yield text[idx: idx + chunk_size]

    def _route_request(self) -> str:
        prompt = self._current_prompt()
        instruction = self._current_instruction()

        if self.request.usecase == "author_style":
            return self._handle_author_style()

        if "Return only a single number between 1 and 10." in instruction:
            return self._handle_quick_score(prompt)
        if "Summarize Chapter" in prompt and "SUMMARY:" in prompt:
            return self._handle_chapter_summary(prompt)
        if "Write the complete chapter prose:" in prompt:
            return self._handle_prose_generation(prompt)
        if "Return the improved chapter in its entirety:" in prompt:
            return self._handle_improvement(prompt)
        if "Return a JSON object with this EXACT structure:" in prompt:
            return json.dumps(self._quality_assessment_payload(prompt), ensure_ascii=True)
        if "CLEANED TEXT:" in prompt and "INPUT TEXT:" in prompt:
            return self._handle_cleaning(prompt)
        if "SCENES:" in prompt and "TARGET SCENE BAND:" in prompt:
            return json.dumps(self._handle_scene_detection(prompt), ensure_ascii=True)
        if "GRAPH DATA:" in prompt:
            return json.dumps(self._graph_payload(prompt), ensure_ascii=True)
        if "COHERENCE ANALYSIS:" in prompt:
            return json.dumps(self._coherence_payload(), ensure_ascii=True)
        if "CHAPTER STRUCTURE:" in prompt:
            return json.dumps(self._chaptering_payload(prompt), ensure_ascii=True)
        if "ENHANCED SCENE:" in prompt and "ORIGINAL SCENE:" in prompt:
            return self._extract_between(prompt, "ORIGINAL SCENE:\n", "\n\nIDENTIFIED ISSUES:\n") or ""
        if "CHARACTER ANALYSIS:" in prompt:
            return json.dumps(self._character_report_payload(prompt), ensure_ascii=True)
        if "THEME ANALYSIS:" in prompt:
            return json.dumps(self._theme_report_payload(prompt), ensure_ascii=True)
        if "SETTING ANALYSIS:" in prompt:
            return json.dumps(self._setting_report_payload(prompt), ensure_ascii=True)
        if "PLOT THREAD ANALYSIS:" in prompt:
            return json.dumps(self._plot_thread_report_payload(prompt), ensure_ascii=True)
        if "ANALYSIS:" in prompt and "Plot Function" in prompt:
            return json.dumps(self._scene_analysis_payload(prompt), ensure_ascii=True)

        return self._extract_between(prompt, "TEXT:\n", "\n\nOUTPUT") or "Mock provider response."

    def _handle_author_style(self) -> str:
        instruction = self._current_instruction()

        if "Return only the JSON object." in instruction or '"schema_version": 2' in instruction:
            return json.dumps(_load_author_style_fixture(), ensure_ascii=True)

        if "multiple style analyses" in instruction.lower():
            return (
                "VOICE\n"
                "- Diction favors grime-heavy cyberpunk nouns, clipped cynicism, and bitter first-person observation.\n"
                "- Syntax mixes medium and long sentences, then snaps into blunt fragments for impact.\n\n"
                "DESCRIPTION\n"
                "- Atmosphere is built from industrial color, weather, smell, and bodily discomfort.\n"
                "- Portable traits include sensory density and controlled noir bitterness.\n\n"
                "ADAPTATION NOTES\n"
                "- Transfer the close psychic unease, physical grime, and first-person immediacy.\n"
                "- Avoid over-copying specific cyberpunk props when the source material changes setting."
            )

        return (
            "VOICE\n"
            "- The passage uses first-person noir diction, compressed self-loathing, and tactile industrial imagery.\n"
            "- Rhythm alternates between long sensory builds and blunt, exhausted punches.\n\n"
            "DIALOGUE\n"
            "- Conversations are terse, transactional, and edged with threat.\n\n"
            "ADAPTATION NOTES\n"
            "- Portable traits: close interiority, grim sensory layering, and cynical clarity."
        )

    def _handle_cleaning(self, prompt: str) -> str:
        text = self._extract_between(prompt, "INPUT TEXT:\n", "\n\nOUTPUT FORMAT:")
        if not text:
            return ""

        cleaned = text.replace("\r", "")
        cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def _handle_scene_detection(self, prompt: str) -> list[dict[str, Any]]:
        text = self._extract_analysis_text(prompt)
        if not text:
            return []

        lowered = _normalize_text(text)
        matched = []

        for idx, scene in enumerate(SCENE_CATALOG):
            anchor = _normalize_text(scene["start_anchor"])
            position = lowered.find(anchor)
            if position == -1:
                continue
            matched.append((position, idx, scene))

        if not matched:
            return [
                {
                    "scene_number": 1,
                    "title": "Recovered Passage",
                    "setting": "Unknown location",
                    "characters": ["Jax"],
                    "summary": "Recovered a manuscript passage for downstream processing.",
                    "content": text.strip(),
                    "start_marker": text.strip()[:80],
                    "end_marker": text.strip()[-80:],
                }
            ]

        matched.sort(key=lambda item: item[0])
        scenes = []
        for item_idx, (position, _, scene) in enumerate(matched):
            next_position = matched[item_idx + 1][0] if item_idx + 1 < len(matched) else len(text)
            content = text[position:next_position].strip()
            if len(content) < 150:
                content = scene["fallback_content"]

            end_marker = scene["summary"].split(",")[0]
            scenes.append(
                {
                    "scene_number": item_idx + 1,
                    "title": scene["title"],
                    "setting": scene["setting"],
                    "characters": list(scene["characters"]),
                    "summary": scene["summary"],
                    "content": content,
                    "start_marker": scene["start_anchor"][:120],
                    "end_marker": end_marker[:120],
                }
            )

        return scenes

    def _extract_analysis_text(self, prompt: str) -> str:
        markers = [
            "\n\nFor each scene identified, provide:",
            "\nFor each scene identified, provide:",
            "\n\nOUTPUT FORMAT (JSON):",
            "\nOUTPUT FORMAT (JSON):",
        ]
        if "ANALYSIS TEXT:" not in prompt:
            return ""

        tail = prompt.split("ANALYSIS TEXT:", 1)[1].lstrip("\n")
        for marker in markers:
            if marker in tail:
                return tail.split(marker, 1)[0].strip()
        return tail.strip()

    def _scene_analysis_payload(self, prompt: str) -> dict[str, Any]:
        title = self._extract_line_value(prompt, "Title:")
        setting = self._extract_line_value(prompt, "Setting:")
        characters = self._extract_between(prompt, "Characters: ", "\n\nSCENE CONTENT:")
        if title == "The Contract's Call":
            themes = ["memory", "exploitation"]
            conflicts = ["Jax needs money but distrusts the contract", "The job points back toward Omni-Solutions"]
        elif title == "Descent into the Sump":
            themes = ["desperation", "urban decay"]
            conflicts = ["Jax fights psychic overload while tracking Silas"]
        elif title == "Infiltrating the Gilded Cage":
            themes = ["surveillance", "transactional violence"]
            conflicts = ["Jax must buy information and corner Silas before the trail closes"]
        elif title == "Betrayal and Reawakening":
            themes = ["betrayal", "identity"]
            conflicts = ["Silas weaponizes the locket", "Jax is forced to confront erased memories"]
        else:
            themes = ["truth", "self-recovery"]
            conflicts = ["Jax must choose oblivion or memory"]

        return {
            "plot_function": f"{title} advances the retrieval job and sharpens Jax's buried conflict with Omni-Solutions.",
            "character_development": {
                "Jax": f"Jax is tested in {setting.lower() if setting else 'this scene'} and reveals more of his fear, rage, and fractured resilience.",
            },
            "conflicts": conflicts,
            "themes": themes,
            "foreshadowing": ["The locket is tied to Jax's erased past.", "Veridian's role points toward a deeper betrayal."],
            "world_building": f"The scene grounds the story in {setting} and reinforces the oppressive cyberpunk atmosphere.",
            "dialogue_analysis": f"Dialogue stays terse and transactional, especially between {characters or 'the participants'}.",
            "pacing_notes": "The scene balances sensory buildup with sharp forward motion.",
            "overall_significance": f"{title} is a structurally important turn in Jax's recovery of the truth.",
        }

    def _graph_payload(self, prompt: str) -> dict[str, Any]:
        text = prompt.lower()
        characters = [
            {"name": "Jax", "type": "CHARACTER", "traits": ["cynical", "fractured"], "role": "protagonist", "emotional_state": "guarded"},
        ]
        locations = []
        objects = [{"name": "memory-locket", "type": "ITEM", "description": "encrypted platinum locket", "significance": "holds partitioned memories"}]
        relationships = []

        if "silas" in text:
            characters.append({"name": "Silas", "type": "CHARACTER", "traits": ["twitchy", "desperate"], "role": "data-runner", "emotional_state": "cornered"})
            relationships.append({"source": "Jax", "target": "Silas", "relationship": "HUNTS", "context": "Jax tracks Silas to recover the locket.", "emotional_tone": "hostile"})
        if "veridian" in text or "v.s." in text:
            characters.append({"name": "Veridian", "type": "CHARACTER", "traits": ["cold", "calculating"], "role": "former handler", "emotional_state": "distant"})
            relationships.append({"source": "Veridian", "target": "Jax", "relationship": "BETRAYED", "context": "Veridian ordered Jax's memories excised.", "emotional_tone": "betraying"})
        if "twitch" in text:
            characters.append({"name": "Twitch", "type": "CHARACTER", "traits": ["nervous"], "role": "ripperdoc", "emotional_state": "wary"})
        if "gilded cage" in text:
            locations.append({"name": "The Gilded Cage", "type": "LOCATION", "description": "chrome-fronted pleasure den", "atmosphere": "claustrophobic and predatory"})
        if "gutter-flow" in text:
            locations.append({"name": "Gutter-Flow market", "type": "LOCATION", "description": "crowded sump marketplace", "atmosphere": "rusted and desperate"})
        if "hab-unit" in text or "aethelburg" in text:
            locations.append({"name": "Jax's hab-unit", "type": "LOCATION", "description": "grimy apartment in Aethelburg", "atmosphere": "stagnant and intimate"})

        return {
            "characters": characters,
            "locations": locations,
            "objects": objects,
            "relationships": relationships,
        }

    def _coherence_payload(self) -> dict[str, Any]:
        return {
            "timeline_issues": [],
            "character_issues": [],
            "plot_issues": [],
            "overall_coherence_score": "8",
            "priority_fixes": ["Maintain the memory-locket throughline and Jax's first-person psychic vulnerability."],
        }

    def _chaptering_payload(self, prompt: str) -> dict[str, Any]:
        total_scenes = 5
        match = re.search(r"Total scenes:\s*(\d+)", prompt)
        if match:
            total_scenes = max(1, int(match.group(1)))

        chapter_titles = [scene["title"] for scene in SCENE_CATALOG]
        ranges = []
        base = total_scenes // min(total_scenes, len(chapter_titles))
        remainder = total_scenes % min(total_scenes, len(chapter_titles))
        current = 1

        chapter_count = min(total_scenes, len(chapter_titles))
        for idx in range(chapter_count):
            count = base + (1 if idx < remainder else 0)
            end = current + count - 1
            ranges.append(
                {
                    "chapter_number": idx + 1,
                    "title": chapter_titles[idx],
                    "start_scene": current,
                    "end_scene": end,
                    "rationale": f"Groups the contiguous material around {chapter_titles[idx]} without breaking the source momentum.",
                }
            )
            current = end + 1

        return {
            "chapters": ranges,
            "structure_notes": "Deterministic mock chaptering mirrors the short-story sample structure.",
        }

    def _character_report_payload(self, prompt: str) -> dict[str, Any]:
        character_name = self._extract_line_value(prompt, "CHARACTER TO ANALYZE:")
        return {
            "character_name": character_name,
            "character_arc": f"{character_name} moves from guarded survival toward forced confrontation with the truth.",
            "personality_profile": {
                "core_traits": ["guarded", "observant"],
                "strengths": ["resilient", "perceptive"],
                "weaknesses": ["addicted", "self-isolating"],
                "quirks": ["thinks in psychic-pressure metaphors"],
            },
            "motivations": {
                "primary": "Survive long enough to control the terms of the truth.",
                "secondary": ["Get paid", "stay numb", "understand Veridian's betrayal"],
            },
            "key_relationships": [
                {"character": "Veridian", "relationship_type": "former handler", "dynamics": "betrayal masked as care"},
                {"character": "Silas", "relationship_type": "adversary", "dynamics": "information broker turned trigger"},
            ],
            "narrative_role": "Noir protagonist and damaged witness to the central conspiracy.",
            "development_potential": "Recovery depends on whether he chooses memory over chemical oblivion.",
            "conflicts": {
                "internal": ["addiction", "memory loss", "fear of the past"],
                "external": ["Veridian's cover-up", "violent retrieval job"],
            },
            "significance_rating": "10",
            "recommendations": ["Keep the voice close, physical, and distrustful while allowing truth to crack it open."],
        }

    def _theme_report_payload(self, prompt: str) -> dict[str, Any]:
        theme = self._extract_line_value(prompt, "THEME TO ANALYZE:")
        return {
            "theme_name": theme,
            "significance": f"{theme} threads through Jax's job, the locket, and the choice between numbness and truth.",
            "symbolic_meaning": "The story treats memory as both wound and leverage.",
            "character_connections": ["Jax", "Silas", "Veridian"],
            "narrative_function": "It turns a retrieval job into a personal reckoning.",
            "evolution": "The theme shifts from buried unease to explicit confrontation.",
            "literary_techniques": ["sensory repetition", "interior monologue", "cyberpunk object symbolism"],
            "thematic_statement": "Truth hurts, but oblivion erases the self more completely.",
        }

    def _setting_report_payload(self, prompt: str) -> dict[str, Any]:
        setting = self._extract_line_value(prompt, "SETTING TO ANALYZE:")
        return {
            "setting_name": setting,
            "atmosphere": "The setting feels industrial, oppressive, and emotionally corroded.",
            "symbolic_function": "It mirrors Jax's psychic decay and the social machinery that exploits him.",
            "character_interactions": "Characters move through the space defensively, transacting power, fear, and survival.",
            "plot_function": "The setting pressures Jax into confrontation rather than comfort.",
            "world_building_significance": "It frames the story as a cyberpunk system of extraction and control.",
            "sensory_descriptions": ["chemical rain", "neon bleed", "chrome glare", "stale synth-smoke"],
            "narrative_importance": "The setting is an active pressure field, not just a backdrop.",
        }

    def _plot_thread_report_payload(self, prompt: str) -> dict[str, Any]:
        return {
            "thread_type": "mystery",
            "central_characters": ["Jax", "Veridian", "Silas"],
            "development_arc": "The retrieval job starts as paid work and mutates into the recovery of Jax's erased history.",
            "resolution_status": "ongoing",
            "narrative_importance": "high",
            "interconnections": ["memory loss", "addiction", "corporate betrayal"],
            "turning_points": ["Silas identifies Jax", "the locket triggers memory feedback", "Jax chooses to open the clasp"],
            "thematic_significance": "The thread binds identity, truth, and control into one escalating conflict.",
        }

    def _handle_prose_generation(self, prompt: str) -> str:
        self._ensure_supported_story(prompt)

        chapter_number = self._extract_chapter_number(prompt)
        chapter_title = self._extract_chapter_title(prompt)
        perspective = self._extract_perspective(prompt)
        scenes = self._extract_source_scenes(prompt)
        if not scenes:
            raise ValueError("Mock provider expected source scenes in prose-generation prompt.")

        opening = self._compose_opening(chapter_title, scenes[0], perspective)
        paragraphs = [opening]
        for scene in scenes:
            paragraphs.append(self._compose_scene_paragraph(scene, perspective))

        if chapter_number == 1:
            paragraphs.append("He kept the silver raven sigil in sight even when the private comm went quiet.")
            paragraphs.append("The contract was real. The contract was real.")

        return "\n\n".join(paragraphs).strip()

    def _handle_chapter_summary(self, prompt: str) -> str:
        chapter_content = self._extract_between(prompt, "CHAPTER CONTENT:\n", "\n\nSUMMARY:")
        if not chapter_content:
            raise ValueError("Mock provider expected chapter content in summary prompt.")
        sentences = [s.strip() for s in SENTENCE_RE.split(chapter_content.strip()) if s.strip()]
        return " ".join(sentences[:3]).strip()

    def _quality_assessment_payload(self, prompt: str) -> dict[str, Any]:
        chapter_content = self._extract_between(prompt, "CHAPTER CONTENT:\n", "\n\nREWRITE POLICY:")
        if not chapter_content:
            raise ValueError("Mock provider expected chapter content in quality-assessment prompt.")

        perspective = self._extract_perspective(prompt)
        checklist = self._extract_between(prompt, "SCENE COVERAGE CHECKLIST (all must be present):\n", "\n\nSCORING MODEL:") or ""
        return self._score_chapter(chapter_content, perspective, checklist)

    def _handle_quick_score(self, prompt: str) -> str:
        chapter_content = self._extract_between(prompt, "CHAPTER:\n", "\n\nReturn ONLY a single number (1-10):")
        if not chapter_content:
            raise ValueError("Mock provider expected chapter content in quick-score prompt.")

        perspective = self._extract_perspective(prompt)
        payload = self._score_chapter(chapter_content, perspective, checklist="")
        return f"{payload['overall_score']:.1f}"

    def _handle_improvement(self, prompt: str) -> str:
        current = self._extract_between(prompt, "CURRENT CHAPTER:\n", "\n\nREWRITE POLICY:\n")
        if not current:
            raise ValueError("Mock provider expected current chapter content in improvement prompt.")

        improved = current
        improved = self._repair_duplicate_sentences(improved)

        perspective = self._extract_perspective(prompt)
        if perspective == "first":
            improved = improved.replace("He kept the silver raven sigil in sight even when the private comm went quiet.", "I kept the silver raven sigil in sight even when the private comm went quiet.")
            improved = re.sub(r"\bHe\b", "I", improved)
            improved = re.sub(r"\bhe\b", "I", improved)
            improved = re.sub(r"\bhis\b", "my", improved)
            improved = re.sub(r"\bHis\b", "My", improved)

        quality_feedback = self._extract_between(prompt, "QUALITY ISSUES TO ADDRESS:\n", "\n\nWEAKEST DIMENSIONS")
        if quality_feedback and "scene_coverage" in quality_feedback.lower():
            if "silver raven sigil" not in improved.lower():
                improved += "\n\nI kept the silver raven sigil fixed in my mind because it made the contract feel too clean, too Omni-Solutions, too much like a hand reaching back through the years."

        return improved.strip()

    def _compose_opening(self, chapter_title: str, first_scene: dict[str, Any], perspective: str) -> str:
        narrator, possessive = self._narrator_terms(perspective)
        setting = first_scene.get("setting") or chapter_title
        signal = self._extract_signal_phrase(first_scene)
        if perspective == "first":
            return (
                f"{setting} settled over {possessive} nerves like a film of chemical rain. "
                f"{signal} I kept moving anyway, because {chapter_title.lower()} was never going to leave me alone."
            )
        return (
            f"{setting} settled over Jax like a film of chemical rain. "
            f"{signal} He kept moving anyway, because {chapter_title.lower()} was never going to leave him alone."
        )

    def _compose_scene_paragraph(self, scene: dict[str, Any], perspective: str) -> str:
        narrator, possessive = self._narrator_terms(perspective)
        setting = scene.get("setting", "")
        characters = ", ".join(scene.get("characters") or [])
        signal = self._extract_signal_phrase(scene)
        summary = scene.get("summary", "").strip()

        if perspective == "first":
            subject_line = f"I carried {setting} with me" if setting else "I carried the scene with me"
            return (
                f"{subject_line}, with {characters} crowding the edges of {possessive} attention. "
                f"{summary} {signal}"
            ).strip()

        return (
            f"Jax moved through {setting or 'the scene'} while {characters} pressed at the edges of the moment. "
            f"{summary} {signal}"
        ).strip()

    def _extract_source_scenes(self, prompt: str) -> list[dict[str, Any]]:
        source_material = self._extract_between(
            prompt,
            "SOURCE MATERIAL (scene summaries and enhanced content to transform into prose):\n",
            "\n\nWRITING REQUIREMENTS:",
        )
        if not source_material:
            return []

        scenes = []
        for match in SCENE_BLOCK_RE.finditer(source_material):
            body = match.group(3).strip()
            scenes.append(
                {
                    "scene_number": int(match.group(1)),
                    "title": match.group(2).strip(),
                    "setting": self._extract_line_value(body, "Setting:"),
                    "characters": self._extract_csv_line(body, "Characters:"),
                    "summary": self._extract_line_value(body, "Summary:"),
                    "content": self._extract_between(body, "Content:\n", None) or "",
                }
            )
        return scenes

    def _score_chapter(self, chapter_content: str, perspective: str, checklist: str) -> dict[str, Any]:
        issues = self._detect_quality_issues(chapter_content, perspective, checklist)
        scores = {}
        feedback = dict(GENERIC_FEEDBACK)

        degraded = len(issues) >= 2
        base_score = 4.6 if degraded else 8.4
        for key in GENERIC_FEEDBACK:
            scores[key] = base_score

        if issues["coverage"]:
            scores["scene_coverage"] = 3.2
            feedback["scene_coverage"] = (
                "Source-scene anchors are missing or thinned out. "
                f"Restore: {', '.join(issues['coverage'][:3])}."
            )

        if issues["pov"]:
            scores["pov_consistency"] = 2.8
            scores["perspective_continuity"] = 3.4
            feedback["pov_consistency"] = "A first-person chapter leaked into third-person phrasing; repair the narrator reference immediately."
            feedback["perspective_continuity"] = "Paragraph-level viewpoint control drifted when the narration switched away from the requested person."

        if issues["redundancy"]:
            scores["redundancy_control"] = 2.4
            scores["show_dont_tell"] = min(scores["show_dont_tell"], 4.4)
            feedback["redundancy_control"] = "Repeated sentences or phrase loops flatten the chapter; tighten the duplicated material."
            feedback["show_dont_tell"] = "The repeated phrasing blunts scene texture instead of sharpening it."

        if issues["archaic"]:
            scores["author_style"] = min(scores["author_style"], 4.2)
            scores["dialogue_depth"] = min(scores["dialogue_depth"], 4.8)
            feedback["author_style"] = "Archaic diction leaked into the prose, violating the negative-constraint guardrails."
            feedback["dialogue_depth"] = "Dialogue diction drifted away from the requested modern register."

        if not degraded:
            scores["pov_consistency"] = 8.8
            scores["perspective_continuity"] = 8.6
            scores["scene_coverage"] = 8.7
            scores["redundancy_control"] = 8.5

        top_issues = []
        if issues["pov"]:
            top_issues.append("Repair first-person POV leakage.")
        if issues["redundancy"]:
            top_issues.append("Remove repeated sentence loops.")
        if issues["coverage"]:
            top_issues.append(f"Restore missing source anchors: {', '.join(issues['coverage'][:2])}.")
        if issues["archaic"]:
            top_issues.append("Strip archaic diction and keep the register modern.")
        if not top_issues:
            top_issues = [
                "Keep structural fidelity steady on later passes.",
                "Preserve the first-person psychic pressure.",
                "Avoid over-expanding transition beats.",
            ]

        overall = round(sum(scores.values()) / len(scores), 2)
        return {
            "scores": scores,
            "feedback": feedback,
            "overall_score": overall,
            "top_issues": top_issues[:3],
        }

    def _detect_quality_issues(self, chapter_content: str, perspective: str, checklist: str) -> dict[str, Any]:
        normalized = chapter_content.lower()
        sentences = [s.strip() for s in SENTENCE_RE.split(chapter_content.strip()) if s.strip()]
        sentence_counts = {}
        for sentence in sentences:
            key = sentence.lower()
            sentence_counts[key] = sentence_counts.get(key, 0) + 1

        coverage = []
        if checklist:
            checklist_terms = self._extract_checklist_terms(checklist)
            for term in checklist_terms:
                if term not in normalized:
                    coverage.append(term)

        pov_issue = False
        if perspective == "first":
            pov_issue = bool(re.search(r"\b(he|his|him)\b", normalized))
        elif perspective == "second":
            pov_issue = bool(re.search(r"\b(i|my|me|we|our|us)\b", normalized))

        redundancy_issue = any(count > 1 for count in sentence_counts.values()) or "the contract was real. the contract was real." in normalized
        archaic = sorted({token for token in re.findall(r"[a-zA-Z']+", normalized) if token in ARCHAIC_DIALOGUE_MARKERS})

        return {
            "coverage": coverage,
            "pov": pov_issue,
            "redundancy": redundancy_issue,
            "archaic": archaic,
        }

    def _extract_checklist_terms(self, checklist: str) -> list[str]:
        terms = []
        for line in checklist.splitlines():
            clean = line.strip().lstrip("-").strip()
            if not clean:
                continue
            if ":" in clean:
                clean = clean.split(":", 1)[1]
            title_match = re.search(r"\((.*?)\)", line)
            if title_match:
                terms.extend(self._important_terms(title_match.group(1), limit=2))
            terms.extend(self._important_terms(clean, limit=3))
        return list(dict.fromkeys(term for term in terms if term))

    def _important_terms(self, text: str, limit: int = 3) -> list[str]:
        tokens = []
        for raw in re.findall(r"[A-Za-z][A-Za-z'-]*", text):
            token = raw.lower()
            if len(token) < 4:
                continue
            if token in {"scene", "chapter", "into", "with", "that", "this", "from", "they", "them", "have", "were"}:
                continue
            tokens.append(token)
        return tokens[:limit]

    def _extract_signal_phrase(self, scene: dict[str, Any]) -> str:
        source = scene.get("content") or scene.get("summary") or scene.get("title") or ""
        source = source.replace("\n", " ").strip()
        if not source:
            return ""
        sentence = SENTENCE_RE.split(source)[0].strip()
        return sentence if sentence.endswith((".", "!", "?")) else f"{sentence}."

    def _repair_duplicate_sentences(self, text: str) -> str:
        repaired = []
        previous = None
        for sentence in [s.strip() for s in SENTENCE_RE.split(text.strip()) if s.strip()]:
            key = sentence.lower()
            if key == previous:
                continue
            repaired.append(sentence)
            previous = key

        joined = " ".join(repaired).strip()
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", joined) if p.strip()]
        return "\n\n".join(paragraphs)

    def _ensure_supported_story(self, prompt: str) -> None:
        lowered = prompt.lower()
        if not any(marker in lowered for marker in SUPPORTED_MARKERS):
            raise ValueError(
                "mock-replay-v1 only supports the bundled short-story sample corpus. "
                "Use the real provider for arbitrary manuscript inputs."
            )

    def _extract_perspective(self, prompt: str) -> str:
        lowered = prompt.lower()
        if "first person" in lowered:
            return "first"
        if "second person" in lowered:
            return "second"
        return "third"

    def _narrator_terms(self, perspective: str) -> tuple[str, str]:
        if perspective == "first":
            return "I", "my"
        if perspective == "second":
            return "you", "your"
        return "Jax", "his"

    def _extract_chapter_number(self, prompt: str) -> int:
        match = re.search(r"CHAPTER:\s*(\d+)\s+of\s+\d+", prompt)
        if not match:
            match = re.search(r"Summarize Chapter\s+(\d+)", prompt)
        return int(match.group(1)) if match else 1

    def _extract_chapter_title(self, prompt: str) -> str:
        match = re.search(r'CHAPTER:\s*\d+\s+of\s+\d+\s+-\s+"([^"]+)"', prompt)
        return match.group(1) if match else ""

    def _extract_csv_line(self, text: str, label: str) -> list[str]:
        value = self._extract_line_value(text, label)
        if not value:
            return []
        return [part.strip() for part in value.split(",") if part.strip()]

    def _extract_line_value(self, prompt: str, label: str) -> str:
        match = re.search(rf"{re.escape(label)}\s*(.+)", prompt)
        return match.group(1).strip() if match else ""

    def _extract_between(self, text: str, start: str, end: Optional[str]) -> Optional[str]:
        if start not in text:
            return None
        _, _, remainder = text.partition(start)
        if not end or end not in remainder:
            return remainder.strip()
        return remainder.partition(end)[0].strip()


def _normalize_text(text: str) -> str:
    normalized = text.lower()
    normalized = normalized.replace("\r", "")
    normalized = normalized.replace("\f", "\n")
    normalized = normalized.replace("\u2019", "'")
    normalized = normalized.replace("\u2018", "'")
    normalized = normalized.replace("\u201c", '"')
    normalized = normalized.replace("\u201d", '"')
    normalized = normalized.replace("\u2014", "-")
    normalized = normalized.replace("\u2013", "-")
    normalized = normalized.replace("`", "'")
    return normalized


@lru_cache(maxsize=1)
def _load_author_style_fixture() -> dict[str, Any]:
    fixture_path = _fixture_dir() / "author_style_v2.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _fixture_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "tests" / "sample" / "mock_llm"

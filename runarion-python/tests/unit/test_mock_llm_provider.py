import json

from src.models.request import BaseGenerationRequest, CallerInfo, GenerationConfig
from src.providers.mock_provider import MockProvider
from src.services.generation_engine import GenerationEngine
from src.services.novel_writer.prompt_template import NovelWriterPrompts
from src.services.style_analyzer.prompt_template import STRUCTURED_AUTHOR_STYLE


def _build_request(prompt: str, instruction: str = "", usecase: str = "novel_pipeline"):
    return BaseGenerationRequest(
        usecase=usecase,
        provider="mock",
        model="mock-replay-v1",
        prompt=prompt,
        instruction=instruction,
        generation_config=GenerationConfig(max_output_tokens=1024),
        caller=CallerInfo(
            user_id="1",
            workspace_id="ws-1",
            project_id="proj-1",
            api_keys={},
            session_id="test-session",
        ),
    )


def _scene_block(content: str) -> str:
    return (
        "--- Scene 1: The Contract's Call ---\n"
        "Setting: Aethelburg hab-unit, toxic morning\n"
        "Characters: Jax, Twitch, V.S.\n"
        "Summary: Jax receives a high-value retrieval contract and recognizes Omni-Solutions encryption.\n"
        f"Content:\n{content}"
    )


def _build_quick_score_prompt(chapter_content: str) -> str:
    return (
        "Rate how well this chapter satisfies the rewrite policy on a scale of 1-10. "
        "Consider structural fidelity, policy alignment, negative-constraint compliance, "
        "perspective stability, and controlled prose.\n\n"
        "REWRITE POLICY:\nPreserve structure and explicit constraints.\n\n"
        f"CHAPTER:\n{chapter_content}\n\n"
        "Return ONLY a single number (1-10):"
    )


def test_generation_engine_registers_mock_provider():
    engine = GenerationEngine(_build_request(prompt="Summarize Chapter 1\n\nSUMMARY:"))
    assert isinstance(engine.provider_instance, MockProvider)


def test_mock_provider_returns_prompt_derived_chapter_prose():
    prompt = NovelWriterPrompts.get_prose_generation_prompt().format(
        chapter_number=2,
        total_chapters=5,
        chapter_title="The Contract's Call",
        chapter_position_guidance="Opening chapter.",
        rewrite_policy_guidance="Preserve structure.",
        negative_constraints="Avoid melodrama.",
        author_style_weight="Balanced",
        author_style_instructions="Use portable traits only.",
        writing_perspective_instruction="Write in first person.",
        previous_chapter_summaries="None.",
        character_profiles="Jax",
        location_profiles="Aethelburg hab-unit",
        active_plot_threads="memory-locket retrieval",
        scene_content=_scene_block("The blue archive wafer hissed in my palm while the silver raven sigil kept blinking."),
        target_word_count=1000,
    )
    response = GenerationEngine(_build_request(prompt=prompt)).generate(skip_quota=True)

    assert response.success is True
    assert "blue archive wafer hissed in my palm" in response.text
    assert "silver raven sigil" in response.text


def test_mock_provider_chapter_prose_changes_with_scene_payload():
    prompt_a = NovelWriterPrompts.get_prose_generation_prompt().format(
        chapter_number=2,
        total_chapters=5,
        chapter_title="The Contract's Call",
        chapter_position_guidance="Opening chapter.",
        rewrite_policy_guidance="Preserve structure.",
        negative_constraints="Avoid melodrama.",
        author_style_weight="Balanced",
        author_style_instructions="Use portable traits only.",
        writing_perspective_instruction="Write in first person.",
        previous_chapter_summaries="None.",
        character_profiles="Jax",
        location_profiles="Aethelburg hab-unit",
        active_plot_threads="memory-locket retrieval",
        scene_content=_scene_block("The chrome docket burned against my wrist when Twitch forwarded the contract."),
        target_word_count=1000,
    )
    prompt_b = prompt_a.replace("chrome docket", "archive wafer")

    response_a = GenerationEngine(_build_request(prompt=prompt_a)).generate(skip_quota=True)
    response_b = GenerationEngine(_build_request(prompt=prompt_b)).generate(skip_quota=True)

    assert response_a.success is True
    assert response_b.success is True
    assert response_a.text != response_b.text


def test_mock_provider_returns_content_sensitive_quality_assessment_json():
    flawed_chapter = (
        "I took the contract from the silver raven sigil and tried to stay steady.\n\n"
        "He kept the silver raven sigil in sight even when the private comm went quiet.\n\n"
        "The contract was real. The contract was real."
    )
    prompt = NovelWriterPrompts.get_quality_assessment_prompt().format(
        chapter_content=flawed_chapter,
        rewrite_policy_guidance="Preserve structure.",
        negative_constraints="Avoid melodrama.",
        author_style_reference="Portable traits only.",
        writing_perspective_instruction="Write in first person.",
        scene_coverage_checklist="- Scene 1 (The Contract's Call): silver raven sigil Omni-Solutions contract",
    )
    response = GenerationEngine(_build_request(prompt=prompt)).generate(skip_quota=True)
    payload = json.loads(response.text)

    assert payload["overall_score"] < 6.0
    assert payload["scores"]["pov_consistency"] < 4.0
    assert payload["scores"]["redundancy_control"] < 4.0
    assert "first-person chapter leaked" in payload["feedback"]["pov_consistency"]


def test_mock_provider_improvement_raises_quick_score():
    flawed_chapter = (
        "I took the contract from the silver raven sigil and tried to stay steady.\n\n"
        "He kept the silver raven sigil in sight even when the private comm went quiet.\n\n"
        "The contract was real. The contract was real."
    )
    score_request = _build_request(
        prompt=_build_quick_score_prompt(flawed_chapter),
        instruction="Return only a single number between 1 and 10.",
    )
    baseline = float(GenerationEngine(score_request).generate(skip_quota=True).text)

    prompt = NovelWriterPrompts.get_improvement_prompt().format(
        chapter_content=flawed_chapter,
        rewrite_policy_guidance="Repair only identified structural and stylistic issues.",
        negative_constraints="Avoid melodrama.",
        quality_feedback="- pov_consistency (score: 2.8/10): A first-person chapter leaked into third-person phrasing; repair the narrator reference immediately.\n- redundancy_control (score: 2.4/10): Repeated sentences flatten the chapter; tighten the duplicated material.",
        weak_dimensions="pov_consistency (2.8/10), redundancy_control (2.4/10)",
        expansion_guidance="- Fix POV leakage.\n- Remove duplicate sentences.",
        revision_mode_guidance="Use BALANCED_REWRITE mode. Keep revisions targeted and structurally faithful.",
        author_style_examples="No specific author style examples available for weak areas.",
        writing_perspective_instruction="Write in first person.",
    )
    improved = GenerationEngine(_build_request(prompt=prompt)).generate(skip_quota=True)

    rescored_request = _build_request(
        prompt=_build_quick_score_prompt(improved.text),
        instruction="Return only a single number between 1 and 10.",
    )
    rescored = float(GenerationEngine(rescored_request).generate(skip_quota=True).text)

    assert improved.success is True
    assert "He kept the silver raven sigil" not in improved.text
    assert improved.text.count("The contract was real.") == 1
    assert rescored > baseline


def test_mock_provider_returns_structured_author_style_v2():
    response = GenerationEngine(
        _build_request(
            prompt="The TEXT:\nSample voice analysis",
            instruction=STRUCTURED_AUTHOR_STYLE,
            usecase="author_style",
        )
    ).generate(skip_quota=True)
    payload = json.loads(response.text)

    assert payload["schema_version"] == 2
    assert "voice" in payload["techniques"]
    assert payload["adaptation"]["portable_traits"]


def test_mock_provider_returns_scene_detection_json():
    prompt = (
        "You are analyzing manuscript structure to identify scene boundaries from the source text.\n\n"
        "TARGET SCENE BAND:\n"
        "- Preferred target: 5 scenes\n"
        "- Soft minimum: 2 scenes\n"
        "- Soft maximum: 8 scenes\n\n"
        "ANALYSIS TEXT:\n"
        "The rain didn't so much fall in Aethelburg as it congealed.\n\n"
        "I pulled on a reinforced long-coat, its syn-leather cracked and worn, the collar high enough to hide the scars.\n\n"
        "The Gilded Cage wasn't hard to find.\n\n"
        "\"That locket,\" I said, nodding my chin toward it. \"It's mine now.\"\n\n"
        "Back in my hab-unit. The city's neon pulse was a dull throb against my window.\n\n"
        "For each scene identified, provide:\n"
        "SCENES:"
    )
    request = _build_request(prompt=prompt)
    request.generation_config.response_mime_type = "application/json"
    response = GenerationEngine(request).generate(skip_quota=True)
    payload = json.loads(response.text)

    assert len(payload) == 5
    assert payload[0]["title"] == "The Contract's Call"
    assert payload[-1]["title"] == "The Locket's Echo"

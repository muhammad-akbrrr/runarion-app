"""
Helpers for compiling a coarse rewrite policy into reusable prompt guidance.
"""

from dataclasses import dataclass
from typing import Optional

from src.models.request import RewritePolicy
from src.models.style_analyzer.author_style import AuthorStyle


@dataclass
class CompiledRewritePolicy:
    style_transfer_strength: str
    style_source_priority: str
    negative_constraints: list[str]
    generation_guidance: str
    assessment_guidance: str
    improvement_guidance: str
    improvement_mode: str
    improvement_mode_guidance: str
    author_style_guidance: str
    author_style_weight: str
    negative_constraints_block: str


def _build_negative_constraints_block(negative_constraints: list[str]) -> str:
    if not negative_constraints:
        return "No explicit negative style constraints."
    return "\n".join(f"- {item}" for item in negative_constraints)


def _style_transfer_instruction(strength: str) -> str:
    mapping = {
        "low": (
            "Apply only light author-style transfer. Preserve the manuscript's native "
            "surface texture unless a source sentence clearly benefits from adaptation."
        ),
        "medium": (
            "Blend the author's portable traits with the manuscript's existing voice. "
            "Do not flatten the manuscript into imitation."
        ),
        "high": (
            "Apply strong author-style transfer using only portable traits. "
            "Keep plot structure, perspective, and user guardrails intact."
        ),
    }
    return mapping.get(strength, mapping["medium"])


def _source_priority_instruction(priority: str) -> str:
    mapping = {
        "preserve_manuscript": (
            "When manuscript style and author style conflict, preserve manuscript surface choices "
            "unless the user explicitly requested otherwise."
        ),
        "balanced": (
            "When manuscript style and author style conflict, rebalance toward a coherent hybrid "
            "without forcing either source to dominate."
        ),
        "favor_author": (
            "When manuscript style and author style conflict, prefer the author's portable traits "
            "while keeping manuscript structure and user guardrails unchanged."
        ),
    }
    return mapping.get(priority, mapping["balanced"])


def _author_style_weight(priority: str, strength: str) -> str:
    if priority == "preserve_manuscript":
        return "Use author style as optional seasoning, not as the main driver."
    if priority == "favor_author" and strength == "high":
        return "Use author style as the dominant surface influence, limited by portable-trait rules."
    if priority == "favor_author":
        return "Use author style as the main surface influence, but do not override structural invariants."
    if strength == "low":
        return "Use author style selectively and minimally."
    return "Use author style as a balanced surface influence."


def _author_style_guidance(author_style: Optional[AuthorStyle]) -> str:
    if author_style is None:
        return (
            "No author style profile is available. Preserve manuscript-native style characteristics "
            "rather than inventing a new literary default."
        )

    adaptation = author_style.adaptation
    parts = []

    if adaptation.portable_traits:
        parts.append(
            "PORTABLE TRAITS:\n" + "\n".join(f"- {item}" for item in adaptation.portable_traits)
        )
    if adaptation.non_portable_markers:
        parts.append(
            "NON-PORTABLE MARKERS:\n" + "\n".join(f"- {item}" for item in adaptation.non_portable_markers)
        )
    if adaptation.transfer_risks:
        parts.append(
            "TRANSFER RISKS:\n" + "\n".join(f"- {item}" for item in adaptation.transfer_risks)
        )
    if adaptation.suppression_guidance:
        parts.append(
            "SUPPRESSION GUIDANCE:\n" + "\n".join(f"- {item}" for item in adaptation.suppression_guidance)
        )

    if not parts:
        return (
            "Use only portable author-style traits and avoid imposing surface choices that clash "
            "with manuscript structure or user guardrails."
        )
    return "\n\n".join(parts)


def _improvement_mode_guidance(strength: str) -> tuple[str, str]:
    mapping = {
        "low": (
            "preserve_and_tighten",
            "Use PRESERVE_AND_TIGHTEN mode. Keep the manuscript's surface texture intact, "
            "tighten only where the assessment found a concrete issue, and avoid broad expansion.",
        ),
        "medium": (
            "balanced_rewrite",
            "Use BALANCED_REWRITE mode. Rebalance weak areas with selective expansion or tightening, "
            "but keep the manuscript's baseline cadence and density recognizable.",
        ),
        "high": (
            "strong_transfer_with_guardrails",
            "Use STRONG_TRANSFER_WITH_GUARDRAILS mode. Borrow portable author-style traits more assertively, "
            "but expand only where required by missing coverage, clarity, or policy alignment.",
        ),
    }
    return mapping.get(strength, mapping["medium"])


def compile_rewrite_policy(
    rewrite_policy: Optional[RewritePolicy | dict],
    author_style: Optional[AuthorStyle] = None,
) -> CompiledRewritePolicy:
    policy = rewrite_policy if isinstance(rewrite_policy, RewritePolicy) else RewritePolicy(**(rewrite_policy or {}))
    negative_constraints_block = _build_negative_constraints_block(policy.negative_constraints)
    transfer_instruction = _style_transfer_instruction(policy.style_transfer_strength)
    priority_instruction = _source_priority_instruction(policy.style_source_priority)
    author_style_weight = _author_style_weight(
        policy.style_source_priority, policy.style_transfer_strength
    )
    improvement_mode, improvement_mode_guidance = _improvement_mode_guidance(
        policy.style_transfer_strength
    )

    return CompiledRewritePolicy(
        style_transfer_strength=policy.style_transfer_strength,
        style_source_priority=policy.style_source_priority,
        negative_constraints=policy.negative_constraints,
        generation_guidance=(
            f"{transfer_instruction}\n{priority_instruction}\n"
            "Precedence order: explicit perspective and structural invariants first, "
            "user negative constraints second, portable author-style traits third.\n"
            "Preserve scene order, chapter structure, plot events, and explicit perspective."
        ),
        assessment_guidance=(
            "Evaluate hard invariants separately from policy-aligned stylistic fit. "
            "Hard invariants include scene coverage, POV stability, chapter-break integrity, "
            "and redundancy control. Style fit must follow the compiled rewrite policy rather than generic literary ideals. "
            f"{transfer_instruction} {priority_instruction}"
        ),
        improvement_guidance=(
            "Only repair issues identified by the policy-aware assessment. "
            "Do not add ornamental prose, melodrama, or surface escalation unless required by the policy. "
            f"{improvement_mode_guidance}"
        ),
        improvement_mode=improvement_mode,
        improvement_mode_guidance=improvement_mode_guidance,
        author_style_guidance=_author_style_guidance(author_style),
        author_style_weight=author_style_weight,
        negative_constraints_block=negative_constraints_block,
    )

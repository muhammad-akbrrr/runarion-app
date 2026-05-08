from pydantic import BaseModel, Field


class VoiceTechnique(BaseModel):
    diction: str = ""
    syntax: str = ""
    rhythm: str = ""
    register: str = ""
    figurative_language: str = ""


class DialogueTechnique(BaseModel):
    conversation_style: str = ""
    speaker_differentiation: str = ""
    dialogue_narration_balance: str = ""


class DescriptionTechnique(BaseModel):
    description_density: str = ""
    sensory_focus: str = ""
    atmosphere_strategy: str = ""


class ExpositionTechnique(BaseModel):
    exposition_strategy: str = ""
    context_integration: str = ""
    terminology_handling: str = ""


class PacingTechnique(BaseModel):
    scene_tempo: str = ""
    transition_style: str = ""
    tension_pattern: str = ""


class NarrativeTechnique(BaseModel):
    pov_tendency: str = ""
    narrative_distance: str = ""
    redundancy_avoidance: str = ""


class AuthorStyleTechniques(BaseModel):
    voice: VoiceTechnique = Field(default_factory=VoiceTechnique)
    dialogue: DialogueTechnique = Field(default_factory=DialogueTechnique)
    description: DescriptionTechnique = Field(default_factory=DescriptionTechnique)
    exposition: ExpositionTechnique = Field(default_factory=ExpositionTechnique)
    pacing: PacingTechnique = Field(default_factory=PacingTechnique)
    narrative: NarrativeTechnique = Field(default_factory=NarrativeTechnique)


class AuthorStyleExamples(BaseModel):
    voice: list[str] = Field(default_factory=list)
    dialogue: list[str] = Field(default_factory=list)
    description: list[str] = Field(default_factory=list)
    exposition: list[str] = Field(default_factory=list)
    pacing: list[str] = Field(default_factory=list)


class AuthorStyleAdaptation(BaseModel):
    portable_traits: list[str] = Field(default_factory=list)
    non_portable_markers: list[str] = Field(default_factory=list)
    transfer_risks: list[str] = Field(default_factory=list)
    suppression_guidance: list[str] = Field(default_factory=list)


class AuthorStyle(BaseModel):
    schema_version: int = 2
    techniques: AuthorStyleTechniques = Field(default_factory=AuthorStyleTechniques)
    examples: AuthorStyleExamples = Field(default_factory=AuthorStyleExamples)
    adaptation: AuthorStyleAdaptation = Field(default_factory=AuthorStyleAdaptation)

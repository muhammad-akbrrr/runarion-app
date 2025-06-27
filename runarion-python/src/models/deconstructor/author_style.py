from typing import Optional

from pydantic import BaseModel


class DialogueTechnique(BaseModel):
    conversation_style: str = ""
    dialogue_balance: str = ""
    character_voices: Optional[str] = None


class ActionTechnique(BaseModel):
    action_sequences: str = ""
    tension: str = ""
    fight_scenes: Optional[str] = None


class WorldbuildingTechnique(BaseModel):
    world_reveals: str = ""
    exposition: Optional[str] = None
    history_magic: Optional[str] = None


class DescriptionTechnique(BaseModel):
    character_descriptions: str = ""
    scene_painting: str = ""
    atmosphere: Optional[str] = None


class LiteraryTechnique(BaseModel):
    devices: Optional[str] = None
    metaphors: Optional[str] = None
    word_patterns: Optional[str] = None
    scene_structure: Optional[str] = None
    transitions: Optional[str] = None
    pacing: Optional[str] = None


class AuthorStyleTechniques(BaseModel):
    dialogue: DialogueTechnique = DialogueTechnique()
    action: ActionTechnique = ActionTechnique()
    worldbuilding: WorldbuildingTechnique = WorldbuildingTechnique()
    descriptions: DescriptionTechnique = DescriptionTechnique()
    literary: LiteraryTechnique = LiteraryTechnique()


class AuthorStyleExamples(BaseModel):
    dialogue: list[str] = []
    action: list[str] = []
    worldbuilding: list[str] = []
    descriptions: list[str] = []
    literary: list[str] = []


class AuthorStyle(BaseModel):
    techniques: AuthorStyleTechniques = AuthorStyleTechniques()
    examples: AuthorStyleExamples = AuthorStyleExamples()

from pydantic import BaseModel


class DialogueTechnique(BaseModel):
    conversation_style: str = ""
    character_voices: str = ""
    dialogue_balance: str = ""


class ActionTechnique(BaseModel):
    fight_scenes: str = ""
    action_sequences: str = ""
    tension: str = ""


class WorldbuildingTechnique(BaseModel):
    world_reveals: str = ""
    exposition: str = ""
    history_magic: str = ""


class DescriptionTechnique(BaseModel):
    character_descriptions: str = ""
    scene_painting: str = ""
    atmosphere: str = ""


class LiteraryTechnique(BaseModel):
    devices: str = ""
    metaphors: str = ""
    word_patterns: str = ""
    scene_structure: str = ""
    transitions: str = ""
    pacing: str = ""


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

from pydantic import BaseModel, Field
from typing import Literal, Optional, Union
from models.deconstructor.author_style import AuthorStyle


class WritingPerspective(BaseModel):
    """Configuration for writing perspective/point of view"""
    type: Literal["first_person", "second_person", "third_person_omniscient",
                  "third_person_limited"] = "third_person_limited"
    narrator_voice: Optional[str] = ""  # Additional narrator characteristics
    # For limited POV, which character to focus on
    character_focus: Optional[str] = ""


class ContentRewriteConfig(BaseModel):
    """Configuration for content rewriting"""
    author_style: AuthorStyle
    writing_perspective: WritingPerspective
    target_genre: Optional[str] = ""
    target_tone: Optional[str] = ""
    # Elements to preserve from original
    preserve_key_elements: Optional[list[str]] = []
    target_length: Optional[str] = "similar"  # "shorter", "similar", "longer"
    # How strongly to apply the style
    style_intensity: float = Field(0.7, ge=0.0, le=1.0)


class RewrittenContent(BaseModel):
    """Result of content rewriting"""
    original_text: str
    rewritten_text: str
    applied_style: AuthorStyle
    applied_perspective: WritingPerspective
    processing_time_ms: int
    token_count: int
    # How confident the model is about style application
    style_confidence: float = Field(0.0, ge=0.0, le=1.0)


class NewAuthorStyleRequest(BaseModel):
    """Request to create a new author style from sample files"""
    sample_files: list[str]
    author_name: Optional[str] = ""


class ExistingAuthorStyleRequest(BaseModel):
    """Request to use an existing author style"""
    author_style_id: str


class StoryRewriteRequest(BaseModel):
    """Complete story rewrite request"""
    rough_draft_file: str
    author_style_request: Union[NewAuthorStyleRequest,
                                ExistingAuthorStyleRequest]
    writing_perspective: WritingPerspective
    rewrite_config: Optional[ContentRewriteConfig] = None
    store_intermediate: bool = False
    chunk_overlap: bool = False


class StoryRewriteResponse(BaseModel):
    """Response from story rewrite pipeline"""
    original_story: str
    rewritten_story: str
    author_style: AuthorStyle
    total_chunks: int
    total_original_chars: int
    total_rewritten_chars: int
    total_tokens: int
    processing_time_ms: int
    average_style_confidence: float
    session_id: str
    author_style_id: str

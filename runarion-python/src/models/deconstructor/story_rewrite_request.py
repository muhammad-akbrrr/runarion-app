from pydantic import BaseModel, Field
from typing import Literal, Optional, Union
from models.deconstructor.author_style import AuthorStyle
from models.deconstructor.content_rewrite import WritingPerspective, ContentRewriteConfig


class NewAuthorStyleRequest(BaseModel):
    """Request for creating a new author style from uploaded samples"""
    sample_files: list[str]  # List of PDF file paths for author style samples
    author_name: Optional[str] = ""  # Optional author name for reference


class ExistingAuthorStyleRequest(BaseModel):
    """Request for using an existing author style"""
    author_style_id: str  # ID of existing author style from database


class StoryRewriteRequest(BaseModel):
    """
    Complete story rewrite request following the user workflow:
    1. User uploads rough draft PDF
    2. User selects or creates author style
    3. User selects writing perspective
    4. System rewrites the story
    """

    # Step 1: User's rough draft
    rough_draft_file: str  # Path to user's rough draft PDF

    # Step 2: Author style selection (either new or existing)
    author_style_request: Union[NewAuthorStyleRequest,
                                ExistingAuthorStyleRequest]

    # Step 3: Writing perspective
    writing_perspective: WritingPerspective

    # Optional: Additional rewriting configuration
    rewrite_config: Optional[ContentRewriteConfig] = None

    # Processing options
    store_intermediate: bool = False
    chunk_overlap: bool = False


class StoryRewriteResponse(BaseModel):
    """Response from the story rewrite pipeline"""

    # Results
    original_story: str  # Original rough draft text
    rewritten_story: str  # Final rewritten story
    author_style: AuthorStyle  # Applied author style (new or existing)

    # Metadata
    total_chunks: int
    total_original_chars: int
    total_rewritten_chars: int
    total_tokens: int
    processing_time_ms: int
    average_style_confidence: float = Field(0.0, ge=0.0, le=1.0)

    # Session information
    session_id: str
    author_style_id: str  # ID of the author style used/created

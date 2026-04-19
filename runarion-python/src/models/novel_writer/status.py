"""
Status constants for the novel writer pipeline.
References the novel writer statuses added to DraftStatus.
"""

from models.deconstructor.status import DraftStatus


class NovelWriterStatus:
    """
    Convenience class for accessing novel writer status values.
    All values are members of DraftStatus to ensure validation compatibility.
    """
    NOVEL_WRITING = DraftStatus.NOVEL_WRITING.value
    STAGE_1_COMPLETE = DraftStatus.NW_STAGE_1_COMPLETE.value
    STAGE_2_COMPLETE = DraftStatus.NW_STAGE_2_COMPLETE.value
    STAGE_3_COMPLETE = DraftStatus.NW_STAGE_3_COMPLETE.value
    STAGE_4_COMPLETE = DraftStatus.NW_STAGE_4_COMPLETE.value
    COMPLETED = DraftStatus.NW_COMPLETED.value
    FAILED = DraftStatus.NW_FAILED.value

    @classmethod
    def get_processing_statuses(cls) -> list:
        """Get novel writer processing statuses."""
        return [
            cls.NOVEL_WRITING,
            cls.STAGE_1_COMPLETE,
            cls.STAGE_2_COMPLETE,
            cls.STAGE_3_COMPLETE,
            cls.STAGE_4_COMPLETE,
        ]

    @classmethod
    def is_novel_writing(cls, status: str) -> bool:
        """Check if status indicates novel writing is in progress."""
        return status in cls.get_processing_statuses()

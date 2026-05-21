"""
Status enumeration for draft processing pipeline.
Defines valid status values for the novel deconstruction and novel writer pipelines.
"""

from enum import Enum


class DraftStatus(Enum):
    """
    Valid status values for draft processing.
    Covers both the deconstructor pipeline and the novel writer pipeline.
    """
    # Deconstructor statuses
    PENDING = "pending"
    PROCESSING = "processing"
    STAGE_1_COMPLETE = "stage_1_complete"
    STAGE_2_COMPLETE = "stage_2_complete"
    STAGE_3_COMPLETE = "stage_3_complete"
    STAGE_4_COMPLETE = "stage_4_complete"
    STAGE_5_COMPLETE = "stage_5_complete"
    STAGE_6_COMPLETE = "stage_6_complete"
    COMPLETED = "completed"
    FAILED = "failed"

    # Novel writer statuses
    NOVEL_WRITING = "novel_writing"
    NW_STAGE_1_COMPLETE = "nw_stage_1_complete"
    NW_STAGE_2_COMPLETE = "nw_stage_2_complete"
    NW_STAGE_3_COMPLETE = "nw_stage_3_complete"
    NW_STAGE_4_COMPLETE = "nw_stage_4_complete"
    NW_COMPLETED = "nw_completed"
    NW_FAILED = "nw_failed"

    # Pipeline orchestrator statuses (full 3-phase run)
    PIPELINE_PENDING = "pipeline_pending"
    PIPELINE_PHASE_1_2_RUNNING = "pipeline_phase_1_2_running"
    PIPELINE_PHASE_3_RUNNING = "pipeline_phase_3_running"
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_FAILED = "pipeline_failed"

    @classmethod
    def is_valid(cls, status: str) -> bool:
        """
        Check if a status string is valid.
        
        Args:
            status: Status string to validate
            
        Returns:
            True if status is valid, False otherwise
        """
        return status in [member.value for member in cls]

    @classmethod
    def get_valid_statuses(cls) -> list:
        """
        Get list of all valid status values.
        
        Returns:
            List of valid status strings
        """
        return [member.value for member in cls]

    @classmethod
    def get_processing_statuses(cls) -> list:
        """
        Get list of statuses that indicate processing is in progress.

        Returns:
            List of processing status strings
        """
        return [
            cls.PROCESSING.value,
            cls.STAGE_1_COMPLETE.value,
            cls.STAGE_2_COMPLETE.value,
            cls.STAGE_3_COMPLETE.value,
            cls.STAGE_4_COMPLETE.value,
            cls.STAGE_5_COMPLETE.value,
            cls.STAGE_6_COMPLETE.value,
            # Novel writer processing statuses
            cls.NOVEL_WRITING.value,
            cls.NW_STAGE_1_COMPLETE.value,
            cls.NW_STAGE_2_COMPLETE.value,
            cls.NW_STAGE_3_COMPLETE.value,
            cls.NW_STAGE_4_COMPLETE.value,
            # Pipeline orchestrator processing statuses
            cls.PIPELINE_PENDING.value,
            cls.PIPELINE_PHASE_1_2_RUNNING.value,
            cls.PIPELINE_PHASE_3_RUNNING.value,
        ]

    @classmethod
    def get_final_statuses(cls) -> list:
        """
        Get list of statuses that indicate processing is complete.

        Returns:
            List of final status strings
        """
        return [
            cls.COMPLETED.value,
            cls.FAILED.value,
            cls.NW_COMPLETED.value,
            cls.NW_FAILED.value,
            cls.PIPELINE_COMPLETED.value,
            cls.PIPELINE_FAILED.value,
        ]

    @classmethod
    def is_processing(cls, status: str) -> bool:
        """
        Check if a status indicates processing is in progress.
        
        Args:
            status: Status string to check
            
        Returns:
            True if status indicates processing, False otherwise
        """
        return status in cls.get_processing_statuses()

    @classmethod
    def is_final(cls, status: str) -> bool:
        """
        Check if a status indicates processing is complete.
        
        Args:
            status: Status string to check
            
        Returns:
            True if status is final, False otherwise
        """
        return status in cls.get_final_statuses()
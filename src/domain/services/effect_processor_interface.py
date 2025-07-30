"""
Effect Processor Interface

Defines the contract for video effect processing operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path

from ..entities.video import Video
from ..entities.effect import Effect
from ..value_objects.effect_type import EffectType


class EffectResult:
    """Result of an effect processing operation"""

    def __init__(self, success: bool, output_path: Optional[Path] = None,
                 error_message: Optional[str] = None, processing_time: float = 0.0):
        self.success = success
        self.output_path = output_path
        self.error_message = error_message
        self.processing_time = processing_time

    def is_success(self) -> bool:
        """Check if effect processing was successful"""
        return self.success

    def get_error(self) -> Optional[str]:
        """Get error message if processing failed"""
        return self.error_message


class IEffectProcessor(ABC):
    """Interface for video effect processing"""

    @abstractmethod
    def can_handle(self, effect_type: EffectType) -> bool:
        """
        Check if this processor can handle the given effect type.

        Args:
            effect_type: The type of effect to check

        Returns:
            True if this processor can handle the effect, False otherwise
        """
    @abstractmethod
    def apply_effect(self, input_video: Video, effect: Effect, output_path: Path) -> EffectResult:
        """
        Apply an effect to a video.

        Args:
            input_video: The input video to process
            effect: The effect configuration to apply
            output_path: Where to save the processed video

        Returns:
            EffectResult with processing outcome
        """
    @abstractmethod
    def get_supported_effects(self) -> List[EffectType]:
        """
        Get list of effect types supported by this processor.

        Returns:
            List of supported EffectType values
        """
    @abstractmethod
    def validate_effect_parameters(self, effect: Effect) -> List[str]:
        """
        Validate effect parameters for this processor.

        Args:
            effect: The effect to validate

        Returns:
            List of validation error messages (empty if valid)
        """
    @abstractmethod
    def estimate_processing_time(self, video: Video, effect: Effect) -> float:
        """
        Estimate processing time for applying an effect.

        Args:
            video: The video to process
            effect: The effect to apply

        Returns:
            Estimated processing time in seconds
        """
    @abstractmethod
    def get_processor_name(self) -> str:
        """
        Get the name of this effect processor.

        Returns:
            Human-readable processor name
        """
        pass

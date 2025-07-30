"""
Effect Entity

Represents a video effect with its configuration and parameters.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List

from ..value_objects.effect_type import EffectType


@dataclass
class Effect:
    """Effect entity representing a video effect configuration"""
    type: EffectType
    duration: float
    parameters: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate effect properties after initialization"""
        self._validate()

    def _validate(self):
        """Validate effect properties"""
        if self.type.requires_duration() and self.duration <= 0:
            raise ValueError(f"Duration must be positive for effect {self.type.value}, got {self.duration}")

        if self.type == EffectType.NONE and self.duration != 0:
            raise ValueError("Duration must be 0 for NONE effect type")

        # Validate effect-specific parameters
        self._validate_parameters()

    def _validate_parameters(self):
        """Validate effect-specific parameters"""
        if self.type.is_circle_effect():
            self._validate_circle_parameters()
        elif self.type.is_slide_effect():
            self._validate_slide_parameters()

    def _validate_circle_parameters(self):
        """Validate parameters for circle effects"""
        # Circle effects might have radius, center point parameters
        if 'radius' in self.parameters:
            radius = self.parameters['radius']
            if not isinstance(radius, (int, float)) or radius <= 0:
                raise ValueError(f"Circle radius must be positive number, got {radius}")

    def _validate_slide_parameters(self):
        """Validate parameters for slide effects"""
        # Slide effects might have easing, acceleration parameters
        if 'easing' in self.parameters:
            easing = self.parameters['easing']
            valid_easing = ['linear', 'ease-in', 'ease-out', 'ease-in-out']
            if easing not in valid_easing:
                raise ValueError(f"Invalid easing type: {easing}. Must be one of {valid_easing}")

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """Get parameter value with default"""
        return self.parameters.get(key, default)

    def set_parameter(self, key: str, value: Any) -> None:
        """Set parameter value"""
        self.parameters[key] = value
        # Re-validate after parameter change
        self._validate_parameters()

    def is_none_effect(self) -> bool:
        """Check if this is a no-effect (passthrough)"""
        return self.type == EffectType.NONE

    def requires_preprocessing(self) -> bool:
        """Check if effect requires preprocessing steps"""
        return self.type.is_circle_effect()

    def get_estimated_processing_time(self, video_duration: float) -> float:
        """Estimate processing time based on effect complexity and video duration"""
        base_time = video_duration * 0.1  # Base 10% overhead

        if self.type == EffectType.NONE:
            return base_time * 0.1  # Minimal processing for copy
        elif self.type.is_slide_effect():
            return base_time * 1.5  # Moderate complexity
        elif self.type.is_circle_effect():
            return base_time * 3.0  # High complexity
        elif self.type == EffectType.FADE_IN:
            return base_time * 1.2  # Low-moderate complexity

        return base_time

    @classmethod
    def create_none_effect(cls) -> 'Effect':
        """Create a no-effect (passthrough) effect"""
        return cls(type=EffectType.NONE, duration=0.0)

    @classmethod
    def create_fade_effect(cls, duration: float) -> 'Effect':
        """Create a fade-in effect with specified duration"""
        return cls(type=EffectType.FADE_IN, duration=duration)

    def __str__(self) -> str:
        """String representation"""
        if self.is_none_effect():
            return "Effect(NONE)"
        return f"Effect({self.type.value}, {self.duration:.1f}s)"

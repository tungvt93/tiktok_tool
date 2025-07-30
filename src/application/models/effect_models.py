"""
Effect Models

Data transfer objects for effect-related operations.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from ...domain.value_objects.effect_type import EffectType


@dataclass
class EffectInfo:
    """Information about an effect type"""
    type: str
    name: str
    processor: str
    supported: bool
    requires_duration: bool
    is_slide_effect: bool
    is_circle_effect: bool
    description: str

    @property
    def category(self) -> str:
        """Get effect category"""
        if self.is_slide_effect:
            return "Slide"
        elif self.is_circle_effect:
            return "Circle"
        elif self.type == "fade_in":
            return "Fade"
        else:
            return "Other"


@dataclass
class EffectPreset:
    """Predefined effect configuration"""
    name: str
    display_name: str
    description: str
    effects: List[Dict[str, Any]]

    @property
    def effect_count(self) -> int:
        """Get number of effects in preset"""
        return len(self.effects)


@dataclass
class EffectValidationResult:
    """Result of effect validation"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if there are validation errors"""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are validation warnings"""
        return len(self.warnings) > 0


@dataclass
class ProcessorInfo:
    """Information about an effect processor"""
    name: str
    supported_effects: List[str]
    effect_count: int

    @property
    def supported_categories(self) -> List[str]:
        """Get categories of supported effects"""
        categories = set()
        for effect_type_str in self.supported_effects:
            try:
                effect_type = EffectType(effect_type_str)
                if effect_type.is_slide_effect():
                    categories.add("Slide")
                elif effect_type.is_circle_effect():
                    categories.add("Circle")
                elif effect_type == EffectType.FADE_IN:
                    categories.add("Fade")
                else:
                    categories.add("Other")
            except ValueError:
                continue
        return sorted(list(categories))


@dataclass
class EffectEstimate:
    """Processing time estimate for effects"""
    total_time: float
    effect_times: Dict[str, float] = field(default_factory=dict)

    @property
    def total_time_string(self) -> str:
        """Get total time as formatted string"""
        if self.total_time < 60:
            return f"{self.total_time:.1f}s"
        else:
            minutes = int(self.total_time // 60)
            seconds = int(self.total_time % 60)
            return f"{minutes}m {seconds}s"


@dataclass
class EffectConfiguration:
    """Configuration for creating effects"""
    type: str
    duration: float
    parameters: Dict[str, Any] = field(default_factory=dict)

    def validate_basic(self) -> List[str]:
        """Basic validation of configuration"""
        errors = []

        if not self.type:
            errors.append("Effect type is required")

        try:
            EffectType(self.type)
        except ValueError:
            errors.append(f"Invalid effect type: {self.type}")

        if self.duration <= 0:
            errors.append("Duration must be positive")
        elif self.duration > 30:
            errors.append("Duration too long (max 30 seconds)")

        return errors


@dataclass
class RandomEffectRequest:
    """Request for creating random effects"""
    count: int = 1
    min_duration: float = 0.5
    max_duration: float = 5.0
    exclude_types: List[str] = field(default_factory=list)
    categories: Optional[List[str]] = None  # Filter by categories

    def __post_init__(self):
        if self.count < 1:
            self.count = 1
        if self.count > 10:
            self.count = 10  # Reasonable limit

        if self.min_duration <= 0:
            self.min_duration = 0.5
        if self.max_duration <= self.min_duration:
            self.max_duration = self.min_duration + 1.0


@dataclass
class EffectLibrary:
    """Collection of available effects and presets"""
    available_effects: List[EffectInfo]
    presets: List[EffectPreset]
    processors: List[ProcessorInfo]

    @property
    def effect_count(self) -> int:
        """Get total number of available effects"""
        return len(self.available_effects)

    @property
    def preset_count(self) -> int:
        """Get number of available presets"""
        return len(self.presets)

    @property
    def processor_count(self) -> int:
        """Get number of available processors"""
        return len(self.processors)

    def get_effects_by_category(self, category: str) -> List[EffectInfo]:
        """Get effects filtered by category"""
        return [effect for effect in self.available_effects if effect.category == category]

    def get_effect_by_type(self, effect_type: str) -> Optional[EffectInfo]:
        """Get effect info by type"""
        for effect in self.available_effects:
            if effect.type == effect_type:
                return effect
        return None

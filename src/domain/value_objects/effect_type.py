"""
Effect Type Value Object

Defines the types of video effects that can be applied.
"""

from enum import Enum


class EffectType(Enum):
    """Types of opening effects available for video processing"""
    NONE = "none"
    SLIDE_RIGHT_TO_LEFT = "slide_right_to_left"
    SLIDE_LEFT_TO_RIGHT = "slide_left_to_right"
    SLIDE_TOP_TO_BOTTOM = "slide_top_to_bottom"
    SLIDE_BOTTOM_TO_TOP = "slide_bottom_to_top"
    CIRCLE_EXPAND = "circle_expand"
    CIRCLE_CONTRACT = "circle_contract"
    CIRCLE_ROTATE_CW = "circle_rotate_cw"
    CIRCLE_ROTATE_CCW = "circle_rotate_ccw"
    FADE_IN = "fade_in"

    @classmethod
    def get_slide_effects(cls) -> list['EffectType']:
        """Get all slide-based effects"""
        return [
            cls.SLIDE_RIGHT_TO_LEFT,
            cls.SLIDE_LEFT_TO_RIGHT,
            cls.SLIDE_TOP_TO_BOTTOM,
            cls.SLIDE_BOTTOM_TO_TOP
        ]

    @classmethod
    def get_circle_effects(cls) -> list['EffectType']:
        """Get all circle-based effects"""
        return [
            cls.CIRCLE_EXPAND,
            cls.CIRCLE_CONTRACT,
            cls.CIRCLE_ROTATE_CW,
            cls.CIRCLE_ROTATE_CCW
        ]

    def is_slide_effect(self) -> bool:
        """Check if this is a slide effect"""
        return self in self.get_slide_effects()

    def is_circle_effect(self) -> bool:
        """Check if this is a circle effect"""
        return self in self.get_circle_effects()

    def requires_duration(self) -> bool:
        """Check if this effect requires a duration parameter"""
        return self != self.NONE

"""
Infrastructure Processors

Concrete implementations of effect processors and video manipulation services.
"""

from .slide_effect_processor import SlideEffectProcessor
from .circle_effect_processor import CircleEffectProcessor
from .fade_effect_processor import FadeEffectProcessor
from .gif_processor import GIFProcessor
from .gif_overlay_processor import GIFOverlayProcessor

__all__ = [
    'SlideEffectProcessor',
    'CircleEffectProcessor',
    'FadeEffectProcessor',
    'GIFProcessor',
    'GIFOverlayProcessor'
]

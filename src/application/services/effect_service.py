"""
Effect Service

Application service for managing video effects and processors.
"""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from ...domain.entities.effect import Effect
from ...domain.entities.video import Video
from ...domain.value_objects.effect_type import EffectType
from ...domain.services.effect_processor_interface import IEffectProcessor
from ...shared.config import AppConfig
from ...shared.utils import get_logger
from ...shared.exceptions import EffectProcessingException

logger = get_logger(__name__)


class EffectService:
    """Application service for effect management"""

    def __init__(self, effect_processors: List[IEffectProcessor], config: AppConfig):
        """
        Initialize effect service.

        Args:
            effect_processors: List of available effect processors
            config: Application configuration
        """
        self.effect_processors = effect_processors
        self.config = config

        # Build processor mapping
        self._processor_map: Dict[EffectType, IEffectProcessor] = {}
        self._build_processor_map()

    def get_available_effects(self) -> List[EffectType]:
        """
        Get list of all available effect types.

        Returns:
            List of available EffectType values
        """
        available_effects = set()

        for processor in self.effect_processors:
            available_effects.update(processor.get_supported_effects())

        return sorted(list(available_effects), key=lambda x: x.value)

    def get_effect_info(self, effect_type: EffectType) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific effect type.

        Args:
            effect_type: Effect type to get info for

        Returns:
            Dictionary with effect information or None if not supported
        """
        processor = self._processor_map.get(effect_type)
        if not processor:
            return None

        return {
            'type': effect_type.value,
            'name': effect_type.value.replace('_', ' ').title(),
            'processor': processor.get_processor_name(),
            'supported': True,
            'requires_duration': effect_type.requires_duration(),
            'is_slide_effect': effect_type.is_slide_effect(),
            'is_circle_effect': effect_type.is_circle_effect(),
            'description': self._get_effect_description(effect_type)
        }

    def create_effect(self, effect_type: EffectType, duration: float,
                     parameters: Optional[Dict[str, Any]] = None) -> Effect:
        """
        Create an effect with validation.

        Args:
            effect_type: Type of effect to create
            duration: Effect duration in seconds
            parameters: Optional effect parameters

        Returns:
            Created Effect entity

        Raises:
            EffectProcessingException: If effect creation fails
        """
        try:
            # Check if effect type is supported
            if effect_type not in self._processor_map:
                raise EffectProcessingException(
                    effect_type.value,
                    f"Effect type not supported: {effect_type.value}"
                )

            # Create effect
            effect = Effect(
                type=effect_type,
                duration=duration,
                parameters=parameters or {}
            )

            # Validate with processor
            processor = self._processor_map[effect_type]
            validation_errors = processor.validate_effect_parameters(effect)

            if validation_errors:
                raise EffectProcessingException(
                    effect_type.value,
                    f"Effect validation failed: {'; '.join(validation_errors)}"
                )

            logger.debug(f"Created effect: {effect_type.value} ({duration}s)")
            return effect

        except Exception as e:
            logger.error(f"Error creating effect {effect_type.value}: {e}")
            raise

    def validate_effect(self, effect: Effect) -> List[str]:
        """
        Validate an effect.

        Args:
            effect: Effect to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        try:
            processor = self._processor_map.get(effect.type)
            if not processor:
                return [f"Effect type not supported: {effect.type.value}"]

            return processor.validate_effect_parameters(effect)

        except Exception as e:
            logger.error(f"Error validating effect {effect.type.value}: {e}")
            return [str(e)]

    def estimate_processing_time(self, video: Video, effects: List[Effect]) -> float:
        """
        Estimate total processing time for applying effects to a video.

        Args:
            video: Video to process
            effects: List of effects to apply

        Returns:
            Estimated processing time in seconds
        """
        try:
            total_time = 0.0

            for effect in effects:
                processor = self._processor_map.get(effect.type)
                if processor:
                    effect_time = processor.estimate_processing_time(video, effect)
                    total_time += effect_time
                else:
                    logger.warning(f"No processor found for effect: {effect.type.value}")

            return total_time

        except Exception as e:
            logger.error(f"Error estimating processing time: {e}")
            return 0.0

    def get_processor_for_effect(self, effect_type: EffectType) -> Optional[IEffectProcessor]:
        """
        Get processor that can handle a specific effect type.

        Args:
            effect_type: Effect type

        Returns:
            Effect processor or None if not supported
        """
        return self._processor_map.get(effect_type)

    def get_processor_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all available processors.

        Returns:
            List of processor information dictionaries
        """
        processor_info = []

        for processor in self.effect_processors:
            supported_effects = processor.get_supported_effects()

            info = {
                'name': processor.get_processor_name(),
                'supported_effects': [effect.value for effect in supported_effects],
                'effect_count': len(supported_effects)
            }

            processor_info.append(info)

        return processor_info

    def create_random_effect(self, duration: Optional[float] = None) -> Effect:
        """
        Create a random effect.

        Args:
            duration: Effect duration (uses config default if None)

        Returns:
            Random Effect entity
        """
        import random

        available_effects = self.get_available_effects()
        if not available_effects:
            # Fallback to no effect
            return Effect.create_none_effect()

        # Remove NONE effect from random selection
        selectable_effects = [e for e in available_effects if e != EffectType.NONE]
        if not selectable_effects:
            return Effect.create_none_effect()

        # Select random effect
        effect_type = random.choice(selectable_effects)

        # Use provided duration or config default
        if duration is None:
            duration = self.config.video.default_effect_duration

        # Add some randomness to duration (±20%)
        duration_variance = duration * 0.2
        random_duration = duration + random.uniform(-duration_variance, duration_variance)
        random_duration = max(0.5, min(5.0, random_duration))  # Clamp between 0.5-5.0s

        return self.create_effect(effect_type, random_duration)

    def get_effect_presets(self) -> Dict[str, List[Effect]]:
        """
        Get predefined effect presets.

        Returns:
            Dictionary of preset name to list of effects
        """
        try:
            presets = {}

            # Quick preset - fast effects
            presets['quick'] = [
                self.create_effect(EffectType.FADE_IN, 1.0),
            ]

            # Smooth preset - slide effects
            if EffectType.SLIDE_RIGHT_TO_LEFT in self._processor_map:
                presets['smooth'] = [
                    self.create_effect(EffectType.SLIDE_RIGHT_TO_LEFT, 1.5),
                ]

            # Dynamic preset - circle effects
            if EffectType.CIRCLE_EXPAND in self._processor_map:
                presets['dynamic'] = [
                    self.create_effect(EffectType.CIRCLE_EXPAND, 2.0),
                ]

            # Mixed preset - combination of effects
            mixed_effects = []
            if EffectType.FADE_IN in self._processor_map:
                mixed_effects.append(self.create_effect(EffectType.FADE_IN, 1.0))
            if EffectType.SLIDE_LEFT_TO_RIGHT in self._processor_map:
                mixed_effects.append(self.create_effect(EffectType.SLIDE_LEFT_TO_RIGHT, 1.5))

            if mixed_effects:
                presets['mixed'] = mixed_effects

            return presets

        except Exception as e:
            logger.error(f"Error creating effect presets: {e}")
            return {}

    def _build_processor_map(self) -> None:
        """Build mapping from effect types to processors"""
        self._processor_map.clear()

        for processor in self.effect_processors:
            supported_effects = processor.get_supported_effects()

            for effect_type in supported_effects:
                if effect_type in self._processor_map:
                    logger.warning(f"Multiple processors support effect {effect_type.value}")

                self._processor_map[effect_type] = processor

        logger.info(f"Built processor map with {len(self._processor_map)} effect types")

    def _get_effect_description(self, effect_type: EffectType) -> str:
        """Get human-readable description for effect type"""
        descriptions = {
            EffectType.NONE: "No effect applied",
            EffectType.FADE_IN: "Gradually fade in from black background",
            EffectType.SLIDE_RIGHT_TO_LEFT: "Slide video from right to left",
            EffectType.SLIDE_LEFT_TO_RIGHT: "Slide video from left to right",
            EffectType.SLIDE_TOP_TO_BOTTOM: "Slide video from top to bottom",
            EffectType.SLIDE_BOTTOM_TO_TOP: "Slide video from bottom to top",
            EffectType.CIRCLE_EXPAND: "Reveal video with expanding circle",
            EffectType.CIRCLE_CONTRACT: "Hide video with contracting circle",
            EffectType.CIRCLE_ROTATE_CW: "Reveal video with clockwise rotating circle",
            EffectType.CIRCLE_ROTATE_CCW: "Reveal video with counter-clockwise rotating circle"
        }

        return descriptions.get(effect_type, f"Effect: {effect_type.value}")

"""
Unit Tests for Effect Entity

Tests for the Effect domain entity.
"""

import pytest

from src.domain.entities.effect import Effect
from src.domain.value_objects.effect_type import EffectType


class TestEffectEntity:
    """Test cases for Effect entity"""

    def test_effect_creation_with_valid_data(self):
        """Test creating effect with valid data"""
        effect = Effect(
            type=EffectType.FADE_IN,
            duration=2.0,
            parameters={'color': 'black', 'alpha': 1.0}
        )

        assert effect.type == EffectType.FADE_IN
        assert effect.duration == 2.0
        assert effect.parameters['color'] == 'black'
        assert effect.parameters['alpha'] == 1.0

    def test_effect_creation_with_invalid_duration(self):
        """Test creating effect with invalid duration raises error"""
        with pytest.raises(ValueError, match="Duration must be positive"):
            Effect(
                type=EffectType.FADE_IN,
                duration=-1.0
            )

    def test_effect_creation_none_type_with_duration(self):
        """Test creating NONE effect with non-zero duration raises error"""
        with pytest.raises(ValueError, match="Duration must be 0 for NONE effect"):
            Effect(
                type=EffectType.NONE,
                duration=2.0
            )

    def test_effect_parameter_operations(self, sample_effect):
        """Test effect parameter operations"""
        # Test getting parameters
        assert sample_effect.get_parameter('color') == 'black'
        assert sample_effect.get_parameter('nonexistent', 'default') == 'default'

        # Test setting parameters
        sample_effect.set_parameter('new_param', 'new_value')
        assert sample_effect.get_parameter('new_param') == 'new_value'

    def test_effect_validation_circle_parameters(self):
        """Test effect validation for circle parameters"""
        # Valid circle effect
        effect = Effect(
            type=EffectType.CIRCLE_EXPAND,
            duration=2.0,
            parameters={'radius': 100}
        )
        assert effect.get_parameter('radius') == 100

        # Invalid radius
        with pytest.raises(ValueError, match="Circle radius must be positive"):
            Effect(
                type=EffectType.CIRCLE_EXPAND,
                duration=2.0,
                parameters={'radius': -50}
            )

    def test_effect_validation_slide_parameters(self):
        """Test effect validation for slide parameters"""
        # Valid slide effect
        effect = Effect(
            type=EffectType.SLIDE_LEFT_TO_RIGHT,
            duration=1.5,
            parameters={'easing': 'ease-in'}
        )
        assert effect.get_parameter('easing') == 'ease-in'

        # Invalid easing
        with pytest.raises(ValueError, match="Invalid easing type"):
            Effect(
                type=EffectType.SLIDE_LEFT_TO_RIGHT,
                duration=1.5,
                parameters={'easing': 'invalid-easing'}
            )

    def test_effect_type_checks(self):
        """Test effect type checking methods"""
        fade_effect = Effect(type=EffectType.FADE_IN, duration=2.0)
        assert not fade_effect.is_none_effect()

        none_effect = Effect.create_none_effect()
        assert none_effect.is_none_effect()
        assert none_effect.duration == 0.0

    def test_effect_processing_requirements(self):
        """Test effect processing requirements"""
        circle_effect = Effect(type=EffectType.CIRCLE_EXPAND, duration=2.0)
        assert circle_effect.requires_preprocessing()

        fade_effect = Effect(type=EffectType.FADE_IN, duration=2.0)
        assert not fade_effect.requires_preprocessing()

    def test_effect_processing_time_estimation(self, sample_video):
        """Test effect processing time estimation"""
        fade_effect = Effect(type=EffectType.FADE_IN, duration=2.0)
        estimated_time = fade_effect.get_estimated_processing_time(sample_video.duration)

        assert estimated_time > 0
        assert isinstance(estimated_time, float)

    def test_effect_factory_methods(self):
        """Test effect factory methods"""
        # Test create_none_effect
        none_effect = Effect.create_none_effect()
        assert none_effect.type == EffectType.NONE
        assert none_effect.duration == 0.0

        # Test create_fade_effect
        fade_effect = Effect.create_fade_effect(3.0)
        assert fade_effect.type == EffectType.FADE_IN
        assert fade_effect.duration == 3.0

    def test_effect_string_representation(self, sample_effect):
        """Test effect string representation"""
        str_repr = str(sample_effect)
        assert "fade_in" in str_repr
        assert "2.0s" in str_repr

        none_effect = Effect.create_none_effect()
        none_str = str(none_effect)
        assert "NONE" in none_str

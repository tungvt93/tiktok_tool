"""
Domain Value Objects

Immutable objects that represent concepts in the domain without identity.
"""

from .effect_type import EffectType
from .job_status import JobStatus
from .dimensions import Dimensions

__all__ = [
    'EffectType',
    'JobStatus',
    'Dimensions'
]

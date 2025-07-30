"""
Dimensions Value Object

Represents video dimensions with validation.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Dimensions:
    """Immutable video dimensions"""
    width: int
    height: int

    def __post_init__(self):
        """Validate dimensions after initialization"""
        if self.width <= 0:
            raise ValueError(f"Width must be positive, got {self.width}")
        if self.height <= 0:
            raise ValueError(f"Height must be positive, got {self.height}")

    @property
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio (width/height)"""
        return self.width / self.height

    @property
    def total_pixels(self) -> int:
        """Calculate total number of pixels"""
        return self.width * self.height

    def as_tuple(self) -> Tuple[int, int]:
        """Return as tuple (width, height)"""
        return (self.width, self.height)

    def scale_to_fit(self, target: 'Dimensions') -> 'Dimensions':
        """Scale dimensions to fit within target while maintaining aspect ratio"""
        scale_x = target.width / self.width
        scale_y = target.height / self.height
        scale = min(scale_x, scale_y)

        new_width = int(self.width * scale)
        new_height = int(self.height * scale)

        return Dimensions(new_width, new_height)

    def is_square(self) -> bool:
        """Check if dimensions are square"""
        return self.width == self.height

    def is_landscape(self) -> bool:
        """Check if dimensions are landscape orientation"""
        return self.width > self.height

    def is_portrait(self) -> bool:
        """Check if dimensions are portrait orientation"""
        return self.height > self.width

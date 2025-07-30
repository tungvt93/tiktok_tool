"""
Common Presentation Components

Shared components and patterns used across different presentation interfaces.
"""

from .base_presenter import BasePresenter, BaseView, ViewModelBase, CommandBase, EventAggregator, get_event_aggregator
from .ui_helpers import UIThread, ProgressTracker, FileDialogHelper, MessageBoxHelper, ValidationHelper, FormatHelper

__all__ = [
    # Base classes
    'BasePresenter',
    'BaseView',
    'ViewModelBase',
    'CommandBase',
    'EventAggregator',
    'get_event_aggregator',
    # UI helpers
    'UIThread',
    'ProgressTracker',
    'FileDialogHelper',
    'MessageBoxHelper',
    'ValidationHelper',
    'FormatHelper'
]

"""
Base Presenter

Base class for MVP pattern presenters.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, Callable
import logging

from ...shared.utils import get_logger

logger = get_logger(__name__)


class BaseView(ABC):
    """Base interface for views"""

    @abstractmethod
    def show_error(self, message: str) -> None:
        """Show error message to user"""
    @abstractmethod
    def show_success(self, message: str) -> None:
        """Show success message to user"""
    @abstractmethod
    def show_loading(self, message: str = "Loading...") -> None:
        """Show loading indicator"""
    @abstractmethod
    def hide_loading(self) -> None:
        """Hide loading indicator"""
    @abstractmethod
    def update_ui(self) -> None:
        """Update UI elements"""
class BasePresenter(ABC):
    """Base presenter class implementing common functionality"""

    def __init__(self, view: BaseView):
        """
        Initialize presenter.

        Args:
            view: View instance to control
        """
        self.view = view
        self._event_handlers: Dict[str, list] = {}
        self._is_disposed = False

    def dispose(self) -> None:
        """Clean up presenter resources"""
        if self._is_disposed:
            return

        self._event_handlers.clear()
        self._is_disposed = True
        logger.debug(f"Presenter disposed: {self.__class__.__name__}")

    def add_event_handler(self, event_name: str, handler: Callable) -> None:
        """
        Add event handler.

        Args:
            event_name: Name of the event
            handler: Handler function
        """
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)

    def remove_event_handler(self, event_name: str, handler: Callable) -> None:
        """
        Remove event handler.

        Args:
            event_name: Name of the event
            handler: Handler function to remove
        """
        if event_name in self._event_handlers:
            try:
                self._event_handlers[event_name].remove(handler)
            except ValueError:
                pass  # Handler not found, ignore
    def emit_event(self, event_name: str, *args, **kwargs) -> None:
        """
        Emit event to all registered handlers.

        Args:
            event_name: Name of the event
            *args: Event arguments
            **kwargs: Event keyword arguments
        """
        if self._is_disposed:
            return

        handlers = self._event_handlers.get(event_name, [])
        for handler in handlers:
            try:
                handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in event handler for {event_name}: {e}")

    def handle_error(self, error: Exception, context: str = "") -> None:
        """
        Handle error with user-friendly message.

        Args:
            error: Exception that occurred
            context: Context where error occurred
        """
        from ...shared.utils import handle_exception

        error_result = handle_exception(error, context)
        self.view.show_error(error_result.user_message)

        logger.error(f"Error in presenter {self.__class__.__name__}: {error_result.technical_message}")

    def execute_async(self, operation: Callable,
                     success_callback: Optional[Callable] = None,
                     error_callback: Optional[Callable] = None,
                     loading_message: str = "Processing...") -> None:
        """
        Execute operation asynchronously with loading indicator.

        Args:
            operation: Operation to execute
            success_callback: Called on success with result
            error_callback: Called on error with exception
            loading_message: Message to show while loading
        """
        import threading

        def worker():
            try:
                self.view.show_loading(loading_message)
                result = operation()

                if success_callback:
                    success_callback(result)

            except Exception as e:
                if error_callback:
                    error_callback(e)
                else:
                    self.handle_error(e)
            finally:
                self.view.hide_loading()

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    @abstractmethod
    def initialize(self) -> None:
        """Initialize presenter (called after construction)"""
class ViewModelBase:
    """Base class for view models with property change notification"""

    def __init__(self):
        self._property_changed_handlers: list = []
        self._properties: Dict[str, Any] = {}

    def add_property_changed_handler(self, handler: Callable[[str, Any], None]) -> None:
        """
        Add property changed handler.

        Args:
            handler: Handler function (property_name, new_value)
        """
        self._property_changed_handlers.append(handler)

    def remove_property_changed_handler(self, handler: Callable) -> None:
        """Remove property changed handler"""
        try:
            self._property_changed_handlers.remove(handler)
        except ValueError:
            pass  # Handler not found, ignore
    def set_property(self, name: str, value: Any) -> None:
        """
        Set property value and notify handlers.

        Args:
            name: Property name
            value: New value
        """
        old_value = self._properties.get(name)
        if old_value != value:
            self._properties[name] = value
            self._notify_property_changed(name, value)

    def get_property(self, name: str, default: Any = None) -> Any:
        """
        Get property value.

        Args:
            name: Property name
            default: Default value if property not set

        Returns:
            Property value
        """
        return self._properties.get(name, default)

    def _notify_property_changed(self, name: str, value: Any) -> None:
        """Notify all handlers of property change"""
        for handler in self._property_changed_handlers:
            try:
                handler(name, value)
            except Exception as e:
                logger.error(f"Error in property changed handler: {e}")


class CommandBase:
    """Base class for commands (Command pattern)"""

    def __init__(self, execute_func: Callable, can_execute_func: Optional[Callable] = None):
        """
        Initialize command.

        Args:
            execute_func: Function to execute
            can_execute_func: Function to check if command can execute
        """
        self._execute_func = execute_func
        self._can_execute_func = can_execute_func or (lambda: True)
        self._can_execute_changed_handlers: list = []

    def execute(self, *args, **kwargs) -> Any:
        """Execute command if possible"""
        if self.can_execute(*args, **kwargs):
            return self._execute_func(*args, **kwargs)

    def can_execute(self, *args, **kwargs) -> bool:
        """Check if command can execute"""
        try:
            return self._can_execute_func(*args, **kwargs)
        except Exception:
            return False

    def add_can_execute_changed_handler(self, handler: Callable) -> None:
        """Add handler for can execute changed event"""
        self._can_execute_changed_handlers.append(handler)

    def remove_can_execute_changed_handler(self, handler: Callable) -> None:
        """Remove can execute changed handler"""
        try:
            self._can_execute_changed_handlers.remove(handler)
        except ValueError:
            pass  # Handler not found, ignore
    def raise_can_execute_changed(self) -> None:
        """Notify that can execute status may have changed"""
        for handler in self._can_execute_changed_handlers:
            try:
                handler()
            except Exception as e:
                logger.error(f"Error in can execute changed handler: {e}")


class EventAggregator:
    """Simple event aggregator for loose coupling between components"""

    def __init__(self):
        self._subscribers: Dict[str, list] = {}

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        Subscribe to event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Handler function
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """
        Unsubscribe from event type.

        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler function to remove
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
            except ValueError:
                pass  # Handler not found, ignore
    def publish(self, event_type: str, event_data: Any = None) -> None:
        """
        Publish event to all subscribers.

        Args:
            event_type: Type of event to publish
            event_data: Event data to send
        """
        subscribers = self._subscribers.get(event_type, [])
        for handler in subscribers:
            try:
                handler(event_data)
            except Exception as e:
                logger.error(f"Error in event subscriber for {event_type}: {e}")

    def clear(self) -> None:
        """Clear all subscriptions"""
        self._subscribers.clear()


# Global event aggregator instance
_event_aggregator: Optional[EventAggregator] = None


def get_event_aggregator() -> EventAggregator:
    """Get global event aggregator instance"""
    global _event_aggregator
    if _event_aggregator is None:
        _event_aggregator = EventAggregator()
    return _event_aggregator

"""
Dependency Injection Container

Simple dependency injection container for managing service dependencies.
"""

from typing import Type, TypeVar, Dict, Any, Callable, Optional, List
import inspect
import logging
from abc import ABC

from .app_config import AppConfig

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DIContainer:
    """Simple dependency injection container"""

    def __init__(self, config: AppConfig):
        """
        Initialize DI container with configuration.

        Args:
            config: Application configuration
        """
        self.config = config
        self._services: Dict[Type, Any] = {}
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._interfaces: Dict[Type, Type] = {}

        # Register config as singleton
        self.register_singleton(AppConfig, config)

    def register_singleton(self, interface: Type[T], implementation: Any) -> None:
        """
        Register a singleton service.

        Args:
            interface: Interface type
            implementation: Implementation instance or class
        """
        if inspect.isclass(implementation):
            # If class is provided, instantiate it
            instance = self._create_instance(implementation)
            self._singletons[interface] = instance
        else:
            # If instance is provided, use it directly
            self._singletons[interface] = implementation

        logger.debug(f"Registered singleton: {interface.__name__}")

    def register_transient(self, interface: Type[T], implementation: Type) -> None:
        """
        Register a transient service (new instance each time).

        Args:
            interface: Interface type
            implementation: Implementation class
        """
        self._services[interface] = implementation
        logger.debug(f"Registered transient: {interface.__name__} -> {implementation.__name__}")

    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """
        Register a factory function for creating instances.

        Args:
            interface: Interface type
            factory: Factory function
        """
        self._factories[interface] = factory
        logger.debug(f"Registered factory: {interface.__name__}")

    def register_interface(self, interface: Type, implementation: Type) -> None:
        """
        Register interface to implementation mapping.

        Args:
            interface: Interface type
            implementation: Implementation type
        """
        self._interfaces[interface] = implementation
        logger.debug(f"Registered interface mapping: {interface.__name__} -> {implementation.__name__}")

    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve a service instance.

        Args:
            interface: Interface type to resolve

        Returns:
            Service instance

        Raises:
            ValueError: If service cannot be resolved
        """
        # Check singletons first
        if interface in self._singletons:
            return self._singletons[interface]

        # Check factories
        if interface in self._factories:
            instance = self._factories[interface]()
            logger.debug(f"Created instance from factory: {interface.__name__}")
            return instance

        # Check transient services
        if interface in self._services:
            implementation = self._services[interface]
            instance = self._create_instance(implementation)
            logger.debug(f"Created transient instance: {interface.__name__}")
            return instance

        # Check interface mappings
        if interface in self._interfaces:
            implementation = self._interfaces[interface]
            instance = self._create_instance(implementation)
            logger.debug(f"Created instance from interface mapping: {interface.__name__}")
            return instance

        # Try to create instance directly if it's a concrete class
        if inspect.isclass(interface) and not inspect.isabstract(interface):
            instance = self._create_instance(interface)
            logger.debug(f"Created direct instance: {interface.__name__}")
            return instance

        raise ValueError(f"Cannot resolve service: {interface.__name__}")

    def _create_instance(self, implementation: Type) -> Any:
        """
        Create instance with dependency injection.

        Args:
            implementation: Class to instantiate

        Returns:
            Instance with dependencies injected
        """
        # Get constructor signature
        signature = inspect.signature(implementation.__init__)
        parameters = signature.parameters

        # Skip 'self' parameter
        param_names = [name for name in parameters.keys() if name != 'self']

        if not param_names:
            # No dependencies, create simple instance
            return implementation()

        # Resolve dependencies
        kwargs = {}
        for param_name in param_names:
            param = parameters[param_name]
            param_type = param.annotation

            if param_type == inspect.Parameter.empty:
                # No type annotation, skip
                continue

            try:
                # Try to resolve dependency
                dependency = self.resolve(param_type)
                kwargs[param_name] = dependency
            except ValueError:
                # Check if parameter has default value
                if param.default != inspect.Parameter.empty:
                    # Use default value
                    kwargs[param_name] = param.default
                else:
                    # Cannot resolve required dependency
                    raise ValueError(f"Cannot resolve dependency {param_type.__name__} for {implementation.__name__}")

        return implementation(**kwargs)

    def get_registered_services(self) -> Dict[str, str]:
        """Get information about registered services"""
        services = {}

        for interface in self._singletons:
            services[interface.__name__] = "singleton"

        for interface in self._services:
            services[interface.__name__] = "transient"

        for interface in self._factories:
            services[interface.__name__] = "factory"

        for interface in self._interfaces:
            impl = self._interfaces[interface]
            services[interface.__name__] = f"interface -> {impl.__name__}"

        return services

    def clear(self) -> None:
        """Clear all registered services"""
        self._services.clear()
        self._singletons.clear()
        self._factories.clear()
        self._interfaces.clear()

        # Re-register config
        self.register_singleton(AppConfig, self.config)
        logger.debug("Cleared all services")


class ServiceRegistry:
    """Service registry for managing service registrations"""

    def __init__(self):
        self._registrations: List[Callable[[DIContainer], None]] = []

    def add_registration(self, registration_func: Callable[[DIContainer], None]) -> None:
        """
        Add a service registration function.

        Args:
            registration_func: Function that registers services with container
        """
        self._registrations.append(registration_func)

    def register_all(self, container: DIContainer) -> None:
        """
        Register all services with the container.

        Args:
            container: DI container to register services with
        """
        for registration_func in self._registrations:
            try:
                registration_func(container)
            except Exception as e:
                logger.error(f"Failed to register services: {e}")
                raise


# Global service registry
_service_registry = ServiceRegistry()


def register_services(registration_func: Callable[[DIContainer], None]) -> None:
    """
    Decorator for registering services.

    Args:
        registration_func: Function that registers services
    """
    _service_registry.add_registration(registration_func)


def create_container(config: AppConfig) -> DIContainer:
    """
    Create and configure DI container.

    Args:
        config: Application configuration

    Returns:
        Configured DI container
    """
    container = DIContainer(config)
    _service_registry.register_all(container)
    return container


# Convenience functions for common patterns
def singleton(interface: Type[T]):
    """Decorator for marking classes as singletons"""
    def decorator(implementation: Type[T]) -> Type[T]:
        def register_func(container: DIContainer):
            container.register_singleton(interface, implementation)
        _service_registry.add_registration(register_func)
        return implementation
    return decorator


def transient(interface: Type[T]):
    """Decorator for marking classes as transient"""
    def decorator(implementation: Type[T]) -> Type[T]:
        def register_func(container: DIContainer):
            container.register_transient(interface, implementation)
        _service_registry.add_registration(register_func)
        return implementation
    return decorator


def implements(interface: Type):
    """Decorator for marking implementation classes"""
    def decorator(implementation: Type) -> Type:
        def register_func(container: DIContainer):
            container.register_interface(interface, implementation)
        _service_registry.add_registration(register_func)
        return implementation
    return decorator

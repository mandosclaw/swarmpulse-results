#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: uppark/accio: accio
# Agent:   @aria
# Date:    2026-03-29T09:54:32.579Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Implement core functionality for uppark/accio
MISSION: uppark/accio: accio
CATEGORY: Engineering
AGENT: @aria (SwarmPulse)
DATE: 2025

Accio is a Python package for declarative dependency injection and service discovery.
This implementation provides the core DI container, service registry, and resolver logic
with production-ready error handling and logging.
"""

import argparse
import json
import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, TypeVar, Union
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceScope(Enum):
    """Service lifetime scopes"""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class RegistrationError(Exception):
    """Raised when service registration fails"""
    pass


class ResolutionError(Exception):
    """Raised when service resolution fails"""
    pass


class CircularDependencyError(Exception):
    """Raised when circular dependency is detected"""
    pass


@dataclass
class ServiceDescriptor:
    """Describes a registered service"""
    interface: Type
    implementation: Optional[Type] = None
    factory: Optional[Callable] = None
    instance: Optional[Any] = None
    scope: ServiceScope = ServiceScope.TRANSIENT
    dependencies: List[Type] = field(default_factory=list)
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "interface": self.interface.__name__ if self.interface else None,
            "implementation": self.implementation.__name__ if self.implementation else None,
            "has_factory": self.factory is not None,
            "is_singleton": self.scope == ServiceScope.SINGLETON,
            "dependencies": [d.__name__ for d in self.dependencies],
            "name": self.name,
            "metadata": self.metadata
        }


class ServiceRegistry:
    """Manages service registrations"""

    def __init__(self):
        self._services: Dict[Tuple[Type, Optional[str]], ServiceDescriptor] = {}
        self._type_mappings: Dict[Type, List[ServiceDescriptor]] = {}
        logger.info("ServiceRegistry initialized")

    def register(
        self,
        interface: Type,
        implementation: Optional[Type] = None,
        factory: Optional[Callable] = None,
        scope: ServiceScope = ServiceScope.TRANSIENT,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ServiceDescriptor:
        """Register a service"""
        if implementation is None and factory is None:
            raise RegistrationError(f"Service {interface} must have implementation or factory")

        if implementation is not None and factory is not None:
            raise RegistrationError(f"Service {interface} cannot have both implementation and factory")

        key = (interface, name)
        if key in self._services:
            logger.warning(f"Re-registering service {interface.__name__}:{name}")

        descriptor = ServiceDescriptor(
            interface=interface,
            implementation=implementation,
            factory=factory,
            scope=scope,
            name=name,
            metadata=metadata or {}
        )

        self._services[key] = descriptor
        if interface not in self._type_mappings:
            self._type_mappings[interface] = []
        self._type_mappings[interface].append(descriptor)

        logger.info(f"Registered service {interface.__name__}:{name} (scope: {scope.value})")
        return descriptor

    def register_singleton(
        self,
        interface: Type,
        implementation: Optional[Type] = None,
        factory: Optional[Callable] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ServiceDescriptor:
        """Register a singleton service"""
        return self.register(interface, implementation, factory, ServiceScope.SINGLETON, name, metadata)

    def register_transient(
        self,
        interface: Type,
        implementation: Optional[Type] = None,
        factory: Optional[Callable] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ServiceDescriptor:
        """Register a transient service"""
        return self.register(interface, implementation, factory, ServiceScope.TRANSIENT, name, metadata)

    def get_descriptor(
        self,
        interface: Type,
        name: Optional[str] = None
    ) -> Optional[ServiceDescriptor]:
        """Get service descriptor"""
        return self._services.get((interface, name))

    def get_all_descriptors(self, interface: Type) -> List[ServiceDescriptor]:
        """Get all descriptors for an interface"""
        return self._type_mappings.get(interface, [])

    def list_services(self) -> List[ServiceDescriptor]:
        """List all registered services"""
        return list(self._services.values())

    def unregister(self, interface: Type, name: Optional[str] = None) -> bool:
        """Unregister a service"""
        key = (interface, name)
        if key in self._services:
            descriptor = self._services[key]
            del self._services[key]
            self._type_mappings[interface].remove(descriptor)
            logger.info(f"Unregistered service {interface.__name__}:{name}")
            return True
        return False


class ServiceContainer:
    """Main DI container for resolving services"""

    def __init__(self, registry: Optional[ServiceRegistry] = None):
        self.registry = registry or ServiceRegistry()
        self._singletons: Dict[Tuple[Type, Optional[str]], Any] = {}
        self._scoped_instances: Dict[str, Dict[Tuple[Type, Optional[str]], Any]] = {}
        self._resolution_stack: Set[Tuple[Type, Optional[str]]] = set()
        logger.info("ServiceContainer initialized")

    def register(
        self,
        interface: Type,
        implementation: Optional[Type] = None,
        factory: Optional[Callable] = None,
        scope: ServiceScope = ServiceScope.TRANSIENT,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ServiceDescriptor:
        """Register a service"""
        return self.registry.register(interface, implementation, factory, scope, name, metadata)

    def register_singleton(
        self,
        interface: Type,
        implementation: Optional[Type] = None,
        factory: Optional[Callable] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ServiceDescriptor:
        """Register a singleton"""
        return self.registry.register_singleton(interface, implementation, factory, name, metadata)

    def register_instance(
        self,
        interface: Type,
        instance: Any,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ServiceDescriptor:
        """Register a singleton instance"""
        descriptor = ServiceDescriptor(
            interface=interface,
            instance=instance,
            scope=ServiceScope.SINGLETON,
            name=name,
            metadata=metadata or {}
        )
        key = (interface, name)
        self.registry._services[key] = descriptor
        if interface not in self.registry._type_mappings:
            self.registry._type_mappings[interface] = []
        self.registry._type_mappings[interface].append(descriptor)
        self._singletons[key] = instance
        logger.info(f"Registered instance {interface.__name__}:{name}")
        return descriptor

    def resolve(self, interface: Type, name: Optional[str] = None) -> Any:
        """Resolve a service instance"""
        key = (interface, name)

        # Check for circular dependency
        if key in self._resolution_stack:
            raise CircularDependencyError(f"Circular dependency detected for {interface.__name__}:{name}")

        self._resolution_stack.add(key)
        try:
            descriptor = self.registry.get_descriptor(interface, name)
            if descriptor is None:
                raise ResolutionError(f"Service {interface.__name__}:{name} not registered")

            # Return singleton instance if exists
            if descriptor.scope == ServiceScope.SINGLETON and key in self._singletons:
                return self._singletons[key]

            # Use registered instance
            if descriptor.instance is not None:
                return descriptor.instance

            # Create instance via factory
            if descriptor.factory is not None:
                instance = descriptor.factory(self)
                logger.debug(f"Resolved {interface.__name__}:{name} via factory")
            else:
                instance = self._create_instance(descriptor.implementation)
                logger.debug(f"Resolved {interface.__name__}:{name} via constructor")

            # Cache singleton
            if descriptor.scope == ServiceScope.SINGLETON:
                self._singletons[key] = instance

            return instance

        finally:
            self._resolution_stack.discard(key)

    def resolve_all(self, interface: Type) -> List[Any]:
        """Resolve all services for an interface"""
        descriptors = self.registry.get_all_descriptors(interface)
        return [self.resolve(interface, desc.name) for desc in descriptors]

    def _create_instance(self, impl_class: Type) -> Any:
        """Create an instance with dependency injection"""
        try:
            # Get constructor parameters
            import inspect
            sig = inspect.signature(impl_class.__init__)
            kwargs = {}

            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue

                # Try to resolve by annotation
                if param.annotation != inspect.Parameter.empty:
                    try:
                        kwargs[param_name] = self.resolve(param.annotation)
                    except ResolutionError:
                        if param.default == inspect.Parameter.empty:
                            raise ResolutionError(f"Cannot resolve parameter {param_name} for {impl_class.__name__}")
                elif param.default == inspect.Parameter.empty:
                    raise ResolutionError(f"Cannot infer type for parameter {param_name} in {impl_class.__name__}")

            return impl_class(**kwargs)
        except Exception as e:
            raise ResolutionError(f"Failed to create instance of {impl_class.__name__}: {str(e)}")

    def create_scope(self) -> 'ScopedContainer':
        """Create a new scoped container"""
        return ScopedContainer(self)

    def list_services(self) -> List[Dict[str, Any]]:
        """List all registered services"""
        return [desc.to_dict() for desc in self.registry.list_services()]


class ScopedContainer:
    """Container for scoped service lifetime"""

    def __init__(self, parent: ServiceContainer):
        self.parent = parent
        self._scope_id = f"scope_{id(self)}"
        self._instances: Dict[Tuple[Type, Optional[str]], Any] = {}
        logger.info(f"Created scoped container {self._scope_id}")

    def resolve(self, interface: Type, name: Optional[str] = None) -> Any:
        """Resolve a service in this scope"""
        key = (interface, name)

        descriptor = self.parent.registry.get_descriptor(interface, name)
        if descriptor is None:
            raise ResolutionError(f"Service {interface.__name__}:{name} not registered")

        if descriptor.scope == ServiceScope.SINGLETON:
            return self.parent.resolve(interface, name)

        if descriptor.scope == ServiceScope.SCOPED:
            if key not in self._instances:
                self._instances[key] = self.parent.resolve(interface, name)
            return self._instances[key]

        # Transient
        return self.parent.resolve(interface, name)


def print_service_report(container: ServiceContainer) -> str:
    """Generate a service registration report"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_services": len(container.registry.list_services()),
        "services": container.list_services()
    }
    return json.dumps(report, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Accio DI Container - Service Discovery and Dependency Injection"
    )
    parser.add_argument(
        "--mode",
        choices=["run", "list", "test"],
        default="test",
        help="Execution mode"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for report (JSON)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    parser.add_argument(
        "--scope",
        choices=["singleton", "transient", "scoped"],
        default="transient",
        help="Default service scope"
    )

    args = parser.parse_args()
    logger.setLevel(args.log_level)

    # Create container and example services
    container = ServiceContainer()

    # Define example services
    class IDatabase(ABC):
        @abstractmethod
        def connect(self) -> str:
            pass

    class PostgresDatabase(IDatabase):
        def __init__(self):
            self.connection_string = "postgresql://localhost/accio"
            logger.info("PostgresDatabase initialized")

        def connect(self) -> str:
            return f"Connected to {self.connection_string}"

    class ILogger(ABC):
        @abstractmethod
        def log(self, message: str) -> None:
            pass

    class ConsoleLogger(ILogger):
        def __init__(self):
            logger.info("ConsoleLogger initialized")

        def log(self, message: str) -> None:
            print(f"[LOG] {message}")

    class UserService:
        def __init__(self, db: IDatabase, logger: ILogger):
            self.db = db
            self.logger = logger
            logger.log("UserService initialized")

        def get_users(self) -> str:
            self.logger.log("Fetching users")
            return f"Users from {self.db.connect()}"

    # Register services
    scope_enum = ServiceScope(args.scope)
    container.register_singleton(IDatabase, PostgresDatabase)
    container.register(ILogger, ConsoleLogger, scope=scope_enum)
    container.register(UserService, scope=scope_enum)

    if args.mode == "list":
        print("\n=== Registered Services ===")
        print(print_service_report(container))

    elif args.mode == "test":
        print("\n=== Service Resolution Test ===")

        # Test transient resolution
        print("\n1. Testing UserService resolution:")
        user_service = container.resolve(UserService)
        result = user_service.get_users()
        print(f"   Result: {result}")

        # Test singleton
        print("\n2. Testing Database singleton:")
        db1 = container.resolve(IDatabase)
        db2 = container.resolve(IDatabase)
        print(f"   Same instance: {db1 is db2}")

        # Test scoped container
        print("\n3. Testing scoped container:")
        scope = container.create_scope()
        logger_1 = scope.resolve(ILogger)
        logger_2 = scope.resolve(ILogger)
        print(f"   Scoped loggers same: {logger_1 is logger_2}")

        # Test resolve all
        print("\n4. Testing resolve all:")
        container.register(ILogger, ConsoleLogger, name="logger2")
        all_loggers = container.resolve_all(ILogger)
        print(f"   Total loggers:
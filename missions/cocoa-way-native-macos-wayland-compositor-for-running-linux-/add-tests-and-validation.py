#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Add tests and validation
# Mission: Cocoa-Way – Native macOS Wayland compositor for running Linux apps seamlessly
# Agent:   @aria
# Date:    2026-03-29T20:40:51.720Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Add tests and validation for Cocoa-Way
Mission: Cocoa-Way – Native macOS Wayland compositor for running Linux apps seamlessly
Agent: @aria (SwarmPulse)
Date: 2025

Unit tests covering main scenarios for the Cocoa-Way Wayland compositor.
This module provides comprehensive test coverage and validation for core functionality.
"""

import unittest
import json
import sys
import argparse
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime


class PlatformType(Enum):
    """Supported platform types."""
    MACOS = "macos"
    LINUX = "linux"
    WAYLAND = "wayland"


class AppStatus(Enum):
    """Application status states."""
    RUNNING = "running"
    STOPPED = "stopped"
    CRASHED = "crashed"
    SUSPENDED = "suspended"


@dataclass
class WaylandDisplay:
    """Represents a Wayland display configuration."""
    display_id: str
    width: int
    height: int
    refresh_rate: float
    scale: float
    enabled: bool

    def validate(self) -> Tuple[bool, str]:
        """Validate display configuration."""
        if self.width <= 0 or self.height <= 0:
            return False, "Display dimensions must be positive"
        if self.refresh_rate <= 0:
            return False, "Refresh rate must be positive"
        if self.scale <= 0:
            return False, "Scale factor must be positive"
        if not self.display_id:
            return False, "Display ID cannot be empty"
        return True, "Display configuration valid"


@dataclass
class LinuxApplication:
    """Represents a Linux application running under Cocoa-Way."""
    app_id: str
    name: str
    pid: int
    status: AppStatus
    memory_mb: float
    cpu_percent: float
    platform: PlatformType
    wayland_socket: Optional[str] = None

    def validate(self) -> Tuple[bool, str]:
        """Validate application configuration."""
        if not self.app_id:
            return False, "Application ID cannot be empty"
        if not self.name:
            return False, "Application name cannot be empty"
        if self.pid < 0:
            return False, "PID must be non-negative"
        if self.memory_mb < 0:
            return False, "Memory usage cannot be negative"
        if self.cpu_percent < 0 or self.cpu_percent > 100:
            return False, "CPU percentage must be between 0 and 100"
        if self.platform != PlatformType.LINUX:
            return False, f"App must target Linux, got {self.platform}"
        return True, "Application configuration valid"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data['status'] = self.status.value
        data['platform'] = self.platform.value
        return data


class CompositorCore:
    """Core Cocoa-Way compositor functionality."""

    def __init__(self):
        """Initialize the compositor."""
        self.displays: Dict[str, WaylandDisplay] = {}
        self.applications: Dict[str, LinuxApplication] = {}
        self.active_display: Optional[str] = None
        self.initialization_time = datetime.now()

    def add_display(self, display: WaylandDisplay) -> Tuple[bool, str]:
        """Register a Wayland display."""
        is_valid, message = display.validate()
        if not is_valid:
            return False, message

        if display.display_id in self.displays:
            return False, f"Display {display.display_id} already registered"

        self.displays[display.display_id] = display
        if self.active_display is None:
            self.active_display = display.display_id
        return True, f"Display {display.display_id} registered successfully"

    def remove_display(self, display_id: str) -> Tuple[bool, str]:
        """Unregister a Wayland display."""
        if display_id not in self.displays:
            return False, f"Display {display_id} not found"

        if self.active_display == display_id:
            remaining = [d for d in self.displays.keys() if d != display_id]
            self.active_display = remaining[0] if remaining else None

        del self.displays[display_id]
        return True, f"Display {display_id} removed successfully"

    def launch_application(self, app: LinuxApplication) -> Tuple[bool, str]:
        """Launch a Linux application."""
        is_valid, message = app.validate()
        if not is_valid:
            return False, message

        if app.app_id in self.applications:
            return False, f"Application {app.app_id} already running"

        if not self.active_display:
            return False, "No active display available"

        app.wayland_socket = f"wayland-{self.active_display}"
        self.applications[app.app_id] = app
        return True, f"Application {app.app_id} launched successfully"

    def terminate_application(self, app_id: str) -> Tuple[bool, str]:
        """Terminate a running Linux application."""
        if app_id not in self.applications:
            return False, f"Application {app_id} not found"

        app = self.applications[app_id]
        if app.status == AppStatus.RUNNING:
            app.status = AppStatus.STOPPED
        del self.applications[app_id]
        return True, f"Application {app_id} terminated successfully"

    def get_application_metrics(self, app_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a running application."""
        if app_id not in self.applications:
            return None

        app = self.applications[app_id]
        return {
            "app_id": app.app_id,
            "name": app.name,
            "status": app.status.value,
            "memory_mb": app.memory_mb,
            "cpu_percent": app.cpu_percent,
            "wayland_socket": app.wayland_socket
        }

    def update_application_status(self, app_id: str, status: AppStatus) -> Tuple[bool, str]:
        """Update application execution status."""
        if app_id not in self.applications:
            return False, f"Application {app_id} not found"

        self.applications[app_id].status = status
        return True, f"Application {app_id} status updated to {status.value}"

    def get_display_info(self, display_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a registered display."""
        if display_id not in self.displays:
            return None

        display = self.displays[display_id]
        return {
            "display_id": display.display_id,
            "width": display.width,
            "height": display.height,
            "refresh_rate": display.refresh_rate,
            "scale": display.scale,
            "enabled": display.enabled
        }

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        running_apps = sum(1 for app in self.applications.values()
                          if app.status == AppStatus.RUNNING)
        total_memory = sum(app.memory_mb for app in self.applications.values())
        avg_cpu = (sum(app.cpu_percent for app in self.applications.values()) /
                   len(self.applications) if self.applications else 0)

        return {
            "timestamp": datetime.now().isoformat(),
            "active_displays": len([d for d in self.displays.values() if d.enabled]),
            "total_displays": len(self.displays),
            "running_applications": running_apps,
            "total_applications": len(self.applications),
            "total_memory_mb": total_memory,
            "average_cpu_percent": avg_cpu,
            "uptime_seconds": (datetime.now() - self.initialization_time).total_seconds()
        }


class TestWaylandDisplay(unittest.TestCase):
    """Unit tests for Wayland display configuration."""

    def test_valid_display_creation(self):
        """Test creating a valid display configuration."""
        display = WaylandDisplay(
            display_id="HDMI-1",
            width=1920,
            height=1080,
            refresh_rate=60.0,
            scale=1.0,
            enabled=True
        )
        is_valid, message = display.validate()
        self.assertTrue(is_valid)
        self.assertIn("valid", message.lower())

    def test_invalid_display_dimensions(self):
        """Test display with invalid dimensions."""
        display = WaylandDisplay(
            display_id="HDMI-1",
            width=-1,
            height=1080,
            refresh_rate=60.0,
            scale=1.0,
            enabled=True
        )
        is_valid, message = display.validate()
        self.assertFalse(is_valid)
        self.assertIn("dimensions", message.lower())

    def test_invalid_display_refresh_rate(self):
        """Test display with invalid refresh rate."""
        display = WaylandDisplay(
            display_id="HDMI-1",
            width=1920,
            height=1080,
            refresh_rate=0,
            scale=1.0,
            enabled=True
        )
        is_valid, message = display.validate()
        self.assertFalse(is_valid)
        self.assertIn("refresh", message.lower())

    def test_invalid_display_scale(self):
        """Test display with invalid scale factor."""
        display = WaylandDisplay(
            display_id="HDMI-1",
            width=1920,
            height=1080,
            refresh_rate=60.0,
            scale=-1.0,
            enabled=True
        )
        is_valid, message = display.validate()
        self.assertFalse(is_valid)
        self.assertIn("scale", message.lower())

    def test_empty_display_id(self):
        """Test display with empty ID."""
        display = WaylandDisplay(
            display_id="",
            width=1920,
            height=1080,
            refresh_rate=60.0,
            scale=1.0,
            enabled=True
        )
        is_valid, message = display.validate()
        self.assertFalse(is_valid)
        self.assertIn("id", message.lower())


class TestLinuxApplication(unittest.TestCase):
    """Unit tests for Linux application configuration."""

    def test_valid_application_creation(self):
        """Test creating a valid Linux application."""
        app = LinuxApplication(
            app_id="firefox-001",
            name="Firefox",
            pid=1234,
            status=AppStatus.RUNNING,
            memory_mb=512.5,
            cpu_percent=25.0,
            platform=PlatformType.LINUX
        )
        is_valid, message = app.validate()
        self.assertTrue(is_valid)
        self.assertIn("valid", message.lower())

    def test_invalid_application_pid(self):
        """Test application with invalid PID."""
        app = LinuxApplication(
            app_id="firefox-001",
            name="Firefox",
            pid=-1,
            status=AppStatus.RUNNING,
            memory_mb=512.5,
            cpu_percent=25.0,
            platform=PlatformType.LINUX
        )
        is_valid, message = app.validate()
        self.assertFalse(is_valid)
        self.assertIn("pid", message.lower())

    def test_invalid_application_memory(self):
        """Test application with invalid memory."""
        app = LinuxApplication(
            app_id="firefox-001",
            name="Firefox",
            pid=1234,
            status=AppStatus.RUNNING,
            memory_mb=-100.0,
            cpu_percent=25.0,
            platform=PlatformType.LINUX
        )
        is_valid, message = app.validate()
        self.assertFalse(is_valid)
        self.assertIn("memory", message.lower())

    def test_invalid_application_cpu(self):
        """Test application with invalid CPU usage."""
        app = LinuxApplication(
            app_id="firefox-001",
            name="Firefox",
            pid=1234,
            status=AppStatus.RUNNING,
            memory_mb=512.5,
            cpu_percent=150.0,
            platform=PlatformType.LINUX
        )
        is_valid, message = app.validate()
        self.assertFalse(is_valid)
        self.assertIn("cpu", message.lower())

    def test_invalid_application_empty_name(self):
        """Test application with empty name."""
        app = LinuxApplication(
            app_id="firefox-001",
            name="",
            pid=1234,
            status=AppStatus.RUNNING,
            memory_mb=512.5,
            cpu_percent=25.0,
            platform=PlatformType.LINUX
        )
        is_valid, message = app.validate()
        self.assertFalse(is_valid)
        self.assertIn("name", message.lower())

    def test_invalid_application_platform(self):
        """Test application with wrong platform."""
        app = LinuxApplication(
            app_id="firefox-001",
            name="Firefox",
            pid=1234,
            status=AppStatus.RUNNING,
            memory_mb=512.5,
            cpu_percent=25.0,
            platform=PlatformType.MACOS
        )
        is_valid, message = app.validate()
        self.assertFalse(is_valid)
        self.assertIn("linux", message.lower())

    def test_application_to_dict(self):
        """Test converting application to dictionary."""
        app = LinuxApplication(
            app_id="firefox-001",
            name="Firefox",
            pid=1234,
            status=AppStatus.RUNNING,
            memory_mb=512.5,
            cpu_percent=25.0,
            platform=PlatformType.LINUX
        )
        app_dict = app.to_dict()
        self.assertEqual(app_dict["app_id"], "firefox-001")
        self.assertEqual(app_dict["status"], "running")
        self.assertEqual(app_dict["platform"], "linux")


class TestCompositorCore(unittest.TestCase):
    """Unit tests for Cocoa-Way compositor core functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.compositor = CompositorCore()

    def test_compositor_initialization(self):
        """Test compositor initializes correctly."""
        self.assertEqual(len(self.compositor.displays), 0)
        self.assertEqual(len(self.compositor.applications), 0)
        self.assertIsNone(self.compositor.active_display)

    def test_add_single_display(self):
        """Test adding a single display."""
        display = WaylandDisplay(
            display_id="HDMI-1",
            width=1920,
            height=1080,
            refresh_rate=60.0,
            scale=1.0,
            enabled=True
        )
        success, message = self.compositor.add_display(display)
        self.assertTrue(success)
        self.assertEqual(len(self.compositor.displays), 1)
        self.assertEqual(self.compositor.active_display, "HDMI-1")

    def test_add_multiple_displays(self):
        """Test adding multiple displays."""
        for i in range(3):
            display = WaylandDisplay(
                display_id=f"HDMI-{i}",
                width=1920,
                height=1080,
                refresh_rate=60.0,
                scale=1.0,
                enabled=True
            )
            success, message = self.compositor.add_display(display)
            self.assertTrue(success)

        self.assertEqual(len(self.compositor.displays), 3)
        self.assertEqual(self
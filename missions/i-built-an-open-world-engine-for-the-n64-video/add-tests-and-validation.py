#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Add tests and validation
# Mission: I Built an Open-World Engine for the N64 [video]
# Agent:   @aria
# Date:    2026-03-31T19:32:01.399Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Add tests and validation for N64 Open-World Engine
Mission: I Built an Open-World Engine for the N64 [video]
Agent: @aria
Date: 2024
Category: Engineering - Unit tests covering main scenarios
"""

import unittest
import sys
import argparse
import json
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from enum import Enum


class TextureFormat(Enum):
    """Supported texture formats for N64 engine."""
    RGBA16 = "rgba16"
    RGBA32 = "rgba32"
    CI4 = "ci4"
    CI8 = "ci8"
    IA4 = "ia4"
    IA8 = "ia8"


@dataclass
class Vector3:
    """3D vector for world coordinates."""
    x: float
    y: float
    z: float
    
    def distance_to(self, other: 'Vector3') -> float:
        """Calculate Euclidean distance to another vector."""
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return (dx*dx + dy*dy + dz*dz) ** 0.5
    
    def magnitude(self) -> float:
        """Calculate vector magnitude."""
        return (self.x*self.x + self.y*self.y + self.z*self.z) ** 0.5
    
    def normalize(self) -> 'Vector3':
        """Return normalized vector."""
        mag = self.magnitude()
        if mag == 0:
            return Vector3(0, 0, 0)
        return Vector3(self.x/mag, self.y/mag, self.z/mag)


@dataclass
class TextureInfo:
    """Texture metadata for N64 engine."""
    name: str
    width: int
    height: int
    format: TextureFormat
    size_bytes: int
    
    def validate(self) -> Tuple[bool, str]:
        """Validate texture properties."""
        if self.width <= 0 or self.height <= 0:
            return False, "Invalid texture dimensions"
        
        if self.width > 2048 or self.height > 2048:
            return False, "Texture exceeds N64 memory limits"
        
        if not (self.width & (self.width - 1) == 0 and self.width != 0):
            return False, "Texture width must be power of 2"
        
        if not (self.height & (self.height - 1) == 0 and self.height != 0):
            return False, "Texture height must be power of 2"
        
        expected_size = self._calculate_expected_size()
        if self.size_bytes != expected_size:
            return False, f"Size mismatch: expected {expected_size}, got {self.size_bytes}"
        
        return True, "Valid"
    
    def _calculate_expected_size(self) -> int:
        """Calculate expected texture size based on format."""
        area = self.width * self.height
        
        format_bits = {
            TextureFormat.RGBA16: 16,
            TextureFormat.RGBA32: 32,
            TextureFormat.CI4: 4,
            TextureFormat.CI8: 8,
            TextureFormat.IA4: 4,
            TextureFormat.IA8: 8,
        }
        
        bits = format_bits.get(self.format, 16)
        return (area * bits) // 8


@dataclass
class Mesh:
    """3D mesh data for world objects."""
    name: str
    vertices: List[Vector3]
    indices: List[int]
    material_name: str
    
    def validate(self) -> Tuple[bool, str]:
        """Validate mesh data integrity."""
        if not self.vertices:
            return False, "Mesh must have vertices"
        
        if not self.indices:
            return False, "Mesh must have indices"
        
        max_index = max(self.indices) if self.indices else -1
        if max_index >= len(self.vertices):
            return False, f"Index {max_index} exceeds vertex count {len(self.vertices)}"
        
        if any(idx < 0 for idx in self.indices):
            return False, "Negative indices not allowed"
        
        if len(self.indices) % 3 != 0:
            return False, "Indices must define complete triangles"
        
        return True, "Valid"
    
    def get_bounds(self) -> Tuple[Vector3, Vector3]:
        """Get axis-aligned bounding box."""
        if not self.vertices:
            return Vector3(0, 0, 0), Vector3(0, 0, 0)
        
        min_x = min(v.x for v in self.vertices)
        max_x = max(v.x for v in self.vertices)
        min_y = min(v.y for v in self.vertices)
        max_y = max(v.y for v in self.vertices)
        min_z = min(v.z for v in self.vertices)
        max_z = max(v.z for v in self.vertices)
        
        return Vector3(min_x, min_y, min_z), Vector3(max_x, max_y, max_z)
    
    def vertex_count(self) -> int:
        """Return vertex count."""
        return len(self.vertices)
    
    def triangle_count(self) -> int:
        """Return triangle count."""
        return len(self.indices) // 3


@dataclass
class WorldArea:
    """Represents a world area in the open-world engine."""
    name: str
    meshes: List[Mesh]
    textures: List[TextureInfo]
    center: Vector3
    radius: float
    
    def validate(self) -> Tuple[bool, str]:
        """Validate world area configuration."""
        if self.radius <= 0:
            return False, "Area radius must be positive"
        
        if not self.meshes:
            return False, "Area must contain at least one mesh"
        
        for mesh in self.meshes:
            valid, msg = mesh.validate()
            if not valid:
                return False, f"Mesh '{mesh.name}' invalid: {msg}"
        
        if not self.textures:
            return False, "Area must contain at least one texture"
        
        for texture in self.textures:
            valid, msg = texture.validate()
            if not valid:
                return False, f"Texture '{texture.name}' invalid: {msg}"
        
        return True, "Valid"
    
    def get_total_vertex_count(self) -> int:
        """Get total vertices across all meshes."""
        return sum(mesh.vertex_count() for mesh in self.meshes)
    
    def get_total_memory_usage(self) -> int:
        """Get total memory usage in bytes."""
        mesh_memory = sum(
            mesh.vertex_count() * 12 for mesh in self.meshes
        )
        texture_memory = sum(tex.size_bytes for tex in self.textures)
        return mesh_memory + texture_memory
    
    def is_point_in_area(self, point: Vector3) -> bool:
        """Check if point is within area bounds."""
        return point.distance_to(self.center) <= self.radius


class N64EngineTestSuite(unittest.TestCase):
    """Comprehensive test suite for N64 open-world engine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_vector_a = Vector3(1.0, 2.0, 3.0)
        self.test_vector_b = Vector3(4.0, 5.0, 6.0)
        
        self.test_vertices = [
            Vector3(0, 0, 0),
            Vector3(1, 0, 0),
            Vector3(0, 1, 0),
            Vector3(1, 1, 0),
        ]
        
        self.test_indices = [0, 1, 2, 1, 3, 2]
        
        self.valid_texture = TextureInfo(
            name="test_texture",
            width=256,
            height=256,
            format=TextureFormat.RGBA16,
            size_bytes=131072
        )
        
        self.valid_mesh = Mesh(
            name="test_mesh",
            vertices=self.test_vertices,
            indices=self.test_indices,
            material_name="default"
        )
    
    def test_vector3_magnitude(self):
        """Test vector magnitude calculation."""
        result = self.test_vector_a.magnitude()
        expected = (1*1 + 2*2 + 3*3) ** 0.5
        self.assertAlmostEqual(result, expected, places=5)
    
    def test_vector3_distance(self):
        """Test distance between vectors."""
        result = self.test_vector_a.distance_to(self.test_vector_b)
        expected = ((4-1)**2 + (5-2)**2 + (6-3)**2) ** 0.5
        self.assertAlmostEqual(result, expected, places=5)
    
    def test_vector3_normalize(self):
        """Test vector normalization."""
        normalized = self.test_vector_a.normalize()
        mag = normalized.magnitude()
        self.assertAlmostEqual(mag, 1.0, places=5)
    
    def test_vector3_zero_normalize(self):
        """Test normalizing zero vector."""
        zero = Vector3(0, 0, 0)
        result = zero.normalize()
        self.assertEqual(result.magnitude(), 0)
    
    def test_texture_validation_valid(self):
        """Test valid texture passes validation."""
        valid, msg = self.valid_texture.validate()
        self.assertTrue(valid, msg)
    
    def test_texture_validation_invalid_size(self):
        """Test texture with invalid size."""
        invalid_tex = TextureInfo(
            name="bad_texture",
            width=256,
            height=256,
            format=TextureFormat.RGBA16,
            size_bytes=1000
        )
        valid, msg = invalid_tex.validate()
        self.assertFalse(valid)
        self.assertIn("Size mismatch", msg)
    
    def test_texture_validation_non_power_of_two_width(self):
        """Test texture with non-power-of-2 width."""
        invalid_tex = TextureInfo(
            name="bad_texture",
            width=255,
            height=256,
            format=TextureFormat.RGBA16,
            size_bytes=131072
        )
        valid, msg = invalid_tex.validate()
        self.assertFalse(valid)
        self.assertIn("power of 2", msg)
    
    def test_texture_validation_dimension_overflow(self):
        """Test texture exceeding N64 limits."""
        invalid_tex = TextureInfo(
            name="huge_texture",
            width=4096,
            height=4096,
            format=TextureFormat.RGBA16,
            size_bytes=33554432
        )
        valid, msg = invalid_tex.validate()
        self.assertFalse(valid)
        self.assertIn("memory limits", msg)
    
    def test_mesh_validation_valid(self):
        """Test valid mesh passes validation."""
        valid, msg = self.valid_mesh.validate()
        self.assertTrue(valid, msg)
    
    def test_mesh_validation_no_vertices(self):
        """Test mesh with no vertices."""
        invalid_mesh = Mesh(
            name="empty",
            vertices=[],
            indices=[],
            material_name="default"
        )
        valid, msg = invalid_mesh.validate()
        self.assertFalse(valid)
    
    def test_mesh_validation_index_overflow(self):
        """Test mesh with out-of-bounds indices."""
        invalid_mesh = Mesh(
            name="bad_indices",
            vertices=self.test_vertices,
            indices=[0, 1, 5],
            material_name="default"
        )
        valid, msg = invalid_mesh.validate()
        self.assertFalse(valid)
        self.assertIn("exceeds vertex count", msg)
    
    def test_mesh_validation_negative_indices(self):
        """Test mesh with negative indices."""
        invalid_mesh = Mesh(
            name="negative_indices",
            vertices=self.test_vertices,
            indices=[0, 1, -1],
            material_name="default"
        )
        valid, msg = invalid_mesh.validate()
        self.assertFalse(valid)
        self.assertIn("Negative indices", msg)
    
    def test_mesh_validation_non_triangle_indices(self):
        """Test mesh with non-triangle index count."""
        invalid_mesh = Mesh(
            name="bad_count",
            vertices=self.test_vertices,
            indices=[0, 1],
            material_name="default"
        )
        valid, msg = invalid_mesh.validate()
        self.assertFalse(valid)
        self.assertIn("complete triangles", msg)
    
    def test_mesh_bounds(self):
        """Test mesh bounding box calculation."""
        min_bound, max_bound = self.valid_mesh.get_bounds()
        self.assertEqual(min_bound.x, 0)
        self.assertEqual(min_bound.y, 0)
        self.assertEqual(max_bound.x, 1)
        self.assertEqual(max_bound.y, 1)
    
    def test_mesh_vertex_count(self):
        """Test mesh vertex count."""
        count = self.valid_mesh.vertex_count()
        self.assertEqual(count, 4)
    
    def test_mesh_triangle_count(self):
        """Test mesh triangle count."""
        count = self.valid_mesh.triangle_count()
        self.assertEqual(count, 2)
    
    def test_world_area_validation_valid(self):
        """Test valid world area passes validation."""
        area = WorldArea(
            name="test_area",
            meshes=[self.valid_mesh],
            textures=[self.valid_texture],
            center=Vector3(0, 0, 0),
            radius=100.0
        )
        valid, msg = area.validate()
        self.assertTrue(valid, msg)
    
    def test_world_area_validation_no_meshes(self):
        """Test world area with no meshes."""
        area = WorldArea(
            name="empty_area",
            meshes=[],
            textures=[self.valid_texture],
            center=Vector3(0, 0, 0),
            radius=100.0
        )
        valid, msg = area.validate()
        self.assertFalse(valid)
        self.assertIn("at least one mesh", msg)
    
    def test_world_area_validation_negative_radius(self):
        """Test world area with negative radius."""
        area = WorldArea(
            name="bad_area",
            meshes=[self.valid_mesh],
            textures=[self.valid_texture],
            center=Vector3(0, 0, 0),
            radius=-50.0
        )
        valid, msg = area.validate()
        self.assertFalse(valid)
    
    def test_world_area_total_vertex_count(self):
        """Test world area total vertex count."""
        area = WorldArea(
            name="test_area",
            meshes=[self.valid_mesh, self.valid_mesh],
            textures=[self.valid_texture],
            center=Vector3(0, 0, 0),
            radius=100.0
        )
        count = area.get_total_vertex_count()
        self.assertEqual(count, 8)
    
    def test_world_area_memory_usage(self):
        """Test world area memory calculation."""
        area = WorldArea(
            name="test_area",
            meshes=[self.valid_mesh],
            textures=[self.valid_texture],
            center=Vector3(0, 0, 0),
            radius=100.0
        )
        memory = area.get_total_memory_usage()
        self.assertGreater(memory, 0)
        self.assertTrue(memory >= 131072)
    
    def test_world_area_point_in_area(self):
        """Test point containment in world area."""
        area = WorldArea(
            name="test_area",
            meshes=[self.valid_mesh],
            textures=[self.valid_texture],
            center=Vector3(0, 0, 0),
            radius=100.0
        )
        inside_point = Vector3(10, 10, 10)
        outside_point = Vector3(200, 200, 200)
        
        self.assertTrue(area.is_point_in_area(inside_point))
        self.assertFalse(area.is_point_in_area(outside_point))
    
    def test_texture_size_calculation_rgba16(self):
        """Test texture size calculation for RGBA16."""
        tex = TextureInfo(
            name="test",
            width=128,
            height=128,
            format=TextureFormat.RGBA16,
            size_bytes=32768
        )
        valid, _ = tex.validate()
        self.assertTrue(valid)
    
    def test_texture_size_calculation_ci4(self):
        """Test texture size calculation for CI4."""
        tex = TextureInfo(
            name="test",
            width=256,
            height=256,
            format=TextureFormat.CI4,
            size_bytes=16384
        )
        valid, _ = tex.validate()
        self.assertTrue(valid)
    
    def test_multiple_meshes_validation(self):
        """Test area with multiple meshes."""
        mesh1 = Mesh(
            name="mesh1",
            vertices=self.test_vertices,
            indices=self.test_indices,
            material_name="mat1"
        )
        mesh2 = Mesh(
            name="mesh2",
            vertices=self.test_vertices,
            indices=self.test_indices,
            material_name="mat2"
        )
        
        area = WorldArea(
            name="complex_area",
            meshes=[mesh1, mesh2],
            textures=[self.valid_texture],
            center=Vector3(0, 0, 0),
            radius=100.0
        )
        valid, msg = area.validate()
        self.assertTrue(valid, msg)
        self.assertEqual(area.get_total_vertex_count(), 8)


class TestRunner:
    """Runner for executing tests with reporting."""
    
    def __init__(self, verbosity: int = 2):
        """Initialize test runner."""
        self.verbosity = verbosity
        self.results = None
    
    def run(self) -> Dict:
        """Run all tests and return results."""
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(N64EngineTestSuite)
        runner = unittest.TextTestRunner(verbosity=self.verbosity)
        self.results = runner.run(suite)
        
        return self.get_summary()
    
    def get_summary(self) -> Dict:
        """Get test summary as dictionary."""
        if not self.results:
            return {}
        
        return {
            "total_tests": self.results.testsRun,
            "passed": self.results.testsRun - len(self.results.failures) - len(self.results.errors),
            "failed": len(self.results.failures),
            "errors": len(self.results.errors),
            "skipped": len(self.results.skipped),
            "success": self.results.wasSuccessful()
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="N64 Open-World Engine Test Suite"
    )
    parser.add_argument(
        "--verbosity",
        type=int,
        choices=[0, 1, 2],
        default=2,
        help="Test output verbosity level"
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        help="Write results to JSON file"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner(verbosity=args.verbosity)
    summary = runner.run()
    
    if args.json_output or args.output_file:
        output = json.dumps(summary, indent=2)
        if args.output_file:
            with open(args.output_file, 'w') as f:
                f.write(output)
            print(f"Results written to {args.output_file}")
        else:
            print(output)
    
    sys.exit(0 if summary["success"] else 1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Add tests and validation
# Mission: I Built an Open-World Engine for the N64 [video]
# Agent:   @aria
# Date:    2026-04-01T17:02:16.988Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Add tests and validation for N64 Open-World Engine
Mission: I Built an Open-World Engine for the N64 [video]
Agent: @aria (SwarmPulse)
Date: 2024
"""

import unittest
import sys
import json
import argparse
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from enum import Enum
from math import sqrt


class GeometryType(Enum):
    MESH = "mesh"
    COLLIDER = "collider"
    TRIGGER = "trigger"


@dataclass
class Vector3:
    x: float
    y: float
    z: float
    
    def __add__(self, other):
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other):
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def distance_to(self, other):
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return sqrt(dx*dx + dy*dy + dz*dz)
    
    def magnitude(self):
        return sqrt(self.x*self.x + self.y*self.y + self.z*self.z)


@dataclass
class Bounds3D:
    min_point: Vector3
    max_point: Vector3
    
    def contains_point(self, point: Vector3) -> bool:
        return (self.min_point.x <= point.x <= self.max_point.x and
                self.min_point.y <= point.y <= self.max_point.y and
                self.min_point.z <= point.z <= self.max_point.z)
    
    def intersects(self, other: 'Bounds3D') -> bool:
        return (self.min_point.x <= other.max_point.x and
                self.max_point.x >= other.min_point.x and
                self.min_point.y <= other.max_point.y and
                self.max_point.y >= other.min_point.y and
                self.min_point.z <= other.max_point.z and
                self.max_point.z >= other.min_point.z)


class Geometry:
    def __init__(self, geom_id: str, geom_type: GeometryType, bounds: Bounds3D, vertex_count: int):
        self.id = geom_id
        self.type = geom_type
        self.bounds = bounds
        self.vertex_count = vertex_count
        self.is_loaded = False
    
    def validate(self) -> Tuple[bool, str]:
        if not self.id or len(self.id) == 0:
            return False, "Geometry ID cannot be empty"
        
        if self.vertex_count < 0:
            return False, f"Vertex count cannot be negative: {self.vertex_count}"
        
        if self.bounds.min_point.x > self.bounds.max_point.x:
            return False, "Bounding box invalid: min.x > max.x"
        if self.bounds.min_point.y > self.bounds.max_point.y:
            return False, "Bounding box invalid: min.y > max.y"
        if self.bounds.min_point.z > self.bounds.max_point.z:
            return False, "Bounding box invalid: min.z > max.z"
        
        return True, "Valid"
    
    def load(self) -> bool:
        if self.vertex_count == 0:
            return False
        self.is_loaded = True
        return True


class Actor:
    def __init__(self, actor_id: str, position: Vector3, geometry: Geometry):
        self.id = actor_id
        self.position = position
        self.geometry = geometry
        self.is_active = True
    
    def validate(self) -> Tuple[bool, str]:
        if not self.id or len(self.id) == 0:
            return False, "Actor ID cannot be empty"
        
        if not self.geometry:
            return False, "Actor must have associated geometry"
        
        geom_valid, geom_msg = self.geometry.validate()
        if not geom_valid:
            return False, f"Geometry validation failed: {geom_msg}"
        
        return True, "Valid"
    
    def get_world_bounds(self) -> Bounds3D:
        offset = self.position - self.geometry.bounds.min_point
        new_min = self.geometry.bounds.min_point + offset
        new_max = self.geometry.bounds.max_point + offset
        return Bounds3D(new_min, new_max)


class WorldChunk:
    def __init__(self, chunk_id: str, bounds: Bounds3D):
        self.id = chunk_id
        self.bounds = bounds
        self.actors: List[Actor] = []
        self.is_loaded = False
    
    def add_actor(self, actor: Actor) -> Tuple[bool, str]:
        valid, msg = actor.validate()
        if not valid:
            return False, f"Cannot add invalid actor: {msg}"
        
        if not self.bounds.contains_point(actor.position):
            return False, f"Actor position {actor.position} outside chunk bounds"
        
        self.actors.append(actor)
        return True, "Actor added"
    
    def get_actors_near(self, position: Vector3, radius: float) -> List[Actor]:
        nearby = []
        for actor in self.actors:
            if position.distance_to(actor.position) <= radius:
                nearby.append(actor)
        return nearby
    
    def validate(self) -> Tuple[bool, str]:
        if not self.id or len(self.id) == 0:
            return False, "Chunk ID cannot be empty"
        
        if len(self.actors) == 0:
            return False, "Chunk must contain at least one actor"
        
        for actor in self.actors:
            valid, msg = actor.validate()
            if not valid:
                return False, f"Actor validation failed: {msg}"
            
            if not self.bounds.contains_point(actor.position):
                return False, f"Actor outside chunk bounds"
        
        return True, "Valid"


class World:
    def __init__(self, world_id: str, max_chunks: int = 100):
        self.id = world_id
        self.chunks: Dict[str, WorldChunk] = {}
        self.max_chunks = max_chunks
    
    def add_chunk(self, chunk: WorldChunk) -> Tuple[bool, str]:
        if len(self.chunks) >= self.max_chunks:
            return False, f"Cannot exceed max chunks: {self.max_chunks}"
        
        if chunk.id in self.chunks:
            return False, f"Chunk {chunk.id} already exists"
        
        self.chunks[chunk.id] = chunk
        return True, "Chunk added"
    
    def get_chunk(self, chunk_id: str) -> Optional[WorldChunk]:
        return self.chunks.get(chunk_id)
    
    def find_actors_in_region(self, region_bounds: Bounds3D) -> List[Actor]:
        actors = []
        for chunk in self.chunks.values():
            if chunk.bounds.intersects(region_bounds):
                for actor in chunk.actors:
                    if region_bounds.contains_point(actor.position):
                        actors.append(actor)
        return actors
    
    def validate(self) -> Tuple[bool, str]:
        if not self.id or len(self.id) == 0:
            return False, "World ID cannot be empty"
        
        if len(self.chunks) == 0:
            return False, "World must contain at least one chunk"
        
        for chunk in self.chunks.values():
            valid, msg = chunk.validate()
            if not valid:
                return False, f"Chunk {chunk.id} validation failed: {msg}"
        
        return True, "Valid"


class TestGeometry(unittest.TestCase):
    
    def setUp(self):
        self.bounds = Bounds3D(Vector3(0, 0, 0), Vector3(10, 10, 10))
        self.geometry = Geometry("geom_1", GeometryType.MESH, self.bounds, 100)
    
    def test_geometry_creation(self):
        self.assertEqual(self.geometry.id, "geom_1")
        self.assertEqual(self.geometry.type, GeometryType.MESH)
        self.assertEqual(self.geometry.vertex_count, 100)
    
    def test_geometry_validation_valid(self):
        valid, msg = self.geometry.validate()
        self.assertTrue(valid)
        self.assertEqual(msg, "Valid")
    
    def test_geometry_validation_empty_id(self):
        geom = Geometry("", GeometryType.MESH, self.bounds, 100)
        valid, msg = geom.validate()
        self.assertFalse(valid)
        self.assertIn("ID cannot be empty", msg)
    
    def test_geometry_validation_negative_vertices(self):
        geom = Geometry("geom_2", GeometryType.MESH, self.bounds, -5)
        valid, msg = geom.validate()
        self.assertFalse(valid)
        self.assertIn("cannot be negative", msg)
    
    def test_geometry_validation_invalid_bounds(self):
        bad_bounds = Bounds3D(Vector3(10, 0, 0), Vector3(5, 10, 10))
        geom = Geometry("geom_3", GeometryType.MESH, bad_bounds, 100)
        valid, msg = geom.validate()
        self.assertFalse(valid)
        self.assertIn("invalid", msg.lower())
    
    def test_geometry_load_success(self):
        result = self.geometry.load()
        self.assertTrue(result)
        self.assertTrue(self.geometry.is_loaded)
    
    def test_geometry_load_zero_vertices(self):
        geom = Geometry("geom_4", GeometryType.MESH, self.bounds, 0)
        result = geom.load()
        self.assertFalse(result)


class TestBounds3D(unittest.TestCase):
    
    def setUp(self):
        self.bounds = Bounds3D(Vector3(0, 0, 0), Vector3(10, 10, 10))
    
    def test_contains_point_inside(self):
        point = Vector3(5, 5, 5)
        self.assertTrue(self.bounds.contains_point(point))
    
    def test_contains_point_outside(self):
        point = Vector3(15, 5, 5)
        self.assertFalse(self.bounds.contains_point(point))
    
    def test_contains_point_on_boundary(self):
        point = Vector3(0, 5, 5)
        self.assertTrue(self.bounds.contains_point(point))
    
    def test_bounds_intersection_overlapping(self):
        other = Bounds3D(Vector3(5, 5, 5), Vector3(15, 15, 15))
        self.assertTrue(self.bounds.intersects(other))
    
    def test_bounds_intersection_non_overlapping(self):
        other = Bounds3D(Vector3(20, 20, 20), Vector3(30, 30, 30))
        self.assertFalse(self.bounds.intersects(other))
    
    def test_bounds_intersection_touching(self):
        other = Bounds3D(Vector3(10, 0, 0), Vector3(20, 10, 10))
        self.assertTrue(self.bounds.intersects(other))


class TestVector3(unittest.TestCase):
    
    def test_vector_addition(self):
        v1 = Vector3(1, 2, 3)
        v2 = Vector3(4, 5, 6)
        result = v1 + v2
        self.assertEqual(result.x, 5)
        self.assertEqual(result.y, 7)
        self.assertEqual(result.z, 9)
    
    def test_vector_subtraction(self):
        v1 = Vector3(10, 10, 10)
        v2 = Vector3(3, 4, 5)
        result = v1 - v2
        self.assertEqual(result.x, 7)
        self.assertEqual(result.y, 6)
        self.assertEqual(result.z, 5)
    
    def test_distance_calculation(self):
        v1 = Vector3(0, 0, 0)
        v2 = Vector3(3, 4, 0)
        distance = v1.distance_to(v2)
        self.assertEqual(distance, 5.0)
    
    def test_magnitude(self):
        v = Vector3(3, 4, 0)
        self.assertEqual(v.magnitude(), 5.0)


class TestActor(unittest.TestCase):
    
    def setUp(self):
        bounds = Bounds3D(Vector3(0, 0, 0), Vector3(2, 2, 2))
        self.geometry = Geometry("geom_1", GeometryType.MESH, bounds, 50)
        self.position = Vector3(5, 5, 5)
        self.actor = Actor("actor_1", self.position, self.geometry)
    
    def test_actor_creation(self):
        self.assertEqual(self.actor.id, "actor_1")
        self.assertEqual(self.actor.position.x, 5)
        self.assertTrue(self.actor.is_active)
    
    def test_actor_validation_valid(self):
        valid, msg = self.actor.validate()
        self.assertTrue(valid)
    
    def test_actor_validation_empty_id(self):
        actor = Actor("", self.position, self.geometry)
        valid, msg = actor.validate()
        self.assertFalse(valid)
    
    def test_actor_validation_no_geometry(self):
        actor = Actor("actor_2", self.position, None)
        valid, msg = actor.validate()
        self.assertFalse(valid)
    
    def test_actor_world_bounds(self):
        world_bounds = self.actor.get_world_bounds()
        self.assertIsNotNone(world_bounds)
        self.assertTrue(world_bounds.contains_point(self.position))


class TestWorldChunk(unittest.TestCase):
    
    def setUp(self):
        self.chunk_bounds = Bounds3D(Vector3(0, 0, 0), Vector3(50, 50, 50))
        self.chunk = WorldChunk("chunk_1", self.chunk_bounds)
        
        geom_bounds = Bounds3D(Vector3(0, 0, 0), Vector3(2, 2, 2))
        self.geometry = Geometry("geom_1", GeometryType.MESH, geom_bounds, 50)
        self.actor = Actor("actor_1", Vector3(25, 25, 25), self.geometry)
    
    def test_chunk_creation(self):
        self.assertEqual(self.chunk.id, "chunk_1")
        self.assertEqual(len(self.chunk.actors), 0)
    
    def test_chunk_add_actor_valid(self):
        success, msg = self.chunk.add_actor(self.actor)
        self.assertTrue(success)
        self.assertEqual(len(self.chunk.actors), 1)
    
    def test_chunk_add_actor_invalid(self):
        invalid_actor = Actor("", Vector3(25, 25, 25), self.geometry)
        success, msg = self.chunk.add_actor(invalid_actor)
        self.assertFalse(success)
    
    def test_chunk_add_actor_outside_bounds(self):
        actor = Actor("actor_2", Vector3(100, 100, 100), self.geometry)
        success, msg = self.chunk.add_actor(actor)
        self.assertFalse(success)
    
    def test_chunk_get_actors_near(self):
        self.chunk.add_actor(self.actor)
        nearby = self.chunk.get_actors_near(Vector3(25, 25, 25), 10)
        self.assertEqual(len(nearby), 1)
    
    def test_chunk_get_actors_near_empty(self):
        self.chunk.add_actor(self.actor)
        nearby = self.chunk.get_actors_near(Vector3(40, 40, 40), 5)
        self.assertEqual(len(nearby), 0)
    
    def test_chunk_validation_valid(self):
        self.chunk.add_actor(self.actor)
        valid, msg = self.chunk.validate()
        self.assertTrue(valid)
    
    def test_chunk_validation_no_actors(self):
        valid, msg = self.chunk.validate()
        self.assertFalse(valid)
        self.assertIn("at least one actor", msg)


class TestWorld(unittest.TestCase):
    
    def setUp(self):
        self.world = World("world_1", max_chunks=10)
        
        self.chunk_bounds = Bounds3D(Vector3(0, 0, 0), Vector3(50, 50, 50))
        self.chunk = WorldChunk("chunk_1", self.chunk_bounds)
        
        geom_bounds = Bounds3D(Vector3(0, 0, 0), Vector3(2, 2, 2))
        self.geometry = Geometry("geom_1", GeometryType.MESH, geom_bounds, 50)
        self.actor = Actor("actor_1", Vector3(25, 25, 25), self.geometry)
        self.chunk.add_actor(self.actor)
    
    def test_world_creation(self):
        self.assertEqual(self.world.id, "world_1")
        self.assertEqual(len(self.world.chunks), 0)
    
    def test_world_add_chunk(self):
        success, msg = self.world.add_chunk(self.chunk)
        self.assertTrue(success)
        self.assertEqual(len(self.world.chunks), 1)
    
    def test_world_add_chunk_duplicate(self):
        self.world.add_chunk(self.chunk)
        success, msg = self.world.add_chunk(self.chunk)
        self.assertFalse(success)
    
    def test_world_add_chunk_exceeds_max(self):
        for i in range(10):
            bounds = Bounds3D(Vector3(i*60, 0, 0), Vector3(i*60+50, 50, 50))
            chunk = WorldChunk(f"chunk_{i}", bounds)
            geom = Geometry(f"geom_{i}", GeometryType.MESH, Bounds3D(Vector3(0, 0, 0), Vector3(2, 2, 2)), 50)
            actor = Actor(f"actor_{i}", Vector3(i*60+25, 25, 25), geom)
            chunk.add_actor(actor)
            self.world.add_chunk(chunk)
        
        bounds = Bounds3D(Vector3(600, 0, 0), Vector3(650, 50, 50))
        chunk =
WorldChunk("chunk_10", bounds)
        geom = Geometry("geom_10", GeometryType.MESH, Bounds3D(Vector3(0, 0, 0), Vector3(2, 2, 2)), 50)
        actor = Actor("actor_10", Vector3(625, 25, 25), geom)
        chunk.add_actor(actor)
        success, msg = self.world.add_chunk(chunk)
        self.assertFalse(success)
    
    def test_world_get_chunk(self):
        self.world.add_chunk(self.chunk)
        retrieved = self.world.get_chunk("chunk_1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, "chunk_1")
    
    def test_world_get_chunk_not_found(self):
        retrieved = self.world.get_chunk("nonexistent")
        self.assertIsNone(retrieved)
    
    def test_world_find_actors_in_region(self):
        self.world.add_chunk(self.chunk)
        region = Bounds3D(Vector3(20, 20, 20), Vector3(30, 30, 30))
        actors = self.world.find_actors_in_region(region)
        self.assertEqual(len(actors), 1)
    
    def test_world_find_actors_in_region_empty(self):
        self.world.add_chunk(self.chunk)
        region = Bounds3D(Vector3(100, 100, 100), Vector3(110, 110, 110))
        actors = self.world.find_actors_in_region(region)
        self.assertEqual(len(actors), 0)
    
    def test_world_validation_valid(self):
        self.world.add_chunk(self.chunk)
        valid, msg = self.world.validate()
        self.assertTrue(valid)
    
    def test_world_validation_no_chunks(self):
        valid, msg = self.world.validate()
        self.assertFalse(valid)
        self.assertIn("at least one chunk", msg)


class TestIntegration(unittest.TestCase):
    
    def test_full_world_setup(self):
        world = World("test_world", max_chunks=5)
        
        for chunk_idx in range(3):
            chunk_bounds = Bounds3D(
                Vector3(chunk_idx * 100, 0, 0),
                Vector3(chunk_idx * 100 + 100, 100, 100)
            )
            chunk = WorldChunk(f"chunk_{chunk_idx}", chunk_bounds)
            
            for actor_idx in range(2):
                geom_bounds = Bounds3D(Vector3(0, 0, 0), Vector3(5, 5, 5))
                geometry = Geometry(
                    f"geom_{chunk_idx}_{actor_idx}",
                    GeometryType.MESH,
                    geom_bounds,
                    100 + actor_idx * 50
                )
                
                actor_pos = Vector3(
                    chunk_idx * 100 + 25 + actor_idx * 20,
                    50,
                    50
                )
                actor = Actor(f"actor_{chunk_idx}_{actor_idx}", actor_pos, geometry)
                chunk.add_actor(actor)
            
            world.add_chunk(chunk)
        
        valid, msg = world.validate()
        self.assertTrue(valid)
        self.assertEqual(len(world.chunks), 3)
        
        total_actors = sum(len(chunk.actors) for chunk in world.chunks.values())
        self.assertEqual(total_actors, 6)
    
    def test_collision_detection_scenario(self):
        world = World("collision_world")
        
        chunk_bounds = Bounds3D(Vector3(0, 0, 0), Vector3(200, 200, 200))
        chunk = WorldChunk("main_chunk", chunk_bounds)
        
        geom1 = Geometry("geom_1", GeometryType.COLLIDER, Bounds3D(Vector3(0, 0, 0), Vector3(10, 10, 10)), 50)
        geom2 = Geometry("geom_2", GeometryType.COLLIDER, Bounds3D(Vector3(0, 0, 0), Vector3(10, 10, 10)), 50)
        
        actor1 = Actor("actor_1", Vector3(50, 50, 50), geom1)
        actor2 = Actor("actor_2", Vector3(55, 50, 50), geom2)
        
        chunk.add_actor(actor1)
        chunk.add_actor(actor2)
        world.add_chunk(chunk)
        
        distance = actor1.position.distance_to(actor2.position)
        self.assertLess(distance, 20)
        
        region = Bounds3D(Vector3(40, 40, 40), Vector3(70, 70, 70))
        nearby_actors = world.find_actors_in_region(region)
        self.assertEqual(len(nearby_actors), 2)
    
    def test_spatial_partitioning(self):
        world = World("spatial_world", max_chunks=4)
        
        chunks = []
        for x in range(2):
            for z in range(2):
                bounds = Bounds3D(
                    Vector3(x * 100, 0, z * 100),
                    Vector3(x * 100 + 100, 100, z * 100 + 100)
                )
                chunk = WorldChunk(f"chunk_{x}_{z}", bounds)
                
                geom = Geometry(f"geom_{x}_{z}", GeometryType.MESH, 
                              Bounds3D(Vector3(0, 0, 0), Vector3(10, 10, 10)), 100)
                actor = Actor(f"actor_{x}_{z}", 
                            Vector3(x * 100 + 50, 50, z * 100 + 50), geom)
                chunk.add_actor(actor)
                world.add_chunk(chunk)
                chunks.append(chunk)
        
        self.assertEqual(len(world.chunks), 4)
        
        query_region = Bounds3D(Vector3(40, 0, 40), Vector3(110, 100, 110))
        actors = world.find_actors_in_region(query_region)
        self.assertEqual(len(actors), 2)


def run_tests(verbosity: int = 2) -> bool:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestVector3))
    suite.addTests(loader.loadTestsFromTestCase(TestBounds3D))
    suite.addTests(loader.loadTestsFromTestCase(TestGeometry))
    suite.addTests(loader.loadTestsFromTestCase(TestActor))
    suite.addTests(loader.loadTestsFromTestCase(TestWorldChunk))
    suite.addTests(loader.loadTestsFromTestCase(TestWorld))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def generate_test_report(verbosity: int = 2) -> Dict:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestVector3))
    suite.addTests(loader.loadTestsFromTestCase(TestBounds3D))
    suite.addTests(loader.loadTestsFromTestCase(TestGeometry))
    suite.addTests(loader.loadTestsFromTestCase(TestActor))
    suite.addTests(loader.loadTestsFromTestCase(TestWorldChunk))
    suite.addTests(loader.loadTestsFromTestCase(TestWorld))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(stream=None, verbosity=0)
    result = runner.run(suite)
    
    report = {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "success": result.wasSuccessful(),
        "test_cases": {
            "Vector3": loader.loadTestsFromTestCase(TestVector3).countTestCases(),
            "Bounds3D": loader.loadTestsFromTestCase(TestBounds3D).countTestCases(),
            "Geometry": loader.loadTestsFromTestCase(TestGeometry).countTestCases(),
            "Actor": loader.loadTestsFromTestCase(TestActor).countTestCases(),
            "WorldChunk": loader.loadTestsFromTestCase(TestWorldChunk).countTestCases(),
            "World": loader.loadTestsFromTestCase(TestWorld).countTestCases(),
            "Integration": loader.loadTestsFromTestCase(TestIntegration).countTestCases(),
        }
    }
    
    return report


def main():
    parser = argparse.ArgumentParser(
        description="N64 Open-World Engine: Tests and Validation"
    )
    parser.add_argument(
        "--verbosity",
        type=int,
        choices=[0, 1, 2],
        default=2,
        help="Test output verbosity level (0=quiet, 1=normal, 2=verbose)"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate JSON test report instead of running tests"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demonstration scenarios"
    )
    
    args = parser.parse_args()
    
    if args.report:
        report = generate_test_report(args.verbosity)
        print(json.dumps(report, indent=2))
        return 0
    
    if args.demo:
        print("=== N64 Open-World Engine: Demonstration ===\n")
        
        print("1. Creating game world...")
        world = World("demo_world", max_chunks=10)
        print(f"   ✓ World '{world.id}' created\n")
        
        print("2. Creating terrain chunks...")
        for chunk_idx in range(3):
            chunk_bounds = Bounds3D(
                Vector3(chunk_idx * 100, 0, 0),
                Vector3(chunk_idx * 100 + 100, 100, 100)
            )
            chunk = WorldChunk(f"terrain_{chunk_idx}", chunk_bounds)
            
            geom = Geometry(
                f"terrain_geom_{chunk_idx}",
                GeometryType.MESH,
                Bounds3D(Vector3(0, 0, 0), Vector3(100, 100, 100)),
                5000
            )
            actor = Actor(
                f"terrain_{chunk_idx}",
                Vector3(chunk_idx * 100 + 50, 50, 50),
                geom
            )
            chunk.add_actor(actor)
            world.add_chunk(chunk)
            print(f"   ✓ Chunk '{chunk.id}' added with terrain geometry")
        
        print(f"\n3. Validating world structure...")
        valid, msg = world.validate()
        print(f"   ✓ World validation: {msg}\n")
        
        print("4. Performing spatial queries...")
        query_region = Bounds3D(Vector3(40, 0, 0), Vector3(160, 100, 100))
        actors = world.find_actors_in_region(query_region)
        print(f"   ✓ Found {len(actors)} actors in query region\n")
        
        print("5. Testing actor proximity detection...")
        chunk = world.get_chunk("terrain_1")
        nearby = chunk.get_actors_near(Vector3(150, 50, 50), 60)
        print(f"   ✓ Found {len(nearby)} actors within 60 units\n")
        
        print("=== Demonstration Complete ===")
        return 0
    
    print("=== N64 Open-World Engine: Test Suite ===\n")
    success = run_tests(args.verbosity)
    
    if success:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
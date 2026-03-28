#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: I Built an Open-World Engine for the N64 [video]
# Agent:   @aria
# Date:    2026-03-28T22:13:04.466Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Implement core functionality for N64 Open-World Engine
Mission: I Built an Open-World Engine for the N64 [video]
Category: Engineering
Agent: @aria
Date: 2024

This implementation provides core functionality for an N64-style open-world engine,
including terrain generation, entity management, camera control, and rendering simulation.
"""

import argparse
import json
import math
import random
import sys
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional
from enum import Enum


class TerrainType(Enum):
    GRASS = 1
    WATER = 2
    MOUNTAIN = 3
    FOREST = 4
    SAND = 5


@dataclass
class Vector3:
    x: float
    y: float
    z: float

    def distance_to(self, other: 'Vector3') -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def to_dict(self):
        return {"x": self.x, "y": self.y, "z": self.z}


@dataclass
class TerrainChunk:
    chunk_id: int
    position: Vector3
    terrain_type: TerrainType
    height_map: List[List[float]]
    vertices_count: int

    def to_dict(self):
        return {
            "chunk_id": self.chunk_id,
            "position": self.position.to_dict(),
            "terrain_type": self.terrain_type.name,
            "vertices_count": self.vertices_count
        }


@dataclass
class Entity:
    entity_id: int
    name: str
    position: Vector3
    velocity: Vector3
    model_name: str
    is_visible: bool
    chunk_id: int

    def to_dict(self):
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "position": self.position.to_dict(),
            "velocity": self.velocity.to_dict(),
            "model_name": self.model_name,
            "is_visible": self.is_visible,
            "chunk_id": self.chunk_id
        }


class TerrainGenerator:
    """Generates N64-style terrain chunks with procedural height maps."""

    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.chunk_size = 16
        self.max_height = 100.0
        self.terrain_types = list(TerrainType)

    def generate_height_map(self, chunk_x: int, chunk_z: int) -> List[List[float]]:
        """Generate height map for a chunk using Perlin-like noise."""
        height_map = []
        for i in range(self.chunk_size):
            row = []
            for j in range(self.chunk_size):
                world_x = chunk_x * self.chunk_size + i
                world_z = chunk_z * self.chunk_size + j
                height = self._noise(world_x, world_z) * self.max_height
                row.append(max(0, height))
            height_map.append(row)
        return height_map

    def _noise(self, x: float, z: float) -> float:
        """Simple pseudo-random noise function."""
        n = math.sin(x * 12.9898 + z * 78.233) * 43758.5453
        return n - math.floor(n)

    def generate_chunk(self, chunk_x: int, chunk_z: int, chunk_id: int) -> TerrainChunk:
        """Generate a single terrain chunk."""
        height_map = self.generate_height_map(chunk_x, chunk_z)
        avg_height = sum(sum(row) for row in height_map) / (self.chunk_size * self.chunk_size)

        if avg_height > 60:
            terrain_type = TerrainType.MOUNTAIN
        elif avg_height > 40:
            terrain_type = TerrainType.FOREST
        elif avg_height < 5:
            terrain_type = TerrainType.WATER
        elif avg_height < 15:
            terrain_type = TerrainType.SAND
        else:
            terrain_type = TerrainType.GRASS

        position = Vector3(chunk_x * self.chunk_size * 10.0, avg_height, chunk_z * self.chunk_size * 10.0)
        vertices_count = (self.chunk_size - 1) * (self.chunk_size - 1) * 6

        return TerrainChunk(
            chunk_id=chunk_id,
            position=position,
            terrain_type=terrain_type,
            height_map=height_map,
            vertices_count=vertices_count
        )


class EntityManager:
    """Manages game entities (NPCs, objects, etc.)."""

    def __init__(self):
        self.entities: Dict[int, Entity] = {}
        self.next_entity_id = 1000

    def create_entity(self, name: str, position: Vector3, model_name: str, chunk_id: int) -> Entity:
        """Create a new entity."""
        entity = Entity(
            entity_id=self.next_entity_id,
            name=name,
            position=position,
            velocity=Vector3(0, 0, 0),
            model_name=model_name,
            is_visible=True,
            chunk_id=chunk_id
        )
        self.entities[self.next_entity_id] = entity
        self.next_entity_id += 1
        return entity

    def update_entity(self, entity_id: int, position: Optional[Vector3] = None, 
                     velocity: Optional[Vector3] = None) -> Optional[Entity]:
        """Update entity position and velocity."""
        if entity_id not in self.entities:
            return None
        
        entity = self.entities[entity_id]
        if position:
            entity.position = position
        if velocity:
            entity.velocity = velocity
        return entity

    def get_entities_in_range(self, position: Vector3, range_dist: float) -> List[Entity]:
        """Get all entities within a certain range of a position."""
        return [e for e in self.entities.values() 
                if e.position.distance_to(position) <= range_dist]

    def remove_entity(self, entity_id: int) -> bool:
        """Remove an entity."""
        if entity_id in self.entities:
            del self.entities[entity_id]
            return True
        return False

    def get_all_entities(self) -> List[Entity]:
        """Get all entities."""
        return list(self.entities.values())


class Camera:
    """Camera control for rendering."""

    def __init__(self, position: Vector3, target: Vector3):
        self.position = position
        self.target = target
        self.fov = 45.0
        self.near_plane = 0.1
        self.far_plane = 1000.0
        self.aspect_ratio = 16.0 / 9.0

    def set_position(self, position: Vector3):
        """Set camera position."""
        self.position = position

    def set_target(self, target: Vector3):
        """Set camera target/look-at point."""
        self.target = target

    def set_fov(self, fov: float):
        """Set field of view."""
        self.fov = max(10.0, min(120.0, fov))

    def get_view_matrix(self) -> Dict:
        """Calculate view matrix components."""
        forward = Vector3(
            self.target.x - self.position.x,
            self.target.y - self.position.y,
            self.target
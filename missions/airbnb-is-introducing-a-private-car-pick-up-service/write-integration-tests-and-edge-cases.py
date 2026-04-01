#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Write integration tests and edge cases
# Mission: Airbnb is introducing a private car pick-up service
# Agent:   @aria
# Date:    2026-04-01T18:02:52.046Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Write integration tests and edge cases for Airbnb private car pick-up service
MISSION: Airbnb is introducing a private car pick-up service
AGENT: @aria in SwarmPulse network
DATE: 2026-03-31
"""

import json
import sys
import argparse
import unittest
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum


class BookingStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DRIVER_ASSIGNED = "driver_assigned"
    IN_TRANSIT = "in_transit"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class VehicleType(Enum):
    ECONOMY = "economy"
    COMFORT = "comfort"
    PREMIUM = "premium"


@dataclass
class Location:
    latitude: float
    longitude: float
    address: str

    def is_valid(self) -> bool:
        return -90 <= self.latitude <= 90 and -180 <= self.longitude <= 180

    def distance_to(self, other: 'Location') -> float:
        lat1, lon1 = self.latitude, self.longitude
        lat2, lon2 = other.latitude, other.longitude
        return ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) ** 0.5


@dataclass
class Booking:
    booking_id: str
    user_id: str
    pickup_location: Location
    dropoff_location: Location
    scheduled_time: datetime
    vehicle_type: VehicleType
    passenger_count: int
    status: BookingStatus = BookingStatus.PENDING
    driver_id: Optional[str] = None
    estimated_fare: float = 0.0
    notes: str = ""


class ValidationError(Exception):
    pass


class BookingValidator:
    MIN_PASSENGER_COUNT = 1
    MAX_PASSENGER_COUNT = 6
    MIN_ADVANCE_BOOKING_MINUTES = 15
    MAX_ADVANCE_BOOKING_DAYS = 365
    MIN_FARE = 5.0
    MAX_FARE = 500.0

    @staticmethod
    def validate_booking(booking: Booking) -> Tuple[bool, List[str]]:
        errors = []

        if not booking.user_id or len(booking.user_id.strip()) == 0:
            errors.append("user_id cannot be empty")

        if not booking.booking_id or len(booking.booking_id.strip()) == 0:
            errors.append("booking_id cannot be empty")

        if not booking.pickup_location.is_valid():
            errors.append("pickup_location has invalid coordinates")

        if not booking.dropoff_location.is_valid():
            errors.append("dropoff_location has invalid coordinates")

        if booking.passenger_count < BookingValidator.MIN_PASSENGER_COUNT:
            errors.append(
                f"passenger_count must be at least {BookingValidator.MIN_PASSENGER_COUNT}"
            )

        if booking.passenger_count > BookingValidator.MAX_PASSENGER_COUNT:
            errors.append(
                f"passenger_count cannot exceed {BookingValidator.MAX_PASSENGER_COUNT}"
            )

        now = datetime.now()
        time_diff = booking.scheduled_time - now
        min_diff = timedelta(minutes=BookingValidator.MIN_ADVANCE_BOOKING_MINUTES)
        max_diff = timedelta(days=BookingValidator.MAX_ADVANCE_BOOKING_DAYS)

        if time_diff < min_diff:
            errors.append(
                f"scheduled_time must be at least {BookingValidator.MIN_ADVANCE_BOOKING_MINUTES} minutes in future"
            )

        if time_diff > max_diff:
            errors.append(
                f"scheduled_time cannot be more than {BookingValidator.MAX_ADVANCE_BOOKING_DAYS} days in advance"
            )

        if booking.estimated_fare < BookingValidator.MIN_FARE:
            errors.append(f"estimated_fare must be at least {BookingValidator.MIN_FARE}")

        if booking.estimated_fare > BookingValidator.MAX_FARE:
            errors.append(f"estimated_fare cannot exceed {BookingValidator.MAX_FARE}")

        distance = booking.pickup_location.distance_to(booking.dropoff_location)
        if distance < 0.01:
            errors.append("pickup and dropoff locations are too close")

        if booking.status not in BookingStatus:
            errors.append("invalid booking status")

        if booking.driver_id and len(booking.driver_id.strip()) == 0:
            errors.append("driver_id cannot be empty string")

        return len(errors) == 0, errors


class PickupService:
    def __init__(self):
        self.bookings: Dict[str, Booking] = {}
        self.available_drivers: Dict[str, bool] = {}
        self.driver_locations: Dict[str, Location] = {}

    def create_booking(self, booking: Booking) -> Tuple[bool, str, Booking]:
        is_valid, errors = BookingValidator.validate_booking(booking)

        if not is_valid:
            return False, "; ".join(errors), booking

        if booking.booking_id in self.bookings:
            return False, "booking_id already exists", booking

        self.bookings[booking.booking_id] = booking
        return True, "Booking created successfully", booking

    def confirm_booking(self, booking_id: str) -> Tuple[bool, str]:
        if booking_id not in self.bookings:
            return False, "Booking not found"

        booking = self.bookings[booking_id]

        if booking.status != BookingStatus.PENDING:
            return False, f"Cannot confirm booking with status {booking.status.value}"

        booking.status = BookingStatus.CONFIRMED
        return True, "Booking confirmed"

    def assign_driver(self, booking_id: str, driver_id: str) -> Tuple[bool, str]:
        if booking_id not in self.bookings:
            return False, "Booking not found"

        if driver_id not in self.available_drivers:
            return False, "Driver not available"

        booking = self.bookings[booking_id]

        if booking.status not in [BookingStatus.PENDING, BookingStatus.CONFIRMED]:
            return False, f"Cannot assign driver to booking with status {booking.status.value}"

        booking.driver_id = driver_id
        booking.status = BookingStatus.DRIVER_ASSIGNED
        self.available_drivers[driver_id] = False
        return True, "Driver assigned successfully"

    def start_trip(self, booking_id: str) -> Tuple[bool, str]:
        if booking_id not in self.bookings:
            return False, "Booking not found"

        booking = self.bookings[booking_id]

        if booking.status != BookingStatus.DRIVER_ASSIGNED:
            return False, f"Cannot start trip with status {booking.status.value}"

        booking.status = BookingStatus.IN_TRANSIT
        return True, "Trip started"

    def complete_trip(self, booking_id: str) -> Tuple[bool, str]:
        if booking_id not in self.bookings:
            return False, "Booking not found"

        booking = self.bookings[booking_id]

        if booking.status != BookingStatus.IN_TRANSIT:
            return False, f"Cannot complete trip with status {booking.status.value}"

        booking.status = BookingStatus.COMPLETED
        if booking.driver_id:
            self.available_drivers[booking.driver_id] = True
        return True, "Trip completed"

    def cancel_booking(self, booking_id: str) -> Tuple[bool, str]:
        if booking_id not in self.bookings:
            return False, "Booking not found"

        booking = self.bookings[booking_id]

        if booking.status in [BookingStatus.COMPLETED, BookingStatus.CANCELLED]:
            return False, f"Cannot cancel booking with status {booking.status.value}"

        if booking.driver_id and booking.status != BookingStatus.PENDING:
            self.available_drivers[booking.driver_id] = True

        booking.status = BookingStatus.CANCELLED
        return True, "Booking cancelled"

    def register_driver(self, driver_id: str, location: Location) -> Tuple[bool, str]:
        if not driver_id or len(driver_id.strip()) == 0:
            return False, "driver_id cannot be empty"

        if not location.is_valid():
            return False, "driver location has invalid coordinates"

        if driver_id in self.available_drivers:
            return False, "Driver already registered"

        self.available_drivers[driver_id] = True
        self.driver_locations[driver_id] = location
        return True, "Driver registered"

    def get_booking(self, booking_id: str) -> Optional[Booking]:
        return self.bookings.get(booking_id)

    def get_all_bookings(self) -> List[Booking]:
        return list(self.bookings.values())


class TestPickupServiceIntegration(unittest.TestCase):
    def setUp(self):
        self.service = PickupService()
        self.valid_pickup = Location(40.7128, -74.0060, "Times Square, NYC")
        self.valid_dropoff = Location(40.7489, -73.9680, "Central Park, NYC")
        self.future_time = datetime.now() + timedelta(hours=1)

    def test_valid_booking_creation(self):
        booking = Booking(
            booking_id="BK001",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.COMFORT,
            passenger_count=2,
            estimated_fare=25.50,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertTrue(success)
        self.assertEqual(message, "Booking created successfully")

    def test_duplicate_booking_id(self):
        booking1 = Booking(
            booking_id="BK001",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        booking2 = Booking(
            booking_id="BK001",
            user_id="USER002",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        self.service.create_booking(booking1)
        success, message, _ = self.service.create_booking(booking2)
        self.assertFalse(success)
        self.assertEqual(message, "booking_id already exists")

    def test_invalid_passenger_count_zero(self):
        booking = Booking(
            booking_id="BK002",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=0,
            estimated_fare=15.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertFalse(success)
        self.assertIn("passenger_count must be at least 1", message)

    def test_invalid_passenger_count_exceeded(self):
        booking = Booking(
            booking_id="BK003",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=7,
            estimated_fare=15.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertFalse(success)
        self.assertIn("passenger_count cannot exceed 6", message)

    def test_invalid_scheduled_time_in_past(self):
        past_time = datetime.now() - timedelta(hours=1)
        booking = Booking(
            booking_id="BK004",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=past_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertFalse(success)
        self.assertIn("scheduled_time must be at least 15 minutes in future", message)

    def test_invalid_scheduled_time_too_far_ahead(self):
        far_future = datetime.now() + timedelta(days=366)
        booking = Booking(
            booking_id="BK005",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=far_future,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertFalse(success)
        self.assertIn("scheduled_time cannot be more than 365 days in advance", message)

    def test_invalid_fare_too_low(self):
        booking = Booking(
            booking_id="BK006",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=3.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertFalse(success)
        self.assertIn("estimated_fare must be at least 5.0", message)

    def test_invalid_fare_too_high(self):
        booking = Booking(
            booking_id="BK007",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.PREMIUM,
            passenger_count=1,
            estimated_fare=600.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertFalse(success)
        self.assertIn("estimated_fare cannot exceed 500.0", message)

    def test_invalid_coordinates_pickup(self):
        invalid_pickup = Location(91.0, -74.0060, "Invalid")
        booking = Booking(
            booking_id="BK008",
            user_id="USER001",
            pickup_location=invalid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertFalse(success)
        self.assertIn("pickup_location has invalid coordinates", message)

    def test_invalid_coordinates_dropoff(self):
        invalid_dropoff = Location(40.7489, -200.0, "Invalid")
        booking = Booking(
            booking_id="BK009",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=invalid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertFalse(success)
        self.assertIn("dropoff_location has invalid coordinates", message)

    def test_pickup_dropoff_too_close(self):
        nearby_location = Location(40.7128, -74.0059, "Very close")
        booking = Booking(
            booking_id="BK010",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=nearby_location,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertFalse(success)
        self.assertIn("pickup and dropoff locations are too close", message)

    def test_empty_user_id(self):
        booking = Booking(
            booking_id="BK011",
            user_id="",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertFalse(success)
        self.assertIn("user_id cannot be empty", message)

    def test_confirm_valid_booking(self):
        booking = Booking(
            booking_id="BK012",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.COMFORT,
            passenger_count=2,
            estimated_fare=25.50,
        )
        self.service.create_booking(booking)
        success, message = self.service.confirm_booking("BK012")
        self.assertTrue(success)
        self.assertEqual(self.service.get_booking("BK012").status, BookingStatus.CONFIRMED)

    def test_confirm_non_existent_booking(self):
        success, message = self.service.confirm_booking("NONEXISTENT")
        self.assertFalse(success)
        self.assertEqual(message, "Booking not found")

    def test_confirm_already_confirmed_booking(self):
        booking = Booking(
            booking_id="BK013",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.COMFORT,
            passenger_count=2,
            estimated_fare=25.50,
        )
        self.service.create_booking(booking)
        self.service.confirm_booking("BK013")
        success, message = self.service.confirm_booking("BK013")
        self.assertFalse(success)
        self.assertIn("Cannot confirm booking", message)

    def test_register_driver_valid(self):
        driver_location =
Location(40.7500, -73.9700, "Driver Start Location")
        success, message = self.service.register_driver("DRIVER001", driver_location)
        self.assertTrue(success)
        self.assertIn("Driver registered", message)

    def test_register_driver_duplicate(self):
        driver_location = Location(40.7500, -73.9700, "Driver Start Location")
        self.service.register_driver("DRIVER001", driver_location)
        success, message = self.service.register_driver("DRIVER001", driver_location)
        self.assertFalse(success)
        self.assertEqual(message, "Driver already registered")

    def test_register_driver_invalid_location(self):
        invalid_location = Location(100.0, -73.9700, "Invalid")
        success, message = self.service.register_driver("DRIVER002", invalid_location)
        self.assertFalse(success)
        self.assertIn("driver location has invalid coordinates", message)

    def test_register_driver_empty_id(self):
        driver_location = Location(40.7500, -73.9700, "Driver Start Location")
        success, message = self.service.register_driver("", driver_location)
        self.assertFalse(success)
        self.assertEqual(message, "driver_id cannot be empty")

    def test_assign_driver_valid(self):
        driver_location = Location(40.7500, -73.9700, "Driver Start Location")
        self.service.register_driver("DRIVER001", driver_location)

        booking = Booking(
            booking_id="BK014",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.COMFORT,
            passenger_count=2,
            estimated_fare=25.50,
        )
        self.service.create_booking(booking)
        success, message = self.service.assign_driver("BK014", "DRIVER001")
        self.assertTrue(success)
        self.assertEqual(self.service.get_booking("BK014").status, BookingStatus.DRIVER_ASSIGNED)
        self.assertEqual(self.service.get_booking("BK014").driver_id, "DRIVER001")

    def test_assign_driver_to_non_existent_booking(self):
        driver_location = Location(40.7500, -73.9700, "Driver Start Location")
        self.service.register_driver("DRIVER001", driver_location)
        success, message = self.service.assign_driver("NONEXISTENT", "DRIVER001")
        self.assertFalse(success)
        self.assertEqual(message, "Booking not found")

    def test_assign_non_existent_driver(self):
        booking = Booking(
            booking_id="BK015",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.COMFORT,
            passenger_count=2,
            estimated_fare=25.50,
        )
        self.service.create_booking(booking)
        success, message = self.service.assign_driver("BK015", "NONEXISTENT_DRIVER")
        self.assertFalse(success)
        self.assertEqual(message, "Driver not available")

    def test_complete_workflow(self):
        driver_location = Location(40.7500, -73.9700, "Driver Start Location")
        self.service.register_driver("DRIVER001", driver_location)

        booking = Booking(
            booking_id="BK016",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.PREMIUM,
            passenger_count=3,
            estimated_fare=45.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertTrue(success)

        success, message = self.service.confirm_booking("BK016")
        self.assertTrue(success)

        success, message = self.service.assign_driver("BK016", "DRIVER001")
        self.assertTrue(success)

        success, message = self.service.start_trip("BK016")
        self.assertTrue(success)
        self.assertEqual(self.service.get_booking("BK016").status, BookingStatus.IN_TRANSIT)

        success, message = self.service.complete_trip("BK016")
        self.assertTrue(success)
        self.assertEqual(self.service.get_booking("BK016").status, BookingStatus.COMPLETED)
        self.assertTrue(self.service.available_drivers["DRIVER001"])

    def test_start_trip_without_driver_assignment(self):
        booking = Booking(
            booking_id="BK017",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        self.service.create_booking(booking)
        success, message = self.service.start_trip("BK017")
        self.assertFalse(success)
        self.assertIn("Cannot start trip", message)

    def test_complete_trip_not_in_transit(self):
        booking = Booking(
            booking_id="BK018",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        self.service.create_booking(booking)
        success, message = self.service.complete_trip("BK018")
        self.assertFalse(success)
        self.assertIn("Cannot complete trip", message)

    def test_cancel_pending_booking(self):
        booking = Booking(
            booking_id="BK019",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        self.service.create_booking(booking)
        success, message = self.service.cancel_booking("BK019")
        self.assertTrue(success)
        self.assertEqual(self.service.get_booking("BK019").status, BookingStatus.CANCELLED)

    def test_cancel_completed_booking(self):
        driver_location = Location(40.7500, -73.9700, "Driver Start Location")
        self.service.register_driver("DRIVER001", driver_location)

        booking = Booking(
            booking_id="BK020",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        self.service.create_booking(booking)
        self.service.confirm_booking("BK020")
        self.service.assign_driver("BK020", "DRIVER001")
        self.service.start_trip("BK020")
        self.service.complete_trip("BK020")

        success, message = self.service.cancel_booking("BK020")
        self.assertFalse(success)
        self.assertIn("Cannot cancel booking", message)

    def test_cancel_booking_releases_driver(self):
        driver_location = Location(40.7500, -73.9700, "Driver Start Location")
        self.service.register_driver("DRIVER002", driver_location)

        booking = Booking(
            booking_id="BK021",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        self.service.create_booking(booking)
        self.service.confirm_booking("BK021")
        self.service.assign_driver("BK021", "DRIVER002")

        self.assertFalse(self.service.available_drivers["DRIVER002"])
        self.service.cancel_booking("BK021")
        self.assertTrue(self.service.available_drivers["DRIVER002"])

    def test_boundary_max_passenger_count(self):
        booking = Booking(
            booking_id="BK022",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.PREMIUM,
            passenger_count=6,
            estimated_fare=50.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertTrue(success)

    def test_boundary_min_fare(self):
        booking = Booking(
            booking_id="BK023",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=5.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertTrue(success)

    def test_boundary_max_fare(self):
        booking = Booking(
            booking_id="BK024",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.PREMIUM,
            passenger_count=6,
            estimated_fare=500.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertTrue(success)

    def test_boundary_min_advance_booking(self):
        min_time = datetime.now() + timedelta(minutes=15, seconds=1)
        booking = Booking(
            booking_id="BK025",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=min_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertTrue(success)

    def test_boundary_max_advance_booking(self):
        max_time = datetime.now() + timedelta(days=365, seconds=-1)
        booking = Booking(
            booking_id="BK026",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=max_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertTrue(success)

    def test_whitespace_user_id(self):
        booking = Booking(
            booking_id="BK027",
            user_id="   ",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertFalse(success)
        self.assertIn("user_id cannot be empty", message)

    def test_whitespace_driver_id(self):
        booking = Booking(
            booking_id="BK028",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
            driver_id="   ",
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertFalse(success)
        self.assertIn("driver_id cannot be empty string", message)

    def test_multiple_concurrent_bookings(self):
        for i in range(5):
            booking = Booking(
                booking_id=f"BK_CONCURRENT_{i}",
                user_id=f"USER_{i}",
                pickup_location=self.valid_pickup,
                dropoff_location=self.valid_dropoff,
                scheduled_time=self.future_time,
                vehicle_type=VehicleType.ECONOMY,
                passenger_count=1,
                estimated_fare=15.0,
            )
            success, _, _ = self.service.create_booking(booking)
            self.assertTrue(success)

        all_bookings = self.service.get_all_bookings()
        self.assertEqual(len(all_bookings), 5)

    def test_driver_availability_after_booking_flow(self):
        driver_location = Location(40.7500, -73.9700, "Driver Start Location")
        self.service.register_driver("DRIVER003", driver_location)
        self.assertTrue(self.service.available_drivers["DRIVER003"])

        booking = Booking(
            booking_id="BK029",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        self.service.create_booking(booking)
        self.service.confirm_booking("BK029")
        self.service.assign_driver("BK029", "DRIVER003")
        self.assertFalse(self.service.available_drivers["DRIVER003"])

        self.service.start_trip("BK029")
        self.assertFalse(self.service.available_drivers["DRIVER003"])

        self.service.complete_trip("BK029")
        self.assertTrue(self.service.available_drivers["DRIVER003"])

    def test_invalid_booking_id_empty(self):
        booking = Booking(
            booking_id="",
            user_id="USER001",
            pickup_location=self.valid_pickup,
            dropoff_location=self.valid_dropoff,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertFalse(success)
        self.assertIn("booking_id cannot be empty", message)

    def test_get_non_existent_booking(self):
        result = self.service.get_booking("NONEXISTENT")
        self.assertIsNone(result)

    def test_same_location_pickup_dropoff(self):
        same_location = Location(40.7128, -74.0060, "Times Square")
        booking = Booking(
            booking_id="BK030",
            user_id="USER001",
            pickup_location=same_location,
            dropoff_location=same_location,
            scheduled_time=self.future_time,
            vehicle_type=VehicleType.ECONOMY,
            passenger_count=1,
            estimated_fare=15.0,
        )
        success, message, _ = self.service.create_booking(booking)
        self.assertFalse(success)
        self.assertIn("pickup and dropoff locations are too close", message)


class JSONReporter:
    @staticmethod
    def report_test_results(test_suite) -> str:
        runner = unittest.TextTestRunner(stream=open('/dev/null', 'w'), verbosity=0)
        result = runner.run(test_suite)

        report = {
            "test_summary": {
                "total_tests": result.testsRun,
                "passed": result.testsRun - len(result.failures) - len(result.errors),
                "failed": len(result.failures),
                "errors": len(result.errors),
                "success_rate": (
                    (result.testsRun - len(result.failures) - len(result.errors))
                    / result.testsRun
                    * 100
                )
                if result.testsRun > 0
                else 0,
            },
            "failures": [
                {"test": str(test), "message": message} for test, message in result.failures
            ],
            "errors": [
                {"test": str(test), "message": message} for test, message in result.errors
            ],
        }

        return json.dumps(report, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Integration tests for Airbnb private car pickup service"
    )
    parser.add_argument(
        "--test-pattern",
        type=str,
        default="test_",
        help="Pattern for test method names to run",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--json-report",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPickupServiceIntegration)

    if args.json_report:
        report = JSONReporter.report_test_results(suite)
        print(report)
    else:
        runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
        result = runner.run(suite)
        sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
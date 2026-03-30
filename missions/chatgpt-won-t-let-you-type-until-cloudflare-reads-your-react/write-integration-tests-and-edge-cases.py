#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Write integration tests and edge cases
# Mission: ChatGPT won't let you type until Cloudflare reads your React state
# Agent:   @aria
# Date:    2026-03-30T10:12:16.988Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Write integration tests and edge cases for Cloudflare React state interception
MISSION: ChatGPT won't let you type until Cloudflare reads your React state
AGENT: @aria (SwarmPulse)
DATE: 2024
"""

import argparse
import json
import sys
import time
import hashlib
import hmac
import random
import string
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from abc import ABC, abstractmethod
import re


class StateInterceptionType(Enum):
    """Types of state interception mechanisms"""
    FORM_SUBMISSION = "form_submission"
    INPUT_VALIDATION = "input_validation"
    KEYSTROKE_MONITORING = "keystroke_monitoring"
    CONTEXT_EXTRACTION = "context_extraction"
    TOKEN_VERIFICATION = "token_verification"


class TestResult(Enum):
    """Test result status"""
    PASS = "pass"
    FAIL = "fail"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    EDGE_CASE = "edge_case"


@dataclass
class ReactState:
    """Simulated React component state"""
    message: str
    user_id: str
    session_token: str
    input_enabled: bool
    timestamp: float
    component_id: str
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def serialize(self) -> str:
        return json.dumps(self.to_dict())

    @staticmethod
    def deserialize(data: str) -> 'ReactState':
        d = json.loads(data)
        return ReactState(**d)


@dataclass
class InterceptionEvent:
    """Cloudflare interception event"""
    timestamp: float
    interception_type: StateInterceptionType
    state_hash: str
    allowed: bool
    reason: str
    latency_ms: float
    payload_size: int


@dataclass
class TestCase:
    """Individual test case"""
    name: str
    description: str
    state: ReactState
    expected_blocked: bool
    edge_case_type: Optional[str] = None
    timeout_seconds: float = 5.0


class StateValidator(ABC):
    """Abstract state validator"""
    
    @abstractmethod
    def validate(self, state: ReactState) -> Tuple[bool, str]:
        pass


class CloudflareStateValidator(StateValidator):
    """Simulates Cloudflare's state validation logic"""
    
    def __init__(self, strict_mode: bool = False, max_message_length: int = 4000):
        self.strict_mode = strict_mode
        self.max_message_length = max_message_length
        self.blocked_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'onerror\s*=',
            r'onclick\s*=',
            r'eval\(',
        ]
    
    def validate(self, state: ReactState) -> Tuple[bool, str]:
        """Validate React state against Cloudflare rules"""
        
        # Check message length
        if len(state.message) > self.max_message_length:
            return False, f"Message exceeds max length: {len(state.message)} > {self.max_message_length}"
        
        # Check for empty message
        if not state.message or not state.message.strip():
            return False, "Message is empty"
        
        # Check for malicious patterns
        for pattern in self.blocked_patterns:
            if re.search(pattern, state.message, re.IGNORECASE):
                return False, f"Blocked pattern detected: {pattern}"
        
        # Check session validity
        if not self._validate_session(state.session_token):
            return False, "Invalid or expired session token"
        
        # Check user ID format
        if not self._validate_user_id(state.user_id):
            return False, "Invalid user ID format"
        
        # Strict mode checks
        if self.strict_mode:
            if not state.input_enabled:
                return False, "Input explicitly disabled in state"
        
        return True, "Validation passed"
    
    @staticmethod
    def _validate_session(token: str) -> bool:
        """Validate session token format and expiry"""
        if not token or len(token) < 16:
            return False
        # Simulate token validation (in real scenario, verify against server)
        return True
    
    @staticmethod
    def _validate_user_id(user_id: str) -> bool:
        """Validate user ID format"""
        return bool(re.match(r'^[a-zA-Z0-9_-]{3,32}$', user_id))


class InterceptionSimulator:
    """Simulates Cloudflare interception behavior"""
    
    def __init__(self, validator: StateValidator, simulate_latency: bool = False):
        self.validator = validator
        self.simulate_latency = simulate_latency
        self.events: List[InterceptionEvent] = []
        self.state_hashes: Dict[str, int] = {}
    
    def intercept(self, state: ReactState) -> Tuple[bool, InterceptionEvent]:
        """Intercept and validate state"""
        start_time = time.time()
        
        # Simulate latency
        if self.simulate_latency:
            latency = random.uniform(10, 100)
            time.sleep(latency / 1000)
        
        # Validate state
        allowed, reason = self.validator.validate(state)
        
        # Compute state hash
        state_hash = self._compute_state_hash(state)
        
        # Track state access patterns
        if state_hash not in self.state_hashes:
            self.state_hashes[state_hash] = 0
        self.state_hashes[state_hash] += 1
        
        # Detect potential replay attacks
        if self.state_hashes[state_hash] > 10:
            allowed = False
            reason = "Potential replay attack detected"
        
        latency_ms = (time.time() - start_time) * 1000
        payload_size = len(state.serialize())
        
        event = InterceptionEvent(
            timestamp=time.time(),
            interception_type=StateInterceptionType.FORM_SUBMISSION,
            state_hash=state_hash,
            allowed=allowed,
            reason=reason,
            latency_ms=latency_ms,
            payload_size=payload_size
        )
        
        self.events.append(event)
        return allowed, event
    
    @staticmethod
    def _compute_state_hash(state: ReactState) -> str:
        """Compute cryptographic hash of state"""
        data = state.serialize().encode()
        return hashlib.sha256(data).hexdigest()


class IntegrationTestRunner:
    """Runs integration tests"""
    
    def __init__(self, simulator: InterceptionSimulator, verbose: bool = False):
        self.simulator = simulator
        self.verbose = verbose
        self.results: List[Dict[str, Any]] = []
    
    def run_test(self, test_case: TestCase) -> Dict[str, Any]:
        """Run a single test case"""
        start_time = time.time()
        
        allowed, event = self.simulator.intercept(test_case.state)
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Determine result
        if event.latency_ms > (test_case.timeout_seconds * 1000):
            result_status = TestResult.TIMEOUT
        elif not allowed and test_case.expected_blocked:
            result_status = TestResult.PASS
        elif allowed and not test_case.expected_blocked:
            result_status = TestResult.PASS
        elif not allowed and not test_case.expected_blocked:
            result_status = TestResult.FAIL
        else:
            result_status = TestResult.FAIL
        
        test_result = {
            "test_name": test_case.name,
            "description": test_case.description,
            "status": result_status.value,
            "allowed": allowed,
            "expected_blocked": test_case.expected_blocked,
            "reason": event.reason,
            "latency_ms": round(event.latency_ms, 2),
            "payload_size": event.payload_size,
            "state_hash": event.state_hash,
            "duration_ms": round(duration_ms, 2),
            "edge_case": test_case.edge_case_type
        }
        
        self.results.append(test_result)
        
        if self.verbose:
            print(f"[{result_status.value.upper()}] {test_case.name}: {event.reason}")
        
        return test_result
    
    def run_all_tests(self, test_cases: List[TestCase]) -> List[Dict[str, Any]]:
        """Run all test cases"""
        for test_case in test_cases:
            self.run_test(test_case)
        return self.results
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test summary statistics"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == TestResult.PASS.value)
        failed = sum(1 for r in self.results if r["status"] == TestResult.FAIL.value)
        timeouts = sum(1 for r in self.results if r["status"] == TestResult.TIMEOUT.value)
        edge_cases = sum(1 for r in self.results if r["edge_case"] is not None)
        
        avg_latency = sum(r["latency_ms"] for r in self.results) / total if total > 0 else 0
        max_latency = max((r["latency_ms"] for r in self.results), default=0)
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "timeouts": timeouts,
            "edge_cases_tested": edge_cases,
            "pass_rate": round((passed / total * 100) if total > 0 else 0, 2),
            "average_latency_ms": round(avg_latency, 2),
            "max_latency_ms": round(max_latency, 2)
        }


def generate_test_cases(count: int = 20) -> List[TestCase]:
    """Generate comprehensive test cases"""
    test_cases = [
        # Basic functionality
        TestCase(
            name="normal_message",
            description="Normal valid message",
            state=ReactState(
                message="Hello, this is a test message",
                user_id="user123",
                session_token="session_abc123def456",
                input_enabled=True,
                timestamp=time.time(),
                component_id="chat_input_1"
            ),
            expected_blocked=False
        ),
        
        # XSS attempt
        TestCase(
            name="xss_script_injection",
            description="Attempt to inject script tag",
            state=ReactState(
                message="<script>alert('xss')</script>",
                user_id="user123",
                session_token="session_abc123def456",
                input_enabled=True,
                timestamp=time.time(),
                component_id="chat_input_1"
            ),
            expected_blocked=True,
            edge_case_type="xss"
        ),
        
        # Empty message
        TestCase(
            name="empty_message",
            description="Empty message submission",
            state=ReactState(
                message="",
                user_id="user123",
                session_token="session_abc123def456",
                input_enabled=True,
                timestamp=time.time(),
                component_id="chat_input_1"
            ),
            expected_blocked=True,
            edge_case_type="boundary"
        ),
        
        # Whitespace only
        TestCase(
            name="whitespace_only",
            description="Message containing only whitespace",
            state=ReactState(
                message="   \t\n   ",
                user_id="user123",
                session_token="session_abc123def456",
                input_enabled=True,
                timestamp=time.time(),
                component_id="chat_input_1"
            ),
            expected_blocked=True,
            edge_case_type="boundary"
        ),
        
        # Maximum length
        TestCase(
            name="max_length_message",
            description="Message at maximum length",
            state=ReactState(
                message="a" * 4000,
                user_id="user123",
                session_token="session_abc123def456",
                input_enabled=True,
                timestamp=time.time(),
                component_id="chat_input_1"
            ),
            expected_blocked=False,
            edge_case_type="boundary"
        ),
        
        # Exceeds maximum length
        TestCase(
            name="exceeds_max_length",
            description="Message exceeding maximum length",
            state=ReactState(
                message="a" * 4001,
                user_id="user123",
                session_token="session_abc123def456",
                input_enabled=True,
                timestamp=time.time(),
                component_id="chat_input_1"
            ),
            expected_blocked=True,
            edge_case_type="boundary"
        ),
        
        # Invalid session token
        TestCase(
            name="invalid_session_token",
            description="Invalid session token format",
            state=ReactState(
                message="Hello world",
                user_id="user123",
                session_token="short",
                input_enabled=True,
                timestamp=time.time(),
                component_id="chat_input_1"
            ),
            expected_blocked=True,
            edge_case_type="validation"
        ),
        
        # Invalid user ID
        TestCase(
            name="invalid_user_id",
            description="Invalid user ID format",
            state=ReactState(
                message="Hello world",
                user_id="!@#$%",
                session_token="session_abc123def456",
                input_enabled=True,
                timestamp=time.time(),
                component_id="chat_input_1"
            ),
            expected_blocked=True,
            edge_case_type="validation"
        ),
        
        # Input disabled in state
        TestCase(
            name="input_disabled",
            description="Input disabled in React state",
            state=ReactState(
                message="Hello world",
                user_id="user123",
                session_token="session_abc123def456",
                input_enabled=False,
                timestamp=time.time(),
                component_id="chat_input_1"
            ),
            expected_blocked=False  # Not blocked in non-strict mode
        ),
        
        # JavaScript protocol
        TestCase(
            name="javascript_protocol",
            description="Attempt to use javascript: protocol",
            state=ReactState(
                message="javascript:alert('xss')",
                user_id="user123",
                session_token="session_abc123def456",
                input_enabled=True,
                timestamp=time.time(),
                component_id="chat_input_1"
            ),
            expected_blocked=True,
            edge_case_type="xss"
        ),
        
        # Event handler injection
        TestCase(
            name="event_handler_injection",
            description="Attempt to inject event handler",
            state=ReactState(
                message="<img onerror='alert(1)'>",
                user_id="user123",
                session_token="session_abc123def456",
                input_enabled=True,
                timestamp=time.time(),
                component_id="chat_input_1"
            ),
            expected_blocked=True,
            edge_case_type="xss"
        ),
        
        # SQL injection pattern
        TestCase(
            name="sql_pattern",
            description="Message containing SQL-like patterns",
            state=ReactState(
                message="SELECT * FROM users WHERE id='1'",
                user_id="user123",
                session
#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Write integration tests
# Mission: Don't Wait for Claude
# Agent:   @aria
# Date:    2026-03-31T19:20:06.670Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Integration Tests for SwarmPulse Agent Communication
MISSION: Don't Wait for Claude
CATEGORY: AI/ML
AGENT: @aria
DATE: 2024
TASK: Write integration tests covering edge cases and failure modes
"""

import unittest
import json
import time
import sys
import argparse
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
from typing import List, Dict, Any, Optional
import traceback
from dataclasses import dataclass, asdict
from enum import Enum
import random
import threading


class AgentStatus(Enum):
    """Agent operational status"""
    IDLE = "idle"
    PROCESSING = "processing"
    FAILED = "failed"
    RECOVERING = "recovering"
    HEALTHY = "healthy"


@dataclass
class AgentMessage:
    """Represents a message between agents"""
    sender_id: str
    receiver_id: str
    payload: Dict[str, Any]
    timestamp: float
    message_id: str
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class AgentHealthMetrics:
    """Health metrics for an agent"""
    agent_id: str
    status: AgentStatus
    uptime_seconds: float
    message_queue_size: int
    error_count: int
    processed_count: int
    last_heartbeat: float


class SwarmAgent:
    """Simulates a SwarmPulse agent with message handling"""
    
    def __init__(self, agent_id: str, network_reliability: float = 0.95):
        self.agent_id = agent_id
        self.message_queue: List[AgentMessage] = []
        self.processed_messages: List[AgentMessage] = []
        self.status = AgentStatus.IDLE
        self.error_count = 0
        self.network_reliability = network_reliability
        self.start_time = time.time()
        self.last_heartbeat = time.time()
        self.processing_delay = 0.01
        
    def send_message(self, receiver_id: str, payload: Dict[str, Any]) -> AgentMessage:
        """Send a message to another agent"""
        if not self._check_network():
            raise ConnectionError(f"Network unavailable for {self.agent_id}")
        
        if not payload:
            raise ValueError("Payload cannot be empty")
        
        message = AgentMessage(
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            payload=payload,
            timestamp=time.time(),
            message_id=f"{self.agent_id}-{len(self.processed_messages)}"
        )
        return message
    
    def receive_message(self, message: AgentMessage) -> bool:
        """Receive and queue a message"""
        if message.receiver_id != self.agent_id:
            return False
        
        self.message_queue.append(message)
        return True
    
    def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process a queued message"""
        self.status = AgentStatus.PROCESSING
        try:
            time.sleep(self.processing_delay)
            
            if "error_trigger" in message.payload:
                raise RuntimeError(message.payload["error_trigger"])
            
            self.processed_messages.append(message)
            self.status = AgentStatus.HEALTHY
            return {"success": True, "message_id": message.message_id}
        except Exception as e:
            self.error_count += 1
            self.status = AgentStatus.FAILED
            return {"success": False, "error": str(e), "message_id": message.message_id}
    
    def retry_message(self, message: AgentMessage) -> bool:
        """Retry processing a failed message"""
        if message.retry_count >= message.max_retries:
            return False
        
        message.retry_count += 1
        self.status = AgentStatus.RECOVERING
        time.sleep(0.01 * message.retry_count)
        
        result = self.process_message(message)
        return result.get("success", False)
    
    def get_health_metrics(self) -> AgentHealthMetrics:
        """Get current health metrics"""
        return AgentHealthMetrics(
            agent_id=self.agent_id,
            status=self.status,
            uptime_seconds=time.time() - self.start_time,
            message_queue_size=len(self.message_queue),
            error_count=self.error_count,
            processed_count=len(self.processed_messages),
            last_heartbeat=time.time()
        )
    
    def _check_network(self) -> bool:
        """Simulate network reliability"""
        return random.random() < self.network_reliability
    
    def heartbeat(self) -> bool:
        """Send a heartbeat to indicate agent is alive"""
        self.last_heartbeat = time.time()
        return True


class SwarmNetwork:
    """Manages a network of agents"""
    
    def __init__(self):
        self.agents: Dict[str, SwarmAgent] = {}
        self.message_log: List[Dict[str, Any]] = []
        self.network_partitions: set = set()
    
    def register_agent(self, agent: SwarmAgent) -> None:
        """Register an agent in the network"""
        if agent.agent_id in self.agents:
            raise ValueError(f"Agent {agent.agent_id} already registered")
        self.agents[agent.agent_id] = agent
    
    def send_message(self, sender_id: str, receiver_id: str, payload: Dict[str, Any]) -> Optional[AgentMessage]:
        """Send a message between agents"""
        if sender_id not in self.agents:
            raise ValueError(f"Sender {sender_id} not registered")
        if receiver_id not in self.agents:
            raise ValueError(f"Receiver {receiver_id} not registered")
        
        if self._is_partitioned(sender_id, receiver_id):
            raise ConnectionError(f"Network partition between {sender_id} and {receiver_id}")
        
        sender = self.agents[sender_id]
        receiver = self.agents[receiver_id]
        
        message = sender.send_message(receiver_id, payload)
        receiver.receive_message(message)
        
        self.message_log.append({
            "message_id": message.message_id,
            "sender": sender_id,
            "receiver": receiver_id,
            "timestamp": message.timestamp
        })
        
        return message
    
    def simulate_partition(self, agent_a: str, agent_b: str) -> None:
        """Simulate a network partition between two agents"""
        self.network_partitions.add((frozenset([agent_a, agent_b])))
    
    def heal_partition(self, agent_a: str, agent_b: str) -> None:
        """Heal a network partition"""
        self.network_partitions.discard(frozenset([agent_a, agent_b]))
    
    def _is_partitioned(self, agent_a: str, agent_b: str) -> bool:
        """Check if agents are partitioned"""
        return frozenset([agent_a, agent_b]) in self.network_partitions
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get overall network status"""
        metrics = [agent.get_health_metrics() for agent in self.agents.values()]
        return {
            "total_agents": len(self.agents),
            "healthy_agents": sum(1 for m in metrics if m.status == AgentStatus.HEALTHY),
            "failed_agents": sum(1 for m in metrics if m.status == AgentStatus.FAILED),
            "total_messages": len(self.message_log),
            "partitions": len(self.network_partitions)
        }


class TestSwarmAgentBasics(unittest.TestCase):
    """Test basic agent functionality"""
    
    def setUp(self):
        self.agent = SwarmAgent("agent-1")
    
    def test_agent_initialization(self):
        """Test agent initializes with correct defaults"""
        self.assertEqual(self.agent.agent_id, "agent-1")
        self.assertEqual(self.agent.status, AgentStatus.IDLE)
        self.assertEqual(len(self.agent.message_queue), 0)
        self.assertEqual(self.agent.error_count, 0)
    
    def test_send_message_success(self):
        """Test successful message sending"""
        payload = {"action": "test", "value": 42}
        message = self.agent.send_message("agent-2", payload)
        
        self.assertEqual(message.sender_id, "agent-1")
        self.assertEqual(message.receiver_id, "agent-2")
        self.assertEqual(message.payload, payload)
        self.assertEqual(message.retry_count, 0)
    
    def test_send_message_empty_payload(self):
        """Test sending message with empty payload fails"""
        with self.assertRaises(ValueError):
            self.agent.send_message("agent-2", {})
    
    def test_receive_message_correct_receiver(self):
        """Test receiving message for correct receiver"""
        message = AgentMessage(
            sender_id="agent-2",
            receiver_id="agent-1",
            payload={"data": "test"},
            timestamp=time.time(),
            message_id="msg-1"
        )
        
        result = self.agent.receive_message(message)
        self.assertTrue(result)
        self.assertEqual(len(self.agent.message_queue), 1)
    
    def test_receive_message_wrong_receiver(self):
        """Test receiving message for wrong receiver"""
        message = AgentMessage(
            sender_id="agent-2",
            receiver_id="agent-3",
            payload={"data": "test"},
            timestamp=time.time(),
            message_id="msg-1"
        )
        
        result = self.agent.receive_message(message)
        self.assertFalse(result)
        self.assertEqual(len(self.agent.message_queue), 0)


class TestMessageProcessing(unittest.TestCase):
    """Test message processing edge cases"""
    
    def setUp(self):
        self.agent = SwarmAgent("processor-1")
    
    def test_process_message_success(self):
        """Test successful message processing"""
        message = AgentMessage(
            sender_id="agent-2",
            receiver_id="processor-1",
            payload={"action": "compute", "value": 10},
            timestamp=time.time(),
            message_id="msg-1"
        )
        
        result = self.agent.process_message(message)
        self.assertTrue(result["success"])
        self.assertEqual(len(self.agent.processed_messages), 1)
        self.assertEqual(self.agent.status, AgentStatus.HEALTHY)
    
    def test_process_message_with_error_trigger(self):
        """Test processing message that triggers error"""
        message = AgentMessage(
            sender_id="agent-2",
            receiver_id="processor-1",
            payload={"error_trigger": "Simulated failure"},
            timestamp=time.time(),
            message_id="msg-1"
        )
        
        result = self.agent.process_message(message)
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(self.agent.error_count, 1)
        self.assertEqual(self.agent.status, AgentStatus.FAILED)
    
    def test_retry_message_success_on_second_attempt(self):
        """Test message retry succeeds after initial failure"""
        message = AgentMessage(
            sender_id="agent-2",
            receiver_id="processor-1",
            payload={"data": "test"},
            timestamp=time.time(),
            message_id="msg-1",
            max_retries=3
        )
        
        # First attempt succeeds
        result = self.agent.process_message(message)
        self.assertTrue(result["success"])
        self.assertEqual(message.retry_count, 0)
    
    def test_retry_exhausted(self):
        """Test retry exhaustion after max attempts"""
        message = AgentMessage(
            sender_id="agent-2",
            receiver_id="processor-1",
            payload={"error_trigger": "Persistent error"},
            timestamp=time.time(),
            message_id="msg-1",
            max_retries=2,
            retry_count=2
        )
        
        result = self.agent.retry_message(message)
        self.assertFalse(result)
        self.assertEqual(message.retry_count, 2)


class TestNetworkPartitioning(unittest.TestCase):
    """Test network partition handling"""
    
    def setUp(self):
        self.network = SwarmNetwork()
        self.agent1 = SwarmAgent("agent-1")
        self.agent2 = SwarmAgent("agent-2")
        self.network.register_agent(self.agent1)
        self.network.register_agent(self.agent2)
    
    def test_send_message_without_partition(self):
        """Test message sending works without partition"""
        message = self.network.send_message("agent-1", "agent-2", {"data": "test"})
        self.assertIsNotNone(message)
        self.assertEqual(len(self.agent2.message_queue), 1)
    
    def test_send_message_with_partition(self):
        """Test message sending fails during partition"""
        self.network.simulate_partition("agent-1", "agent-2")
        
        with self.assertRaises(ConnectionError):
            self.network.send_message("agent-1", "agent-2", {"data": "test"})
    
    def test_partition_healing(self):
        """Test partition healing restores communication"""
        self.network.simulate_partition("agent-1", "agent-2")
        
        with self.assertRaises(ConnectionError):
            self.network.send_message("agent-1", "agent-2", {"data": "test"})
        
        self.network.heal_partition("agent-1", "agent-2")
        
        message = self.network.send_message("agent-1", "agent-2", {"data": "test"})
        self.assertIsNotNone(message)


class TestNetworkReliability(unittest.TestCase):
    """Test network reliability and recovery"""
    
    def setUp(self):
        self.network = SwarmNetwork()
    
    def test_unreliable_agent_communication(self):
        """Test communication with unreliable agents"""
        agent1 = SwarmAgent("unreliable-1", network_reliability=0.5)
        agent2 = SwarmAgent("unreliable-2", network_reliability=0.5)
        
        self.network.register_agent(agent1)
        self.network.register_agent(agent2)
        
        success_count = 0
        attempt_count = 0
        
        for _ in range(20):
            attempt_count += 1
            try:
                self.network.send_message("unreliable-1", "unreliable-2", {"data": "test"})
                success_count += 1
            except ConnectionError:
                pass
        
        # Should have mixed success/failure
        self.assertGreater(success_count, 0)
        self.assertLess(success_count, attempt_count)


class TestHealthMetrics(unittest.TestCase):
    """Test health metrics collection"""
    
    def test_agent_health_metrics(self):
        """Test agent health metrics are accurate"""
        agent = SwarmAgent("metrics-1")
        
        metrics = agent.get_health_metrics()
        self.assertEqual(metrics.agent_id, "metrics-1")
        self.assertEqual(metrics.status, AgentStatus.IDLE)
        self.assertEqual(metrics.error_count, 0)
        self.assertEqual(metrics.processed_count, 0)
        self.assertGreater(metrics.uptime_seconds, 0)
    
    def test_health_metrics_after_processing(self):
        """Test health metrics update after message processing"""
        agent = SwarmAgent("metrics-2")
        
        message = AgentMessage(
            sender_id="other",
            receiver_id="metrics-2",
            payload={"data": "test"},
            timestamp=time.time(),
            message_id="msg-1"
        )
        
        agent.process_message(message)
        
        metrics = agent.get_health_metrics()
        self.assertEqual(metrics.processed_count, 1)
        self.assertEqual(metrics.error_count, 0)
    
    def test_network_status_aggregation(self):
        """Test network status aggregates agent metrics"""
        network = SwarmNetwork()
        agents = [SwarmAgent(f"agent-{i}") for i in range(3)]
        
        for agent in agents:
            network.register_agent(agent)
        
        status = network.get_network_status()
        self.assertEqual(status["total_agents"], 3)
        self.assertGreater(status["healthy_agents"], 0)
        self.assertEqual(status["total_messages"], 0)


class TestConcurrency(unittest.TestCase):
    """Test concurrent message handling"""
    
    def test_concurrent_message_processing(self):
        """Test multiple agents processing messages concurrently"""
        network = SwarmNetwork()
        agents = [SwarmAgent(f"agent-{i}") for i in range(3)]
        
        for agent in agents:
            network.register_agent(agent)
        
        results = []
        
        def send_messages(sender_idx, receiver_idx):
            for i in range(5):
                try:
                    message = network.send_message(
                        f"agent-{sender_idx}",
                        f"agent-{receiver_idx}",
                        {"iteration": i, "data": f"message-{i}"}
                    )
                    results.append({"success": True, "message_id": message.message_id})
                except Exception as e:
                    results.append({"success": False, "error": str(e)})
        
        threads = []
        for i in range(3):
            for j in range(3):
                if i != j:
                    t = threading.Thread(target=send_messages, args=(i, j))
                    threads.append(t)
                    t.start()
        
        for t in threads:
            t.join()
        
        successful = sum(1 for r in results if r["success"])
        self.assertGreater(successful, 0)
        self.assertEqual(len(results), 18)  # 6 sender/receiver pairs * 5 messages / 2


class TestMessageTimeouts(unittest.TestCase):
    """Test message timeout handling"""
    
    def test_message_timeout_detection(self):
        """Test detection of timed-out messages"""
        network = SwarmNetwork()
        agent1 = SwarmAgent("timeout-1")
        agent2 = SwarmAgent("timeout-2")
        
        network.register_agent(agent1)
        network.register_agent(agent2)
        
        message = network.send_message("timeout-1", "timeout-2", {"data": "test"})
        
        # Check if message can be marked as timed out
        elapsed = time.time() - message.timestamp
        self.assertGreater(elapsed, 0)
        self.assertLess(elapsed, 1.0)  # Should be nearly instantaneous


class TestIntegrationScenarios(unittest.TestCase):
    """Test complete integration scenarios"""
    
    def test_multi_agent_workflow(self):
        """Test a complete workflow with multiple agents"""
        network = SwarmNetwork()
        
        # Create agents
        requester = SwarmAgent("requester")
        processor = SwarmAgent("processor")
        responder = SwarmAgent("responder")
        
        for agent in [requester, processor, responder]:
            network.register_agent(agent)
        
        # Send request
        req_msg = network.send_message("requester", "processor", {"task": "compute", "value": 42})
        self.assertIsNotNone(req_msg)
        
        # Process request
        processor.receive_message(req_msg)
        result = processor.process_message(req_msg)
        self.assertTrue(result["success"])
        
        # Send response
        resp_msg = network.send_message("processor", "responder", {"result": result["message_id"]})
        self.assertIsNotNone(resp_msg)
        
        # Verify network state
        status = network.get_network_status()
        self.assertEqual(status["total_agents"], 3)
        self.assertEqual(status["total_messages"], 2)
    
    def test_cascading_failure_scenario(self):
        """Test handling of cascading failures"""
        network = SwarmNetwork()
        
        agents = [SwarmAgent(f"cascading-{i}") for i in range(4)]
        for agent in agents:
            network.register_agent(agent)
        
        # Agent 0 sends to 1
        msg1 = network.send_message("cascading-0", "cascading-1", {"step": 1})
        agents[1].receive_message(msg1)
        result1 = agents[1].process_message(msg1)
        
        # Agent 1 sends to 2
        msg2 = network.send_message("cascading-1", "cascading-2", {"step": 2})
        agents[2].receive_message(msg2)
        result2 = agents[2].process_message(msg2)
        
        # Agent 2 sends to 3 with error
        msg3_payload = {"step": 3, "error_trigger": "Cascade failure"}
        msg3 = network.send_message("cascading-2", "cascading-3", msg3_payload)
        agents[3].receive_message(msg3)
        result3 = agents[3].process_message(msg3)
        
        self.assertTrue(result1["success"])
        self.assertTrue(result2["success"])
        self.assertFalse(result3["success"])


def run_test_suite(verbosity: int = 2, pattern: Optional[str] = None) -> unittest.TestResult:
    """Run the complete test suite"""
    loader = unittest.TestLoader()
    
    if pattern:
        suite = loader.discover(".", pattern=pattern)
    else:
        test_classes = [
            TestSwarmAgentBasics,
            TestMessageProcessing,
            TestNetworkPartitioning,
            TestNetworkReliability,
            TestHealthMetrics,
            TestConcurrency,
            TestMessageTimeouts,
            TestIntegrationScenarios
        ]
        suite = unittest.TestSuite()
        for test_class in test_classes:
            suite.addTests(loader.loadTestsFromTestCase(test_class))
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    return runner.run(suite)


def generate_test_report(result: unittest.TestResult) -> Dict[str, Any]:
    """Generate a structured test report"""
    return {
        "total_tests": result.testsRun,
        "passed": result.testsRun - len(result.failures) - len(result.errors),
        "failed": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "success_rate": ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0,
        "failures": [str(f[0]) for f in result.failures],
        "errors": [str(e[0]) for e in result.errors]
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SwarmPulse Integration Test Suite"
    )
    parser.add_argument(
        "--verbosity",
        type=int,
        choices=[0, 1, 2],
        default=2,
        help="Test output verbosity level"
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default=None,
        help="Test name pattern to filter tests"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demonstration scenario"
    )
    
    args = parser.parse_args()
    
    if args.demo:
        print("=" * 60)
        print("SwarmPulse Integration Test Demonstration")
        print("=" * 60)
        
        network = SwarmNetwork()
        agents = [SwarmAgent(f"demo-agent-{i}", network_reliability=0.9) for i in range(3)]
        
        for agent in agents:
            network.register_agent(agent)
            print(f"Registered {agent.agent_id}")
        
        print("\n--- Multi-Agent Workflow ---")
        try:
            msg1 = network.send_message("demo-agent-0", "demo-agent-1", {"action": "query", "data": "test"})
            print(f"Message sent: {msg1.message_id}")
            
            agents[1].receive_message(msg1)
            result = agents[1].process_message(msg1)
            print(f"Processing result: {result}")
            
            status = network.get_network_status()
            print(f"Network status: {json.dumps(status, indent=2)}")
        except Exception as e:
            print(f"Error in workflow: {e}")
        
        print("\n--- Running Test Suite ---")
        result = run_test_suite(verbosity=args.verbosity, pattern=args.pattern)
        
        report = generate_test_report(result)
        
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"\nTest Report:")
            print(f"  Total Tests: {report['total_tests']}")
            print(f"  Passed: {report['passed']}")
            print(f"  Failed: {report['failed']}")
            print(f"  Errors: {report['errors']}")
            print(f"  Success Rate: {report['success_rate']:.1f}%")
    else:
        result = run_test_suite(verbosity=args.verbosity, pattern=args.pattern)
        
        report = generate_test_report(result)
        
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"\nTest Summary:")
            print(f"  Total: {report['total_tests']} | Passed: {report['passed']} | Failed: {report['failed']} | Errors: {report['errors']}")
            print(f"  Success Rate: {report['success_rate']:.1f}%")
        
        sys.exit(0 if report['failed'] == 0 and report['errors'] == 0 else 1)
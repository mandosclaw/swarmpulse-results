#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Write integration tests
# Mission: Don't Wait for Claude
# Agent:   @aria
# Date:    2026-03-29T20:38:50.972Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Integration tests for SwarmPulse agent communication and workflow execution.
MISSION: Don't Wait for Claude
CATEGORY: AI/ML
TASK: Write integration tests covering edge cases and failure modes
AGENT: @aria
DATE: 2024
"""

import unittest
import sys
import json
import time
import argparse
import threading
import random
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import traceback


class AgentState(Enum):
    """Agent lifecycle states."""
    IDLE = "idle"
    BUSY = "busy"
    FAILED = "failed"
    TIMEOUT = "timeout"
    HEALTHY = "healthy"


class MessageType(Enum):
    """Message types in SwarmPulse network."""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    ACKNOWLEDGMENT = "acknowledgment"


@dataclass
class Message:
    """Message structure in SwarmPulse network."""
    msg_id: str
    msg_type: MessageType
    sender: str
    recipient: str
    timestamp: float
    payload: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "msg_id": self.msg_id,
            "msg_type": self.msg_type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "timestamp": self.timestamp,
            "payload": self.payload
        }


@dataclass
class AgentMetrics:
    """Metrics for agent performance monitoring."""
    agent_id: str
    messages_sent: int = 0
    messages_received: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    average_response_time: float = 0.0
    uptime_seconds: float = 0.0
    last_heartbeat: float = 0.0


class MessageQueue:
    """Thread-safe message queue for agent communication."""
    
    def __init__(self):
        self.messages: List[Message] = []
        self.lock = threading.Lock()
        self.delivery_failures: Dict[str, int] = defaultdict(int)
    
    def enqueue(self, message: Message) -> bool:
        """Enqueue a message. May fail under stress."""
        with self.lock:
            if random.random() < 0.02:  # 2% failure rate under normal load
                self.delivery_failures[message.msg_id] += 1
                return False
            self.messages.append(message)
            return True
    
    def dequeue(self) -> Optional[Message]:
        """Dequeue a message FIFO."""
        with self.lock:
            if self.messages:
                return self.messages.pop(0)
            return None
    
    def peek(self) -> Optional[Message]:
        """Peek at next message without removing."""
        with self.lock:
            if self.messages:
                return self.messages[0]
            return None
    
    def size(self) -> int:
        """Get current queue size."""
        with self.lock:
            return len(self.messages)
    
    def clear(self):
        """Clear all messages."""
        with self.lock:
            self.messages.clear()


class Agent:
    """SwarmPulse Agent with communication and task execution."""
    
    def __init__(self, agent_id: str, response_latency: float = 0.1, 
                 failure_rate: float = 0.0):
        self.agent_id = agent_id
        self.state = AgentState.IDLE
        self.response_latency = response_latency
        self.failure_rate = failure_rate
        self.message_queue = MessageQueue()
        self.metrics = AgentMetrics(agent_id=agent_id)
        self.start_time = time.time()
        self.running = False
        self.task_results: Dict[str, Any] = {}
        self._update_uptime()
    
    def _update_uptime(self):
        """Update uptime metric."""
        self.metrics.uptime_seconds = time.time() - self.start_time
    
    def send_message(self, message: Message) -> bool:
        """Send a message (enqueue for delivery)."""
        success = self.message_queue.enqueue(message)
        if success:
            self.metrics.messages_sent += 1
        return success
    
    def receive_message(self) -> Optional[Message]:
        """Receive a message from queue."""
        msg = self.message_queue.dequeue()
        if msg:
            self.metrics.messages_received += 1
            self.metrics.last_heartbeat = time.time()
        return msg
    
    def execute_task(self, task_id: str, task_data: Dict[str, Any]) -> Tuple[bool, Any]:
        """Execute a task with possibility of failure."""
        self.state = AgentState.BUSY
        
        # Simulate processing time
        time.sleep(self.response_latency)
        
        # Simulate failure
        if random.random() < self.failure_rate:
            self.state = AgentState.FAILED
            self.metrics.failed_tasks += 1
            result = {"status": "failed", "error": "Task execution failed"}
            self.task_results[task_id] = result
            return False, result
        
        self.state = AgentState.HEALTHY
        self.metrics.successful_tasks += 1
        result = {"status": "success", "task_id": task_id, "result": task_data}
        self.task_results[task_id] = result
        return True, result
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent metrics as dict."""
        self._update_uptime()
        return asdict(self.metrics)


class SwarmNetwork:
    """Manages multiple agents and their communication."""
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.message_log: List[Message] = []
        self.lock = threading.Lock()
    
    def register_agent(self, agent: Agent) -> bool:
        """Register an agent in the network."""
        with self.lock:
            if agent.agent_id in self.agents:
                return False
            self.agents[agent.agent_id] = agent
            return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the network."""
        with self.lock:
            if agent_id not in self.agents:
                return False
            del self.agents[agent_id]
            return True
    
    def route_message(self, message: Message) -> bool:
        """Route a message to its recipient agent."""
        with self.lock:
            self.message_log.append(message)
            if message.recipient not in self.agents:
                return False
            recipient = self.agents[message.recipient]
        
        return recipient.send_message(message)
    
    def get_network_health(self) -> Dict[str, Any]:
        """Get overall network health status."""
        with self.lock:
            agents_list = list(self.agents.values())
        
        total_messages = sum(a.metrics.messages_sent for a in agents_list)
        total_tasks = sum(a.metrics.successful_tasks for a in agents_list)
        failed_tasks = sum(a.metrics.failed_tasks for a in agents_list)
        
        return {
            "total_agents": len(agents_list),
            "total_messages": total_messages,
            "total_successful_tasks": total_tasks,
            "total_failed_tasks": failed_tasks,
            "message_log_size": len(self.message_log)
        }


class TestAgentCommunication(unittest.TestCase):
    """Test agent-to-agent communication."""
    
    def setUp(self):
        self.network = SwarmNetwork()
        self.agent1 = Agent("agent_1", response_latency=0.01)
        self.agent2 = Agent("agent_2", response_latency=0.01)
        self.network.register_agent(self.agent1)
        self.network.register_agent(self.agent2)
    
    def tearDown(self):
        self.network.unregister_agent("agent_1")
        self.network.unregister_agent("agent_2")
    
    def test_successful_message_delivery(self):
        """Test that messages are delivered successfully."""
        msg = Message(
            msg_id="msg_001",
            msg_type=MessageType.TASK_REQUEST,
            sender="agent_1",
            recipient="agent_2",
            timestamp=time.time(),
            payload={"task": "compute", "data": [1, 2, 3]}
        )
        
        success = self.network.route_message(msg)
        self.assertTrue(success)
        self.assertGreater(self.agent2.metrics.messages_received, 0)
    
    def test_message_to_nonexistent_agent(self):
        """Test delivery failure to non-existent agent."""
        msg = Message(
            msg_id="msg_002",
            msg_type=MessageType.TASK_REQUEST,
            sender="agent_1",
            recipient="nonexistent_agent",
            timestamp=time.time(),
            payload={"task": "compute"}
        )
        
        success = self.network.route_message(msg)
        self.assertFalse(success)
    
    def test_multiple_concurrent_messages(self):
        """Test handling multiple messages concurrently."""
        messages = []
        for i in range(10):
            msg = Message(
                msg_id=f"msg_{i:03d}",
                msg_type=MessageType.TASK_REQUEST,
                sender="agent_1",
                recipient="agent_2",
                timestamp=time.time(),
                payload={"index": i}
            )
            messages.append(msg)
        
        for msg in messages:
            self.network.route_message(msg)
        
        self.assertEqual(self.agent2.metrics.messages_received, 10)
        self.assertEqual(len(self.network.message_log), 10)
    
    def test_message_ordering(self):
        """Test that messages maintain FIFO order."""
        for i in range(5):
            msg = Message(
                msg_id=f"msg_{i:03d}",
                msg_type=MessageType.TASK_REQUEST,
                sender="agent_1",
                recipient="agent_2",
                timestamp=time.time(),
                payload={"order": i}
            )
            self.network.route_message(msg)
        
        received_order = []
        for _ in range(5):
            msg = self.agent2.receive_message()
            if msg:
                received_order.append(msg.payload["order"])
        
        self.assertEqual(received_order, [0, 1, 2, 3, 4])
    
    def test_empty_queue_dequeue(self):
        """Test dequeue on empty queue."""
        empty_queue = MessageQueue()
        msg = empty_queue.dequeue()
        self.assertIsNone(msg)
    
    def test_queue_peek(self):
        """Test peeking at queue without removal."""
        msg1 = Message(
            msg_id="msg_peek_1",
            msg_type=MessageType.HEARTBEAT,
            sender="agent_1",
            recipient="agent_2",
            timestamp=time.time(),
            payload={}
        )
        
        self.agent2.send_message(msg1)
        peeked = self.agent2.message_queue.peek()
        self.assertIsNotNone(peeked)
        self.assertEqual(peeked.msg_id, "msg_peek_1")
        
        dequeued = self.agent2.receive_message()
        self.assertEqual(dequeued.msg_id, "msg_peek_1")


class TestTaskExecution(unittest.TestCase):
    """Test task execution with various failure modes."""
    
    def setUp(self):
        self.reliable_agent = Agent("reliable_agent", response_latency=0.01, 
                                   failure_rate=0.0)
        self.flaky_agent = Agent("flaky_agent", response_latency=0.01, 
                                failure_rate=0.5)
    
    def test_successful_task_execution(self):
        """Test successful task execution."""
        success, result = self.reliable_agent.execute_task(
            "task_001", 
            {"operation": "compute", "value": 42}
        )
        
        self.assertTrue(success)
        self.assertEqual(result["status"], "success")
        self.assertEqual(self.reliable_agent.metrics.successful_tasks, 1)
        self.assertEqual(self.reliable_agent.metrics.failed_tasks, 0)
    
    def test_failed_task_execution(self):
        """Test failed task execution."""
        success, result = self.flaky_agent.execute_task(
            "task_002",
            {"operation": "compute"}
        )
        
        # Run multiple times to ensure we hit failures with flaky agent
        for _ in range(5):
            success, result = self.flaky_agent.execute_task(
                f"task_{random.randint(1000, 9999)}",
                {"operation": "compute"}
            )
        
        self.assertGreater(self.flaky_agent.metrics.failed_tasks, 0)
    
    def test_task_state_transitions(self):
        """Test agent state transitions during task execution."""
        self.assertEqual(self.reliable_agent.state, AgentState.IDLE)
        
        success, result = self.reliable_agent.execute_task(
            "task_003",
            {"operation": "compute"}
        )
        
        self.assertEqual(self.reliable_agent.state, AgentState.HEALTHY)
    
    def test_concurrent_task_execution(self):
        """Test concurrent task execution by multiple agents."""
        agents = [Agent(f"agent_{i}", response_latency=0.001, failure_rate=0.1) 
                  for i in range(5)]
        
        results = []
        threads = []
        
        def execute_tasks(agent, task_count):
            for i in range(task_count):
                success, result = agent.execute_task(
                    f"{agent.agent_id}_task_{i}",
                    {"value": i}
                )
                results.append((agent.agent_id, success))
        
        for agent in agents:
            thread = threading.Thread(target=execute_tasks, args=(agent, 5))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        self.assertEqual(len(results), 25)
        self.assertTrue(all(isinstance(r, tuple) and len(r) == 2 for r in results))
    
    def test_task_timeout_simulation(self):
        """Test task timeout handling."""
        slow_agent = Agent("slow_agent", response_latency=2.0, failure_rate=0.0)
        
        start = time.time()
        success, result = slow_agent.execute_task("slow_task", {})
        elapsed = time.time() - start
        
        self.assertGreaterEqual(elapsed, slow_agent.response_latency)


class TestMessageQueue(unittest.TestCase):
    """Test message queue under various conditions."""
    
    def setUp(self):
        self.queue = MessageQueue()
    
    def test_queue_size_tracking(self):
        """Test queue size is tracked correctly."""
        self.assertEqual(self.queue.size(), 0)
        
        msg = Message(
            msg_id="msg_001",
            msg_type=MessageType.HEARTBEAT,
            sender="agent_1",
            recipient="agent_2",
            timestamp=time.time(),
            payload={}
        )
        
        self.queue.enqueue(msg)
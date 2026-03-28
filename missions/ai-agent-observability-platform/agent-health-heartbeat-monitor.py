#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Agent health heartbeat monitor
# Mission: AI Agent Observability Platform
# Agent:   @bolt
# Date:    2026-03-28T21:58:32.430Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Agent health heartbeat monitor
MISSION: AI Agent Observability Platform
AGENT: @bolt
DATE: 2024
DESCRIPTION: Ping all registered agents every 60s, detect missed heartbeats, trigger webhook alerts
"""

import argparse
import json
import sys
import time
import threading
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import urllib.request
import urllib.error
from urllib.parse import urljoin


@dataclass
class Agent:
    name: str
    health_endpoint: str
    last_heartbeat: Optional[datetime] = None
    missed_heartbeats: int = 0
    status: str = "unknown"
    latency_ms: float = 0.0


@dataclass
class HeartbeatEvent:
    timestamp: datetime
    agent_name: str
    status: str
    latency_ms: float
    missed_count: int
    alert_triggered: bool


class AgentHealthMonitor:
    def __init__(
        self,
        heartbeat_interval: int = 60,
        heartbeat_timeout: int = 10,
        missed_threshold: int = 3,
        webhook_url: Optional[str] = None,
        log_file: Optional[str] = None,
    ):
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.missed_threshold = missed_threshold
        self.webhook_url = webhook_url
        self.agents: Dict[str, Agent] = {}
        self.events: List[HeartbeatEvent] = []
        self.running = False
        self.lock = threading.Lock()

        # Setup logging
        self.logger = logging.getLogger("AgentHealthMonitor")
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def register_agent(self, name: str, health_endpoint: str) -> None:
        """Register an agent for monitoring."""
        with self.lock:
            self.agents[name] = Agent(name=name, health_endpoint=health_endpoint)
        self.logger.info(f"Registered agent: {name} at {health_endpoint}")

    def ping_agent(self, agent: Agent) -> bool:
        """Ping a single agent and record latency."""
        start_time = time.time()
        try:
            req = urllib.request.Request(
                agent.health_endpoint,
                method="GET",
                headers={"User-Agent": "AgentHealthMonitor/1.0"},
            )
            with urllib.request.urlopen(req, timeout=self.heartbeat_timeout) as response:
                latency_ms = (time.time() - start_time) * 1000
                agent.latency_ms = latency_ms
                agent.last_heartbeat = datetime.utcnow()
                agent.status = "healthy"
                agent.missed_heartbeats = 0
                self.logger.debug(
                    f"Agent {agent.name} heartbeat OK ({latency_ms:.2f}ms)"
                )
                return True
        except urllib.error.URLError as e:
            agent.missed_heartbeats += 1
            agent.status = "unreachable"
            self.logger.warning(
                f"Agent {agent.name} unreachable: {e.reason}"
            )
            return False
        except urllib.error.HTTPError as e:
            agent.missed_heartbeats += 1
            agent.status = "error"
            self.logger.warning(
                f"Agent {agent.name} returned HTTP {e.code}"
            )
            return False
        except Exception as e:
            agent.missed_heartbeats += 1
            agent.status = "error"
            self.logger.error(f"Error pinging agent {agent.name}: {e}")
            return False

    def should_alert(self, agent: Agent) -> bool:
        """Determine if alert should be triggered."""
        return agent.missed_heartbeats >= self.missed_threshold

    def send_webhook_alert(self, agent: Agent, event: HeartbeatEvent) -> bool:
        """Send webhook alert for agent health issue."""
        if not self.webhook_url:
            return False

        payload = {
            "timestamp": event.timestamp.isoformat(),
            "agent_name": agent.name,
            "status": agent.status,
            "latency_ms": agent.latency_ms,
            "missed_heartbeats": agent.missed_heartbeats,
            "threshold": self.missed_threshold,
            "alert_type": "missed_heartbeat_threshold_exceeded",
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                self.logger.info(
                    f"Alert webhook sent for {agent.name}: HTTP {response.status}"
                )
                return True
        except Exception as e:
            self.logger.error(f"Failed to send webhook alert: {e}")
            return False

    def check_all_agents(self) -> None:
        """Check health of all registered agents."""
        with self.lock:
            agents_to_check = list(self.agents.values())

        for agent in agents_to_check:
            self.ping_agent(agent)

            # Check if alert should be triggered
            alert_triggered = False
            if self.should_alert(agent):
                alert_triggered = True
                self.logger.error(
                    f"ALERT: Agent {agent.name} missed {agent.missed_heartbeats} heartbeats"
                )
                event = HeartbeatEvent(
                    timestamp=datetime.utcnow(),
                    agent_name=agent.name,
                    status=agent.status,
                    latency_ms=agent.latency_ms,
                    missed_count=agent.missed_heartbeats,
                    alert_triggered=True,
                )
                self.send_webhook_alert(agent, event)
            else:
                event = HeartbeatEvent(
                    timestamp=datetime.utcnow(),
                    agent_name=agent.name,
                    status=agent.status,
                    latency_ms=agent.latency_ms,
                    missed_count=agent.missed_heartbeats,
                    alert_triggered=alert_triggered,
                )

            with self.lock:
                self.events.append(event)

    def monitoring_loop(self) -> None:
        """Main monitoring loop."""
        self.logger.info(
            f"Starting monitoring loop (interval: {self.heartbeat_interval}s)"
        )
        self.running = True

        try:
            while self.running:
                self.check_all_agents()
                time.sleep(self.heartbeat_interval)
        except KeyboardInterrupt:
            self.logger.info("Monitoring loop interrupted by user")
        finally:
            self.running = False
            self.logger.info("Monitoring loop stopped")

    def start_async(self) -> threading.Thread:
        """Start monitoring in background thread."""
        thread = threading.Thread(target=self.monitoring_loop, daemon=False)
        thread.start()
        return thread

    def
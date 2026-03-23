#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Multi-agent coordination layer
# Mission: Agentic RAG Infrastructure
# Agent:   @quinn
# Date:    2026-03-23T17:53:11.835Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""Multi-agent coordination layer: task queue with priority scheduling, capability matching, work distribution."""

import argparse
import heapq
import json
import logging
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class Task:
    task_id: str
    title: str
    priority: int
    required_capabilities: list[str]
    payload: dict[str, Any]
    created_at: float = field(default_factory=time.time)
    assigned_to: Optional[str] = None
    status: str = "PENDING"
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def __lt__(self, other: "Task") -> bool:
        return self.priority > other.priority


@dataclass
class Agent:
    agent_id: str
    capabilities: list[str]
    max_concurrent: int = 3
    current_load: int = 0
    tasks_completed: int = 0
    available: bool = True

    def can_handle(self, required: list[str]) -> bool:
        return all(cap in self.capabilities for cap in required)

    def has_capacity(self) -> bool:
        return self.available and self.current_load < self.max_concurrent


class PriorityTaskQueue:
    def __init__(self) -> None:
        self._heap: list[tuple[int, float, Task]] = []
        self._tasks: dict[str, Task] = {}

    def push(self, task: Task) -> None:
        heapq.heappush(self._heap, (-task.priority, task.created_at, task))
        self._tasks[task.task_id] = task
        logger.debug(f"Queued task {task.task_id} with priority {task.priority}")

    def pop(self) -> Optional[Task]:
        while self._heap:
            _, _, task = heapq.heappop(self._heap)
            if task.status == "PENDING":
                return task
        return None

    def peek_priority(self) -> int:
        for neg_pri, _, task in self._heap:
            if task.status == "PENDING":
                return -neg_pri
        return 0

    def size(self) -> int:
        return sum(1 for t in self._tasks.values() if t.status == "PENDING")

    def all_tasks(self) -> list[Task]:
        return list(self._tasks.values())


class CoordinationLayer:
    def __init__(self, agents: list[Agent]) -> None:
        self.agents = {a.agent_id: a for a in agents}
        self.queue = PriorityTaskQueue()
        self.completed_tasks: list[Task] = []
        self.failed_tasks: list[Task] = []

    def submit_task(self, task: Task) -> None:
        self.queue.push(task)
        logger.info(f"Submitted: {task.task_id} '{task.title}' priority={task.priority} caps={task.required_capabilities}")

    def find_best_agent(self, task: Task) -> Optional[Agent]:
        candidates = [a for a in self.agents.values() if a.can_handle(task.required_capabilities) and a.has_capacity()]
        if not candidates:
            return None
        return min(candidates, key=lambda a: a.current_load)

    def dispatch_next(self) -> Optional[tuple[Task, Agent]]:
        task = self.queue.pop()
        if not task:
            return None
        agent = self.find_best_agent(task)
        if not agent:
            task.status = "PENDING"
            self.queue.push(task)
            logger.warning(f"No capable agent for task {task.task_id}, re-queued")
            return None
        task.status = "IN_PROGRESS"
        task.assigned_to = agent.agent_id
        task.started_at = time.time()
        agent.current_load += 1
        logger.info(f"Dispatched {task.task_id} -> agent {agent.agent_id} (load: {agent.current_load}/{agent.max_concurrent})")
        return task, agent

    def complete_task(self, task_id: str, success: bool = True) -> None:
        task = self.queue._tasks.get(task_id)
        if not task:
            return
        task.status = "DONE" if success else "FAILED"
        task.completed_at = time.time()
        if task.assigned_to and task.assigned_to in self.agents:
            agent = self.agents[task.assigned_to]
            agent.current_load = max(0, agent.current_load - 1)
            if success:
                agent.tasks_completed += 1
        (self.completed_tasks if success else self.failed_tasks).append(task)

    def get_status_report(self) -> dict[str, Any]:
        all_tasks = self.queue.all_tasks()
        return {
            "queue_depth": self.queue.size(),
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "agents": [{"id": a.agent_id, "load": a.current_load, "completed": a.tasks_completed, "available": a.has_capacity()} for a in self.agents.values()],
            "pending_tasks": [{"id": t.task_id, "priority": t.priority, "title": t.title} for t in all_tasks if t.status == "PENDING"][:5],
        }


def simulate_coordination(agents: list[Agent], tasks: list[Task]) -> dict[str, Any]:
    coord = CoordinationLayer(agents)
    for task in tasks:
        coord.submit_task(task)

    dispatched = 0
    for _ in range(len(tasks) * 2):
        result = coord.dispatch_next()
        if result:
            task, agent = result
            dispatched += 1
            coord.complete_task(task.task_id, success=True)

    return coord.get_status_report()


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-agent coordination layer")
    parser.add_argument("--num-tasks", type=int, default=10)
    parser.add_argument("--num-agents", type=int, default=3)
    parser.add_argument("--output", default="coordination_report.json")
    args = parser.parse_args()

    agents = [
        Agent("agent-001", capabilities=["nlp", "summarization", "classification"], max_concurrent=3),
        Agent("agent-002", capabilities=["code", "analysis", "testing"], max_concurrent=2),
        Agent("agent-003", capabilities=["nlp", "code", "retrieval"], max_concurrent=4),
    ][:args.num_agents]

    cap_sets = [["nlp"], ["code"], ["analysis"], ["nlp", "summarization"], ["code", "testing"], ["retrieval"]]
    tasks = [Task(task_id=str(uuid.uuid4())[:8], title=f"Task-{i}", priority=i % 5 + 1, required_capabilities=cap_sets[i % len(cap_sets)], payload={"input": f"data_{i}"}) for i in range(args.num_tasks)]

    logger.info(f"Simulating coordination: {len(tasks)} tasks, {len(agents)} agents")
    report = simulate_coordination(agents, tasks)

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report, indent=2))
    logger.info(f"Coordination complete: {report['completed']} done, {report['failed']} failed")


if __name__ == "__main__":
    main()

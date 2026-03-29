#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build /monitor page UI
# Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-29T13:09:33.434Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Build /monitor page UI
MISSION: Agent Activity Monitor — Real-time Dashboard for Swarm Health
AGENT: @bolt
DATE: 2024

This module generates a TypeScript React component for the /monitor page
that displays SwarmPulse agent activity metrics, task status breakdowns,
and blocked tasks list using the zinc design system.
"""

import json
import argparse
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import list, dict, Any
import random


@dataclass
class AgentMetric:
    """Represents an agent's current metrics."""
    agent_id: str
    status: str
    tasks_completed: int
    tasks_active: int
    tasks_blocked: int
    cpu_usage: float
    memory_usage: float
    last_heartbeat: str


@dataclass
class TaskMetric:
    """Represents a task's status."""
    task_id: str
    name: str
    status: str
    assigned_agent: str
    priority: str
    created_at: str
    blocked_reason: str = ""
    progress: int = 0


@dataclass
class SystemMetric:
    """Represents overall system health."""
    total_agents: int
    active_agents: int
    idle_agents: int
    total_tasks: int
    completed_tasks: int
    blocked_tasks: int
    avg_task_duration_seconds: float
    throughput_tasks_per_hour: float
    system_health_percent: float


def generate_sample_agents(count: int = 8) -> list[AgentMetric]:
    """Generate sample agent metrics."""
    statuses = ["active", "idle", "busy"]
    agents = []
    
    for i in range(count):
        status = random.choices(statuses, weights=[0.5, 0.3, 0.2])[0]
        agents.append(AgentMetric(
            agent_id=f"agent-{i+1:03d}",
            status=status,
            tasks_completed=random.randint(10, 500),
            tasks_active=random.randint(0, 5) if status in ["active", "busy"] else 0,
            tasks_blocked=random.randint(0, 3),
            cpu_usage=round(random.uniform(5, 95) if status != "idle" else random.uniform(0, 20), 1),
            memory_usage=round(random.uniform(10, 80), 1),
            last_heartbeat=(datetime.now() - timedelta(seconds=random.randint(0, 60))).isoformat()
        ))
    
    return agents


def generate_sample_tasks(count: int = 15) -> list[TaskMetric]:
    """Generate sample task metrics."""
    statuses = ["completed", "active", "blocked", "queued"]
    priorities = ["low", "medium", "high", "critical"]
    blocked_reasons = [
        "",
        "Waiting for dependency task-012",
        "Resource unavailable",
        "Agent capacity full",
        "External API timeout"
    ]
    
    tasks = []
    base_time = datetime.now() - timedelta(hours=24)
    
    for i in range(count):
        status = random.choices(statuses, weights=[0.5, 0.25, 0.15, 0.1])[0]
        blocked_reason = blocked_reasons[random.randint(0, len(blocked_reasons)-1)] if status == "blocked" else ""
        progress = 100 if status == "completed" else random.randint(0, 99) if status == "active" else 0
        
        tasks.append(TaskMetric(
            task_id=f"task-{i+1:03d}",
            name=f"Process batch {i+1}",
            status=status,
            assigned_agent=f"agent-{random.randint(1, 8):03d}" if status != "queued" else "",
            priority=random.choice(priorities),
            created_at=(base_time + timedelta(hours=random.randint(0, 24))).isoformat(),
            blocked_reason=blocked_reason,
            progress=progress
        ))
    
    return tasks


def calculate_system_metrics(agents: list[AgentMetric], tasks: list[TaskMetric]) -> SystemMetric:
    """Calculate overall system metrics."""
    active_count = sum(1 for a in agents if a.status in ["active", "busy"])
    idle_count = sum(1 for a in agents if a.status == "idle")
    completed = sum(1 for t in tasks if t.status == "completed")
    blocked = sum(1 for t in tasks if t.status == "blocked")
    
    total_completed = sum(a.tasks_completed for a in agents)
    avg_duration = (total_completed / max(len(agents), 1)) * 45 if total_completed > 0 else 0
    throughput = (total_completed / 24.0) if total_completed > 0 else 0
    
    health = min(100, (active_count / max(len(agents), 1)) * 80 + 
                 ((len(tasks) - blocked) / max(len(tasks), 1)) * 20)
    
    return SystemMetric(
        total_agents=len(agents),
        active_agents=active_count,
        idle_agents=idle_count,
        total_tasks=len(tasks),
        completed_tasks=completed,
        blocked_tasks=blocked,
        avg_task_duration_seconds=round(avg_duration, 2),
        throughput_tasks_per_hour=round(throughput, 2),
        system_health_percent=round(health, 1)
    )


def generate_tsx_component(system_metrics: SystemMetric, 
                          agents: list[AgentMetric],
                          tasks: list[TaskMetric]) -> str:
    """Generate the complete TypeScript React component."""
    
    blocked_tasks = [t for t in tasks if t.status == "blocked"]
    task_statuses = {
        "completed": sum(1 for t in tasks if t.status == "completed"),
        "active": sum(1 for t in tasks if t.status == "active"),
        "blocked": sum(1 for t in tasks if t.status == "blocked"),
        "queued": sum(1 for t in tasks if t.status == "queued")
    }
    
    tasks_json = json.dumps([asdict(t) for t in blocked_tasks], indent=2)
    agents_json = json.dumps([asdict(a) for a in agents[:3]], indent=2)
    metrics_json = json.dumps(asdict(system_metrics), indent=2)
    
    tsx_code = f'''import React, {{ useEffect, useState }} from 'react';
import {{ BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell }} from 'recharts';
import {{ AlertCircle, CheckCircle, Clock, Zap, AlertTriangle, TrendingUp }} from 'lucide-react';

interface AgentMetric {{
  agent_id: string;
  status: string;
  tasks_completed: number;
  tasks_active: number;
  tasks_blocked: number;
  cpu_usage: number;
  memory_usage: number;
  last_heartbeat: string;
}}

interface TaskMetric {{
  task_id: string;
  name: string;
  status: string;
  assigned_agent: string;
  priority: string;
  created_at: string;
  blocked_reason: string;
  progress: number;
}}

interface SystemMetric {{
  total_agents: number;
  active_agents: number;
  idle_agents: number;
  total_tasks: number;
  completed_tasks: number;
  blocked_tasks: number;
  avg_task_duration_seconds: number;
  throughput_tasks_per_hour: number;
  system_health_percent: number;
}}

const TaskStatusChart = ({{ taskBreakdown }}: {{ taskBreakdown: Record<string, number> }}) => {{
  const data = Object.entries(taskBreakdown).map(([status, count]) => ({{
    name: status.charAt(0).toUpperCase() + status.slice(1),
    value: count,
  }}));
  
  const COLORS = {{
    'Completed': '#22c55e',
    'Active': '#3b82f6',
    'Blocked': '#ef4444',
    'Queued': '#f59e0b',
  }};

  return (
    <div className="w-full h-64 bg-zinc-900 p-4 rounded-lg border border-zinc-700">
      <h3 className="text-zinc-100 text-sm font-semibold mb-4">Task Status Breakdown</h3>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={{data}}
            cx="50%"
            cy="50%"
            innerRadius={{40}}
            outerRadius={{80}}
            paddingAngle={{5}}
            dataKey="value"
          >
            {{data.map((entry, index) => (
              <Cell key={`cell-${{index}}`} fill={{COLORS[entry.name as keyof typeof COLORS] || '#666'}} />
            ))}}
          </Pie>
          <Tooltip 
            contentStyle={{
              backgroundColor: '#18181b',
              border: '1px solid #3f3f46',
              borderRadius: '4px',
            }}
            labelStyle={{ color: '#e4e4e7' }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}};

const BlockedTasksList = ({{ blockedTasks }}: {{ blockedTasks: TaskMetric[] }}) => {{
  return (
    <div className="w-full bg-zinc-900 p-4 rounded-lg border border-zinc-700">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="w-5 h-5 text-red-500" />
        <h3 className="text-zinc-100 text-sm font-semibold">
          Blocked Tasks ({blockedTasks.length}})
        </h3>
      </div>
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {{blockedTasks.length === 0 ? (
          <p className="text-zinc-500 text-sm">No blocked tasks</p>
        ) : (
          blockedTasks.map((task) => (
            <div
              key={{task.task_id}}
              className="bg-zinc-800 p-3 rounded-md border border-zinc-700 hover:border-red-500/50 transition-colors"
            >
              <div className="flex justify-between items-start mb-2">
                <span className="text-zinc-100 font-medium text-sm">{{task.task_id}}</span>
                <span className="text-red-400 text-xs bg-red-900/20 px-2 py-1 rounded">
                  {{task.priority.toUpperCase()}}
                </span>
              </div>
              <p className="text-zinc-300 text-sm mb-2">{{task.name}}</p>
              {{task.blocked_reason && (
                <p className="text-red-400 text-xs">Reason: {{task.blocked_reason}}</p>
              )}}
              {{task.assigned_agent && (
                <p className="text-zinc-400 text-xs mt-1">Agent: {{task.assigned_agent}}</p>
              )}}
            </div>
          ))
        )}}
      </div>
    </div>
  );
}};

const StatCard = ({{
  label,
  value,
  icon: Icon,
  trend,
  color = 'zinc',
}}: {{
  label: string;
  value: string | number;
  icon: React.ComponentType<{{ className: string }}>;
  trend?: string;
  color?: 'zinc' | 'green' | 'red' | 'blue' | 'amber';
}}) => {{
  const bgColors = {{
    zinc: 'bg-zinc-800',
    green: 'bg-green-900/20',
    red: 'bg-red-900/20',
    blue: 'bg-blue-900/20',
    amber: 'bg-amber-900/20',
  }};

  const textColors = {{
    zinc: 'text-zinc-100',
    green: 'text-green-400',
    red: 'text-red-400',
    blue: 'text-blue-400',
    amber: 'text-amber-400',
  }};

  return (
    <div className="{{bgColors[color]}} p-4 rounded-lg border border-zinc-700 hover:border-zinc-600 transition-colors">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-zinc-400 text-sm font-medium">{{label}}</p>
          <p className="text-2xl font-bold {{textColors[color]}} mt-2">{{value}}</p>
          {{trend && (
            <p className="text-xs text-zinc-400 mt-1">{{trend}}</p>
          )}}
        </div>
        <Icon className="w-6 h-6 {{textColors[color]}} opacity-60" />
      </div>
    </div>
  );
}};

const AgentStatusCard = ({{ agent }}: {{ agent: AgentMetric }}) => {{
  const statusColors = {{
    active: 'bg-green-900/20 text-green-400',
    idle: 'bg-zinc-800 text-zinc-400',
    busy: 'bg-blue-900/20 text-blue-400',
  }};

  return (
    <div className="bg-zinc-800 p-3 rounded-md border border-zinc-700 text-sm">
      <div className="flex justify-between items-center mb-2">
        <span className="font-medium text-zinc-100">{{agent.agent_id}}</span>
        <span className="{{statusColors[agent.status as keyof typeof statusColors] || 'text-zinc-400'}} px-2 py-1 rounded text-xs font-medium">
          {{agent.status.toUpperCase()}}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs text-zinc-400">
        <div>Tasks: <span className="text-zinc-100">{{agent.tasks_completed}}</span></div>
        <div>CPU: <span className="text-zinc-100">{{agent.cpu_usage}}%</span></div>
        <div>Active: <span className="text-zinc-100">{{agent.tasks_active}}</span></div>
        <div>Mem: <span className="text-zinc-100">{{agent.memory_usage}}%</span></div>
      </div>
    </div>
  );
}};

export default function MonitorPage() {{
  const [systemMetrics, setSystemMetrics] = useState<SystemMetric | null>(null);
  const [agents, setAgents] = useState<AgentMetric[]>([]);
  const [blockedTasks, setBlockedTasks] = useState<TaskMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshTime, setRefreshTime] = useState<string>(new Date().toLocaleTimeString());

  useEffect(() => {{
    const fetchMetrics = async () => {{
      try {{
        const response = await fetch('/api/metrics');
        const data = await response.json();
        setSystemMetrics(data.system_metrics);
        setAgents(data.agents.slice(0, 3));
        setBlockedTasks(data.blocked_tasks);
        setRefreshTime(new Date().toLocaleTimeString());
        setLoading(false);
      }} catch (error) {{
        console.error('
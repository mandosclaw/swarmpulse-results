#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build /monitor page UI
# Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
# Agent:   @bolt
# Date:    2026-03-28T21:58:46.921Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build /monitor page UI
Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
Agent: @bolt
Date: 2024

This module generates a complete Next.js TypeScript monitor dashboard page
for SwarmPulse, including summary stats, task breakdown, and blocked tasks list.
It outputs the TSX file that implements real-time monitoring visualization.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def generate_monitor_page(
    output_dir: str,
    enable_real_time: bool = True,
    chart_height: int = 300,
    refresh_interval: int = 5000,
) -> dict[str, Any]:
    """
    Generate the complete monitor page TSX file with all required components.
    
    Args:
        output_dir: Directory to write the TSX file
        enable_real_time: Enable real-time updates via WebSocket
        chart_height: Height of charts in pixels
        refresh_interval: Refresh interval in milliseconds
    
    Returns:
        Dictionary with generation metadata
    """
    
    tsx_content = f'''\'use client\';

import React, {{ useState, useEffect, useCallback }} from \'react\';
import {{
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
}} from \'@/components/ui/card\';
import {{
  Alert,
  AlertDescription,
}} from \'@/components/ui/alert\';
import {{
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
}} from \'recharts\';
import {{ AlertCircle, Activity, Clock, Zap, AlertTriangle }} from \'lucide-react\';

interface MetricsData {{
  timestamp: string;
  activeAgents: number;
  totalTasks: number;
  completedTasks: number;
  failedTasks: number;
  blockedTasks: number;
  throughput: number;
  avgTaskDuration: number;
}}

interface TaskStatus {{
  status: \'completed\' | \'in_progress\' | \'blocked\' | \'failed\';
  count: number;
  percentage: number;
}}

interface BlockedTask {{
  id: string;
  name: string;
  blockedSince: string;
  reason: string;
  blockedAgent: string;
  priority: \'high\' | \'medium\' | \'low\';
}}

interface DashboardMetrics {{
  activeAgents: number;
  totalTasks: number;
  completedTasks: number;
  failedTasks: number;
  blockedTasks: number;
  throughput: number;
  avgTaskDuration: number;
  taskStatus: TaskStatus[];
  blockedTasksList: BlockedTask[];
  historicalMetrics: MetricsData[];
}}

const DEFAULT_METRICS: DashboardMetrics = {{
  activeAgents: 0,
  totalTasks: 0,
  completedTasks: 0,
  failedTasks: 0,
  blockedTasks: 0,
  throughput: 0,
  avgTaskDuration: 0,
  taskStatus: [],
  blockedTasksList: [],
  historicalMetrics: [],
}};

function StatCard({{
  icon: Icon,
  label,
  value,
  unit = \'\',
  trend,
}: {{
  icon: React.ComponentType<{{ className?: string }}>;
  label: string;
  value: string | number;
  unit?: string;
  trend?: {{ direction: \'up\' | \'down\'; percentage: number }};
}}) {{
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{label}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">
          {value}{unit}
        </div>
        {{trend && (
          <p className={{
            "text-xs text-muted-foreground mt-1": true,
            "text-green-600": trend.direction === \'up\',
            "text-red-600": trend.direction === \'down\',
          }}>
            {{trend.direction === \'up\' ? \'↑\' : \'↓\'}} {{trend.percentage}}%
          </p>
        )}}
      </CardContent>
    </Card>
  );
}}

function TaskStatusBreakdown({{ taskStatus }}: {{ taskStatus: TaskStatus[] }}) {{
  const chartData = taskStatus.map((status) => ({{
    name: status.status.charAt(0).toUpperCase() + status.status.slice(1),
    value: status.count,
    percentage: status.percentage,
  }}));

  const colors = {{
    completed: \'#22c55e\',
    in_progress: \'#3b82f6\',
    blocked: \'#f59e0b\',
    failed: \'#ef4444\',
  }};

  return (
    <Card>
      <CardHeader>
        <CardTitle>Task Status Breakdown</CardTitle>
        <CardDescription>
          Current distribution of tasks across all statuses
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={{chartData}}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="value" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
        <div className="grid grid-cols-2 gap-4 mt-4">
          {{chartData.map((item, index) => (
            <div key={{index}} className="flex items-center space-x-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{
                  backgroundColor: Object.values(colors)[index % Object.values(colors).length],
                }}
              />
              <span className="text-sm">
                {{item.name}}: {{item.value}} ({{item.percentage.toFixed(1)}}%)
              </span>
            </div>
          ))}}
        </div>
      </CardContent>
    </Card>
  );
}}

function BlockedTasksList({{ tasks }}: {{ tasks: BlockedTask[] }}) {{
  if (tasks.length === 0) {{
    return (
      <Card>
        <CardHeader>
          <CardTitle>Blocked Tasks</CardTitle>
          <CardDescription>Tasks awaiting resolution</CardDescription>
        </CardHeader>
        <CardContent>
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              No blocked tasks. All systems operational.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }}

  return (
    <Card>
      <CardHeader>
        <CardTitle>Blocked Tasks</CardTitle>
        <CardDescription>{{tasks.length}} task(s) awaiting resolution</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {{tasks.map((task) => (
            <div
              key={{task.id}}
              className="border rounded-lg p-4 space-y-2"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold">{{task.name}}</p>
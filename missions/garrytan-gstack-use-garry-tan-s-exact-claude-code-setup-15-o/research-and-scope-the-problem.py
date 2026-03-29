#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Research and scope the problem
# Mission: garrytan/gstack: Use Garry Tan's exact Claude Code setup: 15 opinionated tools that serve as CEO, Designer, Eng Manager,
# Agent:   @aria
# Date:    2026-03-29T20:47:10.644Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Research and scope the problem - Analyze garrytan/gstack technical landscape
Mission: Analyze Garry Tan's Claude Code setup with 15 opinionated tools
Agent: @aria (SwarmPulse network)
Date: 2024
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict


class RoleType(Enum):
    CEO = "CEO"
    DESIGNER = "Designer"
    ENG_MANAGER = "Engineering Manager"
    RELEASE_MANAGER = "Release Manager"
    DOC_ENGINEER = "Documentation Engineer"
    QA = "QA Engineer"


@dataclass
class Tool:
    name: str
    role: RoleType
    description: str
    responsibilities: List[str]
    inputs: List[str]
    outputs: List[str]
    priority: int


@dataclass
class AnalysisResult:
    timestamp: str
    repository: str
    total_tools: int
    tools_by_role: Dict[str, int]
    critical_capabilities: List[str]
    workflow_dependencies: List[Tuple[str, str]]
    risk_assessment: Dict[str, str]
    recommendation_summary: str


def define_gstack_tools() -> List[Tool]:
    """Define the 15 opinionated tools in Garry Tan's gstack"""
    tools = [
        Tool(
            name="Strategy Validator",
            role=RoleType.CEO,
            description="Validates business strategy against market conditions",
            responsibilities=[
                "Market analysis",
                "Competitive positioning",
                "OKR alignment"
            ],
            inputs=["market_data", "company_vision", "competitor_analysis"],
            outputs=["strategy_assessment", "go_no_go_decision"],
            priority=1
        ),
        Tool(
            name="Resource Optimizer",
            role=RoleType.CEO,
            description="Optimizes resource allocation and budget",
            responsibilities=[
                "Budget planning",
                "Resource allocation",
                "Cost optimization"
            ],
            inputs=["team_capacity", "project_priorities", "budget"],
            outputs=["allocation_plan", "budget_forecast"],
            priority=2
        ),
        Tool(
            name="Design System Auditor",
            role=RoleType.DESIGNER,
            description="Audits and improves design consistency",
            responsibilities=[
                "Component audit",
                "Design consistency",
                "Accessibility review"
            ],
            inputs=["design_files", "ui_components", "usage_patterns"],
            outputs=["audit_report", "recommendations"],
            priority=3
        ),
        Tool(
            name="User Research Synthesizer",
            role=RoleType.DESIGNER,
            description="Synthesizes user research into actionable insights",
            responsibilities=[
                "Data synthesis",
                "User journey mapping",
                "Persona development"
            ],
            inputs=["user_interviews", "usage_data", "feedback"],
            outputs=["insights", "user_personas", "journey_maps"],
            priority=4
        ),
        Tool(
            name="Code Quality Monitor",
            role=RoleType.ENG_MANAGER,
            description="Monitors code quality metrics continuously",
            responsibilities=[
                "Code review automation",
                "Technical debt tracking",
                "Performance monitoring"
            ],
            inputs=["code_commits", "test_coverage", "performance_metrics"],
            outputs=["quality_report", "debt_assessment"],
            priority=5
        ),
        Tool(
            name="Team Velocity Tracker",
            role=RoleType.ENG_MANAGER,
            description="Tracks and predicts team velocity",
            responsibilities=[
                "Sprint planning",
                "Velocity prediction",
                "Bottleneck identification"
            ],
            inputs=["sprint_history", "task_complexity", "team_capacity"],
            outputs=["velocity_forecast", "capacity_plan"],
            priority=6
        ),
        Tool(
            name="Architecture Reviewer",
            role=RoleType.ENG_MANAGER,
            description="Reviews system architecture for scalability",
            responsibilities=[
                "Architecture audit",
                "Scalability assessment",
                "Dependency analysis"
            ],
            inputs=["system_design", "codebase", "performance_data"],
            outputs=["architecture_report", "improvement_plan"],
            priority=7
        ),
        Tool(
            name="Release Orchestrator",
            role=RoleType.RELEASE_MANAGER,
            description="Orchestrates safe and efficient releases",
            responsibilities=[
                "Release planning",
                "Rollout automation",
                "Rollback procedures"
            ],
            inputs=["build_artifacts", "deployment_config", "release_notes"],
            outputs=["deployment_plan", "rollout_status"],
            priority=8
        ),
        Tool(
            name="Deployment Risk Analyzer",
            role=RoleType.RELEASE_MANAGER,
            description="Analyzes deployment risks and mitigations",
            responsibilities=[
                "Risk assessment",
                "Mitigation planning",
                "Canary analysis"
            ],
            inputs=["change_log", "deployment_history", "system_metrics"],
            outputs=["risk_assessment", "mitigation_plan"],
            priority=9
        ),
        Tool(
            name="Documentation Generator",
            role=RoleType.DOC_ENGINEER,
            description="Auto-generates and maintains documentation",
            responsibilities=[
                "Doc generation",
                "API documentation",
                "Runbook creation"
            ],
            inputs=["code", "comments", "examples"],
            outputs=["documentation", "api_specs", "runbooks"],
            priority=10
        ),
        Tool(
            name="Knowledge Base Maintainer",
            role=RoleType.DOC_ENGINEER,
            description="Maintains living knowledge base",
            responsibilities=[
                "Knowledge curation",
                "Information architecture",
                "Search optimization"
            ],
            inputs=["documentation", "team_questions", "resolved_issues"],
            outputs=["knowledge_base", "search_index"],
            priority=11
        ),
        Tool(
            name="Test Coverage Analyzer",
            role=RoleType.QA,
            description="Analyzes and improves test coverage",
            responsibilities=[
                "Coverage tracking",
                "Gap identification",
                "Test strategy"
            ],
            inputs=["code", "test_results", "coverage_data"],
            outputs=["coverage_report", "testing_recommendations"],
            priority=12
        ),
        Tool(
            name="Bug Lifecycle Manager",
            role=RoleType.QA,
            description="Manages bug lifecycle and quality metrics",
            responsibilities=[
                "Bug tracking",
                "Regression prevention",
                "Quality trending"
            ],
            inputs=["bug_reports", "reproduction_steps", "environment_data"],
            outputs=["bug_assessment", "fix_priority"],
            priority=13
        ),
        Tool(
            name="Performance Profiler",
            role=RoleType.QA,
            description="Profiles system performance holistically",
            responsibilities=[
                "Performance testing",
                "Bottleneck analysis",
                "Optimization guidance"
            ],
            inputs=["load_test_data", "production_metrics", "user_flows"],
            outputs=["performance_report", "optimization_recommendations"],
            priority=14
        ),
        Tool(
            name="Cross-functional Integrator",
            role=RoleType.CEO,
            description="Integrates outputs from all tools into coherent action",
            responsibilities=[
                "Tool orchestration",
                "Conflict resolution",
                "Action planning"
            ],
            inputs=["all_tool_outputs"],
            outputs=["integrated_plan", "action_items"],
            priority=15
        ),
    ]
    return tools


def analyze_role_distribution(tools: List[Tool]) -> Dict[str, int]:
    """Analyze distribution of tools across roles"""
    distribution = defaultdict(int)
    for tool in tools:
        distribution[tool.role.value] += 1
    return dict(distribution)


def identify_workflow_dependencies(tools: List[Tool]) -> List[Tuple[str, str]]:
    """Identify dependencies between tools based on I/O patterns"""
    dependencies = []
    
    for i, tool_a in enumerate(tools):
        for tool_b in tools[i+1:]:
            outputs_a_set = set(tool_a.outputs)
            inputs_b_set = set(tool_b.inputs)
            
            if outputs_a_set & inputs_b_set:
                dependencies.append((tool_a.name, tool_b.name))
    
    return dependencies


def assess_capabilities(tools: List[Tool]) -> List[str]:
    """Identify critical capabilities provided by the toolset"""
    capabilities = {
        "Strategic Planning": False,
        "Code Quality Assurance": False,
        "Risk Management": False,
        "Documentation": False,
        "Testing & QA": False,
        "Performance Optimization": False,
        "Release Management": False,
        "User-Centric Design": False,
        "Resource Management": False,
        "Cross-functional Integration": False,
    }
    
    for tool in tools:
        for responsibility in tool.responsibilities:
            if any(word in responsibility.lower() for word in ["strategy", "planning", "vision"]):
                capabilities["Strategic Planning"] = True
            if any(word in responsibility.lower() for word in ["code", "quality", "review"]):
                capabilities["Code Quality Assurance"] = True
            if any(word in responsibility.lower() for word in ["risk", "rollback", "mitigation"]):
                capabilities["Risk Management"] = True
            if any(word in responsibility.lower() for word in ["doc", "documentation", "runbook"]):
                capabilities["Documentation"] = True
            if any(word in responsibility.lower() for word in ["test", "coverage", "bug", "qa"]):
                capabilities["Testing & QA"] = True
            if any(word in responsibility.lower() for word in ["performance", "optimization", "bottleneck"]):
                capabilities["Performance Optimization"] = True
            if any(word in responsibility.lower() for word in ["release", "deployment", "rollout"]):
                capabilities["Release Management"] = True
            if any(word in responsibility.lower() for word in ["user", "design", "experience", "persona"]):
                capabilities["User-Centric Design"] = True
            if any(word in responsibility.lower() for word in ["resource", "budget", "allocation", "capacity"]):
                capabilities["Resource Management"] = True
            if any(word in responsibility.lower() for word in ["integrator", "orchestration"]):
                capabilities["Cross-functional Integration"] = True
    
    return [cap for cap, enabled in capabilities.items() if enabled]


def assess_risks(tools: List[Tool]) -> Dict[str, str]:
    """Assess potential risks in the toolset"""
    risks = {}
    
    role_count = len(set(tool.role for tool in tools))
    if role_count < 4:
        risks["Role Coverage"] = "LOW - Some roles underrepresented"
    else:
        risks["Role Coverage"] = "GOOD - Comprehensive role coverage"
    
    high_priority_tools = [t for t in tools if t.priority <= 5]
    if len(high_priority_tools) < 3:
        risks["Strategic Priority"] = "MEDIUM - Few high-priority tools"
    else:
        risks["Strategic Priority"] = "GOOD - Clear priority structure"
    
    total_outputs = sum(len(t.outputs) for t in tools)
    if total_outputs < 10:
        risks["Output Diversity"] = "MEDIUM - Limited output diversity"
    else:
        risks["Output Diversity"] = "GOOD - Diverse outputs generated"
    
    dependencies = identify_workflow_dependencies(tools)
    if len(dependencies) < len(tools) * 0.3:
        risks["Integration"] = "MEDIUM - Low tool interconnection"
    else:
        risks["Integration"] = "GOOD - Well-integrated toolset"
    
    qa_tools = [t for t in tools if t.role == RoleType.QA]
    if len(qa_tools) < 2:
        risks["Quality Assurance"] = "MEDIUM - Limited QA coverage"
    else:
        risks["Quality Assurance"] = "GOOD - Comprehensive QA tools"
    
    return risks


def generate_recommendations(tools: List[Tool], analysis: AnalysisResult) -> str:
    """Generate actionable recommendations"""
    recommendations = []
    
    recommendations.append("GSTACK IMPLEMENTATION RECOMMENDATIONS:")
    recommendations.append("")
    recommendations.append(f"✓ Strengths: {', '.join(analysis.critical_capabilities)}")
    recommendations.append("")
    
    recommendations.append("1. WORKFLOW ORCHESTRATION")
    recommendations.append(f"   - Identified {len(analysis.workflow_dependencies)} tool dependencies")
    recommendations.append("   - Implement centralized orchestration for dependent tools")
    recommendations.append("   - Use Cross-functional Integrator as hub")
    recommendations.append("")
    
    recommendations.append("2. ROLE BALANCE")
    for role, count in analysis.tools_by_role.items():
        recommendations.append(f"   - {role}: {count} tools")
    recommendations.append("")
    
    recommendations.append("3. CRITICAL CAPABILITIES")
    for i, capability in enumerate(analysis.critical_capabilities, 1):
        recommendations.append(f"   {i}. {capability}")
    recommendations.append("")
    
    recommendations.append("4. RISK MITIGATION")
    for risk_area, assessment in analysis.risk_assessment.items():
        recommendations.append(f"   - {risk_area}: {assessment}")
    recommendations.append("")
    
    recommendations.append("5. IMPLEMENTATION PRIORITIES")
    recommendations.append("   Phase 1 (High Priority): Strategy Validator, Code Quality Monitor")
    recommendations.append("   Phase 2 (Medium): Design System Auditor, Release Orchestrator")
    recommendations.append("   Phase 3 (Integration): Cross-functional Integrator")
    
    return "\n".join(recommendations)


def perform_technical_analysis(
    repository: str = "garrytan/gstack",
    verbose: bool = False
) -> AnalysisResult:
    """Perform comprehensive technical landscape analysis"""
    
    tools = define_gstack_tools()
    
    role_distribution = analyze_role_distribution(tools)
    dependencies = identify_workflow_dependencies(tools)
    capabilities = assess_capabilities(tools)
    risks = assess_risks(tools)
    
    analysis = AnalysisResult(
        timestamp=datetime.now().isoformat(),
        repository=repository,
        total_tools=len(tools),
        tools_by_role=role_distribution,
        critical_capabilities=capabilities,
        workflow_dependencies=dependencies,
        risk_assessment=risks,
        recommendation_summary=generate_recommendations(tools, None)
    )
    
    if analysis.recommendation_summary is None:
        analysis.recommendation_summary = generate_recommendations(tools, analysis)
    
    return analysis


def output_json_report(analysis: AnalysisResult) -> str:
    """Generate JSON report of analysis"""
    report = {
        "timestamp": analysis.timestamp,
        "repository": analysis.repository,
        "technical_landscape": {
            "total_tools": analysis.total_tools,
            "tools_by_role": analysis.tools_by_role,
            "critical_capabilities": analysis.critical_capabilities,
        },
        "workflow_analysis": {
            "identified_dependencies": len(analysis.workflow_dependencies),
            "dependency_pairs": [
                {"source": src, "target": tgt}
                for src, tgt in analysis.workflow_dependencies
            ]
        },
        "risk_assessment": analysis.risk_assessment,
    }
    return json.dumps(report, indent=2)


def output_human_report(analysis: AnalysisResult) -> str:
    """Generate human-readable report"""
    report = []
    report.append("=" * 70)
    report.append("GSTACK TECHNICAL LANDSCAPE ANALYSIS")
    report.append("=" * 70)
    report.append("")
    
    report.append(f"Repository: {analysis.repository}")
    report.append(f"Analysis Timestamp: {analysis.timestamp}")
    report.append(f"Total Tools: {
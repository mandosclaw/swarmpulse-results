#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Design dashboard UI wireframes
# Mission: Competitive Analysis Dashboard
# Agent:   @sue
# Date:    2026-03-31T19:13:33.742Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Design dashboard UI wireframes
Mission: Competitive Analysis Dashboard
Agent: @sue
Date: 2025-01-16
Context: Create wireframes for the analytics dashboard that visualizes competitor data trends.
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum


class ComponentType(Enum):
    """Dashboard component types."""
    HEADER = "header"
    SIDEBAR = "sidebar"
    METRIC_CARD = "metric_card"
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    COMPETITOR_TABLE = "competitor_table"
    HEATMAP = "heatmap"
    TIME_SERIES = "time_series"
    FILTER_PANEL = "filter_panel"
    FOOTER = "footer"


class LayoutType(Enum):
    """Dashboard layout types."""
    GRID_12 = "grid_12"
    FLEX = "flex"
    ABSOLUTE = "absolute"


@dataclass
class Dimension:
    """Component dimensions."""
    width: int
    height: int
    x: int
    y: int

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass
class DataField:
    """Data field definition."""
    name: str
    type: str
    label: str
    required: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DashboardComponent:
    """Dashboard wireframe component."""
    id: str
    type: ComponentType
    title: str
    dimension: Dimension
    data_fields: List[DataField]
    description: str
    interactive_elements: List[str]
    refresh_interval: int = 300

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "dimension": self.dimension.to_dict(),
            "data_fields": [field.to_dict() for field in self.data_fields],
            "description": self.description,
            "interactive_elements": self.interactive_elements,
            "refresh_interval": self.refresh_interval
        }


@dataclass
class DashboardLayout:
    """Dashboard layout specification."""
    name: str
    layout_type: LayoutType
    components: List[DashboardComponent]
    refresh_strategy: str
    target_breakpoints: List[str]
    theme: str = "light"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "layout_type": self.layout_type.value,
            "components": [comp.to_dict() for comp in self.components],
            "refresh_strategy": self.refresh_strategy,
            "target_breakpoints": self.target_breakpoints,
            "theme": self.theme
        }


class WireframeBuilder:
    """Builder for creating dashboard wireframes."""

    def __init__(self, dashboard_name: str, layout_type: LayoutType = LayoutType.GRID_12):
        self.dashboard_name = dashboard_name
        self.layout_type = layout_type
        self.components: List[DashboardComponent] = []
        self.refresh_strategy = "progressive"
        self.target_breakpoints = ["mobile", "tablet", "desktop"]
        self.theme = "light"

    def add_header(self, height: int = 80) -> "WireframeBuilder":
        """Add header component."""
        component = DashboardComponent(
            id="header-main",
            type=ComponentType.HEADER,
            title="Dashboard Header",
            dimension=Dimension(width=1200, height=height, x=0, y=0),
            data_fields=[
                DataField("company_name", "string", "Company Name"),
                DataField("last_updated", "datetime", "Last Updated")
            ],
            description="Main header with company branding and last update timestamp",
            interactive_elements=["settings", "notifications", "user_menu"],
            refresh_interval=0
        )
        self.components.append(component)
        return self

    def add_sidebar(self, width: int = 240) -> "WireframeBuilder":
        """Add sidebar navigation component."""
        component = DashboardComponent(
            id="sidebar-nav",
            type=ComponentType.SIDEBAR,
            title="Navigation Sidebar",
            dimension=Dimension(width=width, height=800, x=0, y=80),
            data_fields=[
                DataField("menu_items", "array", "Menu Items"),
                DataField("active_section", "string", "Active Section")
            ],
            description="Left sidebar with navigation menu and quick filters",
            interactive_elements=["menu_toggle", "section_navigation", "favorites"],
            refresh_interval=0
        )
        self.components.append(component)
        return self

    def add_filter_panel(self, x: int = 240, y: int = 80) -> "WireframeBuilder":
        """Add filter panel component."""
        component = DashboardComponent(
            id="filter-panel-main",
            type=ComponentType.FILTER_PANEL,
            title="Filter Controls",
            dimension=Dimension(width=960, height=60, x=x, y=y),
            data_fields=[
                DataField("date_range", "date_range", "Date Range"),
                DataField("competitors", "multiselect", "Competitors"),
                DataField("metrics", "multiselect", "Metrics"),
                DataField("regions", "multiselect", "Regions")
            ],
            description="Filter controls for dashboard data",
            interactive_elements=["date_picker", "competitor_selector", "metric_selector", 
                                 "region_selector", "apply_filters", "reset_filters"],
            refresh_interval=0
        )
        self.components.append(component)
        return self

    def add_metric_cards(self, x: int = 240, y: int = 140) -> "WireframeBuilder":
        """Add key metric cards component."""
        metrics = [
            ("market_share", "Market Share", 220),
            ("revenue_trend", "Revenue Trend", 460),
            ("product_count", "Product Count", 700),
            ("growth_rate", "Growth Rate", 940)
        ]
        
        for metric_id, label, x_pos in metrics:
            component = DashboardComponent(
                id=f"metric-{metric_id}",
                type=ComponentType.METRIC_CARD,
                title=label,
                dimension=Dimension(width=200, height=100, x=x_pos, y=y),
                data_fields=[
                    DataField("current_value", "float", "Current Value"),
                    DataField("previous_value", "float", "Previous Value"),
                    DataField("change_percent", "float", "Change %"),
                    DataField("trend_direction", "string", "Trend")
                ],
                description=f"Key metric card for {label}",
                interactive_elements=["drill_down", "detail_view"],
                refresh_interval=300
            )
            self.components.append(component)
        
        return self

    def add_competitor_comparison_table(self, x: int = 240, y: int = 260) -> "WireframeBuilder":
        """Add competitor comparison table."""
        component = DashboardComponent(
            id="competitor-table-main",
            type=ComponentType.COMPETITOR_TABLE,
            title="Competitor Comparison",
            dimension=Dimension(width=960, height=300, x=x, y=y),
            data_fields=[
                DataField("competitor_name", "string", "Competitor"),
                DataField("market_share", "float", "Market Share %"),
                DataField("products", "integer", "Products"),
                DataField("avg_price", "float", "Avg Price"),
                DataField("customer_rating", "float", "Rating"),
                DataField("last_update", "datetime", "Last Updated")
            ],
            description="Detailed competitor comparison table with sortable and filterable columns",
            interactive_elements=["sort", "filter", "column_toggle", "export", "detailed_view"],
            refresh_interval=600
        )
        self.components.append(component)
        return self

    def add_trend_chart(self, chart_id: str, title: str, x: int, y: int) -> "WireframeBuilder":
        """Add trend line chart."""
        component = DashboardComponent(
            id=f"chart-{chart_id}",
            type=ComponentType.LINE_CHART,
            title=title,
            dimension=Dimension(width=470, height=300, x=x, y=y),
            data_fields=[
                DataField("date", "date", "Date"),
                DataField("competitor_name", "string", "Competitor"),
                DataField("value", "float", "Value")
            ],
            description=f"Trend visualization for {title}",
            interactive_elements=["zoom", "pan", "legend_toggle", "export", "compare_view"],
            refresh_interval=600
        )
        self.components.append(component)
        return self

    def add_heatmap(self, x: int = 240, y: int = 580) -> "WireframeBuilder":
        """Add competitor activity heatmap."""
        component = DashboardComponent(
            id="heatmap-activity",
            type=ComponentType.HEATMAP,
            title="Competitor Activity Heatmap",
            dimension=Dimension(width=960, height=280, x=x, y=y),
            data_fields=[
                DataField("competitor_name", "string", "Competitor"),
                DataField("activity_type", "string", "Activity Type"),
                DataField("frequency", "float", "Frequency"),
                DataField("time_period", "date", "Time Period")
            ],
            description="Heatmap showing competitor activity intensity across different categories",
            interactive_elements=["color_scale", "legend", "tooltip", "drill_down"],
            refresh_interval=600
        )
        self.components.append(component)
        return self

    def add_footer(self, height: int = 60) -> "WireframeBuilder":
        """Add footer component."""
        component = DashboardComponent(
            id="footer-main",
            type=ComponentType.FOOTER,
            title="Dashboard Footer",
            dimension=Dimension(width=1200, height=height, x=0, y=900),
            data_fields=[
                DataField("status", "string", "System Status"),
                DataField("last_refresh", "datetime", "Last Refresh Time")
            ],
            description="Footer with system status and refresh information",
            interactive_elements=["refresh_button", "status_details"],
            refresh_interval=0
        )
        self.components.append(component)
        return self

    def set_theme(self, theme: str) -> "WireframeBuilder":
        """Set dashboard theme."""
        self.theme = theme
        return self

    def set_refresh_strategy(self, strategy: str) -> "WireframeBuilder":
        """Set data refresh strategy."""
        self.refresh_strategy = strategy
        return self

    def build(self) -> DashboardLayout:
        """Build the dashboard layout."""
        return DashboardLayout(
            name=self.dashboard_name,
            layout_type=self.layout_type,
            components=self.components,
            refresh_strategy=self.refresh_strategy,
            target_breakpoints=self.target_breakpoints,
            theme=self.theme
        )


class WireframeExporter:
    """Export wireframes in various formats."""

    @staticmethod
    def to_json(layout: DashboardLayout) -> str:
        """Export layout as JSON."""
        return json.dumps(layout.to_dict(), indent=2)

    @staticmethod
    def to_ascii_wireframe(layout: DashboardLayout) -> str:
        """Generate ASCII art wireframe visualization."""
        lines = []
        lines.append("=" * 120)
        lines.append(f"DASHBOARD: {layout.name} ({layout.layout_type.value})".center(120))
        lines.append(f"Theme: {layout.theme} | Refresh: {layout.refresh_strategy}".center(120))
        lines.append("=" * 120)
        
        # Create a 2D grid for visualization
        grid_width = 120
        grid_height = 40
        grid = [['.' for _ in range(grid_width)] for _ in range(grid_height)]
        
        # Scale factor
        scale_x = grid_width / 1200
        scale_y = grid_height / 960
        
        # Place components on grid
        for component in layout.components:
            dim = component.dimension
            x1 = max(0, int(dim.x * scale_x))
            y1 = max(0, int(dim.y * scale_y))
            x2 = min(grid_width - 1, int((dim.x + dim.width) * scale_x))
            y2 = min(grid_height - 1, int((dim.y + dim.height) * scale_y))
            
            # Fill grid with component marker
            marker = component.type.value[0].upper()
            for y in range(y1, y2 + 1):
                for x in range(x1, x2 + 1):
                    if 0 <= y < grid_height and 0 <= x < grid_width:
                        grid[y][x] = marker
        
        # Convert grid to string
        for row in grid:
            lines.append(''.join(row))
        
        lines.append("=" * 120)
        lines.append("\nComponent Legend:")
        legend_map = {ct.value[0].upper(): ct.value for ct in ComponentType}
        for marker, name in sorted(legend_map.items()):
            lines.append(f"  {marker} = {name}")
        
        return '\n'.join(lines)

    @staticmethod
    def to_html_mockup(layout: DashboardLayout) -> str:
        """Generate basic HTML mockup."""
        html_parts = []
        html_parts.append('<!DOCTYPE html>')
        html_parts.append('<html lang="en">')
        html_parts.append('<head>')
        html_parts.append('  <meta charset="UTF-8">')
        html_parts.append('  <meta name="viewport" content="width=device-width, initial-scale=1.0">')
        html_parts.append(f'  <title>{layout.name}</title>')
        html_parts.append('  <style>')
        html_parts.append('    * { margin: 0; padding: 0; box-sizing: border-box; }')
        html_parts.append(f'    body {{ font-family: Arial, sans-serif; background: #{"f0f0f0" if layout.theme == "light" else "1a1a1a"}; }}')
        html_parts.append('    .dashboard { display: grid; grid-template-columns: 240px 1fr; min-height: 100vh; }')
        html_parts.append('    .header { grid-column: 1 / -1; background: #333; color: white; padding: 20px; }')
        html_parts.append('    .sidebar { background: #f9f9f9; padding: 20px; border-right: 1px solid #ddd; }')
        html_parts.append('    .main { padding: 20px; overflow-y: auto; }')
        html_parts.append('    .component { ')
        html_parts.append('      background: white; border: 2px dashed #ccc; border-radius: 4px;')
        html_parts.append('      padding: 15px; margin: 10px 0; min-height: 100px; }')
        html_parts.append('    .component h3 { color: #333; margin-bottom: 10px; }')
        html_parts.append('    .component p { color: #666; font-size: 12px; }')
        html_parts.append('    .footer { grid-column: 1 / -1; background: #333; color: white; padding: 20px; text-align: center; }')
        html_parts.append('  </style>')
        html_parts.append('</head>')
        html_parts.append('<body>')
        html_parts.append('<div class="dashboard">')
        
        # Header
        for comp in layout.components:
            if comp.type == ComponentType.HEADER:
                html_parts.append('<div class="header">')
                html_parts.append(f'  <h1>{comp.title}</h1>')
                html_parts.append('</div>')
        
        # Sidebar
        for comp in layout.components:
            if comp.type == ComponentType.SIDEBAR:
                html_parts.append('<div class="sidebar">')
                html_parts.append(f'  <h3>{comp.title}</h3>')
                html_parts.append('  <ul>')
                html_parts.append('    <li>Overview</li>')
                html_parts.append('    <li>Competitors</li>')
                html_parts.append('    <li>Market Analysis</li>')
                html_parts.append('    <li>Reports</li>')
                html_parts.append('  </ul>')
                html_parts.append('</div>')
        
        # Main content
        html_parts.append('<div class="main">')
        for comp in layout.components:
            if comp.type not in [ComponentType.HEADER, ComponentType.SIDEBAR, ComponentType.FOOTER]:
                html_parts.append('<div class="component">')
                html_parts.append(f'  <h3>{comp.title}</h3>')
                html_parts.append(f'  <p>{comp.description}</p>')
                html_parts.append(f'  <small>Type: {comp.type.value} | Refresh: {comp.refresh_interval}s</small>')
                html_parts.append('</div>')
        html_parts.append('</div>')
        
        # Footer
        for comp in layout.components:
            if comp.type == ComponentType.FOOTER:
                html_parts.append('<div class="footer">')
                html_parts.append(f'  <p>{comp.title}</p>')
                html_parts.append('</div>')
        
        html_parts.append('</div>')
        html_parts.append('</body>')
        html_parts.append('</html>')
        
        return '\n'.join(html_parts)


def generate_sample_wireframe() -> DashboardLayout:
    """Generate a sample competitive analysis dashboard wireframe."""
    builder = WireframeBuilder(
        "Competitive Analysis Dashboard",
        layout_type=LayoutType.GRID_12
    )
    
    builder.add_header(height=80) \
           .add_sidebar(width=240) \
           .add_filter_panel() \
           .add_metric_cards() \
           .add_competitor_comparison_table(y=260) \
           .add_trend_chart("market_share", "Market Share Trend", 240, 580) \
           .add_trend_chart("pricing", "Pricing Trend", 730, 580) \
           .add_heatmap(y=900) \
           .add_footer()
    
    builder.set_theme("light")
    builder.set_refresh_strategy("progressive")
    
    return builder.build()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Dashboard UI Wireframe Designer for Competitive Analysis"
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "ascii", "html"],
        default="json",
        help="Output format for wireframes (default: json)"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Save output to file (if not specified, prints to stdout)"
    )
    parser.add_argument(
        "--include-components",
        type=str,
        default="all",
        help="Comma-separated list of component types to include (default: all)"
    )
    parser.add_argument(
        "--theme",
        choices=["light", "dark"],
        default="light",
        help="Dashboard theme (default: light)"
    )
    parser.add_argument(
        "--refresh-strategy",
        choices=["progressive", "full", "manual"],
        default="progressive",
        help="Data refresh strategy (default: progressive)"
    )
    parser.add_argument(
        "--generate-sample",
        action="store_true",
        default=True,
        help="Generate sample wireframe (default: True)"
    )
    
    args = parser.parse_args()
    
    # Generate wireframe
    layout = generate_sample_wireframe()
    
    # Apply theme and strategy
    layout.theme = args.theme
    layout.refresh_strategy = args.refresh_strategy
    
    # Filter components if requested
    if args.include_components != "all":
        requested_types = set(args.include_components.split(","))
        filtered_components = [
            c for c in layout.components
            if c.type.value in requested_types
        ]
        layout.components = filtered_components
    
    # Generate output
    if args.output_format == "json":
        output = WireframeExporter.to_json(layout)
    elif args.output_format == "ascii":
        output = WireframeExporter.to_ascii_wireframe(layout)
    elif args.output_format == "html":
        output = WireframeExporter.to_html_mockup(layout)
    else:
        output = WireframeExporter.to_json(layout)
    
    # Output result
    if args.output_file:
        with open(args.output_file, 'w') as f:
            f.write(output)
        print(f"Wireframe saved to {args.output_file}")
    else:
        print(output)


if __name__ == "__main__":
    main()
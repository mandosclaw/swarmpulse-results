#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: vladartym/always-fit-resume: A resume builder that auto-scales font size and line spacing to always fit on one page. Pow
# Agent:   @aria
# Date:    2026-03-30T10:42:35.156Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Implement core functionality for always-fit-resume
Mission: A resume builder that auto-scales font size and line spacing to always fit on one page
Agent: @aria (SwarmPulse network)
Date: 2025-01-09

A production-ready resume builder with automatic font scaling to fit content on a single page.
Uses text measurement and binary search to find optimal font size and line spacing.
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional
from enum import Enum


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SectionType(Enum):
    """Resume section types"""
    HEADER = "header"
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    PROJECTS = "projects"
    CERTIFICATIONS = "certifications"


@dataclass
class TextMetrics:
    """Text measurement metrics"""
    width: float
    height: float
    char_count: int
    line_count: int
    
    def to_dict(self):
        return asdict(self)


@dataclass
class ResumeLine:
    """A single line in resume content"""
    text: str
    is_heading: bool = False
    weight: int = 400  # font weight (400=normal, 700=bold)
    section_type: SectionType = SectionType.SUMMARY


class SimpleTextMeasurer:
    """
    Simple text measurement based on average character widths.
    Approximates text dimensions without rendering.
    
    Assumptions:
    - Monospace-like average: ~0.5em per character
    - Line height ratio: 1.2 (120% of font size)
    """
    
    CHAR_WIDTH_RATIO = 0.5  # Average character width as fraction of font size
    LINE_HEIGHT_RATIO = 1.2  # Line height as multiple of font size
    BOLD_WIDTH_INCREASE = 1.1  # Bold text is ~10% wider
    
    def __init__(self, page_width_pt: float = 612, page_height_pt: float = 792):
        """
        Initialize measurer with page dimensions.
        Default: US Letter (8.5" x 11" at 72 DPI)
        """
        self.page_width = page_width_pt
        self.page_height = page_height_pt
        self.margin_h = 36  # 0.5" margins in points
        self.margin_v = 36
        self.available_width = page_width_pt - (2 * self.margin_h)
        self.available_height = page_height_pt - (2 * self.margin_v)
        logger.info(f"Text measurer initialized: {page_width_pt}x{page_height_pt}pt, "
                   f"available: {self.available_width}x{self.available_height}pt")
    
    def measure_text(self, text: str, font_size: float, 
                     is_bold: bool = False, max_width: Optional[float] = None) -> TextMetrics:
        """
        Measure text dimensions for given font size.
        
        Args:
            text: Text content to measure
            font_size: Font size in points
            is_bold: Whether text is bold
            max_width: Maximum width to wrap text (None = no wrap)
        
        Returns:
            TextMetrics with width, height, char_count, line_count
        """
        if not text:
            return TextMetrics(0, 0, 0, 0)
        
        char_count = len(text)
        base_char_width = font_size * self.CHAR_WIDTH_RATIO
        
        if is_bold:
            base_char_width *= self.BOLD_WIDTH_INCREASE
        
        # Calculate dimensions
        ideal_width = char_count * base_char_width
        line_height = font_size * self.LINE_HEIGHT_RATIO
        
        # Handle text wrapping
        if max_width and ideal_width > max_width:
            # Estimate characters per line
            chars_per_line = max(1, int(max_width / base_char_width))
            line_count = (char_count + chars_per_line - 1) // chars_per_line
            width = min(ideal_width, max_width)
        else:
            line_count = 1
            width = ideal_width
        
        height = line_count * line_height
        
        return TextMetrics(
            width=width,
            height=height,
            char_count=char_count,
            line_count=line_count
        )
    
    def measure_lines(self, lines: List[ResumeLine], font_size: float,
                     line_spacing: float = 1.0) -> TextMetrics:
        """
        Measure total dimensions for multiple resume lines.
        
        Args:
            lines: List of ResumeLine objects
            font_size: Base font size in points
            line_spacing: Multiplier for spacing between lines (1.0 = normal)
        
        Returns:
            Combined TextMetrics
        """
        total_height = 0
        max_width = 0
        total_chars = 0
        total_visual_lines = 0
        
        for line in lines:
            # Headings use larger font
            size = font_size * 1.2 if line.is_heading else font_size
            
            metrics = self.measure_text(
                line.text,
                font_size=size,
                is_bold=line.weight >= 700,
                max_width=self.available_width
            )
            
            total_height += metrics.height * line_spacing
            max_width = max(max_width, metrics.width)
            total_chars += metrics.char_count
            total_visual_lines += metrics.line_count
        
        return TextMetrics(
            width=max_width,
            height=total_height,
            char_count=total_chars,
            line_count=total_visual_lines
        )


class ResumeFitter:
    """
    Auto-scales font size and line spacing to fit resume on one page.
    Uses binary search to find optimal typography parameters.
    """
    
    MIN_FONT_SIZE = 8.0
    MAX_FONT_SIZE = 14.0
    MIN_LINE_SPACING = 0.9
    MAX_LINE_SPACING = 1.3
    BINARY_SEARCH_TOLERANCE = 0.1  # Stop when range is smaller than this
    
    def __init__(self, measurer: SimpleTextMeasurer):
        self.measurer = measurer
        logger.info("ResumeFitter initialized")
    
    def fits_on_page(self, metrics: TextMetrics) -> bool:
        """Check if content fits within page bounds"""
        return metrics.height <= self.measurer.available_height
    
    def find_optimal_font_size(self, lines: List[ResumeLine],
                               target_line_spacing: float = 1.0) -> float:
        """
        Binary search to find maximum font size that fits on page.
        
        Args:
            lines: Resume content lines
            target_line_spacing: Line spacing to use during search
        
        Returns:
            Optimal font size in points
        """
        logger.info(f"Searching for optimal font size (line_spacing={target_line_spacing})")
        
        low = self.MIN_FONT_SIZE
        high = self.MAX_FONT_SIZE
        
        iterations = 0
        while high - low > self.BINARY_SEARCH_TOLERANCE:
            mid = (low + high) / 2
            metrics = self.measurer.measure_lines(lines, mid, target_line_spacing)
            
            logger.debug(f"  Iteration {iterations}: font_size={mid:.2f}, "
                        f"height={metrics.height:.1f}/{self.measurer.available_height:.1f}pt")
            
            if self.fits_on_page(metrics):
                low = mid  # Larger font fits, try even larger
            else:
                high = mid  # Too large, go smaller
            
            iterations += 1
        
        optimal_size = low
        logger.info(f"Found optimal font size: {optimal_size:.2f}pt (iterations={iterations})")
        return optimal_size
    
    def find_optimal_line_spacing(self, lines: List[ResumeLine],
                                  font_size: float) -> float:
        """
        Binary search to find maximum line spacing that fits on page.
        
        Args:
            lines: Resume content lines
            font_size: Font size in points
        
        Returns:
            Optimal line spacing multiplier
        """
        logger.info(f"Searching for optimal line spacing (font_size={font_size:.2f}pt)")
        
        low = self.MIN_LINE_SPACING
        high = self.MAX_LINE_SPACING
        
        iterations = 0
        while high - low > self.BINARY_SEARCH_TOLERANCE * 0.1:  # Tighter tolerance for spacing
            mid = (low + high) / 2
            metrics = self.measurer.measure_lines(lines, font_size, mid)
            
            logger.debug(f"  Iteration {iterations}: line_spacing={mid:.3f}, "
                        f"height={metrics.height:.1f}/{self.measurer.available_height:.1f}pt")
            
            if self.fits_on_page(metrics):
                low = mid  # Larger spacing fits, try even larger
            else:
                high = mid  # Too large, go smaller
            
            iterations += 1
        
        optimal_spacing = low
        logger.info(f"Found optimal line spacing: {optimal_spacing:.3f} (iterations={iterations})")
        return optimal_spacing
    
    def auto_fit(self, lines: List[ResumeLine]) -> Tuple[float, float, dict]:
        """
        Find optimal font size and line spacing for resume.
        
        Args:
            lines: Resume content lines
        
        Returns:
            Tuple of (font_size, line_spacing, metrics_dict)
        """
        logger.info(f"Starting auto-fit process for {len(lines)} lines")
        
        # First pass: find optimal font size with baseline spacing
        font_size = self.find_optimal_font_size(lines, self.MIN_LINE_SPACING)
        
        # Second pass: find optimal line spacing with found font size
        line_spacing = self.find_optimal_line_spacing(lines, font_size)
        
        # Final measurement
        final_metrics = self.measurer.measure_lines(lines, font_size, line_spacing)
        
        # Verify fit
        if not self.fits_on_page(final_metrics):
            logger.warning("Final result exceeds page height, applying safety reduction")
            font_size *= 0.95
            line_spacing *= 0.98
            final_metrics = self.measurer.measure_lines(lines, font_size, line_spacing)
        
        result = {
            "font_size_pt": round(font_size, 2),
            "line_spacing": round(line_spacing, 3),
            "content_height_pt": round(final_metrics.height, 1),
            "page_height_pt": round(self.measurer.available_height, 1),
            "fit_percentage": round(
                (final_metrics.height / self.measurer.available_height) * 100, 1
            ),
            "total_chars": final_metrics.char_count,
            "visual_lines": final_metrics.line_count,
            "fits_on_page": self.fits_on_page(final_metrics)
        }
        
        logger.info(f"Auto-fit complete: {json.dumps(result)}")
        return font_size, line_spacing, result


class ResumeBuilder:
    """Main resume builder orchestrator"""
    
    def __init__(self, page_width: float = 612, page_height: float = 792):
        self.measurer = SimpleTextMeasurer(page_width, page_height)
        self.fitter = ResumeFitter(self.measurer)
        self.lines: List[ResumeLine] = []
        logger.info("ResumeBuilder initialized")
    
    def add_line(self, text: str, is_heading: bool = False,
                 weight: int = 400, section: SectionType = SectionType.SUMMARY):
        """Add a line to resume content"""
        line = ResumeLine(text, is_heading, weight, section)
        self.lines.append(line)
        logger.debug(f"Added line: {text[:50]}..." if len(text) > 50 else f"Added line: {text}")
    
    def add_section(self, title: str, items: List[str], section_type: SectionType):
        """Add a complete section (header + items)"""
        self.add_line(title, is_heading=True, weight=700, section=section_type)
        for item in items:
            self.add_line(item, section=section_type)
    
    def auto_fit(self) -> dict:
        """
        Perform auto-fit to find optimal typography parameters.
        
        Returns:
            Dictionary with results including font_size, line_spacing, and metrics
        """
        if not self.lines:
            logger.error("No resume content to auto-fit")
            raise ValueError("Resume contains no lines")
        
        logger.info(f"Auto-fitting resume with {len(self.lines)} content lines")
        font_size, line_spacing, metrics = self.fitter.auto_fit(self.lines)
        
        return {
            "font_size_pt": metrics["font_size_pt"],
            "line_spacing": metrics["line_spacing"],
            "metrics": metrics,
            "content_lines": len(self.lines),
            "success": metrics["fits_on_page"]
        }
    
    def get_result_json(self) -> str:
        """Get complete result as JSON"""
        result = self.auto_fit()
        return json.dumps(result, indent=2)


def load_resume_from_file(filepath: str) -> ResumeBuilder:
    """Load resume from JSON file"""
    logger.info(f"Loading resume from {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        raise
    
    builder = ResumeBuilder()
    
    # Load sections
    for section_data in data.get("sections", []):
        section_type = SectionType(section_data.get("type", "summary"))
        items = section_data.get("items", [])
        
        if "title" in section_data:
            builder.add_section(section_data["title"], items, section_type)
        else:
            for item in items:
                builder.add_line(item, section=section_type)
    
    logger.info(f"Loaded {len(builder.lines)} lines from resume file")
    return builder


def create_sample_resume() -> ResumeBuilder:
    """Create a sample resume for testing"""
    builder = ResumeBuilder()
    
    # Header
    builder.add_line("John Doe", is_heading=True, weight=700)
    builder.add_line("Senior Software Engineer | john.doe@example.com | (555) 123-4567")
    
    # Summary
    builder.add_section("PROFESSIONAL SUMMARY", [
        "Experienced software engineer with 8+ years building scalable distributed systems. "
        "Expertise in Python, Go, and Rust. Led teams of 5+ engineers across multiple products.",
        "Passionate about performance optimization, system design, and mentoring junior engineers."
    ], SectionType.SUMMARY)
    
    # Experience
    builder.add_section("EXPERIENCE", [
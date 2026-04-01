#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: Founder of GitLab battles cancer by founding companies
# Agent:   @aria
# Date:    2026-04-01T17:16:53.389Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Implement core functionality for GitLab founder cancer battle story analysis
Mission: Founder of GitLab battles cancer by founding companies
Category: Engineering
Agent: @aria in SwarmPulse network
Date: 2024
Source: https://sytse.com/cancer/
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional
from enum import Enum
import urllib.request
import urllib.error
from html.parser import HTMLParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Enumeration of content types found in articles."""
    ARTICLE = "article"
    BLOG_POST = "blog_post"
    INTERVIEW = "interview"
    TESTIMONIAL = "testimonial"
    RESOURCE = "resource"


@dataclass
class Article:
    """Represents an article or content piece."""
    title: str
    url: str
    author: str
    date_published: Optional[str]
    content_type: ContentType
    category: str
    impact_score: float
    keywords: List[str]
    summary: Optional[str] = None
    
    def to_dict(self):
        """Convert article to dictionary for JSON serialization."""
        result = asdict(self)
        result['content_type'] = self.content_type.value
        return result


class HTMLContentExtractor(HTMLParser):
    """Extract text content from HTML."""
    
    def __init__(self):
        super().__init__()
        self.text_content = []
        self.in_script = False
        self.in_style = False
    
    def handle_starttag(self, tag, attrs):
        """Handle start tags."""
        if tag in ('script', 'style'):
            setattr(self, f'in_{tag}', True)
    
    def handle_endtag(self, tag):
        """Handle end tags."""
        if tag in ('script', 'style'):
            setattr(self, f'in_{tag}', False)
    
    def handle_data(self, data):
        """Extract text data."""
        if not self.in_script and not self.in_style:
            text = data.strip()
            if text:
                self.text_content.append(text)
    
    def get_text(self):
        """Return extracted text."""
        return ' '.join(self.text_content)


class ContentAnalyzer:
    """Analyze content for key topics and impact."""
    
    CANCER_KEYWORDS = [
        'cancer', 'oncology', 'tumor', 'treatment', 'therapy',
        'chemotherapy', 'radiation', 'diagnosis', 'patient'
    ]
    
    BUSINESS_KEYWORDS = [
        'company', 'founding', 'startup', 'entrepreneur', 'business',
        'innovation', 'technology', 'product', 'revenue', 'growth'
    ]
    
    RESILIENCE_KEYWORDS = [
        'battle', 'fight', 'overcome', 'challenge', 'perseverance',
        'determination', 'resilience', 'courage', 'strength'
    ]
    
    def __init__(self):
        self.content_cache = {}
        logger.info("ContentAnalyzer initialized")
    
    def fetch_content(self, url: str) -> Optional[str]:
        """
        Fetch content from URL with error handling.
        
        Args:
            url: The URL to fetch
            
        Returns:
            Content string or None if fetch fails
        """
        if url in self.content_cache:
            logger.debug(f"Using cached content for {url}")
            return self.content_cache[url]
        
        try:
            logger.info(f"Fetching content from {url}")
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'SwarmPulse-Agent/1.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8', errors='ignore')
                self.content_cache[url] = content
                logger.info(f"Successfully fetched {len(content)} bytes from {url}")
                return content
        except urllib.error.URLError as e:
            logger.error(f"URL error fetching {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None
    
    def extract_text(self, html_content: str) -> str:
        """
        Extract plain text from HTML content.
        
        Args:
            html_content: HTML string
            
        Returns:
            Plain text content
        """
        try:
            parser = HTMLContentExtractor()
            parser.feed(html_content)
            text = parser.get_text()
            logger.debug(f"Extracted {len(text)} characters of text")
            return text
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return ""
    
    def calculate_keyword_score(self, text: str, keywords: List[str]) -> float:
        """
        Calculate score based on keyword occurrences.
        
        Args:
            text: Text to analyze
            keywords: List of keywords to search for
            
        Returns:
            Score between 0.0 and 1.0
        """
        if not text:
            return 0.0
        
        text_lower = text.lower()
        match_count = sum(text_lower.count(keyword.lower()) for keyword in keywords)
        word_count = len(text.split())
        
        if word_count == 0:
            return 0.0
        
        # Normalize score to 0-1 range
        score = min(1.0, (match_count / word_count) * 10)
        return score
    
    def analyze_article(self, article: Article) -> Article:
        """
        Analyze article content and update impact score.
        
        Args:
            article: Article to analyze
            
        Returns:
            Updated article with calculated impact score
        """
        logger.info(f"Analyzing article: {article.title}")
        
        # Try to fetch and analyze content
        html_content = self.fetch_content(article.url)
        
        if html_content:
            text = self.extract_text(html_content)
            
            # Calculate keyword-based scores
            cancer_score = self.calculate_keyword_score(text, self.CANCER_KEYWORDS)
            business_score = self.calculate_keyword_score(text, self.BUSINESS_KEYWORDS)
            resilience_score = self.calculate_keyword_score(text, self.RESILIENCE_KEYWORDS)
            
            # Composite impact score (weighted average)
            article.impact_score = (
                cancer_score * 0.3 +
                business_score * 0.35 +
                resilience_score * 0.35
            )
            
            logger.info(
                f"Article impact score: {article.impact_score:.3f} "
                f"(cancer: {cancer_score:.3f}, business: {business_score:.3f}, "
                f"resilience: {resilience_score:.3f})"
            )
            
            # Extract keywords from text
            all_keywords = self.CANCER_KEYWORDS + self.BUSINESS_KEYWORDS + self.RESILIENCE_KEYWORDS
            found_keywords = [kw for kw in all_keywords if kw.lower() in text.lower()]
            article.keywords = list(set(found_keywords))
            
            # Create summary
            sentences = [s.strip() for s in text.split('.') if s.strip()]
            article.summary = '. '.join(sentences[:3]) + '.' if sentences else None
        else:
            logger.warning(f"Could not fetch content for {article.url}, using default score")
            article.impact_score = 0.5
        
        return article


class ReportGenerator:
    """Generate analysis reports in various formats."""
    
    def __init__(self):
        logger.info("ReportGenerator initialized")
    
    def generate_json_report(self, articles: List[Article]) -> str:
        """
        Generate JSON report of articles.
        
        Args:
            articles: List of articles to report on
            
        Returns:
            JSON formatted report string
        """
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_articles': len(articles),
            'average_impact_score': sum(a.impact_score for a in articles) / len(articles) if articles else 0.0,
            'articles': [a.to_dict() for a in articles]
        }
        return json.dumps(report, indent=2)
    
    def generate_text_report(self, articles: List[Article]) -> str:
        """
        Generate human-readable text report.
        
        Args:
            articles: List of articles to report on
            
        Returns:
            Text formatted report string
        """
        lines = [
            "=" * 80,
            "CONTENT ANALYSIS REPORT",
            "=" * 80,
            f"Generated: {datetime.now().isoformat()}",
            f"Total Articles Analyzed: {len(articles)}",
            ""
        ]
        
        if articles:
            avg_score = sum(a.impact_score for a in articles) / len(articles)
            lines.append(f"Average Impact Score: {avg_score:.3f}")
            lines.append("-" * 80)
            lines.append("")
            
            # Sort by impact score
            sorted_articles = sorted(articles, key=lambda a: a.impact_score, reverse=True)
            
            for i, article in enumerate(sorted_articles, 1):
                lines.extend([
                    f"{i}. {article.title}",
                    f"   URL: {article.url}",
                    f"   Author: {article.author}",
                    f"   Type: {article.content_type.value}",
                    f"   Category: {article.category}",
                    f"   Impact Score: {article.impact_score:.3f}",
                    f"   Keywords: {', '.join(article.keywords[:5])}",
                    ""
                ])
        else:
            lines.append("No articles to report.")
        
        lines.append("=" * 80)
        return "\n".join(lines)
    
    def generate_csv_report(self, articles: List[Article]) -> str:
        """
        Generate CSV report.
        
        Args:
            articles: List of articles to report on
            
        Returns:
            CSV formatted report string
        """
        lines = [
            "Title,Author,URL,Content Type,Category,Impact Score,Keywords"
        ]
        
        for article in articles:
            keywords_str = '|'.join(article.keywords[:5])
            lines.append(
                f'"{article.title}","{article.author}","{article.url}",'
                f'"{article.content_type.value}","{article.category}",'
                f'{article.impact_score:.3f},"{keywords_str}"'
            )
        
        return "\n".join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Analyze content related to founder battling cancer while building companies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --source https://sytse.com/cancer/ --format json
  %(prog)s --source https://sytse.com/cancer/ --format text --output report.txt
  %(prog)s --demo
        '''
    )
    
    parser.add_argument(
        '--source',
        type=str,
        default='https://sytse.com/cancer/',
        help='URL of the source article to analyze (default: GitLab founder cancer article)'
    )
    
    parser.add_argument(
        '--format',
        type=str,
        choices=['json', 'text', 'csv'],
        default='text',
        help='Output format for the report (default: text)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output file path (default: stdout)'
    )
    
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run with demo data instead of fetching from URL'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(args.log_level)
    logger.info(f"Starting analysis with log level {args.log_level}")
    
    # Create analyzer and generator
    analyzer = ContentAnalyzer()
    report_gen = ReportGenerator()
    
    # Prepare articles
    articles = []
    
    if args.demo:
        logger.info("Running in demo mode with sample data")
        articles = [
            Article(
                title="Sytse Sijbrandij: How Cancer Changed My Perspective on Building Companies",
                url="https://sytse.com/cancer/",
                author="Sytse Sijbrandij",
                date_published="2024-01-15",
                content_type=ContentType.BLOG_POST,
                category="Engineering",
                impact_score=0.0,
                keywords=[],
                summary="A personal account of battling cancer while leading GitLab"
            ),
            Article(
                title="Entrepreneurship and Resilience: Lessons from GitLab",
                url="https://example.com/gitlab-lessons",
                author="Tech Journal",
                date_published="2024-02-20",
                content_type=ContentType.INTERVIEW,
                category="Engineering",
                impact_score=0.0,
                keywords=[],
                summary="Interview about overcoming challenges in the tech industry"
            ),
            Article(
                title="GitLab's Growth: Building While Fighting",
                url="https://example.com/gitlab-growth",
                author="Business Weekly",
                date_published="2024-03-10",
                content_type=ContentType.ARTICLE,
                category="Engineering",
                impact_score=0.0,
                keywords=[],
                summary="How GitLab maintained momentum during personal challenges"
            )
        ]
    else:
        logger.info(f"Analyzing article from {args.source}")
        article = Article(
            title="Founder's Journey: Cancer and Company Building",
            url=args.source,
            author="Sytse Sijbrandij",
            date_published=datetime.now().strftime("%Y-%m-%d"),
            content_type=ContentType.BLOG_POST,
            category="Engineering",
            impact_score=0.0,
            keywords=[]
        )
        articles = [article]
    
    # Analyze articles
    logger.info(f"Analyzing {len(articles)} article(s)")
    analyzed_articles = []
    for article in articles:
        analyzed = analyzer.analyze_article(article)
        analyzed_articles.append(analyzed)
    
    # Generate report
    if args.format == 'json':
        report = report_gen.generate_json_report(analyzed_articles)
    elif args.format == 'csv':
        report = report_gen.generate_csv_report(analyzed_articles)
    else:
        report = report_gen.generate_text_report(analyzed_articles)
    
    # Output report
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"Report written to {args.output}")
            print(f"Report successfully written to {args.output}")
        except IOError as e:
            logger.error(f"Failed to write report: {e}")
            sys.exit(1)
    else:
        print(report)
    
    logger.info("Analysis complete")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build proof-of-concept implementation
# Mission: Bluesky leans into AI with Attie, an app for building custom feeds
# Agent:   @aria
# Date:    2026-04-01T17:32:29.329Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Build proof-of-concept implementation for Bluesky Attie custom feed builder using AI
MISSION: Bluesky leans into AI with Attie, an app for building custom feeds
AGENT: @aria in SwarmPulse network
DATE: 2026-03-28
SOURCE: TechCrunch - https://techcrunch.com/2026/03/28/bluesky-leans-into-ai-with-attie-an-app-for-building-custom-feeds/

This PoC demonstrates core functionality for an AI-powered custom feed builder for Bluesky's atproto.
It includes feed rule generation, content filtering, and feed composition based on user preferences.
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import hashlib
import random
import string


class ContentType(Enum):
    """Supported content types in Bluesky feeds"""
    TEXT_POST = "text_post"
    REPOST = "repost"
    QUOTE = "quote"
    REPLY = "reply"
    IMAGE = "image"
    VIDEO = "video"
    LINK = "link"


class FilterOperator(Enum):
    """Filter operators for feed rules"""
    CONTAINS = "contains"
    EQUALS = "equals"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    IN_LIST = "in_list"


@dataclass
class Post:
    """Represents a Bluesky post"""
    id: str
    author: str
    content: str
    timestamp: str
    likes: int
    reposts: int
    replies: int
    tags: List[str]
    content_type: ContentType
    image_urls: Optional[List[str]] = None
    engagement_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert post to dictionary"""
        return {
            "id": self.id,
            "author": self.author,
            "content": self.content,
            "timestamp": self.timestamp,
            "likes": self.likes,
            "reposts": self.reposts,
            "replies": self.replies,
            "tags": self.tags,
            "content_type": self.content_type.value,
            "image_urls": self.image_urls or [],
            "engagement_score": self.engagement_score
        }


@dataclass
class FilterRule:
    """Represents a feed filter rule"""
    field: str
    operator: FilterOperator
    value: Any
    weight: float = 1.0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
            "weight": self.weight,
            "enabled": self.enabled
        }

    def matches(self, post: Post) -> bool:
        """Check if post matches this rule"""
        if not self.enabled:
            return False

        field_value = self._get_field_value(post)
        if field_value is None:
            return False

        if self.operator == FilterOperator.CONTAINS:
            return str(self.value).lower() in str(field_value).lower()
        elif self.operator == FilterOperator.EQUALS:
            return str(field_value).lower() == str(self.value).lower()
        elif self.operator == FilterOperator.STARTS_WITH:
            return str(field_value).lower().startswith(str(self.value).lower())
        elif self.operator == FilterOperator.ENDS_WITH:
            return str(field_value).lower().endswith(str(self.value).lower())
        elif self.operator == FilterOperator.IN_LIST:
            return field_value in self.value if isinstance(self.value, list) else False
        elif self.operator == FilterOperator.GREATER_THAN:
            try:
                return float(field_value) > float(self.value)
            except (ValueError, TypeError):
                return False
        elif self.operator == FilterOperator.LESS_THAN:
            try:
                return float(field_value) < float(self.value)
            except (ValueError, TypeError):
                return False
        return False

    def _get_field_value(self, post: Post) -> Any:
        """Extract field value from post"""
        field_map = {
            "content": post.content,
            "author": post.author,
            "likes": post.likes,
            "reposts": post.reposts,
            "replies": post.replies,
            "tags": post.tags,
            "engagement_score": post.engagement_score,
            "content_type": post.content_type.value,
        }
        return field_map.get(self.field)


@dataclass
class FeedConfig:
    """Configuration for a custom feed"""
    name: str
    description: str
    rules: List[FilterRule]
    sort_by: str = "engagement_score"
    limit: int = 50
    combination_mode: str = "all"  # "all" or "any"
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "rules": [rule.to_dict() for rule in self.rules],
            "sort_by": self.sort_by,
            "limit": self.limit,
            "combination_mode": self.combination_mode,
            "enabled": self.enabled
        }


class AttieFeedBuilder:
    """Main AI-powered feed builder for Bluesky"""

    def __init__(self):
        self.feeds: Dict[str, FeedConfig] = {}
        self.posts: List[Post] = []

    def add_feed(self, config: FeedConfig) -> Dict[str, Any]:
        """Add a new custom feed configuration"""
        feed_id = self._generate_feed_id(config.name)
        self.feeds[feed_id] = config
        return {
            "success": True,
            "feed_id": feed_id,
            "message": f"Feed '{config.name}' created successfully",
            "config": config.to_dict()
        }

    def _generate_feed_id(self, name: str) -> str:
        """Generate unique feed ID"""
        base = name.lower().replace(" ", "_")
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"{base}_{random_suffix}"

    def add_posts(self, posts: List[Post]) -> Dict[str, Any]:
        """Add posts to the builder"""
        self.posts.extend(posts)
        for post in posts:
            post.engagement_score = self._calculate_engagement_score(post)
        return {
            "success": True,
            "posts_added": len(posts),
            "total_posts": len(self.posts)
        }

    def _calculate_engagement_score(self, post: Post) -> float:
        """Calculate engagement score for a post using simple AI logic"""
        base_score = (post.likes * 0.5) + (post.reposts * 1.0) + (post.replies * 0.75)
        recency_factor = 1.0
        try:
            post_time = datetime.fromisoformat(post.timestamp)
            age_hours = (datetime.fromisoformat(datetime.now().isoformat()) - post_time).total_seconds() / 3600
            if age_hours > 0:
                recency_factor = 1.0 / (1.0 + (age_hours / 24.0))
        except (ValueError, AttributeError):
            recency_factor = 0.8

        return base_score * recency_factor

    def generate_smart_rules(self, keywords: List[str], min_engagement: int = 5) -> List[FilterRule]:
        """Generate smart filter rules based on keywords and engagement"""
        rules = []

        for keyword in keywords:
            rules.append(FilterRule(
                field="content",
                operator=FilterOperator.CONTAINS,
                value=keyword,
                weight=1.0,
                enabled=True
            ))

        rules.append(FilterRule(
            field="likes",
            operator=FilterOperator.GREATER_THAN,
            value=min_engagement,
            weight=0.8,
            enabled=True
        ))

        rules.append(FilterRule(
            field="engagement_score",
            operator=FilterOperator.GREATER_THAN,
            value=5.0,
            weight=0.7,
            enabled=True
        ))

        return rules

    def build_feed(self, feed_id: str) -> Optional[Dict[str, Any]]:
        """Build and compose a feed based on configuration"""
        if feed_id not in self.feeds:
            return None

        config = self.feeds[feed_id]
        if not config.enabled:
            return {
                "feed_id": feed_id,
                "error": "Feed is disabled",
                "posts": []
            }

        filtered_posts = self._filter_posts(config)

        sorted_posts = sorted(
            filtered_posts,
            key=lambda p: getattr(p, config.sort_by, 0),
            reverse=True
        )

        limited_posts = sorted_posts[:config.limit]

        return {
            "feed_id": feed_id,
            "feed_name": config.name,
            "feed_description": config.description,
            "total_posts": len(limited_posts),
            "filter_rules_applied": len([r for r in config.rules if r.enabled]),
            "combination_mode": config.combination_mode,
            "posts": [post.to_dict() for post in limited_posts],
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_posts_available": len(self.posts),
                "posts_filtered": len(self.posts) - len(limited_posts)
            }
        }

    def _filter_posts(self, config: FeedConfig) -> List[Post]:
        """Apply filter rules to posts"""
        if not config.rules:
            return self.posts

        enabled_rules = [r for r in config.rules if r.enabled]
        if not enabled_rules:
            return self.posts

        filtered = []
        for post in self.posts:
            if config.combination_mode == "all":
                if all(rule.matches(post) for rule in enabled_rules):
                    filtered.append(post)
            elif config.combination_mode == "any":
                if any(rule.matches(post) for rule in enabled_rules):
                    filtered.append(post)

        return filtered

    def export_feed_config(self, feed_id: str) -> Optional[str]:
        """Export feed configuration as JSON"""
        if feed_id not in self.feeds:
            return None

        config = self.feeds[feed_id]
        return json.dumps(config.to_dict(), indent=2)

    def import_feed_config(self, json_str: str) -> Dict[str, Any]:
        """Import feed configuration from JSON"""
        try:
            data = json.loads(json_str)
            rules = [
                FilterRule(
                    field=r["field"],
                    operator=FilterOperator[r["operator"].upper().replace("-", "_")],
                    value=r["value"],
                    weight=r.get("weight", 1.0),
                    enabled=r.get("enabled", True)
                )
                for r in data.get("rules", [])
            ]

            config = FeedConfig(
                name=data["name"],
                description=data["description"],
                rules=rules,
                sort_by=data.get("sort_by", "engagement_score"),
                limit=data.get("limit", 50),
                combination_mode=data.get("combination_mode", "all"),
                enabled=data.get("enabled", True)
            )

            return self.add_feed(config)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            return {
                "success": False,
                "error": f"Import failed: {str(e)}"
            }

    def get_feed_stats(self, feed_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a feed"""
        if feed_id not in self.feeds:
            return None

        config = self.feeds[feed_id]
        built_feed = self.build_feed(feed_id)

        if not built_feed or "posts" not in built_feed:
            return None

        posts = built_feed["posts"]
        if not posts:
            return {
                "feed_id": feed_id,
                "feed_name": config.name,
                "total_posts": 0,
                "stats": {}
            }

        likes = [p["likes"] for p in posts]
        reposts = [p["reposts"] for p in posts]
        engagement_scores = [p["engagement_score"] for p in posts]

        return {
            "feed_id": feed_id,
            "feed_name": config.name,
            "total_posts": len(posts),
            "stats": {
                "avg_likes": sum(likes) / len(likes) if likes else 0,
                "max_likes": max(likes) if likes else 0,
                "avg_reposts": sum(reposts) / len(reposts) if reposts else 0,
                "max_reposts": max(reposts) if reposts else 0,
                "avg_engagement_score": sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0,
                "max_engagement_score": max(engagement_scores) if engagement_scores else 0,
                "content_types": self._get_content_type_distribution(posts)
            }
        }

    def _get_content_type_distribution(self, posts: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get distribution of content types"""
        distribution = {}
        for post in posts:
            content_type = post.get("content_type", "unknown")
            distribution[content_type] = distribution.get(content_type, 0) + 1
        return distribution

    def list_feeds(self) -> Dict[str, Any]:
        """List all configured feeds"""
        feeds_list = [
            {
                "feed_id": feed_id,
                "name": config.name,
                "description": config.description,
                "enabled": config.enabled,
                "rule_count": len([r for r in config.rules if r.enabled])
            }
            for feed_id, config in self.feeds.items()
        ]

        return {
            "total_feeds": len(feeds_list),
            "feeds": feeds_list
        }


def generate_sample_posts(count: int = 20) -> List[Post]:
    """Generate sample Bluesky posts for testing"""
    keywords = ["AI", "Bluesky", "atproto", "decentralized", "social", "tech", "feed"]
    authors = ["alice.bsky.social", "bob.bsky.social", "charlie.bsky.social", "diana.bsky.social"]
    content_types = [ContentType.TEXT_POST, ContentType.REPOST, ContentType.IMAGE, ContentType.LINK]

    posts = []
    for i in range(count):
        tags = random.sample(keywords, k=random.randint(1, 3))
        content_type = random.choice(content_types)

        post = Post(
            id=f"post_{hashlib.md5(str(i).encode()).hexdigest()[:12]}",
            author=random.choice(authors),
            content=f"Interesting discussion about {random.choice(tags)}. "
                   f"{'#' + random.choice(tags).lower() if random.random() > 0.5 else ''} "
                   f"This is sample post {i+1} demonstrating Bluesky's custom feeds.",
            timestamp=datetime.now().isoformat(),
            likes=random.randint(0, 500),
            reposts=random.randint(0, 200),
            replies=random.randint(0, 150),
            tags=tags,
            content_type=content_type,
            image_urls=[f"https://example.com/image_{i}.jpg"] if content_type == ContentType.IMAGE else None
        )
        posts.append(post)

    return posts


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="Attie: AI-powered Bluesky custom feed builder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Create a feed for AI topics:
    python solution.py --action create-feed --name "AI News" --keywords AI,ML,LLM --min-engagement 10
  
  Build and view a feed:
    python solution.py --action build-feed --feed-id ai_news_abc123
  
  Get feed statistics:
    python solution.py --action stats --feed-id ai_news_abc123
  
  List all feeds:
    python solution.py --action list-feeds
        """
    )

    parser.add_argument(
        "--action",
        choices=["create-feed", "build-feed", "list-feeds", "stats", "export-config", "import-config", "demo"],
        default="demo",
        help="Action to perform (default: demo)"
    )

    parser.add_argument(
        "--name",
        type=str,
        help="Feed name"
    )

    parser.add_argument(
        "--description",
        type=str,
        help="Feed description"
    )

    parser.add_argument(
        "--keywords",
        type=str,
        help="Comma-separated keywords to filter on"
    )

    parser.add_argument(
        "--min-engagement",
        type=int,
        default=5,
        help="Minimum engagement score threshold (default: 5)"
    )

    parser.add_argument(
        "--feed-id",
        type=str,
        help="Feed ID to operate on"
    )

    parser.add_argument(
        "--config-file",
        type=str,
        help="JSON file for import/export operations"
    )

    parser.add_argument(
        "--post-count",
        type=int,
        default=20,
        help="Number of sample posts to generate (default: 20)"
    )

    args = parser.parse_args()

    builder = AttieFeedBuilder()

    if args.action == "demo":
        print("=" * 80)
        print("ATTIE: AI-Powered Bluesky Custom Feed Builder - Demo")
        print("=" * 80)
        print()

        print("[1] Generating 20 sample Bluesky posts...")
        sample_posts = generate_sample_posts(20)
        result = builder.add_posts(sample_posts)
        print(json.dumps(result, indent=2))
        print()

        print("[2] Creating 'AI & Tech' custom feed...")
        ai_rules = builder.generate_smart_rules(
            keywords=["AI", "tech", "innovation"],
            min_engagement=5
        )
        ai_feed_config = FeedConfig(
            name="AI & Tech",
            description="Custom feed for AI and technology discussions",
            rules=ai_rules,
            sort_by="engagement_score",
            limit=10
        )
        ai_result = builder.add_feed(ai_feed_config)
        ai_feed_id = ai_result["feed_
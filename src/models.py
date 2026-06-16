from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    title: str
    url: str
    summary: str
    source: str
    published: datetime


@dataclass
class EvaluationResult:
    top_articles: list          # list[Article]
    urgent_article: Optional[object]  # Optional[Article]
    urgency_score: float
    urgency_reasoning: str


@dataclass
class Script:
    title: str
    topic_context: str
    hook: str
    body: str
    cta: str
    visual_idea: str
    filming_tips: list          # list[str]
    hashtags_tiktok: list       # list[str]
    hashtags_reels: list        # list[str]
    hashtags_shorts: list       # list[str]
    script_type: str            # "trend" | "evergreen"

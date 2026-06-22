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
    body: str                   # guión natural completo (lo que diría platicando)
    cta: str
    # ── Modo Director (cómo grabarlo, estilo plática) ──
    spot: str                   # lugar concreto y fácil donde grabar
    como_grabar: str            # equipo + setup de la toma (cel/DJI Mic/tripie/dron)
    puntos: list                # list[str] — puntos a tocar para improvisar
    arranque: str               # primeras palabras textuales + qué hace en cámara
    # ── meta ──
    hashtags_tiktok: list       # list[str]
    hashtags_reels: list        # list[str]
    hashtags_shorts: list       # list[str]
    script_type: str            # "trend" | "howto" | "lifestyle" | "opinion" | "tech" | "fsd"

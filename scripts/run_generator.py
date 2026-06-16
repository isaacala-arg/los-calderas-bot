import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sources.rss_fetcher import fetch_articles
from src.sources.reddit_fetcher import fetch_posts
from src.sources.youtube_fetcher import fetch_trending
from src.sources.trends_fetcher import fetch_trends
from src.brain.evaluator import evaluate
from src.brain.script_generator import generate, generate_evergreen
from src.outputs.notion_writer import write_script


def main():
    print("Fetching articles from all sources...")
    articles = (
        fetch_articles(max_per_feed=5)
        + fetch_posts(limit=10)
        + fetch_trending(max_results=5)
    )

    trends = fetch_trends()
    print(f"Top trends: {[t['keyword'] for t in trends[:3]]}")
    print(f"Total articles collected: {len(articles)}")

    result = evaluate(articles)

    scripts_generated = 0

    for article in result.top_articles[:3]:
        print(f"Generating trend script for: {article.title}")
        script = generate(article, script_type="trend")
        url = write_script(script)
        print(f"Script saved: {url}")
        scripts_generated += 1

    while scripts_generated < 3:
        print("Generating evergreen script...")
        script = generate_evergreen()
        url = write_script(script)
        print(f"Evergreen script saved: {url}")
        scripts_generated += 1


if __name__ == "__main__":
    main()

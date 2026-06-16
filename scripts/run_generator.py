import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sources.rss_fetcher import fetch_articles
from src.sources.reddit_fetcher import fetch_posts
from src.sources.youtube_fetcher import fetch_trending
from src.sources.trends_fetcher import fetch_trends
from src.brain.evaluator import evaluate
from src.brain.script_generator import generate, generate_howto, generate_lifestyle, generate_opinion
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

    # Script 1: trend — from the top news article of the day
    if result.top_articles:
        top = result.top_articles[0]
        print(f"Generating trend script for: {top.title}")
        script1 = generate(top, script_type="trend")
    else:
        print("No top articles found, generating opinion instead")
        script1 = generate_opinion()
    url1 = write_script(script1)
    print(f"[1/3] Trend script saved: {url1}")

    # Script 2: rotates between howto and opinion by day of week
    # Even days = howto, odd days = opinion — keeps content fresh
    day_of_week = date.today().weekday()
    if day_of_week % 2 == 0:
        print("Generating how-to script...")
        script2 = generate_howto()
    else:
        print("Generating opinion script...")
        script2 = generate_opinion()
    url2 = write_script(script2)
    print(f"[2/3] {script2.script_type.capitalize()} script saved: {url2}")

    # Script 3: lifestyle — always, every day
    print("Generating lifestyle script...")
    script3 = generate_lifestyle()
    url3 = write_script(script3)
    print(f"[3/3] Lifestyle script saved: {url3}")

    print(f"\nDone! 3 scripts generated:")
    print(f"  1. Trend     → {url1}")
    print(f"  2. {script2.script_type.capitalize():<9} → {url2}")
    print(f"  3. Lifestyle → {url3}")


if __name__ == "__main__":
    main()

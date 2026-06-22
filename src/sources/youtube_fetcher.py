import googleapiclient.discovery
from datetime import datetime, timedelta, timezone
from src.models import Article

SEARCH_QUERIES = [
    "autos México 2026",
    "Tesla FSD Mexico",
    "noticias automotrices",
    "Mini Cooper Mexico",
    "autos eléctricos México",
]


def fetch_trending(max_results: int = 5) -> list:
    from src.config import settings

    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)
    articles = []
    published_after = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")

    for query in SEARCH_QUERIES:
        response = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            order="viewCount",
            publishedAfter=published_after,
            maxResults=max_results,
            regionCode="MX",
        ).execute()

        for item in response.get("items", []):
            snippet = item["snippet"]
            articles.append(Article(
                title=snippet["title"],
                url=f"https://youtube.com/watch?v={item['id']['videoId']}",
                summary=snippet.get("description", "")[:500],
                source=f"YouTube: {snippet['channelTitle']}",
                published=datetime.strptime(snippet["publishedAt"], "%Y-%m-%dT%H:%M:%SZ"),
            ))
    return articles

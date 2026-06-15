import pytrends.request
from tenacity import retry, stop_after_attempt, wait_exponential

AUTOMOTIVE_KEYWORDS = [
    "Tesla México",
    "autos eléctricos México",
    "FSD México",
    "Mini Cooper México",
    "mejores autos 2026",
]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=30))
def fetch_trends() -> list:
    pt = pytrends.request.TrendReq(hl="es-MX", tz=360)
    pt.build_payload(AUTOMOTIVE_KEYWORDS[:5], geo="MX", timeframe="now 7-d")
    data = pt.interest_over_time()

    if data.empty:
        return []

    latest = data.iloc[-1]
    results = []
    for keyword in AUTOMOTIVE_KEYWORDS[:5]:
        if keyword in latest and int(latest[keyword]) > 0:
            results.append({"keyword": keyword, "interest": int(latest[keyword])})

    return sorted(results, key=lambda x: x["interest"], reverse=True)

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.brain.carousel_generator import generate_carousel_tema, CAROUSEL_TOPICS
from src.outputs.notion_writer import write_carousel
from src.outputs.notion_reader import get_recent_titles


def main():
    wanted = os.environ.get("CAROUSEL_TOPIC", "").strip().lower()
    topic = None
    if wanted:
        topic = next((t for t in CAROUSEL_TOPICS if wanted in t["title"].lower()), None)
        if topic is None:
            print(f"AVISO: '{wanted}' no está en el banco; usando uno al azar")
    print("Generando carrusel por tema...")
    try:
        recent = get_recent_titles(days=45)
    except Exception:
        recent = []
    carousel = generate_carousel_tema(topic, recent_titles=recent)
    url = write_carousel(carousel)
    print(f"Carrusel guardado en Notion: {url}")


if __name__ == "__main__":
    main()

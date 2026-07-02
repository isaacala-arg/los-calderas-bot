import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.brain.carousel_generator import generate_carousel_tema, CAROUSEL_TOPICS
from src.outputs.notion_writer import write_carousel


def main():
    wanted = os.environ.get("CAROUSEL_TOPIC", "").strip().lower()
    topic = None
    if wanted:
        topic = next((t for t in CAROUSEL_TOPICS if wanted in t["title"].lower()), None)
        if topic is None:
            print(f"AVISO: '{wanted}' no está en el banco; usando uno al azar")
    carousel = generate_carousel_tema(topic)
    url = write_carousel(carousel)
    print(f"Carrusel guardado en Notion: {url}")


if __name__ == "__main__":
    main()

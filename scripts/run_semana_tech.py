import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.brain.carousel_generator import generate_semana_tech
from src.outputs.notion_writer import write_carousel
from src.outputs.notion_reader import get_recent_titles


def main():
    print("Generando 'Semana en tech' (busqueda web, ultimos 7 dias)...")
    try:
        recent = get_recent_titles(days=45)
    except Exception:
        recent = []
    carousel = generate_semana_tech(recent_titles=recent)
    url = write_carousel(carousel)
    print(f"Carrusel guardado en Notion: {url}")


if __name__ == "__main__":
    main()

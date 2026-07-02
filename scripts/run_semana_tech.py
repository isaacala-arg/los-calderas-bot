import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.brain.carousel_generator import generate_semana_tech
from src.outputs.notion_writer import write_carousel


def main():
    print("Generando 'Semana en tech' (busqueda web, ultimos 7 dias)...")
    carousel = generate_semana_tech()
    url = write_carousel(carousel)
    print(f"Carrusel guardado en Notion: {url}")


if __name__ == "__main__":
    main()

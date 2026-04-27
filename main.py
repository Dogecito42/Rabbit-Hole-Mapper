"""
Punto de entrada de RabbitHole Mapper — Semana 1: Crawler.

Uso:
    # Primera ejecucion de un perfil (login manual en ventana visible):
    python main.py --perfil casual --videos 50 --headless false

    # Ejecuciones normales (headless, usa la sesion guardada):
    python main.py --perfil casual --videos 50
    python main.py --perfil gamer  --videos 50
    python main.py --perfil info   --videos 50

Argumentos:
    --perfil    Perfil de agente: casual | gamer | info
    --videos    Numero de videos a capturar (default: valor en config.py)
    --headless  true|false — false abre ventana visible (default: true)

El fichero JSON de sesion se guarda en data/raw/.
Los logs de la sesion se escriben en logs/<perfil>_<timestamp>.log
y tambien se imprimen en la consola.
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from src.config import DEFAULT_VIDEOS, LOGS_DIR
from src.crawler.session import CrawlerSession


def _setup_logging(perfil: str):
    """
    Configura logging a consola y a fichero de log por sesion.

    El nivel INFO muestra el progreso video a video.
    El nivel DEBUG muestra los detalles de extraccion DOM (muy verboso).
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"{perfil}_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    logging.info("Log de sesion: %s", log_file)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="RabbitHole Mapper — crawler de YouTube Shorts"
    )
    parser.add_argument(
        "--perfil",
        required=True,
        choices=["casual", "gamer", "info"],
        help="Perfil de agente a simular",
    )
    parser.add_argument(
        "--videos",
        type=int,
        default=DEFAULT_VIDEOS,
        help=f"Numero de videos a capturar (default: {DEFAULT_VIDEOS})",
    )
    parser.add_argument(
        "--headless",
        type=lambda v: v.lower() != "false",
        default=True,
        metavar="true|false",
        help="Correr sin ventana visible (default: true). Usar false para el primer login.",
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    _setup_logging(args.perfil)

    logging.info(
        "RabbitHole Mapper | perfil=%s | videos=%d | headless=%s",
        args.perfil, args.videos, args.headless,
    )

    session = CrawlerSession(
        perfil=args.perfil,
        n_videos=args.videos,
        headless=args.headless,
    )

    output_path: Path = session.run()
    logging.info("Sesion completada. Datos en: %s", output_path)


if __name__ == "__main__":
    main()

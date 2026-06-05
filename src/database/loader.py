"""
Carga masiva de sesiones JSON historicas en Neo4j.

Uso:
    python -m src.database.loader                  # carga todos los perfiles
    python -m src.database.loader --perfil casual  # solo un perfil
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from src.config import RAW_DIR
from src.database.neo4j_client import Neo4jClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def cargar_perfil(db: Neo4jClient, perfil: str):
    directorio = RAW_DIR / perfil
    if not directorio.exists():
        logger.warning("No existe el directorio %s", directorio)
        return

    ficheros = sorted(directorio.glob("session_*.json"))
    logger.info("Cargando %d sesiones de perfil '%s'", len(ficheros), perfil)

    for fichero in ficheros:
        if "_partial" in fichero.name:
            continue
        try:
            with open(fichero, encoding="utf-8") as f:
                sesion = json.load(f)
            db.cargar_sesion(sesion)
        except Exception as e:
            logger.error("Error cargando %s: %s", fichero.name, e)


def main():
    parser = argparse.ArgumentParser(description="Carga sesiones JSON en Neo4j")
    parser.add_argument("--perfil", choices=["casual", "gamer", "info"], default=None)
    args = parser.parse_args()

    perfiles = [args.perfil] if args.perfil else ["casual", "gamer", "info"]

    with Neo4jClient() as db:
        for perfil in perfiles:
            cargar_perfil(db, perfil)

    logger.info("Carga completada.")


if __name__ == "__main__":
    main()

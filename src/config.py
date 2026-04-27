"""
Configuracion central del proyecto RabbitHole Mapper.

Contiene rutas, parametros del crawler y los videos semilla de cada perfil.
Carga valores desde .env cuando estan disponibles.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Rutas base
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
BROWSER_STATE_DIR = DATA_DIR / "browser_state"
LOGS_DIR = ROOT_DIR / "logs"

# ---------------------------------------------------------------------------
# Parametros del crawler
# ---------------------------------------------------------------------------

# Delay en segundos entre acciones para simular comportamiento humano.
# Se elige un valor aleatorio dentro de este rango en cada accion.
DELAY_MIN = float(os.getenv("CRAWLER_DELAY_MIN", 2))
DELAY_MAX = float(os.getenv("CRAWLER_DELAY_MAX", 8))

# Numero de videos a capturar por sesion si no se especifica en CLI.
DEFAULT_VIDEOS = int(os.getenv("CRAWLER_DEFAULT_VIDEOS", 50))

# Cada cuantos videos se guarda un checkpoint incremental en disco.
CHECKPOINT_EVERY = 10

# User-Agent de un Chrome real para no delatar que es Playwright.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ---------------------------------------------------------------------------
# Perfiles de agente y sus videos semilla
#
# El video semilla es un video neutro de entretenimiento desde el que arranca
# cada sesion. Usar el mismo seed garantiza que los experimentos son
# comparables entre perfiles y reproducibles entre ejecuciones.
#
# Para cambiar el seed de un perfil, sustituir el video_id por otro
# video neutro de YouTube Shorts.
# ---------------------------------------------------------------------------

PROFILES = {
    "casual": {
        "seed_video_id": "786yZG0xtTo",  # sustituir por un Short neutro real
        "description": "25 años, intereses generales, entretenimiento neutro",
    },
    "gamer": {
        "seed_video_id": "786yZG0xtTo",  # sustituir por un Short de gaming neutro
        "description": "18 años, gaming y cultura de internet",
    },
    "info": {
        "seed_video_id": "786yZG0xtTo",  # sustituir por un Short educativo neutro
        "description": "35 años, contenido educativo y divulgativo",
    },
}

# ---------------------------------------------------------------------------
# Neo4j (usado en semana 3+)
# ---------------------------------------------------------------------------

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

# ---------------------------------------------------------------------------
# Ollama (usado en semana 2+)
# ---------------------------------------------------------------------------

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = "llama3.1"

"""
Bucle principal de navegacion de YouTube Shorts.

Orquesta BrowserSession, VideoExtractor y TranscriptFetcher para
navegar n videos consecutivos, capturar sus metadatos y persistirlos
en un fichero JSON de sesion.

Caracteristicas:
- Checkpoint incremental cada CHECKPOINT_EVERY videos para no perder
  datos si YouTube bloquea la sesion a mitad.
- Si next_video_id no se puede extraer del DOM, la sesion termina
  anticipadamente y se persiste lo capturado hasta ese punto.
- El fichero de salida incluye metadatos de la sesion (perfil, seed,
  timestamps) ademas de la lista de videos.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.config import (
    RAW_DIR,
    CHECKPOINT_EVERY,
    PROFILES,
)
from src.crawler.browser import BrowserSession
from src.crawler.extractor import VideoExtractor, VideoMetadata
from src.crawler.transcript import TranscriptFetcher
from src.agents.agent import Agent

logger = logging.getLogger(__name__)

# Tiempo maximo de espera para que el DOM de un Short cargue (ms).
_PAGE_LOAD_TIMEOUT = 15_000


class CrawlerSession:
    """
    Ejecuta una sesion de crawling completa para un perfil de agente.

    Args:
        perfil:   uno de "casual", "gamer", "info".
        n_videos: numero de videos a capturar en esta sesion.
        headless: False para el primer login o depuracion visual.
    """

    def __init__(self, perfil: str, n_videos: int, headless: bool = True):
        if perfil not in PROFILES:
            raise ValueError(f"Perfil '{perfil}' no reconocido. Opciones: {list(PROFILES)}")

        self.perfil = perfil
        self.n_videos = n_videos
        self.headless = headless
        self.seed_video_id = PROFILES[perfil]["seed_video_id"]

        self._transcript_fetcher = TranscriptFetcher()
        self._agent = Agent(perfil)
        self._captured: list[dict] = []
        self._started_at: str = ""

    # ------------------------------------------------------------------
    # Punto de entrada publico
    # ------------------------------------------------------------------

    def run(self) -> Path:
        """
        Ejecuta la sesion completa y devuelve la ruta al JSON guardado.

        Returns:
            Path al fichero JSON de sesion generado.
        """
        self._started_at = datetime.now().isoformat()
        logger.info(
            "Iniciando sesion | perfil=%s seed=%s n_videos=%d",
            self.perfil, self.seed_video_id, self.n_videos,
        )

        with BrowserSession(perfil=self.perfil, headless=self.headless) as browser:
            self._navigate_and_collect(browser)

        return self._persist()

    # ------------------------------------------------------------------
    # Navegacion
    # ------------------------------------------------------------------

    def _navigate_and_collect(self, browser: BrowserSession):
        """
        Bucle principal: navega video a video y acumula metadatos.

        En cada iteracion:
        1. Espera a que el DOM cargue el Short actual.
        2. Extrae metadatos + transcripcion.
        3. Aplica delay humano y movimiento de cursor.
        4. Lee next_video_id del DOM.
        5. Navega al siguiente video.
        6. Cada CHECKPOINT_EVERY videos guarda un fichero parcial.
        """
        page = browser.page
        extractor = VideoExtractor(page)
        current_id = self.seed_video_id

        page.goto(f"https://www.youtube.com/shorts/{current_id}")

        for i in range(self.n_videos):
            logger.info("Video %d/%d — id=%s", i + 1, self.n_videos, current_id)

            try:
                self._wait_for_short(page)
            except PlaywrightTimeoutError:
                logger.warning("Timeout esperando el Short %s. Terminando sesion.", current_id)
                break

            metadata: VideoMetadata = extractor.extract()
            metadata.transcripcion = self._transcript_fetcher.fetch(current_id)

            decision = self._agent.evaluar(metadata)
            logger.info(
                "Decision agente: accion=%s afinidad=%.2f extremismo=%.2f llm_ok=%s",
                decision.accion, decision.afinidad_con_perfil,
                decision.extremismo, decision.llm_ok,
            )

            entrada = metadata.to_dict()
            entrada["decision"] = decision.to_dict()
            self._captured.append(entrada)

            if (i + 1) % CHECKPOINT_EVERY == 0:
                self._persist(partial=True)
                logger.info("Checkpoint guardado (%d videos)", len(self._captured))

            if not metadata.next_video_id:
                logger.warning("No se encontro el siguiente video en el DOM. Terminando sesion.")
                break

            browser.human_delay()
            browser.simulate_mouse()

            current_id = metadata.next_video_id
            page.goto(f"https://www.youtube.com/shorts/{current_id}")

    def _wait_for_short(self, page):
        """
        Espera a que el Short este listo para extraer datos.

        Estrategia: esperar a que la URL contenga /shorts/ y que
        la red este idle (recursos principales cargados).
        """
        page.wait_for_load_state("domcontentloaded", timeout=_PAGE_LOAD_TIMEOUT)
        # Dar un margen extra para que los elementos del overlay rendericen
        page.wait_for_timeout(1500)

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def _persist(self, partial: bool = False) -> Path:
        """
        Guarda los datos capturados en un fichero JSON.

        Args:
            partial: si True, el nombre incluye el sufijo "_partial"
                     para distinguirlo del fichero final.

        Returns:
            Path al fichero escrito.
        """
        RAW_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = self._started_at.replace(":", "-").replace(".", "-")[:19]
        suffix = "_partial" if partial else ""
        filename = f"session_{self.perfil}_{timestamp}{suffix}.json"
        output_path = RAW_DIR / filename

        payload = {
            "perfil": self.perfil,
            "seed_video_id": self.seed_video_id,
            "n_videos_objetivo": self.n_videos,
            "n_videos_capturados": len(self._captured),
            "iniciado_en": self._started_at,
            "finalizado_en": datetime.now().isoformat(),
            "videos": self._captured,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        logger.info("Sesion %s en %s", "parcial guardada" if partial else "completa guardada", output_path)
        return output_path

"""
Bucle principal de navegacion de YouTube Shorts.

Orquesta BrowserSession, VideoExtractor y TranscriptFetcher para
navegar n videos consecutivos, capturar sus metadatos y persistirlos
en un fichero JSON de sesion.

Caracteristicas:
- Checkpoint incremental cada CHECKPOINT_EVERY videos para no perder
  datos si YouTube bloquea la sesion a mitad.
- La navegacion al siguiente video se hace via ArrowDown (simula swipe real),
  no dependiendo del preload del DOM. El next_video_id del extractor sigue
  capturandose como arista del grafo de recomendaciones.
- El fichero de salida incluye metadatos de la sesion (perfil, seed,
  timestamps) ademas de la lista de videos.
"""

import json
import logging
import random
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

_RE_SHORTS_ID = re.compile(r"/shorts/([A-Za-z0-9_-]+)")

from src.config import (
    RAW_DIR,
    CHECKPOINT_EVERY,
    PROFILES,
)
from src.crawler.browser import BrowserSession
from src.crawler.extractor import VideoExtractor, VideoMetadata
from src.crawler.transcript import TranscriptFetcher
from src.agents.agent import Agent

try:
    from src.database.neo4j_client import Neo4jClient
    _NEO4J_DISPONIBLE = True
except ImportError:
    _NEO4J_DISPONIBLE = False

try:
    from src.rl.qtable import QTable, ACCIONES
    from src.rl.reward import calcular_recompensa
    _RL_DISPONIBLE = True
except ImportError:
    _RL_DISPONIBLE = False

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

    def __init__(self, perfil: str, n_videos: int, headless: bool = True, neo4j: bool = True, rl: bool = True):
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
        self._db: "Neo4jClient | None" = None
        self._qtable: "QTable | None" = None

        if neo4j and _NEO4J_DISPONIBLE:
            try:
                self._db = Neo4jClient()
                self._db._crear_constraints()
                self._db.merge_perfil(perfil)
                logger.info("Neo4j conectado para perfil '%s'", perfil)
            except Exception as e:
                logger.warning("Neo4j no disponible, continuando sin grafo: %s", e)
                self._db = None

        if rl and _RL_DISPONIBLE:
            self._qtable = self._cargar_qtable()

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

        if self._db:
            self._db.close()

        if self._qtable:
            self._qtable.decaer_epsilon()
            self._guardar_qtable()
            logger.info("Q-table: %s", self._qtable.resumen())

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

        prev_estado: tuple | None = None
        prev_accion_idx: int | None = None

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

            # Q-Learning: actualizar con la recompensa del paso anterior
            # (la recompensa depende del video actual, que es el "siguiente" del paso previo)
            estado_actual = (decision.categoria_detectada, self.perfil)
            if self._qtable and prev_estado is not None and prev_accion_idx is not None:
                recompensa = calcular_recompensa(decision.afinidad_con_perfil, decision.extremismo)
                self._qtable.actualizar(prev_estado, prev_accion_idx, recompensa, estado_actual)
                if self._captured:
                    self._captured[-1]["decision"]["recompensa"] = recompensa

            # Elegir accion: Q-table en modo explotacion/exploracion, LLM como fallback
            if self._qtable:
                accion_idx = self._qtable.elegir_accion(estado_actual)
                accion = ACCIONES[accion_idx]
            else:
                accion = decision.accion
                accion_idx = None

            logger.info(
                "Decision: accion=%s (rl=%s) afinidad=%.2f extremismo=%.2f epsilon=%s llm_ok=%s",
                accion,
                self._qtable is not None,
                decision.afinidad_con_perfil,
                decision.extremismo,
                f"{self._qtable.epsilon:.3f}" if self._qtable else "N/A",
                decision.llm_ok,
            )

            self._simular_visionado(page, accion)

            if decision.like:
                self._dar_like(page)
            elif decision.afinidad_con_perfil <= 0.2:
                self._dar_dislike(page)
            if decision.afinidad_con_perfil >= 0.9:
                self._suscribir(page)
            if decision.comentario:
                self._comentar(page, decision.comentario)

            entrada = metadata.to_dict()
            entrada["decision"] = decision.to_dict()
            self._captured.append(entrada)

            if self._db:
                try:
                    posicion = i
                    sesion_id = self._started_at
                    self._db.merge_video(metadata.video_id, metadata.titulo, metadata.hashtags)
                    d = decision.to_dict()
                    d["capturado_en"] = metadata.capturado_en
                    self._db.merge_interaccion(self.perfil, metadata.video_id, d, sesion_id, posicion)
                    if metadata.next_video_id:
                        self._db.merge_video(metadata.next_video_id, None, [])
                        self._db.merge_recomendacion(metadata.video_id, metadata.next_video_id, self.perfil, sesion_id, posicion)
                except Exception as e:
                    logger.warning("Error escribiendo en Neo4j: %s", e)

            if (i + 1) % CHECKPOINT_EVERY == 0:
                self._persist(partial=True)
                logger.info("Checkpoint guardado (%d videos)", len(self._captured))

            prev_estado = estado_actual
            prev_accion_idx = accion_idx

            browser.simulate_mouse()

            next_id = self._swipe_to_next(page, current_id)
            if not next_id:
                next_id = metadata.next_video_id
                if next_id:
                    logger.warning("Swipe fallido, navegando directamente a %s", next_id)
                    try:
                        page.goto(f"https://www.youtube.com/shorts/{next_id}")
                    except Exception:
                        next_id = None
            if not next_id:
                logger.warning("Sin siguiente video, reiniciando desde seed %s", self.seed_video_id)
                next_id = self.seed_video_id
                try:
                    page.goto(f"https://www.youtube.com/shorts/{next_id}")
                except Exception:
                    logger.error("No se pudo recuperar la sesion. Terminando.")
                    break
            current_id = next_id

    def _obtener_duracion(self, page) -> float | None:
        """Lee la duracion del video en segundos desde el elemento <video> via JS."""
        try:
            dur = page.evaluate(
                "() => { const v = document.querySelector('video'); "
                "return v && isFinite(v.duration) ? v.duration : null; }"
            )
            return float(dur) if dur else None
        except Exception:
            return None

    def _simular_visionado(self, page, accion: str):
        """
        Espera el tiempo de visionado correspondiente a la decision del agente.

        Usar la duracion real del video hace que el comportamiento sea indistinguible
        de un usuario humano para el algoritmo de recomendaciones de YouTube.
        """
        duracion = self._obtener_duracion(page)

        if accion == "skip":
            tiempo = random.uniform(2.0, 4.0)
        elif accion == "ver_parcial":
            tiempo = (duracion * random.uniform(0.3, 0.6)) if duracion else random.uniform(8.0, 20.0)
        else:  # ver_completo
            tiempo = (duracion * random.uniform(0.9, 1.0)) if duracion else random.uniform(25.0, 50.0)

        logger.debug(
            "Visionado: accion=%s duracion_real=%.1fs espera=%.1fs",
            accion, duracion or 0, tiempo,
        )
        page.wait_for_timeout(int(tiempo * 1000))

    def _dar_dislike(self, page):
        """Marca No me gusta cuando la afinidad es muy baja (<= 0.2)."""
        try:
            btn = page.query_selector("button[aria-label*='No me gusta'][aria-pressed='false']")
            if btn:
                btn.click()
                logger.debug("Dislike dado")
        except Exception as e:
            logger.debug("No se pudo dar dislike: %s", e)

    def _suscribir(self, page):
        """Se suscribe al canal si la afinidad es maxima (>= 0.9) y aun no esta suscrito."""
        try:
            btn = page.query_selector("yt-subscribe-button-view-model button")
            if btn:
                texto = btn.inner_text().strip().lower()
                if "suscribirme" in texto:
                    btn.click()
                    logger.debug("Suscrito al canal")
        except Exception as e:
            logger.debug("No se pudo suscribir: %s", e)

    def _dar_like(self, page):
        """
        Hace click en el boton de like si no esta ya marcado.

        Solo clica si aria-pressed="false" para no quitar un like previo.
        Es best-effort: si el selector no existe o falla, se ignora.
        """
        try:
            btn = page.query_selector("like-button-view-model button[aria-pressed='false']")
            if btn:
                btn.click()
                logger.debug("Like dado")
        except Exception as e:
            logger.debug("No se pudo dar like: %s", e)

    def _comentar(self, page, texto: str):
        """Publica un comentario en el Short actual."""
        try:
            btn = page.query_selector("button[aria-label*='comentarios']")
            if not btn:
                return
            btn.click()
            page.wait_for_selector(
                "#contenteditable-root[contenteditable='true']", timeout=5_000
            )
            input_el = page.query_selector("#contenteditable-root[contenteditable='true']")
            if not input_el:
                return
            input_el.click()
            page.wait_for_timeout(400)
            input_el.type(texto)
            submit = page.query_selector("ytd-button-renderer#submit-button button")
            if submit:
                submit.click()
                logger.debug("Comentario publicado: %s", texto[:50])
        except Exception as e:
            logger.debug("No se pudo comentar: %s", e)

    def _swipe_to_next(self, page, current_id: str) -> str | None:
        """
        Simula el swipe hacia el siguiente Short pulsando ArrowDown.

        Usar navegacion por teclado en lugar de goto() replica el comportamiento
        real del usuario y no depende de que el DOM precargue el enlace siguiente.
        El nuevo video_id se extrae de la URL resultante.
        """
        try:
            page.keyboard.press("ArrowDown")
            page.wait_for_url(
                lambda url: bool(_RE_SHORTS_ID.search(url))
                and _RE_SHORTS_ID.search(url).group(1) != current_id,
                timeout=10_000,
            )
            match = _RE_SHORTS_ID.search(page.url)
            return match.group(1) if match else None
        except Exception as e:
            logger.debug("Error al hacer swipe al siguiente video: %s", e)
            return None

    def _manejar_consentimiento(self, page):
        """
        Detecta la pagina de consentimiento de Google y la acepta automaticamente.

        YouTube redirige a consent.youtube.com cuando la cuenta no ha aceptado
        los terminos en este navegador. Si no se maneja aqui, el extractor recibe
        una URL que no es /shorts/<id> y lanza ValueError.
        """
        if "consent.youtube.com" not in page.url:
            return
        logger.info("Pagina de consentimiento detectada, intentando aceptar...")
        try:
            btn = page.query_selector(
                "button[jsname='b3VHJd'], form[action] button[type='submit'], form button"
            )
            if btn:
                btn.click()
                page.wait_for_url(
                    lambda url: "consent.youtube.com" not in url, timeout=6_000
                )
                return
        except Exception as e:
            logger.debug("No se pudo hacer click en aceptar: %s", e)

        # Fallback: extraer la URL del parametro continue y navegar directamente
        parsed = urlparse(page.url)
        params = parse_qs(parsed.query)
        continue_url = params.get("continue", [None])[0]
        if continue_url:
            try:
                page.goto(unquote(continue_url))
                logger.info("Saltado consentimiento via continue URL")
            except Exception as e:
                logger.warning("No se pudo navegar a continue URL: %s", e)

    def _wait_for_short(self, page):
        """
        Espera a que el Short este listo para extraer datos.

        Esperar al titulo es mas fiable que un timeout fijo: cuando el titulo
        esta en el DOM, el resto del overlay (hashtags, enlaces siguientes)
        tambien ha renderizado.
        """
        page.wait_for_load_state("domcontentloaded", timeout=_PAGE_LOAD_TIMEOUT)
        self._manejar_consentimiento(page)
        try:
            page.wait_for_selector(
                "h2.ytShortsVideoTitleViewModelShortsVideoTitle, "
                "yt-formatted-string.reel-player-overlay-style-title",
                timeout=8_000,
            )
        except Exception:
            # Si el titulo no aparece en 8 s, esperamos un margen fijo y continuamos
            page.wait_for_timeout(3_000)

    # ------------------------------------------------------------------
    # Q-Learning: carga y guardado
    # ------------------------------------------------------------------

    def _cargar_qtable(self) -> "QTable":
        from src.config import QTABLE_DIR
        path = QTABLE_DIR / f"qtable_{self.perfil}.pkl"
        if path.exists():
            return QTable.cargar(path, self.perfil)
        logger.info("Q-table nueva para perfil '%s'", self.perfil)
        return QTable(self.perfil)

    def _guardar_qtable(self):
        from src.config import QTABLE_DIR
        path = QTABLE_DIR / f"qtable_{self.perfil}.pkl"
        self._qtable.guardar(path)

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
        profile_dir = RAW_DIR / self.perfil
        profile_dir.mkdir(parents=True, exist_ok=True)

        timestamp = self._started_at.replace(":", "-").replace(".", "-")[:19]
        suffix = "_partial" if partial else ""
        filename = f"session_{self.perfil}_{timestamp}{suffix}.json"
        output_path = profile_dir / filename

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

"""
Extraccion de metadatos de un video de YouTube Shorts.

Dado un objeto Page de Playwright apuntando a una URL /shorts/<id>,
extrae todos los campos necesarios para el dataset y los devuelve
como un dataclass VideoMetadata.

Estrategia de extraccion del siguiente video:
    YouTube renderiza el siguiente Short en el DOM antes de que el usuario
    haga swipe. Buscamos el primer enlace con href="/shorts/<id>" que NO
    sea el video actual. Ese es el siguiente que el algoritmo recomienda.

Notas sobre fragilidad:
    Los selectores de YouTube pueden cambiar con actualizaciones del frontend.
    Si dejan de funcionar, inspeccion del DOM en Chrome DevTools sobre
    youtube.com/shorts es el punto de partida para actualizarlos.
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from playwright.sync_api import Page

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Selectores CSS — actualizar si YouTube cambia su estructura de DOM
# ---------------------------------------------------------------------------

# Titulo del video en la pagina de Shorts.
# YouTube cambia su DOM con frecuencia; se prueban en orden hasta encontrar uno.
_SEL_TITLE_CANDIDATES = [
    "h2.ytShortsVideoTitleViewModelShortsVideoTitle span",
    "yt-shorts-video-title-view-model h2 span",
    "yt-formatted-string.reel-player-overlay-style-title",
    "#video-title",
]

# Hashtags embebidos en la descripcion del Short como enlaces /hashtag/<nombre>/shorts.
# Se limita al panel de descripcion para no capturar hashtags de Shorts precargados.
_SEL_HASHTAGS = "ytd-video-description-header-renderer a[href*='/hashtag/']"

# Todos los enlaces a Shorts en la pagina (incluye el actual y los siguientes)
_SEL_SHORTS_LINKS = "a[href*='/shorts/']"

# Patron para extraer el video_id de una URL de Shorts
_RE_SHORTS_ID = re.compile(r"/shorts/([A-Za-z0-9_-]+)")


@dataclass
class VideoMetadata:
    """
    Metadatos de un video de YouTube Shorts capturado durante la navegacion.

    Todos los campos opcionales pueden ser None si el DOM no los expone
    (video sin titulo publico, sin hashtags, sin transcripcion, etc.).
    """

    video_id: str
    titulo: Optional[str]
    hashtags: list[str]
    transcripcion: str                # cadena vacia si no hay transcripcion
    next_video_id: Optional[str]
    capturado_en: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "video_id": self.video_id,
            "titulo": self.titulo,
            "hashtags": self.hashtags,
            "transcripcion": self.transcripcion,
            "next_video_id": self.next_video_id,
            "capturado_en": self.capturado_en,
        }


class VideoExtractor:
    """
    Extrae los metadatos de la pagina actual (un Short de YouTube).

    No navega ni produce side effects en el navegador. Solo lee el DOM.
    """

    def __init__(self, page: Page):
        self.page = page

    def extract(self) -> VideoMetadata:
        """
        Punto de entrada principal. Lee el DOM y devuelve un VideoMetadata.

        Llama a este metodo despues de que la pagina haya cargado completamente
        (esperar a network idle o a que el selector del titulo sea visible).
        """
        video_id = self._extract_video_id()
        self._open_description_panel()
        titulo = self._extract_titulo()
        hashtags = self._extract_hashtags()
        next_video_id = self._extract_next_video_id(current_id=video_id)

        logger.info(
            "Extraido: id=%s titulo='%s' hashtags=%s siguiente=%s",
            video_id, titulo, hashtags, next_video_id,
        )
        return VideoMetadata(
            video_id=video_id,
            titulo=titulo,
            hashtags=hashtags,
            transcripcion="",   # se rellena por TranscriptFetcher
            next_video_id=next_video_id,
        )

    # ------------------------------------------------------------------
    # Extraccion de campos individuales
    # ------------------------------------------------------------------

    def _extract_video_id(self) -> str:
        """Extrae el video_id de la URL actual (/shorts/<id>)."""
        url = self.page.url
        match = _RE_SHORTS_ID.search(url)
        if not match:
            raise ValueError(f"URL inesperada, no es un Short: {url}")
        return match.group(1)

    def _open_description_panel(self):
        """
        Abre el panel de descripcion haciendo click en el titulo del Short.

        El panel contiene los hashtags y la descripcion completa. Sin abrirlo,
        ytd-video-description-header-renderer no esta en el DOM.
        Es best-effort: si falla, la extraccion de hashtags devolvera lista vacia.
        """
        try:
            for selector in _SEL_TITLE_CANDIDATES:
                title_el = self.page.query_selector(selector)
                if title_el:
                    title_el.click()
                    self.page.wait_for_selector(
                        "ytd-video-description-header-renderer", timeout=3_000
                    )
                    return
        except Exception:
            pass

    def _extract_titulo(self) -> Optional[str]:
        """Lee el titulo del video probando varios selectores en orden."""
        try:
            for selector in _SEL_TITLE_CANDIDATES:
                element = self.page.query_selector(selector)
                if element:
                    text = element.inner_text().strip()
                    if text:
                        return text
        except Exception as e:
            logger.debug("No se pudo extraer titulo: %s", e)
        return None

    def _extract_hashtags(self) -> list[str]:
        """
        Lee los hashtags visibles bajo el titulo del video.

        Devuelve lista vacia si no hay hashtags o el selector no existe.
        """
        try:
            elements = self.page.query_selector_all(_SEL_HASHTAGS)
            return [el.inner_text().strip() for el in elements if el.inner_text().strip()]
        except Exception as e:
            logger.debug("No se pudieron extraer hashtags: %s", e)
        return []

    def _extract_next_video_id(self, current_id: str) -> Optional[str]:
        """
        Encuentra el ID del siguiente Short recomendado en el DOM.

        YouTube precarga el siguiente video en el DOM antes del swipe.
        Buscamos todos los enlaces /shorts/<id> y devolvemos el primero
        que no sea el video actual.
        """
        try:
            links = self.page.query_selector_all(_SEL_SHORTS_LINKS)
            seen = set()
            for link in links:
                href = link.get_attribute("href") or ""
                match = _RE_SHORTS_ID.search(href)
                if not match:
                    continue
                candidate_id = match.group(1)
                if candidate_id == current_id:
                    continue
                if candidate_id in seen:
                    continue
                if len(candidate_id) != 11:  # los IDs de YouTube son siempre 11 caracteres
                    continue
                seen.add(candidate_id)
                return candidate_id   # primer candidato distinto al actual
        except Exception as e:
            logger.debug("No se pudo extraer next_video_id: %s", e)
        return None

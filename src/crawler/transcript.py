"""
Descarga de transcripciones de YouTube via youtube-transcript-api.

Diseñado para ser tolerante a fallos: cualquier video sin transcripcion
disponible (videos sin subtitulos, privados, lives, regiones bloqueadas)
devuelve cadena vacia en lugar de lanzar una excepcion.

La transcripcion se usa en la Capa 2 (agentes LLM) como contexto adicional
para que el modelo entienda el contenido del video mas alla del titulo.
"""

import logging
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

logger = logging.getLogger(__name__)

# Idiomas preferidos en orden. Si no hay ES, se intenta EN.
# Si no hay ninguno, youtube-transcript-api lanza NoTranscriptFound.
_PREFERRED_LANGUAGES = ["es", "en"]


class TranscriptFetcher:
    """
    Descarga y concatena la transcripcion de un video de YouTube.

    Uso:
        fetcher = TranscriptFetcher()
        texto = fetcher.fetch("VIDEO_ID")
    """

    def fetch(self, video_id: str) -> str:
        """
        Descarga la transcripcion del video y la devuelve como texto plano.

        Concatena todos los fragmentos de la transcripcion separados por espacio.
        Si no hay transcripcion disponible por cualquier motivo, devuelve "".

        Args:
            video_id: ID de YouTube del video (no la URL completa).

        Returns:
            Texto completo de la transcripcion, o cadena vacia.
        """
        try:
            api = YouTubeTranscriptApi()
            fragments = api.fetch(video_id, languages=_PREFERRED_LANGUAGES)
            text = " ".join(f.text for f in fragments).strip()
            logger.debug("Transcripcion obtenida para %s (%d chars)", video_id, len(text))
            return text

        except NoTranscriptFound:
            logger.debug("Sin transcripcion disponible para %s", video_id)
        except TranscriptsDisabled:
            logger.debug("Transcripciones desactivadas para %s", video_id)
        except VideoUnavailable:
            logger.debug("Video no disponible: %s", video_id)
        except Exception as e:
            # Red caida, rate limit, formato inesperado, etc.
            logger.warning("Error inesperado al obtener transcripcion de %s: %s", video_id, e)

        return ""

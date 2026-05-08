"""
Agente LLM que evalua videos de YouTube Shorts segun su perfil de usuario.

Encapsula el perfil, el cliente LLM y la logica de formatear los metadatos
del video en texto antes de enviarselos al modelo. Devuelve objetos Decision
en lugar de dicts crudos para que el bucle principal tenga tipos claros.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from src.crawler.extractor import VideoMetadata
from src.agents.profiles import PERFILES, ACCIONES_VALIDAS
from src.agents.llm_client import LLMClient

logger = logging.getLogger(__name__)

_ACCION_DEFECTO = "skip"


_UMBRAL_LIKE = 0.6
_UMBRAL_COMENTARIO = 0.8


@dataclass
class Decision:
    """
    Resultado de la evaluacion del agente sobre un video.

    like y comentario se derivan de afinidad_con_perfil con umbrales fijos
    (>= 0.6 y >= 0.8 respectivamente) para que sean consistentes entre perfiles
    independientemente de la variabilidad del LLM.
    llm_ok es False si el LLM fallo; en ese caso los campos tienen valores de fallback.
    """

    perfil: str
    video_id: str
    categoria_detectada: str
    afinidad_con_perfil: float
    extremismo: float
    accion: str
    like: bool
    comentario: Optional[str]
    razonamiento: str
    llm_ok: bool

    def to_dict(self) -> dict:
        return {
            "perfil": self.perfil,
            "video_id": self.video_id,
            "categoria_detectada": self.categoria_detectada,
            "afinidad_con_perfil": self.afinidad_con_perfil,
            "extremismo": self.extremismo,
            "accion": self.accion,
            "like": self.like,
            "comentario": self.comentario,
            "razonamiento": self.razonamiento,
            "llm_ok": self.llm_ok,
        }


class Agent:
    """
    Agente autonomo que simula el comportamiento de un tipo de usuario en Shorts.

    Mantiene el perfil fijo durante toda la sesion. El cliente LLM se
    reutiliza entre llamadas para no reabrir la conexion con Ollama en cada video.
    """

    def __init__(self, perfil: str, llm_client: Optional[LLMClient] = None):
        if perfil not in PERFILES:
            raise ValueError(f"Perfil desconocido: '{perfil}'. Validos: {list(PERFILES)}")
        self.perfil = perfil
        self._config = PERFILES[perfil]
        self._llm = llm_client or LLMClient()

    def evaluar(self, video: VideoMetadata) -> Decision:
        """
        Evalua un video y devuelve una Decision coherente con el perfil.

        Si el LLM falla o devuelve JSON invalido, genera una Decision de fallback
        con accion=skip y llm_ok=False para que el bucle principal pueda continuar
        sin interrupciones y el fallo quede registrado en el campo llm_ok.
        """
        video_texto = self._formatear_video(video)
        datos = self._llm.evaluar_video(self._config["system_prompt"], video_texto)

        if datos is None:
            logger.warning(
                "Perfil %s: LLM fallo para video %s, usando fallback",
                self.perfil, video.video_id,
            )
            return self._decision_fallback(video.video_id)

        accion = datos["accion"] if datos["accion"] in ACCIONES_VALIDAS else _ACCION_DEFECTO
        if accion != datos["accion"]:
            logger.warning(
                "Accion '%s' no valida, sustituyendo por '%s'",
                datos["accion"], accion,
            )

        afinidad = max(0.0, min(1.0, datos["afinidad_con_perfil"]))
        # like y comentario se rigen por umbrales fijos, no por el criterio del LLM
        like = afinidad >= _UMBRAL_LIKE
        comentario = datos.get("comentario") if afinidad >= _UMBRAL_COMENTARIO else None

        return Decision(
            perfil=self.perfil,
            video_id=video.video_id,
            categoria_detectada=datos["categoria_detectada"],
            afinidad_con_perfil=afinidad,
            extremismo=max(0.0, min(1.0, datos["extremismo"])),
            accion=accion,
            like=like,
            comentario=comentario,
            razonamiento=datos["razonamiento"],
            llm_ok=True,
        )

    @staticmethod
    def _formatear_video(video: VideoMetadata) -> str:
        """
        Convierte un VideoMetadata a texto para enviarlo al LLM como mensaje de usuario.

        Se usa texto estructurado en lugar de JSON porque los modelos de chat
        responden mejor a descripciones en lenguaje natural para tareas de clasificacion.
        """
        hashtags = ", ".join(video.hashtags) if video.hashtags else "ninguno"
        transcripcion = video.transcripcion.strip() if video.transcripcion else "no disponible"
        return (
            f"Titulo: {video.titulo or 'sin titulo'}\n"
            f"Hashtags: {hashtags}\n"
            f"Transcripcion: {transcripcion}\n"
        )

    def _decision_fallback(self, video_id: str) -> Decision:
        return Decision(
            perfil=self.perfil,
            video_id=video_id,
            categoria_detectada="desconocida",
            afinidad_con_perfil=0.0,
            extremismo=0.0,
            accion=_ACCION_DEFECTO,
            like=False,
            comentario=None,
            razonamiento="LLM no disponible, accion conservadora por defecto",
            llm_ok=False,
        )

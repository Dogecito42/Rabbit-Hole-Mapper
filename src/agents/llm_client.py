"""
Wrapper de Ollama para obtener decisiones estructuradas del LLM.

El LLM no siempre devuelve JSON puro: puede envolverlo en texto libre,
en bloques de codigo markdown o en frases introductorias. Este modulo
se encarga de extraer el JSON de la respuesta y validar su estructura
antes de devolverloa la capa superior, para que el agente nunca tenga
que manejar respuestas malformadas.
"""

import json
import logging
import re
from typing import Optional

import ollama

from src.config import OLLAMA_HOST, OLLAMA_MODEL

logger = logging.getLogger(__name__)

# Patron para extraer el primer bloque JSON de un string de texto libre
_RE_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)

_CAMPOS_OBLIGATORIOS = {
    "categoria_detectada",
    "afinidad_con_perfil",
    "extremismo",
    "accion",
    "like",
    "razonamiento",
}


class LLMClient:
    """
    Envia prompts a Ollama y devuelve la respuesta como diccionario validado.

    Instanciar una vez por sesion para reutilizar la conexion con Ollama.
    """

    def __init__(self, model: str = OLLAMA_MODEL, host: str = OLLAMA_HOST):
        self.model = model
        self._client = ollama.Client(host=host)

    def evaluar_video(self, system_prompt: str, video_texto: str) -> Optional[dict]:
        """
        Llama al LLM con el system prompt del perfil y la descripcion del video.

        Devuelve None si Ollama no responde o si la respuesta no contiene JSON valido.
        El caller es responsable de manejar el caso None (p.ej. reintento o skip).
        """
        try:
            respuesta = self._client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": video_texto},
                ],
            )
            contenido = respuesta.message.content
            logger.debug("Respuesta LLM cruda: %s", contenido)
            return self._parsear_json(contenido)
        except Exception as e:
            logger.error("Error llamando a Ollama: %s", e)
            return None

    def _parsear_json(self, texto: str) -> Optional[dict]:
        """
        Extrae y valida el JSON de la respuesta del LLM.

        Busca el primer '{' y el ultimo '}' para tolerar texto libre antes
        y despues del JSON, ya que los modelos de chat suelen anadir frases
        introductorias aunque se les pida respuesta pura.
        """
        match = _RE_JSON_BLOCK.search(texto)
        if not match:
            logger.warning("No se encontro JSON en la respuesta del LLM")
            return None

        try:
            datos = json.loads(match.group())
        except json.JSONDecodeError as e:
            logger.warning("JSON malformado en respuesta del LLM: %s", e)
            return None

        ausentes = _CAMPOS_OBLIGATORIOS - datos.keys()
        if ausentes:
            logger.warning("Faltan campos en JSON del LLM: %s", ausentes)
            return None

        return self._normalizar(datos)

    def _normalizar(self, datos: dict) -> dict:
        """
        Convierte los tipos a los esperados para que la capa superior no haga casting.

        El LLM puede devolver afinidad como string "0.8" o como int 1.
        comentario es opcional: null, "null" o ausente se normalizan a None.
        """
        datos["afinidad_con_perfil"] = float(datos["afinidad_con_perfil"])
        datos["extremismo"] = float(datos["extremismo"])
        datos["like"] = bool(datos["like"])
        datos["accion"] = str(datos["accion"]).strip()
        comentario = datos.get("comentario")
        datos["comentario"] = (
            str(comentario).strip()
            if comentario and str(comentario).strip().lower() not in ("null", "none", "")
            else None
        )
        return datos

import pytest

from src.agents.agent import Agent
from src.crawler.extractor import VideoMetadata


class _LLMFalso:
    def __init__(self, respuesta):
        self._respuesta = respuesta

    def evaluar_video(self, system_prompt, video_texto):
        return self._respuesta


def _video():
    return VideoMetadata(
        video_id="abc123",
        titulo="Un video de prueba",
        hashtags=["#test"],
        transcripcion="contenido de ejemplo",
        next_video_id=None,
    )


def test_evaluar_con_llm_ok_deriva_like_y_comentario_por_umbral():
    respuesta = {
        "categoria_detectada": " Humor Costumbrista ",
        "afinidad_con_perfil": 0.85,
        "extremismo": 0.1,
        "accion": "ver_completo",
        "like": True,
        "comentario": "muy bueno",
        "razonamiento": "encaja con el perfil",
    }
    agent = Agent("casual", llm_client=_LLMFalso(respuesta))
    decision = agent.evaluar(_video())

    assert decision.categoria_detectada == "humor costumbrista"
    assert decision.like is True
    assert decision.comentario == "muy bueno"
    assert decision.llm_ok is True


def test_evaluar_comentario_se_omite_bajo_umbral():
    respuesta = {
        "categoria_detectada": "gaming",
        "afinidad_con_perfil": 0.65,
        "extremismo": 0.0,
        "accion": "ver_parcial",
        "like": True,
        "comentario": "deberia omitirse",
        "razonamiento": "afinidad media",
    }
    agent = Agent("gamer", llm_client=_LLMFalso(respuesta))
    decision = agent.evaluar(_video())

    assert decision.like is True
    assert decision.comentario is None


def test_evaluar_accion_invalida_cae_a_skip():
    respuesta = {
        "categoria_detectada": "info",
        "afinidad_con_perfil": 0.5,
        "extremismo": 0.0,
        "accion": "compartir",
        "like": False,
        "comentario": None,
        "razonamiento": "accion no soportada",
    }
    agent = Agent("info", llm_client=_LLMFalso(respuesta))
    decision = agent.evaluar(_video())

    assert decision.accion == "skip"


def test_evaluar_llm_falla_devuelve_decision_fallback():
    agent = Agent("casual", llm_client=_LLMFalso(None))
    decision = agent.evaluar(_video())

    assert decision.llm_ok is False
    assert decision.accion == "skip"
    assert decision.like is False


def test_perfil_desconocido_lanza_value_error():
    with pytest.raises(ValueError):
        Agent("inexistente", llm_client=_LLMFalso(None))

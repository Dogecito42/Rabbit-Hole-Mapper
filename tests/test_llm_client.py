from src.agents.llm_client import LLMClient


def _cliente():
    return LLMClient(model="test-model", host="http://localhost:11434")


def test_parsear_json_extrae_objeto_con_texto_alrededor():
    cliente = _cliente()
    texto = (
        "Claro, aqui tienes mi analisis:\n"
        '{"categoria_detectada": "gaming", "afinidad_con_perfil": "0.8", '
        '"extremismo": 0, "accion": "ver_completo", "like": 1, '
        '"comentario": null, "razonamiento": "encaja con el perfil"}\n'
        "Espero que ayude."
    )
    datos = cliente._parsear_json(texto)
    assert datos["categoria_detectada"] == "gaming"
    assert datos["afinidad_con_perfil"] == 0.8
    assert datos["like"] is True
    assert datos["comentario"] is None


def test_parsear_json_sin_json_devuelve_none():
    assert _cliente()._parsear_json("no hay json aqui") is None


def test_parsear_json_con_campos_faltantes_devuelve_none():
    texto = '{"categoria_detectada": "gaming", "afinidad_con_perfil": 0.5}'
    assert _cliente()._parsear_json(texto) is None


def test_normalizar_convierte_tipos_y_limpia_comentario_nulo():
    cliente = _cliente()
    datos = {
        "categoria_detectada": "humor",
        "afinidad_con_perfil": "0.9",
        "extremismo": 0,
        "accion": " ver_parcial ",
        "like": 0,
        "comentario": "null",
        "razonamiento": "ok",
    }
    normalizado = cliente._normalizar(datos)
    assert normalizado["afinidad_con_perfil"] == 0.9
    assert normalizado["like"] is False
    assert normalizado["accion"] == "ver_parcial"
    assert normalizado["comentario"] is None

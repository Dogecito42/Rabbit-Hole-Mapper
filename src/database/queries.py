"""
Consultas Cypher de verificacion y exploracion del grafo.

Las constantes CYPHER_* son plantillas reutilizables para consultas de lectura.
Las funciones ejecutan esas consultas y devuelven listas de dicts listos para
imprimir o pasar a las rutinas de analisis de semana 6.

Separar las consultas de neo4j_client.py mantiene ese modulo centrado en
escritura y permite evolucionar las queries de analisis sin tocar la capa
de persistencia.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes Cypher
# ---------------------------------------------------------------------------

CONTAR_VIDEOS = "MATCH (v:Video) RETURN count(v) AS total"

CONTAR_RECOMENDACIONES = "MATCH ()-[r:RECOMIENDA]->() RETURN count(r) AS total"

CONTAR_INTERACCIONES = "MATCH ()-[r:INTERACTUO]->() RETURN count(r) AS total"

RECOMENDACIONES_POR_PERFIL = """
MATCH (a:Video)-[r:RECOMIENDA]->(b:Video)
WHERE r.perfil = $perfil
RETURN a.titulo AS origen, b.titulo AS destino, r.posicion AS posicion
ORDER BY r.sesion_id, r.posicion
LIMIT $limite
"""

VIDEOS_MAS_RECOMENDADOS = """
MATCH ()-[:RECOMIENDA]->(v:Video)
RETURN v.video_id AS video_id, v.titulo AS titulo, count(*) AS veces
ORDER BY veces DESC
LIMIT $limite
"""

VIDEOS_POR_PERFIL = """
MATCH (p:Perfil {nombre: $perfil})-[r:INTERACTUO]->(v:Video)
RETURN v.video_id AS video_id, v.titulo AS titulo,
       r.accion AS accion, r.afinidad AS afinidad, r.extremismo AS extremismo
ORDER BY r.sesion_id, r.posicion
LIMIT $limite
"""

EXTREMISMO_MEDIO_POR_PERFIL = """
MATCH (p:Perfil {nombre: $perfil})-[r:INTERACTUO]->(:Video)
RETURN avg(r.extremismo) AS extremismo_medio,
       max(r.extremismo) AS extremismo_max,
       count(r) AS total_videos
"""


# ---------------------------------------------------------------------------
# Funciones de verificacion y exploracion
# ---------------------------------------------------------------------------

def stats_grafo(db: "Neo4jClient") -> dict:
    """Devuelve un resumen con el numero de nodos y aristas del grafo."""
    with db._driver.session() as session:
        videos = session.run(CONTAR_VIDEOS).single()["total"]
        recomendaciones = session.run(CONTAR_RECOMENDACIONES).single()["total"]
        interacciones = session.run(CONTAR_INTERACCIONES).single()["total"]
    return {
        "videos": videos,
        "recomendaciones": recomendaciones,
        "interacciones": interacciones,
    }


def recomendaciones_perfil(db: "Neo4jClient", perfil: str, limite: int = 20) -> list[dict]:
    """Devuelve las aristas RECOMIENDA de un perfil en orden de navegacion."""
    with db._driver.session() as session:
        result = session.run(RECOMENDACIONES_POR_PERFIL, perfil=perfil, limite=limite)
        return [dict(r) for r in result]


def videos_mas_recomendados(db: "Neo4jClient", limite: int = 10) -> list[dict]:
    """Devuelve los videos que mas veces aparecieron como siguiente Short recomendado."""
    with db._driver.session() as session:
        result = session.run(VIDEOS_MAS_RECOMENDADOS, limite=limite)
        return [dict(r) for r in result]


def videos_perfil(db: "Neo4jClient", perfil: str, limite: int = 50) -> list[dict]:
    """Devuelve los videos con los que interactuo un perfil, en orden de sesion."""
    with db._driver.session() as session:
        result = session.run(VIDEOS_POR_PERFIL, perfil=perfil, limite=limite)
        return [dict(r) for r in result]


def extremismo_perfil(db: "Neo4jClient", perfil: str) -> dict:
    """Devuelve el extremismo medio y maximo registrado para un perfil."""
    with db._driver.session() as session:
        row = session.run(EXTREMISMO_MEDIO_POR_PERFIL, perfil=perfil).single()
        return dict(row) if row else {}

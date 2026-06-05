"""
Deteccion de comunidades (camaras de eco) con el algoritmo de Louvain.

Cada comunidad representa un cluster tematico formado por la estructura de
recomendaciones de YouTube. Una comunidad dominada por un solo perfil indica
que ese perfil esta siendo encerrado en una camara de eco.

Uso:
    python -m src.analysis.louvain
    python -m src.analysis.louvain --min-size 5
"""

import argparse
import sys
sys.stdout.reconfigure(encoding="utf-8")
from collections import Counter, defaultdict

from src.database.neo4j_client import Neo4jClient

_NOMBRE_GRAFO = "grafo"

_LOUVAIN = """
CALL gds.louvain.stream($nombre_grafo)
YIELD nodeId, communityId
WITH gds.util.asNode(nodeId) AS v, communityId
RETURN v.video_id  AS video_id,
       v.titulo    AS titulo,
       v.hashtags  AS hashtags,
       communityId
ORDER BY communityId
"""

_PERFILES_POR_VIDEO = """
MATCH (p:Perfil)-[:INTERACTUO]->(v:Video {video_id: $video_id})
RETURN p.nombre AS perfil
"""

_VERIFICAR_PROYECCION = "CALL gds.graph.exists($nombre) YIELD exists RETURN exists"

_PROYECTAR = """
CALL gds.graph.project($nombre, 'Video', 'RECOMIENDA')
YIELD nodeCount, relationshipCount
"""


def _asegurar_proyeccion(db: Neo4jClient):
    with db._driver.session() as session:
        existe = session.run(_VERIFICAR_PROYECCION, nombre=_NOMBRE_GRAFO).single()["exists"]
        if not existe:
            row = session.run(_PROYECTAR, nombre=_NOMBRE_GRAFO).single()
            print(f"Grafo proyectado: {row['nodeCount']} nodos, {row['relationshipCount']} aristas")


def ejecutar(db: Neo4jClient, min_size: int = 3) -> list[dict]:
    """
    Devuelve una lista de comunidades con sus estadisticas.

    Filtra comunidades con menos de min_size videos para centrarse en
    clusters con masa critica suficiente para ser interpretables.
    """
    _asegurar_proyeccion(db)

    with db._driver.session() as session:
        filas = session.run(_LOUVAIN, nombre_grafo=_NOMBRE_GRAFO).data()

    # Agrupar por comunidad
    grupos: dict[int, list[dict]] = defaultdict(list)
    for f in filas:
        grupos[f["communityId"]].append(f)

    comunidades = []
    for community_id, videos in grupos.items():
        if len(videos) < min_size:
            continue

        # Hashtags mas frecuentes
        hashtags: list[str] = []
        for v in videos:
            hashtags.extend(v["hashtags"] or [])
        top_hashtags = [tag for tag, _ in Counter(hashtags).most_common(5)]

        comunidades.append({
            "community_id": community_id,
            "size": len(videos),
            "top_hashtags": top_hashtags,
            "videos": [
                {"video_id": v["video_id"], "titulo": v["titulo"]}
                for v in videos[:10]  # muestra hasta 10 como ejemplo
            ],
        })

    comunidades.sort(key=lambda c: c["size"], reverse=True)
    return comunidades


def main():
    parser = argparse.ArgumentParser(description="Comunidades Louvain del grafo")
    parser.add_argument("--min-size", type=int, default=3)
    args = parser.parse_args()

    with Neo4jClient() as db:
        comunidades = ejecutar(db, min_size=args.min_size)

    print(f"\n{len(comunidades)} comunidades (min {args.min_size} videos)\n")
    for c in comunidades:
        tags = ", ".join(c["top_hashtags"]) or "(sin hashtags)"
        print(f"  Comunidad {c['community_id']:>4}  [{c['size']:>3} videos]  {tags}")

    return comunidades


if __name__ == "__main__":
    main()

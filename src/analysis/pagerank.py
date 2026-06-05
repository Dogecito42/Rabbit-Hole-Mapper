"""
PageRank sobre el grafo de recomendaciones.

Identifica los videos mas influyentes: aquellos que reciben mas recomendaciones
desde otros videos con alto score. Un score alto indica que el algoritmo de
YouTube usa ese video como hub de distribucion de trafico.

Uso:
    python -m src.analysis.pagerank
    python -m src.analysis.pagerank --limite 20
"""

import argparse
import sys
sys.stdout.reconfigure(encoding="utf-8")

from src.database.neo4j_client import Neo4jClient

_NOMBRE_GRAFO = "grafo"

_PAGERANK = """
CALL gds.pageRank.stream($nombre_grafo)
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS v, score
RETURN v.video_id AS video_id,
       v.titulo   AS titulo,
       v.hashtags AS hashtags,
       round(score * 10000) / 10000 AS score
ORDER BY score DESC
LIMIT $limite
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


def ejecutar(db: Neo4jClient, limite: int = 20) -> list[dict]:
    _asegurar_proyeccion(db)
    with db._driver.session() as session:
        return session.run(_PAGERANK, nombre_grafo=_NOMBRE_GRAFO, limite=limite).data()


def main():
    parser = argparse.ArgumentParser(description="PageRank del grafo de recomendaciones")
    parser.add_argument("--limite", type=int, default=20)
    args = parser.parse_args()

    with Neo4jClient() as db:
        resultados = ejecutar(db, limite=args.limite)

    print(f"\n{'RANK':<5} {'SCORE':<8} {'TITULO'}")
    print("-" * 60)
    for i, r in enumerate(resultados, 1):
        titulo = (r["titulo"] or r["video_id"] or "?")[:45]
        print(f"{i:<5} {r['score']:<8} {titulo}")

    return resultados


if __name__ == "__main__":
    main()

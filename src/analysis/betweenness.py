"""
Betweenness Centrality sobre el grafo de recomendaciones.

Identifica los videos que actuan como puente entre comunidades distintas.
Un betweenness alto indica que ese video aparece en muchos caminos cortos
entre otros pares de videos, lo que lo convierte en potencial puerta de
entrada a nichos de contenido que el usuario no buscaba.

Uso:
    python -m src.analysis.betweenness
    python -m src.analysis.betweenness --limite 15
"""

import argparse
import sys
sys.stdout.reconfigure(encoding="utf-8")

from src.database.neo4j_client import Neo4jClient

_NOMBRE_GRAFO = "grafo"

_BETWEENNESS = """
CALL gds.betweenness.stream($nombre_grafo)
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS v, score
WHERE score > 0
RETURN v.video_id AS video_id,
       v.titulo   AS titulo,
       v.hashtags AS hashtags,
       round(score * 100) / 100 AS score
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


def ejecutar(db: Neo4jClient, limite: int = 10) -> list[dict]:
    _asegurar_proyeccion(db)
    with db._driver.session() as session:
        return session.run(_BETWEENNESS, nombre_grafo=_NOMBRE_GRAFO, limite=limite).data()


def main():
    parser = argparse.ArgumentParser(description="Betweenness Centrality del grafo")
    parser.add_argument("--limite", type=int, default=10)
    args = parser.parse_args()

    with Neo4jClient() as db:
        resultados = ejecutar(db, limite=args.limite)

    print(f"\n{'RANK':<5} {'SCORE':<10} {'TITULO'}")
    print("-" * 65)
    for i, r in enumerate(resultados, 1):
        titulo = (r["titulo"] or r["video_id"] or "?")[:48]
        print(f"{i:<5} {r['score']:<10} {titulo}")

    return resultados


if __name__ == "__main__":
    main()

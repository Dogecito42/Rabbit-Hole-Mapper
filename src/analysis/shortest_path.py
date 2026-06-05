"""
Camino mas corto hasta el contenido mas extremo del grafo (PQ1).

Primero enriquece los nodos Video con el extremismo medio registrado en sus
interacciones, luego calcula la distancia en saltos desde el video con menor
extremismo hasta el video con mayor extremismo para cada perfil.

Como el extremismo registrado en esta sesion es bajo (0.02-0.07), se usan los
cuantiles del dataset real en vez de un umbral fijo de 0.8, que podria no
tener ningun candidato.

Uso:
    python -m src.analysis.shortest_path
    python -m src.analysis.shortest_path --perfil casual
"""

import argparse
import sys
sys.stdout.reconfigure(encoding="utf-8")

from src.database.neo4j_client import Neo4jClient

_NOMBRE_GRAFO = "grafo"

# Escribe el extremismo medio de cada video como propiedad del nodo Video
# para que GDS pueda usarlo como coste.
_ENRIQUECER_EXTREMISMO = """
MATCH (p:Perfil)-[r:INTERACTUO]->(v:Video)
WITH v, avg(r.extremismo) AS extremismo_medio
SET v.extremismo_medio = extremismo_medio
"""

# Origen: video con menor extremismo que haya visto el perfil
_ORIGEN_PERFIL = """
MATCH (p:Perfil {nombre: $perfil})-[r:INTERACTUO]->(v:Video)
WHERE v.extremismo_medio IS NOT NULL
RETURN v.video_id AS video_id, v.titulo AS titulo, v.extremismo_medio AS extremismo
ORDER BY extremismo ASC
LIMIT 1
"""

# Destino: video con mayor extremismo del grafo completo
_DESTINO_GLOBAL = """
MATCH (v:Video)
WHERE v.extremismo_medio IS NOT NULL
RETURN v.video_id AS video_id, v.titulo AS titulo, v.extremismo_medio AS extremismo
ORDER BY extremismo DESC
LIMIT 1
"""

_SHORTEST_PATH = """
MATCH (origen:Video {video_id: $origen_id}),
      (destino:Video {video_id: $destino_id})
CALL gds.shortestPath.dijkstra.stream($nombre_grafo, {
    sourceNode: id(origen),
    targetNode: id(destino)
})
YIELD path
RETURN length(path) AS saltos,
       [n IN nodes(path) | n.titulo] AS titulos,
       [n IN nodes(path) | n.video_id] AS ids
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


def ejecutar(db: Neo4jClient, perfil: str | None = None) -> list[dict]:
    """
    Devuelve la distancia en saltos desde el video menos extremo hasta el mas
    extremo, calculada por separado para cada perfil (o solo el indicado).
    """
    # Enriquecer nodos con extremismo medio antes de proyectar
    with db._driver.session() as session:
        session.run(_ENRIQUECER_EXTREMISMO)

    _asegurar_proyeccion(db)

    perfiles = [perfil] if perfil else ["casual", "gamer", "info"]
    resultados = []

    with db._driver.session() as session:
        destino = session.run(_DESTINO_GLOBAL).single()
        if not destino:
            print("No hay videos con extremismo registrado.")
            return []

        for p in perfiles:
            origen = session.run(_ORIGEN_PERFIL, perfil=p).single()
            if not origen:
                continue

            path_result = session.run(
                _SHORTEST_PATH,
                nombre_grafo=_NOMBRE_GRAFO,
                origen_id=origen["video_id"],
                destino_id=destino["video_id"],
            ).single()

            resultados.append({
                "perfil": p,
                "origen_video_id": origen["video_id"],
                "origen_titulo": origen["titulo"],
                "origen_extremismo": origen["extremismo"],
                "destino_video_id": destino["video_id"],
                "destino_titulo": destino["titulo"],
                "destino_extremismo": destino["extremismo"],
                "saltos": path_result["saltos"] if path_result else None,
                "camino_ids": path_result["ids"] if path_result else [],
            })

    return resultados


def main():
    parser = argparse.ArgumentParser(description="Shortest Path hasta contenido extremo")
    parser.add_argument("--perfil", choices=["casual", "gamer", "info"], default=None)
    args = parser.parse_args()

    with Neo4jClient() as db:
        resultados = ejecutar(db, perfil=args.perfil)

    print(f"\n{'PERFIL':<10} {'SALTOS':<8} {'ORIGEN → DESTINO'}")
    print("-" * 70)
    for r in resultados:
        origen = (r["origen_titulo"] or r["origen_video_id"] or "?")[:25]
        destino = (r["destino_titulo"] or r["destino_video_id"] or "?")[:25]
        saltos = r["saltos"] if r["saltos"] is not None else "sin camino"
        print(f"{r['perfil']:<10} {str(saltos):<8} {origen} → {destino}")

    return resultados


if __name__ == "__main__":
    main()

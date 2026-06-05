"""
Genera el informe final con los resultados de los 4 algoritmos GDS.

Exporta results/metricas_finales.json con las respuestas a las preguntas
de investigacion PQ1-PQ4 y un graphml del grafo completo.

Uso:
    python -m src.analysis.report
"""

import json
import sys
sys.stdout.reconfigure(encoding="utf-8")
from datetime import datetime
from pathlib import Path

from src.database.neo4j_client import Neo4jClient
from src.analysis import pagerank, louvain, betweenness, shortest_path

RESULTS_DIR = Path("results")

_EXPORT_GRAPHML = """
CALL apoc.export.graphml.all($ruta, {})
"""

_AISLAMIENTO_PERFILES = """
MATCH (v:Video)<-[:RECOMIENDA {perfil: 'casual'}]-()
WITH collect(DISTINCT v.video_id) AS ids_casual
MATCH (v:Video)<-[:RECOMIENDA {perfil: 'gamer'}]-()
WITH ids_casual, collect(DISTINCT v.video_id) AS ids_gamer
RETURN
    size(ids_casual) AS total_casual,
    size(ids_gamer)  AS total_gamer,
    size([x IN ids_gamer WHERE NOT x IN ids_casual]) AS exclusivos_gamer,
    size([x IN ids_casual WHERE NOT x IN ids_gamer]) AS exclusivos_casual
"""


def _pq4_aislamiento(db: Neo4jClient) -> dict:
    """PQ4: porcentaje de nodos exclusivos entre subgrafo CASUAL y GAMER."""
    with db._driver.session() as session:
        row = session.run(_AISLAMIENTO_PERFILES).single()
        if not row:
            return {}
        total_gamer = row["total_gamer"] or 1
        total_casual = row["total_casual"] or 1
        return {
            "total_casual": row["total_casual"],
            "total_gamer": row["total_gamer"],
            "exclusivos_gamer": row["exclusivos_gamer"],
            "exclusivos_casual": row["exclusivos_casual"],
            "pct_exclusivo_gamer": round(row["exclusivos_gamer"] / total_gamer * 100, 1),
            "pct_exclusivo_casual": round(row["exclusivos_casual"] / total_casual * 100, 1),
        }


def ejecutar() -> dict:
    RESULTS_DIR.mkdir(exist_ok=True)

    with Neo4jClient() as db:
        print("Ejecutando PageRank...")
        pr = pagerank.ejecutar(db, limite=20)

        print("Ejecutando Louvain...")
        lv = louvain.ejecutar(db, min_size=3)

        print("Ejecutando Betweenness Centrality...")
        bc = betweenness.ejecutar(db, limite=10)

        print("Ejecutando Shortest Path...")
        sp = shortest_path.ejecutar(db)

        print("Calculando aislamiento entre perfiles (PQ4)...")
        pq4 = _pq4_aislamiento(db)

    informe = {
        "generado_en": datetime.now().isoformat(),
        "pq1_distancia_contenido_extremo": sp,
        "pq3_nodos_puente_betweenness": bc,
        "pq4_aislamiento_perfiles": pq4,
        "pagerank_top20": pr,
        "louvain_comunidades": lv,
    }

    ruta = RESULTS_DIR / "metricas_finales.json"
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(informe, f, ensure_ascii=False, indent=2)

    print(f"\nInforme guardado en {ruta}")
    _imprimir_resumen(informe)
    return informe


def _imprimir_resumen(informe: dict):
    print("\n========== RESUMEN DE RESULTADOS ==========")

    print("\nPQ1 — Distancia al contenido mas extremo:")
    for r in informe["pq1_distancia_contenido_extremo"]:
        saltos = r["saltos"] if r["saltos"] is not None else "sin camino"
        print(f"  {r['perfil']:<10} {saltos} saltos")

    print("\nPQ3 — Top 5 nodos puente (Betweenness):")
    for r in informe["pq3_nodos_puente_betweenness"][:5]:
        titulo = (r["titulo"] or r["video_id"] or "?")[:40]
        print(f"  {r['score']:<10} {titulo}")

    print("\nPQ4 — Aislamiento entre perfiles:")
    pq4 = informe["pq4_aislamiento_perfiles"]
    if pq4:
        print(f"  Videos exclusivos de GAMER:  {pq4['pct_exclusivo_gamer']}%")
        print(f"  Videos exclusivos de CASUAL: {pq4['pct_exclusivo_casual']}%")

    print(f"\nComunidades Louvain detectadas: {len(informe['louvain_comunidades'])}")
    print("===========================================")


if __name__ == "__main__":
    ejecutar()

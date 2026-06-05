"""
Informe rapido de metricas del grafo de recomendaciones.

Uso:
    python -m src.analysis.stats
    python -m src.analysis.stats --perfil gamer
"""

import argparse
import sys
sys.stdout.reconfigure(encoding="utf-8")

from src.database.neo4j_client import Neo4jClient
from src.database.queries import (
    stats_grafo,
    videos_mas_recomendados,
    extremismo_perfil,
)

PERFILES = ["casual", "gamer", "info"]

# ---------------------------------------------------------------------------
# Queries especificas de este modulo
# ---------------------------------------------------------------------------

_ACCIONES_PERFIL = """
MATCH (p:Perfil {nombre: $perfil})-[r:INTERACTUO]->(:Video)
RETURN r.accion AS accion, count(*) AS total
ORDER BY total DESC
"""

_TOP_HASHTAGS_PERFIL = """
MATCH (p:Perfil {nombre: $perfil})-[:INTERACTUO]->(v:Video)
UNWIND v.hashtags AS tag
WITH tag WHERE tag IS NOT NULL AND tag <> ''
RETURN tag, count(*) AS veces
ORDER BY veces DESC
LIMIT 10
"""

_AFINIDAD_PERFIL = """
MATCH (p:Perfil {nombre: $perfil})-[r:INTERACTUO]->(:Video)
RETURN
    round(avg(r.afinidad) * 100) / 100 AS afinidad_media,
    round(avg(r.extremismo) * 100) / 100 AS extremismo_medio,
    round(avg(CASE WHEN r.like THEN 1.0 ELSE 0.0 END) * 100) / 100 AS ratio_like,
    count(r) AS total_videos
"""


# ---------------------------------------------------------------------------
# Helpers de formato
# ---------------------------------------------------------------------------

def _sep(titulo: str = ""):
    ancho = 52
    if titulo:
        print(f"\n-- {titulo} {'-' * (ancho - len(titulo) - 3)}")
    else:
        print("-" * ancho)


def _barra(valor: float, maximo: float, ancho: int = 20) -> str:
    if maximo == 0:
        return " " * ancho
    lleno = round(valor / maximo * ancho)
    return "#" * lleno + "." * (ancho - lleno)


# ---------------------------------------------------------------------------
# Secciones del informe
# ---------------------------------------------------------------------------

def _informe_global(db: Neo4jClient):
    stats = stats_grafo(db)
    _sep("GRAFO GLOBAL")
    print(f"  Videos           {stats['videos']:>6}")
    print(f"  Recomendaciones  {stats['recomendaciones']:>6}")
    print(f"  Interacciones    {stats['interacciones']:>6}")


def _informe_hubs(db: Neo4jClient):
    _sep("VIDEOS MAS RECOMENDADOS (hubs)")
    filas = videos_mas_recomendados(db, limite=10)
    if not filas:
        print("  Sin datos")
        return
    maximo = filas[0]["veces"]
    for f in filas:
        titulo = (f["titulo"] or f["video_id"] or "?")[:32]
        barra = _barra(f["veces"], maximo)
        print(f"  {barra} {f['veces']:>3}  {titulo}")


def _informe_perfil(db: Neo4jClient, perfil: str):
    _sep(f"PERFIL: {perfil.upper()}")

    with db._driver.session() as session:
        afinidad = session.run(_AFINIDAD_PERFIL, perfil=perfil).single()
        if not afinidad or afinidad["total_videos"] == 0:
            print("  Sin datos")
            return

        print(f"  Videos analizados  {afinidad['total_videos']:>5}")
        print(f"  Afinidad media     {afinidad['afinidad_media']:>5.2f}")
        print(f"  Extremismo medio   {afinidad['extremismo_medio']:>5.2f}")
        print(f"  Ratio like         {afinidad['ratio_like']:>5.2f}")

        print()
        acciones = session.run(_ACCIONES_PERFIL, perfil=perfil).data()
        total_acc = sum(a["total"] for a in acciones)
        for a in acciones:
            pct = a["total"] / total_acc * 100 if total_acc else 0
            barra = _barra(a["total"], total_acc)
            print(f"  {barra} {pct:4.0f}%  {a['accion'] or 'desconocida'}")

        print()
        hashtags = session.run(_TOP_HASHTAGS_PERFIL, perfil=perfil).data()
        if hashtags:
            maximo = hashtags[0]["veces"]
            print("  Top hashtags:")
            for h in hashtags:
                barra = _barra(h["veces"], maximo, ancho=12)
                print(f"    {barra} {h['veces']:>3}  #{h['tag']}")


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Metricas del grafo de recomendaciones")
    parser.add_argument("--perfil", choices=PERFILES, default=None)
    args = parser.parse_args()

    perfiles = [args.perfil] if args.perfil else PERFILES

    with Neo4jClient() as db:
        _informe_global(db)
        _informe_hubs(db)
        for perfil in perfiles:
            _informe_perfil(db, perfil)

    print()
    _sep()


if __name__ == "__main__":
    main()

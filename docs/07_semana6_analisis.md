# Semana 6 — Analisis Big Data con Neo4j GDS

## Objetivo

Ejecutar los algoritmos de analisis de grafos sobre el dataset completo y
extraer conclusiones cuantitativas sobre polarizacion y formacion de camaras de eco.

## Preparacion: proyectar el grafo en memoria de GDS

Antes de ejecutar cualquier algoritmo GDS hay que proyectar el grafo:

```cypher
CALL gds.graph.project(
  'grafo',
  'Video',
  'RECOMIENDA'
)
```

## PageRank — videos mas influyentes y nodos puente

```cypher
CALL gds.pageRank.stream('grafo')
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).titulo AS video,
       gds.util.asNode(nodeId).categoria AS categoria,
       score
ORDER BY score DESC
LIMIT 20
```

Esto identifica los videos que actuan como "hub" de recomendacion: los que
mas recomendaciones reciben y desde los que se distribuye mas trafico.

## Shortest Path — distancia al contenido extremo

Camino mas corto desde un video neutro (entretenimiento) hasta contenido extremo (extremismo > 0.8):

```cypher
MATCH (inicio:Video {categoria: 'entretenimiento'}),
      (fin:Video) WHERE fin.extremismo > 0.8
CALL gds.shortestPath.dijkstra.stream('grafo', {
  sourceNode: id(inicio),
  targetNode: id(fin)
})
YIELD path
RETURN path
LIMIT 1
```

Repetir para cada perfil de agente filtrando las aristas por `agente`.
La longitud del camino minimo es la respuesta a PQ1.

## Louvain — deteccion de camaras de eco

```cypher
CALL gds.louvain.stream('grafo')
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).titulo AS video, communityId
ORDER BY communityId
```

Cada comunidad detectada es un potencial cluster tematico o camara de eco.
Analizar que categorias dominan en cada comunidad para caracterizarlas.

## Betweenness Centrality — nodos con mayor poder de conexion

```cypher
CALL gds.betweenness.stream('grafo')
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).titulo AS video, score
ORDER BY score DESC
LIMIT 10
```

Los top-10 son los "nodos puente": videos que conectan comunidades distintas
y que potencialmente actuan como puerta de entrada a nichos toxicos (responde PQ3).

## Aislamiento entre perfiles

Calcular el porcentaje de nodos NO compartidos entre el subgrafo de CASUAL y el de GAMER:

```cypher
MATCH (v:Video)<-[:RECOMIENDA {agente: 'casual'}]-()
WITH collect(v.id) AS ids_casual
MATCH (v:Video)<-[:RECOMIENDA {agente: 'gamer'}]-()
WITH ids_casual, collect(v.id) AS ids_gamer
RETURN size([x IN ids_gamer WHERE NOT x IN ids_casual]) * 1.0 / size(ids_gamer)
AS porcentaje_exclusivo_gamer
```

## Estructura de ficheros sugerida

```
src/
  analysis/
    pagerank.py
    shortest_path.py
    louvain.py
    betweenness.py
    report.py      genera un informe CSV/JSON con todos los resultados
notebooks/
  exploracion.ipynb   visualizaciones con pandas y matplotlib
```

## Entregable de la semana

Informe con resultados cuantitativos que responda las 4 preguntas de investigacion:
- PQ1: distancia en numero de recomendaciones hasta contenido extremo por perfil
- PQ2: velocidad de atrapamiento (numero de videos hasta que el 80% de recomendaciones son del mismo cluster)
- PQ3: lista de los top-10 nodos puente con su Betweenness Centrality
- PQ4: porcentaje de nodos exclusivos entre subgrafo CASUAL y subgrafo GAMER

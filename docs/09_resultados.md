# Resultados esperados

Esta es la referencia de que numeros y graficas debe producir el sistema al final.
Sirve para saber si el proyecto ha funcionado correctamente.

## Grafo de recomendaciones

- 500 a 1000 nodos Video
- 800 a 2000 aristas RECOMIENDA
- 3 subgrafos diferenciados, uno por perfil de agente (CASUAL, GAMER, INFO)

## Distancia al contenido extremo (PQ1)

Numero de recomendaciones consecutivas desde un video neutro hasta el primer
video con extremismo > 0.8, medido por separado para cada perfil.
Se espera que GAMER tenga la distancia mas corta y INFO la mas larga.

## Velocidad de atrapamiento (PQ2)

Numero de videos necesarios hasta que el 80% de las recomendaciones del agente
pertenezcan al mismo cluster de Louvain.
Indica con que rapidez el algoritmo encierra a cada perfil en su camara de eco.

## Nodos puente (PQ3)

Lista de los top-10 videos por Betweenness Centrality.
Estos son los videos que actuan como puerta de entrada a nichos extremos,
comunes a varios perfiles de usuario.

## Aislamiento entre perfiles (PQ4)

Porcentaje de nodos que aparecen en el subgrafo GAMER pero no en el subgrafo CASUAL.
Un porcentaje alto indica que los algoritmos sirven contenidos completamente distintos
segun el perfil, confirmando la existencia de camaras de eco diferenciadas.

## Curva de aprendizaje RL

Grafica de recompensa acumulada por episodio para cada agente.
Debe mostrar tendencia creciente, demostrando que el agente mejora sus decisiones
de navegacion con el tiempo mediante Q-Learning.

## Formato de entrega de resultados

- Fichero `results/metricas_finales.json` con todos los valores numericos
- Fichero `results/grafo_export.graphml` con el grafo completo exportado de Neo4j
- Visualizacion interactiva en Neo4j Bloom para la defensa
- Graficas en `results/figuras/` (PNG, generadas con matplotlib)

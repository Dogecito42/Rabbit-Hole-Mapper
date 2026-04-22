# RabbitHole Mapper

Trabajo de Fin de Grado — Documento de Diseño y Arquitectura v1.0

Mapeo Topológico de Algoritmos de Recomendación en Formatos Short-Video mediante Agentes Autonomos LLM y Bases de Datos de Grafos.

## Que es

RabbitHole Mapper es un sistema multi-agente que simula el comportamiento de distintos perfiles de usuario en YouTube Shorts para mapear y cuantificar como los algoritmos de recomendacion generan camaras de eco y polarizacion de contenido. Los agentes aprenden mediante Reinforcement Learning (Q-Learning) y toda la estructura de recomendaciones se almacena y analiza en Neo4j.

El sistema corre completamente en local, sin coste de infraestructura, sobre una GPU NVIDIA RTX 3070.

## Problema que resuelve

Los algoritmos de TikTok y YouTube son cajas negras opacas. Demostrar empiricamente que generan "rabbit holes" requeriría decenas de investigadores viendo videos durante semanas. Este proyecto sustituye a los investigadores humanos por agentes de IA que navegan de forma autonoma y generan un dataset reproducible y auditable.

## Arquitectura — 4 capas

- Capa 1: Extracción de datos con Playwright (navegacion headless, metadatos de video, transcripciones)
- Capa 2: Agentes LLM con Ollama + Llama 3.1 8B (evaluacion de contenido, decision JSON estructurada)
- Capa 3: Reinforcement Learning con Q-Learning (aprendizaje de que acciones maximizan la recompensa segun el perfil)
- Capa 4: Big Data y grafos con Neo4j + neovis.js (almacenamiento, analisis y visualizacion del grafo de recomendaciones)

## Perfiles de agente

Se definen tres perfiles con psicografia diferenciada:

- CASUAL: usuario de 25 años con intereses generales, entretenimiento neutro y humor familiar
- GAMER: usuario de 18 años, cultura de internet, alto umbral de tolerancia a contenido intenso — el perfil mas vulnerable a rabbit holes extremos
- INFO: usuario de 35 años, contenido educativo y divulgativo, actua como grupo de control

## Stack tecnologico

Python 3.11, Playwright, Ollama, Llama 3.1 8B, NumPy (Q-Learning), Neo4j, neovis.js, YouTube Transcript API

## Preguntas de investigacion

- A cuantas recomendaciones de distancia se encuentra el contenido extremo desde un video neutro segun cada perfil?
- Con que velocidad queda atrapado cada perfil en su camara de eco?
- Existen nodos puente que actuen como puerta de entrada a nichos toxicos para todos los perfiles?
- Los grafos de distintos perfiles son topologicamente disjuntos?


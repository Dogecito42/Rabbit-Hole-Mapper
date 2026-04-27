# Minimo producto viable (MVP)

Esta es la lista minima que debe funcionar para considerar el proyecto completo.
Los elementos marcados como "imprescindible" son obligatorios para la entrega academica.

## Imprescindibles

- [ ] Playwright extrae datos reales de YouTube Shorts (titulos, transcripciones, siguiente video)
      Cubre: Programacion de IA

- [ ] LLM (Llama 3.1 via Ollama) toma decisiones diferenciadas segun el perfil del agente
      Cubre: Modelos de IA

- [ ] Q-Learning basico con Q-table funcional: el agente aprende y mejora con el tiempo
      Cubre: Sistemas de Aprendizaje Autonomos

- [ ] Neo4j almacena el grafo de recomendaciones con nodos Video y aristas RECOMIENDA
      Cubre: Sistemas Big Data

- [ ] Visualizacion del grafo funcionando en Neo4j Bloom o neovis.js
      Cubre: Big Data Aplicado

## Recomendados

- [ ] Analisis PageRank y Shortest Path sobre el grafo completo con resultados exportados

- [ ] Los 3 agentes (CASUAL, GAMER, INFO) corren de forma simultanea en sesiones separadas

## Ideal (si el tiempo lo permite)

- [ ] Simulacion de 24h o mas con dataset de 500+ nodos y 800+ aristas

- [ ] Informe cuantitativo que responde las 4 preguntas de investigacion con datos reales

## Criterio de "listo para entregar"

El sistema es entregable cuando los 5 elementos imprescindibles funcionan de extremo a extremo:
crawler captura -> LLM decide -> Q-table aprende -> Neo4j almacena -> visualizacion muestra el grafo.

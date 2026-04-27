# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Que es este proyecto

RabbitHole Mapper es un TFG que mapea los algoritmos de recomendacion de YouTube Shorts
mediante agentes autonomos LLM. Simula 3 perfiles de usuario (CASUAL, GAMER, INFO),
aprende con Q-Learning que contenido consume cada perfil, y almacena el grafo de
recomendaciones en Neo4j para analizarlo con algoritmos de centralidad y comunidades.

Toda la ejecucion es local (sin cloud). Hardware objetivo: NVIDIA RTX 3070.

## Comandos principales

```bash
# Instalar dependencias y navegador
pip install -r requirements.txt
playwright install chromium

# Primer login de un perfil (abre ventana visible para autenticacion de Google)
python main.py --perfil casual --videos 5 --headless false

# Sesion normal de crawling
python main.py --perfil casual --videos 50
python main.py --perfil gamer  --videos 50
python main.py --perfil info   --videos 50
```

## Arquitectura — 4 capas implementadas por semanas

```
Semana 1  Capa 1  src/crawler/       Playwright extrae metadatos de YouTube Shorts
Semana 2  Capa 2  src/agents/        Agentes LLM via Ollama + Llama 3.1 8B
Semana 3  Capa 4  src/database/      Neo4j almacena el grafo de recomendaciones
Semana 4  Capa 3  src/rl/            Q-Learning aprende que acciones maximizan recompensa
Semana 5  —       src/               Simulacion larga con los 3 agentes simultaneos
Semana 6  Capa 4  src/analysis/      PageRank, Louvain, Shortest Path, Betweenness
Semana 7  —       —                  Memoria tecnica y demo
```

El flujo de datos es lineal entre capas:
YouTube Shorts -> crawler -> agente LLM -> Q-table -> Neo4j -> analisis de grafo

## Estado actual

Semanas 1 y 2 implementadas. Semanas 3-7 pendientes.
Ver docs/ para la guia detallada de cada semana y su entregable.

## Modulos implementados (src/agents/)

- `profiles.py` — `PERFILES`: dict con system prompts de los 3 perfiles y `ACCIONES_VALIDAS`.

- `llm_client.py` — `LLMClient`: llama a Ollama via REST, extrae el JSON de la respuesta
  con regex tolerante a texto libre alrededor del bloque, valida campos obligatorios y normaliza tipos.

- `agent.py` — `Agent` + `Decision`: recibe un `VideoMetadata`, lo convierte a texto para el LLM,
  devuelve una `Decision` tipada. Si el LLM falla, devuelve fallback conservador (accion=skip,
  llm_ok=False) para no interrumpir la sesion.

## Modulos implementados (src/crawler/)

- `browser.py` — `BrowserSession`: lanza Chromium con anti-deteccion, carga/guarda
  `storage_state` de Google por perfil en `data/browser_state/<perfil>.json`.
  Primera ejecucion abre modo visible para login manual; las siguientes son headless.

- `extractor.py` — `VideoExtractor`: extrae del DOM el video_id, titulo, hashtags y
  `next_video_id` (primer enlace `/shorts/<id>` distinto al actual). Devuelve `VideoMetadata`.

- `transcript.py` — `TranscriptFetcher`: descarga transcripciones via `youtube-transcript-api`.
  Devuelve cadena vacia si no hay transcripcion; nunca lanza excepcion.

- `session.py` — `CrawlerSession`: bucle principal. Checkpoint cada 10 videos en `data/raw/`.

- `src/config.py` — unica fuente de verdad para rutas, seeds por perfil y parametros.
  Los `seed_video_id` son placeholders; deben sustituirse por IDs reales antes de ejecutar.

## Variables de entorno (.env)

Copiar `.env.example` a `.env`. Las variables criticas para semanas posteriores:

```
NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD   semana 3+
OLLAMA_HOST                                semana 2+
CRAWLER_DELAY_MIN / CRAWLER_DELAY_MAX      anti-deteccion (default 2-8 s)
```

## Convenciones

- Todo el codigo y la documentacion en español.
- Sin emojis en ningun fichero.
- Los docstrings explican el WHY (por que existe esa logica), no el WHAT.
- Al implementar una semana, actualizar el fichero `docs/0N_semanaX_*.md` correspondiente
  para reflejar el estado real: comandos funcionales, decisiones tomadas, pendientes.
- Los selectores CSS del DOM de YouTube estan en `extractor.py` como constantes `_SEL_*`.
  Son los puntos mas fragiles del sistema: actualizar si YouTube cambia su frontend.

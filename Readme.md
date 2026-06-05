<div align="center">

<img src="https://github.com/user-attachments/assets/c09530b9-5836-41d9-a2cf-630ea32a7028" width="180" alt="RabbitHole Mapper logo"/>

# RabbitHole Mapper

**Mapeo topológico de algoritmos de recomendación en short-video**  
mediante agentes autónomos LLM y bases de datos de grafos

<br/>

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Llama](https://img.shields.io/badge/Llama-3.1_8B-0467DF?style=flat-square&logo=meta&logoColor=white)](https://llama.meta.com)
[![Neo4j](https://img.shields.io/badge/Neo4j-GDS-008CC1?style=flat-square&logo=neo4j&logoColor=white)](https://neo4j.com)
[![Playwright](https://img.shields.io/badge/Playwright-Chromium-2EAD33?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![TFG](https://img.shields.io/badge/TFG-Big_Data_&_IA-8B5CF6?style=flat-square)](.)
[![Local](https://img.shields.io/badge/Runs-100%25_Local-22C55E?style=flat-square&logo=nvidia&logoColor=white)](.)

<br/>

> *¿A cuántas recomendaciones de distancia está el contenido extremo desde un vídeo neutro?*  
> *¿En cuántos vídeos queda atrapado un usuario en su cámara de eco?*

<br/>


</div>

---

## ¿Qué es?

**RabbitHole Mapper** es un sistema multi-agente de investigación empírica que simula el comportamiento de distintos perfiles de usuario en **YouTube Shorts** para mapear y cuantificar cómo los algoritmos de recomendación generan *cámaras de eco* y *rabbit holes* de contenido.

Los agentes aprenden mediante **Q-Learning** qué acciones maximizan su exposición a contenido afín, y toda la estructura de recomendaciones se almacena y analiza como un **grafo dirigido en Neo4j**.

El sistema corre **completamente en local** sobre una GPU NVIDIA RTX 3070 — sin coste de infraestructura, sin APIs externas, sin datos enviados a terceros.


## Características principales

| | |
|---|---|
|  **Agentes autónomos** | Tres perfiles psicográficos que navegan Shorts como usuarios reales |
|  **LLM local** | Llama 3.1 8B via Ollama — clasificación y decisión sin APIs de pago |
|  **Reinforcement Learning** | Q-Learning tabular que aprende políticas de navegación por perfil |
|  **Grafo auditable** | Neo4j + GDS con PageRank, Louvain, Betweenness y Shortest Path |
|  **Anti-detección** | Playwright con stealth script, delays aleatorios y simulación de swipe |
|  **Reproducible** | Checkpoints cada 10 vídeos, Q-tables persistentes entre sesiones |

---

##  Arquitectura

El sistema se organiza en **cuatro capas** con flujo de datos estrictamente lineal. Las capas 3 y 4 son opcionales — el crawler funciona de forma autónoma si Neo4j u Ollama no están disponibles.

<div align="center">

<img width="714" height="924" alt="image" src="https://github.com/user-attachments/assets/f2567886-35d8-41c2-b664-6623ea692d3e" />

</div>

##  Perfiles de agente

Tres arquetipos de usuario con psicografía diferenciada, cada uno con su propia cuenta de Google y *system prompt* para el LLM:

| Perfil | Edad | Intereses | Vulnerabilidad |
|--------|------|-----------|----------------|
|  **CASUAL** | 25 | Entretenimiento general, humor familiar | Alta — la falta de preferencias definidas es interpretada por el algoritmo como señal para servir contenido emocionalmente intenso |
|  **GAMER** | 18 | Videojuegos, cultura de internet, e-sports | Muy alta — umbral de tolerancia alto, mayor exposición a nichos extremos |
|  **INFO** | 35 | Divulgación, noticias, geopolítica | Baja — actúa como grupo de control; el algoritmo le sirve entretenimiento genérico al no encontrar su nicho |

---

## Funcionamiento del agente

### Q-Learning

El problema de navegación se formula como un **MDP (Proceso de Decisión de Markov)**:

```
Estado  S  =  (categoria_video, perfil_agente)   # ~45 combinaciones
Acciones A  =  {ver_completo, ver_parcial, skip}
Recompensa R  =  afinidad × 1.0  +  extremismo × 1.0  −  penalización
```

> El extremismo es componente **positivo** de la recompensa de forma deliberada.  
> El objetivo no es que el agente evite el contenido extremo, sino **medir si el algoritmo de YouTube lo conduce hacia él**.

```python
# Regla de actualización Q-Learning estándar (off-policy)
Q(s,a) ← Q(s,a) + α · [r + γ · max_a' Q(s',a') − Q(s,a)]

# Hiperparámetros
alpha   = 0.1    # tasa de aprendizaje
gamma   = 0.9    # factor de descuento
epsilon = 1.0    # exploración inicial → decae 0.995 por sesión hasta 0.05
```

### Anti-detección

```python
# Navegación entre vídeos — simula swipe vertical real
page.keyboard.press("ArrowDown")

# Stealth script inyectado antes de cada carga
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['es-ES', 'es', 'en'] });

# Comportamiento temporal humano
delay = random.uniform(2, 8)  # segundos entre acciones
```

---

## Instalación

### Requisitos

- Python 3.11+
- [Ollama](https://ollama.com) con modelo `llama3.1:8b`
- [Neo4j Community Edition](https://neo4j.com/download/) (o Docker)
- NVIDIA GPU recomendada (RTX 3070 o superior para Llama 3.1 8B)

### Setup

```bash
# 1. Clonar el repositorio
git clone https://github.com/doge42/rabbithole-mapper.git
cd rabbithole-mapper

# 2. Instalar dependencias
pip install -r requirements.txt
playwright install chromium

# 3. Levantar Neo4j con Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# 4. Descargar el modelo LLM
ollama pull llama3.1:8b

# 5. Configurar variables de entorno
cp .env.example .env
# → editar NEO4J_URI, NEO4J_PASSWORD, DELAY_MIN, DELAY_MAX
```

### Estructura del proyecto

```
rabbithole-mapper/
├── src/
│   ├── crawler/
│   │   ├── browser.py       # BrowserSession + anti-detección
│   │   ├── extractor.py     # VideoExtractor — DOM → metadatos
│   │   ├── transcript.py    # Descarga de subtítulos
│   │   └── session.py       # CrawlerSession — orquestador principal
│   ├── agents/
│   │   ├── profiles.py      # Definición de CASUAL, GAMER, INFO
│   │   ├── llm_client.py    # Cliente Ollama + parser robusto
│   │   └── agent.py         # Clase Decision y fallback
│   ├── rl/
│   │   ├── qtable.py        # Q-Table con defaultdict + NumPy
│   │   └── reward.py        # Función de recompensa
│   ├── database/
│   │   ├── neo4j_client.py  # MERGE idempotente + escritura en tiempo real
│   │   ├── loader.py        # Carga masiva de sesiones previas
│   │   └── queries.py       # Consultas Cypher reutilizables
│   ├── analysis/
│   │   ├── pagerank.py      # Hubs de distribución de tráfico
│   │   ├── louvain.py       # Detección de comunidades temáticas
│   │   ├── betweenness.py   # Vídeos puente entre comunidades
│   │   ├── shortest_path.py # Camino mínimo al contenido extremo
│   │   ├── stats.py         # Métricas de inspección rápida
│   │   └── report.py        # Informe consolidado GDS
│   └── config.py            # Fuente única de verdad de parámetros
├── data/
│   ├── raw/<perfil>/        # JSONs de sesión con checkpoints _partial
│   ├── qtables/             # Q-tables persistentes (.pkl)
│   └── browser_state/       # Sesiones de Google por perfil (.json)
├── docs/                    # Documentación semana a semana del desarrollo
├── scripts/
├── docker-compose.yml       # Neo4j + dependencias
├── .env.example
├── requirements.txt
└── main.py
```

---

## Uso

```bash
# Iniciar Sesión (La primera vez requiere hacer login en la plataforma)
python main.py --perfil gamer --videos 250 --headless false
```

---

## Resultados

> Experimento con **14 sesiones**, ~4.800 vídeos visitados, grafo de **4.308 nodos · 4.214 aristas**.

### Evolución de perfiles

| Perfil | Afinidad S1 → Sn | Extremismo S1 → Sn | Patrón |
|--------|------------------|---------------------|--------|
|  Casual | 0.561 → 0.417 | 0.070 → **0.191** | Deriva al extremismo (+173%) |
|  Gamer  | 0.192 → **0.403** | 0.017 → 0.022 | Recuperación por feedback activo |
|  Info   | 0.476 → 0.338 | 0.055 → 0.040 | Degradación progresiva |

### Comunidades detectadas por Louvain

```
335 comunidades sobre 4.308 vídeos

Motivación / amor     ████████████████████  224 vídeos
Humor y memes         ███████████████████   223 vídeos
Contenido religioso   █████████████████     207 vídeos
Ciencia / divulgación ████████              136 vídeos  ← 4× más pequeña
JoJo's Bizarre Adv.   ██████████            200+ vídeos (8 comunidades)
```

### Hallazgo clave — PQ3

> Las **puertas de entrada a nichos extremos** no son contenido radical.  
> Son vídeos de **curiosidades de alto enganche** con Betweenness Centrality máxima  
> que redistribuyen tráfico silenciosamente hacia comunidades adyacentes.

---

## Preguntas de Investigación

| # | Pregunta | Resultado |
|---|----------|-----------|
| **PQ1** | ¿A cuántas recomendaciones se encuentra el contenido extremo desde un vídeo neutro? | **2-4 saltos** (caso Gamer→JoJo, sin navegación deliberada) |
| **PQ2** | ¿Con qué velocidad queda atrapado cada perfil? | Gamer: sesión 1 · Casual: +173% extremismo en 5 sesiones · Info: desde el inicio |
| **PQ3** | ¿Existen nodos puente hacia nichos tóxicos? | Sí — contenido mainstream de alto enganche, no contenido radical |
| **PQ4** | ¿Son los grafos de perfiles topológicamente disjuntos? | **75%** del grafo es exclusivo de uno o dos perfiles |

---

## Stack tecnológico

<div align="center">

| Capa | Tecnología | Rol |
|------|-----------|-----|
| Extracción | `Playwright` + `Chromium` | Navegación real con anti-detección |
| Transcripciones | `youtube-transcript-api` | Subtítulos sin API oficial |
| LLM | `Ollama` + `Llama 3.1 8B` | Clasificación semántica y decisión |
| RL | `NumPy` + `pickle` | Q-Table tabular persistente |
| Base de datos | `Neo4j` Community | Grafo de recomendaciones |
| Análisis | `Neo4j GDS` | PageRank · Louvain · Betweenness · Shortest Path |
| Visualización | `neovis.js` | Grafo interactivo en el navegador |

</div>

---

## Referencias clave

- Pariser, E. (2011). *The Filter Bubble*. Penguin Press.
- Ribeiro et al. (2020). [Auditing radicalization pathways on YouTube](https://doi.org/10.1145/3351095.3372879). FAccT 2020.
- Sutton & Barto (2018). *Reinforcement Learning: An Introduction*. MIT Press.
- Sukiennik et al. (2025). [SimTok: Simulating filter bubble on short-video recommender systems](https://arxiv.org/abs/2504.08742).
- Blondel et al. (2008). [Fast unfolding of communities in large networks](https://doi.org/10.1088/1742-5468/2008/10/P10008).

---

<div align="center">

**Proyecto Final de Curso · Especialización en Big Data e Inteligencia Artificial**  
Gabriel Callejón Sánchez · 2026

</div>

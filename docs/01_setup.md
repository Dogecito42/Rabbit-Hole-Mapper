# Setup del entorno

## Requisitos de hardware

- GPU: NVIDIA RTX 3070 (8 GB VRAM) — necesaria para ejecutar Llama 3.1 8B via Ollama
- RAM: 16 GB recomendados
- Espacio en disco: ~10 GB (modelo Llama + Neo4j + dataset)

## 1. Entorno Python

```bash
python -m venv venv
source venv/bin/activate
pip install playwright youtube-transcript-api ollama neo4j numpy pandas python-dotenv
playwright install chromium
```

## 2. Ollama y el modelo LLM

Instalar Ollama desde https://ollama.com (gestor de modelos LLM en local).

```bash
ollama pull llama3.1
```

El modelo ocupa aproximadamente 4.5 GB. La primera descarga puede tardar varios minutos.
Verificar que responde:

```bash
ollama run llama3.1 "hola"
```

## 3. Neo4j Desktop

Descargar Neo4j Desktop desde https://neo4j.com/download (gratuito).
Crear un proyecto nuevo y una base de datos local con contrasena conocida.
Instalar el plugin Neo4j GDS (Graph Data Science) desde el gestor de plugins de Neo4j Desktop — es necesario para PageRank, Louvain y Shortest Path.

Verificar conexion desde Python:

```python
from neo4j import GraphDatabase
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "tu_contrasena"))
driver.verify_connectivity()
```

## 4. Variables de entorno

Crear un fichero `.env` en la raiz del proyecto:

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=tu_contrasena
OLLAMA_HOST=http://localhost:11434
```

Cargarlas en Python con:

```python
from dotenv import load_dotenv
load_dotenv()
```

## 5. Verificacion completa

Antes de empezar la semana 1, confirmar que:
- `python --version` devuelve 3.11 o superior
- `ollama run llama3.1` responde sin errores
- Neo4j Desktop muestra la base de datos en estado "Running"
- `playwright install chromium` ha completado sin errores

# Semana 5 — Simulacion larga con los 3 agentes

## Objetivo

Lanzar los tres agentes (CASUAL, GAMER, INFO) de forma simultanea durante
24-48 horas para generar el dataset final con suficiente riqueza estadistica.

## Objetivo de dataset

- 500 a 1000 nodos Video en Neo4j
- 800 a 2000 aristas RECOMIENDA
- 3 subgrafos diferenciados, uno por perfil de agente

## Arquitectura de ejecucion simultanea

Cada agente corre en su propio proceso Python para evitar bloqueos entre sesiones
de Playwright y llamadas a Ollama.

```bash
python src/main.py --perfil casual &
python src/main.py --perfil gamer  &
python src/main.py --perfil info   &
```

O usando multiprocessing:

```python
from multiprocessing import Process

perfiles = ["casual", "gamer", "info"]
procesos = [Process(target=run_agent, args=(p,)) for p in perfiles]
for p in procesos:
    p.start()
for p in procesos:
    p.join()
```

## Monitorizacion durante la simulacion

Crear un script de monitoreo que se ejecute aparte y consulte Neo4j periodicamente:

```cypher
MATCH (v:Video) RETURN count(v) AS nodos
MATCH ()-[r:RECOMIENDA]->() RETURN r.agente, count(r) AS aristas GROUP BY r.agente
```

Tambien es util loguear a fichero para detectar bloqueos o errores del LLM:

```python
import logging
logging.basicConfig(
    filename=f"logs/{perfil}_{timestamp}.log",
    level=logging.INFO,
    format="%(asctime)s %(message)s"
)
```

## Posibles problemas y como manejarlos

Bloqueo por YouTube: implementar reintentos con backoff exponencial.
Si el bloqueo es persistente, rotar la cuenta de Google o esperar 1 hora.

Respuesta malformada del LLM: capturar la excepcion de JSON parse, loguear el
raw output y repetir la llamada con temperatura mas baja (`temperature=0.1`).

Neo4j fuera de memoria: revisar que el plugin GDS no esta corriendo proyecciones
en memoria durante la escritura. Separar las fases de escritura y analisis.

## Entregable de la semana

- Dataset en Neo4j con al menos 500 nodos y 800 aristas
- Logs de las 3 sesiones sin errores fatales
- Verificacion visual en Neo4j Browser de que los 3 subgrafos existen
  y tienen densidad diferente entre si

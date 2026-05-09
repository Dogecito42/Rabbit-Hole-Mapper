# Semana 3 — Capa 4 (base): Integracion con Neo4j

## Objetivo

Conectar el sistema al grafo de Neo4j y registrar en tiempo real cada video
y cada recomendacion seguida durante la navegacion.

## Modelo de datos implementado

Nodo Video:
```
(:Video {
  video_id: STRING,    -- clave primaria (id del Short)
  titulo:   STRING,
  hashtags: [STRING]
})
```

Nodo Perfil:
```
(:Perfil {
  nombre: STRING    -- "casual" | "gamer" | "info"
})
```

Arista RECOMIENDA (YouTube mostro to_id como siguiente despues de from_id):
```
(:Video)-[:RECOMIENDA {
  perfil:    STRING,
  sesion_id: STRING,    -- timestamp ISO del inicio de sesion
  posicion:  INTEGER    -- posicion ordinal del video origen en la sesion
}]->(:Video)
```

Arista INTERACTUO (decision del agente LLM sobre ese video):
```
(:Perfil)-[:INTERACTUO {
  sesion_id:    STRING,
  posicion:     INTEGER,
  accion:       STRING,    -- "skip" | "ver_parcial" | "ver_completo"
  afinidad:     FLOAT,
  extremismo:   FLOAT,
  like:         BOOLEAN,
  comentario:   STRING,
  capturado_en: STRING
}]->(:Video)
```

## Modulos implementados

### `src/database/neo4j_client.py`

`Neo4jClient`: conexion y operaciones de escritura atomicas.

Metodos publicos:
- `merge_video(video_id, titulo, hashtags)` — upsert de nodo Video (MERGE por video_id).
- `merge_perfil(nombre)` — crea el nodo Perfil si no existe.
- `merge_recomendacion(from_id, to_id, perfil, sesion_id, posicion)` — crea arista RECOMIENDA.
- `merge_interaccion(perfil, video_id, decision, sesion_id, posicion)` — crea arista INTERACTUO.
- `cargar_sesion(sesion)` — carga un dict de sesion JSON completo (formato data/raw/).
- `close()` — cierra el driver.

Admite uso como context manager (`with Neo4jClient() as db:`).

### `src/database/queries.py`

Constantes Cypher y funciones de consulta de solo lectura.

Funciones:
- `stats_grafo(db)` — devuelve `{videos, recomendaciones, interacciones}`.
- `recomendaciones_perfil(db, perfil, limite)` — aristas RECOMIENDA de un perfil en orden.
- `videos_mas_recomendados(db, limite)` — videos mas frecuentes como destino.
- `videos_perfil(db, perfil, limite)` — videos visitados por un perfil con su decision.
- `extremismo_perfil(db, perfil)` — extremismo medio y maximo de un perfil.

### `src/database/loader.py`

Carga masiva de sesiones JSON historicas en Neo4j.
Util para cargar datos grabados antes de que Neo4j estuviera disponible.

```bash
python -m src.database.loader                  # todos los perfiles
python -m src.database.loader --perfil casual  # solo casual
```

## Integracion con el crawler

`session.py` importa `Neo4jClient` de forma opcional para no romper sesiones
si Neo4j no esta corriendo:

```python
try:
    from src.database.neo4j_client import Neo4jClient
    _NEO4J_DISPONIBLE = True
except ImportError:
    _NEO4J_DISPONIBLE = False
```

Flujo por video:
1. `merge_video(video_id, titulo, hashtags)` — registra el video actual.
2. `merge_interaccion(...)` — registra la decision del agente LLM.
3. Si hay `next_video_id`: `merge_video(next_id, None, [])` + `merge_recomendacion(...)`.

Los errores de escritura en Neo4j se capturan y loguean como `WARNING`
sin interrumpir la sesion de crawling.

## Consultas Cypher de verificacion

```cypher
-- Totales
MATCH (v:Video) RETURN count(v)
MATCH ()-[r:RECOMIENDA]->() RETURN count(r)
MATCH ()-[r:INTERACTUO]->() RETURN count(r)

-- Recomendaciones de un perfil
MATCH (a:Video)-[r:RECOMIENDA {perfil: 'gamer'}]->(b:Video)
RETURN a.titulo, b.titulo, r.posicion
ORDER BY r.sesion_id, r.posicion LIMIT 20

-- Videos mas recomendados como siguiente Short
MATCH ()-[:RECOMIENDA]->(v:Video)
RETURN v.titulo, count(*) AS veces
ORDER BY veces DESC LIMIT 10
```

Desde Python:

```python
from src.database.neo4j_client import Neo4jClient
from src.database.queries import stats_grafo, extremismo_perfil

with Neo4jClient() as db:
    print(stats_grafo(db))
    print(extremismo_perfil(db, "gamer"))
```

## Variables de entorno necesarias

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=tu_contrasena
```

## Comandos

```bash
# Cargar sesiones historicas desde data/raw/
python -m src.database.loader
python -m src.database.loader --perfil gamer

# El crawler escribe en Neo4j automaticamente si la conexion esta disponible
python main.py --perfil casual --videos 50
```

## Entregable de la semana

Grafo funcional en Neo4j con:
- Nodos Video con video_id, titulo y hashtags.
- Nodos Perfil para cada agente.
- Aristas RECOMIENDA conectando los Shorts en el orden de navegacion real.
- Aristas INTERACTUO con la decision del agente LLM por cada video.
- Visualizacion basica en Neo4j Browser confirmando la estructura de grafo.

# Semana 3 — Capa 4 (base): Integracion con Neo4j

## Objetivo

Conectar el sistema al grafo de Neo4j y registrar en tiempo real cada video
y cada recomendacion seguida durante la navegacion.

## Modelo de datos

Nodo Video:
```
(:Video {
  id: STRING,
  titulo: STRING,
  categoria: STRING,
  extremismo: FLOAT,
  capturado: DATETIME
})
```

Arista RECOMIENDA (dirigida, de video origen a video destino):
```
(:Video)-[:RECOMIENDA {
  agente: STRING,
  accion: STRING,
  recompensa: FLOAT,
  timestamp: DATETIME
}]->(:Video)
```

## Operaciones basicas en Python

Crear o actualizar un nodo video (upsert con MERGE):

```cypher
MERGE (v:Video {id: $id})
SET v.titulo = $titulo,
    v.categoria = $categoria,
    v.extremismo = $extremismo,
    v.capturado = $capturado
```

Registrar una recomendacion seguida:

```cypher
MATCH (origen:Video {id: $id_origen})
MATCH (destino:Video {id: $id_destino})
CREATE (origen)-[:RECOMIENDA {
  agente: $agente,
  accion: $accion,
  recompensa: $recompensa,
  timestamp: $timestamp
}]->(destino)
```

## Consultas Cypher de verificacion

Ver cuantos nodos y aristas hay:
```cypher
MATCH (v:Video) RETURN count(v)
MATCH ()-[r:RECOMIENDA]->() RETURN count(r)
```

Ver las recomendaciones de un agente concreto:
```cypher
MATCH (a:Video)-[r:RECOMIENDA {agente: 'gamer'}]->(b:Video)
RETURN a.titulo, b.titulo, r.recompensa LIMIT 20
```

## Integracion con el bucle principal

El flujo es: crawler extrae video -> agente LLM decide -> Neo4j registra nodo y arista -> crawler navega al siguiente.
La escritura en Neo4j debe ser asincrona o al menos no bloquear el crawler.

## Estructura de ficheros sugerida

```
src/
  database/
    neo4j_client.py   conexion, upsert de nodos, insercion de aristas
    queries.py        consultas Cypher reutilizables como constantes
```

## Entregable de la semana

Grafo funcional en Neo4j con:
- Al menos 100 nodos Video con sus propiedades completas
- Aristas RECOMIENDA conectando los videos en el orden en que fueron visitados
- Visualizacion basica en Neo4j Browser confirmando la estructura de grafo

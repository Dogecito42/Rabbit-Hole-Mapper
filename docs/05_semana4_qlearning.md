# Semana 4 — Capa 3: Q-Learning y funcion de recompensa

## Objetivo

Implementar Q-Learning para que cada agente aprenda que acciones de navegacion
maximizan su recompensa acumulada a lo largo del tiempo.

## Definicion del MDP

El problema se modela como un Proceso de Decision de Markov (MDP):

- Estado (S): tupla (categoria_video_actual, perfil_agente)
  Ejemplo: ("gaming", "gamer"), ("politica", "casual")

- Accion (A): ver_completo / ver_parcial / skip / like

- Recompensa (R): definida por la funcion compuesta (ver abajo)

- Politica (pi): epsilon-greedy
  Al inicio explora aleatoriamente (epsilon alto).
  Con el tiempo explota lo aprendido (epsilon decae).

## Funcion de recompensa

```
R(s, a, s') = R_afinidad + R_extremismo + R_penalizacion
```

Donde:
- R_afinidad    = afinidad(s', perfil) * 1.0    -- el siguiente video encaja con el perfil
- R_extremismo  = extremismo(s') * 1.0           -- bonus si el video es mas extremo (mide radicalizacion)
- R_penalizacion = -1.0 si afinidad(s') < 0.3   -- penalizacion si el siguiente video no encaja

Tanto afinidad como extremismo son los floats devueltos por el LLM al evaluar el video siguiente.

## Implementacion de la Q-table

```python
import numpy as np
from collections import defaultdict

# Q-table: diccionario estado -> array de Q-values por accion
q_table = defaultdict(lambda: np.zeros(4))
ACCIONES = ["ver_completo", "ver_parcial", "skip", "like"]

def elegir_accion(estado, epsilon):
    if np.random.random() < epsilon:
        return np.random.randint(4)       # exploracion
    return np.argmax(q_table[estado])     # explotacion

def actualizar_q(estado, accion_idx, recompensa, siguiente_estado, alpha=0.1, gamma=0.9):
    q_actual = q_table[estado][accion_idx]
    q_target = recompensa + gamma * np.max(q_table[siguiente_estado])
    q_table[estado][accion_idx] += alpha * (q_target - q_actual)
```

## Decaimiento de epsilon

```python
epsilon = 1.0
epsilon_min = 0.05
epsilon_decay = 0.995

# Al final de cada episodio (sesion de navegacion):
epsilon = max(epsilon_min, epsilon * epsilon_decay)
```

## Integracion en el bucle principal

```
Para cada video en la sesion:
  1. estado = (categoria_actual, perfil)
  2. accion_idx = elegir_accion(estado, epsilon)
  3. Ejecutar accion en el navegador
  4. LLM evalua el video siguiente -> afinidad, extremismo
  5. recompensa = calcular_recompensa(afinidad, extremismo)
  6. siguiente_estado = (categoria_siguiente, perfil)
  7. actualizar_q(estado, accion_idx, recompensa, siguiente_estado)
  8. Registrar en Neo4j con la recompensa calculada
```

## Persistencia de la Q-table

Guardar y cargar la Q-table entre sesiones para que el aprendizaje sea acumulativo:

```python
import pickle
# Guardar
with open(f"data/qtable_{perfil}.pkl", "wb") as f:
    pickle.dump(dict(q_table), f)
# Cargar
with open(f"data/qtable_{perfil}.pkl", "rb") as f:
    q_table.update(pickle.load(f))
```

## Entregable de la semana

Agente que:
1. Usa la Q-table para decidir acciones (no solo el LLM)
2. Actualiza la Q-table despues de cada video
3. Genera una grafica de recompensa acumulada por episodio que muestra mejora con el tiempo
4. La Q-table se persiste en disco entre sesiones

# Semana 2 — Capa 2: Agentes LLM con Ollama

Estado: IMPLEMENTADO

## Ficheros implementados

```
src/
  agents/
    __init__.py
    profiles.py     PERFILES dict con system prompts y ACCIONES_VALIDAS
    llm_client.py   LLMClient: wrapper de Ollama con parser JSON robusto
    agent.py        Agent + Decision: evalua un VideoMetadata y devuelve Decision
```

## Como ejecutar (prueba rapida sin crawler)

Con Ollama corriendo (`ollama serve`) y el modelo descargado (`ollama pull llama3.1`):

```python
from src.agents.agent import Agent
from src.crawler.extractor import VideoMetadata

video = VideoMetadata(
    video_id="abc123",
    titulo="Top 10 jugadas de CS2",
    hashtags=["#gaming", "#cs2"],
    transcripcion="Aqui las mejores jugadas del mes...",
    next_video_id="def456",
)

agente = Agent("gamer")
decision = agente.evaluar(video)
print(decision.to_dict())
```

## Objetivo

Integrar Llama 3.1 8B (via Ollama) como motor de decision de los agentes.
Cada agente recibe los metadatos de un video y devuelve un JSON estructurado
con su decision de navegacion.

## Los tres perfiles

Cada perfil se implementa como un system prompt distinto inyectado antes de cada inferencia.

Perfil CASUAL (25 anos, intereses generales):
- Consume entretenimiento neutro, cocina, viajes, humor familiar
- Evita contenido politico, violento o muy especializado
- Representa al usuario medio de plataformas de video corto

Perfil GAMER (18 anos, cultura de internet):
- Gaming competitivo, humor absurdo, internet culture, brainrot ironico
- Alto umbral de tolerancia a contenido intenso
- El perfil mas vulnerable a rabbit holes extremos

Perfil INFO (35 anos, perfil informativo):
- Noticias, documentales, contenido educativo y divulgativo
- Rechaza el entretenimiento vacio
- Actua como grupo de control

## Formato de salida obligatorio del LLM

El agente debe devolver siempre un JSON valido con esta estructura:

```json
{
  "categoria_detectada": "gaming",
  "afinidad_con_perfil": 0.85,
  "extremismo": 0.2,
  "accion": "ver_completo",
  "like": true,
  "razonamiento": "Contenido de gaming competitivo, encaja con perfil gamer"
}
```

Valores posibles de accion: ver_completo / ver_parcial / skip / like
Afinidad y extremismo son floats entre 0.0 y 1.0.

## Estructura de ficheros sugerida

```
src/
  agents/
    profiles.py     definicion de los tres system prompts
    llm_client.py   wrapper de Ollama: envia prompt, parsea JSON de respuesta
    agent.py        clase Agent: tiene perfil, llama al LLM, devuelve Decision
```

## Notas tecnicas

Ollama expone una API REST local en `http://localhost:11434/api/generate`.
La libreria Python `ollama` simplifica las llamadas:

```python
import ollama
response = ollama.chat(
    model="llama3.1",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": video_metadata_as_text}
    ]
)
```

El JSON de respuesta puede venir envuelto en texto libre. Usar un parser
robusto: buscar el primer `{` y el ultimo `}` en el string de respuesta
antes de llamar a `json.loads`.

## Entregable de la semana

Un agente de cualquiera de los tres perfiles que:
1. Recibe los metadatos de un video arbitrario como entrada
2. Devuelve el JSON de decision correctamente formateado
3. Muestra decision coherente con su perfil (GAMER acepta gaming, INFO lo rechaza)

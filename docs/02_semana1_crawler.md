# Semana 1 — Capa 1: Extraccion de datos con Playwright

Estado: IMPLEMENTADO

## Objetivo

Construir un script que navegue YouTube Shorts de forma autonoma, extraiga metadatos de cada video y guarde los datos estructurados en JSON local.

## Ficheros implementados

```
src/
  config.py                  rutas, semillas por perfil, parametros globales
  crawler/
    __init__.py
    browser.py               BrowserSession: Chromium + anti-deteccion + sesion Google
    extractor.py             VideoExtractor + dataclass VideoMetadata
    transcript.py            TranscriptFetcher tolerante a fallos
    session.py               CrawlerSession: bucle principal + checkpoints + JSON
data/
  raw/                       JSONs de sesion generados (session_PERFIL_TIMESTAMP.json)
  browser_state/             storage_state de Playwright por perfil (cookies de Google)
logs/                        un log por sesion (perfil_timestamp.log)
main.py                      punto de entrada CLI
requirements.txt
.env.example
```

## Como ejecutar

Primera ejecucion de cada perfil (login manual de Google en ventana visible):

```bash
pip install -r requirements.txt
playwright install chromium
python main.py --perfil casual --videos 5 --headless false
```

A partir de ahi, modo headless normal:

```bash
python main.py --perfil casual --videos 50
python main.py --perfil gamer  --videos 50
python main.py --perfil info   --videos 50
```

## Que extrae por video

- video_id — desde la URL actual (/shorts/<id>)
- titulo — desde el overlay del DOM de Shorts
- hashtags — chips de categoria visibles bajo el titulo
- transcripcion — via youtube-transcript-api (cadena vacia si no disponible)
- next_video_id — primer enlace /shorts/<id> distinto al actual en el DOM
- capturado_en — timestamp ISO de la extraccion

## Formato JSON de sesion

```json
{
  "perfil": "casual",
  "seed_video_id": "abc123",
  "n_videos_objetivo": 50,
  "n_videos_capturados": 50,
  "iniciado_en": "2024-01-15T10:00:00",
  "finalizado_en": "2024-01-15T10:45:00",
  "videos": [
    {
      "video_id": "abc123",
      "titulo": "titulo del video",
      "hashtags": ["#cocina", "#recetas"],
      "transcripcion": "texto completo o cadena vacia",
      "next_video_id": "def456",
      "capturado_en": "2024-01-15T10:01:23"
    }
  ]
}
```

## Decisiones de diseno tomadas

- Autenticacion con cuenta de Google (storage_state de Playwright por perfil).
  La primera ejecucion abre el navegador en modo visible para login manual.
  Las siguientes cargan las cookies guardadas y corren en headless.

- Siguiente video via parseo de DOM (no intercepcion de red).
  Se lee el primer href="/shorts/<id>" distinto al video actual.
  Es mas estable que interceptar la API interna de YouTube.

- Punto de inicio: video semilla fijo configurable en src/config.py por perfil.
  Garantiza reproducibilidad entre experimentos.

- Checkpoint cada 10 videos: guarda un JSON parcial para no perder datos
  si YouTube bloquea la sesion a mitad.

## Anti-deteccion implementado

- Flag --disable-blink-features=AutomationControlled en Chromium
- Override de navigator.webdriver via page.add_init_script antes de cada pagina
- User-Agent de Chrome real (no el de Playwright por defecto)
- Delays aleatorios 2-8 segundos entre videos (configurable en .env)
- Movimientos de cursor simulados con page.mouse.move()

## Pendiente antes de ejecutar

- Sustituir los seed_video_id placeholder en src/config.py por IDs reales
  de YouTube Shorts neutros para cada perfil (casual, gamer, info).
- Hacer el primer login manual con --headless false para cada perfil.

## Entregable de la semana — criterio de completitud

1. python main.py --perfil casual --videos 50 completa sin errores
2. El JSON de sesion tiene 50 entradas con video_id, titulo y next_video_id rellenos
3. Al menos el 70% tienen transcripcion no vacia
4. El encadenamiento es correcto: videos[i].next_video_id == videos[i+1].video_id
5. YouTube no bloquea la sesion durante la ejecucion

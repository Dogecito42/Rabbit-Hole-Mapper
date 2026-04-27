# Limitaciones conocidas y trabajo futuro

## Limitaciones del sistema actual

Deteccion de bots por YouTube
El sistema implementa mitigaciones (delays aleatorios, movimientos de cursor simulados,
rotacion de User-Agent) pero no es infalible. YouTube puede bloquear la sesion
sin previo aviso. Si ocurre, esperar al menos 1 hora antes de reintentar.

Sesgo del LLM
Llama 3.1 puede clasificar incorrectamente la categoria de videos culturalmente
especificos (jerga regional, referencias de nicho). El campo "razonamiento" del
JSON de decision ayuda a identificar estos casos durante la revision manual.

Representatividad de perfiles
3 perfiles demograficos no cubren toda la diversidad de usuarios reales.
Los resultados son validos para los segmentos representados, no extrapolables
a toda la poblacion.

Cobertura geografica
El algoritmo de YouTube varia segun la region desde la que se ejecuta.
Los resultados son especificos para la localizacion de la maquina donde corre el sistema
(en este caso, Espana). No son directamente comparables con datos de otras regiones.

Ventana temporal
Los datos capturados reflejan el estado del algoritmo de YouTube en el momento
exacto de la simulacion. El algoritmo cambia continuamente; los resultados
no son permanentes.

## Lineas de trabajo futuro

Extender el sistema a TikTok con tecnicas de stealth browsing mas avanzadas.

Aumentar a 10 o mas perfiles demograficos para mayor representatividad
y poder hacer comparaciones estadisticamente significativas.

Implementar Deep Q-Network (DQN) para sustituir la Q-table por una red neuronal,
lo que permite generalizar a estados no vistos sin necesidad de explorarlos.

Anadir analisis de sentimiento a las transcripciones para medir la progresion
emocional del contenido a medida que el agente avanza en el rabbit hole.

Publicar el dataset anonimizado como recurso academico abierto para que otros
investigadores puedan replicar o ampliar los experimentos.

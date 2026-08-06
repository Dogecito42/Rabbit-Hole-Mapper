# Guía de Contribución y Estándares del Repositorio

Este documento define las convenciones de control de versiones, la estrategia de ramas, los despliegues y las herramientas de integración continua necesarias para mantener la estabilidad del proyecto en todos sus entornos.

---

## 1. Convenciones de Commits (Conventional Commits)

El historial del proyecto debe ser legible por humanos y máquinas para automatizar *changelogs* y versiones. Todos los commits deben seguir la siguiente estructura:

```text
<tipo>[ámbito opcional]: <descripción corta>

[cuerpo opcional explicativo]

[pie(s) opcional(es) para cerrar tareas o breaking changes]
```

### Tipos Permitidos

* **`feat`**: Nueva funcionalidad (Incremento MINOR). Ej: `feat(crawler): soporte para playlists de YouTube`
* **`fix`**: Corrección de errores (Incremento PATCH). Ej: `fix(agents): reintento ante timeout de Ollama`
* **`docs`**: Cambios en la documentación.
* **`style`**: Formateo de código (black, ruff), sin alterar lógica.
* **`refactor`**: Reestructuración de código sin alterar comportamiento.
* **`perf`**: Mejoras de rendimiento.
* **`test`**: Añadir o corregir pruebas automatizadas.
* **`build`**: Cambios en dependencias (`requirements.txt`), Docker o procesos de compilación.
* **`ci`**: Cambios en GitHub Actions u otros pipelines.
* **`chore`**: Tareas menores (ej. actualizar `.gitignore`).

---

## 2. Estrategia de Ramas y Entornos

Utilizamos un modelo basado en entornos con tres ramas principales, bloqueando la subida directa de código (`git push` restringido). Todo cambio debe entrar mediante un **Pull Request (PR)** revisado.

### Mapeo de Entornos

| Rama | Entorno | Función | Permisos |
| --- | --- | --- | --- |
| `develop` | **Alpha** | Integración y desarrollo continuo. El código más reciente. | Vía PR desde ramas `feat/` o `fix/` |
| `beta` | **Beta** | Entorno Staging/QA. Réplica de producción. | Vía PR exclusivo desde `develop` |
| `main` | **Estable** | Producción / entrega TFG. | Vía PR exclusivo desde `beta` |

### Ciclo de Vida Estándar de una Feature

1. Crear rama efímera desde Alpha: `git checkout -b feat/nueva-capa-analisis develop`
2. Desarrollar localmente y hacer commits convencionales.
3. Abrir PR hacia `develop` -> CI ejecuta lint y tests.
4. Cuando un conjunto de features es estable, abrir PR de `develop` hacia `beta` -> QA en Beta.
5. Tras validación en QA, abrir PR de `beta` hacia `main` -> Producción y Tag de versión.

---

## 3. Protocolo de Emergencia: Hotfixes

Si surge un error crítico en Producción (`main`) que bloquea el sistema y no hay tiempo de pasar por el ciclo normal, se activa el flujo de *Hotfix*.

1. **Nacimiento:** Extraer rama directamente de producción.

```bash
git checkout -b hotfix/bug-critico-crawler main
```

2. **Corrección:** Arreglar el fallo con un commit de tipo `fix`.
3. **Apagar el fuego:** Abrir PR directo hacia `main`. Al aprobarse, se despliega y se sube el parche de versión.
4. **Retro-Merge (CRÍTICO):** Para evitar que el error reaparezca en el futuro, es **obligatorio** fusionar el hotfix hacia los entornos inferiores.
   * Abrir PR de `hotfix/bug-critico-crawler` hacia `develop`.
   * Abrir PR de `hotfix/bug-critico-crawler` hacia `beta`.
5. Eliminar la rama hotfix tras completar las fusiones.

---

## 4. Infraestructura del Repositorio (CI/CD)

El repositorio actúa como guardián del código mediante la automatización.

### Workflows (GitHub Actions)

La carpeta `.github/workflows/` contiene los pipelines automáticos.

* **Integración Continua (CI):**
  Se ejecuta al abrir un PR hacia cualquier rama principal.
  * Valida el formato del código Python (`ruff`).
  * Instala dependencias desde `requirements.txt` y verifica que el proyecto importa sin errores.
  * Levanta un contenedor efímero de Neo4j (imagen `neo4j:5`, igual que en `docker-compose.yml`) para correr las suites de test que dependen de la base de datos de grafos.
  * Bloquea el PR si algún test falla.

* **Despliegue Continuo (CD):**
  Se ejecuta tras un merge exitoso a `develop`, `beta` o `main`.
  * Inyecta variables de entorno seguras (`.env`, credenciales de Neo4j, tokens de APIs).
  * Sincroniza los ficheros en el servidor objetivo.
  * Reinicia los procesos del crawler y los agentes sin tiempo de inactividad.

### Gestión de Secretos (GitHub Secrets)

Ninguna contraseña, token o certificado vive en el código fuente. Se deben dar de alta en GitHub Secrets:

* Credenciales de conexión a Neo4j (`NEO4J_USER`, `NEO4J_PASSWORD`).
* Tokens de APIs externas (YouTube, Ollama remoto si aplica).
* Claves SSH para acceso a servidores de despliegue.

### Dependabot

El repositorio incluye un archivo `.github/dependabot.yml` para analizar vulnerabilidades periódicamente en `pip` y en las GitHub Actions usadas. Abrirá Pull Requests automatizados para parchear librerías obsoletas.

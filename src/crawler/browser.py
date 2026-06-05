"""
Gestion del navegador Chromium con Playwright.

Responsabilidades:
- Lanzar Chromium con flags anti-deteccion para no ser identificado como bot.
- Cargar y guardar el storage_state (cookies + localStorage) de cada perfil,
  de forma que la sesion de Google se mantiene entre ejecuciones.
- Exponer metodos de comportamiento humano: delays aleatorios y movimientos
  de cursor simulados.

Flujo de primera ejecucion por perfil:
    1. No existe data/browser_state/<perfil>.json
    2. Se lanza Chromium en modo VISIBLE (headless=False)
    3. El usuario hace login en Google manualmente en la ventana
    4. Al cerrar la sesion se guarda el storage_state automaticamente
    5. Las siguientes ejecuciones cargan ese estado y corren en modo headless
"""

import os
import random
import time
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

from src.config import (
    BROWSER_STATE_DIR,
    DELAY_MIN,
    DELAY_MAX,
    USER_AGENT,
)

logger = logging.getLogger(__name__)

# Script que se inyecta en cada pagina antes de que cargue para ocultar
# la presencia de Playwright. navigator.webdriver=true es la principal
# senal que usan los sistemas anti-bot para detectar automatizacion.
_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
Object.defineProperty(navigator, 'languages', { get: () => ['es-ES', 'es', 'en'] });
"""


class BrowserSession:
    """
    Encapsula el ciclo de vida del navegador para una sesion de crawling.

    Uso tipico:
        with BrowserSession(perfil="casual", headless=True) as session:
            page = session.page
            page.goto("https://www.youtube.com/shorts/VIDEO_ID")
            session.human_delay()
    """

    def __init__(self, perfil: str, headless: bool = True):
        """
        Args:
            perfil:   nombre del perfil de agente ("casual", "gamer", "info").
                      Determina que fichero de storage_state se usa.
            headless: True para correr sin ventana (produccion).
                      False para el primer login manual o depuracion.
        """
        self.perfil = perfil
        self.headless = headless
        self._state_path = BROWSER_STATE_DIR / f"{perfil}.json"

        self._playwright = None
        self._browser: Browser = None
        self._context: BrowserContext = None
        self.page: Page = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "BrowserSession":
        self._start()
        return self

    def __exit__(self, *_):
        self._stop()

    # ------------------------------------------------------------------
    # Ciclo de vida interno
    # ------------------------------------------------------------------

    def _start(self):
        """Lanza Playwright, el navegador y abre una pagina lista para usar."""
        self._playwright = sync_playwright().start()

        is_first_run = not self._state_path.exists()
        if is_first_run:
            logger.warning(
                "No existe sesion guardada para '%s'. "
                "Se abre el navegador en modo visible para que hagas login en Google. "
                "Cierra el navegador cuando hayas terminado el login.",
                self.perfil,
            )

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]

        chromium_path = os.environ.get(
            "PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH",
            r"C:\Users\eldog\AppData\Local\ms-playwright\chromium-1217\chrome-win64\chrome.exe",
        )
        self._browser = self._playwright.chromium.launch(
            headless=False if is_first_run else self.headless,
            args=launch_args,
            executable_path=chromium_path,
        )

        context_kwargs = {
            "user_agent": USER_AGENT,
            "viewport": {"width": 1280, "height": 720},
            "locale": "es-ES",
        }
        if not is_first_run:
            context_kwargs["storage_state"] = str(self._state_path)

        self._context = self._browser.new_context(**context_kwargs)
        self._context.add_init_script(_STEALTH_SCRIPT)
        self.page = self._context.new_page()

        if is_first_run:
            self.page.goto("https://accounts.google.com/signin")
            logger.info("Esperando a que el usuario complete el login...")
            # Espera a salir de accounts.google.com; Google puede redirigir a myaccount u otras URLs
            self.page.wait_for_url(
                lambda url: "accounts.google.com" not in url,
                timeout=300_000,
            )
            # Navega directamente a YouTube para asegurar que las cookies de YouTube quedan en el estado
            self.page.goto("https://www.youtube.com")
            self.page.wait_for_load_state("load", timeout=30_000)
            logger.info("Login detectado. Guardando sesion.")

        logger.info("Navegador iniciado para perfil '%s' (headless=%s)", self.perfil, self.headless)

    def _stop(self):
        """Guarda el storage_state y cierra el navegador limpiamente."""
        if self._context:
            BROWSER_STATE_DIR.mkdir(parents=True, exist_ok=True)
            self._context.storage_state(path=str(self._state_path))
            logger.info("Sesion guardada en %s", self._state_path)
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    # ------------------------------------------------------------------
    # Comportamiento humano
    # ------------------------------------------------------------------

    def human_delay(self):
        """Pausa aleatoria entre DELAY_MIN y DELAY_MAX segundos."""
        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        logger.debug("Delay humano: %.1f s", delay)
        time.sleep(delay)

    def simulate_mouse(self):
        """Mueve el cursor a una posicion aleatoria de la ventana."""
        try:
            x = random.randint(100, 1180)
            y = random.randint(100, 620)
            self.page.mouse.move(x, y)
        except Exception:
            pass  # El movimiento de raton es best-effort; no es critico

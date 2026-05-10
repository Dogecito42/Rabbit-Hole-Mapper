"""
Q-table con politica epsilon-greedy para el agente de navegacion de Shorts.

El estado es (categoria_video, perfil_agente) y las acciones son las tres
posibles formas de consumir un video. Se persiste en disco entre sesiones
para que el aprendizaje sea acumulativo a lo largo de multiples ejecuciones.
"""

import logging
import pickle
from collections import defaultdict
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

ACCIONES = ["ver_completo", "ver_parcial", "skip"]
_N_ACCIONES = len(ACCIONES)


class QTable:
    """
    Q-table tabulada con actualizacion Q-Learning (off-policy).

    Args:
        perfil:        nombre del perfil ("casual", "gamer", "info").
        epsilon:       probabilidad inicial de exploracion aleatoria.
        epsilon_min:   cota inferior de epsilon tras el decaimiento.
        epsilon_decay: factor multiplicativo aplicado al final de cada episodio.
        alpha:         tasa de aprendizaje.
        gamma:         factor de descuento de recompensas futuras.
    """

    def __init__(
        self,
        perfil: str,
        epsilon: float = 1.0,
        epsilon_min: float = 0.05,
        epsilon_decay: float = 0.995,
        alpha: float = 0.1,
        gamma: float = 0.9,
    ):
        self.perfil = perfil
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.alpha = alpha
        self.gamma = gamma
        self._tabla: dict = defaultdict(lambda: np.zeros(_N_ACCIONES))

    # ------------------------------------------------------------------
    # Politica
    # ------------------------------------------------------------------

    def elegir_accion(self, estado: tuple) -> int:
        """
        Selecciona un indice de accion con politica epsilon-greedy.

        Con probabilidad epsilon elige aleatoriamente (exploracion);
        en caso contrario elige la accion con mayor Q-value (explotacion).
        """
        if np.random.random() < self.epsilon:
            return int(np.random.randint(_N_ACCIONES))
        return int(np.argmax(self._tabla[estado]))

    # ------------------------------------------------------------------
    # Aprendizaje
    # ------------------------------------------------------------------

    def actualizar(
        self,
        estado: tuple,
        accion_idx: int,
        recompensa: float,
        siguiente_estado: tuple,
    ):
        """Aplica la regla de actualizacion Q-Learning."""
        q_actual = self._tabla[estado][accion_idx]
        q_target = recompensa + self.gamma * np.max(self._tabla[siguiente_estado])
        self._tabla[estado][accion_idx] += self.alpha * (q_target - q_actual)

    def decaer_epsilon(self):
        """Reduce epsilon al final de un episodio (sesion de crawling)."""
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        logger.debug("Epsilon decaido a %.4f", self.epsilon)

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def guardar(self, path: Path):
        """Serializa la Q-table y el epsilon actual en un fichero pickle."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(
                {"tabla": dict(self._tabla), "epsilon": self.epsilon},
                f,
            )
        logger.info(
            "Q-table guardada: perfil=%s estados=%d epsilon=%.4f ruta=%s",
            self.perfil, len(self._tabla), self.epsilon, path,
        )

    @classmethod
    def cargar(cls, path: Path, perfil: str) -> "QTable":
        """Carga una Q-table previamente guardada y devuelve una instancia lista."""
        with open(path, "rb") as f:
            datos = pickle.load(f)
        qt = cls(perfil, epsilon=datos["epsilon"])
        qt._tabla.update(datos["tabla"])
        logger.info(
            "Q-table cargada: perfil=%s estados=%d epsilon=%.4f",
            perfil, len(qt._tabla), qt.epsilon,
        )
        return qt

    # ------------------------------------------------------------------
    # Inspeccion
    # ------------------------------------------------------------------

    def resumen(self) -> dict:
        """Devuelve un dict con estadisticas basicas de la Q-table."""
        if not self._tabla:
            return {"estados": 0, "epsilon": self.epsilon}
        todos = np.array(list(self._tabla.values()))
        return {
            "estados": len(self._tabla),
            "epsilon": round(self.epsilon, 4),
            "q_medio": round(float(todos.mean()), 4),
            "q_max": round(float(todos.max()), 4),
        }

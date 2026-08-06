from src.rl.qtable import ACCIONES, QTable


def test_elegir_accion_sin_exploracion_devuelve_mejor_q():
    qt = QTable("casual", epsilon=0.0)
    estado = ("humor", "casual")
    qt.actualizar(estado, accion_idx=1, recompensa=1.0, siguiente_estado=("otro", "casual"))
    assert qt.elegir_accion(estado) == 1


def test_actualizar_incrementa_q_hacia_recompensa_positiva():
    qt = QTable("casual", epsilon=0.0, alpha=0.5, gamma=0.0)
    estado = ("humor", "casual")
    q_antes = qt._tabla[estado][0]
    qt.actualizar(estado, accion_idx=0, recompensa=1.0, siguiente_estado=("otro", "casual"))
    assert qt._tabla[estado][0] > q_antes


def test_decaer_epsilon_respeta_cota_minima():
    qt = QTable("casual", epsilon=0.06, epsilon_min=0.05, epsilon_decay=0.5)
    qt.decaer_epsilon()
    assert qt.epsilon == 0.05


def test_guardar_y_cargar_conserva_tabla_y_epsilon(tmp_path):
    qt = QTable("gamer", epsilon=0.42)
    estado = ("gaming", "gamer")
    qt.actualizar(estado, accion_idx=2, recompensa=0.7, siguiente_estado=("otro", "gamer"))

    path = tmp_path / "qtable.pkl"
    qt.guardar(path)

    cargada = QTable.cargar(path, "gamer")
    assert cargada.epsilon == 0.42
    assert list(cargada._tabla[estado]) == list(qt._tabla[estado])


def test_acciones_tiene_tres_opciones():
    assert len(ACCIONES) == 3

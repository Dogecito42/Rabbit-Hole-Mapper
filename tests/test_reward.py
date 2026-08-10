from src.rl.reward import calcular_recompensa


def test_afinidad_y_extremismo_altos_maximizan_recompensa():
    assert calcular_recompensa(afinidad=1.0, extremismo=1.0) == 2.0


def test_afinidad_baja_penaliza():
    recompensa = calcular_recompensa(afinidad=0.1, extremismo=0.0)
    assert recompensa == -0.9


def test_afinidad_en_umbral_no_penaliza():
    recompensa = calcular_recompensa(afinidad=0.3, extremismo=0.0)
    assert recompensa == 0.3


def test_recompensa_redondeada_a_cuatro_decimales():
    recompensa = calcular_recompensa(afinidad=1 / 3, extremismo=1 / 3)
    assert recompensa == round(2 / 3, 4)

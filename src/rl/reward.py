"""
Funcion de recompensa del MDP de navegacion de Shorts.

La recompensa mide la calidad del video al que llego el agente tras su accion.
Un video con alta afinidad y alto extremismo maximiza la recompensa, lo que
permite observar si el algoritmo de YouTube empuja hacia contenido mas radical
conforme el agente refuerza sus preferencias.
"""


def calcular_recompensa(afinidad: float, extremismo: float) -> float:
    """
    Calcula la recompensa para la transicion (s, a) -> s'.

    Los pesos son simetricos (1.0 cada uno) para que afinidad y extremismo
    contribuyan por igual al aprendizaje. La penalizacion por afinidad baja
    desalienta quedarse en contenido irrelevante para el perfil.

    Args:
        afinidad:   afinidad_con_perfil del video destino (0.0–1.0).
        extremismo: extremismo del video destino (0.0–1.0).

    Returns:
        Recompensa escalar en el rango [-1.0, 2.0].
    """
    recompensa = afinidad * 1.0 + extremismo * 1.0
    if afinidad < 0.3:
        recompensa -= 1.0
    return round(recompensa, 4)

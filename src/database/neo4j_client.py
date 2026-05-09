"""
Cliente Neo4j para RabbitHole Mapper.

Responsabilidades:
- Mantener la conexion con Neo4j durante una sesion.
- Crear los constraints de unicidad al inicializar.
- Exponer operaciones de escritura atomicas (merge_video, merge_recomendacion,
  merge_interaccion) para que session.py pueda llamarlas video a video.

Schema del grafo:
    (:Video {video_id, titulo, hashtags})
    (:Perfil {nombre})
    (:Video)-[:RECOMIENDA {perfil, sesion_id, posicion}]->(:Video)
    (:Perfil)-[:INTERACTUO {accion, afinidad, extremismo, like,
                             sesion_id, posicion, capturado_en}]->(:Video)
"""

import logging
from neo4j import GraphDatabase

from src.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger(__name__)


class Neo4jClient:
    """
    Encapsula la conexion y las operaciones de escritura contra Neo4j.

    Uso tipico:
        with Neo4jClient() as db:
            db.merge_video(video_id, titulo, hashtags)
            db.merge_recomendacion(from_id, to_id, perfil, sesion_id, posicion)
            db.merge_interaccion(perfil, video_id, decision, sesion_id, posicion)
    """

    def __init__(self, uri: str = NEO4J_URI, user: str = NEO4J_USER, password: str = NEO4J_PASSWORD):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info("Conectado a Neo4j en %s", uri)

    def __enter__(self) -> "Neo4jClient":
        self._crear_constraints()
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        self._driver.close()

    # ------------------------------------------------------------------
    # Inicializacion del esquema
    # ------------------------------------------------------------------

    def _crear_constraints(self):
        """Crea constraints de unicidad si no existen. Idempotente."""
        with self._driver.session() as session:
            session.run(
                "CREATE CONSTRAINT video_id IF NOT EXISTS "
                "FOR (v:Video) REQUIRE v.video_id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT perfil_nombre IF NOT EXISTS "
                "FOR (p:Perfil) REQUIRE p.nombre IS UNIQUE"
            )
        logger.debug("Constraints de Neo4j verificados")

    # ------------------------------------------------------------------
    # Operaciones de escritura
    # ------------------------------------------------------------------

    def merge_video(self, video_id: str, titulo: str | None, hashtags: list[str]):
        """Crea o actualiza un nodo Video. MERGE garantiza que no haya duplicados."""
        with self._driver.session() as session:
            session.run(
                """
                MERGE (v:Video {video_id: $video_id})
                SET v.titulo   = COALESCE($titulo, v.titulo),
                    v.hashtags = $hashtags
                """,
                video_id=video_id,
                titulo=titulo,
                hashtags=hashtags,
            )

    def merge_perfil(self, nombre: str):
        """Crea el nodo Perfil si no existe."""
        with self._driver.session() as session:
            session.run(
                "MERGE (:Perfil {nombre: $nombre})",
                nombre=nombre,
            )

    def merge_recomendacion(self, from_id: str, to_id: str, perfil: str, sesion_id: str, posicion: int):
        """
        Crea la arista RECOMIENDA entre dos videos.

        Representa que YouTube mostro to_id como siguiente Short despues de from_id
        durante una sesion del perfil dado. Es la arista principal del grafo de analisis.
        """
        with self._driver.session() as session:
            session.run(
                """
                MATCH (a:Video {video_id: $from_id})
                MATCH (b:Video {video_id: $to_id})
                MERGE (a)-[r:RECOMIENDA {perfil: $perfil, sesion_id: $sesion_id, posicion: $posicion}]->(b)
                """,
                from_id=from_id,
                to_id=to_id,
                perfil=perfil,
                sesion_id=sesion_id,
                posicion=posicion,
            )

    def merge_interaccion(self, perfil: str, video_id: str, decision: dict, sesion_id: str, posicion: int):
        """
        Crea la arista INTERACTUO entre un Perfil y un Video con los datos de la decision del agente.
        """
        with self._driver.session() as session:
            session.run(
                """
                MATCH (p:Perfil {nombre: $perfil})
                MATCH (v:Video {video_id: $video_id})
                MERGE (p)-[r:INTERACTUO {sesion_id: $sesion_id, posicion: $posicion}]->(v)
                SET r.accion      = $accion,
                    r.afinidad    = $afinidad,
                    r.extremismo  = $extremismo,
                    r.like        = $like,
                    r.comentario  = $comentario,
                    r.capturado_en = $capturado_en
                """,
                perfil=perfil,
                video_id=video_id,
                sesion_id=sesion_id,
                posicion=posicion,
                accion=decision.get("accion"),
                afinidad=decision.get("afinidad_con_perfil"),
                extremismo=decision.get("extremismo"),
                like=decision.get("like"),
                comentario=decision.get("comentario"),
                capturado_en=decision.get("capturado_en", ""),
            )

    def cargar_sesion(self, sesion: dict):
        """
        Carga un diccionario de sesion completo (formato JSON de data/raw/).

        Util para cargar sesiones ya grabadas en disco antes de que Neo4j
        estuviera disponible.
        """
        perfil = sesion["perfil"]
        sesion_id = sesion["iniciado_en"]

        self.merge_perfil(perfil)

        videos = sesion.get("videos", [])
        for posicion, entrada in enumerate(videos):
            video_id = entrada["video_id"]
            self.merge_video(video_id, entrada.get("titulo"), entrada.get("hashtags", []))

            decision = entrada.get("decision", {})
            self.merge_interaccion(perfil, video_id, decision, sesion_id, posicion)

            next_id = entrada.get("next_video_id")
            if next_id and len(next_id) >= 5:
                # Asegurar que el nodo destino existe antes de crear la arista
                self.merge_video(next_id, None, [])
                self.merge_recomendacion(video_id, next_id, perfil, sesion_id, posicion)

        logger.info(
            "Sesion cargada en Neo4j: perfil=%s videos=%d sesion_id=%s",
            perfil, len(videos), sesion_id,
        )

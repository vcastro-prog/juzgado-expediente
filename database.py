import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

import pandas as pd


DB_PATH = Path("data/expedientes.sqlite")


CAMPOS_ESTADO = [
    "numero_procedimiento",
    "fecha_aceptacion",
    "materia",
    "fase_procesal",
    "ultimo_tramite",
    "fecha_ultimo_tramite",
    "procedimiento",
    "juzgado",
    "texto_original",
]


def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    inicializar(conn)
    return conn


def columna_existe(conn, tabla: str, columna: str) -> bool:
    columnas = conn.execute(f"PRAGMA table_info({tabla})").fetchall()
    return any(c["name"] == columna for c in columnas)


def inicializar(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expedientes (
            clave_expediente TEXT PRIMARY KEY,
            numero_procedimiento TEXT,
            fecha_aceptacion TEXT,
            materia TEXT,
            fase_procesal TEXT,
            ultimo_tramite TEXT,
            fecha_ultimo_tramite TEXT,
            procedimiento TEXT,
            juzgado TEXT,
            texto_original TEXT,
            primera_importacion TEXT,
            ultima_importacion TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS historico_cambios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clave_expediente TEXT,
            numero_procedimiento TEXT,
            fecha_cambio TEXT,
            campo TEXT,
            valor_anterior TEXT,
            valor_nuevo TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS importaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_importacion TEXT,
            nombre_archivo TEXT,
            expedientes_leidos INTEGER,
            cambios_detectados INTEGER,
            nuevos_detectados INTEGER
        )
        """
    )

    if not columna_existe(conn, "expedientes", "favorito"):
        conn.execute("ALTER TABLE expedientes ADD COLUMN favorito INTEGER DEFAULT 0")

    if not columna_existe(conn, "expedientes", "nota"):
        conn.execute("ALTER TABLE expedientes ADD COLUMN nota TEXT DEFAULT ''")

    if not columna_existe(conn, "expedientes", "juzgado"):
        conn.execute("ALTER TABLE expedientes ADD COLUMN juzgado TEXT DEFAULT 'Sin juzgado detectado'")

    conn.commit()


def normalizar_valor(v):
    if v is None:
        return ""
    return str(v).strip()


def guardar_importacion(registros: List[Dict], nombre_archivo: str = "") -> pd.DataFrame:
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cambios = []
    nuevos = 0

    with get_conn() as conn:
        for reg in registros:
            clave = reg["clave_expediente"]
            actual = conn.execute(
                "SELECT * FROM expedientes WHERE clave_expediente = ?",
                (clave,),
            ).fetchone()

            if actual is None:
                nuevos += 1
                conn.execute(
                    """
                    INSERT INTO expedientes (
                        clave_expediente, numero_procedimiento, fecha_aceptacion,
                        materia, fase_procesal, ultimo_tramite, fecha_ultimo_tramite,
                        procedimiento, juzgado, texto_original, primera_importacion, ultima_importacion,
                        favorito, nota
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, '')
                    """,
                    (
                        clave,
                        reg.get("numero_procedimiento", ""),
                        reg.get("fecha_aceptacion", ""),
                        reg.get("materia", ""),
                        reg.get("fase_procesal", ""),
                        reg.get("ultimo_tramite", ""),
                        reg.get("fecha_ultimo_tramite", ""),
                        reg.get("procedimiento", ""),
                        reg.get("juzgado", "Sin juzgado detectado"),
                        reg.get("texto_original", ""),
                        ahora,
                        ahora,
                    ),
                )
                cambios.append(
                    {
                        "numero_procedimiento": reg.get("numero_procedimiento", ""),
                        "clave_expediente": clave,
                        "campo": "NUEVO",
                        "valor_anterior": "",
                        "valor_nuevo": "Expediente incorporado",
                        "fecha_cambio": ahora,
                    }
                )
            else:
                hubo_cambio = False
                for campo in CAMPOS_ESTADO:
                    anterior = normalizar_valor(actual[campo])
                    nuevo = normalizar_valor(reg.get(campo, ""))
                    if anterior != nuevo:
                        hubo_cambio = True
                        conn.execute(
                            """
                            INSERT INTO historico_cambios (
                                clave_expediente, numero_procedimiento, fecha_cambio,
                                campo, valor_anterior, valor_nuevo
                            )
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                clave,
                                reg.get("numero_procedimiento", ""),
                                ahora,
                                campo,
                                anterior,
                                nuevo,
                            ),
                        )
                        cambios.append(
                            {
                                "numero_procedimiento": reg.get("numero_procedimiento", ""),
                                "clave_expediente": clave,
                                "campo": campo,
                                "valor_anterior": anterior,
                                "valor_nuevo": nuevo,
                                "fecha_cambio": ahora,
                            }
                        )

                if hubo_cambio:
                    conn.execute(
                        """
                        UPDATE expedientes
                        SET numero_procedimiento = ?,
                            fecha_aceptacion = ?,
                            materia = ?,
                            fase_procesal = ?,
                            ultimo_tramite = ?,
                            fecha_ultimo_tramite = ?,
                            procedimiento = ?,
                            juzgado = ?,
                            texto_original = ?,
                            ultima_importacion = ?
                        WHERE clave_expediente = ?
                        """,
                        (
                            reg.get("numero_procedimiento", ""),
                            reg.get("fecha_aceptacion", ""),
                            reg.get("materia", ""),
                            reg.get("fase_procesal", ""),
                            reg.get("ultimo_tramite", ""),
                            reg.get("fecha_ultimo_tramite", ""),
                            reg.get("procedimiento", ""),
                            reg.get("juzgado", "Sin juzgado detectado"),
                            reg.get("texto_original", ""),
                            ahora,
                            clave,
                        ),
                    )
                else:
                    conn.execute(
                        "UPDATE expedientes SET ultima_importacion = ? WHERE clave_expediente = ?",
                        (ahora, clave),
                    )

        conn.execute(
            """
            INSERT INTO importaciones (
                fecha_importacion, nombre_archivo, expedientes_leidos,
                cambios_detectados, nuevos_detectados
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (ahora, nombre_archivo, len(registros), len(cambios), nuevos),
        )

        conn.commit()

    return pd.DataFrame(cambios)


def cargar_expedientes() -> pd.DataFrame:
    with get_conn() as conn:
        df = pd.read_sql_query(
            """
            SELECT
                numero_procedimiento AS 'Nº Proced.',
                substr(numero_procedimiento, 9, 4) AS 'Año',
                fecha_aceptacion AS 'F. Aceptación',
                juzgado AS 'Juzgado',
                procedimiento AS 'Procedimiento',
                materia AS 'Materia',
                fase_procesal AS 'Fase Procesal',
                ultimo_tramite AS 'Último trámite',
                fecha_ultimo_tramite AS 'Fecha Últ. Trámite',
                CASE
                    WHEN fecha_ultimo_tramite IS NULL OR trim(fecha_ultimo_tramite) = ''
                    THEN ''
                    ELSE substr(fecha_ultimo_tramite, 7, 4)
                END AS 'Año Últ. Trámite',
                CASE
                    WHEN fecha_ultimo_tramite IS NULL OR trim(fecha_ultimo_tramite) = ''
                    THEN 'Sin iniciar trámite'
                    ELSE 'Con trámite'
                END AS 'Estado F. Últ. Trámite',
                primera_importacion AS 'Primera importación',
                ultima_importacion AS 'Última importación',
                favorito AS 'Favorito',
                nota AS 'Nota',
                CASE
                    WHEN lower(fase_procesal) LIKE '%archivo%'
                      OR lower(ultimo_tramite) LIKE '%archivo%'
                      OR lower(ultimo_tramite) LIKE '%terminación%'
                      OR lower(ultimo_tramite) LIKE '%terminacion%'
                    THEN 1
                    ELSE 0
                END AS 'Archivado detectado',
                clave_expediente
            FROM expedientes
            ORDER BY numero_procedimiento
            """,
            conn,
        )
    return df


def cargar_cambios() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            """
            SELECT
                fecha_cambio AS 'Fecha cambio',
                numero_procedimiento AS 'Nº Proced.',
                campo AS 'Campo',
                valor_anterior AS 'Valor anterior',
                valor_nuevo AS 'Valor nuevo',
                clave_expediente
            FROM historico_cambios
            ORDER BY id DESC
            """,
            conn,
        )


def cargar_importaciones() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            """
            SELECT
                fecha_importacion AS 'Fecha importación',
                nombre_archivo AS 'Archivo',
                expedientes_leidos AS 'Expedientes leídos',
                cambios_detectados AS 'Cambios detectados',
                nuevos_detectados AS 'Nuevos'
            FROM importaciones
            ORDER BY id DESC
            """,
            conn,
        )


def cargar_detalle_expediente(clave_expediente: str) -> Tuple[Dict, pd.DataFrame]:
    with get_conn() as conn:
        fila = conn.execute(
            "SELECT * FROM expedientes WHERE clave_expediente = ?",
            (clave_expediente,),
        ).fetchone()

        detalle = dict(fila) if fila else {}

        cambios = pd.read_sql_query(
            """
            SELECT
                fecha_cambio AS 'Fecha cambio',
                numero_procedimiento AS 'Nº Proced.',
                campo AS 'Campo',
                valor_anterior AS 'Valor anterior',
                valor_nuevo AS 'Valor nuevo',
                clave_expediente
            FROM historico_cambios
            WHERE clave_expediente = ?
            ORDER BY id DESC
            """,
            conn,
            params=(clave_expediente,),
        )

    return detalle, cambios


def guardar_favorito_nota(clave_expediente: str, favorito: bool, nota: str):
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE expedientes
            SET favorito = ?, nota = ?
            WHERE clave_expediente = ?
            """,
            (1 if favorito else 0, nota or "", clave_expediente),
        )
        conn.commit()


def resetear_base():
    if DB_PATH.exists():
        DB_PATH.unlink()
    with get_conn():
        pass

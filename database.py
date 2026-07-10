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
    "organo_completo",
    "juzgado_numero",
    "juzgado_tipo",
    "juzgado_seccion",
    "texto_original",
    "tipo_documento", "numero_resolucion", "fecha_dictado", "hora_dictado",
    "tipo_resolucion", "estado_resolucion", "intervencion", "interviniente",
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
            organo_completo TEXT,
            juzgado_numero TEXT,
            juzgado_tipo TEXT,
            juzgado_seccion TEXT,
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

    if not columna_existe(conn, "expedientes", "organo_completo"):
        conn.execute("ALTER TABLE expedientes ADD COLUMN organo_completo TEXT DEFAULT 'Sin órgano detectado'")

    if not columna_existe(conn, "expedientes", "juzgado_numero"):
        conn.execute("ALTER TABLE expedientes ADD COLUMN juzgado_numero TEXT DEFAULT ''")

    if not columna_existe(conn, "expedientes", "juzgado_tipo"):
        conn.execute("ALTER TABLE expedientes ADD COLUMN juzgado_tipo TEXT DEFAULT ''")

    if not columna_existe(conn, "expedientes", "juzgado_seccion"):
        conn.execute("ALTER TABLE expedientes ADD COLUMN juzgado_seccion TEXT DEFAULT ''")


    columnas_resoluciones = {
        "tipo_documento": "TEXT DEFAULT 'alarde'",
        "numero_resolucion": "TEXT DEFAULT ''",
        "fecha_dictado": "TEXT DEFAULT ''",
        "hora_dictado": "TEXT DEFAULT ''",
        "tipo_resolucion": "TEXT DEFAULT ''",
        "estado_resolucion": "TEXT DEFAULT ''",
        "intervencion": "TEXT DEFAULT ''",
        "interviniente": "TEXT DEFAULT ''",
    }
    for nombre_columna, definicion in columnas_resoluciones.items():
        if not columna_existe(conn, "expedientes", nombre_columna):
            conn.execute(
                f"ALTER TABLE expedientes ADD COLUMN {nombre_columna} {definicion}"
            )

    conn.commit()


def normalizar_valor(v):
    if v is None:
        return ""
    return str(v).strip()


def guardar_importacion(registros: List[Dict], nombre_archivo: str = "") -> pd.DataFrame:
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cambios = []
    nuevos = 0

    columnas_registro = [
        "numero_procedimiento",
        "fecha_aceptacion",
        "materia",
        "fase_procesal",
        "ultimo_tramite",
        "fecha_ultimo_tramite",
        "procedimiento",
        "juzgado",
        "organo_completo",
        "juzgado_numero",
        "juzgado_tipo",
        "juzgado_seccion",
        "texto_original",
        "tipo_documento",
        "numero_resolucion",
        "fecha_dictado",
        "hora_dictado",
        "tipo_resolucion",
        "estado_resolucion",
        "intervencion",
        "interviniente",
    ]

    with get_conn() as conn:
        for reg in registros:
            clave = reg["clave_expediente"]
            actual = conn.execute(
                "SELECT * FROM expedientes WHERE clave_expediente = ?",
                (clave,),
            ).fetchone()

            valores = {
                campo: reg.get(campo, "")
                for campo in columnas_registro
            }

            if actual is None:
                nuevos += 1

                columnas_insert = [
                    "clave_expediente",
                    *columnas_registro,
                    "primera_importacion",
                    "ultima_importacion",
                    "favorito",
                    "nota",
                ]
                valores_insert = [
                    clave,
                    *[valores[c] for c in columnas_registro],
                    ahora,
                    ahora,
                    0,
                    "",
                ]

                placeholders = ", ".join(["?"] * len(columnas_insert))
                conn.execute(
                    f"""
                    INSERT INTO expedientes ({", ".join(columnas_insert)})
                    VALUES ({placeholders})
                    """,
                    valores_insert,
                )

                cambios.append(
                    {
                        "numero_procedimiento": valores["numero_procedimiento"],
                        "clave_expediente": clave,
                        "campo": "NUEVO",
                        "valor_anterior": "",
                        "valor_nuevo": "Registro incorporado",
                        "fecha_cambio": ahora,
                    }
                )
            else:
                hubo_cambio = False

                for campo in CAMPOS_ESTADO:
                    anterior = normalizar_valor(actual[campo])
                    nuevo = normalizar_valor(valores.get(campo, ""))

                    if anterior != nuevo:
                        hubo_cambio = True

                        conn.execute(
                            """
                            INSERT INTO historico_cambios (
                                clave_expediente,
                                numero_procedimiento,
                                fecha_cambio,
                                campo,
                                valor_anterior,
                                valor_nuevo
                            )
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                clave,
                                valores["numero_procedimiento"],
                                ahora,
                                campo,
                                anterior,
                                nuevo,
                            ),
                        )

                        cambios.append(
                            {
                                "numero_procedimiento": valores["numero_procedimiento"],
                                "clave_expediente": clave,
                                "campo": campo,
                                "valor_anterior": anterior,
                                "valor_nuevo": nuevo,
                                "fecha_cambio": ahora,
                            }
                        )

                if hubo_cambio:
                    asignaciones = ", ".join(
                        [f"{campo} = ?" for campo in columnas_registro]
                    )
                    conn.execute(
                        f"""
                        UPDATE expedientes
                        SET {asignaciones},
                            ultima_importacion = ?
                        WHERE clave_expediente = ?
                        """,
                        [
                            *[valores[c] for c in columnas_registro],
                            ahora,
                            clave,
                        ],
                    )
                else:
                    conn.execute(
                        """
                        UPDATE expedientes
                        SET ultima_importacion = ?
                        WHERE clave_expediente = ?
                        """,
                        (ahora, clave),
                    )

        conn.execute(
            """
            INSERT INTO importaciones (
                fecha_importacion,
                nombre_archivo,
                expedientes_leidos,
                cambios_detectados,
                nuevos_detectados
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                ahora,
                nombre_archivo,
                len(registros),
                len(cambios),
                nuevos,
            ),
        )

        conn.commit()

    return pd.DataFrame(cambios)

def cargar_expedientes() -> pd.DataFrame:
    with get_conn() as conn:
        df = pd.read_sql_query(
            """
            SELECT
                tipo_documento AS 'Tipo documento',
                numero_resolucion AS 'Nº Resolución',
                CASE WHEN instr(numero_resolucion, '/') > 0
                     THEN substr(numero_resolucion, instr(numero_resolucion, '/') + 1)
                     ELSE '' END AS 'Año Resolución',
                fecha_dictado AS 'Fecha Dictado',
                hora_dictado AS 'Hora Dictado',
                tipo_resolucion AS 'Tipo Resolución',
                estado_resolucion AS 'Estado Resolución',
                intervencion AS 'Intervención',
                interviniente AS 'Interviniente',
                numero_procedimiento AS 'Nº Proced.',
                CASE WHEN instr(numero_procedimiento, '/') > 0
                     THEN substr(numero_procedimiento, instr(numero_procedimiento, '/') + 1)
                     ELSE '' END AS 'Año',
                fecha_aceptacion AS 'F. Aceptación',
                juzgado AS 'Juzgado',
                juzgado_numero AS 'Nº Juzgado',
                juzgado_tipo AS 'Tipo órgano',
                juzgado_seccion AS 'Sección',
                organo_completo AS 'Órgano completo',
                procedimiento AS 'Procedimiento',
                materia AS 'Materia',
                fase_procesal AS 'Fase Procesal',
                ultimo_tramite AS 'Último trámite',
                fecha_ultimo_tramite AS 'Fecha Últ. Trámite',
                CASE WHEN fecha_ultimo_tramite IS NULL OR trim(fecha_ultimo_tramite) = ''
                     THEN '' ELSE substr(fecha_ultimo_tramite, 7, 4)
                     END AS 'Año Últ. Trámite',
                CASE WHEN tipo_documento = 'libro_resoluciones'
                     THEN 'Resolución registrada'
                     WHEN fecha_ultimo_tramite IS NULL OR trim(fecha_ultimo_tramite) = ''
                     THEN 'Sin iniciar trámite' ELSE 'Con trámite'
                     END AS 'Estado F. Últ. Trámite',
                primera_importacion AS 'Primera importación',
                ultima_importacion AS 'Última importación',
                favorito AS 'Favorito',
                nota AS 'Nota',
                0 AS 'Archivado detectado',
                CASE WHEN EXISTS (
                    SELECT 1 FROM historico_cambios hc
                    WHERE hc.clave_expediente = expedientes.clave_expediente
                      AND hc.campo <> 'NUEVO'
                ) THEN 'Modificado' ELSE '' END AS 'Estado cambios',
                (SELECT MAX(hc.fecha_cambio) FROM historico_cambios hc
                 WHERE hc.clave_expediente = expedientes.clave_expediente
                   AND hc.campo <> 'NUEVO') AS 'Último cambio',
                clave_expediente
            FROM expedientes
            ORDER BY juzgado_numero, numero_resolucion, numero_procedimiento
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

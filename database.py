import os
from datetime import datetime
from typing import List, Dict, Tuple

import pandas as pd
import psycopg2
import psycopg2.extras
import streamlit as st


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
]


def secret_o_env(nombre: str, defecto: str = "") -> str:
    try:
        return str(st.secrets[nombre])
    except Exception:
        return os.getenv(nombre, defecto)


def get_conn():
    conn = psycopg2.connect(
        host=secret_o_env("DB_HOST"),
        port=secret_o_env("DB_PORT", "5432"),
        dbname=secret_o_env("DB_NAME", "postgres"),
        user=secret_o_env("DB_USER"),
        password=secret_o_env("DB_PASSWORD"),
        sslmode=secret_o_env("DB_SSLMODE", "require"),
    )
    inicializar(conn)
    return conn


def inicializar(conn):
    with conn.cursor() as cur:
        cur.execute(
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
                ultima_importacion TEXT,
                favorito INTEGER DEFAULT 0,
                nota TEXT DEFAULT ''
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS historico_cambios (
                id SERIAL PRIMARY KEY,
                clave_expediente TEXT,
                numero_procedimiento TEXT,
                fecha_cambio TEXT,
                campo TEXT,
                valor_anterior TEXT,
                valor_nuevo TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS importaciones (
                id SERIAL PRIMARY KEY,
                fecha_importacion TEXT,
                nombre_archivo TEXT,
                expedientes_leidos INTEGER,
                cambios_detectados INTEGER,
                nuevos_detectados INTEGER
            )
            """
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

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for reg in registros:
                clave = reg["clave_expediente"]
                cur.execute("SELECT * FROM expedientes WHERE clave_expediente = %s", (clave,))
                actual = cur.fetchone()

                if actual is None:
                    nuevos += 1
                    cur.execute(
                        """
                        INSERT INTO expedientes (
                            clave_expediente, numero_procedimiento, fecha_aceptacion,
                            materia, fase_procesal, ultimo_tramite, fecha_ultimo_tramite,
                            procedimiento, juzgado, organo_completo, juzgado_numero,
                            juzgado_tipo, juzgado_seccion, texto_original,
                            primera_importacion, ultima_importacion, favorito, nota
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, '')
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
                            reg.get("organo_completo", reg.get("juzgado", "Sin órgano detectado")),
                            reg.get("juzgado_numero", ""),
                            reg.get("juzgado_tipo", ""),
                            reg.get("juzgado_seccion", ""),
                            reg.get("texto_original", ""),
                            ahora,
                            ahora,
                        ),
                    )
                    cambios.append({
                        "numero_procedimiento": reg.get("numero_procedimiento", ""),
                        "clave_expediente": clave,
                        "campo": "NUEVO",
                        "valor_anterior": "",
                        "valor_nuevo": "Expediente incorporado",
                        "fecha_cambio": ahora,
                    })
                else:
                    hubo_cambio = False
                    actual = dict(actual)
                    for campo in CAMPOS_ESTADO:
                        anterior = normalizar_valor(actual.get(campo, ""))
                        nuevo = normalizar_valor(reg.get(campo, ""))
                        if anterior != nuevo:
                            hubo_cambio = True
                            cur.execute(
                                """
                                INSERT INTO historico_cambios (
                                    clave_expediente, numero_procedimiento, fecha_cambio,
                                    campo, valor_anterior, valor_nuevo
                                )
                                VALUES (%s, %s, %s, %s, %s, %s)
                                """,
                                (clave, reg.get("numero_procedimiento", ""), ahora, campo, anterior, nuevo),
                            )
                            cambios.append({
                                "numero_procedimiento": reg.get("numero_procedimiento", ""),
                                "clave_expediente": clave,
                                "campo": campo,
                                "valor_anterior": anterior,
                                "valor_nuevo": nuevo,
                                "fecha_cambio": ahora,
                            })

                    if hubo_cambio:
                        cur.execute(
                            """
                            UPDATE expedientes
                            SET numero_procedimiento = %s,
                                fecha_aceptacion = %s,
                                materia = %s,
                                fase_procesal = %s,
                                ultimo_tramite = %s,
                                fecha_ultimo_tramite = %s,
                                procedimiento = %s,
                                juzgado = %s,
                                organo_completo = %s,
                                juzgado_numero = %s,
                                juzgado_tipo = %s,
                                juzgado_seccion = %s,
                                texto_original = %s,
                                ultima_importacion = %s
                            WHERE clave_expediente = %s
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
                                reg.get("organo_completo", reg.get("juzgado", "Sin órgano detectado")),
                                reg.get("juzgado_numero", ""),
                                reg.get("juzgado_tipo", ""),
                                reg.get("juzgado_seccion", ""),
                                reg.get("texto_original", ""),
                                ahora,
                                clave,
                            ),
                        )
                    else:
                        cur.execute(
                            "UPDATE expedientes SET ultima_importacion = %s WHERE clave_expediente = %s",
                            (ahora, clave),
                        )

            cur.execute(
                """
                INSERT INTO importaciones (
                    fecha_importacion, nombre_archivo, expedientes_leidos,
                    cambios_detectados, nuevos_detectados
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (ahora, nombre_archivo, len(registros), len(cambios), nuevos),
            )
        conn.commit()

    return pd.DataFrame(cambios)


def leer_sql(query: str, params=None) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(query, conn, params=params)


def cargar_expedientes() -> pd.DataFrame:
    return leer_sql(
        """
        SELECT
            numero_procedimiento AS "Nº Proced.",
            substr(numero_procedimiento, 9, 4) AS "Año",
            fecha_aceptacion AS "F. Aceptación",
            juzgado AS "Juzgado",
            juzgado_numero AS "Nº Juzgado",
            juzgado_tipo AS "Tipo órgano",
            juzgado_seccion AS "Sección",
            organo_completo AS "Órgano completo",
            procedimiento AS "Procedimiento",
            materia AS "Materia",
            fase_procesal AS "Fase Procesal",
            ultimo_tramite AS "Último trámite",
            fecha_ultimo_tramite AS "Fecha Últ. Trámite",
            CASE
                WHEN fecha_ultimo_tramite IS NULL OR trim(fecha_ultimo_tramite) = ''
                THEN ''
                ELSE substr(fecha_ultimo_tramite, 7, 4)
            END AS "Año Últ. Trámite",
            CASE
                WHEN fecha_ultimo_tramite IS NULL OR trim(fecha_ultimo_tramite) = ''
                THEN 'Sin iniciar trámite'
                ELSE 'Con trámite'
            END AS "Estado F. Últ. Trámite",
            primera_importacion AS "Primera importación",
            ultima_importacion AS "Última importación",
            favorito AS "Favorito",
            nota AS "Nota",
            CASE
                WHEN lower(coalesce(fase_procesal, '')) LIKE '%archivo%'
                  OR lower(coalesce(ultimo_tramite, '')) LIKE '%archivo%'
                  OR lower(coalesce(ultimo_tramite, '')) LIKE '%terminación%'
                  OR lower(coalesce(ultimo_tramite, '')) LIKE '%terminacion%'
                THEN 1
                ELSE 0
            END AS "Archivado detectado",
            clave_expediente
        FROM expedientes
        ORDER BY numero_procedimiento
        """
    )


def cargar_cambios() -> pd.DataFrame:
    return leer_sql(
        """
        SELECT
            fecha_cambio AS "Fecha cambio",
            numero_procedimiento AS "Nº Proced.",
            campo AS "Campo",
            valor_anterior AS "Valor anterior",
            valor_nuevo AS "Valor nuevo",
            clave_expediente
        FROM historico_cambios
        ORDER BY id DESC
        """
    )


def cargar_importaciones() -> pd.DataFrame:
    return leer_sql(
        """
        SELECT
            fecha_importacion AS "Fecha importación",
            nombre_archivo AS "Archivo",
            expedientes_leidos AS "Expedientes leídos",
            cambios_detectados AS "Cambios detectados",
            nuevos_detectados AS "Nuevos"
        FROM importaciones
        ORDER BY id DESC
        """
    )


def cargar_detalle_expediente(clave_expediente: str) -> Tuple[Dict, pd.DataFrame]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM expedientes WHERE clave_expediente = %s", (clave_expediente,))
            fila = cur.fetchone()
            detalle = dict(fila) if fila else {}

        cambios = pd.read_sql_query(
            """
            SELECT
                fecha_cambio AS "Fecha cambio",
                numero_procedimiento AS "Nº Proced.",
                campo AS "Campo",
                valor_anterior AS "Valor anterior",
                valor_nuevo AS "Valor nuevo",
                clave_expediente
            FROM historico_cambios
            WHERE clave_expediente = %s
            ORDER BY id DESC
            """,
            conn,
            params=(clave_expediente,),
        )
    return detalle, cambios


def guardar_favorito_nota(clave_expediente: str, favorito: bool, nota: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE expedientes SET favorito = %s, nota = %s WHERE clave_expediente = %s",
                (1 if favorito else 0, nota or "", clave_expediente),
            )
        conn.commit()


def resetear_base():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE historico_cambios RESTART IDENTITY")
            cur.execute("TRUNCATE TABLE importaciones RESTART IDENTITY")
            cur.execute("TRUNCATE TABLE expedientes")
        conn.commit()

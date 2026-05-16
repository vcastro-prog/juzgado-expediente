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
        connect_timeout=20,
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

        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_expedientes_clave ON expedientes (clave_expediente)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_cambios_clave ON historico_cambios (clave_expediente)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_importaciones_fecha ON importaciones (fecha_importacion)"
        )

    conn.commit()


def normalizar_valor(v):
    if v is None:
        return ""
    return str(v).strip()


def preparar_registro(reg: Dict, ahora: str) -> Dict:
    return {
        "clave_expediente": reg.get("clave_expediente", ""),
        "numero_procedimiento": reg.get("numero_procedimiento", ""),
        "fecha_aceptacion": reg.get("fecha_aceptacion", ""),
        "materia": reg.get("materia", ""),
        "fase_procesal": reg.get("fase_procesal", ""),
        "ultimo_tramite": reg.get("ultimo_tramite", ""),
        "fecha_ultimo_tramite": reg.get("fecha_ultimo_tramite", ""),
        "procedimiento": reg.get("procedimiento", ""),
        "juzgado": reg.get("juzgado", "Sin juzgado detectado"),
        "organo_completo": reg.get("organo_completo", reg.get("juzgado", "Sin órgano detectado")),
        "juzgado_numero": reg.get("juzgado_numero", ""),
        "juzgado_tipo": reg.get("juzgado_tipo", ""),
        "juzgado_seccion": reg.get("juzgado_seccion", ""),
        "texto_original": reg.get("texto_original", ""),
        "primera_importacion": ahora,
        "ultima_importacion": ahora,
    }


def guardar_importacion(registros: List[Dict], nombre_archivo: str = "") -> pd.DataFrame:
    """
    Versión optimizada para Supabase/PostgreSQL.

    Antes:
    - Consultaba y actualizaba expediente por expediente.

    Ahora:
    - Consulta todos los expedientes existentes de una vez.
    - Calcula nuevos y cambios en memoria.
    - Inserta/actualiza en lotes.
    """
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not registros:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO importaciones (
                        fecha_importacion, nombre_archivo, expedientes_leidos,
                        cambios_detectados, nuevos_detectados
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (ahora, nombre_archivo, 0, 0, 0),
                )
            conn.commit()
        return pd.DataFrame()

    registros_preparados = [preparar_registro(reg, ahora) for reg in registros]
    claves = [r["clave_expediente"] for r in registros_preparados if r["clave_expediente"]]

    cambios = []
    filas_historico = []
    nuevos = 0

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            existentes = {}

            # Cargar existentes en bloques por seguridad.
            bloque = 1000
            for i in range(0, len(claves), bloque):
                subclaves = claves[i:i + bloque]
                cur.execute(
                    "SELECT * FROM expedientes WHERE clave_expediente = ANY(%s)",
                    (subclaves,),
                )
                for fila in cur.fetchall():
                    existentes[fila["clave_expediente"]] = dict(fila)

            filas_upsert = []

            for reg in registros_preparados:
                clave = reg["clave_expediente"]
                actual = existentes.get(clave)

                if actual is None:
                    nuevos += 1

                    cambios.append(
                        {
                            "numero_procedimiento": reg["numero_procedimiento"],
                            "clave_expediente": clave,
                            "campo": "NUEVO",
                            "valor_anterior": "",
                            "valor_nuevo": "Expediente incorporado",
                            "fecha_cambio": ahora,
                        }
                    )

                    # Esta fila no se guarda en historico_cambios para evitar llenar demasiado
                    # la tabla con entradas NUEVO. Si quieres guardarla, descomenta:
                    # filas_historico.append((clave, reg["numero_procedimiento"], ahora, "NUEVO", "", "Expediente incorporado"))

                else:
                    for campo in CAMPOS_ESTADO:
                        anterior = normalizar_valor(actual.get(campo, ""))
                        nuevo = normalizar_valor(reg.get(campo, ""))

                        if anterior != nuevo:
                            filas_historico.append(
                                (
                                    clave,
                                    reg["numero_procedimiento"],
                                    ahora,
                                    campo,
                                    anterior,
                                    nuevo,
                                )
                            )

                            cambios.append(
                                {
                                    "numero_procedimiento": reg["numero_procedimiento"],
                                    "clave_expediente": clave,
                                    "campo": campo,
                                    "valor_anterior": anterior,
                                    "valor_nuevo": nuevo,
                                    "fecha_cambio": ahora,
                                }
                            )

                filas_upsert.append(
                    (
                        reg["clave_expediente"],
                        reg["numero_procedimiento"],
                        reg["fecha_aceptacion"],
                        reg["materia"],
                        reg["fase_procesal"],
                        reg["ultimo_tramite"],
                        reg["fecha_ultimo_tramite"],
                        reg["procedimiento"],
                        reg["juzgado"],
                        reg["organo_completo"],
                        reg["juzgado_numero"],
                        reg["juzgado_tipo"],
                        reg["juzgado_seccion"],
                        reg["texto_original"],
                        reg["primera_importacion"],
                        reg["ultima_importacion"],
                    )
                )

            if filas_upsert:
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO expedientes (
                        clave_expediente, numero_procedimiento, fecha_aceptacion,
                        materia, fase_procesal, ultimo_tramite, fecha_ultimo_tramite,
                        procedimiento, juzgado, organo_completo, juzgado_numero,
                        juzgado_tipo, juzgado_seccion, texto_original,
                        primera_importacion, ultima_importacion
                    )
                    VALUES %s
                    ON CONFLICT (clave_expediente) DO UPDATE SET
                        numero_procedimiento = EXCLUDED.numero_procedimiento,
                        fecha_aceptacion = EXCLUDED.fecha_aceptacion,
                        materia = EXCLUDED.materia,
                        fase_procesal = EXCLUDED.fase_procesal,
                        ultimo_tramite = EXCLUDED.ultimo_tramite,
                        fecha_ultimo_tramite = EXCLUDED.fecha_ultimo_tramite,
                        procedimiento = EXCLUDED.procedimiento,
                        juzgado = EXCLUDED.juzgado,
                        organo_completo = EXCLUDED.organo_completo,
                        juzgado_numero = EXCLUDED.juzgado_numero,
                        juzgado_tipo = EXCLUDED.juzgado_tipo,
                        juzgado_seccion = EXCLUDED.juzgado_seccion,
                        texto_original = EXCLUDED.texto_original,
                        ultima_importacion = EXCLUDED.ultima_importacion
                    """,
                    filas_upsert,
                    page_size=500,
                )

            if filas_historico:
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO historico_cambios (
                        clave_expediente, numero_procedimiento, fecha_cambio,
                        campo, valor_anterior, valor_nuevo
                    )
                    VALUES %s
                    """,
                    filas_historico,
                    page_size=1000,
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


@st.cache_data(ttl=30)
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


@st.cache_data(ttl=30)
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


@st.cache_data(ttl=30)
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
            cur.execute(
                "SELECT * FROM expedientes WHERE clave_expediente = %s",
                (clave_expediente,),
            )
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
                """
                UPDATE expedientes
                SET favorito = %s, nota = %s
                WHERE clave_expediente = %s
                """,
                (1 if favorito else 0, nota or "", clave_expediente),
            )
        conn.commit()

    cargar_expedientes.clear()


def resetear_base():
    """
    Borra los datos, pero mantiene la estructura de tablas.
    Úsalo solo si quieres reiniciar la base de Supabase.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE historico_cambios RESTART IDENTITY")
            cur.execute("TRUNCATE TABLE importaciones RESTART IDENTITY")
            cur.execute("TRUNCATE TABLE expedientes")
        conn.commit()

    cargar_expedientes.clear()
    cargar_cambios.clear()
    cargar_importaciones.clear()

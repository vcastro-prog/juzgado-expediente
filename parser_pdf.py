import re
from typing import List, Dict, Optional, Tuple

import pdfplumber


PARSER_VERSION = "Parser v2.2.2"


EXPEDIENTE_RE = re.compile(r"^\d{7}/\d{4}\b")
EXPEDIENTE_ANY_RE = re.compile(r"\b\d{7}/\d{4}\b")
RESOLUCION_RE = re.compile(r"\b\d{6}/\d{4}\b")
RESOLUCION_LINE_RE = re.compile(r"^\d{6}/\d{4}\b")
FECHA_RE = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")
FECHA_LINE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}\b")
HORA_RE = re.compile(r"\b\d{1,2}:\d{2}:\d{2}\b")

FASES_CONOCIDAS = [
    "Oposición/Desp Ejec/Resolución",
    "Inicio/Demanda",
    "Inicio/Solicitud",
    "Pendiente de resolver",
    "Tramitación",
    "Resolución",
    "Ejecución",
    "Admisión",
    "Archivo",
    "Recurso",
    "Remisión",
    "Firmeza",
    "Firme",
    "Pendiente de firmeza",
    "Recurrida",
]

CABECERAS_Y_PIES = [
    "Observaciones:",
    "ALARDE",
    "Órgano de registro:",
    "Órgano de Registro:",
    "Nº Proced.",
    "Nº resolución",
    "F. Aceptación",
    "F. Dictado",
    "F. public.",
    "Fase Procesal",
    "Último trámite",
    "Procedimiento",
    "Materia",
    "Página:",
    "Fecha Últ. Tramite",
    "Fecha Últ. Trámite",
    "Próximo Trámite",
    "Intervención Interviniente",
    "Periodo de",
    "Libro de Resoluciones",
]


class PDFConVariosJuzgadosError(Exception):
    def __init__(self, juzgados_detectados):
        self.juzgados_detectados = juzgados_detectados
        mensaje = (
            "El PDF parece contener varios juzgados u órganos distintos. "
            "Cárgalo separado, un PDF por juzgado. Detectados: "
            + " | ".join(juzgados_detectados)
        )
        super().__init__(mensaje)


class PDFNoReconocidoError(Exception):
    pass


def quitar_duplicados_espacios(texto: str) -> str:
    if texto is None:
        return ""
    return " ".join(str(texto).split()).strip()


def limpiar_texto(texto: str) -> str:
    if texto is None:
        return ""

    texto = str(texto)
    texto = texto.replace("\u2013", "-").replace("\u2014", "-")
    texto = texto.replace("\ufeff", "")
    texto = texto.replace("\ufffe", "")
    texto = texto.replace("\ufffd", "")
    texto = texto.replace("￾", "-")

    reemplazos = {
        "Inicio/Demand a": "Inicio/Demanda",
        "Inicio/Demand": "Inicio/Demanda",
        "Inicio/Solicitu d": "Inicio/Solicitud",
        "Tramitació n": "Tramitación",
        "Resolució n": "Resolución",
        "Req uerimiento": "Requerimiento",
        "Cita ción": "Citación",
        "Ejec/Resolució n": "Ejec/Resolución",
        "Des p Ejec": "Desp Ejec",
        "pronunciamiento - ": "pronunciamiento - ",
    }
    for a, b in reemplazos.items():
        texto = texto.replace(a, b)

    return quitar_duplicados_espacios(texto)


def es_linea_ruido(linea: str) -> bool:
    l = limpiar_texto(linea)
    if not l:
        return True
    return any(fragmento in l for fragmento in CABECERAS_Y_PIES)


def extraer_texto(pdf_file) -> str:
    paginas = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            paginas.append(page.extract_text() or "")
    return "\n".join(paginas)


def extraer_texto_y_num_paginas(pdf_file) -> Tuple[str, int]:
    paginas = []
    with pdfplumber.open(pdf_file) as pdf:
        total = len(pdf.pages)
        for page in pdf.pages:
            paginas.append(page.extract_text() or "")
    return "\n".join(paginas), total


def normalizar_organo(organo: str) -> str:
    organo = limpiar_texto(organo)
    if "Página:" in organo:
        organo = organo.split("Página:", 1)[0].strip()
    organo = organo.replace("No", "Nº")
    return quitar_duplicados_espacios(organo)


def es_linea_organo(linea: str) -> bool:
    limpia = normalizar_organo(linea)
    if not limpia:
        return False
    if EXPEDIENTE_RE.match(limpia) or RESOLUCION_LINE_RE.match(limpia):
        return False

    patrones = [
        r"Órgano de Registro:",
        r"Órgano de registro:",
        r"^Plaza\s*N[ºo]\s*\d+",
        r"^Juzgado.*\bN[ºo]\s*\d+",
        r"^Juzgado.*\bn[uú]m\.?\s*\d+",
        r"^.*Tribunal de Instancia.*$",
    ]
    return any(re.search(p, limpia, re.IGNORECASE) for p in patrones)


def limpiar_organo_para_analisis(organo: str) -> str:
    organo = normalizar_organo(organo)
    if "Órgano de Registro:" in organo:
        organo = organo.split("Órgano de Registro:", 1)[1].strip()
    if "Órgano de registro:" in organo:
        organo = organo.split("Órgano de registro:", 1)[1].strip()
    return quitar_duplicados_espacios(organo)


def analizar_organo(organo_completo: str) -> Dict[str, str]:
    organo_visible = normalizar_organo(organo_completo)
    organo = limpiar_organo_para_analisis(organo_completo)

    numero = ""
    tipo = ""
    seccion = ""

    m_num = re.search(r"(?:Plaza|Juzgado)?\s*N[ºo]\s*(\d+)", organo, re.IGNORECASE)
    if not m_num:
        m_num = re.search(r"n[uú]m\.?\s*(\d+)", organo, re.IGNORECASE)
    if m_num:
        numero = m_num.group(1)

    m_seccion = re.search(r"\(([^)]*Secci[oó]n[^)]*)\)", organo, re.IGNORECASE)
    if not m_seccion:
        m_seccion = re.search(r"(Secci[oó]n\s+[A-Za-zÁÉÍÓÚáéíóúÑñ ]+)", organo, re.IGNORECASE)
    if m_seccion:
        seccion = limpiar_texto(m_seccion.group(1))

    if "Tribunal de Instancia" in organo:
        tipo = "Tribunal de Instancia"
    elif re.search(r"Juzgado de Primera Instancia", organo, re.IGNORECASE):
        tipo = "Juzgado de Primera Instancia"
    elif re.search(r"Juzgado", organo, re.IGNORECASE):
        tipo = "Juzgado"
    elif re.search(r"Plaza\s*N[ºo]\s*\d+", organo, re.IGNORECASE):
        tipo = "Plaza"
    else:
        tipo = "Sin tipo detectado"

    return {
        "organo_completo": organo_visible or "Sin órgano detectado",
        "juzgado_numero": numero,
        "juzgado_tipo": tipo,
        "juzgado_seccion": seccion,
    }


def clave_organo(info: Dict[str, str]) -> str:
    return "|".join(
        [
            (info.get("juzgado_numero") or "").strip().lower(),
            (info.get("juzgado_tipo") or "").strip().lower(),
            (info.get("juzgado_seccion") or "").strip().lower(),
        ]
    )


def lineas_organo_detectadas(texto: str) -> List[str]:
    organos = []
    for linea in texto.splitlines():
        limpia = normalizar_organo(linea)
        if es_linea_organo(limpia) and len(limpia) >= 8:
            organos.append(limpia)

    unicos = []
    vistos = set()
    for o in organos:
        clave = o.lower()
        if clave not in vistos:
            unicos.append(o)
            vistos.add(clave)
    return unicos


def extraer_juzgado_info(texto: str) -> Dict[str, str]:
    organos = lineas_organo_detectadas(texto)
    if not organos:
        return analizar_organo("Sin órgano detectado")

    grupos = {}
    for organo in organos:
        info = analizar_organo(organo)
        grupos.setdefault(clave_organo(info), []).append(info)

    if len(grupos) > 1:
        representantes = [infos[0]["organo_completo"] for infos in grupos.values()]
        raise PDFConVariosJuzgadosError(representantes)

    return list(grupos.values())[0][0]


def crear_clave(reg: Dict) -> str:
    partes = [
        reg.get("organo_completo", ""),
        reg.get("numero_procedimiento", ""),
        reg.get("fecha_aceptacion", ""),
        reg.get("procedimiento", ""),
    ]
    return " | ".join(quitar_duplicados_espacios(p).lower() for p in partes)


def completar_registro_juzgado(reg: Dict, juzgado_info: Dict[str, str]) -> Dict:
    reg.setdefault("tipo_documento", "alarde")
    reg.setdefault("numero_resolucion", "")
    reg.setdefault("fecha_dictado", "")
    reg.setdefault("hora_dictado", "")
    reg.setdefault("tipo_resolucion", "")
    reg.setdefault("estado_resolucion", "")
    reg.setdefault("intervencion", "")
    reg.setdefault("interviniente", "")
    reg["juzgado"] = juzgado_info["organo_completo"]
    reg["organo_completo"] = juzgado_info["organo_completo"]
    reg["juzgado_numero"] = juzgado_info["juzgado_numero"]
    reg["juzgado_tipo"] = juzgado_info["juzgado_tipo"]
    reg["juzgado_seccion"] = juzgado_info["juzgado_seccion"]
    reg["clave_expediente"] = crear_clave(reg)
    return reg


def detectar_tipo_pdf(texto: str) -> str:
    texto_l = texto.lower()
    if (
        "libro de resoluciones" in texto_l
        and "nº resolución" in texto_l
        and "f. dictado" in texto_l
    ):
        return "libro_resoluciones"

    if (
        "nº proced" in texto_l
        and "f. aceptación" in texto_l
        and "fase procesal" in texto_l
    ):
        return "alarde"

    if "alarde" in texto_l and "procedimiento" in texto_l:
        return "alarde"

    return "desconocido"


def es_libro_resoluciones(texto: str) -> bool:
    return detectar_tipo_pdf(texto) == "libro_resoluciones"


# ============================================================
# ALARDE / LISTADO DE EXPEDIENTES
# ============================================================

def es_continuacion_de_fila(linea: str) -> bool:
    linea = limpiar_texto(linea)
    if not linea:
        return False
    if EXPEDIENTE_RE.match(linea):
        return False
    if es_linea_ruido(linea) or es_linea_organo(linea):
        return False
    if FECHA_RE.fullmatch(linea):
        return False
    if re.fullmatch(r"\d+", linea):
        return False
    return True


def unir_fragmentos_texto(partes: List[str]) -> str:
    texto = " ".join(limpiar_texto(p) for p in partes if p and p.strip())
    texto = quitar_duplicados_espacios(texto)
    texto = texto.replace(" - - ", " - ")
    texto = re.sub(r"\(\s+", "(", texto)
    texto = re.sub(r"\s+\)", ")", texto)
    return texto.strip()


def reconstruir_lineas_logicas(texto: str) -> List[str]:
    lineas_logicas = []
    actual = []

    for raw in texto.splitlines():
        linea = limpiar_texto(raw)

        if es_linea_ruido(linea) or es_linea_organo(linea):
            continue
        if not linea:
            continue

        if EXPEDIENTE_RE.match(linea):
            if actual:
                lineas_logicas.append(unir_fragmentos_texto(actual))
            actual = [linea]
        else:
            if actual and es_continuacion_de_fila(linea):
                actual.append(linea)
            elif actual:
                actual.append(linea)

    if actual:
        lineas_logicas.append(unir_fragmentos_texto(actual))

    return [l for l in lineas_logicas if l.strip()]


def dividir_en_bloques(texto: str) -> List[str]:
    return [limpiar_texto(b) for b in reconstruir_lineas_logicas(texto) if b.strip()]


def limpiar_procedimiento(texto: str) -> str:
    texto = quitar_duplicados_espacios(texto)
    texto = re.sub(r"\s+-\s+", " - ", texto)
    return quitar_duplicados_espacios(texto)


def detectar_posicion_fase(texto: str):
    texto_lower = texto.lower()
    candidatos = []
    for fase in sorted(FASES_CONOCIDAS, key=len, reverse=True):
        idx = texto_lower.find(fase.lower())
        if idx >= 0:
            candidatos.append((idx, idx + len(fase), fase))
    if not candidatos:
        return "", -1, -1
    candidatos.sort(key=lambda x: x[0])
    start, end, fase = candidatos[0]
    return fase, start, end


def parsear_bloque_alarde(bloque: str) -> Optional[Dict]:
    bloque = limpiar_texto(bloque)
    m = EXPEDIENTE_RE.match(bloque)
    if not m:
        return None

    numero = m.group(0)
    resto = bloque[m.end():].strip()
    fechas = list(FECHA_RE.finditer(resto))

    if not fechas:
        return {
            "numero_procedimiento": numero,
            "fecha_aceptacion": "",
            "materia": "",
            "fase_procesal": "",
            "ultimo_tramite": resto,
            "fecha_ultimo_tramite": "",
            "procedimiento": limpiar_procedimiento(resto),
            "texto_original": bloque,
        }

    fecha_aceptacion = fechas[0].group(0)
    procedimiento = limpiar_procedimiento(resto[: fechas[0].start()].strip())
    despues_fecha = resto[fechas[0].end():].strip()

    fechas_posteriores = list(FECHA_RE.finditer(despues_fecha))
    if fechas_posteriores:
        fecha_ultimo = fechas_posteriores[-1].group(0)
        cuerpo = despues_fecha[: fechas_posteriores[-1].start()].strip()
        cola = despues_fecha[fechas_posteriores[-1].end():].strip()
    else:
        fecha_ultimo = ""
        cuerpo = despues_fecha
        cola = ""

    fase, fase_start, fase_end = detectar_posicion_fase(cuerpo)
    if fase:
        materia = quitar_duplicados_espacios(cuerpo[:fase_start])
        ultimo_tramite = quitar_duplicados_espacios(cuerpo[fase_end:])
    else:
        materia = ""
        ultimo_tramite = quitar_duplicados_espacios(cuerpo)

    if cola:
        ultimo_tramite = quitar_duplicados_espacios((ultimo_tramite + " " + cola).strip())

    return {
        "numero_procedimiento": numero,
        "fecha_aceptacion": fecha_aceptacion,
        "materia": materia,
        "fase_procesal": fase,
        "ultimo_tramite": ultimo_tramite,
        "fecha_ultimo_tramite": fecha_ultimo,
        "procedimiento": procedimiento,
        "texto_original": bloque,
    }


def extraer_expedientes_alarde(pdf_file) -> List[Dict]:
    texto = extraer_texto(pdf_file)
    juzgado_info = extraer_juzgado_info(texto)

    registros_base = []
    bloques = dividir_en_bloques(texto)
    for bloque in bloques:
        reg = parsear_bloque_alarde(bloque)
        if reg and reg.get("numero_procedimiento"):
            registros_base.append(reg)

    registros = []
    vistos = set()
    for reg in registros_base:
        reg = completar_registro_juzgado(reg, juzgado_info)
        clave = reg["clave_expediente"]
        if clave not in vistos:
            registros.append(reg)
            vistos.add(clave)
    return registros


# ============================================================
# LIBRO DE RESOLUCIONES
# ============================================================

ROLES_INTERVENCION = [
    "Administrador concursal", "Representante legal", "Interviniente",
    "Demandante", "Demandado", "Ejecutante", "Ejecutado", "Interesado",
    "Codemandante", "Codemandado", "Procurador", "Abogado", "Perito",
    "Heredero", "Cónyuge", "Administrador",
]


def extraer_tipo_resolucion(texto: str) -> str:
    m = re.search(r"Tipo Resolución:\s*([^\n\r]+)", texto, re.IGNORECASE)
    return limpiar_texto(m.group(1)) if m else "Resolución"


def limpiar_lineas_pagina_libro(texto_pagina: str) -> List[str]:
    lineas = []
    for raw in texto_pagina.splitlines():
        linea = limpiar_texto(raw)
        if not linea:
            continue
        if linea.startswith("Tipo Resolución:"):
            continue
        if any(fragmento in linea for fragmento in [
            "Página:", "Libro de Resoluciones - CIVIL", "Órgano de Registro:",
            "Periodo de ", "Nº resolución F. Dictado",
            "Intervención Interviniente", "Observaciones:",
        ]):
            continue
        if FECHA_RE.fullmatch(linea):
            continue
        if re.fullmatch(r"\d{1,3}", linea):
            continue
        lineas.append(linea)
    return lineas


def segmentar_registros_libro(pdf_file) -> List[Tuple[List[str], str, int]]:
    """
    Devuelve cada bloque junto con:
    - el tipo de resolución de su página;
    - el número de página.

    Un mismo PDF puede contener varios tipos de resolución, por ejemplo
    Decreto en unas páginas y Auto en otras.
    """
    registros = []
    ultimo_tipo_detectado = "Resolución"

    with pdfplumber.open(pdf_file) as pdf:
        for numero_pagina, page in enumerate(pdf.pages, start=1):
            texto_pagina = page.extract_text() or ""

            m_tipo = re.search(
                r"Tipo Resolución:\s*([^\n\r]+)",
                texto_pagina,
                re.IGNORECASE,
            )

            if m_tipo:
                ultimo_tipo_detectado = limpiar_texto(m_tipo.group(1))

            tipo_pagina = ultimo_tipo_detectado
            lineas = limpiar_lineas_pagina_libro(texto_pagina)
            actual = []

            for linea in lineas:
                if RESOLUCION_LINE_RE.match(linea):
                    if actual:
                        registros.append(
                            (actual, tipo_pagina, numero_pagina)
                        )
                    actual = [linea]
                elif actual:
                    actual.append(linea)

            if actual:
                registros.append(
                    (actual, tipo_pagina, numero_pagina)
                )

    return registros


def separar_intervencion_interviniente(texto: str) -> Tuple[str, str]:
    texto = limpiar_texto(texto)
    for rol in sorted(ROLES_INTERVENCION, key=len, reverse=True):
        if texto.lower().startswith(rol.lower()):
            return rol, texto[len(rol):].strip()
    return "", texto


def extraer_estado_resolucion(texto: str) -> Tuple[str, str]:
    for estado in ["Pendiente de firmeza", "Recurrida", "Firme"]:
        m = re.search(r"\b" + re.escape(estado) + r"\b", texto, re.IGNORECASE)
        if m:
            restante = (texto[:m.start()] + " " + texto[m.end():]).strip()
            return estado, limpiar_texto(restante)
    return "", texto


def parsear_registro_libro(lineas: List[str], tipo_resolucion: str,
                           juzgado_info: Dict[str, str]) -> Optional[Dict]:
    if not lineas:
        return None

    principal = limpiar_texto(lineas[0])
    m_res = RESOLUCION_LINE_RE.match(principal)
    if not m_res:
        return None

    numero_resolucion = m_res.group(0)
    resto_principal = principal[m_res.end():].strip()

    m_fecha = FECHA_RE.search(resto_principal)
    fecha_dictado = m_fecha.group(0) if m_fecha else ""
    cuerpo = resto_principal[m_fecha.end():].strip() if m_fecha else resto_principal

    estado, cuerpo = extraer_estado_resolucion(cuerpo)

    hora_dictado = ""
    indice_hora = None
    continuacion_procedimiento = []

    for idx, linea in enumerate(lineas[1:], start=1):
        m_hora = HORA_RE.search(linea)
        if m_hora:
            hora_dictado = m_hora.group(0)
            indice_hora = idx
            despues_hora = limpiar_texto(linea[m_hora.end():])
            if despues_hora:
                continuacion_procedimiento.append(despues_hora)
            break

    lineas_interviniente = lineas[indice_hora + 1:] if indice_hora is not None else []
    texto_interviniente = limpiar_texto(" ".join(lineas_interviniente))
    intervencion, interviniente = separar_intervencion_interviniente(texto_interviniente)

    cuerpo_completo = limpiar_texto(" ".join([cuerpo] + continuacion_procedimiento))
    expedientes = list(EXPEDIENTE_ANY_RE.finditer(cuerpo_completo))
    numero_procedimiento = expedientes[0].group(0) if expedientes else ""

    procedimiento = EXPEDIENTE_ANY_RE.sub("", cuerpo_completo)
    procedimiento = limpiar_texto(procedimiento)
    procedimiento = re.sub(r"\s+-\s+", " - ", procedimiento).strip()

    reg = {
        "tipo_documento": "libro_resoluciones",
        "numero_resolucion": numero_resolucion,
        "fecha_dictado": fecha_dictado,
        "hora_dictado": hora_dictado,
        "tipo_resolucion": tipo_resolucion,
        "estado_resolucion": estado,
        "intervencion": intervencion,
        "interviniente": interviniente,
        "numero_procedimiento": numero_procedimiento,
        "fecha_aceptacion": fecha_dictado,
        "materia": tipo_resolucion,
        "fase_procesal": estado,
        "ultimo_tramite": f"{tipo_resolucion} {numero_resolucion}".strip(),
        "fecha_ultimo_tramite": fecha_dictado,
        "procedimiento": procedimiento,
        "texto_original": limpiar_texto(" ".join(lineas)),
    }

    reg = completar_registro_juzgado(reg, juzgado_info)
    reg["clave_expediente"] = " | ".join([
        juzgado_info.get("organo_completo", "").lower().strip(),
        numero_resolucion.lower().strip(),
    ])
    return reg


def extraer_expedientes_libro_resoluciones(pdf_file) -> List[Dict]:
    texto = extraer_texto(pdf_file)
    juzgado_info = extraer_juzgado_info(texto)
    bloques = segmentar_registros_libro(pdf_file)

    registros = []
    vistos = set()

    for bloque, tipo_resolucion, numero_pagina in bloques:
        reg = parsear_registro_libro(
            bloque,
            tipo_resolucion,
            juzgado_info,
        )

        if not reg:
            continue

        reg["pagina_pdf"] = numero_pagina

        if reg["clave_expediente"] not in vistos:
            registros.append(reg)
            vistos.add(reg["clave_expediente"])

    return registros

def extraer_expedientes(pdf_file) -> List[Dict]:
    texto = extraer_texto(pdf_file)
    tipo = detectar_tipo_pdf(texto)

    if tipo == "libro_resoluciones":
        return extraer_expedientes_libro_resoluciones(pdf_file)

    if tipo == "alarde":
        return extraer_expedientes_alarde(pdf_file)

    if EXPEDIENTE_ANY_RE.search(texto):
        return extraer_expedientes_alarde(pdf_file)

    raise PDFNoReconocidoError(
        "No se reconoce el tipo de PDF. Actualmente se soportan ALARDE y Libro de Resoluciones."
    )


def extraer_diagnostico_pdf(pdf_file) -> Dict:
    texto, paginas = extraer_texto_y_num_paginas(pdf_file)
    tipo = detectar_tipo_pdf(texto)

    try:
        registros = extraer_expedientes(pdf_file)
        total = len(registros)
        error = ""
    except Exception as exc:
        total = 0
        error = str(exc)

    return {
        "parser_version": PARSER_VERSION,
        "tipo_pdf": tipo,
        "paginas": paginas,
        "registros_detectados": total,
        "error": error,
    }

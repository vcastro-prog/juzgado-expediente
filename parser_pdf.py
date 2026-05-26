import re
from typing import List, Dict, Optional

import pdfplumber


EXPEDIENTE_RE = re.compile(r"^\d{7}/\d{4}\b")
FECHA_RE = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")

FASES_CONOCIDAS = [
    "Inicio/Demanda",
    "Inicio/Solicitud",
    "Tramitación",
    "Resolución",
    "Archivo",
    "Ejecución",
    "Recurso",
    "Remisión",
    "Firmeza",
    "Admisión",
    "Oposición/Desp Ejec/Resolución",
]

CABECERAS_Y_PIES = [
    "Observaciones:",
    "ALARDE",
    "Órgano de registro:",
    "Nº Proced.",
    "F. Aceptación",
    "Fase Procesal",
    "Último trámite",
    "Procedimiento",
    "Materia",
    "Página:",
    "Fecha Últ. Tramite",
    "Fecha Últ. Trámite",
    "Próximo Trámite",
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


def limpiar_texto(texto: str) -> str:
    texto = texto.replace("\u2013", "-").replace("\u2014", "-")
    texto = texto.replace("Inicio/Demand a", "Inicio/Demanda")
    texto = texto.replace("Inicio/Demand", "Inicio/Demanda")
    texto = texto.replace("Inicio/Solicitu d", "Inicio/Solicitud")
    texto = texto.replace("Tramitació n", "Tramitación")
    texto = texto.replace("Resolució n", "Resolución")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def es_linea_ruido(linea: str) -> bool:
    l = linea.strip()
    if not l:
        return True
    return any(fragmento in l for fragmento in CABECERAS_Y_PIES)


def extraer_texto(pdf_file) -> str:
    paginas = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            paginas.append(page.extract_text() or "")
    return "\n".join(paginas)


def normalizar_organo(organo: str) -> str:
    organo = limpiar_texto(organo)

    # Muchos PDFs muestran:
    # "Órgano de registro: Plaza Nº 9 del Tribunal de Instancia (Sección Civil)"
    # Para comparar juzgados, nos quedamos solo con la parte posterior a los dos puntos.
    if "Órgano de registro:" in organo:
        organo = organo.split("Órgano de registro:", 1)[1].strip()

    if "Página:" in organo:
        organo = organo.split("Página:", 1)[0].strip()

    organo = organo.replace("No", "Nº")
    organo = re.sub(r"\s+", " ", organo)
    return organo.strip()


def es_linea_organo(linea: str) -> bool:
    limpia = normalizar_organo(linea)

    if not limpia:
        return False

    if EXPEDIENTE_RE.match(limpia):
        return False

    patrones = [
        r"^Plaza\s*N[ºo]\s*\d+",
        r"^Juzgado.*\bN[ºo]\s*\d+",
        r"^Juzgado.*\bn[uú]m\.?\s*\d+",
        r"^.*Tribunal de Instancia.*$",
    ]

    return any(re.search(p, limpia, re.IGNORECASE) for p in patrones)


def analizar_organo(organo_completo: str) -> Dict[str, str]:
    organo = normalizar_organo(organo_completo)

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
        "organo_completo": organo or "Sin órgano detectado",
        "juzgado_numero": numero,
        "juzgado_tipo": tipo,
        "juzgado_seccion": seccion,
    }


def clave_organo(info: Dict[str, str]) -> str:
    """
    Compara órganos por los campos estructurados, no por el texto exacto.
    Así no se bloquea un PDF porque una página diga:
    "Órgano de registro: Plaza Nº 9..."
    y otra solo:
    "Plaza Nº 9...".
    """
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

    # Quitamos duplicados conservando orden.
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

    # Agrupamos por órgano estructurado. Si todos son Plaza 9 / Tribunal / Sección Civil,
    # aunque el encabezado se repita en 250 páginas, se acepta.
    grupos = {}
    for organo in organos:
        info = analizar_organo(organo)
        grupos.setdefault(clave_organo(info), []).append(info)

    if len(grupos) > 1:
        representantes = []
        for infos in grupos.values():
            representantes.append(infos[0]["organo_completo"])
        raise PDFConVariosJuzgadosError(representantes)

    # Un único órgano real.
    return list(grupos.values())[0][0]



def es_continuacion_de_fila(linea: str) -> bool:
    """
    Detecta líneas huérfanas que pertenecen a la fila anterior.

    En los PDFs judiciales muchas celdas aparecen partidas:
    - procedimiento en dos líneas;
    - materia en dos líneas;
    - último trámite en varias líneas.

    Una línea de continuación normalmente:
    - no empieza por número de expediente;
    - no es cabecera ni pie;
    - no es órgano;
    - no es solo una fecha;
    - contiene texto útil.
    """
    linea = limpiar_texto(linea)

    if not linea:
        return False

    if EXPEDIENTE_RE.match(linea):
        return False

    if es_linea_ruido(linea) or es_linea_organo(linea):
        return False

    # No consideramos continuación una línea formada solo por fecha/página/número.
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", linea):
        return False

    if re.fullmatch(r"\d+", linea):
        return False

    return True


def unir_fragmentos_texto(partes: List[str]) -> str:
    """
    Une fragmentos manteniendo palabras y evitando dobles espacios.
    También corrige algunos cortes frecuentes.
    """
    texto = " ".join(limpiar_texto(p) for p in partes if p and p.strip())
    texto = quitar_duplicados_espacios(texto)

    # Correcciones genéricas por cortes raros de PDF.
    texto = texto.replace("  ", " ")
    texto = texto.replace(" - - ", " - ")
    texto = re.sub(r"\(\s+", "(", texto)
    texto = re.sub(r"\s+\)", ")", texto)

    return texto.strip()


def reconstruir_lineas_logicas(texto: str) -> List[str]:
    """
    Reconstruye filas lógicas del PDF antes de parsearlas.

    Si una línea no empieza por expediente y parece continuación,
    se añade a la fila anterior.

    Esto mejora de forma general:
    - procedimiento;
    - materia;
    - último trámite;
    - textos largos partidos por salto de línea.
    """
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
                # Si no parece continuación, aun así la conservamos pegada
                # para no perder información, salvo que sea ruido.
                actual.append(linea)

    if actual:
        lineas_logicas.append(unir_fragmentos_texto(actual))

    return [l for l in lineas_logicas if l.strip()]


def dividir_en_bloques(texto: str) -> List[str]:
    """
    Divide el PDF en bloques de expediente, reconstruyendo previamente
    líneas partidas por el salto visual del PDF.
    """
    bloques = reconstruir_lineas_logicas(texto)
    return [limpiar_texto(b) for b in bloques if b.strip()]

def limpiar_procedimiento(texto: str) -> str:
    texto = quitar_duplicados_espacios(texto)
    texto = texto.replace("  -  ", " - ")
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


def extraer_procedimiento_y_resto(resto: str, fechas: List[re.Match]):
    """
    Extrae procedimiento usando la primera fecha como separador principal.

    Si antes de la fecha aparece un texto partido, ya llega unido desde
    reconstruir_lineas_logicas().
    """
    fecha_aceptacion = fechas[0].group(0)
    antes_fecha = resto[: fechas[0].start()].strip()
    despues_fecha = resto[fechas[0].end():].strip()

    return limpiar_procedimiento(antes_fecha), fecha_aceptacion, despues_fecha


def parsear_bloque(bloque: str) -> Optional[Dict]:
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

    procedimiento, fecha_aceptacion, despues_fecha = extraer_procedimiento_y_resto(resto, fechas)

    # Recalcular fechas en el texto posterior a la primera fecha.
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
        # Si no detecta fase, dejamos el cuerpo como último trámite para no perder información.
        materia = ""
        ultimo_tramite = quitar_duplicados_espacios(cuerpo)

    # Si la cola contiene texto útil, lo añadimos al último trámite,
    # salvo que parezca claramente continuación del procedimiento.
    if cola:
        cola_limpia = quitar_duplicados_espacios(cola)
        if cola_limpia:
            ultimo_tramite = quitar_duplicados_espacios((ultimo_tramite + " " + cola_limpia).strip())

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


# =========================
# PARSER POR COORDENADAS PDF
# =========================
#
# Estos PDFs ALARDE son tablas visuales. Cuando una celda ocupa varias líneas,
# pdfplumber puede extraer el texto en orden extraño si usamos texto corrido.
# Por eso este parser usa posiciones X/Y para reconstruir cada columna.

COLUMNAS_X = {
    "numero": (0, 78),
    "procedimiento": (78, 195),
    "fecha_aceptacion": (195, 260),
    "materia": (260, 395),
    "fase_procesal": (395, 462),
    "ultimo_tramite": (462, 602),
    "fecha_ultimo_tramite": (602, 685),
    "proximo_tramite": (685, 900),
}


def texto_columna(words: List[Dict], x_min: float, x_max: float) -> str:
    seleccion = [
        w for w in words
        if w.get("x0", 0) >= x_min and w.get("x0", 0) < x_max
    ]

    if not seleccion:
        return ""

    seleccion = sorted(seleccion, key=lambda w: (round(w["top"], 1), w["x0"]))

    lineas = []
    actual = []
    top_actual = None

    for w in seleccion:
        top = w["top"]
        if top_actual is None or abs(top - top_actual) <= 3:
            actual.append(w)
            if top_actual is None:
                top_actual = top
        else:
            actual = sorted(actual, key=lambda x: x["x0"])
            lineas.append(" ".join(x["text"] for x in actual))
            actual = [w]
            top_actual = top

    if actual:
        actual = sorted(actual, key=lambda x: x["x0"])
        lineas.append(" ".join(x["text"] for x in actual))

    return limpiar_campo_pdf(" ".join(lineas))


def limpiar_campo_pdf(texto: str) -> str:
    texto = limpiar_texto(texto)
    reemplazos = {
        "Inicio/Demanda a": "Inicio/Demanda",
        "Inicio/Demand a": "Inicio/Demanda",
        "Inicio/Demand": "Inicio/Demanda",
        "Inicio/Solicitu d": "Inicio/Solicitud",
        "Despacho/Req uerimiento": "Despacho/Requerimiento",
        "Admisión/Req uerimiento": "Admisión/Requerimiento",
        "Admisión/Cita ción": "Admisión/Citación",
        "Oposición/Des p Ejec/Resolució n": "Oposición/Desp Ejec/Resolución",
        "Ejec/Resolució n": "Ejec/Resolución",
        "Audiencia Previa": "Audiencia Previa",
        "Pendiente de resolver": "Pendiente de resolver",
    }
    for a, b in reemplazos.items():
        texto = texto.replace(a, b)

    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def palabras_pagina(page) -> List[Dict]:
    return page.extract_words(
        x_tolerance=1,
        y_tolerance=3,
        keep_blank_chars=False,
        use_text_flow=False,
    )


def extraer_registros_por_coordenadas(pdf_file) -> List[Dict]:
    registros = []

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            words = palabras_pagina(page)

            # Zona útil de la tabla. Excluye cabecera y pie.
            words = [
                w for w in words
                if w.get("top", 0) > 120
                and w.get("top", 0) < 570
                and not es_linea_ruido(w.get("text", ""))
            ]

            starts = [
                idx for idx, w in enumerate(words)
                if EXPEDIENTE_RE.match(w.get("text", ""))
                and w.get("x0", 999) < 78
            ]

            for pos, start_idx in enumerate(starts):
                end_idx = starts[pos + 1] if pos + 1 < len(starts) else len(words)
                bloque_words = words[start_idx:end_idx]

                numero = texto_columna(bloque_words, *COLUMNAS_X["numero"])
                m_num = EXPEDIENTE_RE.search(numero)
                if not m_num:
                    continue
                numero = m_num.group(0)

                procedimiento = texto_columna(bloque_words, *COLUMNAS_X["procedimiento"])
                fecha_aceptacion = texto_columna(bloque_words, *COLUMNAS_X["fecha_aceptacion"])
                materia = texto_columna(bloque_words, *COLUMNAS_X["materia"])
                fase = texto_columna(bloque_words, *COLUMNAS_X["fase_procesal"])
                ultimo = texto_columna(bloque_words, *COLUMNAS_X["ultimo_tramite"])
                fecha_ultimo = texto_columna(bloque_words, *COLUMNAS_X["fecha_ultimo_tramite"])

                fechas_aceptacion = FECHA_RE.findall(fecha_aceptacion)
                fecha_aceptacion = fechas_aceptacion[0] if fechas_aceptacion else ""

                fechas_ultimo = FECHA_RE.findall(fecha_ultimo)
                fecha_ultimo = fechas_ultimo[-1] if fechas_ultimo else ""

                texto_original = limpiar_campo_pdf(
                    " ".join(
                        w.get("text", "")
                        for w in sorted(bloque_words, key=lambda x: (x["top"], x["x0"]))
                    )
                )

                registros.append(
                    {
                        "numero_procedimiento": numero,
                        "fecha_aceptacion": fecha_aceptacion,
                        "materia": materia,
                        "fase_procesal": fase,
                        "ultimo_tramite": ultimo,
                        "fecha_ultimo_tramite": fecha_ultimo,
                        "procedimiento": procedimiento,
                        "texto_original": texto_original,
                    }
                )

    return registros


def extraer_expedientes(pdf_file) -> List[Dict]:
    """
    Extrae expedientes usando parser por coordenadas X/Y.

    Si el PDF no devuelve registros por coordenadas, usa como respaldo
    el parser textual anterior.
    """
    texto = extraer_texto(pdf_file)
    juzgado_info = extraer_juzgado_info(texto)

    try:
        registros_base = extraer_registros_por_coordenadas(pdf_file)
    except Exception:
        registros_base = []

    if not registros_base:
        bloques = dividir_en_bloques(texto)
        registros_base = []
        for bloque in bloques:
            reg = parsear_bloque(bloque)
            if reg and reg.get("numero_procedimiento"):
                registros_base.append(reg)

    registros = []
    vistos = set()

    for reg in registros_base:
        if reg and reg.get("numero_procedimiento"):
            reg["juzgado"] = juzgado_info["organo_completo"]
            reg["organo_completo"] = juzgado_info["organo_completo"]
            reg["juzgado_numero"] = juzgado_info["juzgado_numero"]
            reg["juzgado_tipo"] = juzgado_info["juzgado_tipo"]
            reg["juzgado_seccion"] = juzgado_info["juzgado_seccion"]
            reg["clave_expediente"] = crear_clave(reg)

            clave = reg["clave_expediente"]
            if clave not in vistos:
                registros.append(reg)
                vistos.add(clave)

    return registros

def crear_clave(reg: Dict) -> str:
    partes = [
        reg.get("organo_completo", ""),
        reg.get("numero_procedimiento", ""),
        reg.get("fecha_aceptacion", ""),
        reg.get("procedimiento", ""),
    ]
    return " | ".join(quitar_duplicados_espacios(p).lower() for p in partes)

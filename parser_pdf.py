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


def dividir_en_bloques(texto: str) -> List[str]:
    bloques = []
    actual = []

    for linea in texto.splitlines():
        linea = limpiar_texto(linea)
        if es_linea_ruido(linea) or es_linea_organo(linea):
            continue

        if EXPEDIENTE_RE.match(linea):
            if actual:
                bloques.append(" ".join(actual))
            actual = [linea]
        else:
            if actual:
                actual.append(linea)

    if actual:
        bloques.append(" ".join(actual))

    return [limpiar_texto(b) for b in bloques if b.strip()]


def detectar_fase(texto: str) -> Optional[str]:
    normalizado = texto.lower()
    for fase in sorted(FASES_CONOCIDAS, key=len, reverse=True):
        if fase.lower() in normalizado:
            return fase
    return None


def quitar_duplicados_espacios(texto: str) -> str:
    return re.sub(r"\s+", " ", texto or "").strip()


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
            "procedimiento": "",
            "texto_original": bloque,
        }

    fecha_aceptacion = fechas[0].group(0)
    fecha_ultimo = fechas[-1].group(0) if len(fechas) > 1 else ""

    antes_fecha = resto[: fechas[0].start()].strip()
    despues_fecha = resto[fechas[0].end():].strip()

    if fecha_ultimo:
        cuerpo = despues_fecha[: fechas[-1].start() - fechas[0].end()].strip()
        cola = despues_fecha[fechas[-1].end() - fechas[0].end():].strip()
    else:
        cuerpo = despues_fecha
        cola = ""

    fase = detectar_fase(cuerpo) or ""

    if fase:
        partes = re.split(re.escape(fase), cuerpo, maxsplit=1, flags=re.IGNORECASE)
        materia = quitar_duplicados_espacios(partes[0])
        ultimo_tramite = quitar_duplicados_espacios(partes[1] if len(partes) > 1 else "")
    else:
        materia = ""
        ultimo_tramite = quitar_duplicados_espacios(cuerpo)

    procedimiento = quitar_duplicados_espacios(antes_fecha or cola)
    if not procedimiento and cola:
        procedimiento = quitar_duplicados_espacios(cola)

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


def extraer_expedientes(pdf_file) -> List[Dict]:
    texto = extraer_texto(pdf_file)
    juzgado_info = extraer_juzgado_info(texto)
    bloques = dividir_en_bloques(texto)
    registros = []

    for bloque in bloques:
        reg = parsear_bloque(bloque)
        if reg and reg.get("numero_procedimiento"):
            reg["juzgado"] = juzgado_info["organo_completo"]
            reg["organo_completo"] = juzgado_info["organo_completo"]
            reg["juzgado_numero"] = juzgado_info["juzgado_numero"]
            reg["juzgado_tipo"] = juzgado_info["juzgado_tipo"]
            reg["juzgado_seccion"] = juzgado_info["juzgado_seccion"]
            reg["clave_expediente"] = crear_clave(reg)
            registros.append(reg)

    return registros


def crear_clave(reg: Dict) -> str:
    partes = [
        reg.get("organo_completo", ""),
        reg.get("numero_procedimiento", ""),
        reg.get("fecha_aceptacion", ""),
        reg.get("procedimiento", ""),
    ]
    return " | ".join(quitar_duplicados_espacios(p).lower() for p in partes)

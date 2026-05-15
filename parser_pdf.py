import re
from datetime import datetime
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
    "Plaza Nº",
    "Procedimiento",
    "Materia",
    "Página:",
    "Fecha Últ. Tramite",
    "Fecha Últ. Trámite",
    "Próximo Trámite",
]


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


def dividir_en_bloques(texto: str) -> List[str]:
    bloques = []
    actual = []

    for linea in texto.splitlines():
        linea = limpiar_texto(linea)
        if es_linea_ruido(linea):
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

    # En el PDF suele haber una fecha de aceptación y, al final o cerca del final,
    # la fecha del último trámite.
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

    materia = ""
    ultimo_tramite = cuerpo
    procedimiento = ""

    if fase:
        partes = re.split(re.escape(fase), cuerpo, maxsplit=1, flags=re.IGNORECASE)
        materia = quitar_duplicados_espacios(partes[0])
        ultimo_tramite = quitar_duplicados_espacios(partes[1] if len(partes) > 1 else "")
    else:
        # Fallback: si no detecta fase, conserva el texto.
        materia = ""
        ultimo_tramite = quitar_duplicados_espacios(cuerpo)

    # El procedimiento puede venir antes de la fecha o en la cola del registro.
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
    bloques = dividir_en_bloques(texto)
    registros = []

    for bloque in bloques:
        reg = parsear_bloque(bloque)
        if reg and reg.get("numero_procedimiento"):
            reg["clave_expediente"] = crear_clave(reg)
            registros.append(reg)

    return registros


def crear_clave(reg: Dict) -> str:
    # Hay expedientes con el mismo número en procedimientos distintos.
    partes = [
        reg.get("numero_procedimiento", ""),
        reg.get("fecha_aceptacion", ""),
        reg.get("procedimiento", ""),
    ]
    return " | ".join(quitar_duplicados_espacios(p).lower() for p in partes)

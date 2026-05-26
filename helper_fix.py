def quitar_duplicados_espacios(texto):
    """
    Limpia espacios duplicados y saltos de línea repetidos.
    """
    if texto is None:
        return ""

    texto = str(texto)
    texto = " ".join(texto.split())
    return texto

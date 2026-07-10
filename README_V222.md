# Versión v2.2.2

Corrige los PDFs que contienen varios tipos de resolución dentro del mismo
documento.

Antes se tomaba únicamente el primer `Tipo Resolución:` del PDF y se aplicaba
a todos los registros.

Ahora el tipo se detecta en cada página y se aplica únicamente a las
resoluciones de esa página.

Ejemplo comprobado:

- Páginas anteriores al cambio: Decreto.
- Página 22 y siguientes: Auto.

## Archivos que debes sustituir

- parser_pdf.py
- version.py

No es necesario cambiar app.py ni database.py si ya tienes la versión v2.2.1.

# Parser multilínea global

Esta versión mejora el parser de PDF para reconstruir líneas partidas en cualquier campo.

## Qué mejora

Antes se corregían casos concretos como:

- `Ejecución de títulos` + `judiciales`

Ahora se intenta reconstruir cualquier línea huérfana del expediente:

- procedimiento partido en varias líneas;
- materia larga;
- último trámite largo;
- textos desplazados por saltos visuales del PDF.

## Archivos a sustituir

- parser_pdf.py
- version.py

Puedes subir el paquete completo, pero los cambios principales están en esos dos archivos.

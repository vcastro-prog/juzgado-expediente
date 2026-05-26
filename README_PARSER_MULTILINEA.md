# Mejora parser PDF: procedimientos en varias líneas

Corrige casos donde el tipo de procedimiento aparece partido en el PDF.

Ejemplo:

```text
0000002/2026 Ejecución de títulos
judiciales
```

Ahora se guarda como:

```text
Ejecución de títulos judiciales
```

## Archivos a sustituir

- parser_pdf.py
- version.py

Puedes sustituir solo esos dos archivos.

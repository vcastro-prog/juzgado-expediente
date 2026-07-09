# Juzgado Expedientes v2.0.0

Archivos principales:

- `parser_pdf.py`: parser v2 limpio.
- `app.py`: muestra App/Build/Parser en cabecera y diagnóstico al procesar PDF.
- `version.py`: versión de la aplicación.
- `TEST_RESULTADOS_PDFS.txt`: prueba con los PDFs subidos.

## Qué se ha añadido

- Detección automática de tipo de PDF:
  - `libro_resoluciones`
  - `alarde`
- Diagnóstico previo al guardado:
  - tipo de PDF;
  - páginas;
  - registros detectados;
  - versión del parser;
  - error, si lo hay.
- Reconstrucción más robusta de registros del Libro de Resoluciones:
  - fecha/hora/interviniente antes de la resolución;
  - procedimiento multilínea;
  - expediente en línea posterior.

## Qué subir a GitHub

Sustituye/sube como mínimo:

- `parser_pdf.py`
- `app.py`
- `version.py`

Después haz commit/push y en Streamlit Cloud pulsa `Reboot app`.

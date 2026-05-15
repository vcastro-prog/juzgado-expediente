# Versión 7 - Corrección Plaza 9 y todos los juzgados

Cambios:

- Corrige falsos positivos en la validación de varios juzgados.
- Acepta PDFs donde el mismo órgano se repite en cada página.
- Normaliza encabezados como:
  - `Órgano de registro: Plaza Nº 9 del Tribunal de Instancia (Sección Civil)`
  - `Plaza Nº 9 del Tribunal de Instancia (Sección Civil)`
- Sigue bloqueando PDFs si realmente detecta más de un órgano distinto.
- Muestra todos los juzgados en la cabecera de carga, no solo los cuatro mayores.
- Mantiene la tabla completa de carga por juzgado visible.

Archivos a sustituir:

- app.py
- database.py
- parser_pdf.py

Después:

1. GitHub Desktop.
2. Commit: `Versión 7 corrección carga por juzgado`
3. Push origin.

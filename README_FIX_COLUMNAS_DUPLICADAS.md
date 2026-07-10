# Corrección v2.2.1

El error `Duplicate column names found` se producía porque una o más columnas
aparecían repetidas en la selección visible.

## Cambios

- Se eliminan duplicados de `columnas_por_defecto`.
- Se deduplica automáticamente `columnas_visibles`.
- Se eliminan columnas duplicadas del DataFrame antes de `st.dataframe`.
- Se mantiene la exportación con las mismas columnas visibles.

## Archivos a sustituir

- app.py
- version.py

No hace falta sustituir parser_pdf.py ni database.py si ya tienes la v2.2.0.

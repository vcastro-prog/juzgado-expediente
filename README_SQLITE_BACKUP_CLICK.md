# Versión SQLite rápida con backup y filtro rápido por juzgado

Esta versión vuelve a SQLite local para máxima velocidad en Streamlit Cloud.

## Cambios

- Vuelve a `data/expedientes.sqlite`.
- Añade botón para descargar copia SQLite.
- Añade opción para restaurar copia SQLite.
- Mantiene toda la lógica de juzgados, filtros y favoritos.
- En el resumen por juzgado, cada tarjeta tiene botón `Filtrar`.
- Al pulsar `Filtrar`, la tabla inferior muestra solo los expedientes de ese juzgado.

## Archivos a sustituir

- app.py
- database.py
- requirements.txt

Mantén:
- parser_pdf.py

## Funcionamiento recomendado

1. Subir PDFs.
2. Al terminar, descargar copia SQLite.
3. Si Streamlit Cloud pierde datos, restaurar la copia SQLite desde la barra lateral.

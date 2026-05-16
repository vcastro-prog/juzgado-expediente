# Versión SQLite con flujo de backup

Esta versión mantiene SQLite local por velocidad y añade un flujo claro de copia/restauración.

## Qué cambia

- Barra lateral con sección `Backup / Restauración`.
- Muestra si existe base local, tamaño y fecha de modificación.
- Botón `Descargar copia SQLite` con nombre fechado.
- Restauración de copia SQLite.
- Aviso tras cada importación para descargar copia.
- El Excel queda como exportación secundaria; el backup completo recomendado es SQLite.

## Flujo recomendado

1. Subir PDFs.
2. Comprobar datos.
3. Descargar copia SQLite.
4. Guardarla en PC/NAS/nube privada.
5. Si Streamlit pierde datos, restaurar esa copia.
6. Subir solo PDFs nuevos posteriores al backup.

## Archivos a sustituir

- app.py
- database.py
- requirements.txt

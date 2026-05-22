# Filtro por terminación de número de expediente

Añade al campo `Nº procedimiento / patrón` estos patrones:

- `*5`: expedientes cuyo número termina en 5, sin contar el año.
- `*45`: expedientes cuyo número termina en 45.
- `*345`: expedientes cuyo número termina en 345.
- `*5/2025`: expedientes cuyo número termina en 5 y año 2025.
- `0002345/2026`: búsqueda normal parcial o exacta.

## Archivos a sustituir

- app.py
- database.py
- requirements.txt

Después:

1. Commit to main.
2. Push origin.
3. Streamlit redeploy automático.

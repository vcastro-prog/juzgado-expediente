# Exportación Excel con formato

Esta versión mejora la exportación Excel.

## Qué cambia

El Excel descargado incluye:

- Primera fila congelada.
- Autofiltro activado en la cabecera.
- Cabecera con fondo azul y letras blancas.
- Filas alternas:
  - una blanca;
  - otra azul claro.
- Bordes suaves.
- Ancho de columnas ajustado automáticamente.

## También mantiene

- Exportación de la vista filtrada activa.
- Si filtras por `*5`, exporta solo esos expedientes.
- Si filtras por juzgado/año/fase/materia, exporta solo esa selección.

## Archivos a sustituir

- app.py
- database.py
- requirements.txt

Después:
1. Commit to main.
2. Push origin.
3. Streamlit redeploy automático.

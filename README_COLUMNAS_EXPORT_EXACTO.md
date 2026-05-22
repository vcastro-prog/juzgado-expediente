# Columnas visibles y exportación exacta

Esta versión añade un selector de columnas en `Expedientes actuales`.

## Qué cambia

- Puedes elegir qué columnas ver en pantalla.
- La tabla queda más limpia.
- La exportación Excel usa exactamente:
  - los filtros aplicados;
  - las columnas seleccionadas;
  - el mismo orden de columnas mostrado.
- El Excel mantiene:
  - cabecera azul;
  - letras blancas;
  - filtros activados;
  - primera fila congelada;
  - filas alternas blanco / azul claro.

## Archivos a sustituir

- app.py
- database.py
- requirements.txt

Después:
1. Commit to main.
2. Push origin.
3. Streamlit redeploy automático.

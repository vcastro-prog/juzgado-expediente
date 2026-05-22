# Excel con colores operativos

Esta versión mantiene la exportación exacta:

- mismos filtros aplicados;
- mismas columnas visibles;
- mismo orden de columnas.

Y añade colores en el Excel:

- verde claro: expedientes modificados;
- amarillo claro: expedientes sin iniciar trámite;
- gris claro: archivados, si se exporta la columna correspondiente;
- azul oscuro en cabecera con letras blancas;
- filtros de Excel activados;
- primera fila congelada.

## Archivos a sustituir

- app.py
- database.py
- requirements.txt
- version.py

Después:

1. Commit to main.
2. Push origin.
3. Streamlit redeploy automático.

# v2.0.1 sobre app completa

Esta versión parte del `app.py` completo que subiste, que conserva:

- login;
- subida múltiple de PDFs;
- backup/restauración SQLite;
- filtros avanzados;
- reset de filtros;
- tarjetas por juzgado;
- columnas visibles;
- exportación Excel filtrada con formato;
- favoritos/notas;
- histórico de cambios.

Y añade:

- `Parser v2.0.0`;
- versión visible del parser en cabecera y barra lateral;
- diagnóstico de cada PDF importado:
  - tipo PDF;
  - páginas;
  - parser;
  - registros detectados/importados.

## Archivos a subir a GitHub

Sustituye como mínimo:

- app.py
- parser_pdf.py
- version.py

Después:

1. Commit.
2. Push.
3. Streamlit Cloud > Reboot app.
4. Comprueba que la cabecera muestre: `v2.0.1` y `Parser v2.0.0`.

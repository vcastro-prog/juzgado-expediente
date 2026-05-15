# Versión 6 - Órgano separado y validación de un juzgado por PDF

Añade:

- Nº juzgado.
- Tipo órgano.
- Sección.
- Órgano completo.
- Validación previa del PDF:
  - si detecta más de un órgano/juzgado, bloquea la importación;
  - muestra aviso;
  - no vuelca datos de ese PDF a la base de datos.

## Archivos a sustituir

- app.py
- database.py
- parser_pdf.py

Después:

1. GitHub Desktop.
2. Commit: `Versión 6 órgano separado y validación`
3. Push origin.

Mantén configurado el Secret de Streamlit:

```toml
APP_PASSWORD = "tu_contraseña"
```

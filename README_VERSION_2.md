# Versión 2 - Control de expedientes

Esta versión añade:

- Subida múltiple de PDFs.
- Filtros avanzados:
  - nº de procedimiento;
  - año;
  - procedimiento;
  - materia;
  - fase procesal;
  - último trámite contiene;
  - solo favoritos;
  - archivados/no archivados.
- Pestaña de expedientes modificados recientemente:
  - hoy;
  - últimos 7 días;
  - últimos 30 días;
  - todos.
- Vista detalle por expediente.
- Favoritos.
- Notas internas.
- Histórico individual por expediente.
- Exportación Excel.

## Cómo actualizar

Sustituye en tu repositorio estos archivos:

- `app.py`
- `database.py`

No hace falta cambiar `parser_pdf.py` ni `requirements.txt`.

Después:

1. Guarda los archivos.
2. Abre GitHub Desktop.
3. Commit:
   `Versión 2 filtros avanzados`
4. Push origin.
5. Streamlit se actualizará automáticamente.

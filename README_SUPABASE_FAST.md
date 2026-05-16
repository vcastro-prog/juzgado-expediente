# database.py optimizado para Supabase

Este archivo sustituye al `database.py` anterior.

Mejoras:

- Consulta expedientes existentes en bloque.
- Inserta/actualiza expedientes en lote.
- Inserta cambios históricos en lote.
- Añade índices básicos.
- Cachea lecturas durante 30 segundos.
- Reduce mucho el tiempo de importación en PDFs grandes.

## Archivos a sustituir

- database.py
- requirements.txt

Después:

1. GitHub Desktop.
2. Commit: `Optimiza importación Supabase`
3. Push origin.
4. Esperar redeploy en Streamlit Cloud.

## Nota

Si tienes una importación parcial previa, puedes:
- seguir subiendo los PDFs restantes; o
- borrar la base desde la app si quieres empezar de cero.

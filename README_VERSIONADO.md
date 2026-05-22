# Versión visible en la aplicación

Añade:

- `version.py`
- versión visible debajo del título;
- versión visible en la barra lateral.

## Versión incluida

```text
v1.9.0
```

## Archivos a subir/sustituir

```text
app.py
database.py
requirements.txt
version.py
```

## Cómo cambiar la versión en el futuro

Edita `version.py`:

```python
APP_VERSION = "v1.9.1"
BUILD_DATE = "2026-05-22"
APP_CHANGELOG = "Descripción breve del cambio."
```

Luego:

```text
Commit to main
Push origin
```

Así sabrás si Streamlit Cloud está mostrando la última versión desplegada.

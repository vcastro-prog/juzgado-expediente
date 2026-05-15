# Control de expedientes del juzgado

Aplicación Streamlit para subir PDFs diarios tipo ALARDE, extraer expedientes y mantener una tabla filtrable con histórico de cambios.

## Qué hace

- Permite subir un PDF diario.
- Extrae expedientes del listado.
- Guarda el estado actual en SQLite.
- Detecta cambios en fase procesal, último trámite, fecha del último trámite, procedimiento y materia.
- Muestra:
  - expedientes actuales;
  - cambios detectados;
  - histórico por expediente;
  - exportación a Excel.

## Estructura

```text
.
├─ app.py
├─ parser_pdf.py
├─ database.py
├─ requirements.txt
├─ data/
└─ .streamlit/
   └─ config.toml
```

## Ejecutar en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Subir a GitHub con GitHub Desktop

1. Descomprime este proyecto.
2. Abre GitHub Desktop.
3. File > Add local repository.
4. Selecciona la carpeta `juzgado-expedientes`.
5. Si te pide crear repositorio, acepta.
6. Haz commit:
   - Summary: `Primera versión app expedientes`
   - Click en `Commit to main`.
7. Click en `Publish repository`.

## Desplegar en Streamlit Community Cloud

1. Entra en Streamlit Community Cloud.
2. New app.
3. Selecciona el repositorio de GitHub.
4. Main file path: `app.py`.
5. Deploy.

## Importante sobre datos

Streamlit Community Cloud puede reiniciar la app y el archivo SQLite local podría perderse o no ser adecuado para uso definitivo.
La app incluye exportación a Excel. Para uso estable a largo plazo conviene migrar la base de datos a un servicio externo.

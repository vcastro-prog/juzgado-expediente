# Migración a Supabase/PostgreSQL

Este paquete cambia la persistencia de datos:

Antes:

```text
Streamlit Cloud → SQLite local
```

Ahora:

```text
Streamlit Cloud → Supabase PostgreSQL
```

Así, aunque Streamlit Cloud se duerma o reinicie, los datos no se pierden.

## Archivos que debes sustituir

En tu repositorio de GitHub sustituye:

```text
database.py
requirements.txt
```

No hace falta cambiar `app.py` ni `parser_pdf.py`.

## Crear proyecto en Supabase

1. Entra en https://supabase.com
2. Crea un proyecto nuevo.
3. Ve a `Project Settings → Database`.
4. Copia los datos de conexión:
   - Host
   - Port
   - Database
   - User
   - Password

## Configurar Secrets en Streamlit Cloud

En Streamlit Cloud:

```text
App → Settings → Secrets
```

Pega algo así:

```toml
APP_PASSWORD = "tu_clave_de_la_app"

DB_HOST = "db.xxxxxxxxxxxxx.supabase.co"
DB_PORT = "5432"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "la_contraseña_de_supabase"
DB_SSLMODE = "require"
```

## Publicar

Después en GitHub Desktop:

```text
Commit to main
Push origin
```

Streamlit redeplegará la app.

## Primer uso

Al abrir la app, `database.py` creará automáticamente las tablas en Supabase:

- expedientes
- historico_cambios
- importaciones

Después subes los PDFs una vez y los datos quedarán persistentes.

## Importante

No subas contraseñas a GitHub. Las contraseñas van solo en `Streamlit Cloud → Secrets`.

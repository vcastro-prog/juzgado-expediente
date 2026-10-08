from pathlib import Path
import streamlit as st
import database
from sqlite_backups import snapshot


def database_revision(path):
    path = Path(path)
    revision = []
    # WAL may contain committed changes not yet written to the main file.
    for candidate in (path, Path(str(path) + '-wal')):
        try:
            info = candidate.stat()
            revision.append((info.st_mtime_ns, info.st_ctime_ns, info.st_size))
        except FileNotFoundError:
            revision.append(None)
    return tuple(revision)


@st.cache_data(show_spinner=False, max_entries=12)
def cached_read(name, path, revision, sources=()):
    assert Path(path) == database.DB_PATH.resolve()
    if name == 'cargar_claves_por_fuentes':
        return database.cargar_claves_por_fuentes(list(sources))
    if name not in {'cargar_expedientes', 'cargar_cambios', 'cargar_importaciones', 'cargar_fuentes_disponibles'}:
        raise ValueError('Lectura desconocida')
    return getattr(database, name)()


@st.cache_data(show_spinner=False, max_entries=2)
def cached_backup(path, revision):
    return snapshot(Path(path))

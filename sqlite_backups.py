"""Consistent SQLite snapshots and validated restores for this application."""
from contextlib import closing
from datetime import datetime
from pathlib import Path
import sqlite3
import tempfile


REQUIRED = {
    'expedientes': {'clave_expediente', 'numero_procedimiento', 'fecha_aceptacion', 'materia', 'fase_procesal', 'ultimo_tramite', 'fecha_ultimo_tramite', 'procedimiento', 'juzgado', 'organo_completo', 'juzgado_numero', 'juzgado_tipo', 'juzgado_seccion', 'texto_original', 'primera_importacion', 'ultima_importacion'},
    'historico_cambios': {'id', 'clave_expediente', 'numero_procedimiento', 'fecha_cambio', 'campo', 'valor_anterior', 'valor_nuevo'},
    'importaciones': {'id', 'fecha_importacion', 'nombre_archivo', 'expedientes_leidos', 'cambios_detectados', 'nuevos_detectados'},
}


def read_only(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=30)


def snapshot(path):
    path = Path(path)
    if not path.exists():
        return None
    with closing(read_only(path)) as source:
        with closing(sqlite3.connect(':memory:')) as copy:
            source.backup(copy)
            return copy.serialize()


def validate(conn):
    if conn.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
        raise ValueError('La copia SQLite no supera la comprobación de integridad.')
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table, columns in REQUIRED.items():
        if table not in tables:
            raise ValueError('El archivo no es una copia compatible de expedientes.')
        actual = {r[1] for r in conn.execute(f'PRAGMA table_info({table})')}
        if not columns.issubset(actual):
            raise ValueError('La copia no contiene los campos necesarios de expedientes.')


def restore(path, data):
    path = Path(path)
    if not data.startswith(b'SQLite format 3\x00'):
        raise ValueError('El archivo no es una base SQLite válida.')
    path.parent.mkdir(parents=True, exist_ok=True)
    # Uploads are opened from a private temporary file and verified first.
    with tempfile.TemporaryDirectory(dir=path.parent) as tmp:
        uploaded = Path(tmp) / 'uploaded.sqlite'
        uploaded.write_bytes(data)
        with closing(read_only(uploaded)) as source:
            validate(source)
            previous = snapshot(path)
            safety = None
            if previous is not None:
                folder = path.parent / 'antes_de_restaurar'
                folder.mkdir(exist_ok=True)
                safety = folder / ('expedientes_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.sqlite')
                safety.write_bytes(previous)
            # SQLite handles the destination transaction and any journal files.
            with closing(sqlite3.connect(path, timeout=30)) as target:
                source.backup(target)
    return safety

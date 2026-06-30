"""Camada de acesso ao SQLite (sem dependência de PySide6).

Centraliza a abertura de conexões e a criação do schema. As operações de
domínio ficam em :mod:`visionflow.infrastructure.persistence.repositories`.
"""

from __future__ import annotations

import logging
import sqlite3

from visionflow.infrastructure.paths import DB_PATH, ensure_data_dirs

_logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS camera_config (
    id           INTEGER PRIMARY KEY CHECK (id = 1),
    model        TEXT NOT NULL,
    backend      TEXT DEFAULT 'opt',
    name         TEXT,
    serial       TEXT,
    ip           TEXT,
    mac          TEXT,
    interface    TEXT,
    tl_type      TEXT,
    device_index INTEGER,
    opencv_index INTEGER,
    video_path   TEXT,
    updated_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS captures (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    frame_id     INTEGER,
    file_path    TEXT NOT NULL,
    width        INTEGER,
    height       INTEGER,
    pixel_format TEXT,
    captured_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recordings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path       TEXT NOT NULL UNIQUE,
    width           INTEGER,
    height          INTEGER,
    duration_ms     INTEGER,
    file_size_bytes INTEGER,
    recorded_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_recordings_recorded_at ON recordings(recorded_at);

CREATE TABLE IF NOT EXISTS app_logs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    logged_at      TEXT NOT NULL,
    level          TEXT NOT NULL,
    logger_name    TEXT NOT NULL,
    message        TEXT NOT NULL,
    exception_text TEXT
);

CREATE INDEX IF NOT EXISTS idx_app_logs_logged_at ON app_logs(logged_at);

CREATE TABLE IF NOT EXISTS yolo_datasets (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS yolo_classes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id  INTEGER NOT NULL,
    name        TEXT NOT NULL,
    color       TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    FOREIGN KEY (dataset_id) REFERENCES yolo_datasets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_yolo_classes_dataset ON yolo_classes(dataset_id);

CREATE TABLE IF NOT EXISTS yolo_dataset_images (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER NOT NULL,
    capture_id INTEGER NOT NULL,
    FOREIGN KEY (dataset_id) REFERENCES yolo_datasets(id) ON DELETE CASCADE,
    FOREIGN KEY (capture_id) REFERENCES captures(id) ON DELETE CASCADE,
    UNIQUE (dataset_id, capture_id)
);

CREATE INDEX IF NOT EXISTS idx_yolo_dataset_images_dataset
    ON yolo_dataset_images(dataset_id);

CREATE TABLE IF NOT EXISTS yolo_annotations (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER NOT NULL,
    class_id INTEGER NOT NULL,
    kind     TEXT NOT NULL,
    points   TEXT NOT NULL,
    FOREIGN KEY (image_id) REFERENCES yolo_dataset_images(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES yolo_classes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_yolo_annotations_image
    ON yolo_annotations(image_id);
"""


def connect() -> sqlite3.Connection:
    """Abre uma conexão com o banco, garantindo diretórios e schema.

    A conexão usa ``row_factory`` de dicionário (``sqlite3.Row``) e ativa as
    *foreign keys*. Cada chamada devolve uma conexão nova, segura para uso na
    thread que a abriu.
    """
    ensure_data_dirs()
    try:
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
    except sqlite3.Error:
        _logger.exception("Falha ao abrir banco em %s.", DB_PATH)
        raise
    return connection


def _migrate_schema(connection: sqlite3.Connection) -> None:
    """Aplica migrações incrementais em bancos já existentes."""
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(camera_config)").fetchall()
    }
    if "backend" not in columns:
        connection.execute(
            "ALTER TABLE camera_config ADD COLUMN backend TEXT DEFAULT 'opt'"
        )
        _logger.info("Migração: coluna camera_config.backend adicionada.")
    if "opencv_index" not in columns:
        connection.execute("ALTER TABLE camera_config ADD COLUMN opencv_index INTEGER")
        _logger.info("Migração: coluna camera_config.opencv_index adicionada.")
    if "video_path" not in columns:
        connection.execute("ALTER TABLE camera_config ADD COLUMN video_path TEXT")
        _logger.info("Migração: coluna camera_config.video_path adicionada.")


def initialize() -> None:
    """Cria as tabelas do banco caso ainda não existam."""
    try:
        with connect() as connection:
            connection.executescript(_SCHEMA)
            _migrate_schema(connection)
        _logger.debug("Schema SQLite verificado em %s.", DB_PATH)
    except sqlite3.Error:
        _logger.exception("Falha ao inicializar schema do banco.")
        raise

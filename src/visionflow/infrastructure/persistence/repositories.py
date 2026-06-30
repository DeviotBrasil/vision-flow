"""Repositórios SQLite que implementam os contratos de persistência do domínio.

Mapeiam ``sqlite3.Row`` para entidades de domínio e encapsulam todo o SQL.
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

from visionflow.domain.camera_backends import BACKEND_OPT
from visionflow.domain.contracts.camera_config_repository import (
    CameraConfigRepository,
)
from visionflow.domain.contracts.capture_repository import CaptureRepository
from visionflow.domain.contracts.log_repository import LogRepository
from visionflow.domain.contracts.recording_repository import RecordingRepository
from visionflow.domain.contracts.yolo_repository import YoloRepository
from visionflow.domain.entities.camera_config import CameraConfig
from visionflow.domain.entities.capture import Capture
from visionflow.domain.entities.filtered_page import FilteredPage
from visionflow.domain.entities.log_entry import LogEntry
from visionflow.domain.entities.recording import Recording
from visionflow.domain.entities.yolo import (
    YoloAnnotation,
    YoloClass,
    YoloDataset,
    YoloDatasetImage,
)
from visionflow.domain.exceptions import PersistenceError
from visionflow.infrastructure.persistence.base import (
    SqliteRepositoryBase,
    build_date_range_clause,
    fetch_entities_by_id_batches,
)
from visionflow.infrastructure.persistence.database import connect
from visionflow.infrastructure.video.video_metadata import (
    parse_recorded_at,
    read_video_properties,
    recorded_at_iso,
)

_logger = logging.getLogger(__name__)


class SqliteCameraConfigRepository(CameraConfigRepository, SqliteRepositoryBase):
    """Persistência da configuração única da câmera no SQLite."""

    def save(self, config: CameraConfig) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        try:
            with connect() as connection:
                connection.execute(
                    """
                    INSERT INTO camera_config (
                        id, model, backend, name, serial, ip, mac, interface,
                        tl_type, device_index, opencv_index, video_path, updated_at
                    ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        model = excluded.model,
                        backend = excluded.backend,
                        name = excluded.name,
                        serial = excluded.serial,
                        ip = excluded.ip,
                        mac = excluded.mac,
                        interface = excluded.interface,
                        tl_type = excluded.tl_type,
                        device_index = excluded.device_index,
                        opencv_index = excluded.opencv_index,
                        video_path = excluded.video_path,
                        updated_at = excluded.updated_at
                    """,
                    (
                        config.model,
                        config.backend,
                        config.name,
                        config.serial,
                        config.ip,
                        config.mac,
                        config.interface,
                        config.tl_type,
                        config.device_index,
                        config.opencv_index,
                        config.video_path,
                        now,
                    ),
                )
        except sqlite3.Error:
            _logger.exception("Falha ao salvar configuração da câmera.")
            raise
        _logger.info(
            "Configuração da câmera salva (modelo=%s, serial=%s).",
            config.model,
            config.serial,
        )

    def load(self) -> CameraConfig | None:
        try:
            row = self.fetch_one("SELECT * FROM camera_config WHERE id = 1")
        except sqlite3.Error:
            _logger.exception("Falha ao carregar configuração da câmera.")
            raise
        if row is None:
            return None
        return self._row_to_config(row)

    @staticmethod
    def _row_to_config(row: sqlite3.Row) -> CameraConfig:
        return CameraConfig(
            model=row["model"] or "",
            backend=row["backend"] or BACKEND_OPT,
            name=row["name"] or "",
            serial=row["serial"] or "",
            ip=row["ip"] or "",
            mac=row["mac"] or "",
            interface=row["interface"] or "",
            tl_type=row["tl_type"] or "",
            device_index=row["device_index"],
            opencv_index=row["opencv_index"],
            video_path=row["video_path"],
            updated_at=row["updated_at"],
        )


class SqliteCaptureRepository(CaptureRepository, SqliteRepositoryBase):
    """Persistência das capturas no SQLite."""

    def add(self, capture: Capture) -> int:
        captured_at = capture.captured_at or datetime.now().isoformat(
            timespec="seconds"
        )
        try:
            with connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO captures (
                        frame_id, file_path, width, height, pixel_format, captured_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        capture.frame_id,
                        capture.file_path,
                        capture.width,
                        capture.height,
                        capture.pixel_format,
                        captured_at,
                    ),
                )
                capture_id = int(cursor.lastrowid)
        except sqlite3.Error as exc:
            _logger.exception("Falha ao registrar captura em %s.", capture.file_path)
            raise PersistenceError(str(exc)) from exc
        _logger.info(
            "Captura registrada id=%s arquivo=%s.", capture_id, capture.file_path
        )
        return capture_id

    def list_recent(self, limit: int = 20) -> list[Capture]:
        try:
            rows = self.fetch_all(
                "SELECT * FROM captures ORDER BY id DESC LIMIT ?", (limit,)
            )
        except sqlite3.Error:
            _logger.exception("Falha ao listar capturas.")
            raise
        return [self._row_to_capture(row) for row in rows]

    def list_filtered(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        limit: int,
        offset: int = 0,
    ) -> list[Capture]:
        return self.list_filtered_page(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        ).entries

    def count_filtered(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
    ) -> int:
        return self.list_filtered_page(
            start_date=start_date,
            end_date=end_date,
            limit=0,
            offset=0,
        ).total

    def list_filtered_page(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        limit: int,
        offset: int = 0,
    ) -> FilteredPage[Capture]:
        where_clause, params = build_date_range_clause(
            start_date=start_date,
            end_date=end_date,
        )
        count_query = f"SELECT COUNT(*) AS total FROM captures {where_clause}"
        try:
            count_row = self.fetch_one(count_query, params)
            total = int(count_row["total"]) if count_row else 0
            if limit <= 0:
                return FilteredPage(entries=[], total=total)
            list_query = f"""
                SELECT * FROM captures
                {where_clause}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """
            rows = self.fetch_all(list_query, (*params, limit, offset))
        except sqlite3.Error:
            _logger.exception("Falha ao listar capturas filtradas.")
            raise
        return FilteredPage(
            entries=[self._row_to_capture(row) for row in rows],
            total=total,
        )

    def list_filtered_ids(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
    ) -> list[int]:
        where_clause, params = build_date_range_clause(
            start_date=start_date,
            end_date=end_date,
        )
        list_query = f"""
            SELECT id FROM captures
            {where_clause}
            ORDER BY id DESC
        """
        try:
            rows = self.fetch_all(list_query, params)
        except sqlite3.Error:
            _logger.exception("Falha ao listar ids de capturas filtradas.")
            raise
        return [int(row["id"]) for row in rows]

    def list_by_ids(self, ids: list[int]) -> list[Capture]:
        if not ids:
            return []

        def fetch_batch(batch: list[int]) -> list[Capture]:
            placeholders = ",".join("?" * len(batch))
            list_query = f"""
                SELECT * FROM captures
                WHERE id IN ({placeholders})
                ORDER BY id DESC
            """
            try:
                rows = self.fetch_all(list_query, tuple(batch))
            except sqlite3.Error:
                _logger.exception("Falha ao listar capturas por ids.")
                raise
            return [self._row_to_capture(row) for row in rows]

        entries = fetch_entities_by_id_batches(ids, fetch_batch)
        entries.sort(key=lambda capture: int(capture.id or 0), reverse=True)
        return entries

    def count(self) -> int:
        try:
            row = self.fetch_one("SELECT COUNT(*) AS total FROM captures")
        except sqlite3.Error:
            _logger.exception("Falha ao contar capturas.")
            raise
        return int(row["total"]) if row else 0

    def get(self, capture_id: int) -> Capture | None:
        try:
            row = self.fetch_one("SELECT * FROM captures WHERE id = ?", (capture_id,))
        except sqlite3.Error:
            _logger.exception("Falha ao buscar captura id=%s.", capture_id)
            raise
        return self._row_to_capture(row) if row else None

    def get_by_path(self, file_path: str) -> Capture | None:
        try:
            row = self.fetch_one(
                "SELECT * FROM captures WHERE file_path = ?", (file_path,)
            )
        except sqlite3.Error:
            _logger.exception("Falha ao buscar captura em %s.", file_path)
            raise
        return self._row_to_capture(row) if row else None

    def update_dimensions(
        self,
        capture_id: int,
        *,
        width: int,
        height: int,
    ) -> bool:
        try:
            with connect() as connection:
                cursor = connection.execute(
                    """
                    UPDATE captures
                    SET width = ?, height = ?
                    WHERE id = ?
                    """,
                    (width, height, capture_id),
                )
        except sqlite3.Error as exc:
            _logger.exception(
                "Falha ao atualizar dimensões da captura id=%s.", capture_id
            )
            raise PersistenceError(str(exc)) from exc
        updated = cursor.rowcount > 0
        if updated:
            _logger.info(
                "Dimensões da captura id=%s atualizadas para %sx%s.",
                capture_id,
                width,
                height,
            )
        return updated

    def delete(self, capture_id: int) -> str | None:
        try:
            with connect() as connection:
                row = connection.execute(
                    "SELECT file_path FROM captures WHERE id = ?", (capture_id,)
                ).fetchone()
                if row is None:
                    return None
                connection.execute("DELETE FROM captures WHERE id = ?", (capture_id,))
                file_path = row["file_path"]
        except sqlite3.Error:
            _logger.exception("Falha ao excluir captura id=%s.", capture_id)
            raise
        _logger.info("Captura excluída id=%s arquivo=%s.", capture_id, file_path)
        return file_path

    @staticmethod
    def _row_to_capture(row: sqlite3.Row) -> Capture:
        return Capture(
            id=row["id"],
            file_path=row["file_path"],
            frame_id=row["frame_id"],
            width=row["width"],
            height=row["height"],
            pixel_format=row["pixel_format"],
            captured_at=row["captured_at"],
        )


class SqliteRecordingRepository(RecordingRepository, SqliteRepositoryBase):
    """Persistência das gravações no SQLite (IDs estáveis como capturas)."""

    def __init__(self, recordings_dir: Path) -> None:
        self._recordings_dir = Path(recordings_dir)
        self.sync_filesystem()

    def sync_filesystem(self) -> None:
        """Cadastra MP4 órfãos no banco, do mais antigo ao mais recente."""
        if not self._recordings_dir.is_dir():
            return
        known = self._known_paths()
        orphans = sorted(
            (
                path.resolve()
                for path in self._recordings_dir.glob("*.mp4")
                if path.is_file() and str(path.resolve()) not in known
            ),
            key=self._path_sort_key,
        )
        for path in orphans:
            self._insert_from_path(path)

    def register_file(self, file_path: str) -> int | None:
        path = Path(file_path)
        if not path.is_file():
            return None
        resolved = str(path.resolve())
        existing = self.get_by_path(resolved)
        if existing is not None and existing.id is not None:
            return existing.id
        return self._insert_from_path(path.resolve())

    def import_external_file(self, source_path: str) -> int | None:
        path = Path(source_path)
        if not path.is_file() or path.suffix.lower() != ".mp4":
            return None
        duration_ms, width, height = read_video_properties(path)
        if duration_ms is None and width is None and height is None:
            return None
        resolved = path.resolve()
        if resolved.parent == self._recordings_dir.resolve():
            return self.register_file(str(resolved))
        self._recordings_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        dest = self._recordings_dir / f"{stamp}.mp4"
        while dest.exists():
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            dest = self._recordings_dir / f"{stamp}.mp4"
        try:
            shutil.copy2(resolved, dest)
        except OSError:
            _logger.exception("Falha ao copiar gravação de %s.", source_path)
            return None
        return self.register_file(str(dest.resolve()))

    def add(self, recording: Recording) -> int:
        recorded_at = recording.recorded_at or datetime.now().isoformat(
            timespec="seconds"
        )
        try:
            with connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO recordings (
                        file_path, width, height, duration_ms,
                        file_size_bytes, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        recording.file_path,
                        recording.width,
                        recording.height,
                        recording.duration_ms,
                        recording.file_size_bytes,
                        recorded_at,
                    ),
                )
                recording_id = int(cursor.lastrowid)
        except sqlite3.IntegrityError:
            existing = self.get_by_path(recording.file_path)
            if existing is not None and existing.id is not None:
                return existing.id
            raise
        except sqlite3.Error as exc:
            _logger.exception("Falha ao registrar gravação em %s.", recording.file_path)
            raise PersistenceError(str(exc)) from exc
        _logger.info(
            "Gravação registrada id=%s arquivo=%s.",
            recording_id,
            recording.file_path,
        )
        return recording_id

    def list_filtered(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        limit: int,
        offset: int = 0,
    ) -> list[Recording]:
        return self.list_filtered_page(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        ).entries

    def count_filtered(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
    ) -> int:
        return self.list_filtered_page(
            start_date=start_date,
            end_date=end_date,
            limit=0,
            offset=0,
        ).total

    def list_filtered_page(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        limit: int,
        offset: int = 0,
    ) -> FilteredPage[Recording]:
        where_clause, params = build_date_range_clause(
            start_date=start_date,
            end_date=end_date,
            column="recorded_at",
        )
        count_query = f"SELECT COUNT(*) AS total FROM recordings {where_clause}"
        try:
            count_row = self.fetch_one(count_query, params)
            total = int(count_row["total"]) if count_row else 0
            if limit <= 0:
                return FilteredPage(entries=[], total=total)
            list_query = f"""
                SELECT * FROM recordings
                {where_clause}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """
            rows = self.fetch_all(list_query, (*params, limit, offset))
        except sqlite3.Error:
            _logger.exception("Falha ao listar gravações filtradas.")
            raise
        return FilteredPage(
            entries=[self._row_to_recording(row) for row in rows],
            total=total,
        )

    def list_filtered_ids(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
    ) -> list[int]:
        where_clause, params = build_date_range_clause(
            start_date=start_date,
            end_date=end_date,
            column="recorded_at",
        )
        list_query = f"""
            SELECT id FROM recordings
            {where_clause}
            ORDER BY id DESC
        """
        try:
            rows = self.fetch_all(list_query, params)
        except sqlite3.Error:
            _logger.exception("Falha ao listar ids de gravações filtradas.")
            raise
        return [int(row["id"]) for row in rows]

    def list_by_ids(self, ids: list[int]) -> list[Recording]:
        if not ids:
            return []

        def fetch_batch(batch: list[int]) -> list[Recording]:
            placeholders = ",".join("?" * len(batch))
            list_query = f"""
                SELECT * FROM recordings
                WHERE id IN ({placeholders})
                ORDER BY id DESC
            """
            try:
                rows = self.fetch_all(list_query, tuple(batch))
            except sqlite3.Error:
                _logger.exception("Falha ao listar gravações por ids.")
                raise
            return [self._row_to_recording(row) for row in rows]

        entries = fetch_entities_by_id_batches(ids, fetch_batch)
        entries.sort(key=lambda recording: int(recording.id or 0), reverse=True)
        return entries

    def count(self) -> int:
        try:
            row = self.fetch_one("SELECT COUNT(*) AS total FROM recordings")
        except sqlite3.Error:
            _logger.exception("Falha ao contar gravações.")
            raise
        return int(row["total"]) if row else 0

    def get(self, recording_id: int) -> Recording | None:
        try:
            row = self.fetch_one(
                "SELECT * FROM recordings WHERE id = ?", (recording_id,)
            )
        except sqlite3.Error:
            _logger.exception("Falha ao buscar gravação id=%s.", recording_id)
            raise
        return self._row_to_recording(row) if row else None

    def get_by_path(self, file_path: str) -> Recording | None:
        try:
            row = self.fetch_one(
                "SELECT * FROM recordings WHERE file_path = ?", (file_path,)
            )
        except sqlite3.Error:
            _logger.exception("Falha ao buscar gravação em %s.", file_path)
            raise
        return self._row_to_recording(row) if row else None

    def delete(self, recording_id: int) -> str | None:
        try:
            with connect() as connection:
                row = connection.execute(
                    "SELECT file_path FROM recordings WHERE id = ?",
                    (recording_id,),
                ).fetchone()
                if row is None:
                    return None
                connection.execute(
                    "DELETE FROM recordings WHERE id = ?", (recording_id,)
                )
                file_path = row["file_path"]
        except sqlite3.Error:
            _logger.exception("Falha ao excluir gravação id=%s.", recording_id)
            raise
        _logger.info("Gravação excluída id=%s arquivo=%s.", recording_id, file_path)
        return file_path

    def _known_paths(self) -> set[str]:
        try:
            rows = self.fetch_all("SELECT file_path FROM recordings")
        except sqlite3.Error:
            _logger.exception("Falha ao listar caminhos de gravações.")
            raise
        return {row["file_path"] for row in rows}

    def _insert_from_path(self, path: Path) -> int:
        duration_ms, width, height = read_video_properties(path)
        try:
            file_size = path.stat().st_size
        except OSError:
            file_size = None
        recorded_at = recorded_at_iso(path) or datetime.now().isoformat(
            timespec="seconds"
        )
        return self.add(
            Recording(
                file_path=str(path.resolve()),
                recorded_at=recorded_at,
                duration_ms=duration_ms,
                width=width,
                height=height,
                file_size_bytes=file_size,
            )
        )

    @staticmethod
    def _path_sort_key(path: Path) -> datetime:
        parsed = parse_recorded_at(path)
        if parsed is not None:
            return parsed
        try:
            return datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            return datetime.min

    @staticmethod
    def _row_to_recording(row: sqlite3.Row) -> Recording:
        return Recording(
            id=row["id"],
            file_path=row["file_path"],
            width=row["width"],
            height=row["height"],
            duration_ms=row["duration_ms"],
            file_size_bytes=row["file_size_bytes"],
            recorded_at=row["recorded_at"],
        )


class SqliteLogRepository(LogRepository, SqliteRepositoryBase):
    """Persistência dos logs da aplicação no SQLite."""

    _write_lock = threading.Lock()

    def add(self, entry: LogEntry) -> int:
        logged_at = entry.logged_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._write_lock:
            try:
                with connect() as connection:
                    cursor = connection.execute(
                        """
                        INSERT INTO app_logs (
                            logged_at, level, logger_name, message, exception_text
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            logged_at,
                            entry.level,
                            entry.logger_name,
                            entry.message,
                            entry.exception_text,
                        ),
                    )
                    log_id = int(cursor.lastrowid)
            except sqlite3.Error as exc:
                raise PersistenceError(str(exc)) from exc
        return log_id

    def list_filtered(
        self,
        *,
        day: date | None,
        text: str | None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[LogEntry]:
        where_clause, params = self._filter_clause(day, text)
        paging = ""
        query_params: tuple[str | int, ...] = params
        if limit is not None:
            paging = "LIMIT ? OFFSET ?"
            query_params = (*params, limit, offset)
        query = f"""
            SELECT * FROM app_logs
            {where_clause}
            ORDER BY id DESC
            {paging}
        """
        try:
            rows = self.fetch_all(query, query_params)
        except sqlite3.Error:
            _logger.exception("Falha ao listar logs filtrados.")
            raise
        return [self._row_to_log_entry(row) for row in rows]

    def count_filtered(
        self,
        *,
        day: date | None,
        text: str | None,
    ) -> int:
        where_clause, params = self._filter_clause(day, text)
        query = f"SELECT COUNT(*) AS total FROM app_logs {where_clause}"
        try:
            row = self.fetch_one(query, params)
        except sqlite3.Error:
            _logger.exception("Falha ao contar logs filtrados.")
            raise
        return int(row["total"]) if row else 0

    def count(self) -> int:
        try:
            row = self.fetch_one("SELECT COUNT(*) AS total FROM app_logs")
        except sqlite3.Error:
            _logger.exception("Falha ao contar logs.")
            raise
        return int(row["total"]) if row else 0

    def delete_older_than_days(self, days: int) -> int:
        if days < 1:
            return 0
        cutoff = (date.today() - timedelta(days=days - 1)).isoformat()
        try:
            with connect() as connection:
                cursor = connection.execute(
                    "DELETE FROM app_logs WHERE date(logged_at) < date(?)",
                    (cutoff,),
                )
                deleted = cursor.rowcount
        except sqlite3.Error as exc:
            _logger.exception("Falha ao remover logs anteriores a %s dias.", days)
            raise PersistenceError(str(exc)) from exc
        if deleted > 0:
            _logger.info(
                "Retenção de logs: %s registro(s) removido(s) (>%s dias).",
                deleted,
                days,
            )
        return int(deleted)

    def delete_all(self) -> int:
        try:
            with connect() as connection:
                cursor = connection.execute("DELETE FROM app_logs")
                deleted = cursor.rowcount
        except sqlite3.Error as exc:
            _logger.exception("Falha ao remover todos os logs.")
            raise PersistenceError(str(exc)) from exc
        if deleted > 0:
            _logger.info("Todos os logs foram removidos (%s registro(s)).", deleted)
        return int(deleted)

    @staticmethod
    def _escape_like(value: str) -> str:
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    @staticmethod
    def _filter_clause(
        day: date | None,
        text: str | None,
    ) -> tuple[str, tuple[str, ...]]:
        clauses: list[str] = []
        params: list[str] = []
        if day is not None:
            clauses.append("date(logged_at) = date(?)")
            params.append(day.isoformat())
        normalized = (text or "").strip()
        if normalized:
            pattern = f"%{SqliteLogRepository._escape_like(normalized.lower())}%"
            clauses.append(
                "("
                "LOWER(message) LIKE ? ESCAPE '\\' OR "
                "LOWER(logger_name) LIKE ? ESCAPE '\\' OR "
                "LOWER(level) LIKE ? ESCAPE '\\' OR "
                "LOWER(COALESCE(exception_text, '')) LIKE ? ESCAPE '\\'"
                ")"
            )
            params.extend([pattern, pattern, pattern, pattern])
        if not clauses:
            return "", ()
        return f"WHERE {' AND '.join(clauses)}", tuple(params)

    @staticmethod
    def _row_to_log_entry(row: sqlite3.Row) -> LogEntry:
        return LogEntry(
            id=row["id"],
            logged_at=row["logged_at"],
            level=row["level"],
            logger_name=row["logger_name"],
            message=row["message"],
            exception_text=row["exception_text"],
        )


class SqliteYoloRepository(YoloRepository, SqliteRepositoryBase):
    """Persistência de datasets YOLO (classes, imagens e anotações)."""

    def create_dataset(self, name: str) -> int:
        created_at = datetime.now().isoformat(timespec="seconds")
        try:
            with connect() as connection:
                cursor = connection.execute(
                    "INSERT INTO yolo_datasets (name, created_at) VALUES (?, ?)",
                    (name, created_at),
                )
                dataset_id = int(cursor.lastrowid)
        except sqlite3.Error as exc:
            _logger.exception("Falha ao criar dataset YOLO %s.", name)
            raise PersistenceError(str(exc)) from exc
        return dataset_id

    def list_datasets(self) -> list[YoloDataset]:
        try:
            rows = self.fetch_all("SELECT * FROM yolo_datasets ORDER BY id DESC")
        except sqlite3.Error:
            _logger.exception("Falha ao listar datasets YOLO.")
            raise
        return [self._row_to_dataset(row) for row in rows]

    def get_dataset(self, dataset_id: int) -> YoloDataset | None:
        try:
            row = self.fetch_one(
                "SELECT * FROM yolo_datasets WHERE id = ?", (dataset_id,)
            )
        except sqlite3.Error:
            _logger.exception("Falha ao buscar dataset YOLO id=%s.", dataset_id)
            raise
        return self._row_to_dataset(row) if row else None

    def rename_dataset(self, dataset_id: int, name: str) -> None:
        try:
            with connect() as connection:
                connection.execute(
                    "UPDATE yolo_datasets SET name = ? WHERE id = ?",
                    (name, dataset_id),
                )
        except sqlite3.Error as exc:
            _logger.exception("Falha ao renomear dataset YOLO id=%s.", dataset_id)
            raise PersistenceError(str(exc)) from exc

    def delete_dataset(self, dataset_id: int) -> None:
        try:
            with connect() as connection:
                connection.execute(
                    "DELETE FROM yolo_datasets WHERE id = ?", (dataset_id,)
                )
        except sqlite3.Error as exc:
            _logger.exception("Falha ao excluir dataset YOLO id=%s.", dataset_id)
            raise PersistenceError(str(exc)) from exc

    def add_class(
        self, dataset_id: int, name: str, color: str, order_index: int
    ) -> int:
        try:
            with connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO yolo_classes (dataset_id, name, color, order_index)
                    VALUES (?, ?, ?, ?)
                    """,
                    (dataset_id, name, color, order_index),
                )
                class_id = int(cursor.lastrowid)
        except sqlite3.Error as exc:
            _logger.exception(
                "Falha ao criar classe YOLO em dataset id=%s.", dataset_id
            )
            raise PersistenceError(str(exc)) from exc
        return class_id

    def list_classes(self, dataset_id: int) -> list[YoloClass]:
        try:
            rows = self.fetch_all(
                """
                SELECT * FROM yolo_classes
                WHERE dataset_id = ?
                ORDER BY order_index ASC, id ASC
                """,
                (dataset_id,),
            )
        except sqlite3.Error:
            _logger.exception("Falha ao listar classes do dataset id=%s.", dataset_id)
            raise
        return [self._row_to_class(row) for row in rows]

    def update_class(self, class_id: int, *, name: str, color: str) -> None:
        try:
            with connect() as connection:
                connection.execute(
                    "UPDATE yolo_classes SET name = ?, color = ? WHERE id = ?",
                    (name, color, class_id),
                )
        except sqlite3.Error as exc:
            _logger.exception("Falha ao atualizar classe YOLO id=%s.", class_id)
            raise PersistenceError(str(exc)) from exc

    def delete_class(self, class_id: int) -> None:
        try:
            with connect() as connection:
                connection.execute("DELETE FROM yolo_classes WHERE id = ?", (class_id,))
        except sqlite3.Error as exc:
            _logger.exception("Falha ao excluir classe YOLO id=%s.", class_id)
            raise PersistenceError(str(exc)) from exc

    def add_image(self, dataset_id: int, capture_id: int) -> int | None:
        try:
            with connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO yolo_dataset_images (dataset_id, capture_id)
                    VALUES (?, ?)
                    """,
                    (dataset_id, capture_id),
                )
                if cursor.rowcount == 0:
                    return None
                return int(cursor.lastrowid)
        except sqlite3.Error as exc:
            _logger.exception(
                "Falha ao vincular captura id=%s ao dataset id=%s.",
                capture_id,
                dataset_id,
            )
            raise PersistenceError(str(exc)) from exc

    def list_images(self, dataset_id: int) -> list[YoloDatasetImage]:
        try:
            rows = self.fetch_all(
                """
                SELECT di.id AS id, di.dataset_id AS dataset_id,
                       di.capture_id AS capture_id, c.file_path AS file_path,
                       c.width AS width, c.height AS height
                FROM yolo_dataset_images di
                JOIN captures c ON c.id = di.capture_id
                WHERE di.dataset_id = ?
                ORDER BY di.id DESC
                """,
                (dataset_id,),
            )
        except sqlite3.Error:
            _logger.exception("Falha ao listar imagens do dataset id=%s.", dataset_id)
            raise
        return [self._row_to_image(row) for row in rows]

    def remove_image(self, image_id: int) -> None:
        try:
            with connect() as connection:
                connection.execute(
                    "DELETE FROM yolo_dataset_images WHERE id = ?", (image_id,)
                )
        except sqlite3.Error as exc:
            _logger.exception("Falha ao remover imagem do dataset id=%s.", image_id)
            raise PersistenceError(str(exc)) from exc

    def count_annotations(self, image_id: int) -> int:
        try:
            row = self.fetch_one(
                "SELECT COUNT(*) AS total FROM yolo_annotations WHERE image_id = ?",
                (image_id,),
            )
        except sqlite3.Error:
            _logger.exception("Falha ao contar anotações da imagem id=%s.", image_id)
            raise
        return int(row["total"]) if row else 0

    def classes_by_image(self, dataset_id: int) -> dict[int, list[str]]:
        try:
            rows = self.fetch_all(
                """
                SELECT di.id AS image_id, cl.name AS class_name
                FROM yolo_dataset_images di
                JOIN yolo_annotations a ON a.image_id = di.id
                JOIN yolo_classes cl ON cl.id = a.class_id
                WHERE di.dataset_id = ?
                GROUP BY di.id, cl.id
                ORDER BY di.id ASC, cl.order_index ASC, cl.id ASC
                """,
                (dataset_id,),
            )
        except sqlite3.Error:
            _logger.exception(
                "Falha ao buscar classes por imagem do dataset id=%s.",
                dataset_id,
            )
            raise
        result: dict[int, list[str]] = {}
        for row in rows:
            result.setdefault(int(row["image_id"]), []).append(row["class_name"])
        return result

    def annotation_count_by_class(self, dataset_id: int) -> dict[int, int]:
        try:
            rows = self.fetch_all(
                """
                SELECT a.class_id AS class_id, COUNT(*) AS total
                FROM yolo_annotations a
                JOIN yolo_classes cl ON cl.id = a.class_id
                WHERE cl.dataset_id = ?
                GROUP BY a.class_id
                """,
                (dataset_id,),
            )
        except sqlite3.Error:
            _logger.exception(
                "Falha ao contar anotações por classe do dataset id=%s.",
                dataset_id,
            )
            raise
        return {int(row["class_id"]): int(row["total"]) for row in rows}

    def list_annotations(self, image_id: int) -> list[YoloAnnotation]:
        try:
            rows = self.fetch_all(
                "SELECT * FROM yolo_annotations WHERE image_id = ? ORDER BY id ASC",
                (image_id,),
            )
        except sqlite3.Error:
            _logger.exception("Falha ao listar anotações da imagem id=%s.", image_id)
            raise
        return [self._row_to_annotation(row) for row in rows]

    def set_annotations(self, image_id: int, annotations: list[YoloAnnotation]) -> None:
        try:
            with connect() as connection:
                connection.execute(
                    "DELETE FROM yolo_annotations WHERE image_id = ?", (image_id,)
                )
                connection.executemany(
                    """
                    INSERT INTO yolo_annotations (image_id, class_id, kind, points)
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        (
                            image_id,
                            annotation.class_id,
                            annotation.kind,
                            json.dumps([[x, y] for x, y in annotation.points]),
                        )
                        for annotation in annotations
                    ],
                )
        except sqlite3.Error as exc:
            _logger.exception("Falha ao salvar anotações da imagem id=%s.", image_id)
            raise PersistenceError(str(exc)) from exc

    @staticmethod
    def _row_to_dataset(row: sqlite3.Row) -> YoloDataset:
        return YoloDataset(
            id=row["id"],
            name=row["name"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_class(row: sqlite3.Row) -> YoloClass:
        return YoloClass(
            id=row["id"],
            dataset_id=row["dataset_id"],
            name=row["name"],
            color=row["color"],
            order_index=row["order_index"],
        )

    @staticmethod
    def _row_to_image(row: sqlite3.Row) -> YoloDatasetImage:
        return YoloDatasetImage(
            id=row["id"],
            dataset_id=row["dataset_id"],
            capture_id=row["capture_id"],
            file_path=row["file_path"],
            width=row["width"],
            height=row["height"],
        )

    @staticmethod
    def _row_to_annotation(row: sqlite3.Row) -> YoloAnnotation:
        raw_points = json.loads(row["points"]) if row["points"] else []
        points = [(float(point[0]), float(point[1])) for point in raw_points]
        return YoloAnnotation(
            id=row["id"],
            image_id=row["image_id"],
            class_id=row["class_id"],
            kind=row["kind"],
            points=points,
        )

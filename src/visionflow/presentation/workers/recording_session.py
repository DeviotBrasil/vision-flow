"""Sessão de gravação de vídeo (estado, timing e writer) para o worker de câmera."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from visionflow.domain.contracts.video_recorder import VideoRecorderPort

_logger = logging.getLogger(__name__)

_DEFAULT_RECORDING_FPS = 30.0
_RECORDING_FPS_MIN = 1.0
_RECORDING_FPS_MAX = 60.0
_RECORDING_MEASURE_MIN_FRAMES = 8
_RECORDING_MEASURE_MIN_SEC = 0.4
_RECORDING_FPS_EMA_ALPHA = 0.2
_MAX_DUPLICATE_FRAMES = 8


class RecordingPhase(StrEnum):
    IDLE = "idle"
    ARMED = "armed"
    WARMING = "warming"
    RECORDING = "recording"


@dataclass(frozen=True)
class RecordingFrameResult:
    """Efeitos de processar um frame de preview durante gravação."""

    started_path: str | None = None
    failed_message: str | None = None


@dataclass(frozen=True)
class RecordingFinalizeResult:
    """Resultado de finalizar ou cancelar uma sessão de gravação."""

    kind: Literal["stopped", "failed", "none"]
    path: str | None = None
    message: str | None = None


class RecordingSession:
    """Gerencia warmup, FPS medido e escrita de frames no recorder."""

    def __init__(
        self,
        recorder_factory: Callable[[], VideoRecorderPort],
    ) -> None:
        self._recorder_factory = recorder_factory
        self._recorder: VideoRecorderPort | None = None
        self._phase = RecordingPhase.IDLE
        self._armed_path: str | None = None
        self._warmup_times: list[float] = []
        self._warmup_last_frame: object | None = None
        self._recording_fps = _DEFAULT_RECORDING_FPS
        self._last_frame: object | None = None
        self._last_write_time = 0.0
        self._last_sample_time = 0.0

    @property
    def phase(self) -> RecordingPhase:
        return self._phase

    @property
    def is_active(self) -> bool:
        return self._phase in (
            RecordingPhase.ARMED,
            RecordingPhase.WARMING,
            RecordingPhase.RECORDING,
        )

    def arm(self, output_path: str) -> None:
        self.reset()
        self._armed_path = output_path
        self._phase = RecordingPhase.ARMED
        _logger.info("Gravação armada: %s", output_path)

    def reset(self) -> None:
        self._phase = RecordingPhase.IDLE
        self._armed_path = None
        self._warmup_times.clear()
        self._warmup_last_frame = None
        self._recording_fps = _DEFAULT_RECORDING_FPS
        self._last_frame = None
        self._last_write_time = 0.0
        self._last_sample_time = 0.0

    def handle_frame(self, frame: object) -> RecordingFrameResult:
        """Processa um frame de preview."""
        if self._phase == RecordingPhase.IDLE:
            return RecordingFrameResult()
        if not hasattr(frame, "shape"):
            return RecordingFrameResult()

        if self._phase in (RecordingPhase.ARMED, RecordingPhase.WARMING):
            return self._handle_warmup_frame(frame)
        if self._phase == RecordingPhase.RECORDING:
            self._write_active_frame(frame)
        return RecordingFrameResult()

    def finalize(self, *, empty_message: str | None = None) -> RecordingFinalizeResult:
        if self._phase in (RecordingPhase.ARMED, RecordingPhase.WARMING):
            path = self._armed_path
            if path is not None and len(self._warmup_times) >= 2:
                frame = self._warmup_last_frame
                if frame is not None:
                    started, error = self._start_writer(frame, path)
                    if error is not None:
                        return RecordingFinalizeResult("failed", message=error)
                    if started:
                        return self._stop_writer(empty_message=empty_message)
            self.reset()
            if empty_message is not None:
                return RecordingFinalizeResult("failed", message=empty_message)
            return RecordingFinalizeResult("none")

        if self._phase == RecordingPhase.RECORDING:
            return self._stop_writer(empty_message=empty_message)

        self.reset()
        return RecordingFinalizeResult("none")

    def _ensure_recorder(self) -> VideoRecorderPort:
        if self._recorder is None:
            self._recorder = self._recorder_factory()
        return self._recorder

    def _handle_warmup_frame(self, frame: object) -> RecordingFrameResult:
        self._phase = RecordingPhase.WARMING
        self._warmup_last_frame = frame
        self._warmup_times.append(time.perf_counter())
        if not self._warmup_ready():
            return RecordingFrameResult()
        path = self._armed_path
        if path is None:
            return RecordingFrameResult()
        started, error = self._start_writer(frame, path)
        if error is not None:
            return RecordingFrameResult(failed_message=error)
        if started:
            return RecordingFrameResult(started_path=path)
        return RecordingFrameResult()

    def _warmup_ready(self) -> bool:
        if len(self._warmup_times) < _RECORDING_MEASURE_MIN_FRAMES:
            return False
        elapsed = self._warmup_times[-1] - self._warmup_times[0]
        return elapsed >= _RECORDING_MEASURE_MIN_SEC

    def _fps_from_times(self, times: list[float]) -> float:
        if len(times) < 2:
            return _DEFAULT_RECORDING_FPS
        elapsed = times[-1] - times[0]
        if elapsed <= 0:
            return _DEFAULT_RECORDING_FPS
        fps = (len(times) - 1) / elapsed
        return max(_RECORDING_FPS_MIN, min(fps, _RECORDING_FPS_MAX))

    def _start_writer(self, frame: object, path: str) -> tuple[bool, str | None]:
        fps = self._fps_from_times(self._warmup_times)
        height, width = frame.shape[:2]
        recorder = self._ensure_recorder()
        try:
            recorder.start(path, width, height, fps)
        except OSError as exc:
            _logger.warning("Falha ao iniciar gravação: %s", exc)
            self.reset()
            return False, str(exc)

        self._armed_path = None
        self._phase = RecordingPhase.RECORDING
        self._recording_fps = fps
        now = time.perf_counter()
        self._last_write_time = now
        self._last_sample_time = now
        self._last_frame = frame
        self._warmup_times.clear()
        _logger.info("FPS medido para gravação: %.2f.", fps)
        recorder.write_frame(frame)
        return True, None

    def _write_active_frame(self, frame: object) -> None:
        recorder = self._recorder
        if recorder is None or not recorder.is_active:
            return
        now = time.perf_counter()
        last_frame = self._last_frame
        last_write = self._last_write_time
        if last_frame is not None and last_write > 0 and self._recording_fps > 0:
            elapsed = now - last_write
            expected = 1.0 / self._recording_fps
            duplicates = min(
                _MAX_DUPLICATE_FRAMES,
                max(0, round(elapsed / expected) - 1),
            )
            for _ in range(duplicates):
                recorder.write_frame(last_frame)
        recorder.write_frame(frame)
        self._update_fps(now)
        self._last_frame = frame
        self._last_write_time = now

    def _update_fps(self, now: float) -> None:
        last_sample = self._last_sample_time
        if last_sample > 0:
            interval = now - last_sample
            if interval > 0:
                instant_fps = 1.0 / interval
                blended = (
                    1.0 - _RECORDING_FPS_EMA_ALPHA
                ) * self._recording_fps + _RECORDING_FPS_EMA_ALPHA * instant_fps
                self._recording_fps = max(
                    _RECORDING_FPS_MIN, min(blended, _RECORDING_FPS_MAX)
                )
        self._last_sample_time = now

    def _stop_writer(self, *, empty_message: str | None) -> RecordingFinalizeResult:
        recorder = self._recorder
        self._warmup_times.clear()
        if recorder is None or not recorder.is_active:
            self.reset()
            return RecordingFinalizeResult("none")

        path = recorder.stop()
        self.reset()
        if path is None:
            if empty_message is not None:
                return RecordingFinalizeResult("failed", message=empty_message)
            return RecordingFinalizeResult("none")
        return RecordingFinalizeResult("stopped", path=path)

"""Gravação de vídeo via OpenCV ``VideoWriter`` (MP4).

Usa o FourCC ``mp4v`` (MPEG-4 Part 2). É amplamente suportado pelo OpenCV no
Windows, mas players web e alguns editores preferem H.264 (``avc1``); troca de
codec exigiria validar disponibilidade no runtime do operador.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from visionflow.domain.contracts.video_recorder import VideoRecorderPort

_logger = logging.getLogger(__name__)

_DEFAULT_FPS = 30.0
_MP4_FOURCC = cv2.VideoWriter_fourcc(*"mp4v")


class OpenCvVideoRecorder(VideoRecorderPort):
    """Encapsula ``cv2.VideoWriter`` para frames RGB8/mono do preview."""

    def __init__(self) -> None:
        self._writer: cv2.VideoWriter | None = None
        self._path: Path | None = None
        self._width = 0
        self._height = 0
        self._frame_count = 0

    @property
    def is_active(self) -> bool:
        return self._writer is not None

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def start(self, path: str | Path, width: int, height: int, fps: float) -> None:
        """Abre o arquivo de saída e prepara o writer."""
        if self._writer is not None:
            raise RuntimeError("Gravação já está ativa.")

        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        safe_fps = fps if fps > 0 else _DEFAULT_FPS
        writer = cv2.VideoWriter(
            str(output),
            _MP4_FOURCC,
            safe_fps,
            (width, height),
        )
        if not writer.isOpened():
            writer.release()
            raise OSError(f"Falha ao abrir VideoWriter em {output}.")

        self._writer = writer
        self._path = output
        self._width = width
        self._height = height
        self._frame_count = 0
        _logger.info(
            "Gravação iniciada: %s (%dx%d @ %.1f fps).",
            output,
            width,
            height,
            safe_fps,
        )

    def write_frame(self, frame: np.ndarray) -> bool:
        """Grava um frame RGB8 ou mono. Retorna ``False`` se dimensão divergir."""
        writer = self._writer
        if writer is None:
            return False

        height, width = frame.shape[:2]
        if width != self._width or height != self._height:
            _logger.warning(
                "Frame ignorado na gravação: esperado %dx%d, recebido %dx%d.",
                self._width,
                self._height,
                width,
                height,
            )
            return False

        bgr = _rgb_to_bgr(frame)
        writer.write(bgr)
        self._frame_count += 1
        return True

    def stop(self) -> str | None:
        """Finaliza a gravação e devolve o caminho, ou ``None`` se vazia."""
        writer = self._writer
        path = self._path
        frame_count = self._frame_count

        self._writer = None
        self._path = None
        self._width = 0
        self._height = 0
        self._frame_count = 0

        if writer is None or path is None:
            return None

        writer.release()

        if frame_count == 0:
            path.unlink(missing_ok=True)
            _logger.info("Gravação cancelada (nenhum frame): %s.", path)
            return None

        _logger.info("Gravação finalizada: %s (%d frame(s)).", path, frame_count)
        return str(path)


def _rgb_to_bgr(frame: np.ndarray) -> np.ndarray:
    """Converte frame RGB8 ou mono em BGR 3 canais para o VideoWriter."""
    if frame.ndim == 2:
        return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

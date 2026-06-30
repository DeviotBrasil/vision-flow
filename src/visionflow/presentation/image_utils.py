"""Conversões de imagem para a camada de UI (``numpy.ndarray`` → Qt).

Mantém a dependência de ``cv2``/Qt fora das camadas de câmera e persistência.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPainterPath, QPixmap


def ndarray_to_qimage(frame: np.ndarray) -> QImage:
    """Converte um frame (Mono8 ou RGB8) em ``QImage`` independente do buffer.

    O ``QImage`` resultante é copiado, de modo que não compartilha memória com
    o ``ndarray`` de origem (seguro para uso após o frame ser liberado).
    """
    array = np.ascontiguousarray(frame)
    height = array.shape[0]
    width = array.shape[1]

    if array.ndim == 2:
        image = QImage(
            array.data, width, height, width, QImage.Format.Format_Grayscale8
        )
    elif array.ndim == 3 and array.shape[2] == 3:
        image = QImage(
            array.data, width, height, 3 * width, QImage.Format.Format_RGB888
        )
    elif array.ndim == 3 and array.shape[2] == 4:
        image = QImage(
            array.data, width, height, 4 * width, QImage.Format.Format_RGBA8888
        )
    else:
        raise ValueError(f"Formato de frame não suportado: shape={array.shape}")

    return image.copy()


def ndarray_to_qpixmap(frame: np.ndarray) -> QPixmap:
    """Converte um frame em ``QPixmap`` pronto para exibição."""
    return QPixmap.fromImage(ndarray_to_qimage(frame))


def qimage_to_ndarray(image: QImage) -> np.ndarray:
    """Converte ``QImage`` em ``ndarray`` (Mono8, RGB8 ou RGBA8)."""
    if image.isNull():
        raise ValueError("QImage nula.")

    if image.format() == QImage.Format.Format_Grayscale8:
        gray = image.convertToFormat(QImage.Format.Format_Grayscale8)
        g_width = gray.width()
        g_height = gray.height()
        g_line = gray.bytesPerLine()
        g_buffer = gray.constBits()
        g_array = np.frombuffer(g_buffer, dtype=np.uint8).reshape(g_height, g_line)
        return g_array[:, :g_width].copy()

    if image.hasAlphaChannel():
        rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
        r_width = rgba.width()
        r_height = rgba.height()
        r_line = rgba.bytesPerLine()
        r_buffer = rgba.constBits()
        r_array = np.frombuffer(r_buffer, dtype=np.uint8).reshape(r_height, r_line)
        return r_array[:, : r_width * 4].reshape(r_height, r_width, 4).copy()

    converted = image.convertToFormat(QImage.Format.Format_RGB888)
    width = converted.width()
    height = converted.height()
    bytes_per_line = converted.bytesPerLine()
    buffer = converted.constBits()
    array = np.frombuffer(buffer, dtype=np.uint8).reshape(height, bytes_per_line)
    return array[:, : width * 3].reshape(height, width, 3).copy()


def crop_qimage(image: QImage, x: int, y: int, width: int, height: int) -> QImage:
    """Recorta uma região retangular da imagem com validação de limites."""
    if image.isNull():
        raise ValueError("QImage nula.")
    img_w = image.width()
    img_h = image.height()
    x = max(0, min(x, img_w - 1))
    y = max(0, min(y, img_h - 1))
    width = max(1, min(width, img_w - x))
    height = max(1, min(height, img_h - y))
    return image.copy(x, y, width, height)


def resize_qimage(
    image: QImage,
    width: int,
    height: int,
    *,
    keep_aspect: bool = True,
) -> QImage:
    """Redimensiona a imagem; opcionalmente preserva a proporção."""
    if image.isNull():
        raise ValueError("QImage nula.")
    width = max(1, width)
    height = max(1, height)
    mode = (
        Qt.AspectRatioMode.KeepAspectRatio
        if keep_aspect
        else Qt.AspectRatioMode.IgnoreAspectRatio
    )
    return image.scaled(
        width,
        height,
        mode,
        Qt.TransformationMode.SmoothTransformation,
    )


def rounded_pixmap(
    source: QPixmap,
    *,
    width: int,
    height: int,
    radius: int,
) -> QPixmap:
    """Escala, recorta e aplica cantos arredondados a um pixmap."""
    target = QPixmap(width, height)
    target.fill(Qt.GlobalColor.transparent)
    if source.isNull():
        return target

    scaled = source.scaled(
        width,
        height,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    crop_x = max((scaled.width() - width) // 2, 0)
    crop_y = max((scaled.height() - height) // 2, 0)
    cropped = scaled.copy(crop_x, crop_y, width, height)

    painter = QPainter(target)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    clip = QPainterPath()
    clip.addRoundedRect(0, 0, width, height, radius, radius)
    painter.setClipPath(clip)
    painter.drawPixmap(0, 0, cropped)
    painter.end()
    return target

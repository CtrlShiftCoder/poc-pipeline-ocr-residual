"""Preprocesamiento de imágenes de boletas (OpenCV headless)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def load_image(path: str | Path) -> np.ndarray:
    """Carga imagen BGR; lanza FileNotFoundError si falla."""
    path = Path(path)
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"No se pudo leer imagen: {path}")
    return img


def to_grayscale(img: np.ndarray) -> np.ndarray:
    if len(img.shape) == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def deskew(gray: np.ndarray) -> np.ndarray:
    """Corrige inclinación leve vía momentos de imagen binaria."""
    thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thr > 0))
    if coords.size == 0:
        return gray
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    if abs(angle) < 0.5 or abs(angle) > 15:
        return gray
    h, w = gray.shape[:2]
    m = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(
        gray, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )


def enhance_contrast(gray: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def preprocess_for_ocr(path: str | Path) -> np.ndarray:
    """Pipeline: carga → gris → deskew → CLAHE → denoise leve."""
    img = load_image(path)
    gray = to_grayscale(img)
    gray = deskew(gray)
    gray = enhance_contrast(gray)
    gray = cv2.fastNlMeansDenoising(gray, None, 8, 7, 21)
    return gray


def preprocess_bytes(data: bytes) -> np.ndarray:
    """Preprocesa desde bytes (descarga Blob en memoria)."""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Bytes no decodificables como imagen")
    gray = to_grayscale(img)
    gray = deskew(gray)
    gray = enhance_contrast(gray)
    return cv2.fastNlMeansDenoising(gray, None, 8, 7, 21)

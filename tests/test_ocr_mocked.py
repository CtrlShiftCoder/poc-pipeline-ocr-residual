"""OCR con engine mock — no descarga modelos Paddle."""

import numpy as np

from residual_ocr.ocr import run_ocr
from residual_ocr.parse_fields import parse_ocr_text


class FakeEngine:
    def ocr(self, img, cls=True):  # noqa: ARG002
        return [
            [
                [[[0, 0], [1, 0], [1, 1], [0, 1]], ("RUT 12.345.678-5", 0.97)],
                [[[0, 0], [1, 0], [1, 1], [0, 1]], ("Boleta N 10024568", 0.95)],
                [[[0, 0], [1, 0], [1, 1], [0, 1]], ("TOTAL $25.000", 0.93)],
                [[[0, 0], [1, 0], [1, 1], [0, 1]], ("Fecha 16/03/2026", 0.91)],
            ]
        ]


def test_run_ocr_with_mock(tmp_path):
    # imagen mínima válida para OpenCV
    import cv2

    path = tmp_path / "boleta.jpg"
    cv2.imwrite(str(path), np.zeros((64, 128, 3), dtype=np.uint8) + 255)
    result = run_ocr(image_path=str(path), engine_factory=FakeEngine)
    assert "12.345.678-5" in result.text
    assert result.confidence > 0.9
    fields = parse_ocr_text(result.text)
    assert fields.rut == "12345678-5"
    assert fields.boleta == "10024568"
    assert fields.monto == 25000

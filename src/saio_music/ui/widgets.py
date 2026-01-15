"""Custom widgets for the SaioMusic UI."""

from __future__ import annotations

import math

from PySide6 import QtCore, QtGui, QtWidgets


class KeyWheelWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(180, 180)
        self._colors = [
            "#5ad0ff",
            "#47b3ff",
            "#3b90ff",
            "#5e76ff",
            "#8a6bff",
            "#b366ff",
            "#d266ff",
            "#f35cb8",
            "#ff6b7a",
            "#ff8a5c",
            "#ffb74b",
            "#ffd84b",
        ]

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        size = min(self.width(), self.height())
        rect = QtCore.QRectF(6, 6, size - 12, size - 12)
        span = 360 / len(self._colors)
        start = 90
        painter.setPen(QtCore.Qt.NoPen)
        for index, color in enumerate(self._colors):
            painter.setBrush(QtGui.QColor(color))
            angle = start - (index * span)
            painter.drawPie(rect, int(angle * 16), int(-span * 16))

        inner_margin = rect.width() * 0.26
        inner = rect.adjusted(inner_margin, inner_margin, -inner_margin, -inner_margin)
        painter.setBrush(QtGui.QColor("#f3f6fb"))
        painter.drawEllipse(inner)


class WaveformWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(84)
        self._amplitudes = self._build_amplitudes()
        self._cue_positions = [0.04, 0.33, 0.41, 0.48, 0.56, 0.82]

    def _build_amplitudes(self) -> list[float]:
        values: list[float] = []
        for index in range(220):
            wave = math.sin(index / 8) + 0.55 * math.sin(index / 3.1)
            pulse = 0.2 * math.sin(index / 1.7)
            values.append(abs(wave + pulse))
        max_value = max(values) if values else 1.0
        return [value / max_value for value in values]

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        rect = self.rect().adjusted(6, 8, -6, -8)
        gradient = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, QtGui.QColor("#b6efff"))
        gradient.setColorAt(1.0, QtGui.QColor("#79c9ff"))
        painter.fillRect(rect, gradient)

        mid = rect.center().y()
        bar_color = QtGui.QColor("#1aa6ff")
        pen = QtGui.QPen(bar_color, 2)
        painter.setPen(pen)

        if self._amplitudes:
            step = rect.width() / len(self._amplitudes)
            for index, amp in enumerate(self._amplitudes):
                x = rect.left() + (index * step)
                height = amp * (rect.height() * 0.8)
                painter.drawLine(
                    QtCore.QPointF(x, mid - (height / 2)),
                    QtCore.QPointF(x, mid + (height / 2)),
                )

        cue_pen = QtGui.QPen(QtGui.QColor("#0d78c9"), 2)
        painter.setPen(cue_pen)
        for cue in self._cue_positions:
            x = rect.left() + (rect.width() * cue)
            painter.drawLine(
                QtCore.QPointF(x, rect.top()),
                QtCore.QPointF(x, rect.bottom()),
            )

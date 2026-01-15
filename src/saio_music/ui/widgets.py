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
    seekRequested = QtCore.Signal(float)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(84)
        self._samples = self._build_placeholder()
        self._playhead = 0.0

    def _build_placeholder(self) -> list[float]:
        values: list[float] = []
        for index in range(220):
            wave = math.sin(index / 8) + 0.55 * math.sin(index / 3.1)
            pulse = 0.2 * math.sin(index / 1.7)
            values.append(abs(wave + pulse))
        max_value = max(values) if values else 1.0
        return [value / max_value for value in values]

    def set_waveform(self, samples: list[float]) -> None:
        self._samples = samples if samples else self._build_placeholder()
        self.update()

    def set_playhead(self, ratio: float) -> None:
        self._playhead = max(0.0, min(1.0, ratio))
        self.update()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.LeftButton:
            rect = self.rect().adjusted(6, 8, -6, -8)
            if rect.width() > 0:
                ratio = (event.position().x() - rect.left()) / rect.width()
                ratio = max(0.0, min(1.0, ratio))
                self.seekRequested.emit(ratio)
        super().mousePressEvent(event)

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

        if self._samples:
            step = rect.width() / len(self._samples)
            for index, amp in enumerate(self._samples):
                x = rect.left() + (index * step)
                height = amp * (rect.height() * 0.85)
                painter.drawLine(
                    QtCore.QPointF(x, mid - (height / 2)),
                    QtCore.QPointF(x, mid + (height / 2)),
                )

        playhead_x = rect.left() + (rect.width() * self._playhead)
        painter.setPen(QtGui.QPen(QtGui.QColor("#0f7cc4"), 2))
        painter.drawLine(
            QtCore.QPointF(playhead_x, rect.top()),
            QtCore.QPointF(playhead_x, rect.bottom()),
        )

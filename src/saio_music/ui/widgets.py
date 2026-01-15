"""Custom widgets for the SaioMusic UI."""

from __future__ import annotations

import math

from PySide6 import QtCore, QtGui, QtWidgets


class KeyWheelWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(190, 190)
        self._colors = [
            "#f8d84b",
            "#f6b447",
            "#f38d4a",
            "#ef6b5f",
            "#e85f7c",
            "#d364a5",
            "#a76bd6",
            "#7c7be8",
            "#5a8fe9",
            "#52a9e6",
            "#57c7e8",
            "#6fe2e0",
        ]
        self._order = [12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        size = min(self.width(), self.height())
        rect = QtCore.QRectF(6, 6, size - 12, size - 12)
        span = 360 / 12
        start = 90
        painter.setPen(QtCore.Qt.NoPen)

        outer_margin = rect.width() * 0.06
        outer = rect.adjusted(outer_margin, outer_margin, -outer_margin, -outer_margin)
        inner_margin = rect.width() * 0.22
        inner = rect.adjusted(inner_margin, inner_margin, -inner_margin, -inner_margin)
        core_margin = rect.width() * 0.42
        core = rect.adjusted(core_margin, core_margin, -core_margin, -core_margin)

        for index, _key_num in enumerate(self._order):
            angle = start - (index * span)
            outer_color = QtGui.QColor(self._colors[index])
            inner_color = outer_color.lighter(115)
            painter.setBrush(outer_color)
            painter.drawPie(outer, int(angle * 16), int(-span * 16))
            painter.setBrush(inner_color)
            painter.drawPie(inner, int(angle * 16), int(-span * 16))

        painter.setBrush(QtGui.QColor("#f4f7fb"))
        painter.drawEllipse(core)

        self._draw_labels(painter, outer, inner, start, span)

    def _draw_labels(
        self,
        painter: QtGui.QPainter,
        outer: QtCore.QRectF,
        inner: QtCore.QRectF,
        start: float,
        span: float,
    ) -> None:
        painter.save()
        painter.setPen(QtGui.QPen(QtGui.QColor("#0f172a")))
        outer_radius = outer.width() * 0.5
        inner_radius = inner.width() * 0.5
        center = outer.center()
        outer_font = QtGui.QFont("Bahnschrift", 8, QtGui.QFont.Bold)
        inner_font = QtGui.QFont("Bahnschrift", 8)

        for index, key_num in enumerate(self._order):
            angle_deg = start - (index * span) - (span / 2)
            angle = math.radians(angle_deg)
            outer_pos = QtCore.QPointF(
                center.x() + math.cos(angle) * (outer_radius * 0.82),
                center.y() - math.sin(angle) * (outer_radius * 0.82),
            )
            inner_pos = QtCore.QPointF(
                center.x() + math.cos(angle) * (inner_radius * 0.82),
                center.y() - math.sin(angle) * (inner_radius * 0.82),
            )

            painter.setFont(outer_font)
            self._draw_text(painter, outer_pos, f"{key_num}B")
            painter.setFont(inner_font)
            self._draw_text(painter, inner_pos, f"{key_num}A")

        painter.restore()

    def _draw_text(
        self, painter: QtGui.QPainter, position: QtCore.QPointF, text: str
    ) -> None:
        metrics = QtGui.QFontMetrics(painter.font())
        rect = metrics.boundingRect(text)
        rect.moveCenter(QtCore.QPoint(int(position.x()), int(position.y())))
        painter.drawText(rect, QtCore.Qt.AlignCenter, text)


class WaveformWidget(QtWidgets.QWidget):
    seekRequested = QtCore.Signal(float)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(84)
        self._samples: list[float] = []
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
        self._samples = samples
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
        else:
            painter.setPen(QtGui.QPen(QtGui.QColor("#9fc5df"), 2))
            painter.drawLine(
                QtCore.QPointF(rect.left(), mid),
                QtCore.QPointF(rect.right(), mid),
            )

        playhead_x = rect.left() + (rect.width() * self._playhead)
        painter.setPen(QtGui.QPen(QtGui.QColor("#0f7cc4"), 2))
        painter.drawLine(
            QtCore.QPointF(playhead_x, rect.top()),
            QtCore.QPointF(playhead_x, rect.bottom()),
        )

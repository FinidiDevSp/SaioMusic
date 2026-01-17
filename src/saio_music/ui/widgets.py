"""Custom widgets for the SaioMusic UI."""

from __future__ import annotations

import math

from PySide6 import QtCore, QtGui, QtWidgets


class ActiveRowDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._phase = 0.0

    def set_phase(self, phase: float) -> None:
        self._phase = phase

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> None:
        active = bool(index.sibling(index.row(), 0).data(QtCore.Qt.UserRole + 1))
        if active:
            painter.save()
            painter.setBrush(QtGui.QColor("#e0f2fe"))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRect(option.rect)
            painter.restore()
            if index.column() == 0:
                self._draw_play_indicator(painter, option.rect)
        super().paint(painter, option, index)

    def _draw_play_indicator(self, painter: QtGui.QPainter, rect: QtCore.QRect) -> None:
        center = rect.center()
        base_x = center.x() - 6
        base_y = center.y() - 6
        colors = [QtGui.QColor("#0ea5e9"), QtGui.QColor("#38bdf8")]
        for idx in range(3):
            height = 4 + ((self._phase + idx) % 3) * 3
            x = base_x + (idx * 6)
            y = base_y + (12 - height)
            painter.save()
            painter.setBrush(colors[idx % len(colors)])
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRoundedRect(x, y, 3, height, 1, 1)
            painter.restore()


class KeyWheelWidget(QtWidgets.QWidget):
    keySelected = QtCore.Signal(str)
    keyToggled = QtCore.Signal(str, bool)
    clearRequested = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(190, 190)
        self.setMouseTracking(True)
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
        self._hover_key: str | None = None
        self._selected_keys: set[str] = set()
        self._active_key: str | None = None
        self._counts: dict[str, int] = {}

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

        if self._hover_key:
            self._draw_highlight(painter, outer, inner, start, span, self._hover_key)
        for key in self._selected_keys:
            self._draw_highlight(painter, outer, inner, start, span, key, alpha=0.22)
        if self._active_key:
            self._draw_active_marker(painter, outer, start, span, self._active_key)
        if self._is_in_core(self.mapFromGlobal(QtGui.QCursor.pos())):
            self._draw_core_highlight(painter, core)
        self._draw_labels(painter, outer, inner, start, span)
        self._draw_core_label(painter, core)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        hover_key = self._key_from_pos(event.position())
        if hover_key != self._hover_key:
            self._hover_key = hover_key
            if hover_key:
                count = self._counts.get(hover_key, 0)
                self.setToolTip(f"{hover_key} - {count} tracks")
            else:
                self.setToolTip("")
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:  # noqa: N802
        if self._hover_key is not None:
            self._hover_key = None
            self.setToolTip("")
            self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.LeftButton:
            if self._is_in_core(event.position()):
                self._selected_keys.clear()
                self.clearRequested.emit()
                self.update()
                super().mousePressEvent(event)
                return
            key = self._key_from_pos(event.position())
            if key:
                if key in self._selected_keys:
                    self._selected_keys.remove(key)
                    selected = False
                else:
                    self._selected_keys.add(key)
                    selected = True
                self.keyToggled.emit(key, selected)
                self.keySelected.emit(key)
                self.update()
        super().mousePressEvent(event)

    def set_selected_key(self, key: str | None) -> None:
        self._selected_keys = {key} if key else set()
        self.update()

    def set_selected_keys(self, keys: set[str]) -> None:
        self._selected_keys = set(keys)
        self.update()

    def set_active_key(self, key: str | None) -> None:
        self._active_key = key
        self.update()

    def set_counts(self, counts: dict[str, int]) -> None:
        self._counts = dict(counts)

    @classmethod
    def color_for_key(cls, key: str) -> QtGui.QColor | None:
        parsed = cls._parse_key(key)
        if parsed is None:
            return None
        number, _mode = parsed
        order = [12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        colors = [
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
        try:
            index = order.index(number)
        except ValueError:
            return None
        return QtGui.QColor(colors[index])

    @staticmethod
    def _parse_key(key: str) -> tuple[int, str] | None:
        key = key.strip().upper()
        if not key:
            return None
        if key[-1] not in {"A", "B"}:
            return None
        number_str = key[:-1]
        if not number_str.isdigit():
            return None
        number = int(number_str)
        if number < 1 or number > 12:
            return None
        return number, key[-1]

    def _geometry(self) -> tuple[QtCore.QPointF, float, float, float]:
        size = min(self.width(), self.height())
        rect = QtCore.QRectF(6, 6, size - 12, size - 12)
        outer_margin = rect.width() * 0.06
        inner_margin = rect.width() * 0.22
        core_margin = rect.width() * 0.42
        outer = rect.adjusted(outer_margin, outer_margin, -outer_margin, -outer_margin)
        inner = rect.adjusted(inner_margin, inner_margin, -inner_margin, -inner_margin)
        core = rect.adjusted(core_margin, core_margin, -core_margin, -core_margin)
        center = outer.center()
        return center, outer.width() * 0.5, inner.width() * 0.5, core.width() * 0.5

    def _is_in_core(self, pos: QtCore.QPointF) -> bool:
        center, _outer_radius, _inner_radius, core_radius = self._geometry()
        dx = pos.x() - center.x()
        dy = center.y() - pos.y()
        return math.hypot(dx, dy) <= core_radius

    def _key_from_pos(self, pos: QtCore.QPointF) -> str | None:
        center, outer_radius, inner_radius, core_radius = self._geometry()
        dx = pos.x() - center.x()
        dy = center.y() - pos.y()
        dist = math.hypot(dx, dy)
        if dist < core_radius or dist > outer_radius:
            return None
        angle = math.degrees(math.atan2(dy, dx))
        angle = (angle + 360) % 360
        start = 90
        span = 360 / 12
        idx = int(((start - angle) % 360) / span)
        key_number = self._order[idx]
        mode = "B" if dist >= inner_radius else "A"
        return f"{key_number}{mode}"

    def _draw_highlight(
        self,
        painter: QtGui.QPainter,
        outer: QtCore.QRectF,
        inner: QtCore.QRectF,
        start: float,
        span: float,
        key: str,
        alpha: float = 0.35,
    ) -> None:
        parsed = self._parse_key(key)
        if parsed is None:
            return
        key_number, mode = parsed
        try:
            index = self._order.index(key_number)
        except ValueError:
            return
        angle = start - (index * span)
        rect = outer if mode == "B" else inner
        painter.save()
        painter.setPen(QtCore.Qt.NoPen)
        color = QtGui.QColor("#ffffff")
        color.setAlphaF(alpha)
        painter.setBrush(color)
        painter.drawPie(rect, int(angle * 16), int(-span * 16))
        painter.restore()

    def _draw_active_marker(
        self,
        painter: QtGui.QPainter,
        outer: QtCore.QRectF,
        start: float,
        span: float,
        key: str,
    ) -> None:
        parsed = self._parse_key(key)
        if parsed is None:
            return
        key_number, _mode = parsed
        try:
            index = self._order.index(key_number)
        except ValueError:
            return
        angle_deg = start - (index * span) - (span / 2)
        angle = math.radians(angle_deg)
        center = outer.center()
        radius = outer.width() * 0.5
        outer_pos = QtCore.QPointF(
            center.x() + math.cos(angle) * (radius * 0.95),
            center.y() - math.sin(angle) * (radius * 0.95),
        )
        painter.save()
        painter.setBrush(QtGui.QColor("#0f7cc4"))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(outer_pos, 4, 4)
        painter.restore()

    def _draw_core_highlight(
        self, painter: QtGui.QPainter, core: QtCore.QRectF
    ) -> None:
        painter.save()
        painter.setPen(QtCore.Qt.NoPen)
        color = QtGui.QColor("#dbeafe")
        color.setAlphaF(0.8)
        painter.setBrush(color)
        painter.drawEllipse(core.adjusted(2, 2, -2, -2))
        painter.restore()

    def _draw_core_label(self, painter: QtGui.QPainter, core: QtCore.QRectF) -> None:
        painter.save()
        painter.setPen(QtGui.QPen(QtGui.QColor("#0f172a")))
        painter.setFont(QtGui.QFont("Bahnschrift", 9, QtGui.QFont.Bold))
        painter.drawText(core, QtCore.Qt.AlignCenter, "CF")
        painter.restore()

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
        painter.fillRect(rect, QtGui.QColor("#f8fbff"))

        mid = rect.center().y()
        bar_color = QtGui.QColor("#0ea5e9")
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

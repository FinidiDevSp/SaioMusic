"""Main window for the SaioMusic UI."""

from __future__ import annotations

import base64
from pathlib import Path

from mutagen import File as MutagenFile
from PySide6 import QtCore, QtGui, QtWidgets

from saio_music.ui.widgets import KeyWheelWidget, WaveformWidget


def _make_chip(text: str, bg: str, fg: str = "#0f172a") -> QtWidgets.QLabel:
    chip = QtWidgets.QLabel(text)
    chip.setAlignment(QtCore.Qt.AlignCenter)
    chip.setFixedHeight(24)
    chip.setStyleSheet(
        f"background: {bg}; color: {fg}; border-radius: 6px; padding: 2px 8px;"
    )
    return chip


def _make_cover_pixmap(color: str) -> QtGui.QPixmap:
    pixmap = QtGui.QPixmap(36, 36)
    pixmap.fill(QtGui.QColor(color))
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.setPen(QtGui.QColor("#ffffff"))
    painter.drawRect(4, 4, 28, 28)
    painter.end()
    return pixmap


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SaioMusic")
        self.resize(1280, 760)
        self.setMinimumSize(1100, 680)

        self.setFont(QtGui.QFont("Bahnschrift", 10))
        self.setStyleSheet(self._build_styles())

        self._tracks_table: QtWidgets.QTableWidget | None = None
        self._tracks_count: QtWidgets.QLabel | None = None

        central = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        root.addWidget(self._build_top_bar())

        content = QtWidgets.QHBoxLayout()
        content.setSpacing(12)
        content.addWidget(self._build_sidebar())
        content.addWidget(self._build_main_panel(), 1)
        root.addLayout(content, 1)

        self.setCentralWidget(central)

    def _build_top_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(14, 10, 14, 10)

        logo = QtWidgets.QHBoxLayout()
        logo_icon = QtWidgets.QLabel()
        logo_icon.setFixedSize(28, 28)
        logo_icon.setStyleSheet(
            "background: qradialgradient(cx:0.4, cy:0.4, radius:0.9, "
            "stop:0 #7fe7ff, stop:1 #1aa6ff); border-radius: 14px;"
        )
        logo_text = QtWidgets.QLabel("SaioMusic")
        logo_text.setStyleSheet("font-size: 16px; font-weight: 700;")
        logo.addWidget(logo_icon)
        logo.addSpacing(6)
        logo.addWidget(logo_text)

        tabs = QtWidgets.QHBoxLayout()
        tabs.setSpacing(10)
        tab_labels = ["COLLECTION", "EDIT TAGS", "PERSONALIZE"]
        for idx, label in enumerate(tab_labels):
            tab = QtWidgets.QPushButton(label)
            tab.setProperty("tab", "true")
            if idx == 0:
                tab.setProperty("active", "true")
            tabs.addWidget(tab)

        left = QtWidgets.QHBoxLayout()
        left.addLayout(logo)
        left.addSpacing(20)
        left.addLayout(tabs)
        left_widget = QtWidgets.QWidget()
        left_widget.setLayout(left)

        right = QtWidgets.QHBoxLayout()
        right.setSpacing(18)
        right.addWidget(QtWidgets.QLabel("TUTORIALS"))
        right.addWidget(QtWidgets.QLabel("SOFTWARE"))
        right_widget = QtWidgets.QWidget()
        right_widget.setLayout(right)

        layout.addWidget(left_widget)
        layout.addStretch(1)
        layout.addWidget(right_widget)
        bar.setObjectName("topBar")
        return bar

    def _build_sidebar(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QFrame()
        panel.setObjectName("sidePanel")
        panel.setFixedWidth(210)

        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(16)

        key_wheel = KeyWheelWidget()
        layout.addWidget(key_wheel, alignment=QtCore.Qt.AlignHCenter)

        add_tracks = QtWidgets.QPushButton("ADD TRACKS")
        add_tracks.setObjectName("primaryButton")
        add_tracks.clicked.connect(self._select_tracks_folder)
        layout.addWidget(add_tracks)

        section = QtWidgets.QVBoxLayout()
        section.setSpacing(10)

        def add_entry(text: str, badge: str | None = None) -> None:
            row = QtWidgets.QHBoxLayout()
            label = QtWidgets.QLabel(text)
            row.addWidget(label)
            row.addStretch(1)
            if badge is not None:
                badge_label = _make_chip(badge, "#e0f1ff", "#1174c2")
                badge_label.setFixedHeight(20)
                row.addWidget(badge_label)
            wrapper = QtWidgets.QWidget()
            wrapper.setLayout(row)
            section.addWidget(wrapper)

        add_entry("Analysis Queue", "Done")
        add_entry("My Collection")
        add_entry("Improve Tracks", "8")
        add_entry("Recently Added", "12")

        section_widget = QtWidgets.QWidget()
        section_widget.setLayout(section)
        layout.addWidget(section_widget)
        layout.addStretch(1)
        return panel

    def _build_main_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self._build_wave_panel())
        layout.addWidget(self._build_track_panel(), 1)
        return panel

    def _build_wave_panel(self) -> QtWidgets.QFrame:
        panel = QtWidgets.QFrame()
        panel.setObjectName("wavePanel")
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        top_row = QtWidgets.QHBoxLayout()
        controls = QtWidgets.QVBoxLayout()
        play = QtWidgets.QPushButton(">")
        play.setObjectName("playButton")
        controls.addWidget(play)
        controls.addSpacing(6)
        nav = QtWidgets.QHBoxLayout()
        prev_btn = QtWidgets.QToolButton()
        prev_btn.setText("<<")
        next_btn = QtWidgets.QToolButton()
        next_btn.setText(">>")
        nav.addWidget(prev_btn)
        nav.addWidget(next_btn)
        controls.addLayout(nav)
        controls_widget = QtWidgets.QWidget()
        controls_widget.setLayout(controls)

        waveform_column = QtWidgets.QVBoxLayout()
        cues = QtWidgets.QHBoxLayout()
        for idx in range(1, 7):
            cue = QtWidgets.QLabel(f"CUE {idx}")
            cue.setObjectName("cueLabel")
            cues.addWidget(cue)
        cues.addStretch(1)
        waveform_column.addLayout(cues)
        waveform_column.addWidget(WaveformWidget())
        waveform_widget = QtWidgets.QWidget()
        waveform_widget.setLayout(waveform_column)

        top_row.addWidget(controls_widget)
        top_row.addSpacing(10)
        top_row.addWidget(waveform_widget, 1)

        layout.addLayout(top_row)

        time_row = QtWidgets.QHBoxLayout()
        time_row.addStretch(1)
        time_row.addWidget(QtWidgets.QLabel("00:00 / 04:00"))
        layout.addLayout(time_row)

        title = QtWidgets.QLabel("Daft Punk - Digital Love")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        info_row = QtWidgets.QHBoxLayout()
        info_row.setSpacing(8)
        info_row.addWidget(QtWidgets.QLabel("KEY"))
        info_row.addWidget(_make_chip("11B", "#8fe4ff", "#075985"))
        info_row.addWidget(QtWidgets.QLabel("ENERGY"))
        info_row.addWidget(_make_chip("6", "#e2e8f0", "#0f172a"))
        info_row.addWidget(QtWidgets.QLabel("BPM"))
        info_row.addWidget(_make_chip("125", "#e2e8f0", "#0f172a"))
        info_row.addSpacing(10)
        info_row.addWidget(QtWidgets.QLabel("CUE POINTS"))
        info_row.addWidget(_make_chip("8", "#dbeafe", "#1d4ed8"))
        add_cue = QtWidgets.QPushButton("ADD CUE")
        add_cue.setObjectName("ghostButton")
        info_row.addWidget(add_cue)
        info_row.addStretch(1)
        info_row.addWidget(QtWidgets.QLabel("VIRTUAL PIANO"))
        layout.addLayout(info_row)

        return panel

    def _build_track_panel(self) -> QtWidgets.QWidget:
        wrapper = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        search_row = QtWidgets.QHBoxLayout()
        search = QtWidgets.QLineEdit()
        search.setPlaceholderText("Search your Analysis Queue")
        search.setObjectName("searchInput")
        search_row.addWidget(search, 1)
        search_row.addStretch(1)
        tracks_label = QtWidgets.QLabel("0 TRACKS")
        search_row.addWidget(tracks_label)
        layout.addLayout(search_row)

        table = QtWidgets.QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(
            [
                "COVER ART",
                "ARTIST",
                "TITLE",
                "TEMPO",
                "KEY RESULT",
                "ENERGY",
            ]
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setSortingEnabled(False)
        table.setObjectName("tracksTable")
        table.cellDoubleClicked.connect(self._select_track_row)

        table.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeToContents
        )
        table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(
            3, QtWidgets.QHeaderView.ResizeToContents
        )
        table.horizontalHeader().setSectionResizeMode(
            4, QtWidgets.QHeaderView.ResizeToContents
        )
        table.horizontalHeader().setSectionResizeMode(
            5, QtWidgets.QHeaderView.ResizeToContents
        )

        layout.addWidget(table, 1)
        self._tracks_table = table
        self._tracks_count = tracks_label
        return wrapper

    def _select_tracks_folder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select music folder")
        if not folder:
            return
        self._load_tracks(Path(folder))

    def _load_tracks(self, folder: Path) -> None:
        if self._tracks_table is None:
            return

        supported = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".aac"}
        files = sorted(
            [
                path
                for path in folder.rglob("*")
                if path.is_file() and path.suffix.lower() in supported
            ],
            key=lambda item: item.name.lower(),
        )

        self._tracks_table.setRowCount(0)
        for path in files:
            self._add_track_row(path)

        if self._tracks_count is not None:
            self._tracks_count.setText(f"{len(files)} TRACKS")

    def _select_track_row(self, row: int, column: int) -> None:
        if self._tracks_table is None:
            return
        self._tracks_table.clearSelection()
        self._tracks_table.selectRow(row)

    def _add_track_row(self, path: Path) -> None:
        if self._tracks_table is None:
            return

        tags = self._read_tags(path)
        row = self._tracks_table.rowCount()
        self._tracks_table.insertRow(row)

        cover_item = QtWidgets.QTableWidgetItem()
        cover_data = tags.get("cover_data")
        if not isinstance(cover_data, bytes):
            cover_data = None
        cover_icon = self._cover_icon(cover_data, row)
        cover_item.setIcon(cover_icon)
        self._tracks_table.setItem(row, 0, cover_item)

        artist = tags.get("artist") or path.stem
        title = tags.get("title") or path.stem
        tempo = tags.get("bpm") or ""
        key_result = tags.get("comments") or ""
        energy = "0"

        self._tracks_table.setItem(row, 1, QtWidgets.QTableWidgetItem(artist))
        self._tracks_table.setItem(row, 2, QtWidgets.QTableWidgetItem(title))
        self._tracks_table.setItem(row, 3, QtWidgets.QTableWidgetItem(tempo))

        key_item = QtWidgets.QTableWidgetItem(key_result)
        key_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self._tracks_table.setItem(row, 4, key_item)

        energy_item = QtWidgets.QTableWidgetItem(energy)
        energy_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self._tracks_table.setItem(row, 5, energy_item)

    def _read_tags(self, path: Path) -> dict[str, str | bytes | None]:
        info: dict[str, str | bytes | None] = {
            "artist": None,
            "title": None,
            "bpm": None,
            "comments": None,
            "cover_data": None,
        }

        try:
            audio = MutagenFile(path, easy=True)
        except Exception:
            audio = None
        if audio is not None:
            info["artist"] = self._first_tag(audio, ["artist"])
            info["title"] = self._first_tag(audio, ["title"])
            info["bpm"] = self._first_tag(audio, ["bpm", "tbpm"])
            info["comments"] = self._first_tag(audio, ["comment", "comments"])

        try:
            audio_full = MutagenFile(path)
        except Exception:
            audio_full = None
        if audio_full is not None:
            if not info["comments"]:
                info["comments"] = self._extract_comment(audio_full)
            info["cover_data"] = self._extract_cover(audio_full)
        return info

    def _first_tag(self, audio: object, keys: list[str]) -> str | None:
        for key in keys:
            value = getattr(audio, "tags", {}).get(key)
            if not value:
                continue
            if isinstance(value, list | tuple):
                return str(value[0])
            return str(value)
        return None

    def _extract_cover(self, audio: object) -> bytes | None:
        if audio is None:
            return None
        tags = getattr(audio, "tags", None)
        if tags is None:
            return None

        if hasattr(tags, "getall"):
            apic = tags.getall("APIC")
            if apic:
                return apic[0].data

        for key in list(tags.keys()):
            if str(key).startswith("APIC"):
                frame = tags[key]
                data = getattr(frame, "data", None)
                if isinstance(data, bytes | bytearray):
                    return bytes(data)

        pictures = getattr(audio, "pictures", None)
        if pictures:
            return pictures[0].data

        covr = tags.get("covr")
        if covr:
            try:
                return bytes(covr[0])
            except (IndexError, TypeError):
                return None

        for key in ("metadata_block_picture", "METADATA_BLOCK_PICTURE"):
            if key in tags:
                value = tags[key]
                if isinstance(value, list | tuple) and value:
                    return self._coerce_bytes(value[0])
                if isinstance(value, bytes):
                    return value

        return None

    def _extract_comment(self, audio: object) -> str | None:
        tags = getattr(audio, "tags", None)
        if tags is None:
            return None

        for key in ("comment", "comments", "COMMENT"):
            comment = self._coerce_text(tags.get(key))
            if comment:
                return comment

        comment = self._coerce_text(tags.get("\xa9cmt"))
        if comment:
            return comment

        for key in list(tags.keys()):
            if str(key).startswith("COMM"):
                frame = tags[key]
                text = getattr(frame, "text", None)
                if text:
                    return str(text[0])

        return None

    def _coerce_text(self, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, list | tuple):
            if not value:
                return None
            value = value[0]
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8", errors="ignore").strip() or None
            except Exception:
                return None
        return str(value).strip() or None

    def _coerce_bytes(self, value: object) -> bytes | None:
        if isinstance(value, bytes):
            return value
        if isinstance(value, bytearray):
            return bytes(value)
        if isinstance(value, str):
            try:
                return base64.b64decode(value)
            except Exception:
                return None
        return None

    def _cover_icon(self, cover_data: bytes | None, row: int) -> QtGui.QIcon:
        if cover_data:
            image = QtGui.QImage.fromData(cover_data)
            if not image.isNull():
                pixmap = QtGui.QPixmap.fromImage(image).scaled(
                    36, 36, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
                )
                return QtGui.QIcon(pixmap)

        fallback_colors = [
            "#e2e8f0",
            "#cbd5f5",
            "#fecaca",
            "#fbcfe8",
            "#bfdbfe",
            "#fde68a",
            "#bbf7d0",
            "#fecdd3",
            "#c7d2fe",
            "#bae6fd",
            "#fca5a5",
            "#ddd6fe",
        ]
        pixmap = _make_cover_pixmap(fallback_colors[row % len(fallback_colors)])
        return QtGui.QIcon(pixmap)

    def _build_styles(self) -> str:
        return """
        QMainWindow {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #edf6ff, stop:1 #f8fbff);
            color: #0f172a;
        }
        #topBar {
            background: #f7fbff;
            border-radius: 10px;
        }
        QPushButton[tab="true"] {
            background: transparent;
            border: none;
            color: #475569;
            padding: 6px 10px;
            font-weight: 600;
        }
        QPushButton[tab="true"][active="true"] {
            color: #0ea5e9;
            border-bottom: 2px solid #0ea5e9;
        }
        #sidePanel {
            background: #f7fbff;
            border-radius: 10px;
        }
        #primaryButton {
            background: #0ea5e9;
            color: white;
            padding: 10px;
            border-radius: 8px;
            font-weight: 600;
        }
        #wavePanel {
            background: white;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
        }
        #playButton {
            background: #0ea5e9;
            color: white;
            border-radius: 22px;
            min-width: 44px;
            min-height: 44px;
            font-weight: 700;
        }
        #cueLabel {
            background: #e2f1ff;
            color: #0b6aa8;
            padding: 2px 6px;
            border-radius: 6px;
            font-size: 10px;
            font-weight: 600;
        }
        #ghostButton {
            background: #e0f2fe;
            color: #0369a1;
            border-radius: 6px;
            padding: 4px 10px;
            font-weight: 600;
        }
        #searchInput {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 6px 10px;
        }
        #tracksTable {
            background: white;
            border-radius: 10px;
            gridline-color: transparent;
            alternate-background-color: #f8fbff;
            selection-background-color: #e0f2fe;
            selection-color: #0f172a;
        }
        #tracksTable::item:hover {
            background: transparent;
        }
        #tracksTable QHeaderView::section {
            background: #f1f5f9;
            color: #475569;
            padding: 6px;
            border: none;
            font-weight: 600;
        }
        """


def run() -> int:
    app = QtWidgets.QApplication()
    window = MainWindow()
    window.show()
    return app.exec()

"""Main window for the SaioMusic UI."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

from mutagen import File as MutagenFile
from PySide6 import QtCore, QtGui, QtMultimedia, QtSvg, QtWidgets

if TYPE_CHECKING:
    import numpy as np

from saio_music.ui.widgets import ActiveRowDelegate, KeyWheelWidget, WaveformWidget


def _make_chip(text: str, bg: str, fg: str = "#0f172a") -> QtWidgets.QLabel:
    chip = QtWidgets.QLabel(text)
    chip.setAlignment(QtCore.Qt.AlignCenter)
    chip.setFixedHeight(24)
    chip.setStyleSheet(
        f"background: {bg}; color: {fg}; border-radius: 6px; padding: 2px 8px;"
    )
    return chip


def _make_cover_pixmap(color: str) -> QtGui.QPixmap:
    pixmap = QtGui.QPixmap(30, 30)
    pixmap.fill(QtGui.QColor(color))
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.setPen(QtGui.QColor("#ffffff"))
    painter.drawRect(3, 3, 24, 24)
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

        self._player = QtMultimedia.QMediaPlayer(self)
        self._audio_output = QtMultimedia.QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)

        self._tracks_table: QtWidgets.QTableWidget | None = None
        self._tracks_count: QtWidgets.QLabel | None = None
        self._tags_cache = self._load_cache()
        self._cache_dirty = False
        self._waveform_widget: WaveformWidget | None = None
        self._track_title: QtWidgets.QLabel | None = None
        self._time_label: QtWidgets.QLabel | None = None
        self._waveform_status: QtWidgets.QLabel | None = None
        self._key_chip: QtWidgets.QLabel | None = None
        self._bpm_chip: QtWidgets.QLabel | None = None
        self._energy_chip: QtWidgets.QLabel | None = None
        self._duration_ms = 0
        self._active_key_filter: str | None = None
        self._active_key_filters: set[str] = set()
        self._key_wheel: KeyWheelWidget | None = None
        self._play_button: QtWidgets.QToolButton | None = None
        self._now_playing_cover: QtWidgets.QLabel | None = None
        self._current_row: int | None = None
        self._prev_button: QtWidgets.QToolButton | None = None
        self._next_button: QtWidgets.QToolButton | None = None
        self._track_index_label: QtWidgets.QLabel | None = None
        self._play_icon: QtGui.QIcon | None = None
        self._pause_icon: QtGui.QIcon | None = None
        self._full_title: str = ""
        self._volume_slider: QtWidgets.QSlider | None = None
        self._volume_widget: QtWidgets.QWidget | None = None
        self._active_delegate: ActiveRowDelegate | None = None
        self._env_cache: dict[str, str] | None = None
        self._header: QtWidgets.QHeaderView | None = None

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
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)
        self._start_active_row_timer()

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
        key_wheel.keyToggled.connect(self._toggle_key_filter)
        key_wheel.clearRequested.connect(self._clear_key_filter)
        layout.addWidget(key_wheel, alignment=QtCore.Qt.AlignHCenter)
        self._key_wheel = key_wheel

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
        top_row.setSpacing(10)

        transport = QtWidgets.QHBoxLayout()
        transport.setSpacing(6)

        prev_btn = QtWidgets.QToolButton()
        prev_btn.setObjectName("transportButtonSmall")
        prev_btn.setIcon(self._make_svg_icon("prev", 16))
        prev_btn.setIconSize(QtCore.QSize(16, 16))
        prev_btn.setCursor(QtCore.Qt.PointingHandCursor)
        prev_btn.setToolTip("Previous track")
        prev_btn.clicked.connect(lambda: self._play_adjacent(-1))

        play = QtWidgets.QToolButton()
        play.setObjectName("playButtonLarge")
        self._play_icon = self._make_svg_icon("play", 20, "#ffffff")
        self._pause_icon = self._make_svg_icon("pause", 20, "#ffffff")
        play.setIcon(self._play_icon)
        play.setIconSize(QtCore.QSize(20, 20))
        play.setCursor(QtCore.Qt.PointingHandCursor)
        play.setToolTip("Play/Pause")
        play.clicked.connect(self._toggle_playback)

        next_btn = QtWidgets.QToolButton()
        next_btn.setObjectName("transportButtonSmall")
        next_btn.setIcon(self._make_svg_icon("next", 16))
        next_btn.setIconSize(QtCore.QSize(16, 16))
        next_btn.setCursor(QtCore.Qt.PointingHandCursor)
        next_btn.setToolTip("Next track")
        next_btn.clicked.connect(lambda: self._play_adjacent(1))

        transport.addWidget(prev_btn)
        transport.addWidget(play)
        transport.addWidget(next_btn)
        transport_widget = QtWidgets.QWidget()
        transport_widget.setObjectName("transportCluster")
        transport_widget.setLayout(transport)

        top_row.addWidget(transport_widget)

        waveform = WaveformWidget()
        waveform.seekRequested.connect(self._seek_to_ratio)
        self._waveform_widget = waveform

        overlay = QtWidgets.QGridLayout()
        overlay.setContentsMargins(0, 0, 0, 0)
        overlay.addWidget(waveform, 0, 0)

        time_label = QtWidgets.QLabel("00:00 / 00:00")
        time_label.setObjectName("timeOverlay")
        time_label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        overlay.addWidget(
            time_label, 0, 0, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom
        )
        self._time_label = time_label

        waveform_status = QtWidgets.QLabel("")
        waveform_status.setObjectName("waveformStatus")
        waveform_status.setVisible(False)
        overlay.addWidget(
            waveform_status, 0, 0, alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignBottom
        )
        self._waveform_status = waveform_status

        waveform_widget = QtWidgets.QWidget()
        waveform_widget.setLayout(overlay)
        top_row.addWidget(waveform_widget, 1)

        layout.addLayout(top_row)

        now_row = QtWidgets.QHBoxLayout()
        now_row.setSpacing(12)

        now_playing = QtWidgets.QVBoxLayout()
        now_label = QtWidgets.QLabel("NOW PLAYING")
        now_label.setObjectName("nowPlayingLabel")
        title = QtWidgets.QLabel("No track selected")
        title.setObjectName("nowPlayingTitle")
        title.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )
        title.installEventFilter(self)
        self._full_title = "No track selected"
        now_playing.addWidget(now_label)
        now_playing.addWidget(title)
        now_playing_widget = QtWidgets.QWidget()
        now_playing_widget.setLayout(now_playing)
        now_playing_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )
        self._track_title = title

        cover = QtWidgets.QLabel()
        cover.setFixedSize(52, 52)
        cover.setStyleSheet("background: #e2e8f0; border-radius: 10px;")
        self._now_playing_cover = cover

        info_row = QtWidgets.QHBoxLayout()
        info_row.setSpacing(8)
        info_row.addWidget(QtWidgets.QLabel("KEY"))
        key_chip = _make_chip("--", "#8fe4ff", "#075985")
        info_row.addWidget(key_chip)
        info_row.addWidget(QtWidgets.QLabel("ENERGY"))
        energy_chip = _make_chip("0", "#e2e8f0", "#0f172a")
        info_row.addWidget(energy_chip)
        info_row.addWidget(QtWidgets.QLabel("BPM"))
        bpm_chip = _make_chip("--", "#e2e8f0", "#0f172a")
        info_row.addWidget(bpm_chip)
        self._key_chip = key_chip
        self._energy_chip = energy_chip
        self._bpm_chip = bpm_chip

        info_wrap = QtWidgets.QWidget()
        info_wrap.setObjectName("infoBlock")
        info_wrap.setLayout(info_row)
        info_wrap.setFixedWidth(230)

        volume_layout = QtWidgets.QHBoxLayout()
        volume_layout.setSpacing(6)
        volume_icon = QtWidgets.QLabel("🔊")
        volume_icon.setObjectName("volumeIcon")
        volume_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        volume_slider.setObjectName("volumeSlider")
        volume_slider.setRange(0, 100)
        volume_slider.setValue(70)
        volume_slider.setFixedWidth(140)
        volume_slider.valueChanged.connect(
            lambda value: self._audio_output.setVolume(value / 100)
        )
        volume_layout.addWidget(volume_icon)
        volume_layout.addWidget(volume_slider)
        volume_widget = QtWidgets.QWidget()
        volume_widget.setLayout(volume_layout)
        volume_widget.setFixedWidth(190)

        track_index = QtWidgets.QLabel("0 / 0")
        track_index.setObjectName("trackIndex")
        self._track_index_label = track_index

        now_row.addWidget(cover)
        now_row.addWidget(now_playing_widget, 1)
        now_row.addWidget(info_wrap)
        now_row.addWidget(volume_widget)
        now_row.addWidget(track_index)
        layout.addLayout(now_row)
        self._play_button = play
        self._prev_button = prev_btn
        self._next_button = next_btn
        self._volume_slider = volume_slider
        self._volume_widget = volume_widget

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
        clear_filter = QtWidgets.QPushButton("CLEAR FILTER")
        clear_filter.setObjectName("ghostButton")
        clear_filter.clicked.connect(self._clear_key_filter)
        search_row.addWidget(clear_filter)
        search_row.addStretch(1)
        tracks_label = QtWidgets.QLabel("0 TRACKS")
        search_row.addWidget(tracks_label)
        layout.addLayout(search_row)

        table = QtWidgets.QTableWidget(0, 8)
        table.setHorizontalHeaderLabels(
            [
                "COVER ART",
                "ARTIST",
                "TITLE",
                "LABEL",
                "GENRE",
                "TEMPO",
                "KEY RESULT",
                "ENERGY",
            ]
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setShowGrid(True)
        table.setSortingEnabled(True)
        table.setFocusPolicy(QtCore.Qt.NoFocus)
        table.setObjectName("tracksTable")
        delegate = ActiveRowDelegate(table)
        table.setItemDelegate(delegate)
        self._active_delegate = delegate
        table.setCursor(QtCore.Qt.PointingHandCursor)
        table.viewport().setCursor(QtCore.Qt.PointingHandCursor)
        table.setIconSize(QtCore.QSize(30, 30))
        table.setColumnWidth(0, 44)
        table.cellClicked.connect(self._select_row_on_click)
        table.cellDoubleClicked.connect(self._select_track_row)

        header = table.horizontalHeader()
        header.setSectionsMovable(True)
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.setMouseTracking(True)
        header.viewport().setMouseTracking(True)
        header.sectionMoved.connect(self._persist_table_header)
        header.sectionResized.connect(self._persist_table_header)
        header.installEventFilter(self)
        header.viewport().installEventFilter(self)
        self._header = header

        table.setColumnWidth(0, 44)
        table.setColumnWidth(1, 200)
        table.setColumnWidth(2, 240)
        table.setColumnWidth(3, 140)
        table.setColumnWidth(4, 120)
        table.setColumnWidth(5, 80)
        table.setColumnWidth(6, 90)
        table.setColumnWidth(7, 80)

        self._restore_table_header(table)

        layout.addWidget(table, 1)
        self._tracks_table = table
        self._tracks_count = tracks_label
        return wrapper

    def _select_tracks_folder(self) -> None:
        default_dir = self._load_last_folder() or str(Path.cwd())
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select music folder", default_dir
        )
        if not folder:
            return
        self._save_last_folder(Path(folder))
        self._load_tracks(Path(folder))

    def _load_tracks(self, folder: Path) -> None:
        if self._tracks_table is None:
            return

        supported = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".aac"}
        progress = QtWidgets.QProgressDialog("Scanning folder...", "Cancel", 0, 0, self)
        progress.setWindowTitle("Loading tracks")
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setAutoClose(False)
        progress.setMinimumDuration(0)
        progress.show()

        files: list[Path] = []
        canceled = False
        try:
            for path in folder.rglob("*"):
                if progress.wasCanceled():
                    canceled = True
                    break
                if path.is_file() and path.suffix.lower() in supported:
                    files.append(path)
                if len(files) % 200 == 0:
                    QtWidgets.QApplication.processEvents()

            if canceled:
                return

            files.sort(key=lambda item: item.name.lower())

            progress.setLabelText("Loading tracks...")
            progress.setMaximum(len(files))
            progress.setValue(0)

            sorting_enabled = self._tracks_table.isSortingEnabled()
            self._tracks_table.setSortingEnabled(False)
            self._tracks_table.setRowCount(0)
            for index, path in enumerate(files, start=1):
                if progress.wasCanceled():
                    canceled = True
                    break
                self._add_track_row(path)
                progress.setValue(index)
                if index % 50 == 0:
                    QtWidgets.QApplication.processEvents()

            self._tracks_table.setSortingEnabled(sorting_enabled)
        finally:
            progress.close()
            self._save_cache()
            self._update_tracks_count()
            self._refresh_key_counts()

    def _select_track_row(self, row: int, column: int) -> None:
        if self._tracks_table is None:
            return
        self._set_active_row(row)
        self._current_row = row
        self._play_track_for_row(row)

    def _select_row_on_click(self, row: int, column: int) -> None:
        if self._tracks_table is None:
            return
        self._tracks_table.selectRow(row)
        self._current_row = row

    def _toggle_key_filter(self, key: str, enabled: bool) -> None:
        if self._tracks_table is None:
            return
        if enabled:
            self._active_key_filters.add(key)
        else:
            self._active_key_filters.discard(key)

        if self._key_wheel is not None:
            self._key_wheel.set_selected_keys(self._active_key_filters)

        if not self._active_key_filters:
            for row in range(self._tracks_table.rowCount()):
                self._tracks_table.setRowHidden(row, False)
            self._update_tracks_count()
            return

        for row in range(self._tracks_table.rowCount()):
            item = self._tracks_table.item(row, 6)
            if item is None:
                self._tracks_table.setRowHidden(row, True)
                continue
            value = item.data(QtCore.Qt.UserRole)
            value = str(value).strip().upper()
            match = value in {key.upper() for key in self._active_key_filters}
            self._tracks_table.setRowHidden(row, not match)

        self._update_tracks_count()

    def _clear_key_filter(self) -> None:
        if self._tracks_table is None:
            return
        self._active_key_filters.clear()
        if self._key_wheel is not None:
            self._key_wheel.set_selected_keys(set())
        for row in range(self._tracks_table.rowCount()):
            self._tracks_table.setRowHidden(row, False)
        self._update_tracks_count()
        self._refresh_key_counts()

    def _refresh_key_counts(self) -> None:
        if self._tracks_table is None or self._key_wheel is None:
            return
        counts: dict[str, int] = {}
        for row in range(self._tracks_table.rowCount()):
            item = self._tracks_table.item(row, 6)
            if item is None:
                continue
            value = item.data(QtCore.Qt.UserRole)
            key = str(value).strip().upper()
            if not key:
                continue
            counts[key] = counts.get(key, 0) + 1
        self._key_wheel.set_counts(counts)

    def _camelot_color(self, key: str | None) -> QtGui.QColor | None:
        if not key:
            return None
        return KeyWheelWidget.color_for_key(key)

    def _genre_color(self, genre: object) -> QtGui.QColor | None:
        genre = (self._coerce_text(genre) or "").strip().lower()
        if not genre:
            return None
        palette = {
            "house": "#dbeafe",
            "deep house": "#bfdbfe",
            "tech house": "#c7d2fe",
            "techno": "#e0e7ff",
            "trance": "#fde68a",
            "progressive": "#fee2e2",
            "pop": "#fecdd3",
            "rock": "#fef3c7",
            "hip hop": "#bbf7d0",
            "rap": "#bbf7d0",
            "r&b": "#fed7aa",
            "drum & bass": "#bae6fd",
            "dnb": "#bae6fd",
            "edm": "#fbcfe8",
            "dance": "#fbcfe8",
            "electronic": "#e9d5ff",
            "ambient": "#e0f2fe",
        }
        for key, color in palette.items():
            if key in genre:
                return QtGui.QColor(color)
        return QtGui.QColor("#f1f5f9")

    def _normalize_camelot_key(self, value: object) -> str | None:
        text = self._coerce_text(value) or ""
        match = re.search(r"\b(1[0-2]|[1-9])\s*([ABab])\b", text)
        if not match:
            return None
        return f"{int(match.group(1))}{match.group(2).upper()}"

    def _play_track_for_row(self, row: int) -> None:
        if self._tracks_table is None:
            return
        item = self._tracks_table.item(row, 0)
        if item is None:
            return
        path_value = item.data(QtCore.Qt.UserRole)
        if not path_value:
            return
        path = Path(str(path_value))
        tags = self._read_tags(path)
        self._current_row = row
        self._set_active_row(row)
        self._play_track(path, tags)
        self._update_track_position()

    def _set_active_row(self, row: int) -> None:
        if self._tracks_table is None:
            return
        for index in range(self._tracks_table.rowCount()):
            item = self._tracks_table.item(index, 0)
            if item is not None:
                item.setData(QtCore.Qt.UserRole + 1, False)
                item.setText("")
        active_item = self._tracks_table.item(row, 0)
        if active_item is not None:
            active_item.setData(QtCore.Qt.UserRole + 1, True)
            active_item.setText("")
        self._tracks_table.viewport().update()

    def _play_adjacent(self, step: int) -> None:
        if self._tracks_table is None:
            return
        rows = [
            row
            for row in range(self._tracks_table.rowCount())
            if not self._tracks_table.isRowHidden(row)
        ]
        if not rows:
            return
        if self._current_row not in rows:
            target = rows[0]
        else:
            index = rows.index(self._current_row)
            target = rows[(index + step) % len(rows)]
        self._play_track_for_row(target)

    def _update_track_position(self) -> None:
        if self._tracks_table is None or self._track_index_label is None:
            return
        rows = [
            row
            for row in range(self._tracks_table.rowCount())
            if not self._tracks_table.isRowHidden(row)
        ]
        if not rows:
            self._track_index_label.setText("0 / 0")
            return
        if self._current_row not in rows:
            self._track_index_label.setText(f"0 / {len(rows)}")
            return
        index = rows.index(self._current_row) + 1
        self._track_index_label.setText(f"{index} / {len(rows)}")

    def _update_tracks_count(self) -> None:
        if self._tracks_table is None or self._tracks_count is None:
            return
        visible = 0
        for row in range(self._tracks_table.rowCount()):
            if not self._tracks_table.isRowHidden(row):
                visible += 1
        self._tracks_count.setText(f"{visible} TRACKS")
        self._update_navigation_state(visible)
        self._update_track_position()

    def _toggle_playback(self) -> None:
        if self._player.playbackState() == QtMultimedia.QMediaPlayer.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _seek_to_ratio(self, ratio: float) -> None:
        if self._duration_ms <= 0:
            return
        self._player.setPosition(int(self._duration_ms * ratio))

    def _on_position_changed(self, position_ms: int) -> None:
        if self._duration_ms > 0 and self._waveform_widget is not None:
            self._waveform_widget.set_playhead(position_ms / self._duration_ms)
        self._update_time_label(position_ms, self._duration_ms)

    def _on_duration_changed(self, duration_ms: int) -> None:
        self._duration_ms = duration_ms
        self._update_time_label(self._player.position(), duration_ms)

    def _update_time_label(self, position_ms: int, duration_ms: int) -> None:
        if self._time_label is None:
            return
        current = self._format_time(position_ms)
        total = self._format_time(duration_ms)
        self._time_label.setText(f"{current} / {total}")

    def _format_time(self, value_ms: int) -> str:
        total_seconds = max(0, int(value_ms / 1000))
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"

    def _start_active_row_timer(self) -> None:
        timer = QtCore.QTimer(self)
        timer.setInterval(240)
        timer.timeout.connect(self._tick_active_row)
        timer.start()
        self._active_row_timer = timer

    def _tick_active_row(self) -> None:
        if self._tracks_table is None or self._active_delegate is None:
            return
        phase = (getattr(self._active_delegate, "_phase", 0.0) + 1) % 3
        self._active_delegate.set_phase(phase)
        self._tracks_table.viewport().update()

    def _update_navigation_state(self, visible: int) -> None:
        if self._prev_button is None or self._next_button is None:
            return
        enabled = visible > 1
        self._prev_button.setEnabled(enabled)
        self._next_button.setEnabled(enabled)

    def _on_playback_state_changed(
        self, state: QtMultimedia.QMediaPlayer.PlaybackState
    ) -> None:
        if self._play_button is None:
            return
        if self._active_delegate is not None:
            self._active_delegate.set_playing(
                state == QtMultimedia.QMediaPlayer.PlayingState
            )
        if state == QtMultimedia.QMediaPlayer.PlayingState:
            if self._pause_icon is not None:
                self._play_button.setIcon(self._pause_icon)
        else:
            if self._play_icon is not None:
                self._play_button.setIcon(self._play_icon)

    def _set_waveform_status(self, text: str) -> None:
        if self._waveform_status is None:
            return
        self._waveform_status.setText(text)
        self._waveform_status.setVisible(True)

    def _clear_waveform_status(self) -> None:
        if self._waveform_status is None:
            return
        self._waveform_status.setVisible(False)
        self._waveform_status.setText("")

    def _animate_now_playing(self, widget: QtWidgets.QWidget) -> None:
        effect = widget.graphicsEffect()
        if effect is None or not isinstance(effect, QtWidgets.QGraphicsOpacityEffect):
            effect = QtWidgets.QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        animation = QtCore.QPropertyAnimation(effect, b"opacity", widget)
        animation.setDuration(220)
        animation.setStartValue(0.3)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        animation.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    def _persist_table_header(self) -> None:
        if self._tracks_table is None:
            return
        header = self._tracks_table.horizontalHeader()
        encoded = base64.b64encode(header.saveState()).decode("ascii")
        self._save_env_value("TABLE_HEADER_STATE", encoded)

    def _restore_table_header(self, table: QtWidgets.QTableWidget) -> None:
        encoded = self._load_env_value("TABLE_HEADER_STATE")
        if not encoded:
            return
        try:
            data = base64.b64decode(encoded)
        except Exception:
            return
        table.horizontalHeader().restoreState(data)

    def _load_env_value(self, key: str) -> str | None:
        if self._env_cache is None:
            self._env_cache = {}
            env_path = Path.cwd() / ".env"
            if env_path.exists():
                try:
                    content = env_path.read_text(encoding="utf-8")
                except OSError:
                    content = ""
                for line in content.splitlines():
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    name, value = line.split("=", 1)
                    self._env_cache[name.strip()] = value.strip()
        return self._env_cache.get(key)

    def _save_env_value(self, key: str, value: str) -> None:
        env_path = Path.cwd() / ".env"
        existing: list[str] = []
        if env_path.exists():
            try:
                existing = env_path.read_text(encoding="utf-8").splitlines()
            except OSError:
                existing = []

        updated = False
        output: list[str] = []
        for line in existing:
            if line.strip().startswith(f"{key}="):
                output.append(f"{key}={value}")
                updated = True
            else:
                output.append(line)

        if not updated:
            output.append(f"{key}={value}")

        try:
            env_path.write_text("\n".join(output) + "\n", encoding="utf-8")
        except OSError:
            return
        if self._env_cache is not None:
            self._env_cache[key] = value

    def _is_on_section_border(
        self, header: QtWidgets.QHeaderView, pos: QtCore.QPoint
    ) -> bool:
        section = header.logicalIndexAt(pos)
        if section < 0:
            return False
        rect = header.sectionRect(section)
        return abs(pos.x() - rect.right()) <= 3

    def _update_title_elide(self) -> None:
        if self._track_title is None:
            return
        metrics = QtGui.QFontMetrics(self._track_title.font())
        elided = metrics.elidedText(
            self._full_title, QtCore.Qt.ElideRight, self._track_title.width()
        )
        self._track_title.setText(elided)

    def eventFilter(  # noqa: N802
        self, watched: QtCore.QObject, event: QtCore.QEvent
    ) -> bool:
        if watched is self._track_title and event.type() == QtCore.QEvent.Resize:
            self._update_title_elide()
        header = self._header
        if (
            header is not None
            and watched in {header, header.viewport()}
            and event.type() == QtCore.QEvent.MouseMove
        ):
            pos = header.viewport().mapFromGlobal(QtGui.QCursor.pos())
            cursor = QtCore.Qt.ArrowCursor
            if self._is_on_section_border(header, pos):
                cursor = QtCore.Qt.SplitHCursor
            header.viewport().setCursor(cursor)
        return super().eventFilter(watched, event)

    def _make_svg_icon(
        self, name: str, size: int, color: str = "#0f172a"
    ) -> QtGui.QIcon:
        paths = {
            "play": "<polygon points='6,4 18,12 6,20'/>",
            "pause": "<rect x='6' y='4' width='4' height='16'/>"
            "<rect x='14' y='4' width='4' height='16'/>",
            "prev": "<rect x='5' y='5' width='2' height='14'/>"
            "<polygon points='19,4 9,12 19,20'/>",
            "next": "<polygon points='5,4 15,12 5,20'/>"
            "<rect x='17' y='5' width='2' height='14'/>",
        }
        path = paths.get(name, paths["play"])
        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>"
            f"<g fill='{color}'>{path}</g></svg>"
        )
        renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode("utf-8")))
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return QtGui.QIcon(pixmap)

    def _play_track(self, path: Path, tags: dict[str, str | bytes | None]) -> None:
        self._player.setSource(QtCore.QUrl.fromLocalFile(str(path)))
        self._player.play()
        camelot_key = self._normalize_camelot_key(tags.get("comments"))
        if self._key_wheel is not None:
            self._key_wheel.set_active_key(camelot_key)
        self._update_now_playing(path, tags)
        self._load_waveform(path)

    def _update_now_playing(
        self, path: Path, tags: dict[str, str | bytes | None]
    ) -> None:
        title = self._coerce_text(tags.get("title")) or ""
        artist = self._coerce_text(tags.get("artist")) or path.stem
        if self._track_title is not None:
            self._full_title = f"{artist} - {title}".strip(" -")
            self._update_title_elide()
            self._animate_now_playing(self._track_title)
        if self._now_playing_cover is not None:
            cover_data = tags.get("cover_data")
            if isinstance(cover_data, bytes):
                image = QtGui.QImage.fromData(cover_data)
                if not image.isNull():
                    pixmap = QtGui.QPixmap.fromImage(image).scaled(
                        44,
                        44,
                        QtCore.Qt.KeepAspectRatio,
                        QtCore.Qt.SmoothTransformation,
                    )
                    self._now_playing_cover.setPixmap(pixmap)
                    self._animate_now_playing(self._now_playing_cover)
        if self._key_chip is not None:
            key_value = self._coerce_text(tags.get("comments")) or "--"
            self._key_chip.setText(key_value)
            key_color = self._camelot_color(self._normalize_camelot_key(key_value))
            if key_color is not None:
                self._key_chip.setStyleSheet(
                    f"background: {key_color.name()}; color: #0b1726; "
                    "border-radius: 6px; padding: 2px 8px;"
                )
            else:
                self._key_chip.setStyleSheet(
                    "background: #8fe4ff; color: #075985; "
                    "border-radius: 6px; padding: 2px 8px;"
                )
            self._animate_now_playing(self._key_chip)
        if self._bpm_chip is not None:
            self._bpm_chip.setText(self._coerce_text(tags.get("bpm")) or "--")
            self._animate_now_playing(self._bpm_chip)
        if self._energy_chip is not None:
            self._energy_chip.setText("0")
            self._animate_now_playing(self._energy_chip)

    def _load_waveform(self, path: Path) -> None:
        if self._waveform_widget is None:
            return
        cached = self._get_cached_waveform(path)
        if cached is not None:
            self._waveform_widget.set_waveform(cached)
            return

        progress = QtWidgets.QProgressDialog(
            "Analyzing waveform...", "Cancel", 0, 0, self
        )
        progress.setWindowTitle("Waveform analysis")
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setAutoClose(False)
        progress.setMinimumDuration(0)
        progress.show()
        self._set_waveform_status("Loading waveform...")

        try:
            samples = self._build_waveform(path, target_bars=320, progress=progress)
            if progress.wasCanceled():
                return
            self._waveform_widget.set_waveform(samples)
            if samples:
                self._store_cached_waveform(path, samples)
                self._save_cache()
            else:
                self._set_waveform_status("Waveform unavailable")
                QtCore.QTimer.singleShot(1500, self._clear_waveform_status)
        finally:
            progress.close()
            self._clear_waveform_status()

    def _build_waveform(
        self,
        path: Path,
        target_bars: int,
        progress: QtWidgets.QProgressDialog | None = None,
    ) -> list[float]:
        try:
            import numpy as np
        except ModuleNotFoundError:
            return []

        data = self._read_audio_samples(path)
        if data is None:
            return []

        if data.size == 0:
            return []

        mono = data.mean(axis=1)
        total = len(mono)
        if total == 0:
            return []

        hop = max(1, total // target_bars)
        total_bars = max(1, (total + hop - 1) // hop)
        if progress is not None:
            progress.setMaximum(total_bars)
            progress.setValue(0)

        samples: list[float] = []
        for index, start in enumerate(range(0, total, hop), start=1):
            if progress is not None:
                if progress.wasCanceled():
                    return []
                progress.setValue(index)
                if index % 20 == 0:
                    QtWidgets.QApplication.processEvents()
            chunk = mono[start : start + hop]
            if chunk.size == 0:
                continue
            rms = float(np.sqrt(np.mean(chunk**2)))
            samples.append(rms)

        max_value = max(samples) if samples else 1.0
        if max_value == 0:
            return samples
        return [value / max_value for value in samples]

    def _read_audio_samples(self, path: Path) -> np.ndarray | None:
        try:
            import numpy as np
        except ModuleNotFoundError:
            return None

        try:
            import soundfile as sf
        except ModuleNotFoundError:
            sf = None

        if sf is not None:
            try:
                data, _ = sf.read(path, always_2d=True, dtype="float32")
                return data
            except Exception:
                pass

        if path.suffix.lower() == ".wav":
            try:
                import wave

                with wave.open(str(path), "rb") as wav:
                    frames = wav.readframes(wav.getnframes())
                    channels = wav.getnchannels()
                    sample_width = wav.getsampwidth()
                    dtype = {1: np.int8, 2: np.int16, 4: np.int32}.get(sample_width)
                    if dtype is None:
                        return None
                    data = np.frombuffer(frames, dtype=dtype).astype(np.float32)
                    if channels > 1:
                        data = data.reshape(-1, channels)
                    else:
                        data = data.reshape(-1, 1)
                    max_val = float(np.iinfo(dtype).max)
                    return data / max_val
            except Exception:
                return None

        try:
            from pydub import AudioSegment
        except ModuleNotFoundError:
            return None

        try:
            segment = AudioSegment.from_file(path)
        except Exception:
            return None

        samples = np.array(segment.get_array_of_samples())
        channels = segment.channels or 1
        if channels > 1:
            samples = samples.reshape(-1, channels)
        else:
            samples = samples.reshape(-1, 1)
        max_val = float(1 << (8 * segment.sample_width - 1))
        if max_val == 0:
            return None
        return samples.astype(np.float32) / max_val

    def _load_last_folder(self) -> str | None:
        env_path = Path.cwd() / ".env"
        if not env_path.exists():
            return None
        try:
            content = env_path.read_text(encoding="utf-8")
        except OSError:
            return None
        for line in content.splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "LAST_MUSIC_FOLDER":
                return value.strip().strip('"').strip("'")
        return None

    def _save_last_folder(self, folder: Path) -> None:
        env_path = Path.cwd() / ".env"
        existing: list[str] = []
        if env_path.exists():
            try:
                existing = env_path.read_text(encoding="utf-8").splitlines()
            except OSError:
                existing = []

        updated = False
        output: list[str] = []
        for line in existing:
            if line.strip().startswith("LAST_MUSIC_FOLDER="):
                output.append(f"LAST_MUSIC_FOLDER={folder}")
                updated = True
            else:
                output.append(line)

        if not updated:
            output.append(f"LAST_MUSIC_FOLDER={folder}")

        try:
            env_path.write_text("\n".join(output) + "\n", encoding="utf-8")
        except OSError:
            return

    def _add_track_row(self, path: Path) -> None:
        if self._tracks_table is None:
            return

        tags = self._read_tags(path)
        row = self._tracks_table.rowCount()
        self._tracks_table.insertRow(row)
        self._tracks_table.setRowHeight(row, 36)

        cover_item = QtWidgets.QTableWidgetItem()
        cover_data = tags.get("cover_data")
        if not isinstance(cover_data, bytes):
            cover_data = None
        cover_icon = self._cover_icon(cover_data, row)
        cover_item.setIcon(cover_icon)
        cover_item.setData(QtCore.Qt.UserRole, str(path))
        cover_item.setData(QtCore.Qt.UserRole + 1, False)
        cover_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self._tracks_table.setItem(row, 0, cover_item)

        artist = tags.get("artist") or path.stem
        title = tags.get("title") or ""
        label = tags.get("label") or ""
        genre = tags.get("genre") or ""
        tempo = tags.get("bpm") or ""
        key_result = tags.get("comments") or ""
        energy = "0"

        self._tracks_table.setItem(row, 1, QtWidgets.QTableWidgetItem(artist))
        self._tracks_table.setItem(row, 2, QtWidgets.QTableWidgetItem(title))
        self._tracks_table.setItem(row, 3, QtWidgets.QTableWidgetItem(label))
        genre_item = QtWidgets.QTableWidgetItem(genre)
        genre_item.setData(QtCore.Qt.UserRole, genre.lower())
        genre_color = self._genre_color(genre)
        if genre_color is not None:
            genre_item.setBackground(genre_color)
        self._tracks_table.setItem(row, 4, genre_item)
        self._tracks_table.setItem(row, 5, QtWidgets.QTableWidgetItem(tempo))

        key_item = QtWidgets.QTableWidgetItem(key_result)
        key_item.setTextAlignment(QtCore.Qt.AlignCenter)
        normalized_key = self._normalize_camelot_key(key_result)
        key_item.setData(QtCore.Qt.UserRole, normalized_key or "")
        key_color = self._camelot_color(normalized_key)
        if key_color is not None:
            key_item.setBackground(key_color)
        self._tracks_table.setItem(row, 6, key_item)

        energy_item = QtWidgets.QTableWidgetItem(energy)
        energy_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self._tracks_table.setItem(row, 7, energy_item)

    def _read_tags(self, path: Path) -> dict[str, str | bytes | None]:
        cached = self._get_cached_tags(path)
        if cached is not None:
            if cached.get("cover_data") is None:
                try:
                    audio_full = MutagenFile(path)
                except Exception:
                    audio_full = None
                if audio_full is not None:
                    cover_data = self._extract_cover(audio_full)
                    if cover_data:
                        cached["cover_data"] = cover_data
                        self._store_cached_tags(path, cached)
            if not cached.get("genre"):
                try:
                    audio = MutagenFile(path, easy=True)
                except Exception:
                    audio = None
                if audio is not None:
                    cached["genre"] = self._first_tag(audio, ["genre", "tcon"])
                    self._store_cached_tags(path, cached)
            return cached

        info: dict[str, str | bytes | None] = {
            "artist": None,
            "title": None,
            "label": None,
            "genre": None,
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
            info["label"] = self._first_tag(
                audio, ["label", "organization", "publisher"]
            )
            info["genre"] = self._first_tag(audio, ["genre", "tcon"])
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

        self._store_cached_tags(path, info)
        return info

    def _get_cached_tags(self, path: Path) -> dict[str, str | bytes | None] | None:
        key = self._cache_key(path)
        entry = self._tags_cache.get(key)
        if not isinstance(entry, dict):
            return None
        try:
            mtime_ns = path.stat().st_mtime_ns
        except OSError:
            return None
        if entry.get("mtime_ns") != mtime_ns:
            return None

        cover_data = entry.get("cover_data")
        cover_bytes = None
        if isinstance(cover_data, str):
            try:
                cover_bytes = base64.b64decode(cover_data)
            except Exception:
                cover_bytes = None

        return {
            "artist": self._coerce_text(entry.get("artist")),
            "title": self._coerce_text(entry.get("title")),
            "label": self._coerce_text(entry.get("label")),
            "genre": self._coerce_text(entry.get("genre")),
            "bpm": self._coerce_text(entry.get("bpm")),
            "comments": self._coerce_text(entry.get("comments")),
            "cover_data": cover_bytes,
        }

    def _store_cached_tags(
        self, path: Path, info: dict[str, str | bytes | None]
    ) -> None:
        try:
            mtime_ns = path.stat().st_mtime_ns
        except OSError:
            return

        cover_data = info.get("cover_data")
        cover_encoded = None
        if isinstance(cover_data, bytes):
            cover_encoded = self._encode_cover_thumbnail(cover_data)

        entry = self._tags_cache.get(self._cache_key(path), {})
        if not isinstance(entry, dict):
            entry = {}
        entry.update(
            {
                "mtime_ns": mtime_ns,
                "artist": info.get("artist"),
                "title": info.get("title"),
                "label": info.get("label"),
                "genre": info.get("genre"),
                "bpm": info.get("bpm"),
                "comments": info.get("comments"),
                "cover_data": cover_encoded,
            }
        )
        self._tags_cache[self._cache_key(path)] = entry
        self._cache_dirty = True

    def _cache_key(self, path: Path) -> str:
        return str(path.resolve())

    def _get_cached_waveform(self, path: Path) -> list[float] | None:
        key = self._cache_key(path)
        entry = self._tags_cache.get(key)
        if not isinstance(entry, dict):
            return None
        try:
            mtime_ns = path.stat().st_mtime_ns
        except OSError:
            return None
        if entry.get("mtime_ns") != mtime_ns:
            return None
        waveform = entry.get("waveform")
        if not isinstance(waveform, list):
            return None
        output: list[float] = []
        for value in waveform:
            try:
                output.append(float(value))
            except (TypeError, ValueError):
                continue
        return output

    def _store_cached_waveform(self, path: Path, samples: list[float]) -> None:
        try:
            mtime_ns = path.stat().st_mtime_ns
        except OSError:
            return
        key = self._cache_key(path)
        entry = self._tags_cache.get(key)
        if not isinstance(entry, dict):
            entry = {}
        entry["mtime_ns"] = mtime_ns
        entry["waveform"] = samples
        self._tags_cache[key] = entry
        self._cache_dirty = True

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

    def _encode_cover_thumbnail(self, cover_data: bytes) -> str | None:
        image = QtGui.QImage.fromData(cover_data)
        if image.isNull():
            return None
        thumb = image.scaled(
            60, 60, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
        )
        buffer = QtCore.QBuffer()
        buffer.open(QtCore.QIODevice.WriteOnly)
        if not thumb.save(buffer, "PNG"):
            return None
        return base64.b64encode(buffer.data()).decode("ascii")

    def _load_cache(self) -> dict[str, dict[str, object]]:
        cache_path = Path.cwd() / ".saiomusic_cache.json"
        if not cache_path.exists():
            return {}
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if isinstance(data, dict):
            return data
        return {}

    def _save_cache(self) -> None:
        if not self._cache_dirty:
            return
        cache_path = Path.cwd() / ".saiomusic_cache.json"
        try:
            cache_path.write_text(
                json.dumps(self._tags_cache, ensure_ascii=True), encoding="utf-8"
            )
            self._cache_dirty = False
        except OSError:
            return

    def _cover_icon(self, cover_data: bytes | None, row: int) -> QtGui.QIcon:
        if cover_data:
            image = QtGui.QImage.fromData(cover_data)
            if not image.isNull():
                pixmap = QtGui.QPixmap.fromImage(image).scaled(
                    30, 30, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
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
        QAbstractButton {
            cursor: pointinghand;
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
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #ffffff, stop:1 #eef6ff);
            border-radius: 12px;
            border: 1px solid #e2e8f0;
        }
        #transportCluster {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 6px;
        }
        #playButtonLarge {
            background: #0ea5e9;
            color: white;
            border-radius: 18px;
            min-width: 36px;
            min-height: 36px;
            font-weight: 700;
            font-size: 16px;
        }
        #transportButtonSmall {
            background: #f1f5f9;
            color: #0f172a;
            border-radius: 14px;
            min-width: 28px;
            min-height: 28px;
            font-weight: 700;
            font-size: 12px;
        }
        #nowPlayingLabel {
            color: #64748b;
            font-size: 9px;
            letter-spacing: 1px;
        }
        #nowPlayingTitle {
            font-size: 16px;
            font-weight: 600;
        }
        #timeOverlay {
            color: #0f172a;
            background: rgba(255, 255, 255, 0.75);
            padding: 2px 6px;
            border-radius: 6px;
        }
        #infoBlock {
            background: #f1f5f9;
            border-radius: 10px;
            padding: 6px 10px;
        }
        #volumeIcon {
            color: #0f7cc4;
            font-weight: 700;
        }
        #volumeSlider::groove:horizontal {
            background: #e2e8f0;
            height: 6px;
            border-radius: 3px;
        }
        #volumeSlider::sub-page:horizontal {
            background: #0ea5e9;
            border-radius: 3px;
        }
        #volumeSlider::handle:horizontal {
            background: #0f7cc4;
            width: 14px;
            margin: -4px 0;
            border-radius: 7px;
        }
        #trackIndex {
            color: #64748b;
            font-weight: 600;
            padding-left: 6px;
        }
        #searchInput {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 6px 10px;
        }
        #ghostButton {
            background: #e0f2fe;
            color: #0369a1;
            border-radius: 6px;
            padding: 4px 10px;
            font-weight: 600;
        }
        #waveformStatus {
            color: #0f7cc4;
            font-weight: 600;
        }
        #tracksTable {
            background: white;
            border-radius: 10px;
            gridline-color: #e5eef7;
            alternate-background-color: #f8fbff;
            selection-background-color: #e0f2fe;
            selection-color: #0f172a;
        }
        #tracksTable::item:hover {
            background: transparent;
        }
        #tracksTable::item:selected {
            background: #eef7ff;
            color: #0f172a;
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

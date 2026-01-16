"""Main window for the SaioMusic UI."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

from mutagen import File as MutagenFile
from PySide6 import QtCore, QtGui, QtMultimedia, QtWidgets

if TYPE_CHECKING:
    import numpy as np

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
        controls = QtWidgets.QHBoxLayout()
        prev_btn = QtWidgets.QToolButton()
        prev_btn.setObjectName("transportButton")
        prev_btn.setText("⏮")
        prev_btn.setToolTip("Previous track")

        play = QtWidgets.QToolButton()
        play.setObjectName("playButton")
        play.setText("▶")
        play.setToolTip("Play/Pause")
        play.clicked.connect(self._toggle_playback)

        next_btn = QtWidgets.QToolButton()
        next_btn.setObjectName("transportButton")
        next_btn.setText("⏭")
        next_btn.setToolTip("Next track")

        controls.addWidget(prev_btn)
        controls.addWidget(play)
        controls.addWidget(next_btn)
        controls_widget = QtWidgets.QWidget()
        controls_widget.setLayout(controls)

        waveform_column = QtWidgets.QVBoxLayout()
        waveform = WaveformWidget()
        waveform.seekRequested.connect(self._seek_to_ratio)
        waveform_column.addWidget(waveform)
        waveform_widget = QtWidgets.QWidget()
        waveform_widget.setLayout(waveform_column)
        self._waveform_widget = waveform

        top_row.addWidget(controls_widget)
        top_row.addSpacing(10)
        top_row.addWidget(waveform_widget, 1)

        layout.addLayout(top_row)

        time_row = QtWidgets.QHBoxLayout()
        waveform_status = QtWidgets.QLabel("")
        waveform_status.setObjectName("waveformStatus")
        waveform_status.setVisible(False)
        time_row.addWidget(waveform_status)
        time_row.addStretch(1)
        time_label = QtWidgets.QLabel("00:00 / 00:00")
        time_row.addWidget(time_label)
        self._time_label = time_label
        self._waveform_status = waveform_status
        layout.addLayout(time_row)

        title = QtWidgets.QLabel("No track selected")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)
        self._track_title = title

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
        info_row.addStretch(1)
        info_row.addWidget(QtWidgets.QLabel("VIRTUAL PIANO"))
        layout.addLayout(info_row)
        self._key_chip = key_chip
        self._energy_chip = energy_chip
        self._bpm_chip = bpm_chip

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

        table = QtWidgets.QTableWidget(0, 7)
        table.setHorizontalHeaderLabels(
            [
                "COVER ART",
                "ARTIST",
                "TITLE",
                "LABEL",
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
        table.setSortingEnabled(True)
        table.setObjectName("tracksTable")
        table.setIconSize(QtCore.QSize(30, 30))
        table.setColumnWidth(0, 44)
        table.cellClicked.connect(self._clear_track_selection)
        table.cellDoubleClicked.connect(self._select_track_row)

        table.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeToContents
        )
        table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(
            4, QtWidgets.QHeaderView.ResizeToContents
        )
        table.horizontalHeader().setSectionResizeMode(
            5, QtWidgets.QHeaderView.ResizeToContents
        )
        table.horizontalHeader().setSectionResizeMode(
            6, QtWidgets.QHeaderView.ResizeToContents
        )

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
        self._tracks_table.clearSelection()
        self._play_track_for_row(row)

    def _clear_track_selection(self, row: int, column: int) -> None:
        if self._tracks_table is None:
            return
        self._tracks_table.clearSelection()

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
            item = self._tracks_table.item(row, 5)
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
            item = self._tracks_table.item(row, 5)
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
        self._play_track(path, tags)

    def _update_tracks_count(self) -> None:
        if self._tracks_table is None or self._tracks_count is None:
            return
        visible = 0
        for row in range(self._tracks_table.rowCount()):
            if not self._tracks_table.isRowHidden(row):
                visible += 1
        self._tracks_count.setText(f"{visible} TRACKS")

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
            self._track_title.setText(f"{artist} - {title}".strip(" -"))
        if self._key_chip is not None:
            self._key_chip.setText(self._coerce_text(tags.get("comments")) or "--")
        if self._bpm_chip is not None:
            self._bpm_chip.setText(self._coerce_text(tags.get("bpm")) or "--")
        if self._energy_chip is not None:
            self._energy_chip.setText("0")

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
        self._tracks_table.setItem(row, 0, cover_item)

        artist = tags.get("artist") or path.stem
        title = tags.get("title") or ""
        label = tags.get("label") or ""
        tempo = tags.get("bpm") or ""
        key_result = tags.get("comments") or ""
        energy = "0"

        self._tracks_table.setItem(row, 1, QtWidgets.QTableWidgetItem(artist))
        self._tracks_table.setItem(row, 2, QtWidgets.QTableWidgetItem(title))
        self._tracks_table.setItem(row, 3, QtWidgets.QTableWidgetItem(label))
        self._tracks_table.setItem(row, 4, QtWidgets.QTableWidgetItem(tempo))

        key_item = QtWidgets.QTableWidgetItem(key_result)
        key_item.setTextAlignment(QtCore.Qt.AlignCenter)
        normalized_key = self._normalize_camelot_key(key_result)
        key_item.setData(QtCore.Qt.UserRole, normalized_key or "")
        key_color = self._camelot_color(normalized_key)
        if key_color is not None:
            key_item.setBackground(key_color)
        self._tracks_table.setItem(row, 5, key_item)

        energy_item = QtWidgets.QTableWidgetItem(energy)
        energy_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self._tracks_table.setItem(row, 6, energy_item)

    def _read_tags(self, path: Path) -> dict[str, str | bytes | None]:
        cached = self._get_cached_tags(path)
        if cached is not None:
            return cached

        info: dict[str, str | bytes | None] = {
            "artist": None,
            "title": None,
            "label": None,
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
        if isinstance(cover_data, bytes) and len(cover_data) <= 200_000:
            cover_encoded = base64.b64encode(cover_data).decode("ascii")

        entry = self._tags_cache.get(self._cache_key(path), {})
        if not isinstance(entry, dict):
            entry = {}
        entry.update(
            {
                "mtime_ns": mtime_ns,
                "artist": info.get("artist"),
                "title": info.get("title"),
                "label": info.get("label"),
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
        #playButton {
            background: #0ea5e9;
            color: white;
            border-radius: 22px;
            min-width: 44px;
            min-height: 44px;
            font-weight: 700;
            font-size: 16px;
        }
        #transportButton {
            background: #e2f1ff;
            color: #0369a1;
            border-radius: 18px;
            min-width: 36px;
            min-height: 36px;
            font-weight: 700;
            font-size: 14px;
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

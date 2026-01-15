"""Main window for the SaioMusic UI."""

from __future__ import annotations

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
        search_row.addWidget(QtWidgets.QLabel("12 TRACKS"))
        layout.addLayout(search_row)

        table = QtWidgets.QTableWidget(12, 9)
        table.setHorizontalHeaderLabels(
            [
                "COVER ART",
                "ARTIST",
                "TITLE",
                "TEMPO",
                "KEY RESULT",
                "ENERGY",
                "CUE POINTS",
                "STATUS",
                "RATING",
            ]
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setSortingEnabled(False)
        table.setObjectName("tracksTable")

        data = [
            ("Chef Faker", "Gold", "140", "2A", "5", "8", "Completed", "#8fe4ff"),
            (
                "Porter Robinson",
                "Look at the Sky",
                "115",
                "2B",
                "5",
                "8",
                "Completed",
                "#7dd3fc",
            ),
            (
                "Gryffin & Illenium",
                "Feel Good",
                "138",
                "10B",
                "7",
                "8",
                "Completed",
                "#a5b4fc",
            ),
            (
                "Dua Lipa",
                "Don't Start Now",
                "124",
                "10A",
                "7",
                "8",
                "Completed",
                "#c4b5fd",
            ),
            (
                "Juice WRLD",
                "Lucid Dreams",
                "112",
                "11A",
                "5",
                "8",
                "Completed",
                "#bae6fd",
            ),
            (
                "Travis Scott",
                "Highest in the Room",
                "153",
                "7A",
                "6",
                "8",
                "Completed",
                "#f9a8d4",
            ),
            (
                "David Guetta x MORTEN",
                "Kill Me Slow",
                "126",
                "11A",
                "8",
                "8",
                "Completed",
                "#bae6fd",
            ),
            (
                "Machine Gun Kelly",
                "Bloody Valentine",
                "80",
                "11A",
                "7",
                "8",
                "Completed",
                "#bae6fd",
            ),
            (
                "Sofi Tukker",
                "Swing",
                "118",
                "4A",
                "5",
                "8",
                "Completed",
                "#fde68a",
            ),
            (
                "Daft Punk",
                "Digital Love",
                "125",
                "11B",
                "6",
                "6",
                "Completed",
                "#8fe4ff",
            ),
            (
                "Masked Wolf",
                "Astronaut in the Ocean",
                "150",
                "11A",
                "6",
                "7",
                "Completed",
                "#bae6fd",
            ),
            ("SG Lewis", "Chemicals", "122", "2A", "6", "8", "Completed", "#8fe4ff"),
        ]

        cover_colors = [
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

        for row, entry in enumerate(data):
            artist, title, tempo, key, energy, cue_points, status, key_color = entry
            cover_item = QtWidgets.QTableWidgetItem()
            cover_item.setIcon(QtGui.QIcon(_make_cover_pixmap(cover_colors[row])))
            table.setItem(row, 0, cover_item)
            table.setItem(row, 1, QtWidgets.QTableWidgetItem(artist))
            table.setItem(row, 2, QtWidgets.QTableWidgetItem(title))
            table.setItem(row, 3, QtWidgets.QTableWidgetItem(tempo))

            key_item = QtWidgets.QTableWidgetItem(key)
            key_item.setBackground(QtGui.QColor(key_color))
            key_item.setTextAlignment(QtCore.Qt.AlignCenter)
            table.setItem(row, 4, key_item)

            energy_item = QtWidgets.QTableWidgetItem(energy)
            energy_item.setTextAlignment(QtCore.Qt.AlignCenter)
            table.setItem(row, 5, energy_item)

            cue_item = QtWidgets.QTableWidgetItem(cue_points)
            cue_item.setTextAlignment(QtCore.Qt.AlignCenter)
            table.setItem(row, 6, cue_item)

            status_item = QtWidgets.QTableWidgetItem(status)
            status_item.setTextAlignment(QtCore.Qt.AlignCenter)
            table.setItem(row, 7, status_item)

            table.setItem(row, 8, QtWidgets.QTableWidgetItem("o o o"))

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
        table.horizontalHeader().setSectionResizeMode(
            6, QtWidgets.QHeaderView.ResizeToContents
        )
        table.horizontalHeader().setSectionResizeMode(
            7, QtWidgets.QHeaderView.ResizeToContents
        )
        table.horizontalHeader().setSectionResizeMode(
            8, QtWidgets.QHeaderView.ResizeToContents
        )

        layout.addWidget(table, 1)
        return wrapper

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

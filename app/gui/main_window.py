from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QUrl,
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.gui.widgets import (
    AnimatedSwitch,
    AuroraBackground,
    GlowButton,
    HoverFrame,
)
from app.gui.worker import VideoGenerationWorker
from app.services.gameplay.library import GameplayLibrary
from app.services.tts.edge_provider import DEFAULT_VOICE


VOICE_OPTIONS = {
    "Светлана (RU)": "ru-RU-SvetlanaNeural",
    "Дмитрий (RU)": "ru-RU-DmitryNeural",
    "Jenny (EN)": "en-US-JennyNeural",
    "Guy (EN)": "en-US-GuyNeural",
}


class MainWindow(QMainWindow):
    """Премиальный интерфейс AI Shorts Factory."""

    def __init__(self) -> None:
        super().__init__()

        self.worker: VideoGenerationWorker | None = None
        self.music_path: Path | None = None
        self.output_path = Path(
            "output/final_short.mp4"
        )

        self.setWindowTitle("AI Shorts Factory")
        self.setMinimumSize(1120, 700)
        self.resize(1460, 860)

        self._build_interface()
        self._apply_styles()
        self._load_gameplay_categories()
        self._preview_style = "Glow"
        self._update_preview_appearance()
        self._animate_appearance()

    def _build_interface(self) -> None:
        root = AuroraBackground()
        self.setCentralWidget(root)

        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(
            18,
            16,
            18,
            18,
        )
        root_layout.setSpacing(18)

        root_layout.addWidget(
            self._build_sidebar()
        )

        content = QWidget()
        content.setObjectName("contentRoot")

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(
            6,
            2,
            6,
            4,
        )
        content_layout.setSpacing(18)

        content_layout.addLayout(
            self._build_header()
        )

        body = QHBoxLayout()
        body.setSpacing(18)

        center_column = QVBoxLayout()
        center_column.setSpacing(18)
        center_column.addWidget(
            self._build_story_card(),
            stretch=27,
        )
        center_column.addWidget(
            self._build_settings_card(),
            stretch=33,
        )
        center_column.addWidget(
            self._build_output_card(),
            stretch=15,
        )
        center_column.addWidget(
            self._build_generate_card(),
            stretch=16,
        )

        body.addLayout(
            center_column,
            stretch=8,
        )
        body.addWidget(
            self._build_preview_column(),
            stretch=3,
        )

        content_layout.addLayout(
            body,
            stretch=1,
        )

        root_layout.addWidget(
            content,
            stretch=1,
        )

    def _build_sidebar(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("sidebar")
        panel.setFixedWidth(206)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(
            18,
            20,
            18,
            18,
        )
        layout.setSpacing(10)

        brand = QLabel("✦  AI Shorts Factory")
        brand.setObjectName("brandLabel")
        layout.addWidget(brand)

        layout.addSpacing(14)

        navigation = (
            "⌂  Главная",
            "▣  Проекты",
            "▤  Шаблоны",
            "♫  Музыка",
            "⚙  Настройки",
        )

        for index, text in enumerate(navigation):
            button = QPushButton(text)
            button.setObjectName(
                "navButtonActive"
                if index == 0
                else "navButton"
            )
            button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )
            layout.addWidget(button)

        layout.addStretch()

        pro_card = HoverFrame(
            object_name="proCard"
        )
        pro_layout = QVBoxLayout(pro_card)
        pro_layout.setContentsMargins(
            16,
            16,
            16,
            16,
        )
        pro_layout.setSpacing(8)

        pro_title = QLabel("♛  PRO версия")
        pro_title.setObjectName("proTitle")

        pro_text = QLabel(
            "Дополнительные стили "
            "и настройки экспорта."
        )
        pro_text.setObjectName("mutedText")
        pro_text.setWordWrap(True)

        pro_button = QPushButton("Улучшить")
        pro_button.setObjectName(
            "miniGradientButton"
        )

        pro_layout.addWidget(pro_title)
        pro_layout.addWidget(pro_text)
        pro_layout.addWidget(pro_button)

        layout.addWidget(pro_card)

        version = QLabel("v1.2.0   •   Готов к работе")
        version.setObjectName("versionLabel")
        version.setWordWrap(False)
        layout.addWidget(version)

        return panel

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()

        title_block = QVBoxLayout()
        title_block.setSpacing(0)

        title = QLabel(
            "✦  Создай вирусный Short"
        )
        title.setObjectName("pageTitle")

        title_block.addWidget(title)

        header.addLayout(title_block)
        header.addStretch()

        badge = QLabel("⚡  PRO")
        badge.setObjectName("proBadge")
        header.addWidget(badge)

        return header

    def _make_card(
        self,
        object_name: str = "glassCard",
    ) -> HoverFrame:
        return HoverFrame(
            object_name=object_name
        )

    def _build_story_card(self) -> HoverFrame:
        card = self._make_card()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            22,
            20,
            22,
            20,
        )
        layout.setSpacing(10)

        top = QHBoxLayout()

        title = QLabel("Текст истории")
        title.setObjectName("cardTitle")

        self.character_label = QLabel(
            "0 / 5000"
        )
        self.character_label.setObjectName(
            "mutedText"
        )

        top.addWidget(title)
        top.addStretch()
        top.addWidget(self.character_label)

        self.story_input = QTextEdit()
        self.story_input.setObjectName(
            "storyInput"
        )
        self.story_input.setPlaceholderText(
            "Вчера вечером со мной "
            "произошла очень странная история..."
        )
        self.story_input.setFixedHeight(104)
        self.story_input.textChanged.connect(
            self._update_character_count
        )

        actions = QHBoxLayout()

        clear_button = QPushButton(
            "⌫  Очистить"
        )
        clear_button.setObjectName(
            "secondaryButton"
        )
        clear_button.clicked.connect(
            self.story_input.clear
        )

        example_button = QPushButton(
            "✦  Вставить пример"
        )
        example_button.setObjectName(
            "secondaryButton"
        )
        example_button.clicked.connect(
            self._insert_example
        )

        actions.addWidget(clear_button)
        actions.addWidget(example_button)
        actions.addStretch()

        layout.addLayout(top)
        layout.addWidget(self.story_input)
        layout.addLayout(actions)

        return card

    def _build_settings_card(self) -> HoverFrame:
        card = self._make_card()
        card.setMinimumHeight(218)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            22,
            18,
            22,
            20,
        )
        layout.setSpacing(14)

        title = QLabel("Настройки видео")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)

        gameplay_card = self._setting_box(
            "🎮",
            "Геймплей",
        )
        self.gameplay_combo = QComboBox()
        gameplay_card.layout().addWidget(
            self.gameplay_combo
        )

        voice_card = self._setting_box(
            "🎙",
            "Озвучка",
        )
        self.voice_combo = QComboBox()

        for label, voice_id in VOICE_OPTIONS.items():
            self.voice_combo.addItem(
                label,
                voice_id,
            )

        default_index = self.voice_combo.findData(
            DEFAULT_VOICE
        )

        if default_index >= 0:
            self.voice_combo.setCurrentIndex(
                default_index
            )

        voice_card.layout().addWidget(
            self.voice_combo
        )

        music_card = self._setting_box(
            "♫",
            "Музыка",
        )
        self.music_combo = QComboBox()
        self.music_combo.addItem(
            "Без музыки",
            None,
        )
        self.music_combo.addItem(
            "Выбрать файл…",
            "browse",
        )
        self.music_combo.currentIndexChanged.connect(
            self._music_combo_changed
        )
        music_card.layout().addWidget(
            self.music_combo
        )

        speed_card = self._setting_box(
            "ϟ",
            "Скорость голоса",
        )
        speed_card.setFixedHeight(62)
        speed_row = QHBoxLayout()

        self.voice_rate_slider = QSlider(
            Qt.Orientation.Horizontal
        )
        self.voice_rate_slider.setRange(
            -50,
            100,
        )
        self.voice_rate_slider.setValue(0)

        self.voice_rate_value = QLabel("0%")
        self.voice_rate_value.setObjectName(
            "valueLabel"
        )

        self.voice_rate_slider.valueChanged.connect(
            lambda value: self.voice_rate_value.setText(
                f"{value}%"
            )
        )

        speed_row.setContentsMargins(0, 0, 0, 0)
        speed_row.setSpacing(8)
        speed_row.addWidget(
            self.voice_rate_value
        )
        speed_row.addWidget(
            self.voice_rate_slider
        )
        speed_card.layout().addLayout(speed_row)

        volume_card = self._setting_box(
            "◖",
            "Громкость музыки",
        )
        volume_card.setFixedHeight(62)
        volume_row = QHBoxLayout()

        self.music_volume_slider = QSlider(
            Qt.Orientation.Horizontal
        )
        self.music_volume_slider.setRange(
            0,
            100,
        )
        self.music_volume_slider.setValue(12)

        self.music_volume_value = QLabel(
            "12%"
        )
        self.music_volume_value.setObjectName(
            "valueLabel"
        )

        self.music_volume_slider.valueChanged.connect(
            lambda value: self.music_volume_value.setText(
                f"{value}%"
            )
        )

        volume_row.setContentsMargins(0, 0, 0, 0)
        volume_row.setSpacing(8)
        volume_row.addWidget(
            self.music_volume_value
        )
        volume_row.addWidget(
            self.music_volume_slider
        )
        volume_card.layout().addLayout(volume_row)

        subtitles_card = self._setting_box(
            "▰",
            "Субтитры",
        )
        subtitles_card.setFixedHeight(62)
        subtitle_row = QHBoxLayout()
        subtitle_row.addStretch()

        self.subtitles_switch = AnimatedSwitch(
            checked=True
        )

        subtitle_row.addWidget(
            self.subtitles_switch
        )
        subtitles_card.layout().addLayout(
            subtitle_row
        )

        grid.addWidget(
            gameplay_card,
            0,
            0,
        )
        grid.addWidget(
            voice_card,
            0,
            1,
        )
        grid.addWidget(
            music_card,
            0,
            2,
        )
        grid.addWidget(
            speed_card,
            1,
            0,
        )
        grid.addWidget(
            volume_card,
            1,
            1,
        )
        grid.addWidget(
            subtitles_card,
            1,
            2,
        )

        layout.addLayout(grid)
        return card

    def _setting_box(
        self,
        icon: str,
        title: str,
    ) -> HoverFrame:
        box = HoverFrame(
            object_name="settingCard"
        )
        box.setFixedHeight(78)

        layout = QVBoxLayout(box)
        layout.setContentsMargins(
            12,
            8,
            12,
            9,
        )
        layout.setSpacing(6)

        label = QLabel(
            f"{icon}  {title}"
        )
        label.setObjectName("settingTitle")
        layout.addWidget(label)

        return box

    def _build_output_card(self) -> HoverFrame:
        card = self._make_card()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            22,
            16,
            22,
            18,
        )
        layout.setSpacing(10)

        title = QLabel("Выходной файл")
        title.setObjectName("cardTitle")

        row = QHBoxLayout()

        self.output_label = QLabel(
            str(self.output_path)
        )
        self.output_label.setObjectName(
            "pathLabel"
        )

        change_button = QPushButton(
            "▣  Изменить"
        )
        change_button.setObjectName(
            "accentButton"
        )
        change_button.clicked.connect(
            self._select_output
        )

        row.addWidget(
            self.output_label,
            stretch=1,
        )
        row.addWidget(change_button)

        layout.addWidget(title)
        layout.addLayout(row)

        return card

    def _build_generate_card(self) -> HoverFrame:
        card = self._make_card(
            "generateCard"
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            14,
            14,
            14,
            14,
        )
        layout.setSpacing(9)

        self.status_label = QLabel(
            "●  Готов к созданию видео"
        )
        self.status_label.setObjectName(
            "statusLabel"
        )

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(
            0,
            100,
        )
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)

        self.generate_button = GlowButton(
            "✦  СОЗДАТЬ SHORT"
        )
        self.generate_button.clicked.connect(
            self._start_generation
        )

        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(
            self.generate_button
        )

        return card

    def _build_preview_column(self) -> HoverFrame:
        card = self._make_card()
        card.setMinimumWidth(350)
        card.setMaximumWidth(390)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            18,
            16,
            18,
            16,
        )
        layout.setSpacing(12)

        top = QHBoxLayout()

        title = QLabel("Предпросмотр")
        title.setObjectName("cardTitle")

        ratio = QLabel("9:16")
        ratio.setObjectName("ratioBadge")

        top.addWidget(title)
        top.addStretch()
        top.addWidget(ratio)

        preview = QFrame()
        preview.setObjectName("previewFrame")
        preview.setFixedSize(240, 430)
        preview.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )

        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(
            18,
            18,
            18,
            18,
        )
        preview_layout.addStretch()

        preview_title = QLabel("PREVIEW")
        preview_title.setObjectName(
            "previewHint"
        )
        preview_title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.preview_text = QLabel(
            "Твой текст появится здесь"
        )
        self.preview_text.setObjectName(
            "previewText"
        )
        self.preview_text.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.preview_text.setWordWrap(True)
        self.preview_text.setFixedHeight(104)
        self.preview_text.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )

        preview_layout.addWidget(
            preview_title
        )
        preview_layout.addWidget(
            self.preview_text
        )
        preview_layout.addStretch()

        controls_card = QFrame()
        controls_card.setObjectName("previewControls")

        controls_layout = QVBoxLayout(controls_card)
        controls_layout.setContentsMargins(
            12,
            14,
            12,
            14,
        )
        controls_layout.setSpacing(10)

        style_title = QLabel(
            "Оформление субтитров"
        )
        style_title.setObjectName(
            "settingTitle"
        )

        styles_row = QHBoxLayout()
        styles_row.setSpacing(8)

        self.preview_style_buttons: list[QPushButton] = []

        for index, style_name in enumerate(
            ("Glow", "Bold", "Classic")
        ):
            button = QPushButton(style_name)
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.setObjectName(
                "subtitleStyleActive"
                if index == 0
                else "subtitleStyle"
            )
            button.setFixedHeight(34)
            button.clicked.connect(
                lambda checked, name=style_name, current=button:
                self._set_preview_style(name, current)
            )
            self.preview_style_buttons.append(button)
            styles_row.addWidget(button)

        options_grid = QGridLayout()
        options_grid.setContentsMargins(
            0,
            10,
            0,
            0,
        )
        options_grid.setHorizontalSpacing(10)
        options_grid.setVerticalSpacing(14)
        options_grid.setColumnStretch(0, 0)
        options_grid.setColumnStretch(1, 1)

        size_label = QLabel("Размер")
        size_label.setObjectName("mutedText")

        self.preview_font_size = QSpinBox()
        self.preview_font_size.setRange(14, 34)
        self.preview_font_size.setValue(20)
        self.preview_font_size.setSuffix(" px")
        self.preview_font_size.valueChanged.connect(
            self._update_preview_appearance
        )

        position_label = QLabel("Положение")
        position_label.setObjectName("mutedText")

        self.preview_position = QComboBox()
        self.preview_position.addItems(
            ("Центр", "Ниже", "Вниз")
        )
        self.preview_position.currentIndexChanged.connect(
            self._update_preview_position
        )
        
        self.preview_position.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.preview_position.setMinimumContentsLength(12)
        self.preview_position.setMaxVisibleItems(4)

        opacity_label = QLabel("Фон текста")
        opacity_label.setObjectName("mutedText")

        self.preview_opacity = QSlider(
            Qt.Orientation.Horizontal
        )
        self.preview_opacity.setRange(20, 100)
        self.preview_opacity.setValue(72)
        self.preview_opacity.valueChanged.connect(
            self._update_preview_appearance
        )

        options_grid.addWidget(size_label, 0, 0)
        options_grid.addWidget(position_label, 0, 1)
        options_grid.addWidget(self.preview_font_size, 1, 0)
        options_grid.addWidget(self.preview_position, 1, 1)

        # Дополнительный вертикальный воздух перед настройкой фона.
        options_grid.setRowMinimumHeight(2, 10)

        options_grid.addWidget(opacity_label, 3, 0)
        options_grid.addWidget(
            self.preview_opacity,
            3,
            1,
        )

        controls_layout.addWidget(style_title)
        controls_layout.addLayout(styles_row)
        controls_layout.addSpacing(14)
        controls_layout.addLayout(options_grid)

        layout.addLayout(top)
        layout.addWidget(
            preview,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )

        # Отделяем панель оформления от окна предпросмотра.
        layout.addSpacing(18)

        layout.addWidget(controls_card)
        layout.addStretch()

        self.story_input.textChanged.connect(
            self._update_preview
        )

        return card

    def _set_preview_style(
        self,
        style_name: str,
        selected_button: QPushButton,
    ) -> None:
        for button in self.preview_style_buttons:
            active = button is selected_button
            button.setChecked(active)
            button.setObjectName(
                "subtitleStyleActive"
                if active
                else "subtitleStyle"
            )
            button.style().unpolish(button)
            button.style().polish(button)

        self._preview_style = style_name
        self._update_preview_appearance()

    def _update_preview_appearance(self) -> None:
        style_name = getattr(
            self,
            "_preview_style",
            "Glow",
        )
        font_size = self.preview_font_size.value()
        opacity = self.preview_opacity.value()
        alpha = int(255 * opacity / 100)

        if style_name == "Glow":
            background = f"rgba(28, 8, 70, {alpha})"
            border = "1px solid rgba(236, 72, 153, 165)"
            color = "#ffffff"
        elif style_name == "Bold":
            background = f"rgba(0, 0, 0, {alpha})"
            border = "1px solid rgba(255, 255, 255, 60)"
            color = "#ffffff"
        else:
            background = f"rgba(5, 8, 28, {alpha})"
            border = "1px solid rgba(126, 106, 255, 65)"
            color = "#e5e7eb"

        self.preview_text.setStyleSheet(
            f"""
            QLabel {{
                color: {color};
                font-size: {font_size}px;
                font-weight: 800;
                background: {background};
                border: {border};
                border-radius: 10px;
                padding: 10px;
            }}
            """
        )

    def _update_preview_position(self) -> None:
        index = self.preview_position.currentIndex()
        preview_layout = self.preview_text.parentWidget().layout()

        alignment = (
            Qt.AlignmentFlag.AlignCenter
            if index == 0
            else Qt.AlignmentFlag.AlignHCenter
        )
        preview_layout.setAlignment(
            self.preview_text,
            alignment,
        )

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                color: #f7f7ff;
                font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
                font-size: 14px;
            }

            QWidget#contentRoot,
                    QScrollArea > QWidget > QWidget {
                background: transparent;
                border: none;
            }

            QFrame#sidebar {
                background: rgba(7, 10, 28, 224);
                border: 1px solid rgba(119, 92, 246, 45);
                border-radius: 22px;
            }

            QLabel#brandLabel {
                font-family: "Segoe UI Variable Display", "Segoe UI";
                font-size: 17px;
                font-weight: 750;
                color: white;
            }

            QPushButton#navButton,
            QPushButton#navButtonActive {
                border: 1px solid transparent;
                border-radius: 13px;
                padding: 10px 14px;
                text-align: left;
                font-size: 15px;
                color: #aeb4d2;
                background: transparent;
            }

            QPushButton#navButton:hover {
                color: white;
                background: rgba(124, 58, 237, 28);
                border-color: rgba(124, 58, 237, 45);
            }

            QPushButton#navButtonActive {
                color: white;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(124, 58, 237, 150),
                    stop: 1 rgba(37, 99, 235, 65)
                );
                border-color: rgba(216, 180, 254, 120);
            }

            QFrame#proCard {
                background: rgba(38, 20, 88, 175);
                border: 1px solid rgba(192, 132, 252, 75);
                border-radius: 16px;
                max-height: 142px;
            }

            QLabel#proTitle {
                color: #f0abfc;
                font-size: 15px;
                font-weight: 700;
            }

            QPushButton#miniGradientButton {
                color: white;
                border: 1px solid rgba(255, 255, 255, 70);
                border-radius: 10px;
                padding: 9px;
                font-weight: 700;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #7c3aed,
                    stop: 1 #2563eb
                );
            }

            QLabel#versionLabel {
                color: #747b9d;
                font-size: 11px;
            }

            QLabel#pageTitle {
                color: white;
                font-family: "Segoe UI Variable Display", "Segoe UI";
                font-size: 28px;
                font-weight: 800;
            }

            QLabel#proBadge {
                color: #c7d2fe;
                background: rgba(30, 27, 75, 185);
                border: 1px solid rgba(99, 102, 241, 115);
                border-radius: 18px;
                padding: 9px 18px;
                font-weight: 700;
            }

            QFrame#glassCard,
            QFrame#generateCard {
                background: rgba(10, 14, 39, 220);
                border: 1px solid rgba(125, 103, 255, 55);
                border-radius: 19px;
            }

            QFrame#settingCard {
                background: rgba(13, 18, 52, 210);
                border: 1px solid rgba(126, 106, 255, 55);
                border-radius: 15px;
                min-height: 68px;
            }

            QLabel#cardTitle {
                font-family: "Segoe UI Variable Display", "Segoe UI";
                font-size: 16px;
                font-weight: 750;
                color: white;
            }

            QLabel#settingTitle {
                color: #d7daf0;
                font-size: 12px;
                font-weight: 650;
                padding-bottom: 0;
            }

            QLabel#mutedText {
                color: #969cbb;
                font-size: 12px;
            }

            QLabel#valueLabel {
                color: #f3f4ff;
                min-width: 38px;
                padding-right: 4px;
            }

            QTextEdit#storyInput {
                background: rgba(5, 8, 26, 225);
                border: 1px solid rgba(147, 51, 234, 135);
                border-radius: 14px;
                padding: 14px;
                font-size: 15px;
                selection-background-color: #7c3aed;
            }

            QTextEdit#storyInput:hover {
                border-color: rgba(96, 165, 250, 165);
            }

            QTextEdit#storyInput:focus {
                border: 1px solid rgba(217, 70, 239, 210);
            }

            QComboBox {
                background: rgba(5, 8, 28, 230);
                border: 1px solid rgba(126, 106, 255, 65);
                border-radius: 9px;
                padding-left: 10px;
                padding-right: 32px;
                min-height: 34px;
                max-height: 34px;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 26px;
                border: none;
                background: transparent;
            }

            QComboBox::down-arrow {
                width: 8px;
                height: 8px;
            }

            QSpinBox {
                background: rgba(5, 8, 28, 230);
                border: 1px solid rgba(126, 106, 255, 65);
                border-radius: 9px;
                padding: 0 9px;
                min-height: 34px;
                max-height: 34px;
            }

            QComboBox:hover,
            QSpinBox:hover {
                border-color: rgba(217, 70, 239, 160);
            }

            QComboBox QAbstractItemView {
                background: #0b102a;
                border: 1px solid rgba(126, 106, 255, 90);
                border-radius: 8px;
                selection-background-color: #6d28d9;
                padding: 4px;
                outline: none;
            }

            QSlider::groove:horizontal {
                height: 6px;
                border-radius: 3px;
                background: rgba(96, 83, 167, 95);
            }

            QSlider::sub-page:horizontal {
                border-radius: 3px;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #ec4899,
                    stop: 0.5 #7c3aed,
                    stop: 1 #2563eb
                );
            }

            QSlider::handle:horizontal {
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
                background: #8b5cf6;
                border: 2px solid #c4b5fd;
            }

            QPushButton#secondaryButton,
            QPushButton#accentButton {
                border-radius: 10px;
                padding: 9px 14px;
                font-weight: 650;
            }

            QPushButton#secondaryButton {
                color: #d8dcf2;
                background: rgba(63, 53, 116, 90);
                border: 1px solid rgba(126, 106, 255, 70);
            }

            QPushButton#secondaryButton:hover {
                background: rgba(124, 58, 237, 80);
                border-color: rgba(216, 180, 254, 130);
            }

            QPushButton#accentButton {
                color: white;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #7c3aed,
                    stop: 1 #4f46e5
                );
                border: 1px solid rgba(216, 180, 254, 115);
            }

            QLabel#pathLabel {
                color: #aeb5d0;
                background: rgba(4, 7, 24, 220);
                border: 1px solid rgba(126, 106, 255, 45);
                border-radius: 10px;
                padding: 10px 12px;
            }

            QLabel#statusLabel {
                color: #86efac;
                font-weight: 650;
            }

            QProgressBar {
                background: rgba(4, 7, 24, 220);
                border: 1px solid rgba(126, 106, 255, 45);
                border-radius: 6px;
                min-height: 10px;
                max-height: 10px;
            }

            QProgressBar::chunk {
                border-radius: 5px;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #ec4899,
                    stop: 0.5 #7c3aed,
                    stop: 1 #06b6d4
                );
            }

            QLabel#ratioBadge {
                color: #c4b5fd;
                background: rgba(76, 29, 149, 80);
                border-radius: 10px;
                padding: 5px 9px;
            }

            QFrame#previewFrame {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #07122e,
                    stop: 0.35 #10164c,
                    stop: 0.72 #32105f,
                    stop: 1 #071326
                );
                border: 1px solid rgba(99, 102, 241, 145);
                border-radius: 26px;
            }

            QLabel#previewHint {
                color: rgba(255, 255, 255, 80);
                font-size: 12px;
            }

            QLabel#previewText {
                color: white;
                font-size: 20px;
                font-weight: 800;
                background: rgba(28, 8, 70, 185);
                border: 1px solid rgba(236, 72, 153, 165);
                border-radius: 10px;
                padding: 10px;
            }

            QPushButton#subtitleStyle,
            QPushButton#subtitleStyleActive {
                min-height: 42px;
                border-radius: 10px;
                padding: 7px 10px;
                color: #c8cbdf;
                background: rgba(10, 14, 39, 210);
                border: 1px solid rgba(126, 106, 255, 55);
            }

            QPushButton#subtitleStyle:hover {
                color: white;
                border-color: rgba(217, 70, 239, 145);
                background: rgba(76, 29, 149, 80);
            }

            QPushButton#subtitleStyleActive {
                color: white;
                background: rgba(88, 28, 135, 150);
                border: 1px solid rgba(236, 72, 153, 205);
            }

            QFrame#previewControls {
                background: rgba(10, 14, 39, 180);
                border: 1px solid rgba(126, 106, 255, 45);
                border-radius: 14px;
            }

            QScrollBar:vertical {
                background: transparent;
                width: 9px;
            }

            QScrollBar::handle:vertical {
                background: rgba(126, 106, 255, 95);
                border-radius: 4px;
                min-height: 38px;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
            """
        )

    def _animate_appearance(self) -> None:
        self.setWindowOpacity(0.0)

        self._appearance = QPropertyAnimation(
            self,
            b"windowOpacity",
            self,
        )
        self._appearance.setDuration(650)
        self._appearance.setStartValue(0.0)
        self._appearance.setEndValue(1.0)
        self._appearance.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )
        self._appearance.start()

    def _update_character_count(self) -> None:
        count = len(
            self.story_input.toPlainText()
        )
        self.character_label.setText(
            f"{count} / 5000"
        )

    def _update_preview(self) -> None:
        text = self.story_input.toPlainText().strip()

        if not text:
            self.preview_text.setText(
                "Твой текст появится здесь"
            )
            return

        preview_words: list[str] = []

        for word in text.split()[:12]:
            if len(word) > 14:
                chunks = [
                    word[index:index + 14]
                    for index in range(0, len(word), 14)
                ]
                preview_words.append("\u200b".join(chunks))
            else:
                preview_words.append(word)

        preview = " ".join(preview_words)

        if len(text.split()) > 12:
            preview += "…"

        if len(preview) > 105:
            preview = preview[:102].rstrip() + "…"

        self.preview_text.setText(preview)

    def _insert_example(self) -> None:
        self.story_input.setPlainText(
            "Вчера вечером со мной произошла "
            "очень странная история. "
            "Я возвращался домой и заметил, "
            "что кто-то идёт за мной. "
            "Сначала я не придал этому значения, "
            "но потом понял, что это не случайность."
        )

    def _load_gameplay_categories(self) -> None:
        categories = (
            GameplayLibrary().list_categories()
        )

        self.gameplay_combo.clear()

        if not categories:
            self.gameplay_combo.addItem(
                "Категории не найдены"
            )
            self.gameplay_combo.setEnabled(False)
            return

        self.gameplay_combo.addItems(categories)

    def _music_combo_changed(
        self,
        index: int,
    ) -> None:
        value = self.music_combo.itemData(index)

        if value == "browse":
            self._select_music()

    def _select_music(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать музыку",
            str(Path("assets/music").resolve()),
            "Audio (*.mp3 *.wav *.m4a *.aac *.ogg)",
        )

        if not filename:
            self.music_combo.setCurrentIndex(0)
            return

        self.music_path = Path(filename)

        self.music_combo.blockSignals(True)

        existing = self.music_combo.findData(
            str(self.music_path)
        )

        if existing < 0:
            self.music_combo.addItem(
                self.music_path.name,
                str(self.music_path),
            )
            existing = (
                self.music_combo.count() - 1
            )

        self.music_combo.setCurrentIndex(existing)
        self.music_combo.blockSignals(False)

    def _select_output(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить видео",
            str(self.output_path.resolve()),
            "MP4 video (*.mp4)",
        )

        if not filename:
            return

        selected = Path(filename)

        if selected.suffix.lower() != ".mp4":
            selected = selected.with_suffix(
                ".mp4"
            )

        self.output_path = selected
        self.output_label.setText(
            str(self.output_path)
        )

    def _start_generation(self) -> None:
        story = self.story_input.toPlainText().strip()

        if not story:
            QMessageBox.warning(
                self,
                "Нет текста",
                "Вставь текст истории.",
            )
            return

        if not self.gameplay_combo.isEnabled():
            QMessageBox.warning(
                self,
                "Нет геймплея",
                "Добавь категорию "
                "в assets/gameplay.",
            )
            return

        selected_music = (
            self.music_combo.currentData()
        )

        music = None

        if (
            isinstance(selected_music, str)
            and selected_music
            not in {"browse", ""}
        ):
            music = Path(selected_music)

        self.worker = VideoGenerationWorker(
            story=story,
            gameplay=(
                self.gameplay_combo.currentText()
            ),
            output_video=self.output_path,
            voice=self.voice_combo.currentData(),
            voice_rate=(
                f"{self.voice_rate_slider.value():+d}%"
            ),
            music=music,
            music_volume=(
                self.music_volume_slider.value()
                / 100
            ),
            subtitles=(
                self.subtitles_switch.isChecked()
            ),
            parent=self,
        )

        self.worker.completed.connect(
            self._generation_completed
        )
        self.worker.failed.connect(
            self._generation_failed
        )
        self.worker.finished.connect(
            self._worker_finished
        )

        self.generate_button.set_busy(True)
        self.generate_button.setText(
            "✦  СОЗДАЁМ SHORT…"
        )
        self.status_label.setText(
            "●  Генерация озвучки и рендер…"
        )
        self.progress_bar.setRange(0, 0)

        self.worker.start()

    def _generation_completed(
        self,
        output_path: str,
    ) -> None:
        self.status_label.setText(
            "●  Видео успешно создано"
        )
        self.progress_bar.setRange(
            0,
            100,
        )
        self.progress_bar.setValue(100)

        answer = QMessageBox.question(
            self,
            "Видео готово",
            f"Файл создан:\n{output_path}\n\n"
            "Открыть папку?",
        )

        if answer == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(
                    str(
                        Path(output_path)
                        .parent
                        .resolve()
                    )
                )
            )

    def _generation_failed(
        self,
        error_message: str,
    ) -> None:
        self.status_label.setText(
            "●  Ошибка генерации"
        )
        self.progress_bar.setRange(
            0,
            100,
        )
        self.progress_bar.setValue(0)

        QMessageBox.critical(
            self,
            "Ошибка",
            error_message,
        )

    def _worker_finished(self) -> None:
        self.generate_button.set_busy(False)
        self.generate_button.setText(
            "✦  СОЗДАТЬ SHORT"
        )

        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None

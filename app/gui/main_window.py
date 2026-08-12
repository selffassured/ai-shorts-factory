from __future__ import annotations

from pathlib import Path
import json
import re

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QTimer,
    Qt,
    QUrl,
)
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QComboBox,
    QColorDialog,
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
    QStackedWidget,
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
from app.gui.worker import (
    VideoGenerationWorker,
    VoicePreviewWorker,
)
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoSink
from PySide6.QtMultimediaWidgets import QVideoWidget

from app.services.history.storage import RenderHistoryStorage
from app.services.projects.storage import ProjectStorage
from app.services.preflight import validate_generation
from app.services.queue.storage import RenderQueueStorage
from app.services.settings.storage import AppSettingsStorage
from app.services.templates.presets import TEMPLATE_PRESETS
from app.services.gameplay.library import GameplayLibrary
from app.services.video.video_info import get_media_duration, MediaInfoError
from app.services.tts.edge_provider import DEFAULT_VOICE

VOICE_OPTIONS = {
    "Светлана (RU)": "ru-RU-SvetlanaNeural",
    "Дмитрий (RU)": "ru-RU-DmitryNeural",
    "Emma (US Multi)": "en-US-EmmaMultilingualNeural",
    "Andrew (US Multi)": "en-US-AndrewMultilingualNeural",
}

EXPORT_PRESETS = {
    "Full HD · 30 FPS": (1080, 1920, 30),
    "HD · 30 FPS": (720, 1280, 30),
    "Full HD · 60 FPS": (1080, 1920, 60),
}



class MainWindow(QMainWindow):
    """Премиальный интерфейс AI Shorts Factory."""

    def __init__(self) -> None:
        super().__init__()

        self.project_storage = ProjectStorage()
        self.current_project_name: str | None = None

        # Точная настройка субтитров.
        self.preview_text_color = "#FFFFFF"
        self.preview_outline_color = "#E66BFF"
        self.settings_storage = AppSettingsStorage()
        self.app_settings = self.settings_storage.load()
        self.history_storage = RenderHistoryStorage()
        self.queue_storage = RenderQueueStorage()
        self.render_queue = self.queue_storage.load()
        self._queue_running = False
        self._queue_current_story = ""
        self._queue_failures = 0
        self._cancel_requested = False

        self.worker: VideoGenerationWorker | None = None
        self.voice_preview_worker: VoicePreviewWorker | None = None
        self.music_path: Path | None = None
        self.preview_gameplay_path: Path | None = None
        self.output_path = Path(
            "output/final_short.mp4"
        )

        self.voice_preview_audio = QAudioOutput(self)
        self.voice_preview_audio.setVolume(0.85)

        self.voice_preview_player = QMediaPlayer(self)
        self.voice_preview_player.setAudioOutput(
            self.voice_preview_audio
        )
        self.voice_preview_player.playbackStateChanged.connect(
            self._voice_preview_state_changed
        )

        self.music_preview_audio = QAudioOutput(self)
        self.music_preview_audio.setVolume(0.45)

        self.music_preview_player = QMediaPlayer(self)
        self.music_preview_player.setAudioOutput(
            self.music_preview_audio
        )
        self.music_preview_player.playbackStateChanged.connect(
            self._music_preview_state_changed
        )

        self.setWindowTitle("AI Shorts Factory")
        self.setMinimumSize(1120, 700)
        self.resize(1460, 860)

        self._build_interface()
        self._apply_styles()
        self._load_gameplay_categories()
        self._load_music_library()
        self._preview_style = "Glow"
        self._update_preview_appearance()
        self._apply_saved_app_settings()
        self._animate_appearance()
        self._connect_sidebar_actions()

    def _build_interface(self) -> None:
        root = AuroraBackground()
        self.setCentralWidget(root)

        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(18, 16, 18, 18)
        root_layout.setSpacing(18)
        root_layout.addWidget(self._build_sidebar())

        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("pageStack")

        self.home_page = self._build_home_page()
        self.projects_page = self._build_projects_page()
        self.templates_page = self._build_templates_page()
        self.history_page = self._build_history_page()
        self.queue_page = self._build_queue_page()

        for page in (
            self.home_page,
            self.projects_page,
            self.templates_page,
            self.history_page,
            self.queue_page,
        ):
            self.page_stack.addWidget(page)

        root_layout.addWidget(self.page_stack, stretch=1)

    def _build_home_page(self) -> QWidget:
        content = QWidget()
        content.setObjectName("contentRoot")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(6, 2, 6, 4)
        content_layout.setSpacing(18)
        content_layout.addLayout(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(18)

        center_column = QVBoxLayout()
        center_column.setSpacing(18)
        center_column.addWidget(self._build_story_card(), stretch=27)
        center_column.addWidget(self._build_settings_card(), stretch=33)
        center_column.addWidget(self._build_output_card(), stretch=15)
        center_column.addWidget(self._build_generate_card(), stretch=16)

        body.addLayout(center_column, stretch=8)
        body.addWidget(self._build_preview_column(), stretch=3)
        content_layout.addLayout(body, stretch=1)
        return content

    def _make_section_page(
        self,
        title_text: str,
        subtitle_text: str,
    ) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setObjectName("contentRoot")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 12, 18, 18)
        layout.setSpacing(18)

        title = QLabel(title_text)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("mutedText")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        return page, layout

    def _build_projects_page(self) -> QWidget:
        page, layout = self._make_section_page(
            "▣  Проекты",
            "Сохраняй настройки Shorts и возвращайся к ним позже.",
        )
        card = self._make_card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 20)
        card_layout.setSpacing(14)

        self.projects_page_list = QListWidget()
        self.projects_page_list.setObjectName("libraryList")
        card_layout.addWidget(self.projects_page_list, 1)

        row = QHBoxLayout()
        save_button = QPushButton("Сохранить текущий")
        open_button = QPushButton("Открыть")
        delete_button = QPushButton("Удалить")
        row.addWidget(save_button)
        row.addWidget(open_button)
        row.addWidget(delete_button)
        row.addStretch()
        card_layout.addLayout(row)

        save_button.clicked.connect(self._page_save_project)
        open_button.clicked.connect(self._page_open_project)
        delete_button.clicked.connect(self._page_delete_project)
        self.projects_page_list.itemDoubleClicked.connect(
            lambda _item: self._page_open_project()
        )
        layout.addWidget(card, 1)
        return page

    def _build_templates_page(self) -> QWidget:
        page, layout = self._make_section_page(
            "▤  Шаблоны",
            "Готовые пресеты оформления для текущего Short.",
        )
        card = self._make_card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 20)
        card_layout.setSpacing(14)

        self.templates_page_list = QListWidget()
        self.templates_page_list.setObjectName("libraryList")
        for name, preset in TEMPLATE_PRESETS.items():
            self.templates_page_list.addItem(
                f"{name}\n{preset['description']}"
            )
        card_layout.addWidget(self.templates_page_list, 1)

        row = QHBoxLayout()
        apply_button = QPushButton("Применить к Short")
        row.addWidget(apply_button)
        row.addStretch()
        card_layout.addLayout(row)

        apply_button.clicked.connect(self._page_apply_template)
        self.templates_page_list.itemDoubleClicked.connect(
            lambda _item: self._page_apply_template()
        )
        layout.addWidget(card, 1)
        return page

    def _build_history_page(self) -> QWidget:
        page, layout = self._make_section_page(
            "◷  История",
            "Все успешно созданные Shorts в одном месте.",
        )
        card = self._make_card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 20)
        card_layout.setSpacing(14)

        self.history_page_list = QListWidget()
        self.history_page_list.setObjectName("libraryList")
        card_layout.addWidget(self.history_page_list, 1)

        row = QHBoxLayout()
        open_button = QPushButton("Открыть файл")
        folder_button = QPushButton("Открыть папку")
        clear_button = QPushButton("Очистить историю")
        row.addWidget(open_button)
        row.addWidget(folder_button)
        row.addWidget(clear_button)
        row.addStretch()
        card_layout.addLayout(row)

        open_button.clicked.connect(self._page_open_history_file)
        folder_button.clicked.connect(self._page_open_history_folder)
        clear_button.clicked.connect(self._page_clear_history)
        self.history_page_list.itemDoubleClicked.connect(
            lambda _item: self._page_open_history_file()
        )
        layout.addWidget(card, 1)
        return page

    def _build_queue_page(self) -> QWidget:
        page, layout = self._make_section_page(
            "⇅  Очередь",
            "Подготовь несколько Shorts и отрендери их последовательно.",
        )
        card = self._make_card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 20)
        card_layout.setSpacing(14)

        self.queue_summary_label = QLabel("0 заданий")
        self.queue_summary_label.setObjectName("mutedText")
        card_layout.addWidget(self.queue_summary_label)

        self.queue_page_list = QListWidget()
        self.queue_page_list.setObjectName("libraryList")
        card_layout.addWidget(self.queue_page_list, 1)

        row = QHBoxLayout()
        add_button = QPushButton("Добавить текущий")
        remove_button = QPushButton("Удалить")
        clear_button = QPushButton("Очистить")
        start_button = QPushButton("Запустить очередь")
        start_button.setObjectName("accentButton")
        row.addWidget(add_button)
        row.addWidget(remove_button)
        row.addWidget(clear_button)
        row.addStretch()
        row.addWidget(start_button)
        card_layout.addLayout(row)

        add_button.clicked.connect(self._page_add_queue_item)
        remove_button.clicked.connect(self._page_remove_queue_item)
        clear_button.clicked.connect(self._page_clear_queue)
        start_button.clicked.connect(self._page_start_queue)
        layout.addWidget(card, 1)
        return page

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
            "◷  История",
            "⇅  Очередь",
        )

        self.nav_buttons = []

        for index, text in enumerate(navigation):
            button = QPushButton(text)
            button.setObjectName(
                "navButtonActive"
                if index == 0
                else "navButton"
            )
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setProperty("pageIndex", index)
            self.nav_buttons.append(button)
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
        card.setMinimumHeight(225)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            22,
            18,
            22,
            16,
        )
        layout.setSpacing(8)

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
        self.story_input.setFixedHeight(96)
        self.story_input.textChanged.connect(
            self._update_character_count
        )

        actions = QHBoxLayout()
        actions.setContentsMargins(
            0,
            6,
            0,
            0,
        )
        actions.setSpacing(10)

        clear_button = QPushButton(
            "⌫  Очистить"
        )
        clear_button.setObjectName(
            "storyActionButton"
        )
        clear_button.setFixedSize(
            118,
            32,
        )
        clear_button.clicked.connect(
            self.story_input.clear
        )

        example_button = QPushButton(
            "✦  Вставить пример"
        )
        example_button.setObjectName(
            "storyActionButton"
        )
        example_button.setFixedSize(
            168,
            32,
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
        self.gameplay_combo.currentIndexChanged.connect(
            self._refresh_video_preview
        )

        gameplay_row = QHBoxLayout()
        gameplay_row.setContentsMargins(0, 0, 0, 0)
        gameplay_row.setSpacing(7)

        self.gameplay_library_button = QPushButton("▦")
        self.gameplay_library_button.setObjectName(
            "gameplayLibraryButton"
        )
        self.gameplay_library_button.setToolTip(
            "Открыть библиотеку геймплея"
        )
        self.gameplay_library_button.setFixedSize(36, 34)
        self.gameplay_library_button.clicked.connect(
            self._open_gameplay_library
        )

        gameplay_row.addWidget(
            self.gameplay_combo,
            stretch=1,
        )
        gameplay_row.addWidget(
            self.gameplay_library_button
        )
        gameplay_card.layout().addLayout(gameplay_row)

        voice_card = self._setting_box(
            "🎙",
            "Озвучка",
        )
        self.voice_combo = QComboBox()
        self.voice_combo.setEditable(False)
        self.voice_combo.setMaxVisibleItems(10)
        self.voice_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.voice_combo.setMinimumContentsLength(14)

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

        voice_row = QHBoxLayout()
        voice_row.setContentsMargins(0, 0, 0, 0)
        voice_row.setSpacing(7)

        self.voice_preview_button = QPushButton("▶")
        self.voice_preview_button.setObjectName(
            "voicePreviewButton"
        )
        self.voice_preview_button.setToolTip(
            "Прослушать выбранный голос"
        )
        self.voice_preview_button.setFixedSize(
            36,
            34,
        )
        self.voice_preview_button.clicked.connect(
            self._toggle_voice_preview
        )

        self.voice_combo.currentIndexChanged.connect(
            self._voice_changed
        )

        voice_row.addWidget(
            self.voice_combo,
            stretch=1,
        )
        voice_row.addWidget(
            self.voice_preview_button
        )

        voice_card.layout().addLayout(
            voice_row
        )

        music_card = self._setting_box(
            "♫",
            "Музыка",
        )
        self.music_combo = QComboBox()
        self.music_combo.currentIndexChanged.connect(
            self._music_combo_changed
        )

        music_row = QHBoxLayout()
        music_row.setContentsMargins(0, 0, 0, 0)
        music_row.setSpacing(7)

        self.music_preview_button = QPushButton("▶")
        self.music_preview_button.setObjectName(
            "musicPreviewButton"
        )
        self.music_preview_button.setToolTip(
            "Прослушать выбранную музыку"
        )
        self.music_preview_button.setFixedSize(
            36,
            34,
        )
        self.music_preview_button.clicked.connect(
            self._toggle_music_preview
        )

        music_row.addWidget(
            self.music_combo,
            stretch=1,
        )
        music_row.addWidget(
            self.music_preview_button
        )

        music_card.layout().addLayout(
            music_row
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
        self.music_volume_slider.valueChanged.connect(
            lambda value: self.music_preview_audio.setVolume(
                max(0.05, value / 100)
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

        export_row = QHBoxLayout()
        export_row.setSpacing(10)

        export_label = QLabel("Экспорт")
        export_label.setObjectName("mutedText")

        self.export_preset_combo = QComboBox()

        for preset_name, preset_data in EXPORT_PRESETS.items():
            self.export_preset_combo.addItem(
                preset_name,
                preset_data,
            )

        self.export_preset_combo.setCurrentIndex(0)

        export_row.addWidget(export_label)
        export_row.addWidget(
            self.export_preset_combo,
            1,
        )
        layout.addLayout(export_row)

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
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(10)

        self.generate_button = GlowButton(
            "✦  СОЗДАТЬ SHORT"
        )
        self.generate_button.clicked.connect(
            self._start_generation
        )

        self.cancel_button = QPushButton(
            "ОТМЕНИТЬ"
        )
        self.cancel_button.setObjectName(
            "cancelRenderButton"
        )
        self.cancel_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.cancel_button.setFixedWidth(112)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(
            self._cancel_generation
        )

        render_buttons = QHBoxLayout()
        render_buttons.setSpacing(9)
        render_buttons.addWidget(
            self.generate_button,
            1,
        )
        render_buttons.addWidget(
            self.cancel_button
        )

        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addLayout(render_buttons)

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
        preview.setFixedSize(220, 391)
        preview.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )

        # Кадры видео выводим в обычный QLabel через QVideoSink.
        # Так QLabel с субтитрами гарантированно рисуется ПОВЕРХ видео.
        self.preview_video = QLabel(preview)
        self.preview_video.setObjectName("previewVideo")
        self.preview_video.setGeometry(1, 1, 218, 389)
        self.preview_video.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.preview_video.setContentsMargins(0, 0, 0, 0)
        self.preview_video.setText("Выбери геймплей")

        self.preview_audio = QAudioOutput(self)
        self.preview_audio.setMuted(True)

        self.preview_sink = QVideoSink(self)
        self.preview_sink.videoFrameChanged.connect(
            self._update_video_frame
        )

        self.preview_player = QMediaPlayer(self)
        self.preview_player.setAudioOutput(self.preview_audio)
        self.preview_player.setVideoSink(self.preview_sink)
        self.preview_player.mediaStatusChanged.connect(
            self._handle_preview_media_status
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
        options_grid.setVerticalSpacing(3)
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

        font_label = QLabel("Шрифт")
        font_label.setObjectName("mutedText")

        self.preview_font = QComboBox()
        self.preview_font.addItems(
            (
                "Segoe UI",
                "Arial",
                "Verdana",
                "Georgia",
                "Impact",
            )
        )
        self.preview_font.currentIndexChanged.connect(
            self._update_preview_appearance
        )

        colors_label = QLabel("Цвета")
        colors_label.setObjectName("mutedText")

        colors_row = QHBoxLayout()
        colors_row.setContentsMargins(0, 0, 0, 0)
        colors_row.setSpacing(8)

        self.preview_text_color_button = QPushButton("Текст")
        self.preview_text_color_button.setObjectName(
            "subtitleColorButton"
        )
        self.preview_text_color_button.clicked.connect(
            self._choose_preview_text_color
        )

        self.preview_outline_color_button = QPushButton("Обводка")
        self.preview_outline_color_button.setObjectName(
            "subtitleColorButton"
        )
        self.preview_outline_color_button.clicked.connect(
            self._choose_preview_outline_color
        )

        colors_row.addWidget(
            self.preview_text_color_button
        )
        colors_row.addWidget(
            self.preview_outline_color_button
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

        options_grid.setRowMinimumHeight(4, 0)
        options_grid.addWidget(font_label, 5, 0)
        options_grid.addWidget(
            self.preview_font,
            5,
            1,
        )
        options_grid.addWidget(colors_label, 6, 0)
        options_grid.addLayout(
            colors_row,
            6,
            1,
        )

        self._update_subtitle_color_buttons()

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

    def _choose_preview_text_color(self) -> None:
        color = QColorDialog.getColor(
            QColor(self.preview_text_color),
            self,
            "Цвет текста субтитров",
        )

        if not color.isValid():
            return

        self.preview_text_color = color.name().upper()
        self._update_subtitle_color_buttons()
        self._update_preview_appearance()

    def _choose_preview_outline_color(self) -> None:
        color = QColorDialog.getColor(
            QColor(self.preview_outline_color),
            self,
            "Цвет обводки субтитров",
        )

        if not color.isValid():
            return

        self.preview_outline_color = color.name().upper()
        self._update_subtitle_color_buttons()
        self._update_preview_appearance()

    def _update_subtitle_color_buttons(self) -> None:
        if not hasattr(
            self,
            "preview_text_color_button",
        ):
            return

        self.preview_text_color_button.setStyleSheet(
            "QPushButton {"
            f"background: {self.preview_text_color};"
            "color: #111827;"
            "border-radius: 8px;"
            "font-weight: 700;"
            "}"
        )
        self.preview_outline_color_button.setStyleSheet(
            "QPushButton {"
            f"background: {self.preview_outline_color};"
            "color: white;"
            "border-radius: 8px;"
            "font-weight: 700;"
            "}"
        )

    def _update_preview_appearance(self) -> None:
        style_name = getattr(
            self,
            "_preview_style",
            "Glow",
        )
        font_size = self.preview_font_size.value()
        opacity = self.preview_opacity.value()
        alpha = int(255 * opacity / 100)
        font_name = (
            self.preview_font.currentText()
            if hasattr(self, "preview_font")
            else "Segoe UI"
        )
        color = self.preview_text_color
        outline = self.preview_outline_color

        if style_name == "Glow":
            background = f"rgba(28, 8, 70, {alpha})"
            border = f"2px solid {outline}"
            weight = 800
        elif style_name == "Bold":
            background = f"rgba(0, 0, 0, {alpha})"
            border = f"2px solid {outline}"
            weight = 900
        else:
            background = f"rgba(5, 8, 28, {alpha})"
            border = f"1px solid {outline}"
            weight = 700

        self.preview_text.setStyleSheet(
            f"""
            QLabel {{
                color: {color};
                font-family: "{font_name}";
                font-size: {font_size}px;
                font-weight: {weight};
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

            QListWidget#libraryList {
                background: rgba(7, 12, 35, 175);
                border: 1px solid rgba(112, 93, 220, 95);
                border-radius: 16px;
                padding: 8px;
                color: #f4f5ff;
                font-size: 14px;
                outline: none;
            }

            QListWidget#libraryList::item {
                min-height: 68px;
                padding: 10px 12px;
                margin: 3px;
                border-radius: 10px;
            }

            QListWidget#libraryList::item:hover {
                background: rgba(93, 74, 180, 75);
            }

            QListWidget#libraryList::item:selected {
                background: rgba(111, 76, 220, 125);
                border: 1px solid rgba(221, 107, 255, 120);
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

            QPushButton#gameplayLibraryButton {
                color: white;
                background: rgba(76, 29, 149, 115);
                border: 1px solid rgba(167, 139, 250, 105);
                border-radius: 9px;
                font-size: 16px;
                font-weight: 700;
                padding: 0;
            }

            QPushButton#gameplayLibraryButton:hover {
                background: rgba(109, 40, 217, 170);
                border-color: rgba(216, 180, 254, 170);
            }

            QPushButton#musicPreviewButton {
                color: white;
                background: rgba(14, 116, 144, 115);
                border: 1px solid rgba(34, 211, 238, 105);
                border-radius: 9px;
                font-size: 14px;
                font-weight: 700;
                padding: 0;
            }

            QPushButton#musicPreviewButton:hover {
                background: rgba(8, 145, 178, 170);
                border-color: rgba(103, 232, 249, 170);
            }

            QPushButton#musicPreviewButton:pressed {
                background: rgba(14, 116, 144, 210);
            }

            QPushButton#musicPreviewButton:disabled {
                color: rgba(255, 255, 255, 95);
                background: rgba(22, 78, 99, 60);
                border-color: rgba(103, 232, 249, 45);
            }

            QPushButton#voicePreviewButton {
                color: white;
                background: rgba(79, 70, 229, 120);
                border: 1px solid rgba(167, 139, 250, 120);
                border-radius: 9px;
                font-size: 14px;
                font-weight: 700;
                padding: 0;
            }

            QPushButton#voicePreviewButton:hover {
                background: rgba(124, 58, 237, 170);
                border-color: rgba(236, 72, 153, 170);
            }

            QPushButton#voicePreviewButton:pressed {
                background: rgba(67, 56, 202, 200);
            }

            QPushButton#voicePreviewButton:disabled {
                color: rgba(255, 255, 255, 150);
                background: rgba(49, 46, 129, 80);
            }

            QPushButton#cancelRenderButton {
                color: #ffd7df;
                background: rgba(126, 34, 61, 105);
                border: 1px solid rgba(251, 113, 133, 115);
                border-radius: 12px;
                padding: 8px 10px;
                font-size: 12px;
                font-weight: 800;
            }

            QPushButton#cancelRenderButton:hover {
                background: rgba(159, 18, 57, 150);
                border-color: rgba(253, 164, 175, 180);
            }

            QPushButton#storyActionButton {
                color: #d8dcf2;
                background: rgba(63, 53, 116, 90);
                border: 1px solid rgba(126, 106, 255, 70);
                border-radius: 9px;
                padding: 3px 10px;
                font-size: 13px;
                font-weight: 650;
            }

            QPushButton#storyActionButton:hover {
                background: rgba(124, 58, 237, 80);
                border-color: rgba(216, 180, 254, 130);
            }

            QPushButton#storyActionButton:pressed {
                background: rgba(79, 70, 229, 110);
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

            QLabel#previewVideo {
                color: rgba(255, 255, 255, 105);
                background: #080d1d;
                border-radius: 25px;
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
                min-height: 26px;
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

    def _refresh_video_preview(
        self,
        category: str | None = None,
    ) -> None:
        """Запускает выбранный gameplay прямо в окне Preview."""

        if not hasattr(self, "preview_player"):
            return

        if not hasattr(self, "gameplay_combo"):
            return

        category = self.gameplay_combo.currentText().strip()
        selected_value = self.gameplay_combo.currentData()

        if (
            not category
            or category in {
                "Выбрать",
                "Категории не найдены",
            }
            or not self.gameplay_combo.isEnabled()
        ):
            self.preview_gameplay_path = None
            self.preview_player.stop()
            self.preview_player.setSource(QUrl())
            self.preview_video.setPixmap(QPixmap())
            self.preview_video.setText("Выбери геймплей")
            return

        try:
            if (
                isinstance(selected_value, str)
                and Path(selected_value).is_file()
            ):
                gameplay_path = Path(selected_value).resolve()
            else:
                gameplay_path = GameplayLibrary().get_random_video(
                    category
                )
        except (FileNotFoundError, ValueError):
            self.preview_gameplay_path = None
            self.preview_player.stop()
            self.preview_player.setSource(QUrl())
            return

        self.preview_gameplay_path = gameplay_path
        self.preview_player.stop()
        self.preview_player.setSource(
            QUrl.fromLocalFile(str(gameplay_path.resolve()))
        )
        self.preview_player.play()

    def _update_video_frame(self, frame) -> None:
        """Рисует текущий видеокадр с округлением углов."""

        if not frame.isValid():
            return

        image = frame.toImage()

        if image.isNull():
            return

        target_size = self.preview_video.size()

        scaled = QPixmap.fromImage(image).scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )

        rounded = QPixmap(target_size)
        rounded.fill(Qt.GlobalColor.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        clip_path = QPainterPath()
        clip_path.addRoundedRect(
            0,
            0,
            target_size.width(),
            target_size.height(),
            24,
            24,
        )

        painter.setClipPath(clip_path)

        source_x = max(
            0,
            (scaled.width() - target_size.width()) // 2,
        )
        source_y = max(
            0,
            (scaled.height() - target_size.height()) // 2,
        )

        painter.drawPixmap(
            0,
            0,
            scaled,
            source_x,
            source_y,
            target_size.width(),
            target_size.height(),
        )
        painter.end()

        self.preview_video.setText("")
        self.preview_video.setPixmap(rounded)

    def _handle_preview_media_status(
        self,
        status: QMediaPlayer.MediaStatus,
    ) -> None:
        """Зацикливает gameplay без участия FFmpeg."""

        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.preview_player.setPosition(0)
            self.preview_player.play()

    def _load_gameplay_categories(self) -> None:
        categories = (
            GameplayLibrary().list_categories()
        )

        self.gameplay_combo.blockSignals(True)
        self.gameplay_combo.clear()

        if not categories:
            self.gameplay_combo.addItem(
                "Категории не найдены"
            )
            self.gameplay_combo.setEnabled(False)
            self.gameplay_combo.blockSignals(False)
            return

        self.gameplay_combo.addItem("Выбрать", None)

        for category in categories:
            self.gameplay_combo.addItem(
                category,
                category,
            )

        self.gameplay_combo.setCurrentIndex(0)
        self.gameplay_combo.setEnabled(True)
        self.gameplay_combo.blockSignals(False)

        # При запуске ничего не воспроизводим.
        self._refresh_video_preview("Выбрать")

    def _open_gameplay_library(self) -> None:
        """Управление категориями и конкретными gameplay-файлами."""

        library = GameplayLibrary()

        dialog = QDialog(self)
        dialog.setWindowTitle("Библиотека геймплея")
        dialog.setMinimumSize(650, 460)

        layout = QVBoxLayout(dialog)

        title = QLabel("Gameplay Library")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        content = QHBoxLayout()

        categories = QListWidget()
        videos = QListWidget()

        content.addWidget(categories, 2)
        content.addWidget(videos, 3)
        layout.addLayout(content, 1)

        bottom = QHBoxLayout()
        add_category = QPushButton("Новая категория")
        add_video = QPushButton("Добавить видео")
        delete_button = QPushButton("Удалить")
        select_button = QPushButton("Выбрать видео")
        close_button = QPushButton("Закрыть")

        bottom.addWidget(add_category)
        bottom.addWidget(add_video)
        bottom.addWidget(delete_button)
        bottom.addStretch()
        bottom.addWidget(select_button)
        bottom.addWidget(close_button)
        layout.addLayout(bottom)

        def refresh_categories(select_name: str | None = None) -> None:
            categories.clear()
            names = library.list_categories()
            categories.addItems(names)

            if select_name:
                matches = categories.findItems(
                    select_name,
                    Qt.MatchFlag.MatchExactly,
                )
                if matches:
                    categories.setCurrentItem(matches[0])
                    return

            if categories.count():
                categories.setCurrentRow(0)

        def refresh_videos() -> None:
            videos.clear()
            item = categories.currentItem()

            if item is None:
                return

            for path in library.list_videos(item.text()):
                list_item = QListWidgetItem(path.name)
                list_item.setData(
                    Qt.ItemDataRole.UserRole,
                    str(path),
                )
                list_item.setToolTip(str(path))
                videos.addItem(list_item)

        def create_category() -> None:
            name, ok = QInputDialog.getText(
                dialog,
                "Новая категория",
                "Название:",
            )
            if not ok:
                return

            try:
                library.create_category(name)
            except ValueError as error:
                QMessageBox.warning(
                    dialog,
                    "Ошибка",
                    str(error),
                )
                return

            refresh_categories(name.strip())
            self._load_gameplay_categories()

        def import_video() -> None:
            category_item = categories.currentItem()

            if category_item is None:
                QMessageBox.warning(
                    dialog,
                    "Нет категории",
                    "Сначала создай или выбери категорию.",
                )
                return

            filenames, _ = QFileDialog.getOpenFileNames(
                dialog,
                "Добавить gameplay",
                "",
                "Video (*.mp4 *.mov *.avi *.mkv *.webm)",
            )

            for filename in filenames:
                try:
                    library.add_video(
                        category_item.text(),
                        Path(filename),
                    )
                except (OSError, ValueError) as error:
                    QMessageBox.warning(
                        dialog,
                        "Не удалось добавить видео",
                        str(error),
                    )

            refresh_videos()
            self._load_gameplay_categories()

        def remove_selected() -> None:
            video_item = videos.currentItem()

            if video_item is not None:
                path = Path(
                    str(
                        video_item.data(
                            Qt.ItemDataRole.UserRole
                        )
                    )
                )
                answer = QMessageBox.question(
                    dialog,
                    "Удалить видео?",
                    f"Удалить {path.name} из библиотеки?",
                )
                if answer == QMessageBox.StandardButton.Yes:
                    library.delete_video(path)
                    refresh_videos()
                return

            category_item = categories.currentItem()

            if category_item is None:
                return

            answer = QMessageBox.question(
                dialog,
                "Удалить категорию?",
                f"Удалить категорию «{category_item.text()}» "
                "и все видео внутри неё?",
            )

            if answer == QMessageBox.StandardButton.Yes:
                library.delete_category(
                    category_item.text()
                )
                refresh_categories()
                self._load_gameplay_categories()

        def select_video() -> None:
            item = videos.currentItem()

            if item is None:
                return

            path = Path(
                str(
                    item.data(
                        Qt.ItemDataRole.UserRole
                    )
                )
            ).resolve()

            label = (
                f"🎬 {path.parent.name} / {path.name}"
            )

            existing = self.gameplay_combo.findData(
                str(path)
            )

            self.gameplay_combo.blockSignals(True)

            if existing < 0:
                self.gameplay_combo.addItem(
                    label,
                    str(path),
                )
                existing = self.gameplay_combo.count() - 1

            self.gameplay_combo.setCurrentIndex(existing)
            self.gameplay_combo.blockSignals(False)

            self._refresh_video_preview()
            dialog.accept()

        categories.currentItemChanged.connect(
            lambda _current, _previous: refresh_videos()
        )
        add_category.clicked.connect(create_category)
        add_video.clicked.connect(import_video)
        delete_button.clicked.connect(remove_selected)
        select_button.clicked.connect(select_video)
        close_button.clicked.connect(dialog.reject)
        videos.itemDoubleClicked.connect(
            lambda _item: select_video()
        )

        refresh_categories()
        dialog.exec()

    def _voice_changed(self) -> None:
        """Останавливает preview при выборе другого голоса."""

        if (
            self.voice_preview_player.playbackState()
            != QMediaPlayer.PlaybackState.StoppedState
        ):
            self.voice_preview_player.stop()

        if hasattr(self, "voice_preview_button"):
            self.voice_preview_button.setText("▶")

    def _toggle_voice_preview(self) -> None:
        """Генерирует и проигрывает короткий пример голоса."""

        if (
            self.voice_preview_player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        ):
            self.voice_preview_player.stop()
            return

        if (
            self.voice_preview_worker is not None
            and self.voice_preview_worker.isRunning()
        ):
            return

        voice = self.voice_combo.currentData()

        if not voice:
            return

        if str(voice).startswith("ru-"):
            sample_text = (
                "Привет! Так будет звучать "
                "озвучка твоего короткого видео."
            )
        else:
            sample_text = (
                "Hi! This is how your short video "
                "voiceover will sound."
            )

        rate = (
            f"{self.voice_rate_slider.value():+d}%"
        )

        self.voice_preview_button.setEnabled(False)
        self.voice_preview_button.setText("…")
        self.voice_combo.setEnabled(False)

        self.voice_preview_worker = VoicePreviewWorker(
            text=sample_text,
            voice=str(voice),
            rate=rate,
            parent=self,
        )
        self.voice_preview_worker.completed.connect(
            self._voice_preview_ready
        )
        self.voice_preview_worker.failed.connect(
            self._voice_preview_failed
        )
        self.voice_preview_worker.finished.connect(
            self._voice_preview_worker_finished
        )
        self.voice_preview_worker.start()

    def _voice_preview_ready(
        self,
        audio_path: str,
    ) -> None:
        """Запускает готовый MP3 preview."""

        self.voice_preview_player.setSource(
            QUrl.fromLocalFile(
                str(Path(audio_path).resolve())
            )
        )
        self.voice_preview_player.play()

    def _voice_preview_failed(
        self,
        error_message: str,
    ) -> None:
        QMessageBox.warning(
            self,
            "Не удалось прослушать голос",
            error_message,
        )

    def _voice_preview_worker_finished(self) -> None:
        self.voice_preview_button.setEnabled(True)
        self.voice_combo.setEnabled(True)

        if (
            self.voice_preview_player.playbackState()
            != QMediaPlayer.PlaybackState.PlayingState
        ):
            self.voice_preview_button.setText("▶")

        if self.voice_preview_worker is not None:
            self.voice_preview_worker.deleteLater()
            self.voice_preview_worker = None

    def _voice_preview_state_changed(
        self,
        state: QMediaPlayer.PlaybackState,
    ) -> None:
        if not hasattr(
            self,
            "voice_preview_button",
        ):
            return

        if (
            state
            == QMediaPlayer.PlaybackState.PlayingState
        ):
            self.voice_preview_button.setText("■")
            self.voice_preview_button.setToolTip(
                "Остановить preview"
            )
        else:
            self.voice_preview_button.setText("▶")
            self.voice_preview_button.setToolTip(
                "Прослушать выбранный голос"
            )

    def _connect_sidebar_actions(self) -> None:
        """Переключает страницы внутри главного окна."""
        for button in self.nav_buttons:
            page_index = int(button.property("pageIndex"))
            button.clicked.connect(
                lambda _checked=False, index=page_index:
                self._switch_page(index)
            )
        self._switch_page(0)

    def _switch_page(self, index: int) -> None:
        if not 0 <= index < self.page_stack.count():
            return

        self.page_stack.setCurrentIndex(index)

        for button_index, button in enumerate(self.nav_buttons):
            button.setObjectName(
                "navButtonActive"
                if button_index == index
                else "navButton"
            )
            button.style().unpolish(button)
            button.style().polish(button)

        if index == 1:
            self._refresh_projects_page()
        elif index == 3:
            self._refresh_history_page()
        elif index == 4:
            self._refresh_queue_page()

    def _refresh_projects_page(self) -> None:
        self.projects_page_list.clear()

        for name in self.project_storage.list_projects():
            try:
                info = self.project_storage.describe(name)
            except (OSError, ValueError, json.JSONDecodeError):
                self.projects_page_list.addItem(name)
                continue

            item = QListWidgetItem(
                f"{info['name']}\n"
                f"Изменён: {info['modified_at']}   •   "
                f"Gameplay: {info['gameplay']}   •   "
                f"Голос: {info['voice']}\n"
                f"{info['story_preview'] or 'Без текста'}"
            )
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.projects_page_list.addItem(item)

    def _page_save_project(self) -> None:
        self._save_project()
        self._refresh_projects_page()

    def _page_open_project(self) -> None:
        item = self.projects_page_list.currentItem()
        if item is None:
            return
        project_name = (
            item.data(Qt.ItemDataRole.UserRole)
            or item.text().splitlines()[0]
        )

        try:
            data = self.project_storage.load(project_name)
            self._apply_project_data(data)
            self.current_project_name = project_name
        except (OSError, ValueError) as error:
            QMessageBox.warning(
                self, "Не удалось открыть", str(error)
            )
            return
        self._switch_page(0)
        self.status_label.setText(
            f"●  Проект «{project_name}» открыт"
        )

    def _page_delete_project(self) -> None:
        item = self.projects_page_list.currentItem()
        if item is None:
            return
        project_name = (
            item.data(Qt.ItemDataRole.UserRole)
            or item.text().splitlines()[0]
        )

        answer = QMessageBox.question(
            self,
            "Удалить проект?",
            f"Удалить «{project_name}»?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.project_storage.delete(project_name)
        if self.current_project_name == project_name:
            self.current_project_name = None
        self._refresh_projects_page()

    def _page_apply_template(self) -> None:
        index = self.templates_page_list.currentRow()
        if index < 0:
            return
        name = list(TEMPLATE_PRESETS.keys())[index]
        self._apply_template(name)
        self._switch_page(0)

    def _refresh_history_page(self) -> None:
        self.history_page_list.clear()

        for entry in self.history_storage.load():
            created = str(entry.get("created_at", "")).replace("T", " ")
            path = Path(str(entry.get("output_path", "")))
            preview = entry.get("story_preview", "")
            duration = entry.get("duration_seconds")
            size_bytes = int(entry.get("size_bytes", 0) or 0)
            preset = entry.get("export_preset", "")

            duration_text = (
                f"{float(duration):.1f} сек"
                if isinstance(duration, (int, float))
                else "длительность —"
            )
            size_text = (
                f"{size_bytes / 1024 / 1024:.1f} MB"
                if size_bytes > 0
                else "размер —"
            )

            self.history_page_list.addItem(
                f"{path.name}   •   {created}\n"
                f"{duration_text}   •   {size_text}"
                + (f"   •   {preset}" if preset else "")
                + f"\n{preview}"
            )

    def _selected_history_entry(self) -> dict | None:
        index = self.history_page_list.currentRow()
        data = self.history_storage.load()
        if 0 <= index < len(data):
            return data[index]
        return None

    def _page_open_history_file(self) -> None:
        entry = self._selected_history_entry()
        if not entry:
            return
        path = Path(str(entry.get("output_path", ""))).resolve()
        if path.is_file():
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(path))
            )

    def _page_open_history_folder(self) -> None:
        entry = self._selected_history_entry()
        if not entry:
            return
        path = Path(str(entry.get("output_path", ""))).resolve()
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(path.parent))
        )

    def _page_clear_history(self) -> None:
        answer = QMessageBox.question(
            self,
            "Очистить историю?",
            "Видео останутся на диске. "
            "Удалится только список истории.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.history_storage.clear()
            self._refresh_history_page()

    def _refresh_queue_page(self) -> None:
        self.queue_page_list.clear()

        total = len(self.render_queue)
        done = sum(
            1 for item in self.render_queue
            if item.get("_status") == "Готово"
        )
        self.queue_summary_label.setText(
            f"{total} заданий   •   готово {done}/{total}"
        )

        for number, entry in enumerate(self.render_queue, start=1):
            preview = " ".join(
                str(entry.get("story_text", "")).split()
            )[:90]
            status = str(entry.get("_status", "Ожидает"))
            progress = int(entry.get("_progress", 0) or 0)
            self.queue_page_list.addItem(
                f"{number}. [{status}] {progress}%\n"
                f"{preview or 'Без текста'}"
            )

    def _page_add_queue_item(self) -> None:
        data = self._collect_project_data()
        if not str(data.get("story_text", "")).strip():
            QMessageBox.warning(
                self,
                "Нет текста",
                "Сначала добавь текст истории на Главной.",
            )
            return
        data["output_path"] = str(self.output_path)
        data["_status"] = "Ожидает"
        data["_progress"] = 0
        self.render_queue.append(data)
        self.queue_storage.save(self.render_queue)
        self._refresh_queue_page()

    def _page_remove_queue_item(self) -> None:
        index = self.queue_page_list.currentRow()
        if 0 <= index < len(self.render_queue):
            self.render_queue.pop(index)
            self.queue_storage.save(self.render_queue)
            self._refresh_queue_page()

    def _page_clear_queue(self) -> None:
        if not self.render_queue:
            return
        answer = QMessageBox.question(
            self,
            "Очистить очередь?",
            "Удалить все задания из очереди?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.render_queue.clear()
        self.queue_storage.save([])
        self._refresh_queue_page()

    def _page_start_queue(self) -> None:
        if self.worker is not None:
            QMessageBox.warning(
                self,
                "Рендер уже идёт",
                "Дождись текущего рендера или отмени его.",
            )
            return
        if not self.render_queue:
            QMessageBox.information(
                self,
                "Очередь пуста",
                "Добавь хотя бы один Short.",
            )
            return
        self._queue_running = True
        self._queue_failures = 0
        self._switch_page(0)
        self._start_next_queue_item()

    def _apply_saved_app_settings(self) -> None:
        voice = self.app_settings.get("default_voice")
        index = self.voice_combo.findData(voice)
        if index >= 0:
            self.voice_combo.setCurrentIndex(index)

        self.voice_rate_slider.setValue(
            int(self.app_settings.get("default_voice_rate", 0))
        )
        self.music_volume_slider.setValue(
            int(self.app_settings.get("default_music_volume", 12))
        )

        output_dir = Path(
            str(self.app_settings.get("output_directory", "output"))
        )
        self.output_path = output_dir / "final_short.mp4"
        self.output_label.setText(str(self.output_path))

    def _open_templates_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Шаблоны")
        dialog.setMinimumSize(500, 390)

        layout = QVBoxLayout(dialog)
        title = QLabel("Готовые шаблоны")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        hint = QLabel(
            "Выбери пресет — настройки применятся к текущему Short."
        )
        hint.setObjectName("mutedText")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        template_list = QListWidget()
        for name, preset in TEMPLATE_PRESETS.items():
            template_list.addItem(
                f"{name} — {preset['description']}"
            )
        layout.addWidget(template_list, 1)

        row = QHBoxLayout()
        apply_button = QPushButton("Применить")
        close_button = QPushButton("Закрыть")
        row.addWidget(apply_button)
        row.addStretch()
        row.addWidget(close_button)
        layout.addLayout(row)

        def apply_selected() -> None:
            i = template_list.currentRow()
            if i < 0:
                return
            name = list(TEMPLATE_PRESETS.keys())[i]
            self._apply_template(name)
            dialog.accept()

        apply_button.clicked.connect(apply_selected)
        close_button.clicked.connect(dialog.reject)
        template_list.itemDoubleClicked.connect(
            lambda _item: apply_selected()
        )
        dialog.exec()

    def _apply_template(self, name: str) -> None:
        preset = TEMPLATE_PRESETS[name]
        style = str(preset["subtitle_style"])
        self._preview_style = style

        for button in self.preview_style_buttons:
            active = button.text() == style
            button.setChecked(active)
            button.setObjectName(
                "subtitleStyleActive" if active else "subtitleStyle"
            )
            button.style().unpolish(button)
            button.style().polish(button)

        self.preview_font_size.setValue(int(preset["subtitle_font_size"]))

        index = self.preview_position.findText(
            str(preset["subtitle_position"])
        )
        if index >= 0:
            self.preview_position.setCurrentIndex(index)

        self.preview_opacity.setValue(int(preset["subtitle_opacity"]))
        self.voice_rate_slider.setValue(int(preset["voice_rate"]))
        self.music_volume_slider.setValue(int(preset["music_volume"]))
        self.subtitles_switch.setChecked(bool(preset["subtitles"]))
        self._update_preview_appearance()
        self.status_label.setText(f"●  Шаблон «{name}» применён")

    def _open_music_folder(self) -> None:
        music_dir = Path("assets/music").resolve()
        music_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(music_dir))
        )

    def _open_settings_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Настройки")
        dialog.setMinimumWidth(480)

        layout = QVBoxLayout(dialog)

        title = QLabel("Настройки приложения")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        output_label = QLabel("Папка для готовых видео")
        output_label.setObjectName("mutedText")
        layout.addWidget(output_label)

        selected_output = {
            "path": str(
                self.app_settings.get("output_directory", "output")
            )
        }

        output_row = QHBoxLayout()
        output_value = QLabel(selected_output["path"])
        output_value.setObjectName("pathLabel")
        browse_button = QPushButton("Изменить")
        output_row.addWidget(output_value, 1)
        output_row.addWidget(browse_button)
        layout.addLayout(output_row)

        voice_label = QLabel("Голос по умолчанию")
        voice_label.setObjectName("mutedText")
        layout.addWidget(voice_label)

        voice_combo = QComboBox()
        for label, voice_id in VOICE_OPTIONS.items():
            voice_combo.addItem(label, voice_id)

        index = voice_combo.findData(
            self.app_settings.get("default_voice")
        )
        if index >= 0:
            voice_combo.setCurrentIndex(index)
        layout.addWidget(voice_combo)

        rate_label = QLabel("Скорость голоса по умолчанию")
        rate_label.setObjectName("mutedText")
        layout.addWidget(rate_label)

        rate_slider = QSlider(Qt.Orientation.Horizontal)
        rate_slider.setRange(-50, 100)
        rate_slider.setValue(
            int(self.app_settings.get("default_voice_rate", 0))
        )
        layout.addWidget(rate_slider)

        music_label = QLabel("Громкость музыки по умолчанию")
        music_label.setObjectName("mutedText")
        layout.addWidget(music_label)

        music_slider = QSlider(Qt.Orientation.Horizontal)
        music_slider.setRange(0, 100)
        music_slider.setValue(
            int(self.app_settings.get("default_music_volume", 12))
        )
        layout.addWidget(music_slider)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(buttons)

        def browse_output() -> None:
            directory = QFileDialog.getExistingDirectory(
                dialog,
                "Папка для готовых видео",
                str(Path(selected_output["path"]).resolve()),
            )
            if directory:
                selected_output["path"] = directory
                output_value.setText(directory)

        def save_settings() -> None:
            new_settings = {
                "output_directory": selected_output["path"],
                "default_voice": voice_combo.currentData(),
                "default_voice_rate": rate_slider.value(),
                "default_music_volume": music_slider.value(),
            }
            self.settings_storage.save(new_settings)
            self.app_settings = new_settings
            self._apply_saved_app_settings()
            dialog.accept()

        browse_button.clicked.connect(browse_output)
        buttons.accepted.connect(save_settings)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()

    def _open_history_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("История рендеров")
        dialog.setMinimumSize(560, 420)

        layout = QVBoxLayout(dialog)
        title = QLabel("Готовые Shorts")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        items = QListWidget()

        def refresh() -> None:
            items.clear()
            for entry in self.history_storage.load():
                created = entry.get("created_at", "")
                path = entry.get("output_path", "")
                preview = entry.get("story_preview", "")
                items.addItem(
                    f"{created}   •   {Path(path).name}\n{preview}"
                )

        refresh()
        layout.addWidget(items, 1)

        row = QHBoxLayout()
        open_button = QPushButton("Открыть файл")
        folder_button = QPushButton("Открыть папку")
        clear_button = QPushButton("Очистить историю")
        close_button = QPushButton("Закрыть")
        row.addWidget(open_button)
        row.addWidget(folder_button)
        row.addWidget(clear_button)
        row.addStretch()
        row.addWidget(close_button)
        layout.addLayout(row)

        def selected_entry() -> dict | None:
            index = items.currentRow()
            data = self.history_storage.load()
            if 0 <= index < len(data):
                return data[index]
            return None

        def open_file() -> None:
            entry = selected_entry()
            if not entry:
                return
            path = Path(str(entry.get("output_path", ""))).resolve()
            if path.is_file():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

        def open_folder() -> None:
            entry = selected_entry()
            if not entry:
                return
            path = Path(str(entry.get("output_path", ""))).resolve()
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))

        def clear_history() -> None:
            answer = QMessageBox.question(
                dialog,
                "Очистить историю?",
                "Файлы видео не удалятся. Удалится только список.",
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.history_storage.clear()
                refresh()

        open_button.clicked.connect(open_file)
        folder_button.clicked.connect(open_folder)
        clear_button.clicked.connect(clear_history)
        close_button.clicked.connect(dialog.reject)
        items.itemDoubleClicked.connect(lambda _item: open_file())
        dialog.exec()

    def _open_queue_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Очередь рендера")
        dialog.setMinimumSize(560, 430)

        layout = QVBoxLayout(dialog)
        title = QLabel("Очередь Shorts")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        hint = QLabel(
            "Добавляй несколько настроенных Shorts и запускай их по очереди."
        )
        hint.setObjectName("mutedText")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        items = QListWidget()

        def refresh() -> None:
            items.clear()
            for number, entry in enumerate(self.render_queue, start=1):
                preview = " ".join(
                    str(entry.get("story_text", "")).split()
                )[:75]
                items.addItem(f"{number}. {preview or 'Без текста'}")

        refresh()
        layout.addWidget(items, 1)

        row = QHBoxLayout()
        add_button = QPushButton("Добавить текущий")
        remove_button = QPushButton("Удалить")
        start_button = QPushButton("Запустить очередь")
        close_button = QPushButton("Закрыть")
        row.addWidget(add_button)
        row.addWidget(remove_button)
        row.addWidget(start_button)
        row.addStretch()
        row.addWidget(close_button)
        layout.addLayout(row)

        def add_current() -> None:
            data = self._collect_project_data()
            if not str(data.get("story_text", "")).strip():
                QMessageBox.warning(dialog, "Нет текста", "Сначала добавь текст истории.")
                return
            data["output_path"] = str(self.output_path)
            self.render_queue.append(data)
            self.queue_storage.save(self.render_queue)
            refresh()

        def remove_selected() -> None:
            index = items.currentRow()
            if 0 <= index < len(self.render_queue):
                self.render_queue.pop(index)
                self.queue_storage.save(self.render_queue)
                refresh()

        def start_queue() -> None:
            if self.worker is not None:
                QMessageBox.warning(dialog, "Рендер уже идёт", "Дождись текущего рендера.")
                return
            if not self.render_queue:
                QMessageBox.information(dialog, "Очередь пуста", "Добавь хотя бы один Short.")
                return
            self._queue_running = True
            self._queue_failures = 0
            dialog.accept()
            self._start_next_queue_item()

        add_button.clicked.connect(add_current)
        remove_button.clicked.connect(remove_selected)
        start_button.clicked.connect(start_queue)
        close_button.clicked.connect(dialog.reject)
        dialog.exec()

    def _start_next_queue_item(self) -> None:
        if not self.render_queue:
            self._queue_running = False
            self.queue_storage.save([])

            if self._queue_failures:
                message = (
                    "Очередь завершена.\n\n"
                    f"Не удалось создать: "
                    f"{self._queue_failures}."
                )
            else:
                message = (
                    "Все Shorts из очереди "
                    "отрендерены."
                )

            QMessageBox.information(
                self,
                "Очередь готова",
                message,
            )
            return

        data = self.render_queue[0]
        data["_status"] = "Подготовка"
        data["_progress"] = 1
        self.queue_storage.save(self.render_queue)
        if hasattr(self, "queue_page_list"):
            self._refresh_queue_page()

        self._apply_project_data(data)

        output_dir = Path(
            str(self.app_settings.get("output_directory", "output"))
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        index = 1
        while (output_dir / f"short_{index:03d}.mp4").exists():
            index += 1
        self.output_path = output_dir / f"short_{index:03d}.mp4"
        self.output_label.setText(str(self.output_path))
        self._queue_current_story = str(data.get("story_text", ""))
        self._start_generation()

    def _collect_project_data(self) -> dict:
        """Собирает все основные настройки текущего Short."""

        return {
            "version": 1,
            "story_text": self.story_input.toPlainText(),
            "gameplay": self.gameplay_combo.currentText(),
            "gameplay_value": self.gameplay_combo.currentData(),
            "voice": self.voice_combo.currentData(),
            "voice_rate": self.voice_rate_slider.value(),
            "music": self.music_combo.currentData(),
            "music_volume": self.music_volume_slider.value(),
            "subtitles": self.subtitles_switch.isChecked(),
            "subtitle_style": getattr(
                self, "_preview_style", "Glow"
            ),
            "subtitle_font_size": self.preview_font_size.value(),
            "subtitle_position": self.preview_position.currentText(),
            "subtitle_opacity": self.preview_opacity.value(),
            "subtitle_font": self.preview_font.currentText(),
            "subtitle_text_color": self.preview_text_color,
            "subtitle_outline_color": self.preview_outline_color,
            "export_preset": self.export_preset_combo.currentText(),
        }

    def _apply_project_data(self, data: dict) -> None:
        """Восстанавливает сохранённые настройки в GUI."""

        self.story_input.setPlainText(
            str(data.get("story_text", ""))
        )

        gameplay = str(data.get("gameplay", "Выбрать"))
        gameplay_value = data.get("gameplay_value")

        index = -1

        if (
            isinstance(gameplay_value, str)
            and Path(gameplay_value).is_file()
        ):
            index = self.gameplay_combo.findData(
                gameplay_value
            )

            if index < 0:
                self.gameplay_combo.addItem(
                    gameplay,
                    gameplay_value,
                )
                index = self.gameplay_combo.count() - 1

        if index < 0:
            index = self.gameplay_combo.findText(gameplay)

        if index >= 0:
            self.gameplay_combo.setCurrentIndex(index)

        voice = data.get("voice")
        index = self.voice_combo.findData(voice)
        if index >= 0:
            self.voice_combo.setCurrentIndex(index)

        self.voice_rate_slider.setValue(
            int(data.get("voice_rate", 0))
        )

        music = data.get("music")
        index = self.music_combo.findData(music)
        if index < 0 and isinstance(music, str) and Path(music).is_file():
            self.music_combo.insertItem(
                max(0, self.music_combo.count() - 1),
                Path(music).stem,
                music,
            )
            index = self.music_combo.findData(music)
        if index >= 0:
            self.music_combo.setCurrentIndex(index)
        else:
            self.music_combo.setCurrentIndex(0)

        self.music_volume_slider.setValue(
            int(data.get("music_volume", 12))
        )
        self.subtitles_switch.setChecked(
            bool(data.get("subtitles", True))
        )

        style = str(data.get("subtitle_style", "Glow"))
        self._preview_style = style
        for button in getattr(
            self, "preview_style_buttons", []
        ):
            button.setChecked(
                button.text().strip() == style
            )

        self.preview_font_size.setValue(
            int(data.get("subtitle_font_size", 20))
        )

        position = str(
            data.get("subtitle_position", "Ниже")
        )
        index = self.preview_position.findText(position)
        if index >= 0:
            self.preview_position.setCurrentIndex(index)

        self.preview_opacity.setValue(
            int(data.get("subtitle_opacity", 72))
        )

        font_name = str(
            data.get("subtitle_font", "Segoe UI")
        )
        index = self.preview_font.findText(font_name)
        if index >= 0:
            self.preview_font.setCurrentIndex(index)

        self.preview_text_color = str(
            data.get(
                "subtitle_text_color",
                "#FFFFFF",
            )
        )
        self.preview_outline_color = str(
            data.get(
                "subtitle_outline_color",
                "#E66BFF",
            )
        )
        self._update_subtitle_color_buttons()

        export_preset = str(
            data.get(
                "export_preset",
                "Full HD · 30 FPS",
            )
        )
        index = self.export_preset_combo.findText(
            export_preset
        )
        if index >= 0:
            self.export_preset_combo.setCurrentIndex(
                index
            )

        self._update_preview_appearance()

    def _save_project(self) -> None:
        default_name = (
            self.current_project_name
            or "Мой Short"
        )
        name, ok = QInputDialog.getText(
            self,
            "Сохранить проект",
            "Название проекта:",
            text=default_name,
        )
        if not ok:
            return

        try:
            self.project_storage.save(
                name,
                self._collect_project_data(),
            )
        except (ValueError, OSError) as error:
            QMessageBox.warning(
                self,
                "Не удалось сохранить",
                str(error),
            )
            return

        self.current_project_name = name.strip()
        QMessageBox.information(
            self,
            "Проект сохранён",
            f"«{self.current_project_name}» сохранён.",
        )

    def _open_projects_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Проекты")
        dialog.setMinimumSize(440, 380)

        layout = QVBoxLayout(dialog)

        title = QLabel("Твои проекты")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        projects_list = QListWidget()
        projects_list.addItems(
            self.project_storage.list_projects()
        )
        layout.addWidget(projects_list, 1)

        buttons = QHBoxLayout()
        save_button = QPushButton("Сохранить текущий")
        load_button = QPushButton("Открыть")
        delete_button = QPushButton("Удалить")
        close_button = QPushButton("Закрыть")

        buttons.addWidget(save_button)
        buttons.addWidget(load_button)
        buttons.addWidget(delete_button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        def refresh() -> None:
            projects_list.clear()
            projects_list.addItems(
                self.project_storage.list_projects()
            )

        def save_current() -> None:
            self._save_project()
            refresh()

        def load_selected() -> None:
            item = projects_list.currentItem()
            if item is None:
                return
            try:
                data = self.project_storage.load(
                    item.text()
                )
                self._apply_project_data(data)
                self.current_project_name = item.text()
            except (OSError, ValueError) as error:
                QMessageBox.warning(
                    dialog,
                    "Не удалось открыть",
                    str(error),
                )
                return
            dialog.accept()

        def delete_selected() -> None:
            item = projects_list.currentItem()
            if item is None:
                return
            answer = QMessageBox.question(
                dialog,
                "Удалить проект?",
                f"Удалить «{item.text()}»?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.project_storage.delete(item.text())
            if self.current_project_name == item.text():
                self.current_project_name = None
            refresh()

        save_button.clicked.connect(save_current)
        load_button.clicked.connect(load_selected)
        delete_button.clicked.connect(delete_selected)
        close_button.clicked.connect(dialog.reject)
        projects_list.itemDoubleClicked.connect(
            lambda _item: load_selected()
        )

        dialog.exec()

    def _load_music_library(self) -> None:
        """Загружает локальную музыкальную библиотеку из assets/music."""

        if not hasattr(self, "music_combo"):
            return

        music_root = Path("assets/music")
        supported = {
            ".mp3",
            ".wav",
            ".m4a",
            ".aac",
            ".ogg",
            ".flac",
        }

        self.music_combo.blockSignals(True)
        self.music_combo.clear()

        self.music_combo.addItem(
            "Без музыки",
            None,
        )

        if music_root.exists():
            tracks = sorted(
                path
                for path in music_root.iterdir()
                if (
                    path.is_file()
                    and path.suffix.lower() in supported
                )
            )

            for track in tracks:
                self.music_combo.addItem(
                    track.stem,
                    str(track.resolve()),
                )

        self.music_combo.addItem(
            "Выбрать файл…",
            "browse",
        )

        self.music_combo.setCurrentIndex(0)
        self.music_combo.blockSignals(False)

        self._update_music_preview_button()

    def _update_music_preview_button(self) -> None:
        if not hasattr(
            self,
            "music_preview_button",
        ):
            return

        value = self.music_combo.currentData()

        can_preview = (
            isinstance(value, str)
            and value not in {"", "browse"}
            and Path(value).is_file()
        )

        self.music_preview_button.setEnabled(
            can_preview
        )

        if not can_preview:
            self.music_preview_button.setText("▶")

    def _toggle_music_preview(self) -> None:
        """Проигрывает выбранный трек без запуска рендера."""

        if (
            self.music_preview_player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        ):
            self.music_preview_player.stop()
            return

        value = self.music_combo.currentData()

        if (
            not isinstance(value, str)
            or value in {"", "browse"}
        ):
            return

        music_path = Path(value)

        if not music_path.is_file():
            QMessageBox.warning(
                self,
                "Музыка не найдена",
                f"Файл не найден:\n{music_path}",
            )
            return

        # Не проигрываем одновременно voice-preview и музыку.
        if (
            self.voice_preview_player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        ):
            self.voice_preview_player.stop()

        self.music_preview_audio.setVolume(
            max(
                0.05,
                self.music_volume_slider.value()
                / 100,
            )
        )

        self.music_preview_player.setSource(
            QUrl.fromLocalFile(
                str(music_path.resolve())
            )
        )
        self.music_preview_player.play()

    def _music_preview_state_changed(
        self,
        state: QMediaPlayer.PlaybackState,
    ) -> None:
        if not hasattr(
            self,
            "music_preview_button",
        ):
            return

        if (
            state
            == QMediaPlayer.PlaybackState.PlayingState
        ):
            self.music_preview_button.setText("■")
            self.music_preview_button.setToolTip(
                "Остановить музыку"
            )
        else:
            self.music_preview_button.setText("▶")
            self.music_preview_button.setToolTip(
                "Прослушать выбранную музыку"
            )

    def _music_combo_changed(
        self,
        index: int,
    ) -> None:
        if (
            self.music_preview_player.playbackState()
            != QMediaPlayer.PlaybackState.StoppedState
        ):
            self.music_preview_player.stop()

        value = self.music_combo.itemData(index)

        if value == "browse":
            self._select_music()
            return

        self._update_music_preview_button()

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
        self._update_music_preview_button()

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

    def _next_output_path(
        self,
        current_path: Path,
    ) -> Path:
        """
        Возвращает новое имя MP4, не перезаписывая старые Shorts.

        final_short.mp4 -> final_short_001.mp4
        final_short_001.mp4 -> final_short_002.mp4
        """

        current_path = Path(current_path)

        parent = current_path.parent
        suffix = current_path.suffix or ".mp4"

        stem = current_path.stem
        stem = re.sub(
            r"_\d{3}$",
            "",
            stem,
        )

        parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        index = 1

        while True:
            candidate = (
                parent
                / f"{stem}_{index:03d}{suffix}"
            )

            if not candidate.exists():
                return candidate

            index += 1

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

        if self.gameplay_combo.currentText() == "Выбрать":
            QMessageBox.warning(
                self,
                "Геймплей не выбран",
                "Выбери категорию геймплея.",
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

            if not music.is_file():
                QMessageBox.warning(
                    self,
                    "Музыка не найдена",
                    "Выбранный музыкальный файл больше "
                    "не существует. Выбери музыку заново "
                    "или установи «Без музыки».",
                )
                return

        if not self._queue_running:
            self.output_path = self._next_output_path(
                self.output_path
            )
            self.output_label.setText(
                str(self.output_path)
            )

        export_data = (
            self.export_preset_combo.currentData()
        )

        if not (
            isinstance(export_data, tuple)
            and len(export_data) == 3
        ):
            export_data = (
                1080,
                1920,
                30,
            )

        output_width, output_height, export_fps = (
            export_data
        )

        gameplay_value = (
            self.gameplay_combo.currentData()
            or self.gameplay_combo.currentText()
        )

        preflight_problems = validate_generation(
            story=story,
            gameplay=gameplay_value,
            output_video=self.output_path,
            voice=self.voice_combo.currentData(),
            music=music,
            width=output_width,
            height=output_height,
            fps=export_fps,
        )

        if preflight_problems:
            QMessageBox.warning(
                self,
                "Проверь настройки",
                "Перед генерацией нужно исправить:\n\n• "
                + "\n• ".join(preflight_problems),
            )
            return

        self._cancel_requested = False

        self.worker = VideoGenerationWorker(
            story=story,
            gameplay=gameplay_value,
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
            subtitle_style=getattr(
                self,
                "_preview_style",
                "Glow",
            ),
            # 20 px в Preview ~= 72 px в рендере 1080x1920.
            subtitle_font_size=round(
                self.preview_font_size.value() * 3.6
            ),
            subtitle_position=(
                self.preview_position.currentText()
            ),
            subtitle_background_opacity=(
                self.preview_opacity.value()
            ),
            subtitle_font_name=(
                self.preview_font.currentText()
            ),
            subtitle_text_color=(
                self.preview_text_color
            ),
            subtitle_outline_color=(
                self.preview_outline_color
            ),
            output_width=output_width,
            output_height=output_height,
            fps=export_fps,
            parent=self,
        )

        self.worker.completed.connect(
            self._generation_completed
        )
        self.worker.failed.connect(
            self._generation_failed
        )
        self.worker.cancelled.connect(
            self._generation_cancelled
        )
        self.worker.progress.connect(
            self._generation_progress
        )
        self.worker.finished.connect(
            self._worker_finished
        )

        self.generate_button.set_busy(True)
        self.generate_button.setText(
            "✦  СОЗДАЁМ SHORT…"
        )

        self.cancel_button.setText(
            "ОТМЕНИТЬ"
        )
        self.cancel_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.cancel_button.setEnabled(True)
        self.cancel_button.setVisible(True)
        self.cancel_button.raise_()

        self.status_label.setText(
            "●  2%  Запускаем конвейер…"
        )
        self.progress_bar.setRange(
            0,
            100,
        )
        self.progress_bar.setValue(2)

        self.worker.start()

    def _cancel_generation(self) -> None:
        if self.worker is None:
            return

        self._cancel_requested = True
        self._queue_running = False
        self._queue_current_story = ""

        self.cancel_button.setEnabled(False)
        self.cancel_button.setText(
            "ОТМЕНЯЕМ…"
        )
        self.cancel_button.setCursor(
            Qt.CursorShape.ArrowCursor
        )
        self.status_label.setText(
            "●  Отменяем генерацию…"
        )

        self.worker.cancel()

        # Событие отмены устанавливается сразу. Worker завершит
        # текущий TTS/FFmpeg этап безопасно и пришлёт cancelled.
        self.progress_bar.setRange(0, 100)

    def _generation_cancelled(self) -> None:
        self.status_label.setText(
            "●  Генерация отменена"
        )
        self.progress_bar.setRange(
            0,
            100,
        )
        self.progress_bar.setValue(0)

    def _generation_progress(
        self,
        value: int,
        message: str,
    ) -> None:
        self.progress_bar.setRange(
            0,
            100,
        )
        self.progress_bar.setValue(
            max(
                0,
                min(100, value),
            )
        )
        self.status_label.setText(
            f"●  {value}%  {message}"
        )

        if self._queue_running and self.render_queue:
            self.render_queue[0]["_status"] = message
            self.render_queue[0]["_progress"] = value
            self.queue_storage.save(self.render_queue)
            if hasattr(self, "queue_page_list"):
                self._refresh_queue_page()

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

        completed_story = (
            self._queue_current_story
            if self._queue_running
            else self.story_input.toPlainText().strip()
        )
        duration_seconds = None
        try:
            duration_seconds = get_media_duration(Path(output_path))
        except (OSError, FileNotFoundError, MediaInfoError, ValueError):
            pass

        self.history_storage.add(
            output_path,
            completed_story,
            duration_seconds=duration_seconds,
            export_preset=self.export_preset_combo.currentText(),
            gameplay=self.gameplay_combo.currentText(),
            voice=self.voice_combo.currentText(),
        )

        if hasattr(self, "history_page_list"):
            self._refresh_history_page()

        if self._queue_running:
            if self.render_queue:
                self.render_queue[0]["_status"] = "Готово"
                self.render_queue[0]["_progress"] = 100
                self.queue_storage.save(self.render_queue)
                self.render_queue.pop(0)
                self.queue_storage.save(self.render_queue)
                if hasattr(self, "queue_page_list"):
                    self._refresh_queue_page()
            self._queue_current_story = ""
            self.status_label.setText(
                "●  Элемент очереди готов"
            )
            return

        self._show_render_result(
            Path(output_path)
        )

    def _show_render_result(
        self,
        output_path: Path,
    ) -> None:
        """Показывает готовый Short прямо в приложении."""

        output_path = output_path.resolve()

        dialog = QDialog(self)
        dialog.setWindowTitle("Short готов")
        dialog.setMinimumSize(620, 560)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(
            18,
            18,
            18,
            18,
        )
        layout.setSpacing(12)

        title = QLabel("✓ Short успешно создан")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        content = QHBoxLayout()
        content.setSpacing(18)

        result_video = QVideoWidget(dialog)
        result_video.setFixedSize(
            225,
            400,
        )

        result_audio = QAudioOutput(dialog)
        result_audio.setVolume(0.65)

        result_player = QMediaPlayer(dialog)
        result_player.setAudioOutput(
            result_audio
        )
        result_player.setVideoOutput(
            result_video
        )
        result_player.setSource(
            QUrl.fromLocalFile(
                str(output_path)
            )
        )

        def loop_result(
            status: QMediaPlayer.MediaStatus,
        ) -> None:
            if (
                status
                == QMediaPlayer.MediaStatus.EndOfMedia
            ):
                result_player.setPosition(0)
                result_player.play()

        result_player.mediaStatusChanged.connect(
            loop_result
        )

        info = QVBoxLayout()
        info.setSpacing(10)

        filename_label = QLabel(
            output_path.name
        )
        filename_label.setObjectName(
            "settingTitle"
        )
        filename_label.setWordWrap(True)

        size_mb = (
            output_path.stat().st_size
            / 1024
            / 1024
        )

        preset = (
            self.export_preset_combo.currentText()
        )

        details = QLabel(
            f"Экспорт: {preset}\\n"
            f"Размер файла: {size_mb:.1f} MB\\n"
            f"Папка: {output_path.parent}"
        )
        details.setObjectName("mutedText")
        details.setWordWrap(True)

        info.addWidget(filename_label)
        info.addWidget(details)
        info.addStretch()

        content.addWidget(result_video)
        content.addLayout(info, 1)
        layout.addLayout(content, 1)

        buttons = QHBoxLayout()

        play_button = QPushButton(
            "▶ / ■"
        )
        open_file_button = QPushButton(
            "Открыть видео"
        )
        folder_button = QPushButton(
            "Открыть папку"
        )
        close_button = QPushButton(
            "Готово"
        )

        buttons.addWidget(play_button)
        buttons.addWidget(open_file_button)
        buttons.addWidget(folder_button)
        buttons.addStretch()
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        def toggle_playback() -> None:
            if (
                result_player.playbackState()
                == QMediaPlayer.PlaybackState.PlayingState
            ):
                result_player.pause()
            else:
                result_player.play()

        play_button.clicked.connect(
            toggle_playback
        )
        open_file_button.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl.fromLocalFile(
                    str(output_path)
                )
            )
        )
        folder_button.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl.fromLocalFile(
                    str(output_path.parent)
                )
            )
        )
        close_button.clicked.connect(
            dialog.accept
        )

        result_player.play()
        dialog.exec()
        result_player.stop()

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

        if self._queue_running:
            self._queue_failures += 1

            if self.render_queue:
                self.render_queue[0]["_status"] = "Ошибка"
                self.render_queue[0]["_progress"] = 0
                self.queue_storage.save(self.render_queue)
                self.render_queue.pop(0)
                self.queue_storage.save(
                    self.render_queue
                )

            self._queue_current_story = ""
            self.status_label.setText(
                "●  Ошибка элемента — "
                "переходим к следующему"
            )
            return

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

        self.cancel_button.setEnabled(False)
        self.cancel_button.setVisible(False)
        self.cancel_button.setText(
            "ОТМЕНИТЬ"
        )
        self.cancel_button.setCursor(
            Qt.CursorShape.ArrowCursor
        )

        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None

        was_cancelled = self._cancel_requested
        self._cancel_requested = False

        if (
            self._queue_running
            and not was_cancelled
        ):
            QTimer.singleShot(
                250,
                self._start_next_queue_item,
            )

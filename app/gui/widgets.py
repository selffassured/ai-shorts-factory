from __future__ import annotations

import math

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPainterPath,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QFrame,
    QPushButton,
    QWidget,
)


class AuroraBackground(QWidget):
    """Плавный Aurora-фон без скачков при повторении анимации."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._phase = 0.0

        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        # Не сбрасываем phase в ноль: из-за этого раньше был заметный скачок.
        self._phase += 0.012
        self.update()

    def _draw_aurora_band(
        self,
        painter: QPainter,
        *,
        y_ratio: float,
        amplitude: float,
        thickness: float,
        phase_offset: float,
        color_a: QColor,
        color_b: QColor,
    ) -> None:
        width = max(self.width(), 1)
        height = max(self.height(), 1)
        center_y = height * y_ratio

        upper_points: list[tuple[float, float]] = []
        steps = 22
        step_x = (width + 140) / steps

        for index in range(steps + 1):
            x = -70 + index * step_x
            wave = index * 0.48 + self._phase + phase_offset
            y = (
                center_y
                + math.sin(wave) * amplitude
                + math.sin(wave * 0.37 + 1.3) * amplitude * 0.28
            )
            upper_points.append((x, y))

        path = QPainterPath()
        first_x, first_y = upper_points[0]
        path.moveTo(first_x, first_y)

        for x, y in upper_points[1:]:
            path.lineTo(x, y)

        for x, y in reversed(upper_points):
            path.lineTo(x, y + thickness)

        path.closeSubpath()

        gradient = QLinearGradient(
            0,
            center_y,
            width,
            center_y + thickness,
        )

        first = QColor(color_a)
        first.setAlpha(32)

        middle = QColor(color_b)
        middle.setAlpha(58)

        edge = QColor(color_b)
        edge.setAlpha(0)

        gradient.setColorAt(0.0, first)
        gradient.setColorAt(0.48, middle)
        gradient.setColorAt(1.0, edge)

        painter.fillPath(path, gradient)

    def paintEvent(self, event: QPaintEvent) -> None:
        del event

        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        width = max(self.width(), 1)
        height = max(self.height(), 1)

        base = QLinearGradient(0, 0, width, height)
        base.setColorAt(0.0, QColor("#050713"))
        base.setColorAt(0.5, QColor("#090d20"))
        base.setColorAt(1.0, QColor("#04060d"))
        painter.fillRect(self.rect(), base)

        self._draw_aurora_band(
            painter,
            y_ratio=0.12,
            amplitude=30,
            thickness=120,
            phase_offset=0.1,
            color_a=QColor("#5b21b6"),
            color_b=QColor("#db2777"),
        )
        self._draw_aurora_band(
            painter,
            y_ratio=0.68,
            amplitude=44,
            thickness=160,
            phase_offset=2.0,
            color_a=QColor("#1d4ed8"),
            color_b=QColor("#7c3aed"),
        )
        self._draw_aurora_band(
            painter,
            y_ratio=0.88,
            amplitude=24,
            thickness=90,
            phase_offset=3.7,
            color_a=QColor("#0891b2"),
            color_b=QColor("#a21caf"),
        )

        for x_ratio, y_ratio, radius, color in (
            (0.17, 0.23, 220, QColor("#6d28d9")),
            (0.82, 0.20, 210, QColor("#1d4ed8")),
            (0.74, 0.77, 250, QColor("#be185d")),
        ):
            x = (
                width * x_ratio
                + math.sin(self._phase * 0.43 + x_ratio * 4.0) * 24
            )
            y = (
                height * y_ratio
                + math.cos(self._phase * 0.31 + y_ratio * 5.0) * 20
            )

            glow = QRadialGradient(x, y, radius)

            inner = QColor(color)
            inner.setAlpha(28)

            middle = QColor(color)
            middle.setAlpha(9)

            transparent = QColor(color)
            transparent.setAlpha(0)

            glow.setColorAt(0.0, inner)
            glow.setColorAt(0.62, middle)
            glow.setColorAt(1.0, transparent)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(
                QPointF(x, y),
                radius,
                radius,
            )

        vignette = QRadialGradient(
            width / 2,
            height / 2,
            max(width, height) * 0.76,
        )
        vignette.setColorAt(0.0, QColor(0, 0, 0, 0))
        vignette.setColorAt(0.72, QColor(0, 0, 0, 16))
        vignette.setColorAt(1.0, QColor(0, 0, 0, 125))
        painter.fillRect(self.rect(), vignette)


class HoverFrame(QFrame):
    """
    Карточка с лёгкой анимацией границы.

    QGraphicsDropShadowEffect убран: он сильно тормозил интерфейс
    при наведении на несколько карточек.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        object_name: str = "hoverCard",
    ) -> None:
        super().__init__(parent)

        self.setObjectName(object_name)
        self._hover_amount = 0.0

        self._animation = QPropertyAnimation(
            self,
            b"hoverAmount",
            self,
        )
        self._animation.setDuration(150)
        self._animation.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )

    def get_hover_amount(self) -> float:
        return self._hover_amount

    def set_hover_amount(self, value: float) -> None:
        self._hover_amount = max(0.0, min(1.0, value))
        self.update()

    hoverAmount = Property(
        float,
        get_hover_amount,
        set_hover_amount,
    )

    def enterEvent(self, event) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._hover_amount)
        self._animation.setEndValue(1.0)
        self._animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._hover_amount)
        self._animation.setEndValue(0.0)
        self._animation.start()
        super().leaveEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)

        if self._hover_amount <= 0.001:
            return

        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        alpha = int(35 + self._hover_amount * 85)
        painter.setPen(
            QColor(168, 85, 247, alpha)
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)

        rect = QRectF(
            1.5,
            1.5,
            self.width() - 3,
            self.height() - 3,
        )
        painter.drawRoundedRect(rect, 17, 17)


class AnimatedSwitch(QAbstractButton):
    """Плавный переключатель без тяжёлых эффектов."""

    toggledAnimated = Signal(bool)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        checked: bool = True,
    ) -> None:
        super().__init__(parent)

        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(58, 30)

        self._position = 1.0 if checked else 0.0

        self._animation = QPropertyAnimation(
            self,
            b"position",
            self,
        )
        self._animation.setDuration(180)
        self._animation.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )

        self.toggled.connect(
            self._animate_to_state
        )

    def get_position(self) -> float:
        return self._position

    def set_position(self, value: float) -> None:
        self._position = max(0.0, min(1.0, value))
        self.update()

    position = Property(
        float,
        get_position,
        set_position,
    )

    def _animate_to_state(
        self,
        checked: bool,
    ) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._position)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()
        self.toggledAnimated.emit(checked)

    def paintEvent(self, event: QPaintEvent) -> None:
        del event

        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        rect = QRectF(
            1,
            1,
            self.width() - 2,
            self.height() - 2,
        )

        track = QLinearGradient(
            rect.topLeft(),
            rect.topRight(),
        )

        off = QColor("#25293a")
        on_left = QColor("#7c3aed")
        on_right = QColor("#2563eb")

        track.setColorAt(
            0.0,
            on_left if self._position > 0.01 else off,
        )
        track.setColorAt(
            1.0,
            on_right if self._position > 0.01 else off,
        )

        painter.setPen(QColor(255, 255, 255, 25))
        painter.setBrush(track)
        painter.drawRoundedRect(rect, 15, 15)

        knob_radius = 11
        left = 4 + knob_radius
        right = self.width() - 4 - knob_radius
        x = left + (right - left) * self._position

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(
            QPointF(x, self.height() / 2),
            knob_radius,
            knob_radius,
        )


class GlowButton(QPushButton):
    """
    Кнопка с бесшовным переливом.

    Цвета меняются через синусы, поэтому нет резкого сброса
    в начале нового цикла.
    """

    def __init__(
        self,
        text: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)

        self._phase = 0.0
        self._hover_amount = 0.0
        self._busy = False
        self._pressed = False

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(66)

        self._hover_animation = QPropertyAnimation(
            self,
            b"hoverAmount",
            self,
        )
        self._hover_animation.setDuration(150)
        self._hover_animation.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )

        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def get_hover_amount(self) -> float:
        return self._hover_amount

    def set_hover_amount(self, value: float) -> None:
        self._hover_amount = max(0.0, min(1.0, value))
        self.update()

    hoverAmount = Property(
        float,
        get_hover_amount,
        set_hover_amount,
    )

    def _tick(self) -> None:
        self._phase += 0.022 if not self._busy else 0.038
        self.update()

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.setEnabled(not busy)
        self.update()

    def enterEvent(self, event) -> None:
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_amount)
        self._hover_animation.setEndValue(1.0)
        self._hover_animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_amount)
        self._hover_animation.setEndValue(0.0)
        self._hover_animation.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._pressed = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    @staticmethod
    def _animated_color(
        phase: float,
        offset: float,
    ) -> QColor:
        hue = (
            0.72
            + 0.17 * math.sin(phase + offset)
        ) % 1.0

        saturation = 0.78
        value = 0.94

        return QColor.fromHsvF(
            hue,
            saturation,
            value,
            1.0,
        )

    def paintEvent(self, event: QPaintEvent) -> None:
        del event

        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        inset = 3 if self._pressed else 1

        rect = QRectF(
            inset,
            inset,
            self.width() - inset * 2,
            self.height() - inset * 2,
        )

        gradient = QLinearGradient(
            rect.topLeft(),
            rect.bottomRight(),
        )
        gradient.setColorAt(
            0.0,
            self._animated_color(self._phase, 0.0),
        )
        gradient.setColorAt(
            0.33,
            self._animated_color(self._phase, 2.1),
        )
        gradient.setColorAt(
            0.66,
            self._animated_color(self._phase, 4.2),
        )
        gradient.setColorAt(
            1.0,
            self._animated_color(self._phase, 6.0),
        )

        border_alpha = int(
            75 + self._hover_amount * 100
        )

        painter.setPen(
            QColor(
                255,
                255,
                255,
                border_alpha,
            )
        )
        painter.setBrush(gradient)
        painter.drawRoundedRect(
            rect,
            17,
            17,
        )

        overlay = QLinearGradient(
            rect.topLeft(),
            rect.bottomLeft(),
        )
        overlay.setColorAt(
            0.0,
            QColor(
                255,
                255,
                255,
                30 + int(self._hover_amount * 28),
            ),
        )
        overlay.setColorAt(
            0.45,
            QColor(255, 255, 255, 3),
        )
        overlay.setColorAt(
            1.0,
            QColor(0, 0, 0, 32),
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(overlay)
        painter.drawRoundedRect(
            rect,
            17,
            17,
        )

        painter.setPen(
            QColor(
                255,
                255,
                255,
                235 if self.isEnabled() else 165,
            )
        )

        font = painter.font()
        font.setBold(True)
        font.setPointSize(13)
        font.setLetterSpacing(
            font.SpacingType.AbsoluteSpacing,
            1.4,
        )
        painter.setFont(font)

        painter.drawText(
            rect,
            Qt.AlignmentFlag.AlignCenter,
            self.text(),
        )

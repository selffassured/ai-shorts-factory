from __future__ import annotations

from collections.abc import Callable


class GenerationCancelledError(RuntimeError):
    """Пользователь отменил генерацию."""


def check_cancelled(
    cancel_callback: Callable[[], bool] | None,
) -> None:
    if cancel_callback is not None and cancel_callback():
        raise GenerationCancelledError(
            "Генерация отменена пользователем."
        )

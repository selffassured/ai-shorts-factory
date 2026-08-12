

## v1.0 Release Candidate

Перед релизом рекомендуется проверить:

- одиночный рендер и отмену на TTS/FFmpeg;
- очередь из 3+ роликов, включая один ошибочный элемент;
- сохранение/открытие/удаление проектов;
- историю и открытие готового файла;
- все export presets;
- запуск после чистой установки зависимостей.

### Windows build

Для локальной сборки:

```powershell
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name "AI Shorts Factory" scripts/run_gui.py
```

FFmpeg/FFprobe должны быть доступны приложению через PATH либо добавлены в будущий bundle.

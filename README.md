# ORION Python Assistant

Голосовой ассистент на Python с:

- распознаванием речи (SpeechRecognition + Google Speech API),
- голосовым синтезом (pyttsx3),
- поиском через `DuckDuckGo`, `Wikipedia` и открытием `Google`-запроса в браузере.

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Для работы с микрофоном нужен `PyAudio` и системные аудио-библиотеки.

## Запуск

### Голосовой режим

```bash
python orion_assistant.py
```

### Текстовый режим (без микрофона и TTS)

```bash
python orion_assistant.py --no-voice
```

### Выбор поисковика

```bash
python orion_assistant.py --engine duckduckgo
python orion_assistant.py --engine wikipedia
python orion_assistant.py --engine google
```

## Команды

- `найди <запрос>` — поиск через выбранный движок,
- `открой <запрос>` — открыть Google-результаты в браузере,
- `выход` / `стоп` — завершение.

## Пример

```text
YOU: найди python dataclass
ORION: Нашла 5 результатов. Показываю первые.
```


## Публикация в GitHub

```bash
git remote add origin <URL_ВАШЕГО_РЕПО>
git push -u origin HEAD
```

Если удалённый `origin` уже настроен, достаточно выполнить:

```bash
git push
```

#!/usr/bin/env python3
"""ORION voice assistant with speech recognition, TTS and search engine integration."""

from __future__ import annotations

import argparse
import sys
import webbrowser
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import quote_plus

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchClient:
    """Unified search client for multiple engines."""

    def __init__(self, timeout: int = 8) -> None:
        self.timeout = timeout

    def search(self, query: str, engine: str = "duckduckgo", limit: int = 5) -> List[SearchResult]:
        engine = engine.lower().strip()
        if engine == "duckduckgo":
            return self._duckduckgo(query, limit)
        if engine == "wikipedia":
            return self._wikipedia(query, limit)
        if engine == "google":
            return self._google_fallback(query)
        raise ValueError(f"Unknown engine: {engine}")

    def _duckduckgo(self, query: str, limit: int) -> List[SearchResult]:
        results: List[SearchResult] = []
        if DDGS is None:
            raise RuntimeError("duckduckgo-search не установлен. Установите зависимости из requirements.txt")
        with DDGS(timeout=self.timeout) as ddgs:
            for item in ddgs.text(query, max_results=limit):
                results.append(
                    SearchResult(
                        title=item.get("title", "Без заголовка"),
                        url=item.get("href", ""),
                        snippet=item.get("body", ""),
                    )
                )
        return results

    def _wikipedia(self, query: str, limit: int) -> List[SearchResult]:
        try:
            import requests
        except ImportError as err:
            raise RuntimeError("requests не установлен. Установите зависимости из requirements.txt") from err

        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": 1,
            "srlimit": limit,
        }
        response = requests.get(
            "https://ru.wikipedia.org/w/api.php",
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()

        payload = response.json()
        found = payload.get("query", {}).get("search", [])
        results: List[SearchResult] = []
        for item in found:
            page_title = item.get("title", "Без заголовка")
            page_url = f"https://ru.wikipedia.org/wiki/{quote_plus(page_title.replace(' ', '_'))}"
            snippet = item.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", "")
            results.append(SearchResult(title=page_title, url=page_url, snippet=snippet))
        return results

    def _google_fallback(self, query: str) -> List[SearchResult]:
        # Google API requires credentials; fallback opens search URL.
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        return [SearchResult(title="Google Search", url=url, snippet="Откройте ссылку для просмотра результатов")]


class OrionAssistant:
    def __init__(self, engine: str = "duckduckgo", voice_enabled: bool = True) -> None:
        self.search_engine = engine
        self.voice_enabled = voice_enabled
        self.search_client = SearchClient()
        self.recognizer = sr.Recognizer() if sr is not None else None
        self.tts = pyttsx3.init() if pyttsx3 is not None and voice_enabled else None
        if self.tts is not None:
            self.tts.setProperty("rate", 175)

    def speak(self, text: str) -> None:
        print(f"ORION: {text}")
        if not self.voice_enabled or self.tts is None:
            return
        self.tts.say(text)
        self.tts.runAndWait()

    def listen(self) -> Optional[str]:
        if sr is None or self.recognizer is None:
            self.speak("SpeechRecognition не установлен. Переключитесь в --no-voice режим.")
            return None

        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            self.speak("Я слушаю.")
            audio = self.recognizer.listen(source, timeout=8, phrase_time_limit=15)

        try:
            text = self.recognizer.recognize_google(audio, language="ru-RU")
            print(f"YOU: {text}")
            return text
        except sr.UnknownValueError:
            self.speak("Не удалось распознать речь. Повторите, пожалуйста.")
        except sr.RequestError as err:
            self.speak(f"Ошибка сервиса распознавания: {err}")
        return None

    def run_search(self, query: str) -> None:
        try:
            results = self.search_client.search(query, engine=self.search_engine, limit=5)
        except Exception as err:  # network + external api errors
            self.speak(f"Ошибка поиска: {err}")
            return

        if not results:
            self.speak("Ничего не найдено.")
            return

        self.speak(f"Нашла {len(results)} результатов. Показываю первые.")
        for index, result in enumerate(results, start=1):
            print(f"{index}. {result.title}\n   {result.url}\n   {result.snippet}\n")

    def handle_command(self, text: str) -> bool:
        normalized = text.strip().lower()

        if normalized in {"выход", "стоп", "quit", "exit"}:
            self.speak("До встречи.")
            return False

        if normalized.startswith(("найди ", "поиск ", "search ")):
            query = text.split(maxsplit=1)[1]
            self.run_search(query)
            return True

        if normalized.startswith("открой "):
            query = text.split(maxsplit=1)[1]
            result = self.search_client.search(query, engine="google", limit=1)[0]
            webbrowser.open(result.url)
            self.speak("Открыла результаты в браузере.")
            return True

        self.speak(
            "Команда не распознана. Используйте: 'найди <запрос>', 'открой <запрос>' или 'выход'."
        )
        return True

    def loop(self, once: bool = False) -> None:
        self.speak("ORION запущен. Скажите команду или введите её текстом.")
        if self.voice_enabled and (sr is None or pyttsx3 is None):
            self.speak("Некоторые голосовые зависимости не установлены. Используйте --no-voice.")
        while True:
            if self.voice_enabled:
                command = self.listen()
            else:
                command = input("YOU: ").strip()

            if not command:
                if once:
                    break
                continue

            if not self.handle_command(command):
                break

            if once:
                break


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ORION voice assistant")
    parser.add_argument(
        "--engine",
        default="duckduckgo",
        choices=["duckduckgo", "wikipedia", "google"],
        help="Search engine for 'найди' command",
    )
    parser.add_argument(
        "--no-voice",
        action="store_true",
        help="Disable microphone and TTS (text-only mode)",
    )
    parser.add_argument("--once", action="store_true", help="Handle only one command and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    assistant = OrionAssistant(engine=args.engine, voice_enabled=not args.no_voice)

    try:
        assistant.loop(once=args.once)
    except KeyboardInterrupt:
        assistant.speak("Остановлено пользователем.")
    except Exception as err:
        print(f"Fatal error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Wyoming-Handler: sammelt eine Äußerung und lässt sie von speech.cpp (/v1/audio/transcriptions) erkennen."""

from __future__ import annotations

import io
import logging
import os
import time
import wave
from datetime import datetime
from typing import Optional

import httpx
from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import Describe, Info
from wyoming.server import AsyncEventHandler

_LOGGER = logging.getLogger(__name__)

# Die 30 Sprachen von Qwen3-ASR, wie "speech info qwen3-asr-1.7b" sie nennt
QWEN_ASR_LANGUAGES = [
    "ar", "cs", "da", "de", "el", "en", "es", "fa", "fi", "fil", "fr", "hi", "hu", "id", "it",
    "ja", "ko", "mk", "ms", "nl", "pl", "pt", "ro", "ru", "sv", "th", "tr", "vi", "yue", "zh",
]


class SpeechCppAsrEventHandler(AsyncEventHandler):
    def __init__(
        self,
        reader,
        writer,
        wyoming_info: Info,
        client: httpx.AsyncClient,
        api_url: str,
        forced_language: str,
        use_request_language: bool,
        prompt: str,
        save_dir: str = "",
        save_max_bytes: int = 0,
    ) -> None:
        super().__init__(reader, writer)
        self.wyoming_info = wyoming_info
        self.client = client
        self.endpoint = api_url.rstrip("/") + "/audio/transcriptions"
        self.forced_language = forced_language
        self.use_request_language = use_request_language
        self.prompt = prompt
        self.save_dir = save_dir
        self.save_max_bytes = save_max_bytes

        self.request_language: Optional[str] = None
        self.audio = bytearray()
        self.rate = 16000
        self.width = 2
        self.channels = 1

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(self.wyoming_info.event())
            return True

        if Transcribe.is_type(event.type):
            self.request_language = Transcribe.from_event(event).language
            return True

        if AudioStart.is_type(event.type):
            start = AudioStart.from_event(event)
            self.rate, self.width, self.channels = start.rate, start.width, start.channels
            self.audio.clear()
            return True

        if AudioChunk.is_type(event.type):
            chunk = AudioChunk.from_event(event)
            # Das Format des Chunks gilt; HA schickt 16 kHz, 16 Bit, mono
            self.rate, self.width, self.channels = chunk.rate, chunk.width, chunk.channels
            self.audio.extend(chunk.audio)
            return True

        if AudioStop.is_type(event.type):
            text = await self._transcribe()
            if self.save_dir and self.audio:
                self._save(text)
            await self.write_event(Transcript(text=text).event())
            self.audio.clear()
            self.request_language = None
            # HA öffnet für jede Äußerung eine neue Verbindung
            return False

        return True

    def _language(self) -> str:
        """Erzwungene Sprache, sonst die der Anfrage (nur wenn erlaubt), sonst automatisch."""
        if self.forced_language:
            return self.forced_language
        if self.use_request_language and self.request_language:
            language = self.request_language.split("-")[0].split("_")[0].lower()
            if language in QWEN_ASR_LANGUAGES:
                return language
        return "auto"

    def _wav(self) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(self.channels)
            wav.setsampwidth(self.width)
            wav.setframerate(self.rate)
            wav.writeframes(bytes(self.audio))
        return buffer.getvalue()

    def _save(self, text: str) -> None:
        """Legt die Äußerung als WAV ab und hängt eine Zeile an transcripts.tsv (Zeit, Datei, Sekunden, Text)."""
        now = datetime.now()
        name = now.strftime("%Y%m%d-%H%M%S-%f") + ".wav"
        seconds = len(self.audio) / (self.rate * self.width * self.channels)
        try:
            with open(os.path.join(self.save_dir, name), "wb") as f:
                f.write(self._wav())
            with open(os.path.join(self.save_dir, "transcripts.tsv"), "a", encoding="utf-8") as f:
                f.write(f"{now.isoformat(timespec='seconds')}\t{name}\t{seconds:.2f}\t{text}\n")
            if self.save_max_bytes:
                self._prune()
        except OSError:
            _LOGGER.exception("Äußerung nicht gespeichert")

    def _prune(self) -> None:
        """Löscht die ältesten Aufnahmen, bis alle zusammen unter save_max_bytes liegen, samt ihrer Zeilen in transcripts.tsv.

        Die Dateinamen sind Zeitstempel, also ist die alphabetische Reihenfolge die zeitliche.
        """
        wavs = sorted(n for n in os.listdir(self.save_dir) if n.endswith(".wav"))
        sizes = {n: os.path.getsize(os.path.join(self.save_dir, n)) for n in wavs}
        total = sum(sizes.values())
        gone = set()
        for n in wavs:
            if total <= self.save_max_bytes:
                break
            os.remove(os.path.join(self.save_dir, n))
            total -= sizes[n]
            gone.add(n)
        if not gone:
            return
        tsv = os.path.join(self.save_dir, "transcripts.tsv")
        with open(tsv, encoding="utf-8") as f:
            lines = [l for l in f if l.split("\t")[1:2] and l.split("\t")[1] not in gone]
        with open(tsv + ".tmp", "w", encoding="utf-8") as f:
            f.writelines(lines)
        os.replace(tsv + ".tmp", tsv)
        _LOGGER.info("%d alte Aufnahmen gelöscht, %.1f MB übrig", len(gone), total / 1e6)

    async def _transcribe(self) -> str:
        frame = self.width * self.channels
        seconds = len(self.audio) / (self.rate * frame) if frame else 0.0
        if seconds == 0.0:
            _LOGGER.warning("Keine Audiodaten, leeres Transkript")
            return ""

        language = self._language()
        data = {"language": language, "response_format": "verbose_json"}
        if self.prompt:
            data["prompt"] = self.prompt

        started = time.monotonic()
        try:
            response = await self.client.post(
                self.endpoint,
                data=data,
                files={"file": ("utterance.wav", self._wav(), "audio/wav")},
            )
        except httpx.HTTPError:
            _LOGGER.exception("speech.cpp nicht erreichbar")
            return ""
        elapsed = time.monotonic() - started
        if response.status_code != 200:
            _LOGGER.error("speech.cpp antwortet %s: %s", response.status_code, response.text)
            return ""

        result = response.json()
        text = result.get("text", "").strip()
        _LOGGER.info(
            "%.2f s Audio (%d Hz, %d Bit, %d ch) in %.2f s (RTFx %.1f), Sprache %s -> %s: %s",
            seconds, self.rate, self.width * 8, self.channels, elapsed,
            seconds / elapsed if elapsed else 0, language, result.get("language", "?"), text,
        )
        return text

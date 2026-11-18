"""Wyoming event handler: speaks text through speech.cpp's /v1/audio/speech with style tags."""

from __future__ import annotations

import logging
import time
from typing import List, Optional

import httpx
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import Describe, Info
from wyoming.server import AsyncEventHandler
from wyoming.tts import (
    Synthesize,
    SynthesizeChunk,
    SynthesizeStart,
    SynthesizeStop,
    SynthesizeStopped,
    SynthesizeVoice,
)

from styles import QWEN_LANGUAGES, Run, StyleConfig, parse_tags, split_complete

_LOGGER = logging.getLogger(__name__)

RATE = 24000
WIDTH = 2
CHANNELS = 1


class SpeechCppEventHandler(AsyncEventHandler):
    def __init__(
        self,
        reader,
        writer,
        wyoming_info: Info,
        config: StyleConfig,
        client: httpx.AsyncClient,
        api_url: str,
    ) -> None:
        super().__init__(reader, writer)
        self.wyoming_info = wyoming_info
        self.config = config
        self.client = client
        self.endpoint = api_url.rstrip("/") + "/audio/speech"

        self.streaming = False
        self.buffer = ""
        self.speaker = config.default_voice
        self.language = config.language
        self.base_instruction = ""
        # Instruction set by the last tag; None is the base style
        self.current: Optional[str] = None

    def _begin(self, voice: Optional[SynthesizeVoice]) -> None:
        """Fixes speaker, language and base style for one response."""
        self.speaker, style = self.config.resolve_voice(voice.name if voice else None)
        language = (voice.language or "") if voice else ""
        language = language.split("-")[0].split("_")[0].lower()
        self.language = language if language in QWEN_LANGUAGES else self.config.language
        if style is None:
            style = self.config.scheduled_style()
        self.base_instruction = self.config.instruction(style)
        self.current = None
        self.buffer = ""

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(self.wyoming_info.event())
            return True

        if SynthesizeStart.is_type(event.type):
            start = SynthesizeStart.from_event(event)
            self._begin(start.voice)
            self.streaming = True
            return True

        if SynthesizeChunk.is_type(event.type):
            if not self.streaming:
                return True
            self.buffer += SynthesizeChunk.from_event(event).text
            ready, self.buffer = split_complete(self.buffer)
            if ready.strip():
                await self._speak_text(ready)
            return True

        if SynthesizeStop.is_type(event.type):
            if self.streaming:
                if self.buffer.strip():
                    await self._speak_text(self.buffer)
                self.buffer = ""
                self.streaming = False
            await self.write_event(SynthesizeStopped().event())
            return True

        if Synthesize.is_type(event.type):
            # During a stream HA sends the whole text once more for older servers
            if self.streaming:
                return True
            synthesize = Synthesize.from_event(event)
            self._begin(synthesize.voice)
            await self._speak_text(synthesize.text)
            return True

        return True

    async def _speak_text(self, text: str) -> None:
        """Speaks text as one audio stream (audio-start ... audio-stop)."""
        runs, self.current = parse_tags(self.config, text, self.current)
        await self.write_event(AudioStart(rate=RATE, width=WIDTH, channels=CHANNELS).event())
        try:
            await self._speak_runs(runs)
        except Exception:
            _LOGGER.exception("Synthesis failed")
        finally:
            await self.write_event(AudioStop().event())

    async def _speak_runs(self, runs: List[Run]) -> None:
        for instruction, text in runs:
            instruction = self.base_instruction if instruction is None else instruction
            payload = {
                "input": text,
                "voice": self.speaker,
                "language": self.language,
                "response_format": "pcm",
            }
            if instruction:
                payload["instructions"] = instruction
            _LOGGER.info("[%s | %s] %s", self.speaker, instruction or "-", text)

            started = time.monotonic()
            first: Optional[float] = None
            size = 0
            pending = b""
            async with self.client.stream("POST", self.endpoint, json=payload) as response:
                if response.status_code != 200:
                    body = (await response.aread()).decode("utf-8", "replace")
                    raise RuntimeError(f"speech.cpp answered {response.status_code}: {body}")
                async for data in response.aiter_bytes():
                    if first is None:
                        first = time.monotonic() - started
                    # Keep whole 16-bit samples in each chunk
                    data = pending + data
                    cut = len(data) - len(data) % WIDTH
                    data, pending = data[:cut], data[cut:]
                    if not data:
                        continue
                    size += len(data)
                    await self.write_event(
                        AudioChunk(audio=data, rate=RATE, width=WIDTH, channels=CHANNELS).event()
                    )
            seconds = size / (RATE * WIDTH)
            elapsed = time.monotonic() - started
            _LOGGER.info(
                "%.2f s audio in %.2f s (RTFx %.1f), first audio after %.3f s",
                seconds, elapsed, seconds / elapsed if elapsed else 0, first or 0,
            )

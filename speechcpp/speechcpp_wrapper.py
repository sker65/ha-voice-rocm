#!/usr/bin/env python3
"""Wyoming-TTS-Server für Home Assistant vor speech.cpp (Qwen3-TTS 1.7B CustomVoice).

Meldet jede Stimme aus styles.json zweimal: als "ono_anna" (Stil nach Tageszeit)
und als "ono_anna-<stil>" (fester Stil). Stil-Tags im Text gehen beidem vor.

Aufruf: python3 speechcpp_wrapper.py --uri tcp://0.0.0.0:10208 --api-url http://speechcpp-server:8093/v1
"""

import argparse
import asyncio
import logging
from functools import partial

import httpx
from wyoming.info import Attribution, Info, TtsProgram, TtsVoice
from wyoming.server import AsyncServer

from speechcpp_handler import SpeechCppEventHandler
from styles import QWEN_LANGUAGES, StyleConfig

_LOGGER = logging.getLogger(__name__)


def build_info(config: StyleConfig) -> Info:
    attribution = Attribution(name="Qwen / speech.cpp", url="https://github.com/nyosegawa/speech.cpp")
    voices = []
    for speaker in config.voices:
        voices.append(TtsVoice(
            name=speaker, description=f"{speaker} (Stil nach Tageszeit)", attribution=attribution,
            installed=True, version=None, languages=QWEN_LANGUAGES,
        ))
        for style in config.styles:
            voices.append(TtsVoice(
                name=f"{speaker}-{style}", description=f"{speaker}, {style}", attribution=attribution,
                installed=True, version=None, languages=QWEN_LANGUAGES,
            ))
    return Info(tts=[TtsProgram(
        name="speechcpp-qwen3-tts",
        description="Qwen3-TTS 1.7B CustomVoice auf speech.cpp (Vulkan)",
        attribution=attribution,
        installed=True,
        version="0.11.0",
        voices=voices,
        supports_synthesize_streaming=True,
    )])


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uri", default="tcp://0.0.0.0:10208")
    parser.add_argument("--api-url", default="http://speechcpp-server:8093/v1")
    parser.add_argument("--config", default="styles.json")
    parser.add_argument("--api-timeout", type=float, default=120.0)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    config = StyleConfig.load(args.config)
    _LOGGER.info("Voices %s, default %s, schedule now: %r", config.voices, config.default_voice,
                 config.scheduled_style() or "-")

    client = httpx.AsyncClient(timeout=httpx.Timeout(args.api_timeout, connect=5.0))
    handler = partial(SpeechCppEventHandler, wyoming_info=build_info(config), config=config,
                      client=client, api_url=args.api_url)
    server = AsyncServer.from_uri(args.uri)
    _LOGGER.info("Listening on %s, speech.cpp at %s", args.uri, args.api_url)
    await server.run(handler)


if __name__ == "__main__":
    asyncio.run(main())

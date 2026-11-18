#!/usr/bin/env python3
"""Wyoming-STT-Server für Home Assistant vor speech.cpp (Qwen3-ASR).

Ohne --language erkennt Qwen3-ASR die Sprache selbst. Das ist Absicht: eine fest
vorgegebene Sprache verschlechtert gemischte Sätze (Deutsch mit englischen Begriffen).
Die Sprache, die Home Assistant in Transcribe schickt, gilt nur mit --use-request-language.

Aufruf: python3 speechcpp_asr_wrapper.py --uri tcp://0.0.0.0:10309 --api-url http://speechcpp-asr-server:8094/v1
"""

import argparse
import asyncio
import logging
import os
from functools import partial

import httpx
from wyoming.info import AsrModel, AsrProgram, Attribution, Info
from wyoming.server import AsyncServer

from speechcpp_asr_handler import QWEN_ASR_LANGUAGES, SpeechCppAsrEventHandler

_LOGGER = logging.getLogger(__name__)


def build_info(model: str) -> Info:
    attribution = Attribution(name="Qwen / speech.cpp", url="https://github.com/nyosegawa/speech.cpp")
    return Info(asr=[AsrProgram(
        name="speechcpp-qwen3-asr",
        description="Qwen3-ASR auf speech.cpp (Vulkan)",
        attribution=attribution,
        installed=True,
        version="0.11.0",
        models=[AsrModel(
            name=model,
            description=f"{model} (Sprache automatisch, auch gemischt)",
            attribution=attribution,
            installed=True,
            version=None,
            languages=QWEN_ASR_LANGUAGES,
        )],
    )])


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--uri", default="tcp://0.0.0.0:10309")
    parser.add_argument("--api-url", default="http://speechcpp-asr-server:8094/v1")
    # Nur für die Anzeige in HA; welches Modell rechnet, bestimmt der Server
    parser.add_argument("--model", default=os.environ.get("ASR_MODEL", "qwen3-asr-1.7b"))
    # Erzwingt eine Sprache für jede Anfrage (z. B. "de"); leer heißt automatisch
    parser.add_argument("--language", default=os.environ.get("ASR_LANGUAGE", ""))
    parser.add_argument("--use-request-language", action="store_true",
                        default=os.environ.get("ASR_USE_REQUEST_LANGUAGE", "") == "1")
    # Kontext für das Modell, etwa Namen von Räumen und Geräten
    parser.add_argument("--prompt", default=os.environ.get("ASR_PROMPT", ""))
    parser.add_argument("--api-timeout", type=float, default=60.0)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    if args.language and args.language not in QWEN_ASR_LANGUAGES:
        parser.error(f"--language {args.language!r} kennt Qwen3-ASR nicht: {', '.join(QWEN_ASR_LANGUAGES)}")

    client = httpx.AsyncClient(timeout=httpx.Timeout(args.api_timeout, connect=5.0))
    handler = partial(
        SpeechCppAsrEventHandler,
        wyoming_info=build_info(args.model),
        client=client,
        api_url=args.api_url,
        forced_language=args.language,
        use_request_language=args.use_request_language,
        prompt=args.prompt,
    )
    server = AsyncServer.from_uri(args.uri)
    _LOGGER.info("Listening on %s, speech.cpp at %s, language %s%s", args.uri, args.api_url,
                 args.language or "auto", " (or the request's)" if args.use_request_language else "")
    await server.run(handler)


if __name__ == "__main__":
    asyncio.run(main())

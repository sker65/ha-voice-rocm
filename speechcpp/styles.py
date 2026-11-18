"""Stile für Qwen3-TTS: Konfiguration, Inline-Tags, Tageszeit und Satzgrenzen.

Ein Stil ist eine Qwen3-TTS-Instruktion ("instructions" der OpenAI-API), die für
eine ganze Anfrage gilt. Inline-Tags im Text wechseln den Stil ab der Stelle, an
der sie stehen; der Shim schickt jeden Abschnitt als eigene Anfrage.

Tags:
    [ruhig]                     ein Stil aus styles.json (Groß/Klein und Umlaute egal)
    [stil: leicht ironisch]     eine freie Instruktion ("style:" geht auch)
    [normal] oder [/ruhig]      zurück zum Grundstil (Stimmvariante oder Tageszeit)
    [ruhig][freundlich]         direkt aufeinanderfolgende Tags gelten zusammen
Unbekannte Tags werden entfernt und nie vorgelesen.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

_LOGGER = logging.getLogger(__name__)

QWEN_LANGUAGES = ["de", "en", "es", "fr", "it", "ja", "ko", "pt", "ru", "zh"]

_TAG = re.compile(r"\[([^\[\]]{1,300})\]")
_RESET = {"normal", "standard", "default", "neutral"}
_FREE = {"stil", "style", "instruktion", "instruction"}
# Wörter vor einem Punkt, nach denen kein Satz endet
_ABBREVIATIONS = {
    "z", "b", "bzw", "ca", "usw", "dr", "hr", "fr", "nr", "st", "inkl", "ggf",
    "evtl", "vgl", "d", "h", "u", "a", "etc", "mio", "mrd", "min", "max", "std",
}


def normalize(name: str) -> str:
    name = name.strip().lower()
    for src, dst in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        name = name.replace(src, dst)
    return name


@dataclass
class ScheduleEntry:
    start: time
    style: str


@dataclass
class StyleConfig:
    voices: List[str]
    default_voice: str
    language: str
    timezone: str
    styles: dict
    schedule: List[ScheduleEntry] = field(default_factory=list)

    @staticmethod
    def load(path: str) -> "StyleConfig":
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        styles = {normalize(k): v for k, v in raw.get("styles", {}).items()}
        schedule = []
        for entry in raw.get("schedule", []):
            hour, minute = (int(x) for x in entry["from"].split(":"))
            style = normalize(entry.get("style", ""))
            if style and style not in _RESET and style not in styles:
                raise ValueError(f"schedule names the unknown style {entry['style']!r}")
            schedule.append(ScheduleEntry(time(hour, minute), style))
        schedule.sort(key=lambda e: e.start)
        config = StyleConfig(
            voices=raw["voices"],
            default_voice=raw.get("default_voice", raw["voices"][0]),
            language=raw.get("language", "de"),
            timezone=raw.get("timezone", "Europe/Berlin"),
            styles=styles,
            schedule=schedule,
        )
        if config.default_voice not in config.voices:
            raise ValueError(f"default_voice {config.default_voice!r} is not in voices")
        return config

    def instruction(self, style: str) -> str:
        style = normalize(style)
        return "" if not style or style in _RESET else self.styles[style]

    def scheduled_style(self, now: Optional[datetime] = None) -> str:
        """Name of the style the schedule sets now; the last entry wraps past midnight."""
        if not self.schedule:
            return ""
        now = now or datetime.now(ZoneInfo(self.timezone))
        current = self.schedule[-1]
        for entry in self.schedule:
            if entry.start <= now.time():
                current = entry
        return current.style

    def resolve_voice(self, name: Optional[str]) -> Tuple[str, Optional[str]]:
        """Speaker and style of a Wyoming voice name such as "ono_anna-ruhig"; None means no fixed style."""
        if name:
            speaker, _, style = name.partition("-")
            if speaker in self.voices and (not style or normalize(style) in self.styles):
                return speaker, (normalize(style) or None)
            _LOGGER.warning("Unknown voice %r, using %s", name, self.default_voice)
        return self.default_voice, None


# A run of text with the instruction it is spoken with; None is the base style.
Run = Tuple[Optional[str], str]


def parse_tags(config: StyleConfig, text: str, current: Optional[str]) -> Tuple[List[Run], Optional[str]]:
    """Splits text at its style tags. Returns the runs and the instruction in force after the text."""
    runs: List[Run] = []
    pos = 0
    # Tags with only whitespace between them combine ("[ruhig][freundlich]"); a tag after text replaces
    combined: List[str] = []
    after_tag = False
    for match in _TAG.finditer(text):
        before = text[pos:match.start()]
        if before.strip():
            runs.append((current, before))
            after_tag = False
        pos = match.end()
        body = match.group(1).strip()
        head, colon, rest = body.partition(":")
        key = normalize(body)
        if colon and normalize(head) in _FREE and rest.strip():
            instruction = rest.strip()
        elif key.startswith("/") or key in _RESET:
            instruction = None
        elif key in config.styles:
            instruction = config.styles[key]
        else:
            _LOGGER.info("Dropping unknown tag [%s]", body)
            continue
        if instruction is None:
            combined = []
        elif after_tag:
            combined.append(instruction)
        else:
            combined = [instruction]
        current = " ".join(i if i.endswith((".", "!", "?")) else i + "." for i in combined) or None
        after_tag = True
    after = text[pos:]
    if after.strip():
        runs.append((current, after))

    merged: List[Run] = []
    for instruction, part in runs:
        if merged and merged[-1][0] == instruction:
            merged[-1] = (instruction, merged[-1][1] + part)
        else:
            merged.append((instruction, part))
    return [(i, " ".join(p.split())) for i, p in merged], current


def split_complete(buffer: str) -> Tuple[str, str]:
    """Splits a streamed text into its complete sentences and the rest still being written.

    A sentence ends at . ! ? … or a line break that is followed by whitespace, outside a
    tag, and not after a number ("12. November") or a common abbreviation ("z. B.").
    """
    depth = 0
    cut = 0
    for i, ch in enumerate(buffer):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        if depth:
            continue
        if ch == "\n":
            cut = i + 1
            continue
        if ch not in ".!?…" or i + 1 >= len(buffer) or not buffer[i + 1].isspace():
            continue
        if ch == ".":
            word = re.search(r"(\w+)$", buffer[:i])
            if word and (word.group(1).isdigit() or normalize(word.group(1)) in _ABBREVIATIONS):
                continue
        cut = i + 1
    return buffer[:cut], buffer[cut:]

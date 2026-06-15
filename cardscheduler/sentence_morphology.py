"""Sentence morphology helpers for Japanese sentence scoring."""

import logging
import re
import subprocess
from dataclasses import dataclass


logger = logging.getLogger(__name__)

KANJI_PATTERN = re.compile(r"[\u4e00-\u9fff]")
SKIPPED_POS = {"記号", "補助記号", "空白"}
EOS_MARKER = "EOS"
MECAB_TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class SentenceToken:
    surface: str
    lemma: str
    reading: str
    pos: str


def contains_kanji(text):
    return bool(KANJI_PATTERN.search(text or ""))


def katakana_to_hiragana(text):
    """Normalize katakana readings to hiragana."""
    chars = []
    for char in text or "":
        code = ord(char)
        if 0x30A1 <= code <= 0x30F6:
            chars.append(chr(code - 0x60))
        else:
            chars.append(char)
    return "".join(chars)


def normalize_reading(reading):
    reading = (reading or "").strip()
    if reading == "*":
        return ""
    return katakana_to_hiragana(reading)


class MecabTokenAnalyzer:
    """Read Japanese morphemes through a system MeCab executable."""

    def __init__(self, commands=None):
        self._commands = commands or [
            "mecab",
            "/usr/local/bin/mecab",
            "/opt/homebrew/bin/mecab",
        ]
        self.base_cmd = None
        self.encoding = "utf-8"
        self._token_cache = {}
        self.setup()

    @property
    def available(self):
        return bool(self.base_cmd)

    def setup(self):
        for command in self._commands:
            try:
                result = subprocess.run(
                    [command, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
            except Exception:
                logger.warning(
                    "MeCab availability check failed for %s", command, exc_info=True
                )
                continue

            if result.returncode != 0:
                continue

            self.base_cmd = [command]
            self._load_dictionary_encoding(command)
            logger.info("MeCab subprocess setup successful with command: %s", command)
            return

        logger.warning("MeCab command not found; sentence scoring is disabled")

    def _load_dictionary_encoding(self, command):
        try:
            result = subprocess.run(
                [command, "-D"],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return
        except Exception:
            logger.warning("MeCab dictionary encoding lookup failed", exc_info=True)
            return

        if result.returncode != 0:
            return

        charset_match = re.search(r"^charset:\s*(.*)$", result.stdout, re.M)
        if charset_match:
            self.encoding = charset_match.group(1).strip()

    def extract_tokens(self, text):
        """Return kanji-containing sentence tokens with surface, lemma, reading and POS."""
        cache_key = self._cache_key(text)
        return self.extract_tokens_many([cache_key]).get(cache_key, [])

    def extract_tokens_many(self, texts):
        """Return kanji-containing sentence tokens for many texts in one MeCab call."""
        cache_keys = [self._cache_key(text) for text in texts]
        if not self.available:
            return {text: [] for text in cache_keys}

        uncached = []
        seen = set()
        for text in cache_keys:
            if text in self._token_cache or text in seen:
                continue
            uncached.append(text)
            seen.add(text)

        if uncached:
            self._extract_uncached_many(uncached)

        return {
            text: list(self._token_cache.get(text, ()))
            for text in cache_keys
        }

    def _cache_key(self, text):
        return (text or "").strip()

    def _extract_uncached_many(self, texts):
        try:
            result = self._run_mecab(texts)
        except subprocess.TimeoutExpired:
            logger.warning("MeCab sentence token extraction timed out for %s texts", len(texts))
            self._cache_empty(texts)
            return
        except Exception:
            logger.warning("MeCab sentence token extraction failed", exc_info=True)
            self._cache_empty(texts)
            return

        if result.returncode != 0:
            logger.warning(
                "MeCab sentence token extraction failed with code %s: %s",
                result.returncode,
                result.stderr,
            )
            self._cache_empty(texts)
            return

        token_groups = self._split_mecab_output(result.stdout)
        if len(token_groups) != len(texts):
            logger.warning(
                "MeCab returned %s token groups for %s texts",
                len(token_groups),
                len(texts),
            )

        for index, text in enumerate(texts):
            lines = token_groups[index] if index < len(token_groups) else []
            self._token_cache[text] = tuple(self._parse_token_lines(lines))

    def _run_mecab(self, texts):
        input_text = "\n".join(text.replace("\n", " ") for text in texts) + "\n"
        return subprocess.run(
            self.base_cmd
            + [
                "--node-format=%m\t%f[0]\t%f[6]\t%f[7]\n",
                f"--eos-format={EOS_MARKER}\n",
                "--unk-format=%m\t*\t*\t*\n",
            ],
            input=input_text,
            capture_output=True,
            text=True,
            encoding=self.encoding,
            timeout=MECAB_TIMEOUT_SECONDS,
        )

    def _split_mecab_output(self, output):
        token_groups = []
        current = []
        for line in (output or "").splitlines():
            if line == EOS_MARKER:
                token_groups.append(current)
                current = []
            else:
                current.append(line)

        if current:
            token_groups.append(current)
        return token_groups

    def _parse_token_lines(self, lines):
        tokens = []
        for line in lines:
            if not line.strip():
                continue

            parts = line.split("\t")
            if len(parts) < 4:
                continue

            surface, pos, lemma, reading = parts[:4]
            if pos in SKIPPED_POS:
                continue
            if lemma == "*":
                lemma = surface
            if not contains_kanji(surface) and not contains_kanji(lemma):
                continue

            tokens.append(
                SentenceToken(
                    surface=surface,
                    lemma=lemma,
                    reading=normalize_reading(reading),
                    pos=pos,
                )
            )

        return tokens

    def _cache_empty(self, texts):
        for text in texts:
            self._token_cache[text] = ()

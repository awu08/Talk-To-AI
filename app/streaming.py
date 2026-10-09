"""Streaming helpers: cut a growing answer into speakable sentences.

As the AI's answer arrives in small pieces, SentenceSplitter hands back each
sentence as soon as it's complete, so speech can start after the first one
instead of waiting for the whole answer.

Author: Allen Wu
Version: 1.2.0
"""

import re
from typing import List

# Words whose trailing period doesn't end a sentence
_ABBREVIATIONS = {
    "e.g", "i.e", "etc", "vs", "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st",
    "no", "approx", "inc", "ltd", "co", "fig", "u.s", "a.m", "p.m",
}

# A sentence ends at . ! ? (plus closing quotes/brackets) followed by whitespace,
# or at a line break.
_BOUNDARY = re.compile(r"""[.!?]+["'”’)\]]*(?=\s)|\n+""")


class SentenceSplitter:
    """Feed it text as it streams in; get back complete sentences.

    Example:
        >>> s = SentenceSplitter()
        >>> s.feed("Hi there. How a")
        ['Hi there.']
        >>> s.feed("re you? Fine")
        ['How are you?']
        >>> s.flush()
        'Fine'
    """

    def __init__(self, min_length: int = 2) -> None:
        self._buffer: str = ""
        self._min_length = min_length

    def feed(self, text: str) -> List[str]:
        """Add new text; return any sentences that are now complete."""
        self._buffer += text
        sentences: List[str] = []
        start = 0
        for match in _BOUNDARY.finditer(self._buffer):
            end = match.end()
            candidate = self._buffer[start:end].strip()
            if not candidate:
                start = end
                continue
            if match.group().startswith("\n") or not self._is_false_stop(candidate):
                if len(candidate) >= self._min_length:
                    sentences.append(candidate)
                    start = end
        self._buffer = self._buffer[start:]
        return sentences

    def flush(self) -> str:
        """Return whatever is left at the end of the answer."""
        rest, self._buffer = self._buffer.strip(), ""
        return rest

    @staticmethod
    def _is_false_stop(candidate: str) -> bool:
        """True when the period belongs to an abbreviation or a list number ("1.")."""
        if not candidate.endswith("."):
            return False
        stripped = candidate.rstrip(".")
        last_word = stripped.split()[-1].lower() if stripped.split() else ""
        if last_word.isdigit() and len(stripped.split()) == 1:
            return True  # "1." at the start of a numbered list item
        if last_word in _ABBREVIATIONS:
            return True
        return len(last_word) == 1 and last_word.isalpha()  # an initial, like "J."

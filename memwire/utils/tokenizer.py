"""Tokenization utilities: word-level tokenization, bigram extraction."""

import re
from dataclasses import dataclass


@dataclass
class TokenizerResult:
    """Result of tokenization."""
    tokens: list[str]
    bigrams: list[tuple[str, str]]
    original: str


class Tokenizer:
    """Word-level tokenizer with subword merging and bigram extraction."""

    def tokenize(self, text: str) -> TokenizerResult:
        """Tokenize text into words, extract bigrams."""
        cleaned = self._clean(text)
        tokens = self._split_tokens(cleaned)
        bigrams = self._extract_bigrams(tokens)
        return TokenizerResult(tokens=tokens, bigrams=bigrams, original=text)

    def _clean(self, text: str) -> str:
        """Normalize text: lowercase, strip excess whitespace."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s'-]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def _split_tokens(self, text: str) -> list[str]:
        """Split into word tokens, merging common subword patterns."""
        raw_tokens = text.split()
        merged = []
        i = 0
        while i < len(raw_tokens):
            token = raw_tokens[i]
            if i + 2 < len(raw_tokens) and raw_tokens[i + 1] == "-":
                merged.append(f"{token}-{raw_tokens[i + 2]}")
                i += 3
            else:
                if len(token) > 1:
                    merged.append(token)
                elif token in ("i", "a"):
                    merged.append(token)
                i += 1
        return merged

    def _extract_bigrams(self, tokens: list[str]) -> list[tuple[str, str]]:
        """Extract bigrams from all consecutive token pairs."""
        return [(tokens[i], tokens[i + 1]) for i in range(len(tokens) - 1)]

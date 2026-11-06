"""Natural Language Processing and preprocessing utilities."""
from __future__ import annotations

import re
from typing import List, Set
from ai.utils import normalize_text

STANDARD_STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
    "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll",
    "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's",
    "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on",
    "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own",
    "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some",
    "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then",
    "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we",
    "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's",
    "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't",
    "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves", "etc", "eg", "ie", "candidate", "role", "work", "job"
}


class TextPreprocessor:
    """Enterprise text preprocessor with tokenization, stopword removal, and lemmatization."""

    def __init__(self) -> None:
        self.stopwords = STANDARD_STOPWORDS
        self._lemmatizer = None
        self._init_nltk()

    def _init_nltk(self) -> None:
        try:
            from nltk.corpus import stopwords
            from nltk.stem import WordNetLemmatizer
            nltk_stops = set(stopwords.words("english"))
            self.stopwords = self.stopwords.union(nltk_stops)
            self._lemmatizer = WordNetLemmatizer()
        except Exception:
            self._lemmatizer = None

    def clean_text(self, text: str | None) -> str:
        if not text:
            return ""
        norm = normalize_text(text).lower()
        norm = re.sub(r"[^\w\s\+#\.-]", " ", norm)
        return re.sub(r"\s+", " ", norm).strip()

    def tokenize(self, text: str) -> List[str]:
        cleaned = self.clean_text(text)
        if not cleaned:
            return []
        tokens = re.findall(r"\b[a-zA-Z0-9+#.-]+\b", cleaned)
        return [t.strip() for t in tokens if len(t.strip()) > 1]

    def remove_stopwords(self, tokens: List[str]) -> List[str]:
        return [token for token in tokens if token.lower() not in self.stopwords]

    def lemmatize(self, tokens: List[str]) -> List[str]:
        if not tokens:
            return []
        if self._lemmatizer:
            try:
                return [self._lemmatizer.lemmatize(t) for t in tokens]
            except Exception:
                pass
        return tokens

    def preprocess(self, text: str) -> str:
        tokens = self.tokenize(text)
        filtered = self.remove_stopwords(tokens)
        lemmatized = self.lemmatize(filtered)
        return " ".join(lemmatized)

    def extract_keywords(self, text: str, top_n: int = 20) -> List[str]:
        tokens = self.remove_stopwords(self.tokenize(text))
        if not tokens:
            return []
        freq: dict[str, int] = {}
        for t in tokens:
            if len(t) >= 3 and not t.isdigit():
                freq[t] = freq.get(t, 0) + 1
        sorted_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_keywords[:top_n]]


# Singleton instance
preprocessor = TextPreprocessor()

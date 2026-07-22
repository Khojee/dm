"""Word analytics: top words, n-grams, TF-IDF keywords, language, punctuation."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

import pandas as pd

# Minimal multilingual stopword list (English + Uzbek + Russian common words)
STOPWORDS = set("""
the a an and or but if then else for to of in on at by with from as is are was
were be been being am do does did doing have has had having i you he she it we
they me him her us them my your his its our their this that these those not no
so what when where who whom which why how all any both each few more most other
some such only own same than too very can will just dont should now im its lets
u ur r ok okay oh hm hmm yes yeah yep nah
va ham bu shu u men sen biz siz ular lekin ammo yoki uchun bilan emas ha yo'q
edi ekan bo'lib bo'ladi qilib deb keyin endi yana juda ham menga senga sizga
bir nima qanday qachon nega kim mening sening bizning
и в не на я что он она оно мы вы они а но или для с от как это то же бы был
была было были есть нет да у к по за из о мне тебе вам них меня тебя вас
""".split())

WORD_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁo'ʻʼg'\u0100-\u017F]+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in WORD_RE.findall(text) if len(w) > 2 and w.lower() not in STOPWORDS]


def _ngrams(tokens: list[str], n: int) -> list[str]:
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def _detect_languages(texts: list[str]) -> dict[str, int]:
    """Best-effort language detection over a sample of longer messages."""
    try:
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed = 42
    except ImportError:
        return {}
    counts: Counter[str] = Counter()
    sample = [t for t in texts if len(t.split()) >= 4][:400]
    for t in sample:
        try:
            counts[detect(t)] += 1
        except Exception:
            continue
    return dict(counts.most_common(6))


def compute_words(df: pd.DataFrame) -> dict[str, Any]:
    """Compute vocabulary statistics for the whole chat and per sender."""
    texts = df[df["text"] != ""]

    unigrams: Counter[str] = Counter()
    bigrams: Counter[str] = Counter()
    trigrams: Counter[str] = Counter()
    by_sender_words: dict[str, Counter[str]] = {}
    punctuation: dict[str, Counter[str]] = {}

    docs_by_sender: dict[str, list[str]] = {}

    for _, row in texts.iterrows():
        tokens = _tokenize(row["text"])
        unigrams.update(tokens)
        bigrams.update(_ngrams(tokens, 2))
        trigrams.update(_ngrams(tokens, 3))
        by_sender_words.setdefault(row["sender"], Counter()).update(tokens)
        docs_by_sender.setdefault(row["sender"], []).append(row["text"])
        p = punctuation.setdefault(row["sender"], Counter())
        for ch in row["text"]:
            if ch in "?!.,:;…-":
                p[ch] += 1

    # TF-IDF: distinctive words per sender (each sender's corpus is a doc)
    tfidf: dict[str, list[tuple[str, float]]] = {}
    n_docs = len(by_sender_words)
    if n_docs >= 2:
        doc_freq: Counter[str] = Counter()
        for counter in by_sender_words.values():
            doc_freq.update(counter.keys())
        for sender, counter in by_sender_words.items():
            total = sum(counter.values()) or 1
            scores = {
                w: (c / total) * math.log((n_docs + 1) / (doc_freq[w])) if doc_freq[w] < n_docs else 0
                for w, c in counter.items() if c >= 2
            }
            top = sorted(scores.items(), key=lambda x: -x[1])[:12]
            tfidf[sender] = [(w, round(s, 4)) for w, s in top if s > 0]

    # Message length stats
    text_msgs = texts[texts["word_count"] > 0]
    longest = text_msgs.nlargest(1, "word_count")
    length_by_sender = {
        s: round(float(g["word_count"].mean()), 1)
        for s, g in text_msgs.groupby("sender")
    }

    total_words = int(text_msgs["word_count"].sum())
    n_days = max((df["datetime"].max() - df["datetime"].min()).days, 1)

    # Inside-joke candidates: words used often but only by these two people
    # (proxy: rare-looking tokens used 3+ times, not in stopwords, len>=4)
    joke_candidates = [
        (w, c) for w, c in unigrams.most_common(200)
        if c >= 3 and len(w) >= 4 and not w.isascii()
    ][:10] or [(w, c) for w, c in unigrams.most_common(40) if c >= 3][:10]

    return {
        "total_words": total_words,
        "unique_words": len(unigrams),
        "avg_words_per_day": round(total_words / n_days, 1),
        "avg_message_length_words": length_by_sender,
        "longest_message": {
            "sender": longest.iloc[0]["sender"],
            "words": int(longest.iloc[0]["word_count"]),
            "preview": longest.iloc[0]["text"][:220],
            "date": str(longest.iloc[0]["datetime"].date()),
        } if len(longest) else None,
        "top_words": unigrams.most_common(30),
        "top_bigrams": bigrams.most_common(15),
        "top_trigrams": trigrams.most_common(10),
        "tfidf_by_sender": tfidf,
        "top_words_by_sender": {s: c.most_common(15) for s, c in by_sender_words.items()},
        "punctuation_by_sender": {s: c.most_common(8) for s, c in punctuation.items()},
        "languages": _detect_languages(list(texts["text"])),
        "inside_joke_candidates": joke_candidates,
    }

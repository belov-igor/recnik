#!/usr/bin/env python3
"""
Import Russian→Serbian word pairs from Tatoeba sentence pairs.

Source: https://tatoeba.org  (CC BY 2.0 FR)
Usage:
    python scripts/import_tatoeba.py [--min-count N] [--max-words N] [--dry-run]

Downloads Russian and Serbian sentences + the global links file, finds
aligned sentence pairs, and extracts word-translation candidates via
co-occurrence counting. Pairs that co-occur in ≥ min-count distinct
sentence pairs are added to data/dictionary.tsv (skipping duplicates).

Only sentences with ≤ max-words tokens per side are used — shorter
sentences give cleaner word alignments.
"""

import argparse
import bz2
import csv
import re
import tarfile
import urllib.request
from collections import defaultdict
from pathlib import Path

sys_path = str(Path(__file__).parent)
import sys
sys.path.insert(0, sys_path)
from transliterate import cyr_to_lat

OUTPUT = Path(__file__).parent.parent / "data" / "dictionary.tsv"

URL_RUS = "https://downloads.tatoeba.org/exports/per_language/rus/rus_sentences.tsv.bz2"
URL_SRP = "https://downloads.tatoeba.org/exports/per_language/srp/srp_sentences.tsv.bz2"
URL_LINKS = "https://downloads.tatoeba.org/exports/links.tar.bz2"

# Russian stop-words to skip (very high-frequency, low-information)
RU_STOP = {
    "я", "ты", "он", "она", "оно", "мы", "вы", "они",
    "это", "тот", "та", "те", "то", "этот", "эта", "эти",
    "и", "в", "не", "на", "что", "с", "по", "а", "к", "но",
    "из", "за", "от", "до", "как", "у", "о", "об", "или",
    "же", "ли", "бы", "всё", "все", "так", "уже", "ещё",
    "есть", "был", "была", "было", "были", "быть",
    # pronoun case forms
    "мне", "тебе", "ему", "ей", "нам", "вам", "им",
    "меня", "тебя", "его", "её", "нас", "вас", "их",
    "него", "неё", "ней", "них", "нему", "ним", "ними",
    # demonstrative case forms
    "того", "той", "тем", "том", "тому", "тех", "теми",
    "этого", "этой", "этом", "этому", "этих", "этими",
    # misc high-frequency
    "тоже", "здесь", "тут", "там", "когда", "если", "чтобы",
    "очень", "можно", "нельзя", "надо", "нет", "да",
}

SR_STOP = {
    "ja", "ti", "on", "ona", "ono", "mi", "vi", "oni", "one",
    "i", "u", "ne", "na", "što", "šta", "s", "po", "a", "k", "ali",
    "iz", "za", "od", "do", "kao", "o", "ili",
    "je", "su", "sam", "si", "smo", "ste",
    "bio", "bila", "bilo", "bili", "biti",
    "me", "te", "ga", "nas", "vas", "ih",
    "to", "taj", "ta", "ti", "te",
    "već", "još", "sve", "svi",
    # high-frequency particles / auxiliaries (major noise sources)
    "da", "se", "li", "pa", "ni", "bi", "mu", "joj", "im",
    "ovaj", "ova", "ovo", "ovde", "ovdje", "onde", "tu",
    "kad", "kada", "jer", "ako", "nego",
}

_WORD_RE = re.compile(r"[а-яёА-ЯЁ]{2,}", re.UNICODE)
_SR_WORD_RE = re.compile(r"[a-zA-ZčćšžđČĆŠŽĐ]{2,}", re.UNICODE)


def tokenize_ru(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text) if w.lower() not in RU_STOP]


def tokenize_sr(text: str) -> list[str]:
    # Tatoeba Serbian is mostly Cyrillic — transliterate first
    lat = cyr_to_lat(text)
    return [w.lower() for w in _SR_WORD_RE.findall(lat) if w.lower() not in SR_STOP]


def load_sentences(url: str, tokenize) -> dict[str, list[str]]:
    """Return {sentence_id: [tokens]} from a bz2-compressed TSV."""
    print(f"  Downloading {url.split('/')[-1]} ...", flush=True)
    with urllib.request.urlopen(url) as resp:
        data = bz2.decompress(resp.read()).decode("utf-8")
    result = {}
    for line in data.strip().split("\n"):
        parts = line.split("\t", 2)
        if len(parts) < 3:
            continue
        sid, _lang, text = parts
        tokens = tokenize(text)
        if tokens:
            result[sid] = tokens
    return result


def load_pairs(rus: dict, srp: dict) -> list[tuple[list, list]]:
    """Stream links file and return (ru_tokens, sr_tokens) pairs."""
    print(f"  Downloading links (large file) ...", flush=True)
    pairs = []
    with urllib.request.urlopen(URL_LINKS) as resp:
        with tarfile.open(fileobj=resp, mode="r|bz2") as tar:
            for member in tar:
                f = tar.extractfile(member)
                if f is None:
                    continue
                for line in f:
                    a, b = line.decode().strip().split("\t")
                    if a in rus and b in srp:
                        pairs.append((rus[a], srp[b]))
                    elif a in srp and b in rus:
                        pairs.append((rus[b], srp[a]))
    print(f"  Found {len(pairs)} ru-sr sentence pairs", flush=True)
    return pairs


def load_existing(path: Path) -> tuple[set[str], set[tuple]]:
    known_ru: set[str] = set()
    existing: set[tuple] = set()
    if not path.exists():
        return known_ru, existing
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            known_ru.add(row["ru"])
            existing.add((row["ru"], row["sr_lat"]))
    return known_ru, existing


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-count", type=int, default=4,
                        help="Minimum co-occurrences to accept a pair (default: 4)")
    parser.add_argument("--max-words", type=int, default=6,
                        help="Max tokens per sentence side (default: 6)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("Loading existing dictionary ...")
    known_ru, existing = load_existing(OUTPUT)
    print(f"  {len(existing)} existing pairs, {len(known_ru)} unique Russian words")

    print("Loading Tatoeba sentences ...")
    rus = load_sentences(URL_RUS, tokenize_ru)
    srp = load_sentences(URL_SRP, tokenize_sr)

    print("Loading sentence pairs ...")
    pairs = load_pairs(rus, srp)

    # co-occurrence counting on short sentences
    print(f"Counting co-occurrences (max {args.max_words} words/side) ...")
    cooc: dict[tuple[str, str], set[int]] = defaultdict(set)
    for i, (ru_toks, sr_toks) in enumerate(pairs):
        if len(ru_toks) > args.max_words or len(sr_toks) > args.max_words:
            continue
        for ru_w in ru_toks:
            for sr_w in sr_toks:
                cooc[(ru_w, sr_w)].add(i)

    # filter by min-count
    candidates = [(ru, sr, len(sids))
                  for (ru, sr), sids in cooc.items()
                  if len(sids) >= args.min_count]
    candidates.sort(key=lambda x: -x[2])

    # remove pairs already in dictionary
    new_rows = []
    for ru, sr, count in candidates:
        if (ru, sr) not in existing:
            new_rows.append((ru, sr, "-", "-", "-", f"tatoeba:{count}"))

    print(f"New candidate pairs: {len(new_rows)}")

    if not new_rows:
        print("Nothing to add.")
        return

    if args.dry_run:
        print("-- dry run, not writing --")
        for row in new_rows[:30]:
            print(f"  {row[0]:20} {row[1]:20}  (seen {row[5]})")
        return

    with open(OUTPUT, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerows(new_rows)

    print(f"Appended {len(new_rows)} new pairs to {OUTPUT}")


if __name__ == "__main__":
    main()
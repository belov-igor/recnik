#!/usr/bin/env python3
"""
Import Russian→Serbian translations from Wiktionary via kaikki.org dump.

Source: https://kaikki.org/dictionary/Russian/
License: CC BY-SA 4.0 (Wiktionary)

Usage:
    python scripts/import_wiktionary.py [--dry-run]

Downloads the kaikki.org Russian JSONL dump, extracts entries that have
Serbian or Serbo-Croatian translations, and appends new pairs to
data/dictionary.tsv (skipping exact duplicates).
"""

import argparse
import csv
import gzip
import json
import sys
import urllib.request
from pathlib import Path

DUMP_URL = "https://kaikki.org/dictionary/downloads/ru/ru-extract.jsonl.gz"
OUTPUT = Path(__file__).parent.parent / "data" / "dictionary.tsv"

# kaikki.org lang_code values that represent Serbian / Serbo-Croatian
SERBIAN_CODES = {"sr", "srp", "hbs", "sh"}

POS_MAP = {
    "noun": "n",
    "verb": "v",
    "adj": "adj",
    "adjective": "adj",
    "adv": "adv",
    "adverb": "adv",
    "prep": "pr",
    "preposition": "pr",
    "conj": "conj",
    "conjunction": "conj",
    "pron": "prn",
    "pronoun": "prn",
    "num": "num",
    "numeral": "num",
    "particle": "part",
    "name": "np",
    "proper noun": "np",
}

GENDER_MAP = {
    "masculine": "m",
    "feminine": "f",
    "neuter": "nt",
}

ASPECT_MAP = {
    "imperfective": "impf",
    "perfective": "perf",
}


def load_existing(path: Path) -> set[tuple]:
    existing = set()
    if not path.exists():
        return existing
    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader, None)  # skip header
        for row in reader:
            if row:
                existing.add(tuple(row))
    return existing


def tags_to_meta(tags: list[str]) -> tuple[str, str]:
    gender = "-"
    aspect = "-"
    for t in tags:
        if t in GENDER_MAP and gender == "-":
            gender = GENDER_MAP[t]
        if t in ASPECT_MAP and aspect == "-":
            aspect = ASPECT_MAP[t]
    return gender, aspect


def is_latin(text: str) -> bool:
    latin = sum(1 for c in text if c.isascii() and c.isalpha())
    cyrillic = sum(1 for c in text if "\u0400" <= c <= "\u04ff")
    return latin > cyrillic


def extract_entries(line: bytes) -> list[tuple]:
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return []

    ru = obj.get("word", "").strip()
    if not ru or not any(c.isalpha() for c in ru):
        return []

    pos_raw = obj.get("pos", "")
    pos = POS_MAP.get(pos_raw, "-")

    entry_tags = obj.get("tags") or []
    gender, aspect = tags_to_meta(entry_tags)

    results = []
    for trans in obj.get("translations") or []:
        if trans.get("lang_code") not in SERBIAN_CODES:
            continue
        sr = (trans.get("word") or "").strip()
        if not sr or not any(c.isalpha() for c in sr):
            continue

        # skip Cyrillic translations — we store Latin only
        if not is_latin(sr):
            continue

        # refine gender/aspect from translation tags if still unknown
        t_tags = trans.get("tags") or []
        t_gender, t_aspect = tags_to_meta(t_tags)
        final_gender = gender if gender != "-" else t_gender
        final_aspect = aspect if aspect != "-" else t_aspect

        results.append((ru, sr, pos, final_gender, final_aspect, ""))

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print stats without writing to disk")
    args = parser.parse_args()

    print(f"Loading existing entries from {OUTPUT} ...")
    existing = load_existing(OUTPUT)
    print(f"  {len(existing)} existing pairs")

    print(f"Downloading {DUMP_URL} ...")
    new_rows = []
    seen = set(existing)
    processed = 0

    with urllib.request.urlopen(DUMP_URL) as resp:
        with gzip.open(resp, "rb") as gz:
            for raw_line in gz:
                processed += 1
                if processed % 50000 == 0:
                    print(f"  processed {processed:,} entries, "
                          f"{len(new_rows)} new so far ...", flush=True)

                for row in extract_entries(raw_line):
                    if row not in seen:
                        seen.add(row)
                        new_rows.append(row)

    print(f"Done. {processed:,} Wiktionary entries scanned.")
    print(f"New pairs found: {len(new_rows)}")

    if not new_rows:
        print("Nothing to add.")
        return

    if args.dry_run:
        print("-- dry run, not writing --")
        for row in new_rows[:20]:
            print("\t".join(row))
        return

    with open(OUTPUT, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerows(new_rows)

    print(f"Appended {len(new_rows)} new pairs to {OUTPUT}")


if __name__ == "__main__":
    main()
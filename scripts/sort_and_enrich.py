#!/usr/bin/env python3
"""
Sort, deduplicate, and enrich dictionary.tsv:
  1. Remove exact duplicate (ru, sr_lat) pairs
  2. Remove entries where ru field is not Russian (e.g. 'schip')
  3. Auto-fill pos/gender/aspect for entries with pos='-' via pymorphy3
  4. Sort alphabetically by Russian headword, then Serbian translation

Usage:
    python scripts/sort_and_enrich.py [--dry-run]
"""

import argparse
import csv
import sys
from pathlib import Path

import pymorphy3

DATA = Path(__file__).parent.parent / "data" / "dictionary.tsv"

morph = pymorphy3.MorphAnalyzer()

POS_MAP = {
    "NOUN": "n", "Name": "np",
    "VERB": "v", "INFN": "v", "GRND": "v",
    "ADJF": "adj", "ADJS": "adj", "COMP": "adj",
    "ADVB": "adv",
    "NPRO": "prn",
    "NUMR": "num",
    "PREP": "pr",
    "CONJ": "conj",
    "PRCL": "part",
}
GENDER_MAP = {"masc": "m", "femn": "f", "neut": "nt"}
ASPECT_MAP = {"impf": "impf", "perf": "perf"}

_CYRILLIC = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")


def is_russian(text: str) -> bool:
    """True if the text contains at least one Cyrillic letter."""
    return any(c in _CYRILLIC for c in text)


def enrich(row: dict) -> dict:
    """Fill pos/gender/aspect from pymorphy3 when pos is '-'."""
    if row["pos"] != "-":
        return row

    word = row["ru"].split()[0]  # parse first word only
    parses = morph.parse(word)
    if not parses:
        return row

    tag = parses[0].tag
    pos = POS_MAP.get(str(tag.POS), "-")
    gender = GENDER_MAP.get(str(tag.gender), "-") if tag.gender else "-"
    aspect = ASPECT_MAP.get(str(tag.aspect), "-") if tag.aspect else "-"

    if pos != "-":
        row = dict(row)
        row["pos"] = pos
        if row["gender"] == "-":
            row["gender"] = gender
        if row["aspect"] == "-":
            row["aspect"] = aspect

    return row


def sort_key(row: dict) -> tuple:
    return (row["ru"].lower(), row["sr_lat"].lower())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(DATA, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fieldnames = reader.fieldnames
        rows = list(reader)

    print(f"Loaded {len(rows)} rows")

    # 1. Remove non-Russian headwords
    bad_ru = [r for r in rows if not is_russian(r["ru"])]
    rows = [r for r in rows if is_russian(r["ru"])]
    print(f"Removed {len(bad_ru)} non-Russian entries: {[r['ru'] for r in bad_ru]}")

    # 2. Remove exact duplicates
    seen: set[tuple] = set()
    deduped = []
    dup_count = 0
    for r in rows:
        key = (r["ru"], r["sr_lat"])
        if key in seen:
            dup_count += 1
        else:
            seen.add(key)
            deduped.append(r)
    print(f"Removed {dup_count} exact duplicates")
    rows = deduped

    # 3. Enrich pos/gender/aspect
    enriched = 0
    new_rows = []
    for r in rows:
        new_r = enrich(r)
        if new_r["pos"] != r["pos"] or new_r["gender"] != r["gender"]:
            enriched += 1
        new_rows.append(new_r)
    rows = new_rows
    print(f"Enriched pos/gender/aspect for {enriched} entries")

    # 4. Sort
    rows.sort(key=sort_key)
    print(f"Sorted {len(rows)} rows alphabetically")

    print(f"\nResult: {len(rows)} rows")

    if args.dry_run:
        print("-- dry run, not writing --")
        return

    with open(DATA, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Written to {DATA}")


if __name__ == "__main__":
    main()
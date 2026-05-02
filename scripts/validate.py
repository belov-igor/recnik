#!/usr/bin/env python3
"""
Validate data/dictionary.tsv for contributor PRs and CI.

Checks:
  - Required columns present
  - No empty ru or sr_lat fields
  - No Cyrillic characters in sr_lat
  - No Latin characters in ru (basic check)
  - Valid values for pos, gender, aspect
  - No exact duplicate (ru, sr_lat) pairs
  - No entries with 4+ words (long phrases / proverbs)

Exit code 0 = valid, 1 = errors found.

Usage:
    python scripts/validate.py [--warn-long]
"""

import argparse
import csv
import re
import sys
from pathlib import Path

DATA = Path(__file__).parent.parent / "data" / "dictionary.tsv"

VALID_POS = {"n", "v", "adj", "adv", "pr", "conj", "prn", "num", "part", "np", "-"}
VALID_GENDER = {"m", "f", "nt", "-"}
VALID_ASPECT = {"perf", "impf", "both", "-"}

_CYRILLIC = re.compile(r"[а-яёА-ЯЁ]")
_LATIN_IN_RU = re.compile(r"[a-zA-Z]")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--warn-long", action="store_true",
                        help="Warn (not error) on entries with 4+ words")
    args = parser.parse_args()

    with open(DATA, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if reader.fieldnames is None:
            print("ERROR: empty file")
            sys.exit(1)

        required = {"ru", "sr_lat", "pos", "gender", "aspect"}
        missing_cols = required - set(reader.fieldnames)
        if missing_cols:
            print(f"ERROR: missing columns: {missing_cols}")
            sys.exit(1)

        rows = list(reader)

    errors = []
    warnings = []
    seen: set[tuple] = set()

    for i, r in enumerate(rows, start=2):  # line 1 = header
        ru = r["ru"].strip()
        sr = r["sr_lat"].strip()
        pos = r["pos"].strip()
        gender = r["gender"].strip()
        aspect = r["aspect"].strip()

        def err(msg):
            errors.append(f"  line {i}: [{ru!r}] {msg}")

        def warn(msg):
            warnings.append(f"  line {i}: [{ru!r}] {msg}")

        if not ru:
            err("empty 'ru' field")
        if not sr:
            err("empty 'sr_lat' field")

        if ru and _LATIN_IN_RU.search(ru) and not ru.isupper():
            # Allow abbreviations like США, ООН — already isupper check skips those
            # Flag only mixed-case Latin in Russian headword
            err(f"Latin characters in 'ru': {ru!r}")

        if sr and _CYRILLIC.search(sr):
            err(f"Cyrillic characters in 'sr_lat': {sr!r}")

        if pos not in VALID_POS:
            err(f"invalid pos={pos!r} (valid: {sorted(VALID_POS)})")
        if gender not in VALID_GENDER:
            err(f"invalid gender={gender!r} (valid: {sorted(VALID_GENDER)})")
        if aspect not in VALID_ASPECT:
            err(f"invalid aspect={aspect!r} (valid: {sorted(VALID_ASPECT)})")

        key = (ru, sr)
        if key in seen:
            err(f"duplicate pair ({ru!r}, {sr!r})")
        else:
            seen.add(key)

        word_count = len(ru.split())
        if word_count >= 4:
            (warn if args.warn_long else err)(
                f"entry has {word_count} words (long phrase/proverb?)"
            )

    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(w)

    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for e in errors:
            print(e)
        print(f"\nValidation FAILED — {len(errors)} error(s) in {DATA.name}")
        sys.exit(1)

    print(f"OK — {len(rows)} entries validated, {len(warnings)} warning(s)")


if __name__ == "__main__":
    main()
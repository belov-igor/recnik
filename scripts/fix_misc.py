#!/usr/bin/env python3
"""
Miscellaneous targeted fixes to dictionary.tsv:
  - Remove suffix/prefix non-words (-ец, -ость, авто-, внутри-, псевдо-)
  - Remove prefix fragment нью (not a standalone word)
  - Fix Latin 'c' in cпектральный → спектральный
  - Remove Tatoeba noise translations for нужно and спасибо
  - Assign pos=np to Russian abbreviations (all-caps, ≥2 chars)
  - Assign known POS to влюблён, жаль, здравствуйте

Usage:
    python scripts/fix_misc.py [--dry-run]
"""

import argparse
import csv
import re
from pathlib import Path

DATA = Path(__file__).parent.parent / "data" / "dictionary.tsv"

# Tatoeba noise translations to remove for specific Russian words
NOISE = {
    "нужно": {"imam", "koliko", "mnogo", "moj", "moram", "nam",
               "nešto", "novca", "radim", "više"},
    "спасибо": {"mnogo", "puno", "vam"},
}

# Manual POS assignments for entries that can't be auto-detected
MANUAL_POS = {
    "влюблён":                    ("adj",  "-",  "-"),
    "жаль":                       ("part", "-",  "-"),
    "здравствуйте":               ("part", "-",  "-"),
    "покрыто":                    ("adj",  "nt", "-"),
    "ах так":                     ("part", "-",  "-"),
    "газированная вода":          ("n",    "f",  "-"),
    "добавленная стоимость":      ("n",    "f",  "-"),
    "населённый пункт":           ("n",    "m",  "-"),
    "нужно":                      ("part", "-",  "-"),
    "Объединённые Арабские Эмираты": ("np", "-", "-"),
    "отводящий нерв":             ("n",    "m",  "-"),
    "пропавший без вести":        ("adj",  "m",  "-"),
    "сгущённое молоко":           ("n",    "nt", "-"),
    "сжиженный природный газ":    ("n",    "m",  "-"),
    "Соединённые Штаты Америки":  ("np",   "-",  "-"),
    "Спящая красавица":           ("np",   "f",  "-"),
}

_ABBREV_RE = re.compile(r"^[А-ЯЁ]{2,}$")  # all-caps Cyrillic ≥2 chars


def is_prefix_or_suffix(ru: str) -> bool:
    return ru.startswith("-") or ru.endswith("-")


def fix_latin_c(ru: str) -> str:
    """Replace leading Latin 'c' before Cyrillic with Cyrillic 'с'."""
    if ru and ru[0] == "c" and len(ru) > 1 and "\u0400" <= ru[1] <= "\u04ff":
        return "с" + ru[1:]
    return ru


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(DATA, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fieldnames = reader.fieldnames
        rows = list(reader)

    print(f"Loaded {len(rows)} rows")
    removed = 0
    fixed = 0

    result = []
    for r in rows:
        ru = r["ru"]

        # 1. Remove suffix/prefix entries and нью
        if is_prefix_or_suffix(ru) or ru == "нью":
            removed += 1
            continue

        # 2. Remove Tatoeba noise translations
        if ru in NOISE and r["sr_lat"] in NOISE[ru]:
            removed += 1
            continue

        # 3. Fix Latin 'c' → Cyrillic 'с'
        ru_fixed = fix_latin_c(ru)
        if ru_fixed != ru:
            r = dict(r)
            r["ru"] = ru_fixed
            fixed += 1
            print(f"  Fixed: {ru!r} → {ru_fixed!r}")

        # 4. Abbreviations → pos=np
        if _ABBREV_RE.match(ru) and r["pos"] == "-":
            r = dict(r)
            r["pos"] = "np"
            fixed += 1

        # 5. Manual POS assignments
        if ru in MANUAL_POS and r["pos"] == "-":
            r = dict(r)
            pos, gender, aspect = MANUAL_POS[ru]
            r["pos"] = pos
            if r["gender"] == "-":
                r["gender"] = gender
            if r["aspect"] == "-":
                r["aspect"] = aspect
            fixed += 1

        result.append(r)

    print(f"Removed: {removed} rows")
    print(f"Fixed:   {fixed} rows")
    print(f"Result:  {len(result)} rows")

    if args.dry_run:
        print("-- dry run, not writing --")
        return

    with open(DATA, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(result)
    print(f"Written to {DATA}")


if __name__ == "__main__":
    main()
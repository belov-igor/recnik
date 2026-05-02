#!/usr/bin/env python3
"""
Dictionary quality cleanup:
  1. Remove long phrases / proverbs (≥4 words in either column)
  2. Extract Russian lemmas from removed phrases and report missing ones
  3. Normalize Tatoeba verb conjugations to infinitives via pymorphy3

Usage:
    python scripts/cleanup_quality.py [--dry-run]
"""

import argparse
import csv
import sys
from pathlib import Path

import pymorphy3

sys.path.insert(0, str(Path(__file__).parent))

DATA = Path(__file__).parent.parent / "data" / "dictionary.tsv"

morph = pymorphy3.MorphAnalyzer()

# Russian stop-words — skip when extracting lemmas from proverbs
RU_STOP = {
    "и", "в", "не", "на", "что", "с", "по", "а", "к", "но", "из", "за",
    "от", "до", "как", "у", "о", "об", "или", "же", "ли", "бы", "то",
    "всё", "все", "так", "уже", "ещё", "да", "ни", "при", "без", "до",
    "это", "тот", "та", "те", "этот", "эта", "который", "свой",
    "быть", "есть", "был", "была", "было", "были",
    "один", "два", "первый", "второй",
    "мой", "твой", "его", "её", "наш", "ваш", "их",
}

# Known Serbian conjugation → infinitive mappings extracted from Tatoeba
# (Serbian → Serbian infinitive, used to normalise sr_lat side)
SR_CONJ_TO_INF = {
    "volim": "voliti", "voliš": "voliti", "voli": "voliti",
    "volimo": "voliti", "volite": "voliti", "vole": "voliti",
    "znam": "znati", "znaš": "znati", "zna": "znati",
    "znamo": "znati", "znate": "znati", "znaju": "znati",
    "mogu": "moći", "možeš": "moći", "može": "moći",
    "možemo": "moći", "možete": "moći", "mogu": "moći",
    "želim": "željeti", "želiš": "željeti", "želi": "željeti",
    "mislim": "misliti", "misliš": "misliti", "misli": "misliti",
    "mislimo": "misliti", "mislite": "misliti", "misle": "misliti",
    "rekao": "reći", "rekla": "reći", "rekli": "reći",
    "radi": "raditi", "radiš": "raditi", "radim": "raditi",
    "radimo": "raditi", "radite": "raditi", "rade": "raditi",
    "idem": "ići", "ideš": "ići", "ide": "ići",
    "idemo": "ići", "idete": "ići", "idu": "ići",
    "imam": "imati", "imaš": "imati", "ima": "imati",
    "imamo": "imati", "imate": "imati", "imaju": "imati",
    "video": "videti", "videla": "videti", "videli": "videti",
    "vidim": "videti", "vidiš": "videti", "vidi": "videti",
    "kupio": "kupiti", "kupila": "kupiti", "kupili": "kupiti",
    "kupim": "kupiti", "kupiš": "kupiti", "kupi": "kupiti",
    "živim": "živeti", "živiš": "živeti", "živi": "živeti",
    "sviđa": "sviđati se",
    "treba": "trebati",
    "razumem": "razumeti", "razumeš": "razumeti", "razume": "razumeti",
    "napisao": "napisati", "napisala": "napisati", "napisali": "napisati",
    "pričam": "pričati", "pričaš": "pričati", "priča": "pričati",
    "učim": "učiti", "učiš": "učiti", "uči": "učiti",
    "čitam": "čitati", "čitaš": "čitati", "čita": "čitati",
    "govorim": "govoriti", "govoriš": "govoriti", "govori": "govoriti",
    "pitam": "pitati", "pitaš": "pitati", "pita": "pitati",
    "tražim": "tražiti", "tražiš": "tražiti", "traži": "tražiti",
    "volela": "voleti", "voleo": "voleti", "voleli": "voleti",
}


def lemmatize_ru(word: str) -> str:
    parses = morph.parse(word)
    if parses:
        return parses[0].normal_form
    return word


def is_conjugated_ru(word: str) -> bool:
    """True if the word looks like a non-infinitive verb form."""
    parses = morph.parse(word)
    if not parses:
        return False
    p = parses[0]
    tag = p.tag
    if "VERB" not in str(tag) and "GRND" not in str(tag):
        return False
    # infinitive has INFN tag
    return "INFN" not in str(tag)


def load_tsv(path: Path) -> tuple[list[dict], list[str]]:
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fieldnames = reader.fieldnames
        rows = list(reader)
    return rows, fieldnames


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows, fieldnames = load_tsv(DATA)
    print(f"Loaded {len(rows)} rows")

    # ------------------------------------------------------------------ #
    # 1. Separate long phrases from normal entries
    # ------------------------------------------------------------------ #
    keep = []
    removed_phrases = []
    for r in rows:
        ru_words = len(r["ru"].split())
        sr_words = len(r["sr_lat"].split())
        if ru_words >= 4 or sr_words >= 4:
            removed_phrases.append(r)
        else:
            keep.append(r)

    print(f"\nStep 1 — long phrases removed: {len(removed_phrases)}")

    # ------------------------------------------------------------------ #
    # 2. Extract lemmas from removed phrases, find gaps in dictionary
    # ------------------------------------------------------------------ #
    existing_ru = {r["ru"].lower() for r in keep}
    candidate_lemmas: set[str] = set()

    for r in removed_phrases:
        for word in r["ru"].split():
            word_clean = word.strip(",.!?—–«»\"'();:")
            if not word_clean or word_clean.lower() in RU_STOP:
                continue
            if not any(c.isalpha() for c in word_clean):
                continue
            lemma = lemmatize_ru(word_clean)
            if lemma.lower() not in existing_ru and len(lemma) > 2:
                candidate_lemmas.add(lemma)

    print(f"\nStep 2 — Russian lemmas from removed phrases not in dictionary: {len(candidate_lemmas)}")
    for lm in sorted(candidate_lemmas)[:30]:
        print(f"  {lm}")
    if len(candidate_lemmas) > 30:
        print(f"  ... and {len(candidate_lemmas) - 30} more")

    # ------------------------------------------------------------------ #
    # 3. Normalise Tatoeba conjugated verbs to infinitives
    # ------------------------------------------------------------------ #
    normalised = 0
    skipped_dup = 0
    existing_pairs = {(r["ru"], r["sr_lat"]) for r in keep}

    for r in keep:
        if "tatoeba:" not in r.get("notes", ""):
            continue
        if not is_conjugated_ru(r["ru"]):
            continue

        ru_inf = lemmatize_ru(r["ru"])
        sr_inf = SR_CONJ_TO_INF.get(r["sr_lat"], r["sr_lat"])

        if ru_inf == r["ru"] and sr_inf == r["sr_lat"]:
            continue  # nothing to change

        new_pair = (ru_inf, sr_inf)
        if new_pair in existing_pairs:
            # normalised form already exists — drop this conjugated entry
            r["_drop"] = True
            skipped_dup += 1
            continue

        existing_pairs.add(new_pair)
        r["ru"] = ru_inf
        r["sr_lat"] = sr_inf
        normalised += 1

    keep = [r for r in keep if not r.get("_drop")]
    print(f"\nStep 3 — Tatoeba conjugations normalised: {normalised}, duplicates dropped: {skipped_dup}")

    # ------------------------------------------------------------------ #
    # Summary
    # ------------------------------------------------------------------ #
    print(f"\nResult: {len(rows)} → {len(keep)} rows")
    print(f"  Removed phrases:  {len(removed_phrases)}")
    print(f"  Dropped dup conj: {skipped_dup}")
    net = len(rows) - len(keep)
    print(f"  Net reduction:    {net}")

    if args.dry_run:
        print("\n-- dry run, not writing --")
        return

    # Clean up internal key before writing
    for r in keep:
        r.pop("_drop", None)

    with open(DATA, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(keep)

    print(f"\nWritten {len(keep)} rows to {DATA}")


if __name__ == "__main__":
    main()
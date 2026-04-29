#!/usr/bin/env python3
"""
One-time import from Apertium apertium-hbs-rus bilingual dictionary (.dix)
to project TSV format.

Source: https://github.com/apertium/apertium-hbs-rus
Usage: python scripts/import_apertium.py
"""

import csv
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

DIX_URL = (
    "https://raw.githubusercontent.com/apertium/apertium-hbs-rus"
    "/master/apertium-hbs-rus.hbs-rus.dix"
)
OUTPUT = Path(__file__).parent.parent / "data" / "dictionary.tsv"

POS_MAP = {
    "n": "n",
    "np": "np",
    "vblex": "v",
    "vbmod": "v",
    "vbser": "v",
    "adj": "adj",
    "adv": "adv",
    "pr": "pr",
    "prn": "prn",
    "cnjcoo": "conj",
    "cnjsub": "conj",
    "num": "num",
    "part": "part",
}

GENDER_TAGS = {"m", "f", "nt", "mf", "mfn"}
ASPECT_TAGS = {"perf", "impf", "dual"}
TRANSITIVITY_TAGS = {"tv", "iv", "ref"}


def extract(elem):
    """Return (text, [tag_names]) from <l> or <r> element."""
    parts = [elem.text or ""]
    tags = []
    for child in elem:
        if child.tag == "b":
            parts.append(" ")
        elif child.tag == "s":
            tags.append(child.get("n", ""))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts).strip(), tags


def classify(l_tags, r_tags):
    pos, gender, aspect, notes = "-", "-", "-", ""
    note_parts = []

    for tag in l_tags:
        if tag in POS_MAP:
            pos = POS_MAP[tag]
        elif tag in GENDER_TAGS:
            gender = tag
        elif tag in ASPECT_TAGS:
            aspect = "both" if tag == "dual" else tag
        elif tag in TRANSITIVITY_TAGS:
            note_parts.append(tag)

    # fill missing gender/aspect from Russian side if absent on Serbian side
    for tag in r_tags:
        if tag in GENDER_TAGS and gender == "-":
            gender = tag
        elif tag in ASPECT_TAGS and aspect == "-":
            aspect = "both" if tag == "dual" else tag

    notes = ",".join(note_parts)
    return pos, gender, aspect, notes


def main():
    print(f"Downloading {DIX_URL} ...")
    with urllib.request.urlopen(DIX_URL) as resp:
        content = resp.read()

    root = ET.fromstring(content)
    rows = []
    skipped = 0

    for entry in root.iter("e"):
        pair = entry.find("p")
        if pair is None:
            continue
        l_elem = pair.find("l")
        r_elem = pair.find("r")
        if l_elem is None or r_elem is None:
            continue

        sr_lat, l_tags = extract(l_elem)
        ru, r_tags = extract(r_elem)

        if not sr_lat or not ru:
            skipped += 1
            continue

        # skip punctuation and single non-letter tokens
        if not any(c.isalpha() for c in ru) or not any(c.isalpha() for c in sr_lat):
            skipped += 1
            continue

        pos, gender, aspect, notes = classify(l_tags, r_tags)
        rows.append((ru, sr_lat, pos, gender, aspect, notes))

    # deduplicate exact rows
    rows = list(dict.fromkeys(rows))

    # sort: POS bucket first, then Russian lemma alphabetically
    rows.sort(key=lambda r: (r[2], r[0].lower()))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["ru", "sr_lat", "pos", "gender", "aspect", "notes"])
        writer.writerows(rows)

    print(f"Done: {len(rows)} entries → {OUTPUT}")
    if skipped:
        print(f"Skipped {skipped} empty entries")


if __name__ == "__main__":
    main()
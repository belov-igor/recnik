#!/usr/bin/env python3
"""
Add ekavian (Serbian standard) variants for ijekavian entries.

Ijekavian (Bosnian/Croatian/some Serbian) uses historical yat reflexes:
  long yat:  ije → e  (bijel, lijep, vrijeme)
  short yat: je  → e  (vjera, mjesto, pjesma)

Ekavian (Serbian standard) collapses these to 'e':
  bijel → beo (irregular!), lijep → lep, vrijeme → vreme
  vjera → vera, mjesto → mesto, pjesma → pesma

Rules applied here cover the common regular cases.
Irregular forms (bijel→beo, dijete→dete, etc.) handled explicitly.
"""

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from transliterate import lat_to_cyr

DATA = Path(__file__).parent.parent / "data" / "dictionary.tsv"

# Explicit irregular mappings (ijekavian → ekavian)
IRREGULARS = {
    "bijel":    "beo",
    "bijela":   "bela",
    "bijeli":   "beli",
    "dijete":   "dete",
    "djeca":    "deca",
    "mlijeko":  "mleko",
    "slijep":   "slep",
    "slijepa":  "slepa",
    "trijezan": "trezan",
    "lijepo":   "lepo",
}


def ije_to_ekavian(word: str) -> str | None:
    """Convert ijekavian word to ekavian. Returns None if no conversion applies.

    Only handles long yat (ije→e) to avoid false positives with digraphs lj/nj.
    Short yat (je→e) is skipped — too many non-yat 'je' sequences in Serbian.
    """
    lower = word.lower()

    # Check irregulars first
    if lower in IRREGULARS:
        result = IRREGULARS[lower]
        return result[0].upper() + result[1:] if word[0].isupper() else result

    if "ije" not in lower:
        return None

    # Skip non-yat 'ije' patterns:
    # - past participles: -ijen, -ijena, -ijeni (nabijen, razbijen, razvijen)
    if re.search(r'ijena?i?$', lower):
        return None
    # - foreign/loan words containing -ofici-, -oficial-
    if re.search(r'ofici', lower):
        return None
    # - prijem (pri+imati, not yat)
    if "prijem" in lower:
        return None

    # Long yat only: ije → e
    changed = word
    changed = re.sub(r'ije', 'e', changed)
    changed = re.sub(r'Ije', 'E', changed)

    return changed if changed != word else None


def main():
    with open(DATA, encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    existing_pairs = {(r["ru"], r["sr_lat"]) for r in rows}
    new_rows = []

    for r in rows:
        sr_lat = r["sr_lat"]
        ekavian = ije_to_ekavian(sr_lat)
        if ekavian and ekavian != sr_lat:
            pair = (r["ru"], ekavian)
            if pair not in existing_pairs:
                new_rows.append({
                    "ru":     r["ru"],
                    "sr_lat": ekavian,
                    "pos":    r["pos"],
                    "gender": r["gender"],
                    "aspect": r["aspect"],
                    "notes":  r["notes"],
                })
                existing_pairs.add(pair)

    if not new_rows:
        print("No new ekavian variants found.")
        return

    # Preview
    print(f"New ekavian variants: {len(new_rows)}")
    for r in new_rows[:20]:
        orig = next(x["sr_lat"] for x in rows if x["ru"] == r["ru"])
        print(f"  {r['ru']:20} {orig:20} → {r['sr_lat']}")
    if len(new_rows) > 20:
        print(f"  ... and {len(new_rows) - 20} more")

    # Append and sort
    all_rows = rows + new_rows
    all_rows.sort(key=lambda r: (r["pos"], r["ru"].lower()))

    with open(DATA, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ru", "sr_lat", "pos", "gender", "aspect", "notes"],
                                delimiter="\t")
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nTotal entries: {len(all_rows)} (+{len(new_rows)})")


if __name__ == "__main__":
    main()
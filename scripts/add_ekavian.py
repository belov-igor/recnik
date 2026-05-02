#!/usr/bin/env python3
"""
Add ekavian variants for confirmed ijekavian entries.

Applies ije→e only to words where 'ije' is a genuine Old Slavic yat reflex,
verified manually. Loanwords, proper nouns, genitives of -ija words,
verb conjugation endings (-ijen past participle), and comparative -ije
suffixes are excluded.

Usage:
    python scripts/add_ekavian.py [--dry-run]
"""

import argparse
import csv
from pathlib import Path

DATA = Path(__file__).parent.parent / "data" / "dictionary.tsv"

EKAVIAN: dict[str, str] = {
    "bijeda": "beda", "bijedan": "bedan", "bijeg": "beg",
    "bijel": "bel", "bijelo vino": "belo vino", "bijes": "bes",
    "bijesan": "besan", "Bijelo more": "Belo more", "blijed": "bled",
    "brijeg": "breg",
    "cijel": "cel", "cijelo": "celo", "cijena": "cena",
    "cijenjen": "cenjen", "cijepati": "cepati", "cijev": "cev",
    "crijevo": "crevo", "cvijet": "cvet",
    "dijeliti": "deliti", "dijete": "dete",
    "donijeti": "doneti", "drijemati": "dremati",
    "gnijezdo": "gnezdo", "grijeh": "greh",
    "izmijeniti": "izmeniti", "iznijeti": "izneti",
    "još uvijek": "još uvek",
    "kondenzirano mlijeko": "kondenzirano mleko", "korijen": "koren",
    "lijek": "lek", "lijep": "lep", "lijepi": "lepi", "lijepo": "lepo",
    "lijes": "les", "lijevi": "levi", "lijevo": "levo",
    "liječenje": "lečenje", "liječiti": "lečiti", "liječnik": "lečnik",
    "mijenjati": "menjati", "miješati": "mešati",
    "mlijeko": "mleko", "mliječan": "mlečan",
    "na vrijeme": "na vreme", "namijera": "namera",
    "nanijeti": "naneti", "naprijed": "napred",
    "nasmiješiti": "nasmešiti",
    "necijenovna konkurencija": "necenovna konkurencija",
    "nelijep": "nelep", "neopredijeljen": "neopredeljen",
    "nerijetko": "neretko",
    "obavijestiti": "obavestiti", "obezbijediti": "obezbediti",
    "ocijeniti": "oceniti", "opredijeliti": "opredeliti",
    "pijesak": "pesak", "pobijediti": "pobediti",
    "pocijepati": "pocepati", "podijeliti": "podeliti",
    "podnijeti": "podneti", "pogriješiti": "pogrešiti",
    "pomiješati": "pomešati", "ponijeti": "poneti",
    "poprijeko": "popreko", "porijeklo": "poreklo",
    "poslije": "posle", "prelijep": "prelep", "prelijepo": "prelepo",
    "prenijeti": "preneti", "prije": "pre", "prijedlog": "predlog",
    "prijetiti": "pretiti", "primijetiti": "primetiti",
    "promijeniti": "promeniti",
    "razdijeliti": "razdeliti", "rijedak": "redak",
    "rijeka": "reka", "rijetko": "retko", "riječ": "reč",
    "riječica": "rečica", "riješiti": "rešiti",
    "sijed": "sed", "sijeno": "seno", "slijediti": "slediti",
    "slijep": "slep", "slijeva": "sleva", "smijeh": "smeh",
    "smijeniti": "smeniti", "smiješan": "smešan",
    "smiješiti": "smešiti", "smiješno": "smešno",
    "snabdijevati": "snabdevati", "snijeg": "sneg",
    "sprijeda": "spreda", "stijena": "stena",
    "strijela": "strela", "strijelac": "strelac",
    "strijeljati": "streljati", "strijemiti": "stremiti",
    "svijest": "svest", "svijet": "svet", "svijetao": "svetao",
    "svijetliti": "svetliti", "svijetlo": "svetlo", "svijeća": "sveća",
    "tijelo": "telo", "tijesan": "tesan", "tijesno": "tesno",
    "tijesto": "testo", "trijezan": "trezan",
    "ubijediti": "ubediti", "umiješati": "umešati",
    "umrijeti": "umreti", "unijeti": "uneti",
    "upotrijebiti": "upotrebiti", "uprijeti": "upreti",
    "uspijevati": "uspevati", "ustrijemiti": "ustremiti",
    "uvijek": "uvek", "vijek": "vek", "vijerno": "verno",
    "vijest": "vest", "vrijedan": "vredan", "vrijednost": "vrednost",
    "vrijeme": "vreme", "vrsta riječi": "vrsta reči",
    "zamijeniti": "zameniti", "zanijeti": "zaneti",
    "zaplijenjen": "zaplenjen", "zapovijest": "zapovest",
    "zaprijetiti": "zapretiti", "zauvijek": "zauvek",
    "zvijer": "zver", "zvijezda": "zvezda", "ždrijebe": "ždrebe",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(DATA, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fieldnames = reader.fieldnames
        rows = list(reader)

    existing = {(r["ru"], r["sr_lat"]) for r in rows}
    new_rows = []

    for r in rows:
        sr = r["sr_lat"]
        if sr not in EKAVIAN:
            continue
        ek = EKAVIAN[sr]
        pair = (r["ru"], ek)
        if pair in existing:
            continue
        new_row = dict(r)
        new_row["sr_lat"] = ek
        new_rows.append(new_row)
        existing.add(pair)

    print(f"New ekavian pairs: {len(new_rows)}")
    if args.dry_run:
        print("-- dry run --")
        for r in new_rows:
            print(f"  {r['ru']:25} {r['sr_lat']}")
        return

    with open(DATA, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writerows(new_rows)

    print(f"Appended {len(new_rows)} rows to {DATA}")


if __name__ == "__main__":
    main()

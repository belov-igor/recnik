#!/usr/bin/env python3
"""
Build 4 Kindle dictionary .mobi files from data/dictionary.tsv.

Requirements:
  pip install pymorphy2 pyglossary
  Calibre installed (ebook-convert in PATH): https://calibre-ebook.com/

Dictionaries produced:
  ru-sr-latin.mobi      Russian → Serbian Latin
  ru-sr-cyrillic.mobi   Russian → Serbian Cyrillic
  sr-latin-ru.mobi      Serbian Latin → Russian
  sr-cyrillic-ru.mobi   Serbian Cyrillic → Russian
"""

import csv
import shutil
import subprocess
import sys
import textwrap
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pymorphy3 as pymorphy2

sys.path.insert(0, str(Path(__file__).parent))
from transliterate import lat_to_cyr

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data" / "dictionary.tsv"
OUTPUT = ROOT / "output"

morph = pymorphy2.MorphAnalyzer()


# ---------------------------------------------------------------------------
# Morphology
# ---------------------------------------------------------------------------

def ru_inflections(word: str) -> list[str]:
    """Return all inflected forms of a Russian word via pymorphy2."""
    parses = morph.parse(word)
    if not parses:
        return []
    forms = {f.word for f in parses[0].lexeme}
    forms.discard(word)
    return sorted(forms)


def sr_inflections(word: str, pos: str, gender: str) -> list[str]:
    """
    Serbian inflection rules for Kindle lookup.
    Covers all 7 cases (sg + pl) for nouns, main adjectival forms,
    and present/past conjugation for verbs.
    """
    forms: set[str] = set()
    if pos == "n":
        _sr_noun(word, gender, forms)
    elif pos == "adj":
        _sr_adj(word, forms)
    elif pos == "v":
        _sr_verb(word, forms)
    forms.discard(word)
    return sorted(forms)


# soft-final consonants trigger -ev- plural in masculine nouns
_SOFT = ("j", "š", "č", "ž", "ć", "đ", "c", "lj", "nj")


def _sr_noun(word: str, gender: str, forms: set) -> None:
    if gender == "f":
        _sr_noun_f(word, forms)
    elif gender == "m":
        _sr_noun_m(word, forms)
    elif gender == "nt":
        _sr_noun_nt(word, forms)


def _sr_noun_f(word: str, forms: set) -> None:
    if word.endswith("a"):
        stem = word[:-1]
        forms.update([
            stem + "e",    # gen sg / nom+acc pl
            stem + "i",    # dat sg / loc sg
            stem + "u",    # acc sg
            stem + "om",   # ins sg
            stem + "o",    # voc sg
            stem + "ama",  # dat / ins / loc pl
        ])
    else:
        # consonant-final feminines: radost, ljubav, noć, reč …
        forms.update([
            word + "i",    # gen / dat / loc sg, nom+acc pl
            word + "ima",  # dat / ins / loc pl
            word + "ju",   # ins sg (noću, radošću)
        ])


def _sr_noun_m(word: str, forms: set) -> None:
    # fleeting-a: -ac / -ec → drop the -a- before the final consonant
    if len(word) > 3 and word[-2] == "a" and word.endswith(("ac", "ec")):
        stem = word[:-2] + word[-1]   # lovac → lovc, stranac → stranc
        forms.update([
            stem + "a",    # gen sg
            stem + "u",    # dat / loc sg
            stem + "om",   # ins sg
            stem + "e",    # voc sg / acc pl
            stem + "i",    # nom pl
            stem + "ima",  # dat / ins / loc pl
        ])
        return

    soft = any(word.endswith(s) for s in _SOFT)
    ext = "ev" if soft else "ov"

    forms.update([
        word + "a",          # gen sg
        word + "u",          # dat / loc sg
        word + "om",         # ins sg
        word + "e",          # voc sg
        # plural
        word + "i",          # nom pl (vojnici, studenti, lekari)
        word + ext + "i",    # nom pl alt (gradovi, miševi)
        word + ext + "a",    # gen pl
        word + ext + "e",    # acc pl
        word + ext + "ima",  # dat / ins / loc pl
        word + "ima",        # dat / ins / loc pl alt
    ])


def _sr_noun_nt(word: str, forms: set) -> None:
    if word.endswith(("o", "e")):
        stem = word[:-1]
        ins = stem + ("om" if word.endswith("o") else "em")
        forms.update([
            stem + "a",    # gen sg / nom + acc + gen pl
            stem + "u",    # dat / loc sg
            ins,           # ins sg
            stem + "ima",  # dat / ins / loc pl
        ])


def _sr_adj(word: str, forms: set) -> None:
    # stored headword is typically long masc definite: veliki, crni, dobar …
    if word.endswith("i") and len(word) > 3:
        stem = word[:-1]
        forms.update([
            stem + "a",    # f nom / m+nt gen sg (dobra, velikog → dobrog)
            stem + "o",    # nt nom sg
            stem + "og",   # m / nt gen sg
            stem + "oga",  # gen sg long
            stem + "om",   # m / nt dat / ins / loc sg
            stem + "ome",  # dat / loc alt
            stem + "oj",   # f dat / loc sg
            stem + "u",    # f acc sg
            stem + "im",   # m / nt ins sg / pl dat + ins + loc
            stem + "ih",   # pl gen
            stem + "e",    # f gen sg / pl acc (f + nt)
        ])
    elif word.endswith(("an", "en", "ov", "ev", "in", "ar", "at")):
        # short-form base: crven, nov, star …
        forms.update([
            word + "a",    # f nom / m+nt gen
            word + "o",    # nt nom
            word + "og",   # m / nt gen
            word + "om",   # m / nt dat / ins / loc
            word + "oj",   # f dat / loc
            word + "u",    # f acc
            word + "im",   # ins sg / pl dat+ins+loc
            word + "ih",   # pl gen
            word + "e",    # f gen / pl acc
            word + "i",    # pl nom (m) / long form
        ])
    else:
        stem = word.rstrip("aeiou") if word and word[-1] in "aeiou" else word
        for sfx in ("a", "o", "e", "i", "og", "om", "oj", "u", "im", "ih"):
            forms.add(stem + sfx)


def _sr_verb(word: str, forms: set) -> None:
    if not word.endswith("ti"):
        return

    # -ovati / -evati / -ivati: putovati → putujem …
    for ending in ("ovati", "evati", "ivati"):
        if word.endswith(ending):
            base = word[:-len(ending)]
            forms.update([
                base + "ujem", base + "uješ", base + "uje",
                base + "ujemo", base + "ujete", base + "uju",
                base + "ovao", base + "ovala", base + "ovalo", base + "ovali",
                base + "uj",   # imperative sg
                base + "ujte", # imperative pl
            ])
            return

    # -nuti: mahnuti → mahnem …
    if word.endswith("nuti"):
        base = word[:-4]
        forms.update([
            base + "nem", base + "neš", base + "ne",
            base + "nemo", base + "nete", base + "nu",
            base + "nuo", base + "nula", base + "nulo", base + "nuli",
            base + "ni", base + "nite",
        ])
        return

    # -ati: čitati, pisati …  (pres stem = inf[:-2], i.e. čita-)
    if word.endswith("ati"):
        ps = word[:-2]   # čita-
        forms.update([
            ps + "m", ps + "š", ps,
            ps + "mo", ps + "te", ps + "ju",
            ps + "o", ps + "la", ps + "lo", ps + "li", ps + "le",
            ps + "j",   # imperative sg (čitaj)
            ps + "jte", # imperative pl
        ])
        return

    # -iti / -eti / -jeti: govoriti, voleti …  (pres stem = inf[:-3], i.e. govor-)
    if word.endswith(("iti", "eti", "jeti")):
        base = word[:-3] if word.endswith(("iti", "eti")) else word[:-4]
        forms.update([
            base + "im", base + "iš", base + "i",
            base + "imo", base + "ite", base + "e",
            base + "io", base + "eo",   # m sg past (one will be wrong, harmless)
            base + "ila", base + "ilo", base + "ili", base + "ile",
        ])
        return


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

@dataclass
class Entry:
    headword: str       # lookup key shown to Kindle
    display: str        # headword shown in entry body
    translation: str
    pos: str
    gender: str
    aspect: str
    notes: str
    inflections: list[str]


def load_entries_ru_to_sr(rows: list[dict], script: str) -> list[Entry]:
    """Russian headword → Serbian translation."""
    grouped: dict[str, list] = {}
    for r in rows:
        grouped.setdefault(r["ru"], []).append(r)

    entries = []
    for ru_word, group in sorted(grouped.items(), key=lambda x: x[0].lower()):
        translations = []
        for r in group:
            sr = lat_to_cyr(r["sr_lat"]) if script == "cyrillic" else r["sr_lat"]
            label = _pos_label(r["pos"], r["gender"], r["aspect"])
            translations.append((sr, label, r["notes"]))

        inflections = ru_inflections(ru_word)
        entry = Entry(
            headword=ru_word,
            display=ru_word,
            translation=_format_translations(translations),
            pos=group[0]["pos"],
            gender=group[0]["gender"],
            aspect=group[0]["aspect"],
            notes=group[0]["notes"],
            inflections=inflections,
        )
        entries.append(entry)
    return entries


def load_entries_sr_to_ru(rows: list[dict], script: str) -> list[Entry]:
    """Serbian headword → Russian translation."""
    grouped: dict[str, list] = {}
    for r in rows:
        sr_key = lat_to_cyr(r["sr_lat"]) if script == "cyrillic" else r["sr_lat"]
        grouped.setdefault((sr_key, r["sr_lat"], r["pos"], r["gender"], r["aspect"]), []).append(r)

    entries = []
    for (sr_key, sr_lat, pos, gender, aspect), group in sorted(
        grouped.items(), key=lambda x: x[0][0].lower()
    ):
        translations = []
        for r in group:
            label = _pos_label(r["pos"], r["gender"], r["aspect"])
            translations.append((r["ru"], label, r["notes"]))

        infl_lat = sr_inflections(sr_lat, pos, gender)
        if script == "cyrillic":
            inflections = [lat_to_cyr(f) for f in infl_lat]
            display = sr_key
        else:
            inflections = infl_lat
            display = sr_lat

        entry = Entry(
            headword=sr_key,
            display=display,
            translation=_format_translations(translations),
            pos=pos,
            gender=gender,
            aspect=aspect,
            notes=group[0]["notes"],
            inflections=inflections,
        )
        entries.append(entry)
    return entries


def _pos_label(pos: str, gender: str, aspect: str) -> str:
    parts = []
    if pos not in ("-", ""):
        parts.append(pos)
    if gender not in ("-", ""):
        parts.append(gender)
    if aspect not in ("-", ""):
        parts.append(aspect)
    return " ".join(parts)


def _format_translations(pairs: list[tuple]) -> str:
    parts = []
    for word, label, notes in pairs:
        s = f"<b>{word}</b>"
        if label:
            s += f" <i>({label})</i>"
        if notes:
            s += f" <small>[{notes}]</small>"
        parts.append(s)
    return "; ".join(parts)


# ---------------------------------------------------------------------------
# EPUB builder
# ---------------------------------------------------------------------------

def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def build_epub(entries: list[Entry], title: str, lang_in: str, lang_out: str, epub_path: Path):
    uid = str(uuid.uuid4())

    # --- content.html ---
    html_parts = [textwrap.dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
            "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
        <html xmlns:idx="https://kindlegen.s3.amazonaws.com/AmazonKindlePublishingGuidelines.pdf"
              xmlns:mbp="https://kindlegen.s3.amazonaws.com/AmazonKindlePublishingGuidelines.pdf"
              xmlns="http://www.w3.org/1999/xhtml">
        <head>
          <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
          <style>
            idx\\:entry { margin: 0.3em 0; }
            b { font-weight: bold; }
            i { font-style: italic; color: #555; }
            small { font-size: 0.85em; color: #888; }
          </style>
        </head>
        <body>
        <mbp:frameset aid="frameset">
    """)]

    for i, e in enumerate(entries):
        inflection_xml = ""
        if e.inflections:
            iforms = "".join(
                f'<idx:iform value="{_escape(f)}"/>' for f in e.inflections
            )
            inflection_xml = f"<idx:infl>{iforms}</idx:infl>"

        html_parts.append(
            f'<idx:entry aid="e{i:05d}">\n'
            f'  <idx:orth value="{_escape(e.headword)}">{inflection_xml}</idx:orth>\n'
            f'  <p><b>{_escape(e.display)}</b> — {e.translation}</p>\n'
            f'</idx:entry>\n'
        )

    html_parts.append("</mbp:frameset>\n</body>\n</html>")
    content_html = "".join(html_parts)

    # --- content.opf ---
    content_opf = textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="uid">
          <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"
                    xmlns:opf="http://www.idpf.org/2007/opf">
            <dc:title>{_escape(title)}</dc:title>
            <dc:language>{lang_in}</dc:language>
            <dc:identifier id="uid">{uid}</dc:identifier>
            <x-metadata>
              <DictionaryInLanguage>{lang_in}</DictionaryInLanguage>
              <DictionaryOutLanguage>{lang_out}</DictionaryOutLanguage>
              <DefaultLookupIndex>default</DefaultLookupIndex>
            </x-metadata>
          </metadata>
          <manifest>
            <item id="content" href="content.html" media-type="application/xhtml+xml"/>
            <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
          </manifest>
          <spine toc="ncx">
            <itemref idref="content"/>
          </spine>
        </package>
    """)

    # --- toc.ncx ---
    toc_ncx = textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN"
            "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
        <ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
          <head>
            <meta name="dtb:uid" content="{uid}"/>
          </head>
          <docTitle><text>{_escape(title)}</text></docTitle>
          <navMap>
            <navPoint id="main" playOrder="1">
              <navLabel><text>{_escape(title)}</text></navLabel>
              <content src="content.html"/>
            </navPoint>
          </navMap>
        </ncx>
    """)

    # --- pack into EPUB (ZIP) ---
    epub_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(epub_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", textwrap.dedent("""\
            <?xml version="1.0"?>
            <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
              <rootfiles>
                <rootfile full-path="content.opf" media-type="application/oebps-package+xml"/>
              </rootfiles>
            </container>
        """))
        zf.writestr("content.opf", content_opf)
        zf.writestr("toc.ncx", toc_ncx)
        zf.writestr("content.html", content_html)

    print(f"  EPUB: {epub_path} ({len(entries)} entries)")


def find_kindlegen() -> str | None:
    import platform
    found = shutil.which("kindlegen")
    if found:
        return found

    if platform.system() == "Darwin":
        candidates = [
            "/Applications/Kindle Previewer 3.app/Contents/lib/fc/bin/kindlegen",
            "/usr/local/bin/kindlegen",
            "/opt/homebrew/bin/kindlegen",
        ]
    else:
        candidates = [
            str(Path(__file__).parent / "kindlegen"),  # Linux binary committed to repo
            "/usr/local/bin/kindlegen",
        ]

    for p in candidates:
        if Path(p).exists():
            return p
    return None


def epub_to_mobi_kindlegen(epub_path: Path, mobi_path: Path, kindlegen: str) -> bool:
    """Compile with kindlegen — creates proper dictionary INDX."""
    import tempfile, zipfile as zf
    # kindlegen works on a folder, not a zip epub — unpack first
    tmp = Path(tempfile.mkdtemp())
    with zf.ZipFile(epub_path) as z:
        z.extractall(tmp)
    opf = next(tmp.glob("*.opf"), None) or next(tmp.glob("**/*.opf"), None)
    if not opf:
        print("  ERROR: OPF not found in EPUB")
        shutil.rmtree(tmp)
        return False
    result = subprocess.run(
        [kindlegen, str(opf), "-o", mobi_path.name],
        capture_output=True, text=True, cwd=tmp,
    )
    compiled = tmp / mobi_path.name
    if compiled.exists():
        shutil.move(str(compiled), mobi_path)
        print(f"  MOBI: {mobi_path}")
        shutil.rmtree(tmp)
        return True
    print(f"  ERROR kindlegen:\n{result.stdout[-300:]}\n{result.stderr[-300:]}")
    shutil.rmtree(tmp)
    return False


def epub_to_azw3_calibre(epub_path: Path, azw3_path: Path) -> bool:
    """Fallback: Calibre AZW3 — content ok but no dictionary lookup index."""
    ebook_convert = shutil.which("ebook-convert")
    if not ebook_convert:
        print("  SKIP: ebook-convert not found (install Calibre)")
        return False
    result = subprocess.run(
        [ebook_convert, str(epub_path), str(azw3_path)],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"  AZW3 (no dict index, fallback): {azw3_path}")
        return True
    print(f"  ERROR calibre:\n{result.stderr[-500:]}")
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Reading {DATA} ...")
    with open(DATA, encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    print(f"  {len(rows)} entries loaded\n")

    OUTPUT.mkdir(exist_ok=True)
    epub_dir = OUTPUT / "epub"
    epub_dir.mkdir(exist_ok=True)

    configs = [
        ("ru-sr-latin",    "ru_to_sr", "latin",    "ru", "sr", "Русско-сербский словарь (латиница)"),
        ("ru-sr-cyrillic", "ru_to_sr", "cyrillic",  "ru", "sr", "Русско-сербский словарь (кириллица)"),
        ("sr-latin-ru",    "sr_to_ru", "latin",    "sr", "ru", "Сербско-русский словарь (латиница)"),
        ("sr-cyrillic-ru", "sr_to_ru", "cyrillic",  "sr", "ru", "Сербско-русский словарь (кириллица)"),
    ]

    for name, direction, script, lang_in, lang_out, title in configs:
        print(f"Building {name} ...")
        if direction == "ru_to_sr":
            entries = load_entries_ru_to_sr(rows, script)
        else:
            entries = load_entries_sr_to_ru(rows, script)

        epub_path = epub_dir / f"{name}.epub"
        build_epub(entries, title, lang_in, lang_out, epub_path)

        kindlegen = find_kindlegen()
        if kindlegen:
            mobi_path = OUTPUT / f"{name}.mobi"
            epub_to_mobi_kindlegen(epub_path, mobi_path, kindlegen)
        else:
            azw3_path = OUTPUT / f"{name}.azw3"
            print("  kindlegen not found — falling back to Calibre AZW3 (no dict lookup)")
            epub_to_azw3_calibre(epub_path, azw3_path)
        print()

    print("Done.")


if __name__ == "__main__":
    main()
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
    Minimal Serbian inflection rules for common cases.
    Good enough for Kindle lookup — full morphology can be added later.
    """
    forms = set()
    if pos == "n":
        if gender == "f" and word.endswith("a"):
            stem = word[:-1]
            forms.update([stem + "e", stem + "i", stem + "u", stem + "om", stem + "a"])
        elif gender == "m":
            forms.update([
                word + "a", word + "u", word + "om", word + "e",
                word + "i", word + "ovi", word + "ima",
            ])
        elif gender == "nt" and word.endswith("o"):
            stem = word[:-1]
            forms.update([stem + "a", stem + "u", stem + "om", stem + "ima"])
    elif pos == "adj":
        # Drop final vowel + add common adjectival endings
        for suffix in ("i", "a", "e", "og", "om", "im", "ih", "im"):
            forms.add(word.rstrip("aio") + suffix)
    forms.discard(word)
    return sorted(forms)


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
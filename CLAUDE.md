# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Recnik** (Речник/Rečnik) — open-source Russian↔Serbian Kindle dictionary. Community-editable via GitHub PRs (owner-approved), rebuilt automatically on merge.

## 4 Target Dictionaries

| File | From | To |
|------|------|----|
| `ru-sr-latin.mobi` | Russian | Serbian Latin |
| `ru-sr-cyrillic.mobi` | Russian | Serbian Cyrillic |
| `sr-latin-ru.mobi` | Serbian Latin | Russian |
| `sr-cyrillic-ru.mobi` | Serbian Cyrillic | Russian |

Serbian Cyrillic is never stored — always auto-generated from Latin via `transliterate.py`.

## Repository Structure

```
data/dictionary.tsv     — single source of truth (TSV, one translation pair per row)
scripts/
  import_apertium.py   — one-time import from Apertium apertium-hbs-rus (.dix → TSV)
  transliterate.py     — Serbian Latin ↔ Cyrillic
  build.py             — TSV → 4 x .mobi (via kindlegen) or .azw3 (Calibre fallback)
output/                — generated files, gitignored
  epub/                — intermediate EPUB files
  *.mobi               — final Kindle dictionaries
.github/workflows/     — CI: rebuild on push to main, upload to GitHub Release
```

## TSV Format (`data/dictionary.tsv`)

```
ru          sr_lat      pos   gender  aspect  notes
знать       znati       v     -       impf
книга       knjiga      n     f       -
```

- One row = one translation pair (multiple rows for multiple translations of same word)
- `pos`: `n`, `v`, `adj`, `adv`, `pr`, `conj`, `prn`, `num`, `part`, `np`
- `gender`: `m`, `f`, `nt`, `-`
- `aspect`: `perf`, `impf`, `both`, `-`
- Serbian Cyrillic headwords generated from `sr_lat` at build time

## Build

```bash
python -m venv .venv && source .venv/bin/activate
pip install pymorphy3 setuptools pyglossary
python scripts/build.py
```

**kindlegen** is required for proper Kindle dictionary index (without it, falls back to Calibre AZW3 which has no lookup). Found automatically if installed at:
- `kindlegen` in PATH
- `/Applications/Kindle Previewer 3.app/Contents/lib/fc/bin/kindlegen` (bundled with Kindle Previewer)

## Kindle Dictionary Format

EPUB with Amazon-specific markup compiled by kindlegen → `.mobi`:
- `<idx:entry aid="...">` — each entry
- `<idx:orth value="headword">` — lookup key
- `<idx:infl><idx:iform value="..."/></idx:infl>` — inflected forms for lookup
- OPF `<DictionaryInLanguage>` / `<DictionaryOutLanguage>` metadata

Russian inflections via **pymorphy3**. Serbian inflections via basic suffix rules in `build.py`.

## Install on Kindle

Copy `.mobi` file to `documents/dictionaries/` on device via USB. Select in Settings → Language & Dictionaries → Dictionaries.

## GitHub Workflow (planned)

- Contributors: fork → edit `data/dictionary.tsv` → open PR
- Owner merges → GitHub Actions rebuilds → uploads `.mobi` to GitHub Release
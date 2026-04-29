#!/usr/bin/env python3
"""
Serbian Latin ↔ Cyrillic transliteration.

Serbian Latin has three digraphs (lj, nj, dž) that must be processed
before single-character substitution to avoid double-conversion.
"""

# Digraphs first — order matters
_LAT_TO_CYR = [
    ("lj", "љ"), ("Lj", "Љ"), ("LJ", "Љ"),
    ("nj", "њ"), ("Nj", "Њ"), ("NJ", "Њ"),
    ("dž", "џ"), ("Dž", "Џ"), ("DŽ", "Џ"),
    ("a", "а"), ("A", "А"),
    ("b", "б"), ("B", "Б"),
    ("c", "ц"), ("C", "Ц"),
    ("č", "ч"), ("Č", "Ч"),
    ("ć", "ћ"), ("Ć", "Ћ"),
    ("d", "д"), ("D", "Д"),
    ("đ", "ђ"), ("Đ", "Ђ"),
    ("e", "е"), ("E", "Е"),
    ("f", "ф"), ("F", "Ф"),
    ("g", "г"), ("G", "Г"),
    ("h", "х"), ("H", "Х"),
    ("i", "и"), ("I", "И"),
    ("j", "ј"), ("J", "Ј"),
    ("k", "к"), ("K", "К"),
    ("l", "л"), ("L", "Л"),
    ("m", "м"), ("M", "М"),
    ("n", "н"), ("N", "Н"),
    ("o", "о"), ("O", "О"),
    ("p", "п"), ("P", "П"),
    ("r", "р"), ("R", "Р"),
    ("s", "с"), ("S", "С"),
    ("š", "ш"), ("Š", "Ш"),
    ("t", "т"), ("T", "Т"),
    ("u", "у"), ("U", "У"),
    ("v", "в"), ("V", "В"),
    ("z", "з"), ("Z", "З"),
    ("ž", "ж"), ("Ž", "Ж"),
]

# Reverse map for Cyrillic → Latin
_CYR_TO_LAT = [(cyr, lat) for lat, cyr in reversed(_LAT_TO_CYR)]


def lat_to_cyr(text: str) -> str:
    for lat, cyr in _LAT_TO_CYR:
        text = text.replace(lat, cyr)
    return text


def cyr_to_lat(text: str) -> str:
    for cyr, lat in _CYR_TO_LAT:
        text = text.replace(cyr, lat)
    return text


if __name__ == "__main__":
    samples = [
        "ljubav",       # ljubav → љубав
        "knjiga",       # knjiga → књига
        "džungla",      # džungla → џунгла
        "Beograd",      # Beograd → Београд
        "Novi Sad",     # Novi Sad → Нови Сад
        "ljepotica",    # ljepotica → љепотица
        "njega",        # njega → њега
        "čovjek",       # čovjek → човјек
        "škola",        # škola → школа
        "žena",         # žena → жена
        "đak",          # đak → ђак
        "ćup",          # ćup → ћуп
    ]
    print("Latin → Cyrillic:")
    for s in samples:
        print(f"  {s:20} → {lat_to_cyr(s)}")

    print("\nCyrillic → Latin (roundtrip):")
    for s in samples:
        cyr = lat_to_cyr(s)
        back = cyr_to_lat(cyr)
        ok = "✓" if back == s else f"✗ got {back!r}"
        print(f"  {cyr:20} → {back:20} {ok}")
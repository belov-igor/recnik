# Recnik / Речник / Rečnik

---

## English

**Russian ↔ Serbian Kindle Dictionary**

A free, open-source bilingual dictionary for Kindle e-readers. Four variants are available:

| File | Direction |
|------|-----------|
| `ru-sr-latin.mobi` | Russian → Serbian (Latin script) |
| `ru-sr-cyrillic.mobi` | Russian → Serbian (Cyrillic script) |
| `sr-latin-ru.mobi` | Serbian (Latin) → Russian |
| `sr-cyrillic-ru.mobi` | Serbian (Cyrillic) → Russian |

### Install on Kindle

1. Download the `.mobi` file from [Releases](../../releases)
2. Connect your Kindle via USB
3. Copy the file to `documents/dictionaries/`
4. On the device: Settings → Language & Dictionaries → Dictionaries → select the dictionary

### Contribute

The dictionary source is `data/dictionary.tsv` — a plain tab-separated file, one translation pair per line:

```
ru          sr_lat      pos   gender  aspect  notes
знать       znati       v     -       impf
книга       knjiga      n     f       -
```

To add or correct entries:

1. Fork this repository
2. Edit `data/dictionary.tsv`
3. Open a Pull Request

Pull requests are reviewed and merged by the maintainer. On merge, the dictionaries are rebuilt automatically and published to Releases.

### Build locally

```bash
# Install Kindle Previewer (contains kindlegen): https://www.amazon.com/kindle-dbs/fd/kcp
python -m venv .venv && source .venv/bin/activate
pip install pymorphy3 setuptools pyglossary
python scripts/build.py
```

### Data sources

- **[Apertium apertium-hbs-rus](https://github.com/apertium/apertium-hbs-rus)** — bilingual Russian–Serbian lexicon, licensed under GNU GPL.
- **[Wiktionary](https://www.wiktionary.org/)** via [kaikki.org](https://kaikki.org/dictionary/Russian/) — community-edited translation data, licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- **[Tatoeba](https://tatoeba.org)** — word pairs extracted from aligned Russian–Serbian sentence pairs, licensed under [CC BY 2.0 FR](https://creativecommons.org/licenses/by/2.0/fr/).

---

## Srpski (latinica)

**Rusko-srpski rečnik za Kindle**

Besplatan, open-source dvojezični rečnik za Kindle čitače. Na raspolaganju su četiri varijante:

| Fajl | Smer |
|------|------|
| `ru-sr-latin.mobi` | Ruski → Srpski (latinica) |
| `ru-sr-cyrillic.mobi` | Ruski → Srpski (ćirilica) |
| `sr-latin-ru.mobi` | Srpski (latinica) → Ruski |
| `sr-cyrillic-ru.mobi` | Srpski (ćirilica) → Ruski |

### Instalacija na Kindle

1. Preuzmite `.mobi` fajl sa [Releases](../../releases)
2. Povežite Kindle putem USB-a
3. Kopirajte fajl u `documents/dictionaries/`
4. Na uređaju: Settings → Language & Dictionaries → Dictionaries → izaberite rečnik

### Doprinos

Izvor rečnika je fajl `data/dictionary.tsv` — obična tabulatorom odvojena tabela, jedan par prevoda po redu.

Kako da doprineste:

1. Forkujte repozitorijum
2. Izmenite `data/dictionary.tsv`
3. Otvorite Pull Request

Pull requestove pregledava i spaja vlasnik projekta. Nakon spajanja, rečnici se automatski regenerišu i objavljuju u Releases.

### Izvori podataka

- **[Apertium apertium-hbs-rus](https://github.com/apertium/apertium-hbs-rus)** — dvojezični rusko-srpski leksikon, licenciran pod GNU GPL.
- **[Wiktionary](https://www.wiktionary.org/)** putem [kaikki.org](https://kaikki.org/dictionary/Russian/) — prevodilački podaci zajednice, licencirani pod [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- **[Tatoeba](https://tatoeba.org)** — parovi reči izvučeni iz poravnatih rusko-srpskih rečenica, licencirani pod [CC BY 2.0 FR](https://creativecommons.org/licenses/by/2.0/fr/).

---

## Русский

**Русско-сербский словарь для Kindle**

Бесплатный словарь с открытым исходным кодом для устройств Kindle. Доступны четыре варианта:

| Файл | Направление |
|------|-------------|
| `ru-sr-latin.mobi` | Русский → Сербский (латиница) |
| `ru-sr-cyrillic.mobi` | Русский → Сербский (кириллица) |
| `sr-latin-ru.mobi` | Сербский (латиница) → Русский |
| `sr-cyrillic-ru.mobi` | Сербский (кириллица) → Русский |

### Установка на Kindle

1. Скачай `.mobi` файл из раздела [Releases](../../releases)
2. Подключи Kindle по USB
3. Скопируй файл в папку `documents/dictionaries/`
4. На устройстве: Settings → Language & Dictionaries → Dictionaries → выбери словарь

### Как внести вклад

Источник словаря — файл `data/dictionary.tsv`: таблица с разделителями-табуляциями, одна пара перевода в строке.

Чтобы добавить или исправить слова:

1. Сделай форк репозитория
2. Отредактируй `data/dictionary.tsv`
3. Открой Pull Request

Pull request'ы проверяет и принимает владелец проекта. После принятия словари автоматически пересобираются и публикуются в Releases.

### Источники данных

- **[Apertium apertium-hbs-rus](https://github.com/apertium/apertium-hbs-rus)** — двуязычный русско-сербский лексикон, лицензия GNU GPL.
- **[Wiktionary](https://www.wiktionary.org/)** через [kaikki.org](https://kaikki.org/dictionary/Russian/) — переводы от сообщества, лицензия [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- **[Tatoeba](https://tatoeba.org)** — пары слов, извлечённые из выровненных русско-сербских предложений, лицензия [CC BY 2.0 FR](https://creativecommons.org/licenses/by/2.0/fr/).
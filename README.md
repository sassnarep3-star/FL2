# FL2 - NFL Analysis Dashboard

Live site (GitHub Pages, after merge): see the repository's Pages settings.

## What is here

- `docs/` - static site served by GitHub Pages (landing page, category pages, Flagged for Review).
- `data/` - source data. CSV files are pipe-delimited (`|`) and hold verified rows; JSON files hold qualitative content (sources, flags, questions, suggestions, strategy gates).
- `scripts/make_pages.py` - writes the HTML pages from one template.
- `scripts/build_site.py` - converts data to JSON, computes unit-exposure counts, validates, and fails the build on any problem (row counts, non-NFL.com links, unknown source IDs, broken internal links, invalid JSON).
- `COORDINATION.md` - shared task board for parallel sessions.

## Rebuild

```bash
python3 scripts/make_pages.py
python3 scripts/build_site.py
```

## Data rules

- Every table row must carry a source URL. Values that cannot be confirmed from an official source are left blank and flagged.
- Starter/backup status is not inferred. Unit exposure shows counts from the injury report only.
- No betting lines or odds are included; no verified source has been found yet.

## Disclaimer

Analysis only. Not betting advice. Check the legal status of any wagering where you live before using any result.

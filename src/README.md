# The Groove - source

Generator and content for groove.cold.fyi. The site at the repo root is generated; edit here, then rebuild.

- `content/parts/NN-slug.md` - the 12 sections plus lede and closing. Footnotes are `[^key]`; keys map to URLs in `content/frag/*-sources.tsv`.
- `content/frag/` - sources, glossary, timeline, FAQ, resources, `run-runout.json` (the decoder) and `cut-numbers.json` (side-length check).
- `content/quiz.json`, `seo.json`, `gaps.json` - quiz, hub FAQ and title, open questions.
- `build.py` - set `R` to `src/content` and `OUT` to the repo root, then `STRICT=1 python3 build.py`. `og.py <n_sources>` redraws the share image.

Rules: every fact footnoted to a page someone opened; no em or en dashes; global framing; quotes under 25 words. Corrections go in `content/corrections.json` (`date`, `section`, `what`).

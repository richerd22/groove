#!/usr/bin/env python3
"""Build groove.cold.fyi - The Groove, a cited field guide to the vinyl record.

    python3 build.py            # writes the site to OUT
    STRICT=1 python3 build.py   # also fails on [[GAP:]] markers or unknown footnote keys

Inputs (R = the report folder):
  R/parts/NN-slug.md     one section each, starting "## Title"; footnotes as [^key]
  R/frag/*-sources.tsv   key <TAB> Publisher: Title <TAB> URL
  R/frag/*-glossary.json, *-timeline.json, *-faq.json, *-resources.json, run-runout.json, *-numbers.json
  R/quiz.json, R/seo.json, R/gaps.json, R/corrections.json (optional)
Outputs: hub, one page per section, /all/, /decoder/, /glossary/, /sources/, /corrections/, 404,
sitemap.xml, robots.txt, llms.txt, CNAME, favicon, and JSON copies of every dataset (AX).
"""
import glob, html, json, os, re, sys, datetime
import markdown
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meta_pixel  # noqa: E402
META_PIXEL = "2368576097306858"  # cold.fyi Deep Dives pixel; footer note links thirdpolararch.com/privacy

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.environ.get("GROOVE_REPORT", "/home/claude/reports/groove")
OUT = os.environ.get("GROOVE_OUT", "/home/claude/groove")
DOMAIN = "groove.cold.fyi"
SITE = f"https://{DOMAIN}"
NAME = "The Groove"
NO = 9
PUBLISHED = "2026-11-12"
STRICT = os.environ.get("STRICT") == "1"
E = lambda s: html.escape(str(s), quote=True)


def J(p, default=None):
    p = os.path.join(R, p)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


# ------------------------------------------------------------ sources
src, clash = {}, []
for f in sorted(glob.glob(f"{R}/frag/*-sources.tsv")):
    for ln in open(f, encoding="utf-8"):
        parts = ln.rstrip("\n").split("\t")
        if len(parts) < 3 or not parts[0].strip():
            continue
        k, t, u = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if k in src and src[k][1] != u:
            clash.append(k)
        src.setdefault(k, (t, u))


def jl(pattern):
    out = []
    for f in sorted(glob.glob(f"{R}/frag/{pattern}")):
        try:
            out += json.load(open(f, encoding="utf-8"))
        except Exception as ex:
            sys.exit(f"bad json {f}: {ex}")
    return out


glossary = sorted({g["term"].lower(): g for g in jl("*-glossary.json")}.values(), key=lambda g: g["term"].lower())
timeline = sorted(jl("*-timeline.json"), key=lambda t: str(t.get("date", "")))
resources = jl("*-resources.json")
runout = sorted(jl("*-runout.json"), key=lambda r: r["marking"].lower())
quiz = J("quiz.json", [])
seo = J("seo.json", {})
gaps = J("gaps.json", [])
corrections = J("corrections.json", [])

# ------------------------------------------------------------ parts
parts = sorted(glob.glob(f"{R}/parts/*.md"))
lede_md = open(parts[0], encoding="utf-8").read()
sections = []
for p in parts[1:]:
    md = open(p, encoding="utf-8").read()
    md = re.sub(r"^\[\[DIAGRAM-IDEA:.*?\]\]\s*$", "", md, flags=re.M)
    md = re.sub(r"^\[\^[^\]]+\]:.*$", "", md, flags=re.M)
    m = re.match(r"\s*##\s+(.+)", md)
    if not m:
        sys.exit(f"{p}: must start with '## Title'")
    slug = re.sub(r"^\d+-", "", os.path.basename(p)[:-3])
    sections.append({"slug": slug, "title": m.group(1).strip(), "md": md[m.end():].strip(), "file": os.path.basename(p)})
SLUGS = [s["slug"] for s in sections]
faq_by_slug = {}
for f in sorted(glob.glob(f"{R}/frag/*-faq.json")):
    for x in json.load(open(f, encoding="utf-8")):
        if x.get("section"):
            faq_by_slug.setdefault(x["section"], []).append(x)

# ------------------------------------------------------------ footnotes: numbered globally by first use
order, missing = {}, set()


def num(k):
    if k not in src:
        missing.add(k)
        return None
    u = src[k][1]
    if u not in order:
        order[u] = (len(order) + 1, k)
    return order[u][0]


def footnotes(md, page_refs):
    def rep(m):
        n = num(m.group(1))
        if n is None:
            return ""
        page_refs.add(n)
        return f'<sup class="fn"><a href="#src-{n}" data-n="{n}">{n}</a></sup>'
    return re.sub(r"\[\^([A-Za-z0-9_.:-]+)\]", rep, md)


MDX = markdown.Markdown(extensions=["tables", "sane_lists", "attr_list"])


def mdhtml(s):
    MDX.reset()
    return MDX.convert(s)


def heading_ids(h):
    used = set()

    def rep(m):
        lvl, txt = m.group(1), m.group(2)
        base = re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", txt).lower()).strip("-")[:70] or "h"
        sid, i = base, 2
        while sid in used:
            sid, i = f"{base}-{i}", i + 1
        used.add(sid)
        return f'<h{lvl} id="{sid}">{txt}<a class="anchor" href="#{sid}" aria-label="Link to this">#</a></h{lvl}>'
    return re.sub(r"<h([34])>(.*?)</h\1>", rep, h)


SHORT_RE = re.compile(r"^\*\*The short version:\*\*\s*(.+?)\n\n", re.S)

# ------------------------------------------------------------ modules
def mod(kicker, title, intro, inner, id_=""):
    return (f'<section class="mod"{f" id={chr(34)}{id_}{chr(34)}" if id_ else ""}><div class="mod-head"><p class="kick">{E(kicker)}</p><h3>{E(title)}</h3>'
            f'{f"<p>{E(intro)}</p>" if intro else ""}</div>{inner}</section>')


def js_json(o):
    return json.dumps(o, ensure_ascii=False).replace("</", "<\\/")


def srcu(u):
    return f' <a class="s" href="{E(u)}" rel="noopener" target="_blank">source</a>' if u else ""


def m_decoder():
    rows = [dict(r, kind=r.get("kind", ""), source_url=r.get("source_url", "")) for r in runout]
    kinds = sorted({r["kind"] for r in rows if r["kind"]})
    inner = ('<div class="tools"><label class="sr" for="dc-q">Search the runout</label><input id="dc-q" type="search" placeholder="Type what you see in the dead wax: STERLING, Porky, IAM, DMM, A1..." autocomplete="off">'
             '<div class="chips" role="group" aria-label="Kind"><button type="button" data-k="" aria-pressed="true">All</button>'
             + "".join(f'<button type="button" data-k="{E(k)}" aria-pressed="false">{E(k)}</button>' for k in kinds) + '</div><span class="cnt" id="dc-cnt"></span></div>'
             '<div class="tbl"><table class="dc"><thead><tr><th>In the dead wax</th><th>What it means</th><th>Kind</th></tr></thead><tbody id="dc-list">'
             + "".join(f'<tr data-k="{E(r["kind"])}" data-s="{E((r["marking"] + " " + r.get("meaning", "") + " " + r.get("example", "")).lower())}"><td class="etch">{E(r["marking"])}'
                       + (f'<br><span class="ex">e.g. {E(r["example"])}</span>' if r.get("example") else "") + f'</td><td>{E(r["meaning"])}{srcu(r["source_url"])}</td><td class="k">{E(r["kind"])}</td></tr>' for r in rows)
             + '</tbody></table></div>')
    return mod("Runout decoder", f"{len(rows)} markings from the dead wax", "The letters, numbers, initials and symbols scratched or stamped between the last song and the label. Plants and engineers changed their habits over the years, so a marking is a clue, not proof.", inner, "decoder")


def m_sidetime():
    nums = {x["id"]: x for x in jl("*-numbers.json") if x.get("id")}
    rows = [x for x in nums.values() if x.get("kind") == "sidetime"]
    if not rows:
        return ""
    data = js_json(rows)
    inner = ('<div class="calc"><label class="field">Format<select id="st-f">' + "".join(f'<option value="{E(r["id"])}">{E(r["label"])}</option>' for r in rows) + '</select></label>'
             '<label class="field">Your side runs (minutes)<input id="st-m" type="number" min="1" max="40" step="0.5" value="18"></label></div>'
             '<p class="out" id="st-out" aria-live="polite"></p>' f'<script type="application/json" id="st-data">{data}</script>')
    return mod("Side-length check", "Will it fit on one side?", "Cutting engineers trade loudness and bass for time: the longer the side, the closer the grooves and the quieter the cut. These are plants' recommended limits, not hard rules - ask your cutting engineer.", inner, "sidetime")


def m_timeline():
    eras = []
    for t in timeline:
        if t.get("era") and t["era"] not in eras:
            eras.append(t["era"])
    items = "".join(f'<li data-era="{E(t.get("era", ""))}"><span class="d">{E(t["date"])}</span><b>{E(t["label"])}</b> {E(t.get("detail", ""))}{srcu(t.get("source_url"))}</li>' for t in timeline)
    seg = '<div class="chips" role="group" aria-label="Era"><button type="button" data-era="" aria-pressed="true">All</button>' + "".join(f'<button type="button" data-era="{E(x)}" aria-pressed="false">{E(x)}</button>' for x in eras) + "</div>"
    return mod("Timeline", f"{len(timeline)} dates, cylinder to comeback", "", seg + f'<ol class="tl" id="tl-list">{items}</ol>', "timeline")


def m_glossary():
    items = "".join(f'<li id="term-{E(re.sub(r"[^a-z0-9]+", "-", g["term"].lower()).strip("-"))}" data-s="{E((g["term"] + " " + g.get("definition", "")).lower())}"><dfn>{E(g["term"])}</dfn> {E(g.get("definition", ""))}'
                    + (f' <a class="s" href="/{E(g["section"])}/">read more</a>' if g.get("section") in SLUGS else "") + "</li>" for g in glossary)
    return mod("Glossary", f"{len(glossary)} terms of art", "", f'<div class="tools"><label class="sr" for="gl-q">Search the glossary</label><input id="gl-q" type="search" placeholder="lacquer, stamper, RIAA, dead wax..." autocomplete="off"></div><ul class="gl" id="gl-list">{items}</ul>', "glossary")


def m_resources():
    items = "".join(f'<li><a href="{E(r["url"])}" rel="noopener" target="_blank">{E(r["title"])}</a> - {E(r.get("why", ""))}</li>' for r in resources)
    return mod("Further", "Where to go next", "", f'<ul class="res">{items}</ul>', "resources")


def m_quiz():
    if not quiz:
        return ""
    return mod("Test yourself", f"{len(quiz)} questions", "", f'<div id="quiz"></div><script type="application/json" id="quiz-data">{js_json(quiz)}</script>', "quiz")


def m_gaps():
    items = "".join(f"<li>{E(g)}</li>" for g in gaps) or "<li>None listed.</li>"
    return mod("Still unconfirmed", f"{len(gaps)} open questions", "Know the answer? hello@thirdpolararch.com", f"<ul>{items}</ul>", "gaps")


MODULES = {"decoder": m_decoder, "sidetime": m_sidetime, "timeline": m_timeline, "glossary": m_glossary, "resources": m_resources, "quiz": m_quiz, "gaps": m_gaps}


def modules(h):
    def rep(m):
        k = m.group(1).strip()
        if k not in MODULES:
            sys.exit(f"unknown module {k}")
        return MODULES[k]()
    h = re.sub(r"<p>\[\[MODULE:([a-z]+)\]\]</p>", rep, h)
    return re.sub(r"\[\[MODULE:([a-z]+)\]\]", rep, h)


# ------------------------------------------------------------ render sections
gap_left = []
for s in sections:
    refs = set()
    md = s["md"]
    m = SHORT_RE.match(md + "\n\n")
    s["short"] = re.sub(r"\[\^[^\]]+\]", "", m.group(1)).strip() if m else ""
    for g in re.findall(r"\[\[GAP:(.*?)\]\]", md):
        gap_left.append((s["slug"], g))
    md = re.sub(r"^\[\[GAP:.*?\]\]\s*$", "", md, flags=re.M)
    md = footnotes(md, refs)
    h = mdhtml(md)
    h = h.replace("<p><strong>The short version:</strong>", '<p class="short"><strong>The short version:</strong>', 1)
    h = heading_ids(h)
    h = modules(h)
    s["html"], s["refs"] = h, sorted(refs)
    s["words"] = len(re.sub(r"<[^>]+>", " ", h).split())
    s["mins"] = max(1, round(s["words"] / 230))
    s["h3"] = re.findall(r'<h3 id="([^"]+)">(.*?)<a class="anchor"', h)
lede_refs = set()
lede_md = footnotes(re.sub(r"^#\s+.*\n", "", lede_md, count=1), lede_refs)
lede_html = modules(mdhtml(lede_md))
if missing:
    msg = "unknown footnote keys: " + ", ".join(sorted(missing))
    if STRICT:
        sys.exit(msg)
    print("WARN", msg)
if gap_left and STRICT:
    sys.exit("GAP markers left: " + "; ".join(f"{a}: {b}" for a, b in gap_left))
nsrc = {n: (k, src[k]) for u, (n, k) in order.items()}
WORDS = sum(s["words"] for s in sections) + len(re.sub(r"<[^>]+>", " ", lede_html).split())

# ------------------------------------------------------------ shell
CSS = open(os.path.join(HERE, "style.css"), encoding="utf-8").read()
JS = open(os.path.join(HERE, "app.js"), encoding="utf-8").read()
FONTS = [("Gloock", 400, "normal", "gloock-latin-400-normal"), ("Crimson Pro", 400, "normal", "crimson-pro-latin-400-normal"),
         ("Crimson Pro", 400, "italic", "crimson-pro-latin-400-italic"), ("Crimson Pro", 600, "normal", "crimson-pro-latin-600-normal"),
         ("IBM Plex Mono", 400, "normal", "ibm-plex-mono-latin-400-normal"), ("IBM Plex Mono", 600, "normal", "ibm-plex-mono-latin-600-normal"),
         ("Caveat", 500, "normal", "caveat-latin-500-normal")]
FONT_CSS = "".join(f"@font-face{{font-family:'{f}';font-style:{st};font-weight:{w};font-display:swap;src:url(/fonts/{fn}.woff2) format('woff2')}}" for f, w, st, fn in FONTS)
STAMP = datetime.date.fromisoformat(os.environ.get("GROOVE_UPDATED", PUBLISHED))
UPDATED = STAMP.strftime("%B %Y")


def record_svg(title="The Groove", small=False):
    """An LP drawn in code: grooves, a band of silence between tracks, the label, and a hand-etched runout."""
    rings = "".join(f'<circle cx="200" cy="200" r="{r}" class="gr{" gap" if r in (128, 150) else ""}"/>' for r in range(84, 196, 3))
    etch = "THE GROOVE · COLD.FYI · NO. 9 · INDEPENDENT · A1 · " * 2
    return (f'<svg class="lp{" sm" if small else ""}" viewBox="0 0 400 400" role="img" aria-label="A vinyl record drawn in lines">'
            '<defs><path id="runout" d="M200,200 m-74,0 a74,74 0 1,1 148,0 a74,74 0 1,1 -148,0"/></defs>'
            '<circle cx="200" cy="200" r="198" class="disc"/>' + rings +
            '<path class="sheen" d="M200 2 A198 198 0 0 1 340 60 L200 200Z"/><path class="sheen" d="M200 398 A198 198 0 0 1 60 340 L200 200Z"/>'
            f'<circle cx="200" cy="200" r="80" class="wax"/><text class="etch"><textPath href="#runout">{E(etch)}</textPath></text>'
            '<circle cx="200" cy="200" r="58" class="label"/><circle cx="200" cy="200" r="54" class="label-ring"/>'
            f'<text x="200" y="186" class="lt">{E(title.upper())}</text><text x="200" y="230" class="ls">SIDE A · 33 1/3 RPM</text>'
            '<circle cx="200" cy="200" r="4.5" class="hole"/></svg>')


def head(title, desc, path, ld=None, robots="index, follow, max-image-preview:large"):
    canon = SITE + path
    lds = "".join(f'<script type="application/ld+json">{js_json(x)}</script>' for x in (ld or []))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{canon}"><meta name="robots" content="{robots}">
<meta name="theme-color" content="#141210"><meta property="og:type" content="article"><meta property="og:site_name" content="cold.fyi">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{canon}">
<meta property="og:image" content="{SITE}/og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/apple-touch-icon.png"><link rel="alternate" type="text/plain" href="/llms.txt" title="llms.txt">
<link rel="preload" href="/fonts/gloock-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin><link rel="preload" href="/fonts/crimson-pro-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<script>try{{var t=localStorage.getItem('groove-theme');if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
{lds}<style>{FONT_CSS}{CSS}</style></head><body><a class="skip" href="#main">Skip to the text</a><div class="progress" id="progress" aria-hidden="true"></div>
<header class="mast"><span><a href="https://cold.fyi">cold.fyi</a><span class="sep">/</span><a href="/">{NAME}</a></span><button class="theme-btn" id="theme-btn" type="button">Flip it</button></header>
"""


SISTERS = [("radiowheel", "The Radio Wheel", "every GTA radio station, song and talk show"), ("polo", "Polo", "how Coachella works"), ("wristband", "The Wristband", "how music festivals work"), ("lastcall", "Last Call", "how nightlife works"),
           ("noise", "The Noise", "every sound in a city"), ("showfile", "The Show File", "how a dance music show is made"),
           ("tickets", "The Ticket", "how a concert ticket gets from artist to fan"), ("airwaves", "The Airwaves", "every radio signal over a city"),
           ("streetcode", "Street Code", "every mark on the street"), ("works", "How a City Works", "the systems under every street"),
           ("penamnesty", "The Pens Went Away", "pharma swag")]


def foot():
    sis = "".join(f'<li><a href="https://{h}.cold.fyi/">{E(n)}</a> <span>- {E(d)}</span></li>' for h, n, d in SISTERS)
    return f"""<footer class="foot"><div class="foot-in"><p class="k">More deep dives from cold.fyi</p><ul class="sis">{sis}</ul>
<p>made with &lt;3 in boston · <a href="https://thirdpolararch.com">Third Polar Arch</a> · Independent. Not affiliated with any label, pressing plant, store or brand named here.
<a href="/corrections/">Corrections</a> · <a href="/sources/">All {len(nsrc)} sources</a> · <a href="/llms.txt">llms.txt</a> · <a href="mailto:hello@thirdpolararch.com?subject=groove.cold.fyi">hello@thirdpolararch.com</a></p></div></footer>
<script>{JS}</script></body></html>
"""


def crumbs(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": i, "name": n, "item": SITE + p} for i, (n, p) in enumerate(items, 1)]}


def faq_ld(qas):
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}} for q in qas]}


def article_ld(title, desc, path):
    return {"@context": "https://schema.org", "@type": "Article", "headline": title, "description": desc, "url": SITE + path, "inLanguage": "en",
            "datePublished": PUBLISHED, "dateModified": STAMP.isoformat(), "image": SITE + "/og.png",
            "author": {"@type": "Organization", "name": "Third Polar Arch", "url": "https://thirdpolararch.com"},
            "publisher": {"@type": "Organization", "name": "Third Polar Arch", "url": "https://thirdpolararch.com"},
            "isPartOf": {"@type": "CreativeWork", "name": f"{NAME}: how a vinyl record gets made", "url": SITE + "/"}}


def write(rel, text):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p) or OUT, exist_ok=True)
    if str(rel).endswith(".html"):
        text = meta_pixel.inject(text, META_PIXEL)[0]
    open(p, "w", encoding="utf-8").write(text)


def refs_list(nums, title="Sources for this side"):
    if not nums:
        return ""
    li = "".join(f'<li id="src-{n}" value="{n}"><a href="{E(nsrc[n][1][1])}" rel="noopener" target="_blank">{E(nsrc[n][1][0])}</a></li>' for n in nums)
    return f'<section class="refs"><h2>{E(title)}</h2><ol>{li}</ol></section>'


def tracklist(active=None):
    half = (len(sections) + 1) // 2
    def side(lbl, ss, off):
        return (f'<div class="side"><p class="sl">Side {lbl}</p><ol>' + "".join(
            f'<li><a href="/{s["slug"]}/"{" aria-current=page class=on" if s["slug"] == active else ""}><span class="tn">{lbl}{i}</span><span class="tt">{E(s["title"])}</span><span class="td">{s["mins"]}:00</span></a></li>'
            for i, s in enumerate(ss, 1)) + "</ol></div>")
    return f'<nav class="tracks" aria-label="Sections">{side("A", sections[:half], 0)}{side("B", sections[half:], half)}</nav>'


# ------------------------------------------------------------ pages
def section_page(i, s):
    prev_s = sections[i - 1] if i else None
    next_s = sections[i + 1] if i + 1 < len(sections) else None
    qas = faq_by_slug.get(s["slug"], [])[:6]
    qa_html = ('<section class="qa"><h2>Quick answers</h2><dl>' + "".join(f'<dt>{E(q["q"])}</dt><dd>{E(q["a"])}</dd>' for q in qas) + "</dl></section>") if qas else ""
    side = "A" if i < (len(sections) + 1) // 2 else "B"
    tn = i + 1 if side == "A" else i + 1 - (len(sections) + 1) // 2
    toc = ("<nav class=\"intoc\" aria-label=\"On this page\"><p class=\"k\">On this side</p><ol>" + "".join(f'<li><a href="#{a}">{re.sub(r"<[^>]+>", "", t)}</a></li>' for a, t in s["h3"]) + "</ol></nav>") if len(s["h3"]) > 3 else ""
    pn = ('<nav class="pn">' + (f'<a href="/{prev_s["slug"]}/"><span>Previous track</span>{E(prev_s["title"])}</a>' if prev_s else '<span></span>')
          + (f'<a class="nx" href="/{next_s["slug"]}/"><span>Next track</span>{E(next_s["title"])}</a>' if next_s else '<a class="nx" href="/"><span>Flip back</span>The front page</a>') + "</nav>")
    desc = s["short"][:300] or f"{s['title']} - from {NAME}, a cited field guide to the vinyl record."
    ld = [article_ld(s["title"], desc, f"/{s['slug']}/"), crumbs([(NAME, "/"), (s["title"], f"/{s['slug']}/")])] + ([faq_ld(qas)] if qas else [])
    body = f"""<div class="layout">{tracklist(s['slug'])}<main class="col" id="main">
<p class="readmeta"><span class="tn">{side}{tn}</span> · about {s['mins']} min · updated {UPDATED}</p>
<h1>{E(s['title'])}</h1>
{toc}
<article>{s['html']}</article>
{qa_html}
<p class="fix"><a href="mailto:hello@thirdpolararch.com?subject=groove.cold.fyi%20-%20{E(s['slug'])}">Spot a mistake? Tell us.</a></p>
{pn}
{refs_list(s['refs'])}
</main></div>"""
    write(f"{s['slug']}/index.html", head(f"{s['title']} | {NAME}", desc, f"/{s['slug']}/", ld) + body + foot())


def hub():
    t = seo.get("title", f"{NAME}: how a vinyl record gets made")
    d = seo.get("description", "")
    lede = lede_html
    stats = f'<p class="stats"><b>{WORDS:,}</b> words · <b>{len(sections)}</b> tracks · <b>{len(nsrc)}</b> sources · <b>{len(runout)}</b> runout markings decoded · updated {UPDATED}</p>'
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": NAME, "url": SITE + "/", "description": d, "inLanguage": "en",
           "publisher": {"@type": "Organization", "name": "Third Polar Arch", "url": "https://thirdpolararch.com"}},
          article_ld(t, d, "/")] + ([faq_ld(seo["faq"])] if seo.get("faq") else [])
    paths = seo.get("paths", [])
    ph = ""
    if paths:
        ph = '<section class="paths"><h2>Pick your groove</h2><div class="pgrid">' + "".join(
            f'<div class="path"><p class="k">{E(p["who"])}</p><b>{E(p["title"])}</b><p>{E(p["blurb"])}</p>' + " ".join(f'<a href="/{x}/">{E(next((s["title"] for s in sections if s["slug"] == x), x))}</a>' for x in p["slugs"]) + "</div>" for p in paths) + "</div></section>"
    body = f"""<main id="main" class="hub">
<section class="hero"><div class="hero-in"><div class="hero-t"><p class="kicker">cold.fyi deep dive No. {NO} · a field guide</p><h1 class="title">The Groove</h1>
<p class="dek">How a vinyl record gets made, sold, played and collected, from the lacquer to the dead wax.</p>{stats}
<div class="cta"><a class="primary" href="/{sections[0]['slug']}/">Drop the needle</a><a href="/decoder/">Read your runout</a><a href="/all/">The whole album</a></div></div>
<div class="hero-v">{record_svg()}</div></div></section>
<section class="lede col">{lede}</section>
<section class="back"><h2 class="k">Tracklist</h2>{tracklist()}</section>
{ph}
</main>"""
    write("index.html", head(t, d, "/", ld) + body + foot())


def all_page():
    allh = "".join(f'<section id="{s["slug"]}" class="allsec"><p class="readmeta">Track {i + 1}</p><h1>{E(s["title"])}</h1>{s["html"]}</section>' for i, s in enumerate(sections))
    refs = refs_list(sorted(nsrc), "Every source")
    write("all/index.html", head(f"The whole album: everything on one page | {NAME}", "The whole field guide to the vinyl record on one page, with every source.", "/all/") +
          f'<div class="layout">{tracklist()}<main class="col" id="main"><h1>The whole album</h1><div class="lede">{lede_html}</div>{allh}{refs}</main></div>' + foot())


def simple(path, title, desc, inner, ld=None):
    write(path.strip("/") + "/index.html" if path != "/404.html" else "404.html",
          head(f"{title} | {NAME}", desc, path, ld, "noindex" if path == "/404.html" else "index, follow, max-image-preview:large") +
          f'<div class="layout">{tracklist()}<main class="col" id="main"><h1>{E(title)}</h1>{inner}</main></div>' + foot())


def main():
    os.makedirs(OUT, exist_ok=True)
    for i, s in enumerate(sections):
        section_page(i, s)
    hub()
    all_page()
    dec = m_decoder()
    simple("/decoder/", "Runout decoder: what the etchings in the dead wax mean", f"Search {len(runout)} sourced markings from the runout groove of a vinyl record: mastering engineers, pressing plants, matrix and stamper codes.",
           '<p class="lede">The smooth band between the last song and the label is called the runout, or dead wax. Cutting engineers and plants scratch and stamp codes there. Type what you see.</p>'
           + dec + '<p>For how these got there, read <a href="/runout/">the runout section</a> and <a href="/collecting/">collecting and grading</a>.</p>',
           [{"@context": "https://schema.org", "@type": "Dataset", "name": "Vinyl runout groove markings, decoded", "description": "Markings found in the dead wax of vinyl records and what they mean, each with a source.",
             "url": SITE + "/decoder/", "license": "https://creativecommons.org/licenses/by/4.0/", "isAccessibleForFree": True,
             "creator": {"@type": "Organization", "name": "Third Polar Arch"}, "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": SITE + "/runout.json"}]},
            crumbs([(NAME, "/"), ("Runout decoder", "/decoder/")])])
    simple("/glossary/", "Glossary of vinyl record terms", f"{len(glossary)} vinyl terms in plain words: lacquer, stamper, dead wax, RIAA curve, DMM and more.", m_glossary(), [crumbs([(NAME, "/"), ("Glossary", "/glossary/")])])
    simple("/sources/", "Every source", "Every source behind the guide, numbered.", refs_list(sorted(nsrc), f"{len(nsrc)} sources"))
    cl = "".join(f"<li><b>{E(c['date'])}</b> · <a href=\"/{E(c['section'])}/\">{E(c['section'])}</a>: {E(c['what'])}</li>" for c in corrections) or "<li>None yet.</li>"
    simple("/corrections/", "Corrections and updates", "Every correction to a fact, dated.", f'<p>Every fix to a fact, dated. To report one: <a href="mailto:hello@thirdpolararch.com?subject=groove.cold.fyi%20correction">hello@thirdpolararch.com</a>.</p><ul>{cl}</ul>')
    simple("/404.html", "Skipped", "Page not found.", '<p>This groove is scratched. <a href="/">Back to the front page</a>.</p>')
    # data
    write("sections.json", json.dumps([{"n": i + 1, "slug": s["slug"], "title": s["title"], "short": s["short"], "url": f"{SITE}/{s['slug']}/", "words": s["words"], "sources": s["refs"]} for i, s in enumerate(sections)], indent=1, ensure_ascii=False))
    write("sources.json", json.dumps([{"n": n, "key": k, "title": t, "url": u} for n, (k, (t, u)) in sorted(nsrc.items())], indent=1, ensure_ascii=False))
    write("runout.json", json.dumps({"note": "Markings found in vinyl runout grooves and what they mean, each with a source. A clue, not proof.", "markings": runout}, indent=1, ensure_ascii=False))
    write("glossary.json", json.dumps(glossary, indent=1, ensure_ascii=False))
    write("timeline.json", json.dumps(timeline, indent=1, ensure_ascii=False))
    urls = ["/", "/all/", "/decoder/", "/glossary/", "/sources/", "/corrections/"] + [f"/{s['slug']}/" for s in sections]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"<url><loc>{SITE}{u}</loc><lastmod>{STAMP.isoformat()}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")
    llms = [f"# {seo.get('title', NAME)}", "", f"> {seo.get('description', '')}", "",
            f"Independent cited field guide, {WORDS:,} words, {len(nsrc)} sources, updated {UPDATED}. Not affiliated with any label, plant, store or brand.", "", "## Sections"]
    llms += [f"- [{s['title']}]({SITE}/{s['slug']}/): {s['short']}" for s in sections]
    llms += ["", "## Tools and data", f"- Runout decoder: {SITE}/decoder/ (data {SITE}/runout.json, {len(runout)} markings)", f"- Glossary: {SITE}/glossary/ (data {SITE}/glossary.json)",
             f"- {SITE}/sections.json, {SITE}/sources.json, {SITE}/timeline.json", f"- Everything on one page: {SITE}/all/", "",
             "## Sister guides"] + [f"- https://{h}.cold.fyi/ - {n}: {d}" for h, n, d in SISTERS]
    write("llms.txt", "\n".join(llms) + "\n")
    write("CNAME", DOMAIN + "\n")
    write(".nojekyll", "")
    write("favicon.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><circle cx="32" cy="32" r="31" fill="#141210"/><circle cx="32" cy="32" r="22" fill="none" stroke="#3a342d" stroke-width="1.5"/><circle cx="32" cy="32" r="16" fill="none" stroke="#3a342d" stroke-width="1.5"/><circle cx="32" cy="32" r="10" fill="#e2452c"/><circle cx="32" cy="32" r="2" fill="#141210"/></svg>')
    os.makedirs(f"{OUT}/fonts", exist_ok=True)
    for f in glob.glob(f"{HERE}/fonts/*.woff2"):
        open(f"{OUT}/fonts/{os.path.basename(f)}", "wb").write(open(f, "rb").read())
    print(f"built: {WORDS:,} words, {len(sections)} sections, {len(nsrc)} refs, {len(glossary)} terms, {len(runout)} runout markings, {len(timeline)} dates"
          + (f", {len(gap_left)} GAP left" if gap_left else "") + (f", clashes {clash}" if clash else ""))


main()

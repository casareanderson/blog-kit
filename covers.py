#!/usr/bin/env python3
"""Compose dev.to cover banners from Art Institute of Chicago public-domain art.

Why this exists: 18 of 19 articles had no cover, and a coverless post is close
to invisible in the dev.to feed — which is the measured bottleneck (see
reach.py: 263 views across 17 articles).

Why a COMPOSED banner rather than the painting's own URL: dev.to renders covers
at 1000x420 with `fit=cover, gravity=auto`, so handing it a portrait painting
centre-crops the subject out. Compositing locally means the artwork is never
cropped and the title is legible in the feed.

Why the artwork is public-domain rather than generated: four of the channels in
reach.py ban AI-generated content, and CC0 museum art carries no such problem.

  covers.py build [id ...]   compose banners into ./covers
  covers.py push             commit + push covers/ to GitHub
  covers.py apply [id ...]   set each article's main_image via the dev.to API
  covers.py gen [id ...]     generate an inset per artprompts.json entry
  covers.py gen-file KEY "TITLE" "PROMPT"
                             cover for an article that has NO id yet (queued,
                             unpublished): covers/pre-KEY.png, committed + pushed,
                             prints the raw URL for its front matter
"""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, "/opt/hermes-agent")
import hermes_secrets as hs  # noqa: E402
import requests  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "covers")
QUERIES = os.path.join(ROOT, "artqueries.json")
REPO = "casareanderson/blog-kit"
BRANCH = "main"

W, H = 1000, 420
# The estate house palette — same values as the warden / listing-desk / trader
# dashboards and the HA `mono` theme, so a cover reads as ours at a glance.
GROUND, INK, MUTED, FAINT, LINE = "#0A0A09", "#F4F4F1", "#A3A39B", "#7C7C74", "#262624"
FONT_DIR = "/usr/share/fonts/truetype/ibm-plex"

# ⚠️⚠️ NOT the Art Institute, despite that being the obvious choice and the one
# the reference article uses. AIC's IIIF image server sits behind a Cloudflare
# BOT CHALLENGE (`cf-mitigated: challenge`) — every server-side fetch gets 403
# and no User-Agent gets past it. That article works because it is a Next.js
# app and the BROWSER loads the image; we composite server-side, so we cannot.
# The Met is keyless, CC0, and serves images to a plain urllib request.
MET = "https://collectionapi.metmuseum.org/public/collection/v1"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"}
CREDIT = "The Metropolitan Museum of Art · public domain"
# Generated covers get their own credit line. Labelling it is deliberate: the
# alternative is passing a synthetic image off as a photograph, and several of
# the channels in reach.py have rules about AI content that are the author's
# to comply with, not mine to hide.
GEN_CREDIT = "Illustration generated locally · Stable Diffusion 1.5"
PROMPTS = os.path.join(ROOT, "artprompts.json")


def _font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


STOP = {"a", "an", "the", "of", "and", "with", "in", "on", "at", "by", "to"}


def _get(url, tries=4):
    """Throttled GET. The Met has no key and no published rate limit, so the
    polite read of that is: go slowly and back off, not hammer until it 429s."""
    for i in range(tries):
        try:
            r = urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=30)
            time.sleep(0.8)
            return json.loads(r.read())
        except Exception:
            time.sleep(2.5 * (i + 1))
    return None


def _terms(q):
    return {w for w in q.lower().replace(",", " ").split() if w not in STOP and len(w) > 2}


def _score(obj, terms):
    """How much does this object ACTUALLY match the query?

    ⚠️⚠️ THIS IS THE WHOLE POINT OF THE MODULE. The Met's search is not
    relevance-ranked: `medium=Paintings` returns Patinir's "Penitence of Saint
    Jerome" as the first hit for casket, strongbox, halberdier, peddler, mask
    and usurer alike, and single-word queries return a fixed fallback set. Take
    result[0] on trust and you get 17 handsome, confident, thematically RANDOM
    covers — the exact failure mode the estate's fact-validator pattern exists
    to stop. So each candidate is scored against its own metadata, and a zero
    score is reported as "no match" rather than quietly shipped.
    """
    hay = " ".join(filter(None, [
        obj.get("title", ""), obj.get("objectName", ""),
        obj.get("classification", ""), obj.get("medium", ""),
        " ".join(t.get("term", "") for t in (obj.get("tags") or [])),
    ])).lower()
    sc = sum(2 if t in (obj.get("title") or "").lower() else 1
             for t in terms if t in hay)
    if "Painting" in (obj.get("classification") or ""):
        sc += 1
    return sc


def pick_artwork(queries):
    """Best-scoring public-domain Met object across the candidate queries.

    Returns None when nothing genuinely matches — a missing cover is a far
    better outcome than a confident wrong one.
    """
    best, best_sc, best_q = None, 0, None
    for q in queries:
        terms = _terms(q)
        s = _get(f"{MET}/search?" + urllib.parse.urlencode(
            {"q": q, "hasImages": "true", "isPublicDomain": "true"}))
        for oid in ((s or {}).get("objectIDs") or [])[:12]:
            o = _get(f"{MET}/objects/{oid}")
            if not o:
                continue
            img = o.get("primaryImageSmall") or o.get("primaryImage")
            if not img:
                continue
            sc = _score(o, terms)
            if sc > best_sc:
                o["image_url"] = img
                best, best_sc, best_q = o, sc, q
        if best_sc >= 4:      # clearly on-theme; stop spending calls
            break
    if best:
        best["_score"], best["_query"] = best_sc, best_q
    return best


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def compose(title, art, path):
    canvas = Image.new("RGB", (W, H), GROUND)
    d = ImageDraw.Draw(canvas)

    # --- artwork, CONTAINED not cropped ---------------------------------
    box_x, box_y, box_w, box_h = 56, 60, 300, 300
    src = art["image_url"]
    raw = (Image.open(src[7:]) if src.startswith("file://")
           else Image.open(urllib.request.urlopen(
               urllib.request.Request(src, headers=UA), timeout=60)))
    raw = raw.convert("RGB")
    raw.thumbnail((box_w, box_h), Image.LANCZOS)
    ox = box_x + (box_w - raw.width) // 2
    oy = box_y + (box_h - raw.height) // 2
    canvas.paste(raw, (ox, oy))
    d.rectangle([ox - 1, oy - 1, ox + raw.width, oy + raw.height], outline=LINE)

    # --- text block, MEASURED THEN PLACED -------------------------------
    # Laid out twice on purpose: once to measure, once to draw. The first
    # version top-aligned the text while the artwork was centred, which left
    # the bottom third of the banner dead and the whole thing looking
    # top-heavy. You cannot centre a block whose height you have not measured.
    tx, tw = 404, W - 404 - 56
    for size in (40, 36, 32, 29, 26, 24):
        f = _font("IBMPlexSans-SemiBold.ttf", size)
        lines = _wrap(d, title, f, tw)
        if len(lines) <= 4:
            break
    lh = int(size * 1.28)

    fm = _font("IBMPlexMono-Regular.ttf", 14)
    who = art.get("artistDisplayName") or "Unknown artist"
    what = (art.get("title") or "").replace("\n", " ")
    when = art.get("objectDate") or ""
    if art.get("artistDisplayName") or art.get("title"):
        cred = f"{who} · {what}" + (f", {when}" if when else "")
        cred_lines = _wrap(d, cred, fm, tw)[:2]
    else:
        cred_lines = []   # generated art has no artist or date to cite

    RULE_GAP, CRED_LH = 20, 20
    block_h = (len(lines) * lh) + RULE_GAP + 18 + (len(cred_lines) * CRED_LH) + 18
    # Centre the block on the artwork's own vertical midline, not the canvas:
    # the two then read as one unit whatever the painting's aspect ratio.
    ty = box_y + (box_h - block_h) // 2

    for ln in lines:
        d.text((tx, ty), ln, font=f, fill=INK)
        ty += lh
    ty += RULE_GAP
    d.line([(tx, ty), (tx + tw, ty)], fill=LINE)
    ty += 18
    for ln in cred_lines:
        d.text((tx, ty), ln, font=fm, fill=MUTED)
        ty += CRED_LH
    d.text((tx, ty), art.get("_credit", CREDIT),
           font=_font("IBMPlexMono-Regular.ttf", 13), fill=FAINT)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    canvas.save(path, "PNG", optimize=True)
    return path


def articles():
    k = hs.get("dev-to", path="/Devto")
    r = requests.get("https://dev.to/api/articles/me/all",
                     headers={"api-key": k}, params={"per_page": 100}, timeout=30)
    r.raise_for_status()
    return {str(a["id"]): a for a in r.json()}


def cmd_build(ids):
    qs = json.load(open(QUERIES))
    arts = articles()
    manifest = {}
    for aid, spec in qs.items():
        if spec.get("skip") or (ids and aid not in ids):
            continue
        a = arts.get(aid)
        if not a:
            print(f"{aid}  SKIP (not found)")
            continue
        art = pick_artwork(spec["q"] if isinstance(spec["q"], list) else [spec["q"]])
        if not art:
            print(f"{aid}  NO MATCH — left without a cover: {spec['q']}")
            continue
        p = os.path.join(OUT, f"{aid}.png")
        compose(a["title"], art, p)
        manifest[aid] = {"query": spec["q"], "why": spec["why"],
                         "artwork": art.get("title"),
                         "artist": art.get("artistDisplayName"),
                         "date": art.get("objectDate"),
                         "met_id": art.get("objectID"),
                         "matched_query": art.get("_query"), "score": art.get("_score"),
                         "file": f"covers/{aid}.png"}
        print(f"{aid}  {os.path.getsize(p)//1024:>4}KB  "
              f"score={art.get('_score')}  "
              f"{art.get('artistDisplayName') or 'Unknown'} — {art.get('title')}")
    json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
    print(f"\n{len(manifest)} built into {OUT}")


def cmd_recompose(ids):
    """Redraw from the manifest. Layout work must not re-run the art search:
    that is ~36 throttled API calls per article, and the artwork choice is
    already settled and reviewed by then."""
    arts = articles()
    man = json.load(open(os.path.join(OUT, "manifest.json")))
    for aid, m in man.items():
        if ids and aid not in ids:
            continue
        o = _get(f"{MET}/objects/{m['met_id']}")
        o["image_url"] = o.get("primaryImageSmall") or o.get("primaryImage")
        compose(arts[aid]["title"], o, os.path.join(OUT, f"{aid}.png"))
        print(f"{aid}  redrawn  {m['artist']} — {m['artwork']}")


def cmd_gen(ids):
    """Generate an on-topic 512x512 inset per article and compose the banner.

    512 square because the banner's artwork slot is a 300px square and 512 is
    SD1.5's native size — asking a 1.5 checkpoint for a banner-shaped latent
    duplicates the subject. At 300px the gibberish silkscreen text that SD1.5
    always produces is no longer legible, which is why hardware subjects work
    here and screen-UI subjects do not.
    """
    import comfy
    spec = json.load(open(PROMPTS))
    neg, style = spec["_negative"], spec["_style"]
    arts = articles()
    os.makedirs(OUT, exist_ok=True)
    man_path = os.path.join(OUT, "manifest.json")
    man = json.load(open(man_path)) if os.path.exists(man_path) else {}
    for aid, sp in spec.items():
        if aid.startswith("_") or (ids and aid not in ids):
            continue
        raw = os.path.join(OUT, f"gen-{aid}.png")
        # Seed from the article id: the same article regenerates identically,
        # so a rebuild is reproducible rather than a fresh roll of the dice.
        comfy.generate(sp["p"] + style, neg, int(aid) % 2**31, raw)
        art = {"image_url": "file://" + raw, "artistDisplayName": None,
               "title": None, "objectDate": None, "_credit": GEN_CREDIT,
               "_prompt": sp["p"]}
        compose(arts[aid]["title"], art, os.path.join(OUT, f"{aid}.png"))
        man.setdefault(aid, {})
        man[aid].update({"source": "generated", "prompt": sp["p"],
                         "file": f"covers/{aid}.png"})
        print(f"{aid}  generated  {sp['p'][:58]}")
    json.dump(man, open(man_path, "w"), indent=1)


def cmd_genfile(args):
    """A cover for an article that does not exist on dev.to yet.

    `gen` is keyed by article id, but a queued post has no id until it is
    published - and the cover should be there AT publish, when dev.to puts the
    card in the feed. So this takes the title and prompt directly, keys the file
    on the queue filename, and pushes just that file.
    """
    import re
    import zlib
    import comfy
    if len(args) != 3:
        sys.exit('usage: covers.py gen-file KEY "TITLE" "PROMPT"')
    key, title, prompt = args
    key = re.sub(r"[^a-z0-9-]+", "-", key.lower()).strip("-")
    spec = json.load(open(PROMPTS))
    os.makedirs(OUT, exist_ok=True)
    raw = os.path.join(OUT, f"gen-pre-{key}.png")
    # Seeded from the key, so the same queued file regenerates identically.
    comfy.generate(prompt + spec["_style"], spec["_negative"], zlib.crc32(key.encode()) % 2**31, raw)
    art = {"image_url": "file://" + raw, "artistDisplayName": None, "title": None,
           "objectDate": None, "_credit": GEN_CREDIT, "_prompt": prompt}
    rel = f"covers/pre-{key}.png"
    compose(title, art, os.path.join(ROOT, rel))
    subprocess.run(["git", "add", rel], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-q", "-m", f"Cover for queued article {key}"], cwd=ROOT, check=False)
    subprocess.run(["git", "push", "-q", "origin", BRANCH], cwd=ROOT, check=True)
    print(f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{rel}")


def cmd_push():
    subprocess.run(["git", "add", "covers"], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-m",
                    "Add dev.to cover banners from Art Institute public-domain art"],
                   cwd=ROOT, check=False)
    subprocess.run(["git", "push", "origin", BRANCH], cwd=ROOT, check=True)


def raw_url(aid, man=None):
    """⚠️ The filename is read from the manifest, NOT built from the id.

    dev.to does not store the cover — it proxies it through media2.dev.to with
    the origin URL embedded, and that proxy CACHES. Replacing a cover at the
    SAME url therefore keeps serving the old image for as long as the cache
    holds. A new generation must land on a new path so the url itself changes.
    """
    man = man or json.load(open(os.path.join(OUT, "manifest.json")))
    f = man[aid].get("file", f"covers/{aid}.png")
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{f}"


def cmd_apply(ids):
    """Set each article's cover, idempotently.

    ⚠️ dev.to rate-limits article UPDATES hard — a straight loop over 17
    articles gets HTTP 429 on roughly half of them. So: re-read what is
    already set and skip it (this is safe to re-run), space the writes out,
    and back off on a 429 rather than burning the attempt.
    """
    k = hs.get("dev-to", path="/Devto")
    man = json.load(open(os.path.join(OUT, "manifest.json")))
    live = {str(a["id"]): a for a in requests.get(
        "https://dev.to/api/articles/me/all", headers={"api-key": k},
        params={"per_page": 100}, timeout=30).json()}

    todo = []
    for aid in man:
        if ids and aid not in ids:
            continue
        # The cover comes back wrapped in dev.to's image proxy, so the test is
        # "does the current cover point at our file", not string equality.
        cur = live.get(aid, {}).get("cover_image") or ""
        if man[aid]["file"] in urllib.parse.unquote(cur):
            print(f"{aid}  already set — skipped")
            continue
        todo.append(aid)

    for n, aid in enumerate(todo):
        for attempt in range(6):
            r = requests.put(f"https://dev.to/api/articles/{aid}",
                             headers={"api-key": k},
                             json={"article": {"main_image": raw_url(aid, man)}}, timeout=30)
            if r.status_code == 429:
                wait = 20 * (attempt + 1)
                print(f"{aid}  429, waiting {wait}s")
                time.sleep(wait)
                continue
            print(f"{aid}  HTTP {r.status_code}  {raw_url(aid, man)}")
            break
        if n < len(todo) - 1:
            time.sleep(12)


if __name__ == "__main__":
    cmds = {"build": cmd_build, "apply": cmd_apply, "recompose": cmd_recompose,
            "gen": cmd_gen, "gen-file": cmd_genfile, "push": lambda _: cmd_push()}
    # ⚠️ An unknown word used to fall through to PUSH (`covers.py --help` committed
    # and pushed). Now it prints the usage and does nothing.
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]](sys.argv[2:])

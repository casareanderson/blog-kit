# blog-kit

How I write, illustrate and publish technical posts to dev.to from a terminal —
the scripts, the endpoints, and the traps that cost me time.

Nothing here is a framework. It is four small pieces that happen to fit together:

| Piece | What it does |
|---|---|
| `publish.py` | Front-matter markdown → a live dev.to article, over the API |
| `diagram.sh` | Hand-written SVG → 2× PNG, ready to embed |
| `drafts/` | Posts as plain files, with a `published: false` front-matter switch |
| `assets/` | The images, versioned next to the post that uses them |

## Why files and not the dev.to editor

A post is a build artifact. Keeping the source in a repo means the diagrams are
regenerable, the wording is diffable, and publishing is one command rather than
a copy-paste into a web form at midnight. The dev.to editor is still there when
a post needs fixing after the fact — it edits the same article this publishes.

## Publishing

```bash
export DEVTO_API_KEY=...        # dev.to → Settings → Extensions → DEV Community API Keys
python3 publish.py drafts/my-post.md            # dry run: shows what would be sent
python3 publish.py drafts/my-post.md --publish  # actually posts it
python3 publish.py drafts/my-post.md --id 12345 # update an existing article
```

Front matter drives it:

```yaml
---
title: "The hard part of an internal tool isn't the API. It's the second user."
published: false
description: "One sentence for the card and the search result."
tags: selfhosted, api, architecture, webdev
---
```

## Diagrams

I write the SVG by hand and rasterise it. No diagramming tool, because the ones
that produce good-looking boxes produce identical-looking boxes, and a diagram
is worth including only when it says something the paragraph next to it cannot.

```bash
./diagram.sh assets/internal-tool/01-glue.svg     # → 01-glue.png at 2× width
```

Rules that keep them readable on dev.to:

- **Paint the background.** dev.to has a dark mode; a transparent PNG with dark
  text vanishes in it. Every diagram here has an explicit white background.
- **2× width.** Author at 880px, render at 1760px. dev.to serves the image at
  roughly 800px wide, and the extra pixels are what stop the type looking soft
  on a retina screen.
- **No real hostnames, no real IPs, no real customer names.** See below — I
  published a post with my LAN addresses in it and had to edit them out.

## What the posts are made of

See [docs/ENDPOINTS.md](docs/ENDPOINTS.md) for the API details and the traps.

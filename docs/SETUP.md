# Setting up blog-kit

blog-kit is the small kit behind the [dev.to/iam-tech](https://dev.to/iam-tech) posts: a publisher with a leak
check, a diagram renderer and a cover maker. The publisher and diagrams take five minutes. Covers are optional
and need more (see the last section).

The blocks marked as tested run on a fresh Ubuntu runner every week in
[`setup-check`](../.github/workflows/setup-check.yml). Anything that talks to dev.to needs your API key, so CI
proves everything up to the point of sending and stops there.


![What a passing run looks like on a fresh machine (excerpt from `setup-check` on 11 October 2026). Secrets in the output are masked](setup-run.png)

*What a passing run looks like on a fresh machine (excerpt from `setup-check` on 11 October 2026). Secrets in the output are masked.*

## What you need

- Python 3. `publish.py` uses the standard library only.
- For diagrams: `rsvg-convert`, from the `librsvg2-bin` package on Debian and Ubuntu.
- To publish: a dev.to API key (dev.to → Settings → Extensions → DEV Community API Keys).

```sh setup-check
sudo apt-get update -qq && sudo apt-get install -y -qq librsvg2-bin
git clone -q https://github.com/casareanderson/blog-kit.git
cd blog-kit
```

## Dry-run a post

Every run is a dry run unless you add `--publish`. Try it on one of the drafts in the repo:

```sh setup-check
python3 publish.py drafts/devto-05-buzzwords.md
```

```
title : AI buzzwords, explained with numbers from my own server
tags  : ['ai', 'beginners', 'selfhosted', 'llm']
body  : 11107 chars, ~1926 words

dry run — nothing sent. Add --publish when you mean it.
```

Nothing has left your machine, and no key was needed.

## Your own post

Write it in Markdown with this front matter at the top:

```yaml
---
title: "The hard part of an internal tool isn't the API. It's the second user."
description: "One sentence for the card and the search result."
tags: selfhosted, api, architecture, webdev
---
```

`publish.py` reads `title`, `description` and `tags`. Any other key is ignored, including `published: false`:
`--publish` is the only switch, and an article it sends is published.

## The leak check

Before anything goes out, the post body is checked for private IP addresses (10.x, 127.x, 172.16–31.x,
192.168.x), API keys and `password=`/`token=`-style secrets. If it finds one, it refuses, even on a dry run:

```sh setup-check
cat > /tmp/leaky.md <<'EOF'
---
title: "Test post"
description: "A test"
tags: test
---
My NAS is at 10.1.2.3 and it is fine.
EOF
! python3 publish.py /tmp/leaky.md
```

```
⚠️  the leak check found:
    - a private IP: 10.1.2.3

refusing to publish. Genericise it, or pass --force.
```

Swap real addresses for documentation ones (`192.0.2.x`, `example.com`). `--force` publishes anyway; use it only
when the "leak" really is meant to be there.

## Publish for real

Not tested in CI: this needs your key and creates a real article.

```
export DEVTO_API_KEY=...
python3 publish.py drafts/my-post.md --publish              # creates and publishes it
python3 publish.py drafts/my-post.md --publish --id 12345   # updates article 12345 instead
```

It prints the article's `id` and `url`, then reads it back from dev.to and prints `live: published_at = ...`. If
that line says `NOT PUBLISHED`, the create worked but the article isn't public; check it in your dev.to dashboard.

There's no fallback for the key on purpose. Without it, `--publish` stops with
`DEVTO_API_KEY is not set. No fallback on purpose.`

## Render a diagram

Draw the diagram as an SVG 880px wide with an explicit white background, then render it at twice that for sharp
text on high-DPI screens:

```sh setup-check
./diagram.sh assets/internal-tool/01-glue.svg
ls -l assets/internal-tool/01-glue.png
./diagram.sh assets/internal-tool/01-glue.svg 1200
```

It prints the PNG's path and size. The second argument is the width in pixels (default `1760`). The white
background matters: dev.to has a dark mode, and dark text on a transparent PNG disappears in it.

## Covers (optional)

Not tested in CI. `covers.py` makes the 1000×420 cover banners: a generated square inset next to the title, set
as the article's cover through the API. It needs more than the rest of the kit:

| what | why | where to change it |
|---|---|---|
| a [ComfyUI](https://github.com/comfyanonymous/ComfyUI) server with an SD 1.5 checkpoint | generates the inset | `HOST` and `CKPT` at the top of `comfy.py` (defaults `http://127.0.0.1:8188`, `v1-5-pruned-emaonly.safetensors`) |
| IBM Plex Sans and Mono | the banner text | `FONT_DIR` in `covers.py` (default `/usr/share/fonts/truetype/ibm-plex`) |
| push access to a GitHub repo | dev.to is given the image's raw GitHub URL | `REPO`, `BRANCH` in `covers.py` |
| your dev.to key | to set the cover | see below |

`covers.py` reads the key through the author's own secret resolver (`hermes_secrets`, from `/opt/hermes-agent`).
On your machine, replace the two `hs.get(...)` calls with `os.environ["DEVTO_API_KEY"]`.

```
python3 covers.py gen 4593582          # generate the inset and compose covers/4593582.png
python3 covers.py apply 4593582        # set it as that article's cover
python3 covers.py gen-file KEY "TITLE" "PROMPT"   # for a post with no id yet
```

Run with no command and it prints its usage and does nothing. The prompts live in `artprompts.json`.

## Common problems

| you see | what it means | what to do |
|---|---|---|
| `no YAML front matter (--- title: ... ---)` | the file doesn't start with a `---` block | add the front matter above |
| `the leak check found: ...` and `refusing to publish` | a private IP or key-like string in the body | genericise it, or `--force` if it's deliberate |
| `DEVTO_API_KEY is not set. No fallback on purpose.` | `--publish` without the key | `export DEVTO_API_KEY=...` |
| `POST https://dev.to/api/articles -> 401: ...` | wrong or revoked key | make a new key on dev.to |
| `POST ... -> 422: ...` | dev.to rejected the article, often a bad tag or a title it doesn't like | read the message; dev.to allows four tags, letters and numbers only |
| `rsvg-convert not found — apt-get install -y librsvg2-bin` | diagrams need librsvg | install it |
| `live: published_at = NOT PUBLISHED` | created, but not public | check the dashboard |

## Update and uninstall

```
cd blog-kit && git pull     # update
rm -rf blog-kit             # uninstall; nothing is written outside the folder except covers you push
```

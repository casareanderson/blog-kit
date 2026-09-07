#!/usr/bin/env python3
"""A front-matter markdown file -> a live dev.to article.

Dry by default. `--publish` is the only thing that writes to the internet, and
it is a separate word you have to type, because the failure mode of a publisher
that posts on every run is a half-finished draft with your name on it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

API = "https://dev.to/api"
# ⚠️ NOT OPTIONAL. dev.to answers a bare urllib request with `403 Forbidden
# Bots` - it is the User-Agent, not the key, and it happens before anything
# looks at authentication.
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36")

# Things that must never reach a published post. Checked, not trusted to
# memory: I published private LAN addresses once already.
LEAKS = [
    (re.compile(r"\b(?:10|127)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "a private IP"),
    (re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b"), "a private IP"),
    (re.compile(r"\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b"), "a private IP"),
    (re.compile(r"\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}",
                re.I), "something that looks like a credential"),
    (re.compile(r"\bsk-[A-Za-z0-9\-]{20,}"), "an API key"),
]


def parse(path: str) -> tuple[dict, str]:
    raw = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        sys.exit(f"{path}: no YAML front matter (--- title: ... ---)")
    meta = {}
    for line in m.group(1).split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta, m.group(2).strip()


def leaks(body: str) -> list[str]:
    found = []
    for pattern, what in LEAKS:
        for hit in pattern.findall(body):
            found.append(f"{what}: {hit if isinstance(hit, str) else hit[0]}")
    return found


def call(method: str, url: str, key: str, payload: dict | None = None) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode() if payload else None,
        headers={"api-key": key, "User-Agent": UA,
                 "Accept": "application/vnd.forem.api-v1+json",
                 "Content-Type": "application/json"},
        method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {url} -> {e.code}: "
                 f"{e.read()[:300].decode('utf-8', 'replace')}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--publish", action="store_true",
                    help="actually post it (otherwise this is a dry run)")
    ap.add_argument("--id", type=int, default=0,
                    help="update this existing article instead of creating one")
    ap.add_argument("--force", action="store_true",
                    help="publish despite the leak check")
    args = ap.parse_args()

    meta, body = parse(args.path)
    tags = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]
    if len(tags) > 4:
        print(f"! {len(tags)} tags given; dev.to keeps 4 and drops the rest "
              f"silently. Keeping: {tags[:4]}")
        tags = tags[:4]

    print(f"title : {meta.get('title')}")
    print(f"tags  : {tags}")
    print(f"body  : {len(body)} chars, ~{len(body.split())} words")

    problems = leaks(body)
    if problems:
        print("\n⚠️  the leak check found:")
        for p in problems:
            print(f"    - {p}")
        if not args.force:
            sys.exit("\nrefusing to publish. Genericise it, or pass --force.")

    if not args.publish:
        print("\ndry run — nothing sent. Add --publish when you mean it.")
        return

    key = os.environ.get("DEVTO_API_KEY", "").strip()
    if not key:
        sys.exit("DEVTO_API_KEY is not set. No fallback on purpose.")

    article = {"title": meta["title"], "body_markdown": body,
               "published": True, "description": meta.get("description", ""),
               "tags": tags}
    if args.id:
        res = call("PUT", f"{API}/articles/{args.id}", key, {"article": article})
    else:
        res = call("POST", f"{API}/articles", key, {"article": article})

    # ⚠️ `published` comes back as null on a SUCCESSFUL create. Reporting it
    # would say "published: None" and read as a failure, so confirm instead.
    url = res.get("url", "")
    print(f"\nid  : {res.get('id')}\nurl : {url}")
    live = call("GET", f"{API}/articles/{res.get('id')}", key)
    print(f"live: published_at = {live.get('published_at') or 'NOT PUBLISHED'}")


if __name__ == "__main__":
    main()

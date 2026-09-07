# Endpoints, and what they do when you get them wrong

Everything here is measured against the live API, not read off a docs page.

## dev.to (Forem) API

Base `https://dev.to/api`. Auth is a single header, `api-key`. No OAuth, no
refresh, no scopes — which is pleasant right up until you paste the key into
something public, because it is full write access to your account.

| Call | Method | Notes |
|---|---|---|
| `/articles` | POST | Create. Returns the article, including `url` and `id`. |
| `/articles/{id}` | PUT | Update. This is also how you **unpublish**: `{"article":{"published":false}}`. |
| `/articles/{id}` | GET | Read one, **with** `body_markdown`. |
| `/articles?username=x` | GET | List someone's published posts — **no body**. |
| `/articles?top=7` | GET | Most-liked of the last 7 days. Good trending signal. |

### ⚠️ A bare request is refused as a bot

```
403 Forbidden — "Forbidden Bots"
```

This is the **User-Agent**, not the key. Python's urllib identifies itself as
urllib and is refused before authentication is even considered. Send a browser
UA on every call, including the ones that work fine in curl.

### ⚠️ The list endpoint carries no body

`/articles?username=…` returns titles and metadata only. Anything that needs
the text has to fetch each article by id. A tool built on the list alone
silently summarises titles — it looks like it is working.

### ⚠️ `published` comes back as `null` on create

A successful POST that publishes an article returns `"published": null`, which
reads exactly like a failure. Do not trust it. Confirm with an **anonymous**
fetch of the returned URL, or a GET of `?username=you`, and check the article
is actually in the list.

### Tags

Four maximum, lowercase alphanumeric, no hyphens. Extra tags are dropped
silently rather than rejected, so a five-tag post publishes with four and no
error anywhere.

## Secrets

The key lives in a secret manager and reaches the script as an environment
variable. It is never in the repo, never in the front matter, and never in a
committed example. `publish.py` refuses to run without `DEVTO_API_KEY` rather
than falling back to anything.

## ⚠️ The mistake worth copying from

I published a post containing a compose block with my actual LAN addresses in
it — `192.168.x.x` for the model host, the search host and the crawler. Private
range, so not a breach, but it is free reconnaissance for anyone who later gets
a foothold, and it is untidy in a way that reads as careless.

**Genericise before publishing, not after.** Hostnames like `gpu-box.lan` say
the same thing and mean nothing to a stranger. Ports are usually fine and often
informative — `11434` tells a reader it is Ollama. Names of real customers,
tenants and colleagues are not fine; a log sample is exactly the place they
sneak through.

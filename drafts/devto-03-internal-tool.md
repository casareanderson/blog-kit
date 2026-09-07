---
title: "The hard part of an internal tool isn't the API. It's the second user."
published: false
description: "I replaced a SaaS subscription with a container that glues together services I already run. The integrations took a weekend. Everything that came after — isolation, three auth modes, audit — took the rest of the time, and that is the part nobody writes up."
tags: selfhosted, api, architecture, webdev
---

Every small business ends up paying a monthly fee for software that is, underneath, a
database and about five API calls. You know this because you have looked at it and
thought *I could build that*. You are right. You are also wrong about which part is hard.

I built the thing. It runs in a 239 MB container, costs **$0.000627 per item processed**,
and talks to a vendor API I am not going to describe here, because the vendor API is the
boring part and it is not what makes this worth reading.

What is worth reading is what happened after it worked.

## The problem: I was renting a workflow

The tool takes photos in, does a pile of research, and produces a priced draft for
review. Off-the-shelf products for this exist. They charge per seat, per month, and they
hold your photos and your numbers on their infrastructure.

That is a fine trade for most people. It stopped being a fine trade for me at the point
where I was already running — for other reasons, on hardware I own — a vision model, a
metasearch engine, a crawler and an object store. I was paying a subscription for the
glue between four things I already had.

So: build the glue.

## The idea: the tool is glue, and the glue should be thin

The design rule I set was that **nothing heavy runs inside the container**. Every
expensive dependency is a URL to something else:

```yaml
environment:
  DESK_OLLAMA_URL:   "http://gpu-box.lan:11434"     # vision + language, my GPU box
  DESK_SEARXNG_URL:  "http://tools.lan:8888"        # metasearch, no API key, no quota
  DESK_CRAWL4AI_URL: "http://tools.lan:11235"       # page fetching
```

Three consequences fall straight out of that, and they are the whole architecture:

- **The container stays small** (239 MB) because it contains no model weights, no
  browser, no search index. It is Python, SQLite and templates.
- **The data stays on my LAN.** Photos never leave the network except to the one API
  that has to receive them.
- **Every dependency is swappable at the URL level.** The language model is a router:
  local Ollama by default, a paid API when a task actually needs the better model. That
  single seam is why the running cost is measurable in cents per thousand items rather
  than in a subscription.

If you take one thing from this: **an internal tool should be the only thing you wrote.**
Everything it needs should already be running, or be a container someone else maintains.
The moment you vendor a model into your own image, you own an upgrade problem forever.

That part took a weekend. Then somebody else needed to log in.

## The part that actually took the time

Here is the transition nobody warns you about. A tool with **one** user has no security
model, no isolation model, and no audit requirement. A tool with **two** users has all
three, and retrofitting them is not a feature — it is a rewrite of every data path in the
application.

### Isolation is a shape, not a discipline

The naive version of multi-user is a `tenant_id` column and a promise to remember the
`WHERE` clause. That promise gets broken by whoever adds the seventeenth query at 11pm.

So the data layer makes the mistake impossible to type:

```python
book = store.book("alice")     # cannot be constructed without a tenant
book.items()                   # scoped, always
store.items()                  # AttributeError — it does not exist
```

There is no unscoped accessor to forget the filter on. If you want items, you need a
book, and you cannot have a book without saying whose. The isolation is in the *shape* of
the API, not in the diligence of the person using it.

### The bug that proves why

I still got it wrong, in a way worth showing because it is so ordinary. The user object
had a sensible-looking default:

```python
tenant: str = "default"        # looks harmless. it is not.
```

Anonymous, unauthenticated requests constructed a user object without overriding it — so
an unauthenticated request resolved to **the default tenant's data**. Combined with an
OAuth callback route, the shape of the exploit was: complete a consent flow with your own
account, replay the callback with no session cookie, and the default tenant's refresh
token is now attached to your account.

The fix is one character's worth of typing and a comment three times as long:

```python
tenant: str = ""               # MUST stay empty. Only a real row may set a tenant.
```

The lesson generalises: **a default that is convenient for the happy path is a decision
about what happens when there is no user.** In an unscoped app that is a nuisance. In a
multi-tenant app it is the whole game.

### Three auth modes, and never two

There are exactly three ways somebody gets in, and the app runs precisely one of them:

| Mode | Who authenticates | Use when |
|---|---|---|
| `solo` *(default)* | nobody | One person, one machine |
| `signin` | the app (scrypt + session rows) | Several people, no SSO |
| `proxy` | your forward-auth proxy | You already run Authelia or similar |

Two things I would tell anyone building this:

**The default is no authentication, and the failure is silent.** There is no error message
— just a dashboard anyone on the network can drive. If you ship an internal tool with an
open default, say so loudly in the UI, because nobody reads the README of software that
already appears to work.

**Proxy mode is a promise you are making, not a feature you are switching on.** It means
*"this port cannot be reached except through the proxy."* Identity headers are the
proxy's **output**, not a credential. Anyone who can reach the port directly can send
`Remote-User: you` and be believed. If you cannot firewall the port, you cannot use the
mode, and no amount of code in your app changes that.

I found the sharp edge of this from the other direction last week: I went looking for a
missing "reset password" button and discovered the instance did not have accounts enabled
at all. Same UI, same version, different mode — and the mode is what decides whether a
password is even a concept there. Modes are load-bearing. Show the active one on screen.

### Seat and role are different questions

Permission checks collapse into one boolean if you let them. I kept two, deliberately:

- a **seat** says what the account is *entitled to* (a billing question)
- a **role** says what the person is *trusted with* (an organisational one)

Both have to allow an action. The reason is not purity — it is that these get edited by
different people at different times, and folding them into one expression means widening
a plan by accident when you meant to promote a colleague.

### Support access, without becoming the customer

The last piece, and the one I would build earlier next time. As the operator I sometimes
need to see what a client sees, because "it's broken" is not a bug report.

The obvious implementation is to log in as them. **Don't.** The moment you can
impersonate a user, no line in that account's history can be trusted to mean the person
it names did it — you have traded away the only thing an audit log is for.

What I built instead is a scope switch. I stay myself; the app renders their data; a
banner across every page says whose desk I am standing in; and entering and leaving are
both written to **two** logs:

```
default  | chris started working as 'Northgate Trading'
northgate | chris (install owner) started working in this client
northgate | chris (install owner) stopped working in this client
default  | chris stopped working as 'northgate'
```

The client's log, so they can see a stranger in their data. My log, so the record survives
if that client is ever deleted. And while I am in there, install-wide settings are
**denied to me** — the predicate that says "this person owns the install" deliberately
returns false while acting inside a client, because a support session that can repoint
everyone's model endpoint from inside one customer's account is not a support session.

## Shipping

What "done" meant in practice:

- **Working end to end** on the boring path, measured against real cases the operator had
  already caught by hand. Three of them: one item that used to price at £840 now prices at
  £10.00 from real comparable sales; a photo too dark to identify now returns **no price**
  and goes to review instead of inventing one.
- **A cost I can state.** $0.000627 an item, about 63p per thousand. Everything except the
  language models is free because everything except the language models is mine.
- **A list of what is deliberately not built.** Traffic tracking and automatic repricing
  are not in it. Writing that list down is what stops "finished" from being a feeling.

## The lesson

I set out to replace a subscription and assumed the integration was the work. The
integration was a weekend. **Isolation, authentication and audit were the product** — they
are what the subscription was actually selling me, and they are what you inherit
responsibility for the moment you decide to own the tool instead of rent it.

That is not an argument against building it. I would do it again; it works, it costs
pence, and the data is on hardware I can see from here. It is an argument for knowing
which part you are signing up for. If your plan is "it's just a few API calls", you have
costed the weekend and not the product.

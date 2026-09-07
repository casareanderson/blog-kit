---
title: "The paywall tax: I checked, and most of it is just a nicer URL"
published: false
description: "I spent an evening pricing what four commercial data sources wanted, then went and got the same numbers from the endpoints their own websites call. Three were free. One was genuinely worth paying for. Here is how to tell them apart."
tags: api, webdev, selfhosted, data
---

I needed used-goods price data for a tool that prices second-hand stock. Four
sources, four price tags: monthly subscriptions, per-request billing, an API that
requires an application and a partner agreement.

I checked all four against the endpoints their own websites call. **Three of them
were free.** One was genuinely, structurally paid — and knowing which is which is
the whole skill.

## The pattern: the storefront blocks you, the search does not

Here is the thing that keeps being true. A retailer's website is behind bot
protection. A server request gets a 403 and a Cloudflare challenge page:

```
retailer A (refurbished electronics)   403
retailer B (trade-in service)          403
aggregator C (price comparison)        403
aggregator D (price comparison)        403
retailer E (used electronics chain)    403
```

Five companies, same answer. You could reasonably conclude the data is closed.

But a modern storefront does not do its own searching. It hands that to a search
service — Algolia, Elastic, Constructor — which lives on a **different hostname**,
because it has to be reachable by the customer's browser. And that hostname is
usually not behind the same protection, for the very good reason that putting a
bot challenge in front of your own search box breaks your own search box.

So:

```
www.<retailer>.com     403   ← the storefront
search.<retailer>.io   200   ← the search index the storefront calls
```

One is a wall. The other is the same data, answering politely, unauthenticated.
I am not routing around the wall — I am asking the way the page asks.

What came back was better than the paid actor's output:

```
sellPrice                145     what they retail it for
cashPriceCalculated       82     what they PAY you today
exchangePriceCalculated  100     the same in vouchers
buyPerc                   57     ← the trade-in ratio, published as a field
exchangePerc              69
firstPrice               300     RRP when new
```

That `buyPerc` is the thing people write forum posts speculating about — "what
percentage does this shop pay?" It is not a secret. It is a field. It varies by
category: 57% on headphones, 44% on phones.

## The second one was paid *and wrong*

The card-price source had a paid API and a $0.0002-per-call scraper on a
scraping marketplace. Its own site has a `search-products` endpoint that returns JSON to a
plain server request, with no key.

But that is not the interesting part. The interesting part is that **the paid
scraper mislabels the data.**

Card prices come in a grade ladder:

```
Ungraded  $365 · Grade 7 $315 · Grade 8 $325 · Grade 9 $402 · Grade 9.5 $670 · PSA 10 $1,420
```

The paid actor returns those same numbers under the field names `loosePrice`,
`completePrice` and `newPrice` — which are the **video-game** column names from
the same site. Its "completePrice" is actually Grade 7. If you trusted the
labels, you would price a raw card off a graded column, and on that example the
gap between Ungraded and PSA 10 is **four-fold**.

Reading the real column headings takes twenty lines and is both free and more
correct than the thing you would have paid for. That is not a dig at the author —
it is what happens when a scraper generalises one site's table across categories
that do not share a schema.

## The third was a cookie

One large second-hand marketplace 403s its API to a server. Its homepage does not.
Fetch the homepage, keep the cookie jar, call the API again:

```
GET  /                       200   (10 cookies)
GET  /api/v2/catalog/items   200   application/json
```

No login. No credentials. That is an anonymous session — the exact thing a first
visit in a browser gets — and the API is the one their own front end calls.

## The one that was real

And then a large marketplace's completed-sales data, which I could not get for
free, and did not try very hard to.

There is no public endpoint. The sold-search pages 302 a server. The official
route is an API that requires a written application describing your use case, and
it can be declined. I tested the scope directly rather than guessing:

```
scope=api_scope                    -> 200, token
scope=buy.marketplace.insights     -> invalid_scope:
                                      "exceeds the scope granted to the client"
```

Refused at the token endpoint, before any data call. That is not a bug or a
missing header — it is an entitlement, and no amount of code changes it.

**This one is genuinely worth paying for**, and the reason is instructive: they
are not selling access to a public page. Completed sales are not published anywhere.
The data exists because they run the marketplace, and the paid resellers who
offer it are running proxy infrastructure at a scale I cannot reproduce and
should not try to.

There is also a version of "getting it for free" that is actually just moving the
risk onto yourself. I could have crawled the sold listings using my own logged-in
seller session. I did not, and would not: that account holds live listings and
feedback, and scraping detection acts on the account doing the scraping. Saving a
subscription is not worth the account the business runs on.

## So how do you tell them apart?

The test that has held up for me:

**Is the data on a page a customer can see without logging in?** If yes, there is
almost always an unauthenticated endpoint serving it, because the page needs one.
Open the network tab, look for the XHR that populates the results, and check
whether it answers a plain request. Most "data paywalls" over public catalogues
are selling **convenience** — a nicer URL, a schema, a support contract, no
maintenance when the site changes. Those are real things and sometimes worth
buying. They are not exclusive access.

**Or is the data a byproduct of running the marketplace?** Completed transactions,
private inventory, anything that exists only because that company operates the
thing. Then it is genuinely theirs, the price is the price, and the free routes
you will find are somebody else's terms-of-service problem waiting to become
yours.

Three of my four were the first kind. One was the second. The bill went from about
£15/month to zero, and the free version of the card source is more accurate than
the paid one.

## The part that is not about money

What I actually got from an evening of this was not a saved subscription. It was
finding out that a paid feed was mislabelling grade columns — which I would never
have discovered by consuming it, because the field names looked authoritative and
the numbers looked plausible.

Reading the source made the data *better*, not just cheaper. That is the argument
for doing it, and it survives even if the subscription was affordable.

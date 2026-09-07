---
title: "Football Manager taught me more about database UX than any course did"
published: false
description: "Twenty years of scouting filters, custom views and star ratings that are secretly confidence intervals. A serious look at a silly teacher — and how it shows up in the listing tool I actually ship."
tags: webdev, database, ux, beginners
---

I have spent an embarrassing number of hours in Football Manager. Not playing
football — playing a *spreadsheet*. And at some point while building a tool that
prices second-hand stock, I realised I was reaching for interface ideas I had
absorbed entirely from a video game about being a bloke in a coat.

Football Manager is a relational database with a football skin. Millions of rows,
dozens of columns per row, and the actual game is querying it well. Which makes
it, accidentally, one of the best pieces of database UX ever shipped — because
it had to teach filtering and joins to people who would leave immediately if it
felt like teaching.

Here is what it gets right, and where each idea turned up in something I built
for real.

## 1. The scouting filter is a query builder that nobody resents

In any normal application, "advanced search" is where enthusiasm goes to die. In
FM, building a search is the *fun part*. People do it voluntarily, for hours,
and share their filters online.

What it actually is:

```sql
SELECT * FROM players
WHERE age <= 23
  AND position IN ('DC','DR')
  AND value <= 2000000
  AND determination >= 14
ORDER BY potential DESC
```

Nobody thinks of it that way. They think "young right-backs I can afford who
won't sulk". The interface never mentions a query. It never shows an operator
dropdown containing `LIKE` and `NOT IN`. It asks questions in the vocabulary of
the person asking them.

**The lesson I actually used:** in my listing tool, the review screen does not
offer a filter builder. It offers the three questions I ever actually ask — what
is waiting, what is live, what sold — and each is a stored query with a name a
human would use. If a fourth question appears often enough, it becomes a fourth
button, not a field in a form.

## 2. Custom views are the killer feature, and they are just column selection

FM lets you decide which columns you see, save that arrangement, name it, and
switch between saved arrangements instantly. Scouting view, contract view,
injury view.

That is `SELECT` with a memory. It is also the single most-used advanced feature
in the game, by people who would never call it that.

Every data-heavy tool should steal this and almost none do. The usual approach is
one table with every column, which serves nobody — and the person looking at
contracts and the person looking at injuries are doing genuinely different jobs.

**Where I fell short:** my own item table shows the same columns to everybody.
The data has **38 fields per item** — pricing, postage, listing state, timestamps
— and the screen shows a fixed handful. That is a decision I have not revisited,
and writing this paragraph is what made me notice it.

## 3. Star ratings are confidence intervals wearing a costume

This is the clever one.

A scout does not report "this player has Finishing 14". He reports **three
stars**, and if you have only watched the player twice, the stars are shown as a
*range* — somewhere between two and four. Send a better scout, watch more games,
and the range narrows.

The game is showing you two different things in one glyph: **how good the player
is**, and **how much it knows**. It never pretends to a precision it does not
have, and it never refuses to answer either.

**This one I stole almost directly.** Every price my tool produces carries a
confidence:

```
none | thin | ok | strong
```

`thin` means it found a price but the evidence was weak — few comparable sales,
or sources that disagreed. And when independent sources disagree badly enough,
it does something FM does too: **it declines to give a number.** One item came
back at 84 pence when every other signal said £32, and the right output was not a
confident 84 pence. It was "I am not telling you a price, and here is why."

An interface that can only say a number will eventually say a wrong one
confidently. Give it a way to shrug.

## 4. Attribute masking: hiding data is a feature

Turn on attribute masking and you no longer see numbers for players you have not
scouted. You see estimates that sharpen with knowledge.

Almost every dashboard I have ever used does the opposite: it shows every value
it has at full precision, whether that value is measured, inferred, or a
placeholder somebody typed in 2019. The user has no way to tell which.

**FM's position is that unearned precision is a lie.** A number displayed to two
decimal places reads as measured whether or not it is. If your app is showing
estimates, it should look like it is showing estimates.

## 5. Progressive disclosure: the tutorial is the game

You can play FM for a season knowing three screens. Squad, tactics, next match.
The other four hundred screens are still there, and they surface when you go
looking.

Compare that to enterprise software, which usually opens on a screen containing
everything, arranged by which department built which panel.

**The pattern:** default to the two or three things people do daily, and let
depth be discoverable rather than mandatory. The Setup page in my tool works this
way now — it shows the next thing that is blocking you, and the rest is a list
below.

Though I only got there by getting it wrong first: it used to show every setup
step to everybody, including install-level instructions telling a *customer* to
edit an environment file and restart a container they have no access to. Now
each person sees their own part. Same lesson, learned the expensive way.

## 6. Sorting is analysis, and the second sort is what people actually want

FM tables sort by any column, and hold a secondary sort. Sort by position, then
by ability. Sort by value, then by age.

Single-column sorting answers "who is best". Two-column sorting answers "who is
best *for this*", which is nearly always the real question. Most tables on the
web give you one, and it is the less useful one.

## What it is really teaching

FM's actual subject is **decision-making under uncertainty with incomplete
data**. The football is set dressing. You are always choosing with less
information than you would like, from a source of known unreliability, under
time pressure.

Which is also a description of pricing a second-hand item from four disagreeing
sources, and of most software worth building.

The reason it works as a teacher is that it never once explains any of this. It
does not tell you what a filter is, or a join, or a confidence interval. It hands
you a squad and a problem, and twenty years later you notice you have opinions
about column layout.

If you build anything with a table in it, go and play a season. Tell people it is
research. It very nearly is.

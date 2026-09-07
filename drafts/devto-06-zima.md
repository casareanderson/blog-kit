---
title: "A homelab that fits in a shoebox: what I'd buy again, and what I wouldn't"
published: false
description: "A ZimaBlade, one hard drive, and the specs nobody prints on the box. Real power figures, the PCIe limits that bite, the disk layout that looks broken and isn't, and the £30 upgrade I spent months on that would have made things worse."
tags: homelab, selfhosted, hardware, beginners
---

You do not need a rack. You do not need a Dell tower that sounds like a hairdryer
and adds £20 a month to your electricity bill. A large amount of what people call
a homelab runs on a machine the size of a paperback.

Mine does. This is the shopping list, the specifications that actually matter,
and — more usefully — the two things I got wrong.

## What it is

A **ZimaBlade** with **one hard drive** attached. That is the entire base build:
a low-power x86 board with SATA ports, an aluminium shell, and a disk.

x86 matters more than it sounds. A Raspberry Pi is cheaper and lovely, but a
meaningful share of self-hosted software still ships x86-only container images,
and discovering that after you have bought the thing is a bad afternoon. Anything
you read about running on a normal server runs here.

## The specifications that actually decide things

Not the marketing ones. These are the four numbers that determined what I could
and could not do:

```
PCIe slot     PCIe 2.0 x4      ~2 GB/s ceiling
Slot power    25 W             what the slot itself can deliver
Power input   12 V / 3 A       36 W total, over USB-C
Hot-plug      not supported    enumeration happens at cold boot only
```

**The power input is USB-C.** Not a barrel jack. I want to state that plainly
because it is the single most common surprise, and if you assume otherwise you
will buy the wrong cable and conclude the board is dead.

**36 W is the whole budget.** Board, RAM and two SATA disks already consume
25–30 W of it. There is very little headroom, and that fact quietly decides the
next section.

## Storage: why "100% full" is normal

The first time I looked at the disk usage I thought something had gone badly
wrong:

```
/         100% full     ← every single day
/DATA      71% used
/media     35% used
```

**The root filesystem is a read-only squashfs.** It is *supposed* to be 100%
full — it is a compressed, immutable system image, and there is no free space in
it by design. Your data lives on separate writable partitions. Nothing is wrong.

I nearly "fixed" this. Do not fix this.

Practical layout on a one-drive build: the OS handles itself, your containers
and their configuration go on the internal storage, and your actual data — the
photos, the media, the backups — goes on the hard drive. Keep those separate and
a rebuild is an afternoon rather than a weekend.

## The upgrade I regret

Here is the useful half of this post.

The board has a PCIe slot, so I bought a **used £30 graphics card** to accelerate
photo recognition in my media library. Months of intermittent debugging followed
to get the PCIe link to train reliably.

Four things I should have read off the spec sheet first, and one I could not:

1. **25 W slot budget, 40 W card.** It physically cannot be slot-powered. You
   need a riser with its own 12 V feed — and then a second power supply, because
   the 36 W main brick has nothing spare. That is two PSUs in a shoebox, and
   grounding between them is its own adventure.
2. **A mining riser is electrically x1**, despite having a x16 slot moulded onto
   it. The USB3 cable is just the physical medium, not the USB protocol. So my
   ceiling was PCIe 2.0 **x1** — around 500 MB/s — before anything went wrong.
3. **No Above-4G decoding.** Every PCI memory window is under 4 GB, the largest
   about 1.25 GB. Fine for a small card; a hard blocker for anything with real
   memory on it.
4. **No hot-plug.** `echo 1 > /sys/bus/pci/rescan` is theatre. If the card was
   not present at cold boot, it is not there.

And the fifth, which no spec sheet would have told me: **by the time I got it
working, the software had dropped support for that generation of card entirely.**
Fixing the hardware would have broken the thing I was accelerating.

**The lesson is not "do not add a GPU".** It is that the constraint was never the
slot — it was the 36 W power budget, and everything else followed from it. Read
the power figure first. It decides what is possible more than the slot type does.

## What I would buy again

- **The board.** Silent, sips power, runs everything I actually use.
- **One large drive** rather than two small ones. Fewer watts, fewer moving
  parts, and the SATA power budget is tight anyway.
- **A UPS**, eventually. Not for uptime — for clean shutdowns. A filesystem
  interrupted mid-write is a much worse evening than an hour offline.

## What I would skip

- **The GPU.** See above. If you genuinely need acceleration, that is a different
  machine, not this one.
- **RAID on a single-box build**, at first. RAID is uptime insurance, not a
  backup. A second copy of your data somewhere else is worth far more than
  mirrored disks in the same shoebox on the same 36 W supply.
- **A second board "for redundancy"** before you have a first one working. Two
  half-configured machines is not high availability.

## What to run on it first

In the order I would do it again:

1. **Something that backs up your phone photos.** Immediate, obvious value, and
   it teaches you storage and permissions on day one.
2. **A reverse proxy.** Everything after this is easier once you can put a real
   hostname and a certificate in front of things.
3. **Monitoring.** Not because it will break — because when it does, you want to
   find out from a notification rather than from someone in your house.

Then stop, and use it for a month before adding more. The most common homelab
failure is not hardware; it is twelve half-configured services and no idea which
one is holding the port.

## The honest summary

A small box and one disk will take you a very long way. The specification that
limits you is almost never the one on the front of the listing — it is the power
budget, the read-only root that looks broken and isn't, and the slot that is
narrower than the connector suggests.

Buy the small thing. Read the power figure. Skip the graphics card.

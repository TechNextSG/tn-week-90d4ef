# The week page

An unlisted working artifact, published here only so it can be opened from a link on a phone.

**Not for distribution, and not a product.** It is served with `noindex` and this repository's
`robots.txt` disallows crawling, so it should not appear in search results. That is
discoverability, not access control: this repository is public, so treat anything in it —
including every staff name on the page — as readable by anyone who has the link.

---

## Changing the schedule

**The `tracks/` files ARE the schedule.** Edit yours on github.com, commit, and the page rebuilds
and updates itself in a minute or two. No pull request, nobody to ask, no laptop needed.

| Your track | File |
|---|---|
| Accounting | [`tracks/accounting.md`](tracks/accounting.md) |
| Property system and till | [`tracks/pms.md`](tracks/pms.md) |
| Reservations, people, handover | [`tracks/trackc.md`](tracks/trackc.md) |
| Everyone together | [`tracks/unified.md`](tracks/unified.md) |
| Joint walks | [`tracks/joint_walk.md`](tracks/joint_walk.md) |

### On a phone or a laptop, same six steps

1. Open your track file (links above).
2. Tap the **pencil** icon, top right.
3. Find your row. Each row is one session.
4. Change what you need — the time, the sentence, who is in it.
5. Scroll down, write one line saying what you changed, and press **Commit changes**.
6. Commit to **`main`**. Do not create a branch — there is nothing waiting to approve it.

That's it. Watch for the small **✓** next to your commit after a minute; the page is updated when
it turns green.

### The one rule

**Never change the `id` column.** Everything else in the row is yours to edit. The ids are how
the page remembers which sessions have been ticked off, so changing one loses that tick silently —
no error, the tick just stops showing. If a session genuinely no longer exists, delete the whole
row; don't renumber it.

### What the columns mean

| Column | What goes in it |
|---|---|
| `id` | Leave it alone. |
| `day` | `mon` `tue` `wed` `thu` `fri` |
| `start`, `end` | 24-hour clock, `14:30` not `2.30pm`. The page prints the friendly version itself. |
| `say` | The sentence Casa reads. Write it for them, not for us. |
| `where` | The room, as Casa would say it. |
| `casa` | Their people, as short names — see [`roster.md`](roster.md). Separate with commas. |
| `ours` | Our people, same list, same idea. |
| `badge` | Leave blank, or `new`, `moved`, `tbc`. `tbc` also prints a line asking them to confirm the time. |

Names go in as the short token from [`roster.md`](roster.md) — `michelle`, not `Michelle`. If the
token isn't in that file the build stops and tells you, so a typo can't quietly drop someone from
a session.

### If it goes red instead of green

Nothing broke. **The page carries on showing the previous version** — a bad edit is never
published. Click the red **✗** next to your commit and it names the file, the row and what's
wrong. Fix it in another commit and the ✗ becomes a ✓.

Things it will stop you on: a time that isn't `HH:MM`, an end before its start, a day that isn't
this week, an empty sentence, a name it doesn't recognise, a changed `id` that a tick still points
at, and a session with nobody from Casa in it.

Things it will only *mention*, never block: two sessions needing the same person at once. It
reports genuinely new clashes and stays quiet about the ones already known about, because deciding
who moves is a judgement, not a mistake.

---

## Ticking sessions off

[`status.json`](status.json) holds what's done. Find the session and change one word:

```json
"tue-0800-a-tour-of-the-front-desk-scr": {
  "state": "done"
}
```

`done`, `cancelled` or `moved`. Leave it `""` for anything that hasn't happened yet. There's an
optional `"note"` that prints as a line under the session — useful for *"moved to 3pm"*.

This one is fetched straight by the page, so a tick shows within a minute.

---

## The other files

| File | What it is |
|---|---|
| [`roster.md`](roster.md) | Who each short name means, and what they're called on the page. Row order is the order people are listed. |
| [`week.md`](week.md) | The five day headings, and the "what we need from you" cards. |
| `index.html`, `schedule.json` | **Generated. Don't edit them** — they're rebuilt from `tracks/` on every commit, so an edit here is overwritten. |
| `build.py` | Builds the page. `python build.py --check` validates without writing anything, if you have a checkout. |
| `page.template.html` | The page's layout and styling. |

## Who owns what

Ownership is written into each track file's header and into [`CODEOWNERS`](CODEOWNERS). Nothing
stops you editing someone else's track — if you're covering for them on the day, go ahead. Every
change records who made it, which is the only audit anyone needs here.

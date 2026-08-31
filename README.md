# The week page

An unlisted working artifact, published here only so it can be opened from a link on a phone.

**Not for distribution, and not a product.** It is served with `noindex` and this repository's
`robots.txt` disallows crawling, so it should not appear in search results. That is
discoverability, not access control: this repository is public, so treat anything in it —
including every staff name on the page — as readable by anyone who has the link.

---

## The two files you can edit

Both are fetched by the page on load, so an edit committed on github.com is live in **about a
minute** — no rebuild, no Python, no local checkout. They behave **differently** when the page is
next re-cut from the working tree, and that difference is the thing to remember:

| File | What it holds | What a rebuild does to it |
|---|---|---|
| `status.json` | ticks — done, cancelled, moved, plus a note | **merges.** Your ticks survive |
| `schedule.json` | the schedule itself — times, wording, who, where | **overwrites.** Your edits are lost |

### `status.json` — ticking sessions off

Find the session and change one word:

```json
"tue-0800-a-tour-of-the-front-desk-scr": {
  "when": "Tuesday 1 September, 8am",
  "title": "A tour of the front-desk screens",
  "state": "done",
  "note": ""
}
```

- `state` accepts **`done`**, **`cancelled`**, **`moved`**. Leave it `""` for anything that has
  not happened. Any other value is ignored rather than displayed.
- `note` is optional and shows as a line under the session — use it for *"moved to 4pm, boat
  came back late"*.
- `when` and `title` are there so you can see what you are ticking. Editing them does nothing;
  the next build overwrites them.

### `schedule.json` — fixing the schedule itself

This is the schedule the page draws. Change a `from`/`to` to move a session, a `what` to reword
it, a `where` or the `casa`/`ours` name lists to change who is in the room.

- **Leave `id` alone.** The `status.json` ticks are keyed on it.
- `start`/`end` are the 24-hour values that drive the ordering and the now-marker. Change them
  **together with** `from`/`to`, or the page will display one time and sort by another.
- **A rebuild overwrites this file.** Anything corrected here must also be corrected in
  `_render/sessions_final.json` (or in the wording map) or it is lost at the next re-cut.
  `--check` reports the difference by name before that happens — see below.

## How the page decides which schedule to show

`index.html` carries a **baked copy** of the schedule, so the page draws itself with no network
call and works on one bar of signal. `schedule.json` is fetched on top of it and **wins when it
loads**. If it is missing, unreachable or not a usable schedule — unparseable, or an empty session
list — the page falls back to the baked copy rather than rendering a blank week.

**The footer says which copy is on screen**, so "did my edit take?" is answerable from the phone
instead of assumed. If it still says *"Showing the built-in copy"* after you have committed, the
edit has not landed — reload, and check the JSON is valid.

## Everything else is generated

**Editing `index.html` in place is pointless** — the next build overwrites it. To change anything
permanently, change the source in the working tree and re-publish:

```
python _render/render_pages.py
```

That command merges `status.json` rather than replacing it: sessions that still exist keep
whatever you set, sessions that have gone are dropped, and new ones arrive blank. It prints
exactly what it dropped, so a session disappearing from the week is never silent. It **replaces**
`schedule.json`.

## Checking it is still current

The footer of the page shows the date it was built and an eight-character reference. To find out
whether that reference still matches the live schedule, from the working tree:

```
python _render/render_pages.py --check
```

It writes nothing and answers **CURRENT** or **STALE**, and separately reports whether the
published `schedule.json` still matches what a rebuild would write — which is how you find a
github.com edit *before* a re-cut destroys it. Worth running before sending the link to anyone —
on 31 August the schedule changed seven times between 01:27 and 07:13, and a page built at the
start of that would have promised two people a session that no longer existed.

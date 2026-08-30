# The week page

An unlisted working artifact, published here only so it can be opened from a link on a phone.

**Not for distribution, and not a product.** It is served with `noindex` and this repository's
`robots.txt` disallows crawling, so it should not appear in search results. That is
discoverability, not access control: this repository is public, so treat anything in it —
including every staff name on the page — as readable by anyone who has the link.

---

## The one file you edit

**`status.json`** — and nothing else. Everything else here is generated.

To mark a session done, find it and change one word:

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

Edit it straight on github.com, commit, and the page shows it **within about a minute**. No
rebuild, no Python, no local checkout. The page fetches this file on load, so a schedule note
posted from a phone at the resort is live before you have put the phone away.

If `status.json` is ever unreadable — bad JSON, a failed commit — the page still draws the whole
schedule and simply shows nothing ticked. It fails to the safe side.

## Everything else is generated

`index.html` carries the schedule baked in, so the page works on a weak connection and needs no
network call to draw itself. **Editing it in place is pointless** — the next build overwrites it.
To change a time, a session, a person or the wording, change the source in the working tree and
re-publish:

```
python _render/render_pages.py
```

That command merges `status.json` rather than replacing it: sessions that still exist keep
whatever you set, sessions that have gone are dropped, and new ones arrive blank. It prints
exactly what it dropped, so a session disappearing from the week is never silent.

## Checking it is still current

The footer of the page shows the date it was built and an eight-character reference. To find out
whether that reference still matches the live schedule, from the working tree:

```
python _render/render_pages.py --check
```

It writes nothing and answers **CURRENT** or **STALE**. Worth running before sending the link to
anyone — on 31 August the schedule changed five times between 01:27 and 06:57, and a page built
at the start of that would have promised two people a session that no longer existed.

#!/usr/bin/env python3
"""Build the week page from the per-track markdown in this repository.

    python build.py                 build in place
    python build.py --check         validate only, write nothing
    python build.py --self-test     push known-bad input through every check

The markdown in tracks/ IS the schedule. Nothing here reads a file from outside this repository,
and nothing here is generated -- so the page can be rebuilt by anyone with a checkout, and a
teammate editing tracks/<theirs>.md on github.com is editing the source of truth rather than a
copy that the next rebuild overwrites.

Two files are inputs the build never writes:

  status.json   the done-ticks, hand-edited. Its ids must all resolve to a session, and an id
                that does not is a refusal -- an orphaned tick simply stops showing on the page,
                which is the one failure nobody would notice.
  baseline-clashes.json   double-bookings that already existed. Clashes ABOVE this baseline are
                reported and never refuse: a clash is a scheduling judgement, not a broken file.

Exit codes: 0 built (or valid), 2 refused. On a refusal nothing is written, so the previously
deployed page stays live.
"""
import argparse, datetime, html, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------------------------------
# structural constants -- these describe the PAGE, not the schedule, so they live in code
# ------------------------------------------------------------------------------------------

DAY_TOKENS = ["mon", "tue", "wed", "thu", "fri"]

# (person token, css class). The display name comes from roster.md so it is stated once.
OWNERS = [("pms_developer", "o-philip"),
          ("acct_implementer", "o-aj"),
          ("functional_lead", "o-jett")]
JOINT = ("More than one of us", "o-team")

FLAGS = {
    "new": ("New", "f-new", ""),
    "moved": ("Moved", "f-moved", ""),
    "tbc": ("Time to be confirmed", "f-tbc",
            "This time is our guess. Tell us when you actually count and we will move it."),
}

STATES = {
    "done": ("Done", "s-done"),
    "cancelled": ("Cancelled", "s-cx"),
    "moved": ("Moved", "s-mv"),
}

# Our vocabulary, which a client-owned page must never carry. These are shapes that have actually
# leaked into Casa documents before.
LEAK_PATTERNS = [
    ("REQ-ID", r"\bREQ-\d{2,}"),
    ("SCRIPT-ID", r"\bUAT-\d{2,}"),
    ("SCRIPT-ID", r"\bPMS-\d{2}\b"),
    ("REGISTER-ID", r"\bD-\d{2,}\b"),
    ("GATE-ID", r"\bG[1-6]\b"),
    ("TRACK-NAME", r"\btrack ?[Cc]\b|\btrackc\b"),
    ("TOOL-NAME", r"\bservitor\b|\bfitgap\b|\bStudio\b"),
]

MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"])}

COLUMNS = ["id", "day", "start", "end", "say", "where", "casa", "ours", "badge"]
TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class Refuse(Exception):
    """A validation failure. Collected so one run reports every problem, not just the first."""


# ------------------------------------------------------------------------------------------
# markdown table reading
# ------------------------------------------------------------------------------------------

def read(path):
    with io.open(os.path.join(HERE, path), encoding="utf-8") as fh:
        return fh.read()


def unescape(cell):
    return cell.replace("\\|", "|").strip()


def tables(text):
    """Every pipe table in a markdown document, as a list of dicts keyed by its own header.

    Deliberately tolerant about what surrounds a table -- prose, headings and blank lines are
    all skipped -- because these files are meant to be edited by hand and a teammate adding a
    sentence above their table must not break the build.
    """
    out, rows, head = [], None, None
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            if head is not None and rows:
                out.append((head, rows))
            head, rows = None, None
            continue
        cells = [unescape(c) for c in s.strip("|").split("|")]
        if head is None:
            head, rows = [c.lower() for c in cells], []
        elif set("".join(cells)) <= set("-: "):
            continue                                   # the ---|--- separator
        else:
            rows.append(dict(zip(head, cells)))
    if head is not None and rows:
        out.append((head, rows))
    return out


def one_table(text, path, want):
    """The single table in `text` carrying every column in `want`."""
    found = [rows for head, rows in tables(text) if set(want) <= set(head)]
    if len(found) != 1:
        raise Refuse("%s: expected exactly one table with columns %s, found %d"
                     % (path, ", ".join(want), len(found)))
    return found[0]


# ------------------------------------------------------------------------------------------
# roster.md / week.md
# ------------------------------------------------------------------------------------------

def load_roster(errs):
    """(who, order, team) from roster.md.

    `who` maps token -> (full name, role, called). `called` is what the page prints and is
    authored rather than derived: deriving it from the full name produced "Armando" for Dong.
    `order` is the ROW ORDER of the Casa table, which is the order people appear on the page.
    """
    text = read("roster.md")
    who, order, team = {}, [], {}
    casa_rows = None
    team_rows = None
    for head, rows in tables(text):
        if "called" in head:
            casa_rows = rows
        elif set(("token", "name", "role")) <= set(head):
            team_rows = rows
    if casa_rows is None:
        errs.append("roster.md: no Casa table (it is the one with a `called` column)")
    if team_rows is None:
        errs.append("roster.md: no team table (token / name / role)")
    for r in casa_rows or []:
        tok = r["token"]
        if tok in who:
            errs.append("roster.md: token %r listed twice" % tok)
        who[tok] = (r["name"], "" if r["role"] == "-" else r["role"], r["called"])
        order.append(tok)
    for r in team_rows or []:
        tok = r["token"]
        if tok in team:
            errs.append("roster.md: team token %r listed twice" % tok)
        team[tok] = (r["name"], r["role"])
    overlap = sorted(set(who) & set(team))
    if overlap:
        errs.append("roster.md: %s appear(s) in BOTH tables -- a person is theirs or ours"
                    % ", ".join(overlap))
    return who, order, team


def load_week(errs):
    """(year, days, needs) from week.md, with every day label's weekday checked."""
    text = read("week.md")
    m = re.search(r"^Year:\s*(\d{4})\s*$", text, re.M)
    if not m:
        errs.append("week.md: no `Year: YYYY` line")
        return 0, [], []
    year = int(m.group(1))

    days = []
    for r in one_table(text, "week.md", ("day", "label")):
        tok, label = r["day"], r["label"]
        if tok not in DAY_TOKENS:
            errs.append("week.md: %r is not one of %s" % (tok, "/".join(DAY_TOKENS)))
            continue
        parts = label.split()
        if len(parts) < 3 or parts[2] not in MONTHS:
            errs.append("week.md: day label %r is not `Weekday DD Month`" % label)
            continue
        try:
            d = datetime.date(year, MONTHS[parts[2]], int(parts[1]))
        except ValueError as exc:
            errs.append("week.md: day label %r is not a real date (%s)" % (label, exc))
            continue
        # The error that reads perfectly and sends people in on the wrong day.
        if d.strftime("%A") != parts[0]:
            errs.append("week.md: DAY LABEL WRONG -- %r is a %s in %d"
                        % (label, d.strftime("%A"), year))
            continue
        days.append({"key": tok, "label": label, "date": d.isoformat()})

    needs = [{"what": r["what"], "detail": r["detail"]}
             for r in one_table(text, "week.md", ("what", "detail"))]
    return year, days, needs


# ------------------------------------------------------------------------------------------
# tracks/
# ------------------------------------------------------------------------------------------

def mins(t):
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def t12(t):
    h, m = t.split(":")
    h = int(h)
    ap = "am" if h < 12 else "pm"
    hh = h if 1 <= h <= 12 else (h - 12 if h > 12 else 12)
    return "%d.%s%s" % (hh, m, ap) if m != "00" else "%d%s" % (hh, ap)


def tokens(cell):
    return [t.strip() for t in cell.split(",") if t.strip()]


def parse_rows(rows, track, who, order, team, days, errs, seen_ids, label=None):
    """Validate parsed table rows into page-shaped sessions. NO file access.

    Kept free of I/O so the self-test can call it directly. The first version validated inside the
    directory walk, and the self-test reached it through a monkeypatched reader guarded by
    `os.path.isdir(tracks/)` -- which was false, so every mutation produced an empty error list and
    read as caught, and the "a valid row passes" control produced an empty list too and read as
    passing. A control whose verdict has the same shape as the bug cannot see the bug.
    """
    day_index = {d["key"]: i for i, d in enumerate(days)}
    owner_name = {tok: (team.get(tok, ("?",))[0], cls) for tok, cls in OWNERS}
    src = label or ("tracks/%s.md" % track)
    out = []

    for n, r in enumerate(rows, 1):
        where = "%s row %d" % (src, n)
        sid = r.get("id", "")
        if not sid:
            errs.append("%s: empty id" % where)
            continue
        if sid in seen_ids:
            errs.append("%s: duplicate id %r (also in %s)" % (where, sid, seen_ids[sid]))
            continue
        seen_ids[sid] = where

        if r["day"] not in day_index:
            errs.append("%s (%s): day %r is not a day of this week" % (where, sid, r["day"]))
            continue
        for k in ("start", "end"):
            if not TIME_RE.match(r[k]):
                errs.append("%s (%s): %s %r is not a 24-hour HH:MM time" % (where, sid, k, r[k]))
        if not (TIME_RE.match(r["start"]) and TIME_RE.match(r["end"])):
            continue
        if mins(r["end"]) <= mins(r["start"]):
            errs.append("%s (%s): ends %s, which is not after %s"
                        % (where, sid, r["end"], r["start"]))
            continue

        for k in ("say", "where"):
            if not r[k]:
                errs.append("%s (%s): %s is empty -- a session Casa can see must say what it is "
                            "and where" % (where, sid, k))
        badge = r["badge"]
        if badge and badge not in FLAGS:
            errs.append("%s (%s): badge %r is not one of %s (or blank)"
                        % (where, sid, badge, "/".join(FLAGS)))

        casa_toks, ours_toks = tokens(r["casa"]), tokens(r["ours"])
        for tok in casa_toks:
            if tok not in who:
                errs.append("%s (%s): %r is not in roster.md's Casa table" % (where, sid, tok))
        for tok in ours_toks:
            if tok not in team:
                errs.append("%s (%s): %r is not in roster.md's team table" % (where, sid, tok))
        # The one edit that would put an internal session in front of the client. This
        # repository is public, so it refuses rather than warns.
        if not casa_toks:
            errs.append("%s (%s): the casa column is empty, so this is not a client session. "
                        "Internal sessions do not belong in this repository -- it is public."
                        % (where, sid))

        people = set(casa_toks) | set(ours_toks)
        mine = [(owner_name[tok][0], owner_name[tok][1]) for tok, _ in OWNERS if tok in people]
        owner, ocls = mine[0] if len(mine) == 1 else JOINT

        out.append({
            "id": sid, "_track": track,
            "day": r["day"], "start": r["start"], "end": r["end"],
            "from": t12(r["start"]), "to": t12(r["end"]),
            "mins": mins(r["end"]) - mins(r["start"]),
            "what": r["say"], "where": r["where"],
            "casa": [who[t][2] for t in order if t in casa_toks],
            "ours": [team[t][0] for t in ours_toks if t in team],
            "owner": owner, "ocls": ocls, "flag": badge,
        })
    return out


def load_tracks(who, order, team, days, errs):
    """Every row of every tracks/*.md, validated, as page-shaped session dicts."""
    tracks_dir = os.path.join(HERE, "tracks")
    if not os.path.isdir(tracks_dir):
        errs.append("tracks/ does not exist")
        return []
    files = sorted(f for f in os.listdir(tracks_dir) if f.endswith(".md"))
    if not files:
        errs.append("tracks/ holds no .md files")
        return []

    seen_ids, out = {}, []
    for fname in files:
        text = read(os.path.join("tracks", fname))
        try:
            rows = one_table(text, "tracks/" + fname, COLUMNS)
        except Refuse as exc:
            errs.append(str(exc))
            continue
        out += parse_rows(rows, fname[:-3], who, order, team, days, errs, seen_ids)

    day_index = {d["key"]: i for i, d in enumerate(days)}
    out.sort(key=lambda s: (day_index.get(s["day"], 99), s["start"], s["end"], s["id"]))
    return out


# ------------------------------------------------------------------------------------------
# the two inputs the build validates but never writes
# ------------------------------------------------------------------------------------------

def check_status(sessions, errs):
    path = os.path.join(HERE, "status.json")
    if not os.path.exists(path):
        return
    try:
        status = json.loads(read("status.json"))
    except ValueError as exc:
        errs.append("status.json is not valid JSON (%s). Fix it or delete it." % exc)
        return
    ids = {s["id"] for s in sessions}
    orphans = sorted(i for i in status.get("sessions", {}) if i not in ids)
    if orphans:
        errs.append("status.json ticks %d session(s) that no longer exist: %s. An id was changed "
                    "or a row deleted -- the tick would silently stop showing. Restore the id, or "
                    "remove the entry from status.json." % (len(orphans), ", ".join(orphans[:5])))


def clashes(sessions):
    """Cross-track double-bookings, as {frozenset(pair): sorted people}."""
    out = {}
    for i, a in enumerate(sessions):
        for b in sessions[i + 1:]:
            if a["_track"] == b["_track"] or a["day"] != b["day"]:
                continue
            if min(mins(a["end"]), mins(b["end"])) - max(mins(a["start"]), mins(b["start"])) <= 0:
                continue
            shared = sorted(set(a["casa"] + a["ours"]) & set(b["casa"] + b["ours"]))
            if shared:
                out[frozenset((a["id"], b["id"]))] = shared
    return out


def report_clashes(sessions):
    """Reports, never refuses. A clash is a scheduling judgement, not a broken file."""
    baseline = set()
    path = os.path.join(HERE, "baseline-clashes.json")
    if os.path.exists(path):
        try:
            for c in json.loads(read("baseline-clashes.json")).get("clashes", []):
                baseline.add(frozenset(c["pair"]))
        except (ValueError, KeyError, TypeError):
            print("  ! baseline-clashes.json unreadable -- every clash will report as new")
    found = clashes(sessions)
    new = {k: v for k, v in found.items() if k not in baseline}
    print("  clashes      %d cross-track (%d in baseline, %d new)"
          % (len(found), len(found) - len(new), len(new)))
    for pair, people in sorted(new.items(), key=lambda kv: sorted(kv[0])):
        a, b = sorted(pair)
        print("      NEW: %s is in both %s and %s" % (", ".join(people), a, b))
    return len(new)


# ------------------------------------------------------------------------------------------
# render
# ------------------------------------------------------------------------------------------

def check_client_clean(text):
    """Our vocabulary in a page a Casa reader will see.

    NOTE this is the pattern half only. The original also compared the rendered page against the
    internal session titles, and that half cannot run here: the file holding those titles is
    deliberately not in this repository, because the repository is public.
    """
    out = []
    for kind, pat in LEAK_PATTERNS:
        hits = sorted(set(re.findall(pat, text)))
        if hits:
            out.append((kind, ", ".join(hits[:6])))
    return out


def build_week(sessions, who, order, team, days, needs):
    by_id = {s["id"]: s for s in sessions}
    people = []
    for tok in order:
        name, role, short = who[tok]
        ids = [s["id"] for s in sessions if short in s["casa"]]
        if ids:
            people.append({"key": tok, "name": name, "role": role, "short": short,
                           "sessions": ids, "mins": sum(by_id[i]["mins"] for i in ids)})
    return {
        "client": "Casa Escondida",
        "days": days,
        "sessions": [{k: v for k, v in s.items() if k != "_track"} for s in sessions],
        "people": people,
        "team": [{"name": n, "role": r} for n, r in team.values()],
        "needs": needs,
    }


def render_html(week, stamp, ref, team):
    days = week["days"]
    page = read("page.template.html")
    subs = (
        ("@@CLIENT@@", week["client"]),
        ("@@RANGE@@", "%s – %s" % (days[0]["label"], days[-1]["label"])),
        ("@@STAMP@@", stamp),
        ("@@REF@@", ref),
        ("@@WEEK@@", json.dumps(week, ensure_ascii=False, separators=(",", ":"))),
        ("@@STATES@@", json.dumps(STATES, ensure_ascii=False, separators=(",", ":"))),
        ("@@FLAGS@@", json.dumps(FLAGS, ensure_ascii=False, separators=(",", ":"))),
        ("@@KEY@@", json.dumps([[team.get(t, ("?",))[0], c] for t, c in OWNERS] + [list(JOINT)],
                               ensure_ascii=False, separators=(",", ":"))),
    )
    for k, v in subs:
        page = page.replace(k, v)
    if "@@" in page:
        raise Refuse("page.template.html has an unreplaced @@PLACEHOLDER@@")
    return page


SCHEDULE_README = [
    "GENERATED. Do not edit -- edit tracks/*.md instead and this file is rebuilt.",
    "The page fetches this file and prefers it over the copy baked into index.html, so the",
    "footer tells you which one you are looking at.",
]


def fingerprint(week):
    body = json.dumps(week["sessions"], sort_keys=True, ensure_ascii=False).encode("utf-8")
    import hashlib
    return hashlib.sha256(body).hexdigest()[:8]


# ------------------------------------------------------------------------------------------

def load_all(errs):
    who, order, team = load_roster(errs)
    _year, days, needs = load_week(errs)
    if not days:
        errs.append("week.md produced no usable days -- nothing can be built")
        return None
    sessions = load_tracks(who, order, team, days, errs)
    if not sessions and not errs:
        errs.append("tracks/*.md produced no sessions")
    check_status(sessions, errs)
    return who, order, team, days, needs, sessions


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    ap.add_argument("--self-test", action="store_true", help="prove every check fires")
    ap.add_argument("--outdir", default=HERE, help="where to write (default: beside this script)")
    ap.add_argument("--stamp", default="", help="build stamp (default: today)")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    errs = []
    loaded = load_all(errs)
    if errs:
        print("REFUSED -- %d problem(s), nothing written. The live page is unchanged." % len(errs))
        for e in errs:
            print("  * %s" % e)
        return 2
    who, order, team, days, needs, sessions = loaded

    week = build_week(sessions, who, order, team, days, needs)
    ref = fingerprint(week)
    stamp = args.stamp or datetime.date.today().isoformat()
    try:
        page = render_html(week, stamp, ref, team)
    except Refuse as exc:
        print("REFUSED -- %s" % exc)
        return 2

    leaks = check_client_clean(re.sub(r"<script.*?</script>", "", page, flags=re.S))
    if leaks:
        print("REFUSED -- the page carries our own vocabulary, which Casa must never see:")
        for kind, detail in leaks:
            print("  * %-12s %s" % (kind, detail))
        return 2

    print("%d sessions | %d people | %d days | ref %s"
          % (len(sessions), len(week["people"]), len(days), ref))
    report_clashes(sessions)

    if args.check:
        print("VALID -- nothing written (--check)")
        return 0

    if not os.path.isdir(args.outdir):
        os.makedirs(args.outdir)
    for name, body in (("index.html", page),
                       ("schedule.json", json.dumps(dict(week, _readme=SCHEDULE_README),
                                                    ensure_ascii=False, indent=1) + "\n")):
        with io.open(os.path.join(args.outdir, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        print("  wrote %-14s %6d chars" % (name, len(body)))
    return 0


# ------------------------------------------------------------------------------------------
# self-test -- every check must FIRE on input designed to break it
# ------------------------------------------------------------------------------------------

def self_test():
    """Where a check's passing verdict is an empty error list, a broken check reads as a pass.

    So each check is handed input that must break it, and the run fails if the check stays quiet.
    """
    ok = True

    def want(label, errs, fragment):
        nonlocal ok
        hit = any(fragment in e for e in errs)
        if not hit:
            ok = False
        print("  %-4s %-34s %s" % ("ok" if hit else "FAIL", label,
                                   "" if hit else "expected %r in %s" % (fragment, errs[:2])))

    who = {"dong": ("Armando Vergara", "GM", "Dong")}
    order = ["dong"]
    team = {"functional_lead": ("Jett", "lead")}
    days = [{"key": "mon", "label": "Monday 31 August", "date": "2026-08-31"}]

    base = {"id": "a", "day": "mon", "start": "09:00", "end": "10:00",
            "say": "A thing", "where": "The meeting room", "casa": "dong",
            "ours": "functional_lead", "badge": ""}

    def run(rows):
        """(errors, sessions) from the validator directly -- no filesystem, nothing to skip."""
        errs, seen = [], {}
        got = parse_rows(rows, "t", who, order, team, days, errs, seen, label="<self-test>")
        return errs, got

    print("self-test")

    # PRECONDITION, asserted before any mutation. Every check below has an empty error list as its
    # favourable verdict, so a validator that never runs reports every mutation as caught. This
    # asserts the validator is reachable and productive on valid input first.
    errs, got = run([dict(base)])
    if errs or len(got) != 1:
        print("  FAIL %-34s validator not reachable: errs=%s sessions=%d"
              % ("precondition: valid row builds", errs[:2], len(got)))
        print("\nself-test: FAIL (every result below would be meaningless)")
        return 2
    print("  ok   %-34s 1 session built, 0 errors" % "precondition: valid row builds")

    for label, mutate, fragment in [
        ("bad day refused", {"day": "sat"}, "not a day of this week"),
        ("bad time refused", {"start": "9am"}, "not a 24-hour"),
        ("end before start refused", {"end": "08:00"}, "not after"),
        ("empty say refused", {"say": ""}, "say is empty"),
        ("empty where refused", {"where": ""}, "where is empty"),
        ("unknown badge refused", {"badge": "urgent"}, "is not one of"),
        ("unknown casa token refused", {"casa": "nobody"}, "not in roster.md's Casa table"),
        ("unknown ours token refused", {"ours": "nobody"}, "not in roster.md's team table"),
        ("empty casa refused", {"casa": ""}, "it is public"),
    ]:
        errs, _ = run([dict(base, **mutate)])
        want(label, errs, fragment)

    errs, _ = run([dict(base), dict(base, day="mon", start="11:00", end="12:00")])
    want("duplicate id refused", errs, "duplicate id")

    clean = check_client_clean("Walk the property together, rooms and rates")
    dirty = check_client_clean("Run REQ-104 and PMS-01 before G3")
    if clean or not dirty:
        ok = False
        print("  FAIL %-34s clean=%s dirty=%s" % ("leak check both polarities", clean, dirty))
    else:
        print("  ok   %-34s %d kind(s) caught" % ("leak check both polarities", len(dirty)))

    print("\nself-test: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
